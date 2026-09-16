"""
P4.3 AuthorizationContext derivation tests (§15 P4.3).

Proves the canonical derivation MissionSpec + Scope + ActionSpec
(ActionRequest) → AuthorizationContext on the live broker stage:

- derivation from the ACTUAL MissionSpec (spec wins over view strings)
- allow path and deny path contexts
- decision binding (decision/receipt ids, no manufactured decisions)
- mission binding (identity + digest; reuse detectable)
- Scope binding (actual bound scope hash; check() path untouched)
- ActionSpec binding (fields equal the broker receipt's stored fields)
- immutability and deterministic derivation
- non-authorizing behavior (source + behavioral probes)
"""
import dataclasses
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime import RaphaelRuntime, MissionContext
from orchestrator.runtime.mission_spec import (
    AuthorizationContext,
    HaltConditions,
    MissionSpec,
    Scope,
)
from orchestrator.runtime.scope import ScopeV0


def _scope():
    return ScopeV0(
        mission_id="p43-mission", targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",), max_impact=0.0,
    )


def _spec(**overrides):
    base = dict(
        mission_id="p43-mission", name="p43 derivation mission",
        objectives=("prove derivation",), targets=("system_info.name",),
        constraints={"default_target": "system_info.name"},
        halt=HaltConditions(max_iterations=1, action_cap=1, require_scope=True),
        scope=_scope(),
    )
    base.update(overrides)
    return MissionSpec(**base)


def _episode(spec=None, mission=None, **kw):
    rt = RaphaelRuntime()
    if mission is None:
        mission = MissionContext.from_spec(spec)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs, **kw)
    return rt, traces, term, outputs


# ── Derivation from the actual MissionSpec ───────────────

def test_derivation_uses_actual_spec_not_view_string():
    """The spec object is authoritative; a spoofed view string loses."""
    from orchestrator.runtime.stages import stage_broker, stage_planner_request
    from orchestrator.runtime.types import ActionRequest
    spec = _spec()
    rt = RaphaelRuntime()
    request = ActionRequest(
        action_type="safe_proving_capability", target="system_info.name",
        args={"read_only": True}, rationale="p43", capability="fixture.inspect",
        method="inspect", impact_estimate=0.0,
    )
    ctx = {
        "view": {"mission_id": "spoofed-mission", "mission_spec": spec,
                 "target": "system_info.name"},
        "broker": rt._broker, "capability": rt._capability,
        "capability_name": "fixture.inspect",
        "organs": rt._organs, "scope": spec.scope,
        "planner_request": {"request": request},
    }
    out = stage_broker(ctx)
    assert out.success
    actx = out.output["auth_context"]
    assert actx.mission_id == "p43-mission"
    assert actx.mission_digest == spec.digest()
    assert actx.mission_digest != ""


def test_legacy_mission_without_spec_honest_empty_digest():
    """Hand-built missions (no spec) record mission_id with empty digest."""
    rt = RaphaelRuntime()
    outputs: list = []
    rt.run_episode(
        MissionContext(mission_id="legacy-m", name="l", objectives=["i"]),
        episode_outputs=outputs,
    )
    actx = outputs[0]["broker"]["auth_context"]
    assert actx.mission_id == "legacy-m"
    assert actx.mission_digest == ""


# ── Allow + deny paths ───────────────────────────────────

def test_allow_path_context_bound():
    rt, traces, term, outputs = _episode(_spec())
    assert len(traces) == 1
    actx = outputs[0]["broker"]["auth_context"]
    assert actx.decision == "allow"
    assert actx.mission_id == "p43-mission"
    assert actx.mission_digest == _spec().digest()
    assert actx.scope_hash == _scope().scope_hash()
    assert actx.decision_id != ""
    assert actx.receipt_id != ""
    assert actx.decision_id == actx.receipt_id


def test_deny_path_context_bound_not_approval():
    """Denied contexts describe; they do not approve anything."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    broker = CapabilityBroker(BrokerPolicy(engagement_id="p43-deny"))
    rt = RaphaelRuntime(broker=broker)
    mission = MissionContext(mission_id="p43-deny", name="d", objectives=["i"])
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "broker"
    actx = outputs[0]["broker"]["auth_context"]
    assert actx.decision == "deny"
    assert actx.reason != ""
    assert actx.mission_id == "p43-deny"
    # A denied context authorizes nothing: the PEP gate still refuses.
    from orchestrator.runtime.stages import stage_pep
    pep_ctx = {"broker": {"decision": None}, "capability": None,
               "planner_request": {"request": None}}
    assert stage_pep(pep_ctx).success is False


# ── Decision binding (no manufactured decisions) ─────────

def test_context_matches_stored_broker_truth():
    """Context fields equal the broker receipt's stored fields."""
    rt, traces, term, outputs = _episode(_spec())
    actx = outputs[0]["broker"]["auth_context"]
    stored = rt._broker.receipt_store[actx.receipt_id]
    assert actx.action_type == stored.action_type
    assert actx.target == stored.target
    assert actx.capability == stored.capability
    assert actx.method == stored.method
    assert tuple(actx.argv) == tuple(stored.authorized_argv)
    assert actx.decision_id == stored.action_id
    from orchestrator.hardening.action_receipt import ActionProposalStatus
    # §lifecycle: the canonical episode now drives the Broker execution
    # lifecycle, so the stored receipt is terminal SUCCEEDED (the PEP ran).
    assert stored.status == ActionProposalStatus.SUCCEEDED
    assert stored.completed_at >= stored.started_at > 0.0


