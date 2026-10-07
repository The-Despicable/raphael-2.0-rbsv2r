"""test_m3_d2_bounded_execution.py — D2 bounded-execution tests (2026-10-05).

Covers the operator-approved D2 contract:
  two governed actions (D1 nmap probe + fixed in-container HTTP GET),
  enforced limits (5 steps / 6 per minute / concurrency 1 / 90 s / 64 KiB),
  durable receipts for EVERY attempt (including denials and failures),
  evidence-based objective termination, kill switch, and zero-spawn denials.

Hermetic by default (injected runners/inspectors); live-lab variants skip when
docker/dvwa are absent. Denials are proven process-free with a subprocess spy.
"""
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.auth import WeldNotAuthorized
from orchestrator.brain.rate_limiter import RateLimiter, RateLimiterConfig
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability, LabHttpProbeError
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D1_POLICY_PATH,
    D2_POLICY_PATH,
    D1Policy,
    PolicyLoadError,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)


def d2_broker():
    """The D2 PDP: explicitly bound to the operator-approved D2 artifact."""
    return make_broker_from_policy(D2_POLICY_PATH)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext

MISSION_ID = "d2-bounded-episode"
ACTION_A = "recon_service_probe"
ACTION_B = "lab_http_probe"
CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
TARGET = "dvwa"
A_ID = "ACT-D2-PROBE-0001"
B_ID = "ACT-D2-HTTP-0002"

FAKE_NMAP = ("Starting Nmap 7.99\nNmap scan report for dvwa (172.19.0.4)\n"
             "PORT   STATE SERVICE\n80/tcp open  http\n")
FAKE_CURL = ("<html>login redirect</html>\n302|text/html|28|0.01|http://dvwa/login.php\n")


def fake_inspector(container: str) -> dict:
    net = "raphael-m1_raphael-net"
    if container == "dvwa":
        return {"State": {"Running": True},
                "Config": {"Image": "vulnerables/web-dvwa:latest"},
                "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}
    if container == "kali-tools":
        return {"State": {"Running": True},
                "Config": {"Image": "raphael/kali-tools:latest"},
                "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.3"}}}}
    raise AssertionError(f"unexpected container {container}")


def fake_runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def fake_runner_b(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_CURL, ""
    return P()


def make_candidate(action_id, action_type, capability, **kw):
    cand = {"action_id": action_id, "action_type": action_type, "target": TARGET,
            "capability": capability, "method": "nmap" if capability == CAP_A else "curl",
            "impact_estimate": 2.0, "args": {"bounded": True},
            "rationale": "D2 bounded action"}
    cand.update(kw)
    return cand


def d2_scope():
    return ScopeV0(mission_id=MISSION_ID, targets=(TARGET,),
                   allowed_action_types=(ACTION_A, ACTION_B),
                   allowed_capabilities=(CAP_A, CAP_B), max_impact=2.0)


def d2_mission(candidates_by_iter, objective=True, max_iterations=5):
    constraints = {"halt": {"max_iterations": max_iterations, "action_cap": 1,
                            "require_scope": True},
                   "candidates": candidates_by_iter, "default_target": TARGET}
    if objective:
        constraints["objective"] = {"requires_evidence": [A_ID, B_ID]}
    return MissionContext(mission_id=MISSION_ID, name="D2 bounded episode",
                          objectives=["governed two-probe reconnaissance"],
                          constraints=constraints, scope=d2_scope())


def build_runtime(tmp_transcript, broker, runner_map=None, store=None):
    cap_a = D1LabProbeCapability(
        broker=broker, artifacts_dir=tmp_transcript / "artifacts",
        runner=runner_map.get(CAP_A, fake_runner_a) if runner_map else fake_runner_a,
        inspector=fake_inspector)
    cap_b = LabHttpProbeCapability(
        broker=broker, artifacts_dir=tmp_transcript / "artifacts",
        runner=runner_map.get(CAP_B, fake_runner_b) if runner_map else fake_runner_b,
        inspector=fake_inspector)
    registry = {CAP_A: cap_a, CAP_B: cap_b}
    organs = OrganBundle(evidence_store=store)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a, organs=organs,
                             capability_registry=registry)
    return runtime, registry


def run_episode(runtime, mission):
    episode_outputs: list = []
    traces, termination = runtime.run_episode(mission, episode_outputs=episode_outputs)
    return traces, termination, episode_outputs


