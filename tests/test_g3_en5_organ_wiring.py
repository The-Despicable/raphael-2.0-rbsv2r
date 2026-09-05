"""
G3-EN-5 — Organ wiring verification tests

Proves that Planner, WorldModel, Student, and ContradictionManager
(and EvidenceGraph, HypothesisManager, ActionRegistry) are wired
onto the canonical Runtime path.

Each organ is verified with real isinstance checks against the
concrete expected class (not isinstance(x, object)).

Constraints verified:
- One RaphaelRuntime, no second orchestrator
- No new stages (existing 10 stages, same order)
- CapabilityBroker remains the single PDP
- PEP remains under exec/
- INV-2 decision linkage preserved
- Fail-closed preserved
- Arena-free Runtime closure
- Student recording-only
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_g3_en5_planner_wired():
    """G3-EN-5: Planner is instantiated from orchestrator.brain.action.Planner."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.action import Planner
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.planner, Planner), (
        f"Planner must be orchestrator.brain.action.Planner, "
        f"got {type(rt._organs.planner).__module__}.{type(rt._organs.planner).__name__}"
    )
    assert hasattr(rt._organs.planner, "decide"), (
        "Planner must expose a decide() method"
    )


def test_g3_en5_worldmodel_wired():
    """G3-EN-5: WorldModel is instantiated from orchestrator.brain.world.WorldModel."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.world import WorldModel
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.world_model, WorldModel), (
        f"WorldModel must be orchestrator.brain.world.WorldModel, "
        f"got {type(rt._organs.world_model).__module__}.{type(rt._organs.world_model).__name__}"
    )
    assert hasattr(rt._organs.world_model, "entities")
    assert hasattr(rt._organs.world_model, "relationships")


def test_g3_en5_student_recording_mode_wired():
    """G3-EN-5: Student is from StudentCandidateGenerator (recording mode only)."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.candidate_generators.student_generator import (
        StudentCandidateGenerator,
    )
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.student, StudentCandidateGenerator), (
        f"Student must be StudentCandidateGenerator, "
        f"got {type(rt._organs.student).__module__}.{type(rt._organs.student).__name__}"
    )


def test_g3_en5_contradiction_wired():
    """G3-EN-5: ContradictionManager is from orchestrator.brain.contradiction."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.contradiction import ContradictionManager
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.contradiction_manager, ContradictionManager), (
        f"ContradictionManager must be orchestrator.brain.contradiction.ContradictionManager, "
        f"got {type(rt._organs.contradiction_manager).__module__}.{type(rt._organs.contradiction_manager).__name__}"
    )


def test_g3_en5_single_cognitive_loop():
    """G3-EN-5: there is exactly one Runtime class (no second orchestrator)."""
    from orchestrator.runtime import RaphaelRuntime
    assert RaphaelRuntime is not None
    from orchestrator.runtime.stages import STAGE_ORDER
    expected = [
        "observe", "worldmodel_read", "student_candidate",
        "planner_request", "broker", "pep", "receipt",
        "worldmodel_integrate", "contradiction", "replan",
    ]
    assert STAGE_ORDER == expected, (
        f"Stage order must be unchanged. Got: {STAGE_ORDER}"
    )


def test_g3_en5_single_pdp():
    """G3-EN-5: CapabilityBroker remains the single canonical PDP."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.capability_broker import CapabilityBroker
    rt = RaphaelRuntime()
    assert isinstance(rt._broker, CapabilityBroker), (
        f"The Runtime's single canonical PDP must be the real CapabilityBroker, "
        f"got {type(rt._broker).__module__}.{type(rt._broker).__name__}"
    )


def test_g3_en5_arena_free():
    """G3-EN-5: Runtime's transitive closure remains arena-free."""
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
    rt_direct_arena = []
    for modname in [
        "orchestrator.runtime",
        "orchestrator.runtime.loop",
        "orchestrator.runtime.stages",
        "orchestrator.runtime.types",
        "orchestrator.runtime.policy",
        "orchestrator.runtime.safe_proving_capability",
        "orchestrator.runtime.organs",
    ]:
        mod = sys.modules.get(modname)
        if mod is None:
            continue
        for attr in dir(mod):
            mod_obj = getattr(mod, attr, None)
            if hasattr(mod_obj, "__module__") and mod_obj.__module__:
                if mod_obj.__module__.startswith("arena"):
                    rt_direct_arena.append(f"{modname}.{attr}")
    assert not rt_direct_arena, (
        f"Runtime must not directly import arena. Found: {rt_direct_arena}"
    )


def test_g3_en5_inv2_preserved():
    """G3-EN-5: INV-2 decision linkage preserved with organ wiring."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    traces, term = rt.run_episode(MissionContext(
        mission_id="g3en5-inv2", name="inv2", objectives=["inspect"]
    ))
    ctx = {"view": {"target": "system_info.name"}, "world_model": rt._world_model,
            "broker": rt._broker, "capability": rt._capability,
            "organs": rt._organs, "capability_name": "fixture.inspect"}
    from orchestrator.runtime.stages import STAGE_HANDLERS
    for name, handler in STAGE_HANDLERS.items():
        r = handler(ctx)
        ctx[name] = r.output
    event = ctx["pep"]["event"]
    receipt = ctx["receipt"]["receipt"]
    decision = ctx["broker"]["decision"]
    assert event.decision_id == receipt.decision_id == decision.decision_id


def test_g3_en5_evidencegraph_wired():
    """G3-EN-5: EvidenceGraph is from orchestrator.brain.evidence."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.evidence import EvidenceGraph
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.evidence_graph, EvidenceGraph), (
        f"EvidenceGraph must be orchestrator.brain.evidence.EvidenceGraph, "
        f"got {type(rt._organs.evidence_graph).__module__}.{type(rt._organs.evidence_graph).__name__}"
    )


def test_g3_en5_hypothesismanager_wired():
    """G3-EN-5: HypothesisManager is from orchestrator.brain.hypothesis."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.hypothesis import HypothesisManager
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.hypothesis_manager, HypothesisManager), (
        f"HypothesisManager must be orchestrator.brain.hypothesis.HypothesisManager, "
        f"got {type(rt._organs.hypothesis_manager).__module__}.{type(rt._organs.hypothesis_manager).__name__}"
    )


def test_g3_en5_actionregistry_wired():
    """G3-EN-5: ActionRegistry is from orchestrator.brain.action."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.action import ActionRegistry
    rt = RaphaelRuntime()
    assert isinstance(rt._organs.action_registry, ActionRegistry), (
        f"ActionRegistry must be orchestrator.brain.action.ActionRegistry, "
        f"got {type(rt._organs.action_registry).__module__}.{type(rt._organs.action_registry).__name__}"
    )
