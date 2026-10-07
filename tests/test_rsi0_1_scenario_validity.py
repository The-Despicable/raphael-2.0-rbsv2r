"""test_rsi0_1_scenario_validity.py — RSI-0.1 regression tests (2026-10-07).

Verifies the corrected S3 rate-limit scenario, the C2 retry semantics (what the
runtime supports and what it does not), and the preservation of all governance
invariants. Root cause of RSI-0's S3 zero-denial result: objective completion
terminates the episode at stage_replan before the third candidate step is ever
proposed — the limiter was never reached (source: stages.py stage_replan +
loop.py termination; reproduced by test_s3_root_cause_reproduction).
"""
import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D2_POLICY_PATH,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
from orchestrator.rsi import scenario_validity as SV
from orchestrator.rsi.exploration_policy import CONSTRAINT_ECHO

D1_POLICY_PATH = D2_POLICY_PATH.parent / "engagement-d1-v1.json"

MISSION_ID = SV.MISSION_ID
A_ID = SV.A_ID
B_ID = SV.B_ID


@pytest.fixture
def spy(monkeypatch):
    state = {"count": 0}
    orig = subprocess.run

    def counting(*a, **kw):
        state["count"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(subprocess, "run", counting)
    yield state


# 1. the actual cause of RSI-0's S3 zero-denial result
def test_s3_root_cause_objective_terminates_before_third_proposal(tmp_path):
    """With a 2/min policy and candidates [A, B, A-retry], the objective is
    met after two steps and the loop terminates — the third candidate step is
    never proposed, so the limiter is never reached. This REPRODUCES the
    RSI-0 zero-denial observation and proves it is scenario design, not a
    limiter defect."""
    workdir = tmp_path / "s3"
    broker = make_broker_from_policy(SV.scenario_policy_2pm(workdir))
    runtime, caps = SV.build_runtime(broker, EvidenceStore(workdir / "store.jsonl"),
                                     workdir / "artifacts")
    mission = SV.d2_mission({"0": [SV.cand("0", "A")],
                             "1": [SV.cand("1", "B")],
                             "2": [SV.cand("2", "A")]}, max_iterations=5)
    outs = []
    _, termination = runtime.run_episode(mission, episode_outputs=outs)
    assert "objective met" in termination.reason
    executed = sum(1 for o in outs if "pep" in o)
    assert executed == 2, "objective completion must terminate at two steps"
    assert all("pep" not in o for o in outs[2:]) or len(outs) == 2


# 2+3+4. the third proposal reaches the rate limiter and is denied with a
# durable receipt; zero PEP/capability invocations for the denied attempt.
def test_third_proposal_rate_denied_at_broker_with_durable_receipt(tmp_path, spy):
    workdir = tmp_path / "s3"
    broker = make_broker_from_policy(SV.scenario_policy_2pm(workdir))
    recorder = SV.ProposalRecorder(broker)
    store = EvidenceStore(workdir / "store.jsonl")
    runtime, caps = SV.build_runtime(broker, store, workdir / "artifacts")

    m1 = SV.d2_mission({"0": [SV.cand("0", "A")], "1": [SV.cand("1", "B")]},
                       max_iterations=5)
    outs1 = []
    before = spy["count"]
    runtime.run_episode(m1, episode_outputs=outs1)
    # hermetic runners spawn no subprocesses; the governed executions are
    # proven by the proposal sequence and PEP counts, not by spawn counts

    m2 = SV.d2_mission({"0": [SV.cand("2", "A")]}, max_iterations=1)
    outs2 = []
    runtime.run_episode(m2, episode_outputs=outs2)
    assert spy["count"] == before, "the denied third attempt must not spawn"

    seq = recorder.sequence()
    assert seq == [("recon_service_probe", "allow"),
                   ("lab_http_probe", "allow"),
                   ("recon_service_probe", "denied")]
    # the third proposal never reached the PEP
    assert sum(1 for o in outs2 if "pep" in o) == 0
    assert spy["count"] == before, (
        "the denied third attempt must not spawn anything (episode-1 executions "
        "are hermetic in this test, so the spy must remain at zero)")

    # durable denial receipt with the rate reason
    rows = SV.store_rows(store.path)
    rate_denials = [r for r in rows if r.get("status") == "denied"
                    and "rate limit exceeded" in r.get("reason", "").lower()]
    assert len(rate_denials) == 1
    assert rate_denials[0]["action_id"] == "ACT-D2-PROBE-0001"
    assert rate_denials[0]["decision"] == "deny"


# 5. limiter state is shared across episodes on the same broker
def test_limiter_state_shared_across_episodes(tmp_path):
    workdir = tmp_path / "s3"
    broker = make_broker_from_policy(SV.scenario_policy_2pm(workdir))
    runtime, _ = SV.build_runtime(broker, EvidenceStore(workdir / "store.jsonl"),
                                  workdir / "artifacts")
    m = SV.d2_mission({"0": [SV.cand("0", "A")], "1": [SV.cand("1", "B")]},
                      max_iterations=5)
    runtime.run_episode(m, episode_outputs=[])
    # same broker, new episode: the window still holds the two prior actions
    receipt = broker.propose_action(target="dvwa", action_type="recon_service_probe",
                                    capability="exec.d1_lab_probe", method="nmap",
                                    impact_estimate=2.0)
    assert "DENIED" in str(receipt.status)
    assert "rate limit" in str(receipt.reason).lower()


# 6. Action A capability-failure fixture produces an honest failure receipt
def test_action_a_capability_fault_honest_failure(tmp_path):
    workdir = tmp_path / "c2fault"
    broker = make_broker_from_policy(D2_POLICY_PATH)
    store = EvidenceStore(workdir / "store.jsonl")
    runtime, caps = SV.build_runtime(broker, store, workdir / "artifacts",
                                     runner_a=SV.hermetic_nmap)  # placeholder
    # inject the fault on the NMAP runner specifically
    def failing_nmap(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "nmap: connection refused (fixture)"
        return P()
    runtime._capability_registry["exec.d1_lab_probe"] = D1LabProbeCapability(
        broker=broker, artifacts_dir=workdir / "artifacts",
        runner=failing_nmap, inspector=SV.hermetic_inspector)
    from orchestrator.rsi.exploration_policy import ExplorationPolicy
    policy = ExplorationPolicy(
        policy_id="rsi01-c2-retry-a", version=1, status="experimental",
        created_by="rsi01", motivation="retry verification",
        parameters={"order": ["A", "B"], "retry": {"action": "A", "at_most": 1}})
    policy.validate()
    steps = policy.ordered_action_keys()
    mission = SV.d2_mission({str(i): [SV.cand(str(i), k)]
                             for i, k in enumerate(steps)}, max_iterations=5)
    outs = []
    _, termination = runtime.run_episode(mission, episode_outputs=outs)
    assert termination.final_stage == "pep"
    rows = SV.store_rows(store.path)
    failed = [r for r in rows if r.get("status") == "failed"]
    assert failed, "capability fault must persist a failure receipt"
    assert "refused" in failed[0].get("reason", "")


# 7+8. C2 retry branch: unsupported for capability faults (halts at PEP);
# exercised across episodes for transient rate denials.
def test_c2_retry_unsupported_for_capability_faults(tmp_path):
    result = SV.c2_capability_fault_test(tmp_path / "c2fault")
    assert result["terminated_at"] == "pep"
    assert result["retry_step_proposed"] is False
    assert result["persisted_failure_receipts"] == 1
    assert "UNSUPPORTED" in result["verdict"]


def test_c2_retry_exercised_across_episodes_after_window_expiry(tmp_path):
    result = SV.c2_rate_retry_window_test(tmp_path / "c2window")
    assert result["denials_before_window_expiry"] >= 2  # B + A-retry denied in ep1
    assert result["retry_exercised_across_episodes"] is True
    assert result["episode_2"]["pep_invocations"] == 1
    # B remains honestly denied under the 1/min scenario budget
    assert result["episode_2"]["b_executed_http_302"] is False


def test_c2_in_episode_rate_denial_continuation_is_bounded_and_honest(tmp_path):
    workdir = tmp_path / "c2in"
    broker = make_broker_from_policy(SV.scenario_policy_1pm(workdir))
    store = EvidenceStore(workdir / "store.jsonl")
    runtime, caps = SV.build_runtime(broker, store, workdir / "artifacts")
    mission = SV.d2_mission({"0": [SV.cand("0", "A")],
                             "1": [SV.cand("1", "B")],
                             "2": [SV.cand("2", "A")]}, max_iterations=3)
    outs = []
    _, termination = runtime.run_episode(mission, episode_outputs=outs)
    # A executes; B and the A-retry are rate-denied at the broker stage; the
    # loop ends at the last broker denial with a truthful reason and never
    # claims objective success
    assert termination.final_stage == "broker"
    assert "rate limit" in termination.reason.lower()
    assert "objective met" not in termination.reason
    rows = SV.store_rows(store.path)
    denied = [r for r in rows if r.get("status") == "denied"]
    assert len(denied) == 2  # B + A-retry, both rate-denied, both persisted


# 9. no budget reset, policy broadening, evidence fabrication, or bypass

def test_budget_is_not_reset_by_a_new_episode(tmp_path):
    workdir = tmp_path / "s3"
    broker = make_broker_from_policy(SV.scenario_policy_2pm(workdir))
    runtime, _ = SV.build_runtime(broker, EvidenceStore(workdir / "store.jsonl"),
                                  workdir / "artifacts")
    m = SV.d2_mission({"0": [SV.cand("0", "A")], "1": [SV.cand("1", "B")]},
                      max_iterations=5)
    runtime.run_episode(m, episode_outputs=[])
    # a fresh episode on the SAME broker is still rate-limited (no reset)
    receipt = broker.propose_action(target="dvwa", action_type="recon_service_probe",
                                    capability="exec.d1_lab_probe", method="nmap",
                                    impact_estimate=2.0)
    assert "DENIED" in str(receipt.status)
    assert "rate limit" in str(receipt.reason).lower()


def test_scenario_policy_copy_cannot_broaden_production_policy(tmp_path):
    """The S3 scenario writes its own policy copy; the production D2 artifact
    must remain byte-identical and its cap unchanged."""
    import hashlib
    before = hashlib.sha256(Path(D2_POLICY_PATH).read_bytes()).hexdigest()
    SV.scenario_policy_2pm(tmp_path)
    after = hashlib.sha256(Path(D2_POLICY_PATH).read_bytes()).hexdigest()
    assert before == after
    policy_data = json.loads(Path(D2_POLICY_PATH).read_text())
    assert policy_data["max_episode_steps"] == 5
    assert policy_data["rate_limits"]["max_actions_per_minute"] == 6


def test_forged_success_record_still_rejected_after_remediation(tmp_path):
    from orchestrator.runtime.evidence_v1 import EvidenceRecord
    from orchestrator.runtime.stages import _verify_objective_action
    store = EvidenceStore(tmp_path / "store.jsonl")
    store.append(EvidenceRecord.execution_result(
        mission_id="d2-bounded-episode", producer="runtime.receipt",
        action_id=CONSTRAINT_ECHO["objective_requires"][0], status="ok",
        decision="allow"))  # no artifacts, no decision_id
    v = _verify_objective_action(store, {"mission_id": "d2-bounded-episode"},
                                 CONSTRAINT_ECHO["objective_requires"][0],
                                 (tmp_path,))
    assert v["ok"] is False


# 10. D2 governance cap and D1 policy remain intact

def test_d2_policy_cap_and_d1_policy_unchanged():
    d2 = json.loads(Path(D2_POLICY_PATH).read_text())
    assert d2["max_episode_steps"] == 5
    d1 = json.loads(Path(D1_POLICY_PATH.parent / "engagement-d1-v1.json").read_text())
    assert "lab_http_probe" not in d1["allowed"]["action_types"]
    assert "exec.http_probe" not in d1["allowed"]["capabilities"]
