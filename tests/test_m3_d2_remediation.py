"""test_m3_d2_remediation.py — D2 audit remediation regression tests (2026-10-05).

Remediates the two blockers of the D2 Independent Verification Audit:

A. Objective completion is evidence-verifiable. Every required action must
   present the complete chain
       current mission -> required action -> authorization decision
       -> execution result -> persisted artifact -> verified bytes
   Fabricated, cross-episode, provenance-free, artifact-less, dangling-digest,
   wrong-decision and contradictory records must all be rejected.

B. The five-step maximum is enforced at the D2 runtime boundary by the
   validated policy (``max_episode_steps``), not by a launcher argument. A
   caller cannot raise it, and a sixth governed action never reaches the PEP.

Hermetic: every store and artifact lives under tmp_path; injected runners and
inspectors mean no docker and no subprocess. Historical evidence is untouched.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.evidence_v1 import EvidenceRecord
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D2_POLICY_PATH,
    D1Policy,
    PolicyLoadError,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
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
    images = {"dvwa": "vulnerables/web-dvwa:stable", "kali-tools": "raphael/kali-tools:latest"}
    if container not in images:
        raise AssertionError(f"unexpected container {container}")
    return {"State": {"Running": True},
            "Config": {"Image": images[container]},
            "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}


def fake_runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def fake_runner_b(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_CURL, ""
    return P()


def candidate(action_id, action_type, capability):
    return {"action_id": action_id, "action_type": action_type, "target": TARGET,
            "capability": capability,
            "method": "nmap" if capability == CAP_A else "curl",
            "impact_estimate": 2.0, "args": {"bounded": True},
            "rationale": "D2 bounded action"}


def d2_scope():
    return ScopeV0(mission_id=MISSION_ID, targets=(TARGET,),
                   allowed_action_types=(ACTION_A, ACTION_B),
                   allowed_capabilities=(CAP_A, CAP_B), max_impact=2.0)


def d2_mission(candidates_by_iter, required=None, max_iterations=5):
    constraints = {"halt": {"max_iterations": max_iterations, "action_cap": 1,
                            "require_scope": True},
                   "candidates": candidates_by_iter, "default_target": TARGET,
                   "objective": {"requires_evidence": list(
                       required if required is not None else [A_ID, B_ID])}}
    return MissionContext(mission_id=MISSION_ID, name="D2 bounded episode",
                          objectives=["governed two-probe reconnaissance"],
                          constraints=constraints, scope=d2_scope())


def build_runtime(tmp_path, broker, store, runner_map=None):
    cap_a = D1LabProbeCapability(
        broker=broker, artifacts_dir=tmp_path / "artifacts",
        runner=(runner_map or {}).get(CAP_A, fake_runner_a), inspector=fake_inspector)
    cap_b = LabHttpProbeCapability(
        broker=broker, artifacts_dir=tmp_path / "artifacts",
        runner=(runner_map or {}).get(CAP_B, fake_runner_b), inspector=fake_inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A: cap_a, CAP_B: cap_b})
    return runtime, {CAP_A: cap_a, CAP_B: cap_b}


def run(runtime, mission):
    outs: list = []
    traces, termination = runtime.run_episode(mission, episode_outputs=outs)
    return traces, termination, outs


def both_candidates():
    return {"0": [candidate(A_ID, ACTION_A, CAP_A)],
            "1": [candidate(B_ID, ACTION_B, CAP_B)]}


def new_store(tmp_path):
    return EvidenceStore(tmp_path / "evidence_store.jsonl")


@pytest.fixture
def spy(monkeypatch):
    state = {"count": 0}
    orig = subprocess.run

    def counting(*a, **kw):
        state["count"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(subprocess, "run", counting)
    yield state


def evaluate(tmp_path, broker, store, candidates, required):
    """Run one episode and return its terminal state (no assertions)."""
    runtime, _ = build_runtime(tmp_path, broker, store)
    _, termination, outs = run(runtime, d2_mission(candidates, required=required))
    return termination, outs


def replan_verdicts(outs):
    """The objective evaluation recorded by each reached replan stage."""
    return [o["replan"] for o in outs
            if isinstance(o.get("replan"), dict) and o["replan"].get("objective_evaluated")]


def assert_objective_rejected(outs):
    """No reached objective evaluation ever reported completion."""
    verdicts = replan_verdicts(outs)
    assert verdicts, "the episode never reached objective evaluation"
    assert not any(v.get("objective_met") for v in verdicts), verdicts
    return verdicts[-1]["reason"]


# ── Remediation A: objective evidence integrity ──────────────────────────────

def test_positive_control_genuine_episode_completes(tmp_path, spy):
    """EXP9: the real two-action episode still completes under the contract."""
    store = new_store(tmp_path)
    termination, outs = evaluate(tmp_path, make_broker_from_policy(D2_POLICY_PATH),
                                 store, both_candidates(), [A_ID, B_ID])
    assert "objective met" in termination.reason, termination.reason
    assert len(outs) == 2
    for out in outs:
        relpath = out["pep"]["event"].output["artifact_relpath"]
        measured = hashlib.sha256(
            (tmp_path / "artifacts" / Path(relpath).name).read_bytes()).hexdigest()
        assert measured == out["pep"]["event"].output["artifact_sha256"]


def test_exp1_cross_episode_injection_is_rejected(tmp_path, spy):
    """EXP1: another mission's successful record cannot complete this objective."""
    store = new_store(tmp_path)
    store.append(EvidenceRecord.execution_result(
        mission_id="totally-unrelated-run", producer="attacker", action_id=A_ID,
        status="ok", decision="allow", decision_id="DEC-FORGED"))
    store.append(EvidenceRecord.execution_result(
        mission_id="totally-unrelated-run", producer="attacker", action_id=B_ID,
        status="ok", decision="allow", decision_id="DEC-FORGED"))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store,
                       {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    assert "objective not met" in assert_objective_rejected(outs)


def test_exp2_missing_required_action_is_rejected(tmp_path, spy):
    """EXP2: one missing required action means the objective is not met."""
    store = new_store(tmp_path)
    _, outs = evaluate(tmp_path, make_broker_from_policy(D2_POLICY_PATH), store,
                       {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    reason = assert_objective_rejected(outs)
    assert B_ID in reason, reason


def test_exp3_success_without_artifact_is_rejected(tmp_path, spy):
    """EXP3: a succeeded record with no artifact evidence cannot complete it."""
    store = new_store(tmp_path)
    store.append(EvidenceRecord.execution_result(
        mission_id=MISSION_ID, producer="runtime.receipt", action_id=A_ID,
        status="ok", decision="allow", decision_id="DEC-A"))
    store.append(EvidenceRecord.execution_result(
        mission_id=MISSION_ID, producer="runtime.receipt", action_id=B_ID,
        status="ok", decision="allow", decision_id="DEC-B"))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    # No capability runs (the episode is short), so nothing else is persisted.
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    assert "objective not met" in assert_objective_rejected(outs)


def test_exp4_dangling_or_forged_digest_is_rejected(tmp_path, spy):
    """EXP4: an artifact ref to a nonexistent file / wrong digest cannot pass."""
    store = new_store(tmp_path)
    forged_relpath = "artifacts/http_probe_forged.txt"
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    # The claimed bytes exist but the recorded digest is a well-formed forgery.
    (tmp_path / "artifacts" / Path(forged_relpath).name).write_bytes(b"genuine bytes")
    for action_id, decision_id in ((A_ID, "DEC-A"), (B_ID, "DEC-B")):
        exec_rec = EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow", decision_id=decision_id,
            artifacts=(forged_relpath,))
        store.append(exec_rec)
        store.append(EvidenceRecord.artifact(
            mission_id=MISSION_ID, producer="runtime.receipt", relpath=forged_relpath,
            size_bytes=len(b"genuine bytes"), sha256="0" * 64,
            execution_ref=exec_rec.identity, parents=(exec_rec.identity,)))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    reason = assert_objective_rejected(outs)
    # RSI-1 Fix A: this record is now rejected one gate EARLIER than the digest
    # comparison — its forged decision id does not resolve against the
    # authoritative broker receipt state, so the attempt never reaches artifact
    # verification. That is strictly stronger than a digest mismatch, so assert
    # the provenance gate fired and that the weaker digest reason did not.
    # Digest rejection itself is exercised with a GENUINE decision id in
    # tests/test_rsi1_governance_remediation.py::test_a10a_digest_invalid_is_rejected.
    assert "digest mismatch" not in reason
    assert "decision-linked record" in reason


def test_exp4b_dangling_artifact_reference_is_rejected(tmp_path, spy):
    """EXP4b: a ref to a file that was never stored cannot pass."""
    store = new_store(tmp_path)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    missing = "artifacts/never_written.txt"
    for action_id, decision_id in ((A_ID, "DEC-A"), (B_ID, "DEC-B")):
        exec_rec = EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow", decision_id=decision_id, artifacts=(missing,))
        store.append(exec_rec)
        store.append(EvidenceRecord.artifact(
            mission_id=MISSION_ID, producer="runtime.receipt", relpath=missing,
            size_bytes=3, sha256=hashlib.sha256(b"abc").hexdigest(),
            execution_ref=exec_rec.identity, parents=(exec_rec.identity,)))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    assert "objective not met" in assert_objective_rejected(outs)


def test_provenance_free_result_is_rejected(tmp_path, spy):
    """A success-shaped record with no decision_id linkage cannot complete it."""
    store = new_store(tmp_path)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    for action_id in (A_ID, B_ID):
        exec_rec = EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow")
        store.append(exec_rec)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    reason = assert_objective_rejected(outs)
    assert "decision_id" in reason


def test_wrong_decision_cannot_satisfy_the_objective(tmp_path, spy):
    """A denied or authorization-only record never satisfies the objective."""
    store = new_store(tmp_path)
    for action_id in (A_ID, B_ID):
        store.append(EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="denied", decision="deny"))
        store.append(EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow"))  # authorization-only, no linkage
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    assert "objective not met" in assert_objective_rejected(outs)


def test_contradictory_records_for_one_attempt_are_rejected(tmp_path, spy):
    """Conflicting outcomes for the SAME attempt cannot create objective success."""
    store = new_store(tmp_path)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    relpath = "artifacts/shared.txt"
    (tmp_path / "artifacts" / Path(relpath).name).write_bytes(b"body")
    digest = hashlib.sha256(b"body").hexdigest()
    for action_id in (A_ID, B_ID):
        ok_rec = EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow", decision_id="DEC-SHARED",
            artifacts=(relpath,))
        store.append(ok_rec)
        store.append(EvidenceRecord.artifact(
            mission_id=MISSION_ID, producer="runtime.receipt", relpath=relpath,
            size_bytes=4, sha256=digest, execution_ref=ok_rec.identity,
            parents=(ok_rec.identity,)))
        # Same action_id + same decision_id, opposite outcome.
        store.append(EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="failed", decision="allow", decision_id="DEC-SHARED"))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    reason = assert_objective_rejected(outs)
    assert "contradictory" in reason