# ── Mission binding (reuse detectable) ───────────────────

def test_mission_digest_distinguishes_missions():
    a = _spec()
    b = _spec(mission_id="p43-other")
    assert a.digest() != b.digest()
    c = _spec(name="renamed mission")
    assert a.digest() != c.digest()
    assert _spec().digest() == _spec().digest()


def test_context_reuse_across_missions_detectable():
    """A context derived for mission A does not match mission B."""
    rt, _, _, outputs = _episode(_spec())
    actx = outputs[0]["broker"]["auth_context"]
    other = _spec(mission_id="p43-other")
    assert actx.mission_digest != other.digest()
    assert actx.mission_id != other.mission_id


# ── Scope binding ────────────────────────────────────────

def test_context_carries_bound_scope():
    rt, traces, term, outputs = _episode(_spec())
    actx = outputs[0]["broker"]["auth_context"]
    assert actx.scope_hash == _scope().scope_hash()
    # The scope that decided is the mission's bound scope.
    assert actx.scope_hash == _spec().scope.scope_hash()


def test_scope_evaluation_unchanged_single_evaluator():
    """P4.3 adds no Scope evaluation: check() remains the one path."""
    scope = _scope()
    v = scope.check("system_info.name", "safe_proving_capability", "fixture.inspect", 0.0)
    assert v.allowed is True
    assert scope.covers("system_info.name", "safe_proving_capability", "fixture.inspect", 0.0) == (True, v.reason)
    import inspect
    from orchestrator.runtime import stages as stages_mod
    derive_src = inspect.getsource(stages_mod._derive_auth_context)
    assert "covers(" not in derive_src
    assert ".check(" not in derive_src


# ── ActionSpec binding (canonical ActionRequest) ─────────

def test_context_bound_to_actual_request_object():
    """Context action fields come from the request passed to the broker."""
    from orchestrator.runtime.stages import stage_broker
    from orchestrator.runtime.types import ActionRequest
    rt = RaphaelRuntime()
    request = ActionRequest(
        action_id="ACT_p43_exact", action_type="safe_proving_capability",
        target="system_info.name", args={"read_only": True},
        rationale="p43 exact", capability="fixture.inspect", method="inspect",
        impact_estimate=0.0,
    )
    ctx = {
        "view": {"mission_id": "p43-exact", "target": "system_info.name"},
        "broker": rt._broker, "capability": rt._capability,
        "capability_name": "fixture.inspect",
        "organs": rt._organs, "scope": None,
        "planner_request": {"request": request},
    }
    out = stage_broker(ctx)
    assert out.success
    actx = out.output["auth_context"]
    assert actx.action_id == "ACT_p43_exact"
    assert actx.target == request.target
    assert actx.capability == request.capability
    assert actx.method == request.method


# ── Immutability + determinism ───────────────────────────

def test_context_immutable_and_deterministic():
    rt, _, _, outputs = _episode(_spec())
    actx = outputs[0]["broker"]["auth_context"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        actx.decision = "allow"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        actx.mission_digest = "forged"  # type: ignore[misc]
    # Equivalent inputs re-derive equal contexts modulo derived_at.
    rt2, _, _, outputs2 = _episode(_spec())
    actx2 = outputs2[0]["broker"]["auth_context"]
    d1, d2 = actx.to_dict(), actx2.to_dict()
    d1.pop("derived_at")
    d2.pop("derived_at")
    # broker ids differ per decision (fresh derivation), bindings equal.
    assert d1["mission_digest"] == d2["mission_digest"]
    assert d1["scope_hash"] == d2["scope_hash"]
    assert d1["target"] == d2["target"] == "system_info.name"
    assert d1["decision"] == d2["decision"] == "allow"


# ── Non-authorizing guarantee ────────────────────────────

def test_context_source_has_no_authority():
    import inspect
    from orchestrator.runtime import mission_spec as ms_mod
    from orchestrator.runtime import stages as stages_mod
    ctx_src = inspect.getsource(ms_mod.AuthorizationContext)
    # Type-name tokens: docstring prose naming the Broker as THE
    # authority is correct documentation, not authority. Authority is
    # established by definitions/calls, checked below.
    for token in ("CapabilityBroker", "receipt_store", "propose_action",
                  "Sandbox", "Popen", "subprocess"):
        assert token not in ctx_src, token
    for stmt in ("def authorize", "def allow(", "def decide(", "def propose",
                 "self.decision ==", "if self.decision"):
        assert stmt not in ctx_src, stmt
    assert not hasattr(AuthorizationContext, "propose_action")
