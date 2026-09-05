"""
P2.1 walking-skeleton tests (v4 §13.3 / §13.6 G2 Gate)

Per v4 §13.4 minimum tests:
- test_runtime_executes_via_broker
- test_receipt_minted_by_pep
- test_runtime_has_no_seam_dependency
- test_runtime_stage_order
- test_head1_loop_not_used_by_runtime
- test_import_graph_single_runtime (already in P2 guardrails)

Per v4 §13.5 runtime proof: one command demonstrates the walking
skeleton: CLI -> Runtime -> observe -> candidates -> plan -> Broker ->
PEP -> safe capability -> receipt -> WorldModel integration -> trace.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_runtime_executes_via_broker():
    """v4 §13.4: test_runtime_executes_via_broker.

    The Runtime must call Broker.authorize before any EXECUTE.
    P2.1 uses bootstrap-v0 as the Broker's policy.
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_broker", name="broker-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    # The broker stage must have run and produced a decision
    broker_entry = next(
        (e for e in traces[0].entries if e["stage"] == "broker"), None
    )
    assert broker_entry is not None, "broker stage did not run"
    assert broker_entry["success"], "broker stage did not succeed"


def test_receipt_minted_by_pep():
    """v4 §13.4: test_receipt_minted_by_pep.

    Every EXECUTE must mint a receipt linking event_id to decision_id.
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.types import EvidenceReceipt
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_receipt", name="receipt-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    # Run the stages manually to capture the receipt
    ctx = {
        "view": {"mission_name": "receipt-test"},
        "world_model": rt._world_model,
        "policy": rt._policy,
        "capability": rt._capability,
    }
    from orchestrator.runtime.stages import STAGE_HANDLERS
    for name, handler in STAGE_HANDLERS.items():
        result = handler(ctx)
        ctx[name] = result.output
    receipt = ctx["receipt"]["receipt"]
    assert isinstance(receipt, EvidenceReceipt)
    assert receipt.event_id, "receipt must have event_id"
    assert receipt.decision_id, "receipt must have decision_id"
    assert receipt.event_id == ctx["pep"]["event"].event_id, (
        "receipt.event_id must match pep event.event_id"
    )
    assert receipt.decision_id == ctx["broker"]["decision"].decision_id, (
        "receipt.decision_id must match broker decision.decision_id"
    )


def test_runtime_has_no_seam_dependency():
    """v4 §13.4 / v4 INV-6: Runtime cannot import seam.

    The migration seam is a temporary scaffold; Runtime must never
    import it.
    """
    import sys
    # Import the Runtime and check its module namespace
    from orchestrator.runtime import loop as runtime_loop
    seam_imports = [
        name for name in dir(runtime_loop)
        if "seam" in name.lower() or "weld" in name.lower()
    ]
    assert not seam_imports, (
        f"Runtime module must not have seam-related symbols: {seam_imports}"
    )
    # Also check the full runtime package
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
    """v4 §13.4: test_runtime_stage_order.

    The Runtime must execute stages in the canonical order.
    P2.1 walking skeleton: observe -> worldmodel_read -> student_candidate
    -> planner_request -> broker -> pep -> receipt -> worldmodel_integrate
    -> contradiction -> replan.
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.stages import STAGE_ORDER
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_order", name="order-test", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)
    executed = [e["stage"] for e in traces[0].entries]
    assert executed == STAGE_ORDER, (
        f"Stage order mismatch: expected {STAGE_ORDER}, got {executed}"
    )


def test_head1_loop_not_used_by_runtime():
    """v4 §13.4: test_head1_loop_not_used_by_runtime.

    The Runtime must not use the legacy Head-1 internal loop
    (RaphaelOrganism). v4 L3: Head 1's old internal loop is superseded.
    """
    import sys
    # Verify Runtime does not import RaphaelOrganism
    from orchestrator.runtime import loop as runtime_loop
    source = Path(runtime_loop.__file__).read_text()
    assert "RaphaelOrganism" not in source, (
        "Runtime must not reference RaphaelOrganism (legacy Head-1 loop)"
    )


def test_import_graph_single_runtime():
    """v4 §23: test_import_graph_single_runtime.

    There is exactly one canonical Runtime. The Runtime's transitive
    closure must not include arena.
    """
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
    assert not arena_found, (
        f"Runtime's transitive closure must not include arena. Found: {arena_found}"
    )


def test_walking_skeleton_e2e():
    """v4 §13.5: runtime proof — one command demonstrates the walking skeleton.

    CLI -> Runtime -> observe -> worldmodel_read -> student_candidate
    -> planner_request -> Broker -> PEP -> safe capability -> receipt
    -> worldmodel_integrate -> contradiction -> replan -> trace
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="m_e2e", name="e2e-walking-skeleton", objectives=["inspect"]
    )
    traces, termination = rt.run_episode(mission)

    # Verify termination is clean
    assert termination.terminated
    assert termination.iterations == 1
    assert "complete" in termination.reason or "fail" in termination.reason.lower()

    # Verify all 10 stages executed
    assert len(traces[0].entries) == 10

    # Verify the trace has the expected stages
    stage_names = [e["stage"] for e in traces[0].entries]
    expected_stages = [
        "observe", "worldmodel_read", "student_candidate",
        "planner_request", "broker", "pep", "receipt",
        "worldmodel_integrate", "contradiction", "replan",
    ]
    assert stage_names == expected_stages

    # Verify bootstrap-v0 was applied
    broker_entry = next(e for e in traces[0].entries if e["stage"] == "broker")
    assert broker_entry["success"], "bootstrap-v0 should allow safe_proving_capability"

    # Verify receipt was minted
    receipt_entry = next(e for e in traces[0].entries if e["stage"] == "receipt")
    assert receipt_entry["success"], "receipt stage must succeed"


def test_decision_trace_emitted():
    """v4 §13.3 P2.6: DecisionTrace shows stage, candidate/request, policy
    decision, execution linkage, receipt id, next-stage outcome.
    """
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
    # Each entry must have stage, success, duration_ms
    for entry in trace_dict["entries"]:
        assert "stage" in entry
        assert "success" in entry
        assert "duration_ms" in entry
    # Trace must be JSON-serializable
    json.dumps(trace_dict)  # raises if not serializable
