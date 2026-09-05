"""
G2-C2 / G3-EN-4 — FAIL-CLOSED PROOF (re-proven against real CapabilityBroker)

CONV-1: these tests are re-proven against the real brain
CapabilityBroker, not the old BootstrapPolicy placeholder.
Assertions are preserved; the policy source is the real Broker.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


def _make_broker(allowed_action_types=None, allowed_capabilities=None,
                 allowed_targets=None):
    """Create a real CapabilityBroker for testing."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    return CapabilityBroker(BrokerPolicy(
        schema_version=1,
        engagement_id="g3-en-4-fail-closed",
        allowed_targets=allowed_targets or ["*"],
        allowed_action_types=allowed_action_types or ["safe_proving_capability", "mock_capability"],
        allowed_capabilities=allowed_capabilities or ["fixture.inspect", "*"],
    ))


def test_c2_1_non_allowlisted_action_class_denied():
    """G2-C2.1: real Broker denies any action_class not in its policy."""
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker, ActionProposalStatus,
    )
    broker = CapabilityBroker(BrokerPolicy(
        schema_version=1,
        engagement_id="g3-en-4-c2-1",
        allowed_targets=["*"],
        allowed_action_types=[],
        allowed_capabilities=["fixture.inspect"],
    ))
    receipt = broker.propose_action(
        target="system_info.name",
        action_type="unauthorized_subprocess_exec",
        capability="fixture.inspect",
        method="inspect",
        impact_estimate=0.0,
    )
    assert receipt.status != ActionProposalStatus.AUTHORIZED, (
        f"Non-allowlisted action_class must be denied. Got: {receipt.status}"
    )
    assert receipt.reason, "Denied receipt must have a reason"


def test_c2_2_denied_produces_no_execution_event():
    """G2-C2.2: a denied action must not reach the PEP stage."""
    from orchestrator.runtime.types import ActionRequest
    from orchestrator.runtime.stages import STAGE_BROKER, STAGE_HANDLERS

    broker = _make_broker(allowed_action_types=[])
    bad_request = ActionRequest(
        action_type="unauthorized_subprocess_exec",
        target="10.0.0.1",
        args={},
    )
    stage_ctx: dict = {
        "view": {},
        "world_model": {"entities": {}, "facts": {}},
        "broker": broker,
        "capability": None,
        "capability_name": "fixture.inspect",
        "planner_request": {"request": bad_request},
    }
    broker_result = STAGE_HANDLERS[STAGE_BROKER](stage_ctx)
    assert not broker_result.success
    assert broker_result.output["decision"].decision == "deny"
    assert "pep" not in stage_ctx, "PEP stage must not run when broker denies"


def test_c2_3_denied_produces_no_receipt():
    """G2-C2.3: a denied action must not produce an EvidenceReceipt."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import ActionRequest, StageResult
    from orchestrator.runtime import stages as _stages

    broker = _make_broker(allowed_action_types=[])

    def bad_planner(ctx):
        return StageResult.make(
            stage_name="planner_request",
            success=True,
            output={"request": ActionRequest(
                action_type="unauthorized_subprocess_exec",
                target="10.0.0.1",
                args={},
            )},
        )

    original_planner = _stages.STAGE_HANDLERS["planner_request"]
    _stages.STAGE_HANDLERS["planner_request"] = bad_planner
    rt = RaphaelRuntime(broker=broker)
    try:
        mission = MissionContext(
            mission_id="c2_3", name="fail-closed", objectives=["denied"]
        )
        traces, termination = rt.run_episode(mission)
    finally:
        _stages.STAGE_HANDLERS["planner_request"] = original_planner

    broker_entry = next(
        (e for e in traces[0].entries if e["stage"] == "broker"), None
    )
    assert broker_entry is not None
    assert not broker_entry["success"]
    stage_names = [e["stage"] for e in traces[0].entries]
    assert "receipt" not in stage_names
    assert "pep" not in stage_names


def test_c2_4_denial_appears_in_decision_trace():
    """G2-C2.4: a denial must appear in the DecisionTrace."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import ActionRequest, StageResult
    from orchestrator.runtime import stages as _stages

    broker = _make_broker(allowed_action_types=[])

    def bad_planner(ctx):
        return StageResult.make(
            stage_name="planner_request",
            success=True,
            output={"request": ActionRequest(
                action_type="unauthorized_subprocess_exec",
                target="10.0.0.1",
                args={},
            )},
        )

    original_planner_c24 = _stages.STAGE_HANDLERS["planner_request"]
    _stages.STAGE_HANDLERS["planner_request"] = bad_planner
    rt = RaphaelRuntime(broker=broker)
    try:
        mission = MissionContext(
            mission_id="c2_4", name="trace-denial", objectives=["denied"]
        )
        traces, termination = rt.run_episode(mission)
    finally:
        _stages.STAGE_HANDLERS["planner_request"] = original_planner_c24

    trace_dict = traces[0].to_dict()
    broker_entry = next(
        (e for e in trace_dict["entries"] if e["stage"] == "broker"), None
    )
    assert broker_entry is not None
    assert broker_entry["success"] is False
    assert broker_entry.get("error") is not None
    assert "broker" in termination.reason or "failed" in termination.reason.lower()