def test_artifact_from_another_attempt_is_rejected(tmp_path, spy):
    """EXP8: a valid artifact bound to a DIFFERENT execution cannot be borrowed."""
    store = new_store(tmp_path)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    relpath = "artifacts/other_attempt.txt"
    (tmp_path / "artifacts" / Path(relpath).name).write_bytes(b"body")
    digest = hashlib.sha256(b"body").hexdigest()
    other_exec = EvidenceRecord.execution_result(
        mission_id=MISSION_ID, producer="runtime.receipt", action_id="ACT-UNRELATED",
        status="ok", decision="allow", decision_id="DEC-OTHER")
    store.append(other_exec)
    store.append(EvidenceRecord.artifact(
        mission_id=MISSION_ID, producer="runtime.receipt", relpath=relpath,
        size_bytes=4, sha256=digest, execution_ref=other_exec.identity,
        parents=(other_exec.identity,)))
    # The required action borrows that artifact ref but has no linked artifact record.
    for action_id in (A_ID, B_ID):
        store.append(EvidenceRecord.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=action_id,
            status="ok", decision="allow", decision_id=f"DEC-{action_id}",
            artifacts=(relpath,)))
    broker = make_broker_from_policy(D2_POLICY_PATH)
    _, outs = evaluate(tmp_path, broker, store, {"0": [candidate(A_ID, ACTION_A, CAP_A)]}, [A_ID, B_ID])
    assert "objective not met" in assert_objective_rejected(outs)


