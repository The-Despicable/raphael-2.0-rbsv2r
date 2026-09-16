"""
§14.3/§14.4 authorization lifecycle on the canonical Runtime path.

The Runtime owns the Broker execution lifecycle around the PEP:

    AUTHORIZED -> STARTED (before execution) -> SUCCEEDED / FAILED

Terminal receipts cannot start again (existing VALID_TRANSITIONS contract),
so completed authorization is not replayable. Evidence v1 stays downstream
and non-authoritative; the Broker remains the sole PDP.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime import MissionContext, RaphaelRuntime, RuntimeContext
from orchestrator.runtime.policy import make_broker_from_bootstrap
from orchestrator.runtime.stages import stage_pep
from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.hardening.action_receipt import ActionProposalStatus


def _step_outputs(rt, mission_id="lc"):
    ctx = RuntimeContext(
        mission_id=mission_id, objective_id="o",
        view={"target": "system_info.name"}, iteration=0, scope=None,
    )
    outputs: dict = {}
    traces, term = rt.step(ctx, stage_outputs=outputs)
    return outputs, traces, term


def _candidate_mission(mission_id, impact=0.0, action_id="lc-cand-001",
                       action_type="safe_proving_capability",
                       target="system_info.name", method="inspect",
                       args=None):
    candidate = {
        "action_id": action_id,
        "action_type": action_type,
        "target": target,
        "capability": "fixture.inspect",
        "method": method,
        "args": args if args is not None else {"read_only": True},
        "rationale": "lifecycle test",
        "confidence": 1.0,
        "impact_estimate": impact,
    }
    return MissionContext(
        mission_id=mission_id, name=mission_id, objectives=["inspect"],
        constraints={"candidates": {"0": [candidate]},
                     "default_target": "system_info.name",
                     "objective_id": "lc-objective"},
    )


# ── 1. Successful lifecycle ─────────────────────────────────────────

def test_canonical_success_lifecycle():
    rt = RaphaelRuntime()
    outputs, traces, term = _step_outputs(rt)
    receipt = outputs["broker"]["receipt"]

    pep_entry = next(e for e in traces.entries if e["stage"] == "pep")
    assert pep_entry["success"] is True
    assert receipt.status == ActionProposalStatus.SUCCEEDED
    assert receipt.started_at > 0.0
    assert receipt.completed_at >= receipt.started_at
    assert receipt.result != ""
    # Terminal receipt is a valid non-restartable state.
    assert not receipt.can_transition_to(ActionProposalStatus.STARTED)


def test_started_state_is_live_during_execution():
    """STARTED is entered before the capability executes."""
    from orchestrator.exec.safe_capability import CapabilityResult

    captured = {}

    class _RecordingCapability:
        def __init__(self, broker):
            self.broker = broker

        def record_authorization(self, target):
            pass

        def inspect(self, target):
            captured["started_count"] = sum(
                1 for r in self.broker.receipt_store.values()
                if r.status == ActionProposalStatus.STARTED
            )
            captured["concurrent"] = self.broker.get_rate_status()["concurrent"]
            return CapabilityResult(
                capability="fixture.inspect", target=target, output="during")

    broker = make_broker_from_bootstrap()
    rt = RaphaelRuntime(broker=broker, capability=_RecordingCapability(broker))
    outputs, traces, term = _step_outputs(rt, "lc-started")

    assert captured["started_count"] == 1
    assert captured["concurrent"] == 1  # start accounted before execution
    assert outputs["broker"]["receipt"].status == ActionProposalStatus.SUCCEEDED


# ── 2. Failed lifecycle ─────────────────────────────────────────────

def test_canonical_failed_lifecycle():
    class _FailingCapability:
        def __init__(self, broker):
            self.broker = broker

        def record_authorization(self, target):
            pass

        def inspect(self, target):
            raise RuntimeError("capability exploded")

    broker = make_broker_from_bootstrap()
    rt = RaphaelRuntime(broker=broker, capability=_FailingCapability(broker))
    outputs, traces, term = _step_outputs(rt, "lc-fail")

    receipt = outputs["broker"]["receipt"]
    assert receipt.status == ActionProposalStatus.FAILED
    assert receipt.completed_at >= receipt.started_at > 0.0
    pep_entry = next(e for e in traces.entries if e["stage"] == "pep")
    assert pep_entry["success"] is False
    # Terminal failure: no false success, and concurrency was released.
    assert not receipt.can_transition_to(ActionProposalStatus.SUCCEEDED)
    assert broker.get_rate_status()["concurrent"] == 0


# ── 3/4. Terminal receipt + accounting ──────────────────────────────

def test_canonical_accounting_moves():
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="lc-acct", allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"], max_impact_per_action=5.0,
    ))
    rt = RaphaelRuntime(broker=broker)
    outputs: list = []
    rt.run_episode(_candidate_mission("lc-acct", impact=1.5),
                   episode_outputs=outputs)

    receipt = outputs[0]["broker"]["receipt"]
    assert receipt.status == ActionProposalStatus.SUCCEEDED
    rate = broker.get_rate_status()
    assert rate["per_minute"] >= 1          # rate tracker advanced
    assert rate["concurrent"] == 0          # released after completion
    assert broker.get_cumulative_impact() == 1.5  # terminal success impact


# ── 5. Replay denied ────────────────────────────────────────────────

def test_terminal_receipt_replay_denied():
    rt = RaphaelRuntime()
    outputs, traces, term = _step_outputs(rt, "lc-replay")
    receipt = outputs["broker"]["receipt"]
    assert receipt.status == ActionProposalStatus.SUCCEEDED

    replay_ctx = {
        "capability": rt._capability,
        "broker": outputs["broker"],
        "planner_request": outputs["planner_request"],
        "scope": None,
    }
    out = stage_pep(replay_ctx)
    assert out.success is False
    assert "not STARTABLE" in (out.error or "")
    assert receipt.status == ActionProposalStatus.SUCCEEDED  # unchanged


# ── Sandbox branch also gets a truthful lifecycle ───────────────────

def test_sandbox_branch_lifecycle_and_terminal_replay():
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="lc-sbx", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    rt = RaphaelRuntime(broker=broker)
    mission = _candidate_mission(
        "lc-sbx", action_id="lc-sbx-001", action_type="sandboxed_exec",
        target="sbx-target", method="exec",
        args={"argv": ("/bin/echo", "lifecycle")})
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)

    receipt = outputs[0]["broker"]["receipt"]
    pep_entry = next(e for e in traces[0].entries if e["stage"] == "pep")
    assert pep_entry["success"] is True
    assert receipt.status == ActionProposalStatus.SUCCEEDED
    assert receipt.started_at > 0.0

    out = stage_pep({
        "capability": rt._capability,
        "broker": outputs[0]["broker"],
        "planner_request": outputs[0]["planner_request"],
        "scope": None,
    })
    assert out.success is False
    assert "not STARTABLE" in (out.error or "")


# ── 8. Evidence v1 stays downstream (records the lifecycle-terminal run) ──

def test_evidence_records_after_lifecycle(tmp_path):
    from orchestrator.exec.evidence_store import EvidenceStore

    store = EvidenceStore(str(tmp_path / "ev.jsonl"))
    rt = RaphaelRuntime(evidence_store=store)
    outputs: list = []
    rt.run_episode(_candidate_mission("lc-ev"), episode_outputs=outputs)

    evidence_id = outputs[0]["receipt"]["evidence_v1_id"]
    assert evidence_id.startswith("ev1_")
    record = store.get(evidence_id)
    assert record is not None
    assert dict(record.payload)["decision"] == "allow"
    assert outputs[0]["broker"]["receipt"].status == ActionProposalStatus.SUCCEEDED
