"""test_m2_d1_governed_action.py — M2/D1 acceptance tests (2026-10-04).

Covers the ten required D1 test groups:
  1  positive authorization        6  restrictive control (bootstrap-v0)
  2  wrong target                  7  kill switch (decision-source swap)
  3  wrong capability              8  no direct bypass (CONV-3 gating)
  4  wrong action                  9  receipt integrity (decision linkage +
  5  malformed/absent policy          artifact digest)
                                  10  legacy welds remain fail-closed

Hermetic by default: the probe's subprocess runner and docker inspector are
injected. One live test (group 1's real-path variant) runs the actual probe
against the local lab and skips when the lab is not present. Denial paths are
proven process-free with a subprocess spy, not just response-code assertions.
"""
import asyncio
import dataclasses
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.brain.capability_broker import CapabilityBroker
from orchestrator.exec.capabilities.d1_lab_probe import (
    D1LabProbeCapability,
    D1LabProbeError,
)
from orchestrator.exec.safe_capability import CapabilityNotGatedError
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D1_POLICY_PATH,
    D1Policy,
    PolicyLoadError,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext

MISSION_ID = "d1-governed-action"
ACTION_TYPE = "recon_service_probe"
CAPABILITY = "exec.d1_lab_probe"
TARGET = "dvwa"

FAKE_NMAP_STDOUT = (
    "Starting Nmap 7.99 ( https://nmap.org )\n"
    "Nmap scan report for dvwa (172.19.0.4)\n"
    "Host is up (0.00030s latency).\n\n"
    "PORT   STATE SERVICE\n"
    "80/tcp open  http\n\n"
    "Nmap done: 1 IP address (1 host up) scanned in 0.05 seconds\n"
)


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


def fake_runner(argv, timeout):
    class Proc:
        returncode = 0
        stdout = FAKE_NMAP_STDOUT
        stderr = ""
    return Proc()


@pytest.fixture
def tmp_transcript(tmp_path):
    transcript = tmp_path / "transcript"
    (transcript / "artifacts").mkdir(parents=True)
    return transcript


def make_candidate(**overrides):
    cand = {
        "action_id": "ACT-D1-TEST-0001",
        "action_type": ACTION_TYPE,
        "target": TARGET,
        "capability": CAPABILITY,
        "method": "nmap",
        "impact_estimate": 2.0,
        "args": {"probe": "nmap_service", "bounded": True},
        "rationale": "D1 bounded service probe of the declared lab identity",
    }
    cand.update(overrides)
    return cand


def make_mission(scope, candidates):
    return MissionContext(
        mission_id=MISSION_ID,
        name="D1 Governed Action",
        objectives=["one governed probe"],
        constraints={
            "halt": {"max_iterations": 1, "action_cap": 1, "require_scope": True},
            "candidates": {"0": candidates},
            "default_target": TARGET,
        },
        scope=scope,
    )


def make_d1_scope():
    return ScopeV0(
        mission_id=MISSION_ID,
        targets=(TARGET,),
        allowed_action_types=(ACTION_TYPE,),
        allowed_capabilities=(CAPABILITY,),
        max_impact=2.0,
    )


def build_runtime(tmp_transcript, broker, store=None):
    capability = D1LabProbeCapability(
        broker=broker, artifacts_dir=tmp_transcript / "artifacts",
        runner=fake_runner, inspector=fake_inspector,
    )
    organs = OrganBundle(evidence_store=store)
    runtime = RaphaelRuntime(broker=broker, capability=capability, organs=organs)
    return runtime, capability


def run_episode(runtime, mission):
    episode_outputs: list = []
    traces, termination = runtime.run_episode(mission, episode_outputs=episode_outputs)
    return traces, termination, (episode_outputs[0] if episode_outputs else {})