def test_attempt_isolation_distinct_attempts_evaluated_separately(tmp_path, spy):
    """A denial for one attempt does not block a later genuine successful attempt."""
    store = new_store(tmp_path)
    termination, outs = evaluate(tmp_path, make_broker_from_policy(D2_POLICY_PATH),
                                 store, both_candidates(), [A_ID, B_ID])
    assert "objective met" in termination.reason
    denials = [r for r in store.records()
               if r.kind.value == "execution_result"
               and dict(r.payload).get("status") == "denied"]
    for denial in denials:
        assert dict(denial.payload).get("decision") == "deny"


def test_http_302_control_remains_valid_evidence(tmp_path, spy):
    """EXP10: a genuine unfollowed redirect is valid evidence when its chain verifies."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    termination, outs = evaluate(tmp_path, broker, store, both_candidates(), [A_ID, B_ID])
    assert "objective met" in termination.reason
    http_out = outs[1]
    event = http_out["pep"]["event"]
    assert event.output["http_status"] == 302
    assert event.output["redirect_followed"] is False
    assert event.output["redirect_url"] == "http://dvwa/login.php"


def test_http_transport_failure_is_not_valid_evidence(tmp_path, spy):
    """A transport failure (non-zero curl) proves nothing and cannot satisfy it."""
    def failing_runner(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect"
        return P()

    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker, store,
                                  runner_map={CAP_B: failing_runner})
    _, termination, _ = run(runtime, d2_mission(both_candidates()))
    assert "objective met" not in termination.reason
    assert caps[CAP_B].invocation_count == 1
    succeeded = [r for r in store.records()
                 if r.kind.value == "execution_result"
                 and dict(r.payload).get("action_id") == B_ID
                 and dict(r.payload).get("status") in ("ok", "succeeded")]
    assert not succeeded


def test_artifact_verification_refuses_path_escape(tmp_path):
    """An evidence ref escaping the artifact root is refused, not followed."""
    from orchestrator.exec.artifact_verify import (
        ArtifactVerificationError,
        verify_artifact,
    )
    root = tmp_path / "artifacts"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    with pytest.raises(ArtifactVerificationError):
        verify_artifact(root, "../outside.txt")
    with pytest.raises(ArtifactVerificationError):
        verify_artifact(root, str(outside))


def test_symlinked_artifact_is_refused(tmp_path):
    """A symlink escaping the artifact root is refused (containment, not syntax)."""
    from orchestrator.exec.artifact_verify import (
        ArtifactVerificationError,
        verify_artifact,
    )
    root = tmp_path / "artifacts"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    try:
        (root / "link.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(ArtifactVerificationError):
        verify_artifact(root, "link.txt")


def test_artifact_read_is_bounded(tmp_path):
    """An oversized artifact is refused rather than read into memory."""
    from orchestrator.exec.artifact_verify import (
        ArtifactVerificationError,
        verify_artifact,
    )
    root = tmp_path / "artifacts"
    root.mkdir(parents=True)
    (root / "big.bin").write_bytes(b"0" * 5000)
    with pytest.raises(ArtifactVerificationError):
        verify_artifact(root, "big.bin", max_bytes=100)


# ── Remediation B: authoritative five-step cap at the runtime boundary ───────

def test_d2_policy_declares_the_five_step_cap():
    policy = D1Policy(D2_POLICY_PATH)
    assert policy.max_episode_steps == 5
    assert policy.to_broker_policy().max_episode_steps == 5


def test_d1_policy_declares_no_episode_cap():
    from orchestrator.runtime.policy import D1_POLICY_PATH
    assert D1Policy(D1_POLICY_PATH).max_episode_steps is None


@pytest.mark.parametrize("bad", ["5", 5.0, True, 0, -1, 999, None if False else "x"])
def test_malformed_step_limit_fails_closed(tmp_path, bad):
    data = json.loads(D2_POLICY_PATH.read_text())
    data["max_episode_steps"] = bad
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        D1Policy(path)


def test_normal_episode_still_completes_under_the_cap(tmp_path, spy):
    """The approved two-action episode works with the policy cap active."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _ = build_runtime(tmp_path, broker, store)
    _, termination, outs = run(runtime, d2_mission(both_candidates()))
    assert "objective met" in termination.reason
    assert len(outs) == 2


