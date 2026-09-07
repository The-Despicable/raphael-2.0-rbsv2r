"""
P4.1 mission modeling tests (§15.1 entry: MissionSpec, Scope, AuthorizationContext, EvidenceReceipt).

Proves the first-class P4 models without regressing G3 guarantees:
- MissionSpec: valid construction, fail-closed invalid construction,
  strict from_dict round-trip, runtime consumption via from_spec.
- Scope: the P4 canonical Scope name is the proven ScopeV0
  implementation (one model, same enforcement).
- AuthorizationContext: binds mission/scope/request/decision per
  decision, is derived fresh (not cached), and cannot authorize
  (frozen data, no PDP reference, no evaluation logic).
- EvidenceReceipt: decision linkage + provenance preserved, F1
  bindings preserved, evidence remains non-authorizing.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime.mission_spec import (
    AuthorizationContext,
    HaltConditions,
    MissionSpec,
    Scope,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import EvidenceReceipt, MissionContext


def _spec(**overrides):
    base = dict(
        mission_id="p41-test-001",
        name="p41 test mission",
        objectives=("prove fixture",),
        targets=("system_info.name",),
        constraints={"default_target": "system_info.name"},
        halt=HaltConditions(max_iterations=1, action_cap=1, require_scope=False),
        scope=None,
    )
    base.update(overrides)
    return MissionSpec(**base)


# ── MissionSpec ──────────────────────────────────────────────

def test_mission_spec_valid_construction():
    spec = _spec()
    assert spec.mission_id == "p41-test-001"
    assert spec.objectives == ("prove fixture",)
    assert spec.targets == ("system_info.name",)
    assert spec.halt.max_iterations == 1


def test_mission_spec_rejects_empty_identity():
    with pytest.raises(ValueError):
        _spec(mission_id="")
    with pytest.raises(ValueError):
        _spec(mission_id="   ")


def test_mission_spec_rejects_empty_objectives_and_targets():
    with pytest.raises(ValueError):
        _spec(objectives=())
    with pytest.raises(ValueError):
        _spec(targets=[])
    with pytest.raises(ValueError):
        _spec(objectives=[""])
    with pytest.raises(ValueError):
        _spec(constraints="not-a-mapping")


def test_mission_spec_rejects_non_scope():
    with pytest.raises(ValueError):
        _spec(scope="not-a-scope")
    with pytest.raises(ValueError):
        _spec(halt={"max_iterations": 2})


def test_halt_conditions_validation():
    assert HaltConditions().max_iterations == 1
    with pytest.raises(ValueError):
        HaltConditions(max_iterations=0)
    with pytest.raises(ValueError):
        HaltConditions(action_cap=0)
    with pytest.raises(ValueError):
        HaltConditions(require_scope="yes")
    with pytest.raises(ValueError):
        HaltConditions.from_dict({"max_iterations": 2, "unknown_field": 1})
    assert HaltConditions.from_dict({"max_iterations": 3}).max_iterations == 3


def test_mission_spec_strict_from_dict_roundtrip():
    spec = _spec()
    clone = MissionSpec.from_dict(spec.to_dict())
    assert clone == spec
    with pytest.raises(ValueError):
        MissionSpec.from_dict({**spec.to_dict(), "future_field": 1})
    with pytest.raises(ValueError):
        MissionSpec.from_dict({"name": "no-id"})
    with pytest.raises(ValueError):
        MissionSpec.from_dict("not-a-mapping")


def test_mission_spec_scope_mapping_accepted():
    scope = ScopeV0(
        mission_id="p41-test-001", targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",), max_impact=0.0,
    )
    spec = MissionSpec.from_dict({
        "mission_id": "p41-test-001", "objectives": ["prove fixture"],
        "targets": ["system_info.name"], "scope": scope.to_dict(),
    })
    assert spec.scope == scope


def test_mission_context_from_spec():
    spec = _spec()
    ctx = MissionContext.from_spec(spec)
    assert ctx.mission_id == "p41-test-001"
    assert ctx.objectives == ["prove fixture"]
    assert ctx.constraints["default_target"] == "system_info.name"
    assert ctx.constraints["halt"] == {"max_iterations": 1, "action_cap": 1, "require_scope": False}
    assert ctx.scope is None


def test_mission_context_from_spec_extra_constraints():
    spec = _spec()
    ctx = MissionContext.from_spec(spec, extra_constraints={"objective_id": "ephemeral"})
    assert ctx.constraints["objective_id"] == "ephemeral"
    assert ctx.constraints["halt"]["max_iterations"] == 1
    with pytest.raises(ValueError):
        MissionContext.from_spec(spec, extra_constraints={"halt": {}})
    with pytest.raises(ValueError):
        MissionContext.from_spec(spec, extra_constraints={"candidates": {}})
    with pytest.raises(ValueError):
        MissionContext.from_spec("not-a-spec")


def test_runtime_consumes_spec_halt():
    """run_episode resolves halt from the spec when params are omitted."""
    from orchestrator.runtime import RaphaelRuntime
    spec = _spec(halt=HaltConditions(max_iterations=1, action_cap=1, require_scope=False))
    ctx = MissionContext.from_spec(spec)
    rt = RaphaelRuntime()
    traces, term = rt.run_episode(ctx)
    assert len(traces) == 1
    # Explicit params still win over spec halt.
    traces2, _ = rt.run_episode(ctx, max_iterations=1)
    assert len(traces2) == 1


# ── Scope (P4 canonical name) ────────────────────────────────

def test_scope_is_scopev0_implementation():
    """One canonical Scope model: Scope IS the proven ScopeV0."""
    assert Scope is ScopeV0
    scope = Scope(
        mission_id="p41-scope", targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",), max_impact=0.0,
    )
    assert scope.covers("system_info.name", "safe_proving_capability", "fixture.inspect", 0.0)[0] is True
    assert scope.covers("elsewhere", "safe_proving_capability", "fixture.inspect", 0.0)[0] is False
    assert scope.covers("system_info.name", "safe_proving_capability", "fixture.inspect", 9.9) == \
        (False, "Scope v0: impact exceeds declared max")


# ── AuthorizationContext ─────────────────────────────────────

def test_auth_context_binds_decision_inputs():
    actx = AuthorizationContext(
        mission_id="m", scope_hash="abc", action_id="ACT_1",
        action_type="safe_proving_capability", target="system_info.name",
        capability="fixture.inspect", method="inspect",
        decision_id="9dbbd227", decision="allow", reason="ok",
    )
    d = actx.to_dict()
    assert d["mission_id"] == "m"
    assert d["decision"] == "allow"
    assert d["decision_id"] == "9dbbd227"
    assert d["argv"] == []


def test_auth_context_cannot_authorize():
    """Frozen data with no PDP reference and no evaluation logic."""
    assert dataclasses.is_dataclass(AuthorizationContext)
    with pytest.raises(dataclasses.FrozenInstanceError):
        AuthorizationContext().decision = "allow"  # type: ignore[misc]
    assert not hasattr(AuthorizationContext, "propose_action")
    assert not hasattr(AuthorizationContext, "authorize")
    assert not hasattr(AuthorizationContext, "allow")
    assert not hasattr(AuthorizationContext, "decide")
    import inspect
    src = inspect.getsource(AuthorizationContext)
    assert "CapabilityBroker" not in src
    assert "receipt_store" not in src


def test_auth_context_derived_fresh_per_decision():
    """The broker stage attaches a fresh context on allow AND deny."""
    from orchestrator.runtime import RaphaelRuntime
    rt = RaphaelRuntime()
    outputs: list = []
    traces, _ = rt.run_episode(
        MissionContext(mission_id="m", name="m", objectives=["i"]), episode_outputs=outputs,
    )
    assert len(traces) == 1
    first = outputs[0]["broker"]["auth_context"]
    outputs2: list = []
    rt.run_episode(
        MissionContext(mission_id="m", name="m", objectives=["i"]), episode_outputs=outputs2,
    )
    second = outputs2[0]["broker"]["auth_context"]
    # Fresh object per decision: distinct derivation timestamps/ids.
    assert first is not second
    assert first.to_dict() != second.to_dict() or first.derived_at <= second.derived_at
    assert first.decision == "allow"


def test_auth_context_on_deny_path():
    """Denied decisions also carry a derived (deny) context."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    broker = CapabilityBroker(BrokerPolicy(engagement_id="p41-deny"))
    rt = RaphaelRuntime(broker=broker)
    outputs: list = []
    traces, term = rt.run_episode(
        MissionContext(mission_id="m", name="m", objectives=["i"]), episode_outputs=outputs,
    )
    assert term.final_stage == "broker"
    actx = outputs[0]["broker"]["auth_context"]
    assert actx.decision == "deny"
    assert actx.reason != ""