def test_c2_5_denied_episode_terminates_deterministically():
    """G2-C2.5: a denied episode terminates with a deterministic reason."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import ActionRequest, StageResult
    from orchestrator.runtime import stages as _stages

    def bad_planner(ctx):
        return StageResult.make(
            stage_name="planner_request",
            success=True,
            output={"request": ActionRequest(
                action_type="unauthorized_subprocess_exec",
                target="x",
                args={},
            )},
        )

    broker = _make_broker(allowed_action_types=[])
    original_planner_c25 = _stages.STAGE_HANDLERS["planner_request"]
    _stages.STAGE_HANDLERS["planner_request"] = bad_planner
    rt = RaphaelRuntime(broker=broker)
    try:
        mission = MissionContext(
            mission_id="c2_5", name="deterministic", objectives=["d"]
        )
        traces, term = rt.run_episode(mission)
    finally:
        _stages.STAGE_HANDLERS["planner_request"] = original_planner_c25

    assert term.terminated
    assert term.iterations == 1
    assert "broker" in term.final_stage or "fail" in term.reason.lower()
    assert isinstance(term.final_stage, str)
    assert len(traces[0].entries) == 5


def test_c2_6a_missing_broker_fails_closed():
    """G2-C2.6a: when broker is None, broker stage fails (fail-closed)."""
    from orchestrator.runtime.stages import STAGE_BROKER, STAGE_HANDLERS
    from orchestrator.runtime.types import ActionRequest

    ctx = {
        "view": {},
        "world_model": None,
        "broker": None,
        "capability": None,
        "capability_name": "fixture.inspect",
        "planner_request": {"request": ActionRequest(
            action_type="safe_proving_capability", target="x", args={},
        )},
    }
    result = STAGE_HANDLERS[STAGE_BROKER](ctx)
    assert not result.success
    assert result.output.get("decision") is None


def test_c2_6b_failing_broker_fails_closed():
    """G2-C2.6b: a broker that raises during propose_action fails closed."""
    from orchestrator.runtime.stages import STAGE_BROKER, STAGE_HANDLERS
    from orchestrator.runtime.types import ActionRequest

    class BrokenBroker:
        def propose_action(self, **kwargs):
            raise RuntimeError("broker is broken")

    ctx = {
        "view": {},
        "world_model": None,
        "broker": BrokenBroker(),
        "capability": None,
        "capability_name": "fixture.inspect",
        "planner_request": {"request": ActionRequest(
            action_type="safe_proving_capability", target="x", args={},
        )},
    }
    result = STAGE_HANDLERS[STAGE_BROKER](ctx)
    assert not result.success


def test_c2_7_default_deny_dynamically_exercised():
    """G2-C2.7: the default-deny branch is actually executed for an unknown class."""
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker, ActionProposalStatus,
    )

    broker = CapabilityBroker(BrokerPolicy(
        schema_version=1,
        engagement_id="g3-en-4-c2-7",
        allowed_targets=["*"],
        allowed_action_types=[],
        allowed_capabilities=["fixture.inspect"],
    ))

    receipt = broker.propose_action(
        target="x",
        action_type="this_is_not_a_real_action_class_xyz",
        capability="fixture.inspect",
        method="inspect",
        impact_estimate=0.0,
    )

    assert receipt.status != ActionProposalStatus.AUTHORIZED
    assert receipt.reason

    allow_broker = _make_broker(allowed_action_types=["safe_proving_capability"])
    allowed_receipt = allow_broker.propose_action(
        target="x",
        action_type="safe_proving_capability",
        capability="fixture.inspect",
        method="inspect",
        impact_estimate=0.0,
    )
    assert allowed_receipt.status == ActionProposalStatus.AUTHORIZED
    assert receipt.status != allowed_receipt.status


def test_c2_8_full_fail_closed_episode():
    """G2-C2.8: end-to-end fail-closed with real Broker."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import ActionRequest, StageResult
    from orchestrator.runtime import stages as _stages

    broker = _make_broker(allowed_action_types=[])

    def bad_planner(ctx):
        return StageResult.make(
            stage_name="planner_request",
            success=True,
            output={"request": ActionRequest(
                action_type="totally_unknown_action_class_zzz",
                target="x",
                args={},
            )},
        )

    original_planner_c28 = _stages.STAGE_HANDLERS["planner_request"]
    _stages.STAGE_HANDLERS["planner_request"] = bad_planner
    rt = RaphaelRuntime(broker=broker)
    try:
        mission = MissionContext(
            mission_id="c2_8", name="full-fail-closed", objectives=["d"]
        )
        traces, term = rt.run_episode(mission)
    finally:
        _stages.STAGE_HANDLERS["planner_request"] = original_planner_c28

    broker = next(e for e in traces[0].entries if e["stage"] == "broker")
    assert broker["success"] is False

    stage_names = [e["stage"] for e in traces[0].entries]
    assert "pep" not in stage_names
    assert "receipt" not in stage_names
    assert "broker" in [e["stage"] for e in traces[0].entries]
    assert term.terminated
    assert term.iterations == 1
    assert "broker" in term.final_stage
