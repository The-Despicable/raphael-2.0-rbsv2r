"""
P2.1 walking-skeleton tests (updated for CONV-1 real Broker)

Per v4 section 13.3 / 13.6 G2 Gate. The Runtime now uses the real brain
CapabilityBroker.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_runtime_executes_via_broker():
    """v4 section 13.4: test_runtime_executes_via_broker.

    P3.0 CONV-1: uses real brain CapabilityBroker.
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_broker", name="broker-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    broker_entry = next(
        (e for e in traces[0].entries if e["stage"] == "broker"), None
    )
    assert broker_entry is not None
    assert broker_entry["success"]


def test_receipt_minted_by_pep():
    """v4 section 13.4: test_receipt_minted_by_pep.

    Every EXECUTE must mint a receipt linking event_id to decision_id (INV-2).
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import EvidenceReceipt
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_receipt", name="receipt-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    ctx = {
        "view": {"mission_name": "receipt-test"},
        "world_model": rt._world_model,
        "broker": rt._broker,
        "capability": rt._capability,
        "capability_name": "fixture.inspect",
        # RSI-1 C-1: direct stage driving must carry the Runtime-bound
        # execution authority; the PEP refuses unbound contexts.
        "capability_governance": rt._governance,
        "governed_step_budget": rt._step_budget,
    }
    from orchestrator.runtime.stages import STAGE_HANDLERS
    for name, handler in STAGE_HANDLERS.items():
        result = handler(ctx)
        ctx[name] = result.output
    receipt = ctx["receipt"]["receipt"]
    assert isinstance(receipt, EvidenceReceipt)
    assert receipt.event_id
    assert receipt.decision_id
    assert receipt.event_id == ctx["pep"]["event"].event_id
    assert receipt.decision_id == ctx["broker"]["decision"].decision_id


def test_runtime_has_no_seam_dependency():
    """v4 section 13.4 / v4 INV-6: Runtime cannot import seam."""
    import sys
    from orchestrator.runtime import loop as runtime_loop
    seam_imports = [
        name for name in dir(runtime_loop)
        if "seam" in name.lower() or "weld" in name.lower()
    ]
    assert not seam_imports
    import orchestrator.runtime as runtime_pkg
    for modname in ["orchestrator.runtime", "orchestrator.runtime.loop",
                    "orchestrator.runtime.stages", "orchestrator.runtime.types",
                    "orchestrator.runtime.policy",
                    "orchestrator.runtime.safe_proving_capability"]:
        mod = sys.modules.get(modname)
        if mod is None:
            continue
        for attr in dir(mod):
            if "seam" in attr.lower() or "weld" in attr.lower():
                pytest.fail(f"{modname}.{attr} looks seam-related")


def test_runtime_stage_order():
    """v4 section 13.4: test_runtime_stage_order."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.stages import STAGE_ORDER
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_order", name="order-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    executed = [e["stage"] for e in traces[0].entries]
    assert executed == STAGE_ORDER


def test_head1_loop_not_used_by_runtime():
    """v4 section 13.4: test_head1_loop_not_used_by_runtime."""
    import sys
    from orchestrator.runtime import loop as runtime_loop
    source = Path(runtime_loop.__file__).read_text()
    assert "RaphaelOrganism" not in source


def test_import_graph_single_runtime():
    """v4 section 23: test_import_graph_single_runtime."""
    import sys
    from orchestrator.runtime import RaphaelRuntime

    seen = set()
    arena_found = []

    def walk(modname):
        if modname in seen:
            return
        seen.add(modname)
        mod = sys.modules.get(modname)
        if mod is None:
            return
        import inspect
        for _name, val in inspect.getmembers(mod):
            if inspect.ismodule(val) and val.__name__:
                if val.__name__.startswith("arena") and val.__name__ not in seen:
                    arena_found.append(val.__name__)
                walk(val.__name__)

    walk("orchestrator.runtime")
    assert not arena_found


def test_walking_skeleton_e2e():
    """v4 section 13.5: runtime proof."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_e2e", name="e2e-walking-skeleton", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)

    assert termination.terminated
    assert termination.iterations == 1
    assert "complete" in termination.reason or "fail" in termination.reason.lower()

    assert len(traces[0].entries) == 10

    stage_names = [e["stage"] for e in traces[0].entries]
    expected_stages = [
        "observe", "worldmodel_read", "student_candidate",
        "planner_request", "broker", "pep", "receipt",
        "worldmodel_integrate", "contradiction", "replan",
    ]
    assert stage_names == expected_stages

    broker_entry = next(e for e in traces[0].entries if e["stage"] == "broker")
    assert broker_entry["success"]

    receipt_entry = next(e for e in traces[0].entries if e["stage"] == "receipt")
    assert receipt_entry["success"]


def test_decision_trace_emitted():
    """v4 section 13.3 P2.6: DecisionTrace."""
    import json
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_trace", name="trace-test", objectives=["inspect"]
    )
    traces, _ = rt.run_episode(mission)
    trace_dict = traces[0].to_dict()
    assert "trace_id" in trace_dict
    assert "mission_id" in trace_dict
    assert "entries" in trace_dict
    assert len(trace_dict["entries"]) == 10
    for entry in trace_dict["entries"]:
        assert "stage" in entry
        assert "success" in entry
        assert "duration_ms" in entry
    json.dumps(trace_dict)