def test_caller_cannot_raise_the_policy_cap(tmp_path, spy):
    """EXP5: max_iterations=7 cannot execute more than five governed steps."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    mission = d2_mission(candidates, required=["ACT-NEVER"], max_iterations=7)
    outs: list = []
    traces, termination = runtime.run_episode(mission, max_iterations=7,
                                              episode_outputs=outs)
    assert len(traces) == 5, "the policy cap, not the caller, bounds the episode"
    assert termination.iterations == 5
    assert caps[CAP_A].invocation_count <= 5


def test_sixth_action_never_reaches_the_pep(tmp_path, spy, monkeypatch):
    """Instrument the PEP boundary: no sixth governed action executes."""
    from orchestrator.runtime import stages as stages_mod

    pep_invocations: list = []
    original = stages_mod.stage_pep

    def counting_pep(ctx):
        pep_invocations.append(ctx["planner_request"]["request"].action_id)
        return original(ctx)

    monkeypatch.setattr(stages_mod, "stage_pep", counting_pep)
    monkeypatch.setitem(stages_mod.STAGE_HANDLERS, stages_mod.STAGE_PEP, counting_pep)

    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    runtime.run_episode(d2_mission(candidates, required=["ACT-NEVER"]), max_iterations=7)
    assert len(pep_invocations) == 5, pep_invocations
    assert caps[CAP_A].invocation_count == 5


def test_requested_and_effective_budget_are_reported(tmp_path, spy):
    """The terminal state distinguishes the caller's request from the D2 limit."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _ = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    _, termination, _ = run(runtime, d2_mission(candidates, required=["ACT-NEVER"], max_iterations=7))
    assert termination.requested_budget == 7
    assert termination.effective_budget == 5
    assert termination.policy_max_episode_steps == 5
    assert termination.budget_clamped is True
    assert "budget clamped" in termination.reason
    assert "requested 7" in termination.reason