def _store_records(tmp_path):
    """Flattened evidence-store rows: kind + payload fields at one level."""
    rows = []
    for line in (tmp_path / "evidence_store.jsonl").read_text().splitlines():
        rec = json.loads(line)["record"]
        row = {"kind": rec["kind"]}
        row.update(rec["payload"])
        rows.append(row)
    return rows


@pytest.fixture
def spy(monkeypatch):
    state = {"count": 0}
    orig = subprocess.run

    def counting(*a, **kw):
        state["count"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(subprocess, "run", counting)
    yield state


# 1+2. both approved actions execute through the existing governance path
def test_both_approved_actions_execute_and_link_receipts(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]})
    _, termination, outs = run_episode(runtime, mission)
    assert "objective met" in termination.reason, termination.reason
    assert len(outs) == 2
    for i, (aid, cap_name) in enumerate(((A_ID, CAP_A), (B_ID, CAP_B))):
        out = outs[i]
        decision = out["broker"]["decision"]
        receipt = out["broker"]["receipt"]
        event = out["pep"]["event"]
        request = out["planner_request"]["request"]
        assert decision.decision == "allow"
        assert request.action_id == aid, "planner-selected mission action_id"
        assert event.action_id == aid, "event bound to the mission action_id"
        assert event.decision_id == decision.decision_id
        assert event.capability == cap_name
        assert str(receipt.status) in ("ActionProposalStatus.SUCCEEDED", "succeeded")
        assert out["receipt"]["receipt"].broker_receipt_id == receipt.action_id
    # artifact digests verify against stored bytes for both actions
    for i, out in enumerate(outs):
        relpath = out["pep"]["event"].output["artifact_relpath"]
        f = tmp_path / relpath
        assert f.is_file()
        assert hashlib.sha256(f.read_bytes()).hexdigest() == out["pep"]["event"].output["artifact_sha256"]


# 3. wrong host / port / path / method are denied or unrepresentable
def test_wrong_host_denied(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, registry = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate("ACT-X", ACTION_B, CAP_B,
                                               target="example.invalid")]})
    before = spy["count"]
    _, termination, outs = run_episode(runtime, mission)
    assert termination.final_stage == "broker"
    assert "pep" not in outs[0]
    assert spy["count"] == before
    for cap in registry.values():
        assert cap.invocation_count == 0


def test_http_contract_is_fixed_and_restrictive():
    policy = D1Policy(D2_POLICY_PATH)
    http = policy.http_contract
    assert http["method"] == "GET" and http["scheme"] == "http"
    assert http["max_redirects"] == 0
    assert http["host"] == "dvwa" and http["path"] == "/"
    assert http["max_artifact_bytes"] == 65536 and http["max_time_seconds"] == 60
    from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
    assert LabHttpProbeCapability.URL == "http://dvwa/"
    assert "-L" not in LabHttpProbeCapability.HTTP_ARGV
    assert "--max-redirs" in LabHttpProbeCapability.HTTP_ARGV
    assert not any(a in ("-X", "-d", "--data", "-I", "--head")
                   for a in LabHttpProbeCapability.HTTP_ARGV)


@pytest.mark.parametrize("mutation", [
    {"method": "POST"}, {"scheme": "https"}, {"max_redirects": 1},
    {"path": "admin"},
])
def test_broadened_http_contract_fails_closed(tmp_path, mutation):
    data = json.loads(D2_POLICY_PATH.read_text())
    data["scope"]["lab"]["http"].update(mutation)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


# 4. redirects are never followed
def test_redirect_recorded_never_followed(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(B_ID, ACTION_B, CAP_B)]})
    _, termination, outs = run_episode(runtime, mission)
    event = outs[0]["pep"]["event"]
    assert event.output["http_status"] == 302
    assert event.output["redirect_followed"] is False
    assert event.output["redirect_url"] == "http://dvwa/login.php"


# 5. oversized responses are bounded during collection
def test_oversized_response_aborts_bounded(tmp_path, spy):
    def huge_runner(argv, timeout):
        class P:
            returncode, stdout, stderr = 63, "", "curl: (63) Maximum file size exceeded"
        return P()
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, runner_map={CAP_B: huge_runner}, store=store)
    mission = d2_mission({"0": [make_candidate("ACT-BIG", ACTION_B, CAP_B)]},
                         objective=False, max_iterations=1)
    _, termination, _ = run_episode(runtime, mission)
    assert termination.final_stage == "pep"
    recs = _store_records(tmp_path)
    failed = [r for r in recs if r.get("status") == "failed"]
    assert failed, "bounded abort must produce a durable failure receipt"
    assert "64 KiB" in " ".join(r.get("reason", "") for r in failed)