@pytest.fixture
def spy(monkeypatch):
    """Instrument subprocess.run to count real spawns in this process."""
    state = {"count": 0}
    orig = subprocess.run

    def counting(*a, **kw):
        state["count"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(subprocess, "run", counting)
    yield state


# ── 1. positive authorization ────────────────────────────────────────────

def test_positive_d1_request_is_authorized_and_executed(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    traces, termination, out = run_episode(runtime, make_mission(make_d1_scope(), [make_candidate()]))
    assert termination.final_stage == "replan", termination.reason
    decision = out["broker"]["decision"]
    receipt = out["broker"]["receipt"]
    event = out["pep"]["event"]
    assert decision.decision == "allow"
    assert event.decision_id == decision.decision_id
    assert event.target == TARGET
    assert event.output["service_confirmed"] is True
    assert event.output["returncode"] == 0
    assert str(receipt.status) in ("ActionProposalStatus.SUCCEEDED", "succeeded")
    # artifact digest matches the stored bytes
    artifact_file = tmp_transcript / event.output["artifact_relpath"]
    assert artifact_file.is_file()
    assert hashlib.sha256(artifact_file.read_bytes()).hexdigest() == event.output["artifact_sha256"]


@pytest.mark.skipif(
    not Path("/var/run/docker.sock").exists(),
    reason="docker not available in this environment",
)
def test_d1_live_probe_against_local_dvwa(tmp_transcript):
    """Real-path variant: the actual nmap probe runs against the local lab."""
    import shutil as _shutil
    if _shutil.which("docker") is None:
        pytest.skip("docker binary not available")
    probe = subprocess.run(["docker", "inspect", "dvwa"], capture_output=True)
    if probe.returncode != 0:
        pytest.skip("lab container dvwa not running")
    broker = make_broker_from_policy()
    capability = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_transcript / "artifacts")
    capability.record_authorization(TARGET)
    result = capability.inspect(TARGET)
    assert result.output["service_confirmed"] is True
    assert "80/tcp open" in result.output["stdout"]


# ── 2. wrong target ──────────────────────────────────────────────────────

def test_wrong_target_is_denied_and_never_executes(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    before = spy["count"]
    _, termination, out = run_episode(
        runtime, make_mission(make_d1_scope(), [make_candidate(target="example.invalid")]))
    assert termination.final_stage == "broker"
    assert "pep" not in out
    assert spy["count"] == before, "a denied action spawned a process"
    assert capability.invocation_count == 0


# ── 3. wrong capability ──────────────────────────────────────────────────

def test_wrong_capability_is_denied(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    _, termination, out = run_episode(
        runtime,
        make_mission(make_d1_scope(),
                     [make_candidate(capability="chains.tool_registry")]))
    assert termination.final_stage == "broker"
    assert "pep" not in out
    assert capability.invocation_count == 0


# ── 4. wrong action ──────────────────────────────────────────────────────

def test_wrong_action_is_denied(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    _, termination, out = run_episode(
        runtime,
        make_mission(make_d1_scope(),
                     [make_candidate(action_type="tool_execute")]))
    assert termination.final_stage == "broker"
    assert "pep" not in out
    # "tool_execute" is additionally explicitly prohibited by the D1 policy
    assert capability.invocation_count == 0


# ── 5. malformed / absent policy fails closed ────────────────────────────

def test_policy_missing_file_fails_closed(tmp_path):
    with pytest.raises(PolicyLoadError):
        D1Policy(tmp_path / "does-not-exist.json")


def test_policy_malformed_json_fails_closed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_policy_unsupported_schema_version_fails_closed(tmp_path):
    data = json.loads(D1_POLICY_PATH.read_text())
    data["schema_version"] = 999
    bad = tmp_path / "stale.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_policy_empty_allow_list_fails_closed(tmp_path):
    path = D1_POLICY_PATH
    data = json.loads(path.read_text())
    data["allowed"]["targets"] = []
    bad = tmp_path / "empty.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_policy_missing_lab_contract_fails_closed(tmp_path):
    path = D1_POLICY_PATH
    data = json.loads(path.read_text())
    del data["scope"]["lab"]["target_image_prefix"]
    bad = tmp_path / "nolab.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_policy_unsupported_mode_fails_closed(tmp_path):
    path = D1_POLICY_PATH
    data = json.loads(path.read_text())
    data["mode"] = "OPEN"
    bad = tmp_path / "open.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


def test_policy_relaxed_fail_closed_flag_fails_closed(tmp_path):
    path = D1_POLICY_PATH
    data = json.loads(path.read_text())
    data["fail_closed"]["on_missing_file"] = False
    bad = tmp_path / "relaxed.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(bad)


# ── 6. restrictive control (bootstrap-v0) ────────────────────────────────

def test_restrictive_policy_denies_the_d1_request(tmp_transcript, spy):
    broker = make_broker_from_bootstrap()
    receipt = broker.propose_action(
        target=TARGET, action_type=ACTION_TYPE, capability=CAPABILITY,
        method="nmap", impact_estimate=2.0,
    )
    assert str(receipt.status) in ("ActionProposalStatus.DENIED", "denied")


def test_restrictive_policy_denies_via_full_episode(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_bootstrap()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    _, termination, out = run_episode(runtime, make_mission(make_d1_scope(), [make_candidate()]))
    assert termination.final_stage == "broker"
    assert "pep" not in out
    assert capability.invocation_count == 0


# ── 7. kill switch (decision-source swap) ────────────────────────────────

def test_kill_switch_swap_denies_with_no_process(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    # authorized first under the D1 policy
    d1_broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, d1_broker, store)
    _, termination, out = run_episode(runtime, make_mission(make_d1_scope(), [make_candidate()]))
    assert out["broker"]["decision"].decision == "allow"
    # kill switch: swap the decision source to bootstrap-v0 (one-file revert)
    kill_broker = make_broker_from_bootstrap()
    kill_runtime, kill_capability = build_runtime(tmp_transcript, kill_broker, store)
    before = spy["count"]
    _, termination, out = run_episode(kill_runtime, make_mission(make_d1_scope(), [make_candidate()]))
    assert termination.final_stage == "broker"
    assert "pep" not in out
    assert spy["count"] == before, "kill-switch denial spawned a process"
    assert kill_capability.invocation_count == 0


# ── 8. no direct bypass ──────────────────────────────────────────────────

def test_capability_without_broker_binding_is_gated(tmp_transcript):
    capability = D1LabProbeCapability(artifacts_dir=tmp_transcript / "artifacts")
    with pytest.raises(CapabilityNotGatedError):
        capability.inspect(TARGET)


def test_capability_without_recorded_authorization_is_gated(tmp_transcript):
    broker = make_broker_from_policy()
    capability = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_transcript / "artifacts",
                                      runner=fake_runner, inspector=fake_inspector)
    with pytest.raises(CapabilityNotGatedError):
        capability.inspect(TARGET)


def test_capability_refuses_non_lab_target_even_when_authorized(tmp_transcript):
    broker = make_broker_from_policy()
    capability = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_transcript / "artifacts",
                                      runner=fake_runner, inspector=fake_inspector)
    # Even if a foreign target were (wrongly) recorded as authorized, the
    # capability's own identity check must refuse it.
    capability.record_authorization("example.invalid")
    with pytest.raises(D1LabProbeError):
        capability.inspect("example.invalid")


def test_pep_stage_refuses_denied_receipt(tmp_transcript, spy):
    """A DENIED receipt cannot be started through the PEP (defense in depth)."""
    broker = make_broker_from_bootstrap()
    receipt = broker.propose_action(
        target=TARGET, action_type=ACTION_TYPE, capability=CAPABILITY,
        method="nmap", impact_estimate=2.0,
    )
    assert receipt.status.name == "DENIED"
    before = spy["count"]
    # The lifecycle state machine refuses the transition. RSI-1 remediation:
    # that refusal is reported as None rather than surfacing as an incidental
    # AttributeError from dereferencing the refused receipt; the PEP stage
    # treats None as fail-closed. Either way no process is spawned.
    started = broker.start_execution(receipt)
    assert started is None
    assert receipt.status.name == "DENIED", "a refused start must not mutate state"
    assert spy["count"] == before
    assert broker.get_receipt(receipt.action_id).status.name == "DENIED"


# ── 9. receipt integrity ─────────────────────────────────────────────────

def test_receipt_integrity_decision_and_artifact_binding(tmp_transcript, spy):
    store = EvidenceStore(tmp_transcript / "evidence_store.jsonl")
    broker = make_broker_from_policy()
    runtime, capability = build_runtime(tmp_transcript, broker, store)
    _, termination, out = run_episode(runtime, make_mission(make_d1_scope(), [make_candidate()]))
    decision = out["broker"]["decision"]
    broker_receipt = out["broker"]["receipt"]
    event = out["pep"]["event"]
    evidence_receipt = out["receipt"]["receipt"]
    assert evidence_receipt.decision_id == decision.decision_id
    assert evidence_receipt.broker_receipt_id == broker_receipt.action_id
    assert evidence_receipt.action_type == ACTION_TYPE
    assert evidence_receipt.target == TARGET
    assert evidence_receipt.capability == CAPABILITY
    assert evidence_receipt.scope_hash, "receipt must record the scope hash"
    relpath = event.output["artifact_relpath"]
    assert evidence_receipt.artifact_refs == (relpath,)
    # persisted evidence: the execution_result plus its linked artifact record,
    # both carrying the authorizing decision_id (M3/D2 remediation).
    records = [json.loads(line)["record"]
               for line in (tmp_transcript / "evidence_store.jsonl").read_text().splitlines()]
    by_kind = {}
    for rec in records:
        by_kind.setdefault(rec["kind"], []).append(rec)
    exec_rec = by_kind["execution_result"][0]
    assert exec_rec["payload"]["decision_id"] == decision.decision_id
    assert exec_rec["payload"]["artifacts"] == [relpath]
    artifact_rec = by_kind["artifact"][0]
    assert artifact_rec["payload"]["relpath"] == relpath
    assert artifact_rec["payload"]["execution_ref"] == exec_rec["identity"]
    assert artifact_rec["parents"] == [exec_rec["identity"]]


# ── 10. legacy welds remain fail-closed ──────────────────────────────────

def test_w01_tool_registry_body_still_fail_closed():
    from orchestrator.auth import WeldNotAuthorized
    from orchestrator.chains.tool_registry import _run_command
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(_run_command(["echo", "nope"]))


def test_d1_broker_denies_unimplemented_welded_capabilities(tmp_transcript):
    broker = make_broker_from_policy()
    for capability, action_type, method in (
        ("c2.beacon", "c2_listen", "start"),
        ("sandbox.run_code", "exploit_execute", "run_code"),
        ("chains.tool_registry", "tool_execute", "_run_command"),
    ):
        receipt = broker.propose_action(
            target=TARGET, action_type=action_type, capability=capability,
            method=method, impact_estimate=9.0,
        )
        assert str(receipt.status) in ("ActionProposalStatus.DENIED", "denied"), (
            f"D1 policy must deny unimplemented capability {capability}"
        )


def test_d1_policy_is_exact_not_open():
    """The active D1 artifact must be the bounded one, not the open policy."""
    policy = D1Policy()
    assert policy.name == "engagement-d1-v1"
    bp = policy.to_broker_policy()
    assert bp.allowed_targets == ("dvwa",)
    assert bp.allowed_action_types == ("recon_service_probe",)
    assert bp.allowed_capabilities == ("exec.d1_lab_probe",)
    assert "*" not in bp.allowed_targets
    assert "*" not in bp.allowed_action_types
    assert "*" not in bp.allowed_capabilities