def test_achieved_objective_is_not_downgraded_by_a_clamp(tmp_path, spy):
    """A clamp never turns a genuinely met objective into a reported failure."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _ = build_runtime(tmp_path, broker, store)
    mission = d2_mission(both_candidates())
    _, termination = runtime.run_episode(mission, max_iterations=7)
    assert "objective met" in termination.reason
    assert "budget clamped" in termination.reason
    assert termination.effective_budget == 5


def test_replanning_does_not_reset_the_budget(tmp_path, spy):
    """Repeated replan continuation consumes the one episode budget."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _ = build_runtime(tmp_path, broker, store)
    # Every iteration yields a fresh (unmet) objective -> always replans.
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    _, termination, outs = run(runtime, d2_mission(candidates, required=["ACT-NEVER"]))
    assert len(outs) == 5
    assert termination.iterations == 5


def test_denial_loop_cannot_create_unbounded_continuation(tmp_path, spy):
    """Repeated broker denials stay inside the cap."""
    store = new_store(tmp_path)
    broker = make_broker_from_bootstrap()  # denies everything
    runtime, caps = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    _, termination, outs = run(runtime, d2_mission(candidates, required=["ACT-NEVER"]))
    assert len(outs) <= 5
    assert all("pep" not in o for o in outs)
    for cap in caps.values():
        assert cap.invocation_count == 0


def test_failure_loop_cannot_create_unbounded_continuation(tmp_path, spy):
    """Repeated execution failures stay inside the cap."""
    def failing_runner(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect"
        return P()

    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker, store,
                                  runner_map={CAP_A: failing_runner, CAP_B: failing_runner})
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    _, termination, outs = run(runtime, d2_mission(candidates, required=["ACT-NEVER"]))
    assert len(outs) <= 5
    assert caps[CAP_A].invocation_count <= 5


def test_extra_candidates_cannot_bypass_the_cap(tmp_path, spy):
    """A long candidate tail still executes at most five governed steps."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A),
                           candidate(f"ACT-F{i}", ACTION_B, CAP_B)]
                  for i in range(9)}
    runtime.run_episode(d2_mission(candidates, required=["ACT-NEVER"]), max_iterations=50)
    assert caps[CAP_A].invocation_count + caps[CAP_B].invocation_count <= 5


@pytest.mark.parametrize("requested,expected_effective", [(-3, 1), (0, 1), ("nope", 1), (2, 2), (9, 5)])
def test_invalid_or_large_budgets_are_bounded_by_the_policy(tmp_path, spy,
                                                           requested, expected_effective):
    """Malformed input keeps safe behavior and may never weaken the policy cap."""
    store = new_store(tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _ = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(9)}
    _, termination = runtime.run_episode(d2_mission(candidates, required=["ACT-NEVER"]),
                                            max_iterations=requested)
    assert termination.effective_budget == expected_effective
    assert termination.iterations <= expected_effective


def test_kill_switch_broker_has_no_cap_and_keeps_its_budget(tmp_path, spy):
    """A policy without an episode cap does not weaken or invent one."""
    store = new_store(tmp_path)
    broker = make_broker_from_bootstrap()
    runtime, _ = build_runtime(tmp_path, broker, store)
    candidates = {str(i): [candidate(f"ACT-R{i}", ACTION_A, CAP_A)] for i in range(3)}
    _, termination, _ = run(runtime, d2_mission(candidates, required=["ACT-NEVER"], max_iterations=3))
    assert termination.policy_max_episode_steps == 0
    assert termination.effective_budget == 3
    assert termination.budget_clamped is False