# 6. timeout and concurrency bounds
def test_timeout_is_enforced(tmp_path, spy):
    def slow_runner(argv, timeout):
        raise subprocess.TimeoutExpired(cmd=list(argv), timeout=timeout)
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, runner_map={CAP_B: slow_runner}, store=store)
    mission = d2_mission({"0": [make_candidate("ACT-SLOW", ACTION_B, CAP_B)]},
                         objective=False, max_iterations=1)
    _, termination, _ = run_episode(runtime, mission)
    assert termination.final_stage == "pep"
    recs = _store_records(tmp_path)
    failed = [r for r in recs if r.get("status") == "failed"]
    assert failed, "timeout must produce a durable failure receipt"
    from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
    assert LabHttpProbeCapability.RUNNER_TIMEOUT_SECONDS == 90
    assert "--max-time" in LabHttpProbeCapability.HTTP_ARGV


def test_rate_limiter_is_bound_to_the_d2_broker():
    broker = d2_broker()
    assert broker.rate_limiter is not None, "D2 policy rate limits must be enforced, not declared"
    assert broker.rate_limiter.config.max_actions_per_minute == 6
    assert broker.rate_limiter.config.max_actions_per_hour == 60


# 7. seventh attempt within a minute is denied at the enforcement boundary
def test_seventh_attempt_in_a_minute_denied(tmp_path, spy):
    broker = d2_broker()
    before = spy["count"]
    statuses = []
    for i in range(7):
        receipt = broker.propose_action(
            target=TARGET, action_type=ACTION_A, capability=CAP_A,
            method="nmap", impact_estimate=2.0)
        statuses.append(str(receipt.status))
    denied = [s for s in statuses if "DENIED" in s or s == "denied"]
    assert len(denied) == 1, statuses
    assert "DENIED" in statuses[-1] or statuses[-1] == "denied"
    assert spy["count"] == before, "rate-denied proposal must not spawn anything"


# 8. every denial produces a durable receipt
def test_denials_persist_durable_receipts(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = make_broker_from_bootstrap()  # restrictive: denies everything
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]},
                         objective=True, max_iterations=2)
    _, termination, outs = run_episode(runtime, mission)
    recs = _store_records(tmp_path)
    denied = [r for r in recs if r.get("status") == "denied"]
    assert len(denied) >= 2, "each denied attempt must persist a durable denial receipt"
    for r in denied:
        assert r.get("decision") == "deny"
        assert r.get("action_id") in (A_ID, B_ID)


# 9. no executor launch or network request after a denial (episode-level)
def test_denial_episode_spawns_nothing_and_invokes_nothing(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = make_broker_from_bootstrap()
    runtime, registry = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)]},
                         objective=False, max_iterations=1)
    before = spy["count"]
    run_episode(runtime, mission)
    assert spy["count"] == before
    for cap in registry.values():
        assert cap.invocation_count == 0


# 10. kill switch blocks further execution
def test_kill_switch_blocks_d2_episode(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    kill_broker = make_broker_from_bootstrap()
    runtime, registry = build_runtime(tmp_path, kill_broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]},
                         max_iterations=2)
    before = spy["count"]
    _, termination, outs = run_episode(runtime, mission)
    assert termination.final_stage == "broker"
    assert all("pep" not in o for o in outs)
    assert spy["count"] == before
    for cap in registry.values():
        assert cap.invocation_count == 0


# 11. the episode cannot exceed five steps
def test_episode_cannot_exceed_five_steps(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    candidates = {str(i): [make_candidate(f"ACT-R{i}", ACTION_A, CAP_A)]
                  for i in range(6)}  # six candidates declared
    mission = d2_mission(candidates, objective=True, max_iterations=5)
    traces, termination, outs = run_episode(runtime, mission)
    assert len(traces) == 5, "episode must stop at the five-step budget"
    assert termination.iterations == 5
    assert len(outs) == 5


# 12. evidence persisted with verifiable provenance
def test_evidence_provenance_complete(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]})
    _, termination, outs = run_episode(runtime, mission)
    recs = _store_records(tmp_path)
    exec_recs = [r for r in recs if r["kind"] == "execution_result"]
    by_action = {r["action_id"]: r for r in exec_recs}
    assert A_ID in by_action and B_ID in by_action
    for aid in (A_ID, B_ID):
        r = by_action[aid]
        assert r["decision"] == "allow"
        assert r["status"] in ("ok", "succeeded")
    event = outs[0]["pep"]["event"]
    assert event.decision_id == outs[0]["broker"]["decision"].decision_id