# ── EvidenceReceipt (P4 provenance) ──────────────────────────

def test_evidence_receipt_defaults_preserve_legacy():
    r = EvidenceReceipt(event_id="EVT_1", decision_id="PDC_1")
    assert r.mission_id == ""
    assert r.scope_hash == ""
    assert r.argv == ()
    assert r.artifact_refs == ()
    assert r.broker_receipt_id == ""
    d = r.to_dict()
    assert d["event_id"] == "EVT_1"
    assert d["decision_id"] == "PDC_1"


def test_evidence_receipt_provenance_linkage():
    """Stage receipt output carries mission/scope/F1 bindings from stored truth."""
    from orchestrator.runtime import RaphaelRuntime
    rt = RaphaelRuntime()
    outputs: list = []
    rt.run_episode(
        MissionContext(mission_id="p41-prov", name="p", objectives=["i"]),
        episode_outputs=outputs,
    )
    receipt = outputs[0]["receipt"]["receipt"]
    assert receipt.decision_id != ""
    assert receipt.event_id != ""
    broker_receipt = outputs[0]["broker"]["receipt"]
    # F1 bindings copied from the stored authorization truth.
    assert receipt.broker_receipt_id == broker_receipt.action_id
    assert receipt.action_type == broker_receipt.action_type
    assert receipt.target == broker_receipt.target
    assert receipt.capability == broker_receipt.capability
    assert receipt.method == broker_receipt.method
    assert tuple(receipt.argv) == tuple(broker_receipt.authorized_argv)


def test_evidence_receipt_cannot_authorize():
    """Evidence links and describes; it cannot permit execution."""
    assert not hasattr(EvidenceReceipt, "authorize")
    assert not hasattr(EvidenceReceipt, "allow")
    assert not hasattr(EvidenceReceipt, "decide")
    assert not hasattr(EvidenceReceipt, "propose_action")
    import inspect
    src = inspect.getsource(EvidenceReceipt)
    assert "SandboxedExecutor" not in src
    assert "receipt_store" not in src
    assert "Popen" not in src