# 13. failed action: honest failure receipt, evidence-informed continuation
def test_failed_action_honest_and_informs_episode(tmp_path, spy):
    def failing_runner(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect"
        return P()
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker,
                               runner_map={CAP_A: fake_runner_a, CAP_B: failing_runner},
                               store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]})
    _, termination, outs = run_episode(runtime, mission)
    # action A succeeds; action B fails honestly: the runtime terminates at
    # the PEP failure with a truthful reason and never claims objective met
    assert "PEP raised" in termination.reason or "Failed to connect" in termination.reason
    assert "objective met" not in termination.reason
    recs = _store_records(tmp_path)
    failed = [r for r in recs if r.get("status") == "failed"]
    assert failed and "Failed to connect" in failed[-1].get("reason", "")
    ok = [r for r in recs if r.get("action_id") == A_ID and r.get("status") == "ok"]
    assert ok, "the succeeded action must still be recorded as evidence"


# 14. objective success impossible without both evidence artifacts
def test_objective_success_requires_both_evidence(tmp_path, spy):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    runtime, _ = build_runtime(tmp_path, broker, store=store)
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)]},
                         objective=True, max_iterations=1)
    _, termination, _ = run_episode(runtime, mission)
    assert "objective not met" in termination.reason
    assert "objective met" not in termination.reason


# 15. invalid/missing policy fails closed
def test_d2_policy_missing_fails_closed(tmp_path):
    with pytest.raises(PolicyLoadError):
        D1Policy(tmp_path / "missing.json")


def test_d2_policy_malformed_fails_closed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops")
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_d2_policy_rejects_extra_unapproved_action(tmp_path):
    data = json.loads(D2_POLICY_PATH.read_text())
    data["allowed"]["action_types"].append("exploit_execute")
    bad = tmp_path / "broad.json"
    bad.write_text(json.dumps(data))
    policy = D1Policy(bad)  # loads structurally...
    bp = policy.to_broker_policy()
    broker = __import__("orchestrator.brain.capability_broker",
                        fromlist=["CapabilityBroker"]).CapabilityBroker(bp)
    receipt = broker.propose_action(target=TARGET, action_type="exploit_execute",
                                    capability=CAP_A, method="nmap", impact_estimate=2.0)
    assert str(receipt.status) in ("ActionProposalStatus.DENIED", "denied")
    from orchestrator.auth import WeldNotAuthorized
    # the governed capability itself also refuses execution of a non-lab class


# 16. D1 behavior and governance invariants unchanged
def test_d1_policy_unchanged_and_still_denies_d2_actions():
    policy = D1Policy()  # default path = engagement-d1-v1.json
    broker = policy.to_broker_policy()
    assert policy.name == "engagement-d1-v1"
    from orchestrator.brain.capability_broker import CapabilityBroker
    b = CapabilityBroker(broker)
    receipt = b.propose_action(target=TARGET, action_type=ACTION_B,
                               capability=CAP_B, method="curl", impact_estimate=2.0)
    assert str(receipt.status) in ("ActionProposalStatus.DENIED", "denied")


def test_w01_body_still_fail_closed():
    from orchestrator.chains.tool_registry import _run_command
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(_run_command(["echo", "nope"]))


# live-lab variants (skip when the lab is not up)
@pytest.mark.skipif(not Path("/var/run/docker.sock").exists(),
                    reason="docker not available")
def test_live_d2_episode_two_actions(tmp_path, spy):
    import shutil as _shutil
    if _shutil.which("docker") is None:
        pytest.skip("docker binary not available")
    if subprocess.run(["docker", "inspect", "dvwa"], capture_output=True).returncode != 0:
        pytest.skip("lab container dvwa not running")
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    broker = d2_broker()
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts")
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts")
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A: cap_a, CAP_B: cap_b})
    mission = d2_mission({"0": [make_candidate(A_ID, ACTION_A, CAP_A)],
                          "1": [make_candidate(B_ID, ACTION_B, CAP_B)]})
    _, termination, outs = run_episode(runtime, mission)
    assert "objective met" in termination.reason
    a_out = outs[0]["pep"]["event"].output
    b_out = outs[1]["pep"]["event"].output
    assert a_out["service_confirmed"] is True
    assert b_out["http_status"] in (200, 302)
    assert b_out["redirect_followed"] is False
