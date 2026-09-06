"""
Scope v0 tests (§14.6): explicit, bounded, enforceable mission boundary.

Negative tests first (fail-closed), then positive integration, then
anti-bypass surface checks. The Broker remains the sole PDP; the PEP
remains the sole enforcement point. Scope only narrows.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime import (
    MissionContext,
    RaphaelRuntime,
    RuntimeContext,
)
from orchestrator.runtime.scope import ScopeError, ScopeV0


def _walking_skeleton_scope(**overrides):
    base = dict(
        mission_id="scope-test",
        targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",),
    )
    base.update(overrides)
    return ScopeV0(**base)


# ── Negative: missing / malformed scope fails closed ──────────────

def test_missing_scope_required_fails_closed_before_any_stage():
    """§14.6(7): require_scope with no declared scope terminates pre-stage."""
    rt = RaphaelRuntime()
    traces, term = rt.run_episode(
        MissionContext(mission_id="m", name="m", objectives=["inspect"]),
        require_scope=True,
    )
    assert term.terminated
    assert term.iterations == 0
    assert term.final_stage == "scope"
    assert "scope" in term.reason.lower()
    assert traces == []
    # No PEP execution occurred: zero traces, zero iterations.
    assert all(
        entry.get("stage") != "pep"
        for trace in traces
        for entry in trace.entries
    )


def test_non_scopev0_scope_object_fails_closed():
    """§14.6(7): duck-typed scope impostors are rejected, not accepted."""
    rt = RaphaelRuntime()
    mission = MissionContext(mission_id="m", name="m", objectives=["inspect"])
    mission.scope = {"mission_id": "m", "targets": ["*"]}
    traces, term = rt.run_episode(mission, require_scope=True)
    assert term.terminated
    assert term.iterations == 0
    assert term.final_stage == "scope"


def test_missing_mission_id_rejected():
    with pytest.raises(ScopeError):
        ScopeV0(
            mission_id="  ",
            targets=("10.0.0.0/24",),
            allowed_action_types=("scan",),
            allowed_capabilities=("nmap",),
        )


def test_empty_targets_rejected():
    """§14.6(2): a scope declaring no targets is malformed, not permissive."""
    with pytest.raises(ScopeError):
        ScopeV0(
            mission_id="m",
            targets=(),
            allowed_action_types=("scan",),
            allowed_capabilities=("nmap",),
        )


def test_malformed_entries_rejected():
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=("10.0.0.0/999",),
                allowed_action_types=("scan",), allowed_capabilities=("nmap",))
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=(42,),
                allowed_action_types=("scan",), allowed_capabilities=("nmap",))
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=("10.0.0.0/24",),
                allowed_action_types=("scan", "scan"),
                prohibited_action_types=("scan",),
                allowed_capabilities=("nmap",))
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=("10.0.0.0/24",),
                allowed_action_types=("scan",),
                allowed_capabilities=("nmap",), max_impact=-1.0)
    with pytest.raises(ScopeError):
        ScopeV0.from_dict({"mission_id": "m", "targets": ["*"], "nope": 1})
    with pytest.raises(ScopeError):
        ScopeV0.from_dict({"mission_id": "m"})


# ── Negative: out-of-scope operations rejected ────────────────────

def test_out_of_scope_target_rejected_after_broker_allow():
    """§14.6(6): broker-allowed but out-of-scope target fails at broker stage."""
    rt = RaphaelRuntime()  # bootstrap broker allows "*" targets
    scope = _walking_skeleton_scope(targets=("10.0.0.0/24",))
    ctx = RuntimeContext(
        mission_id="m", objective_id="inspect",
        view={"target": "10.99.99.99"}, scope=scope,
    )
    _, term = rt.step(ctx)
    assert term.terminated
    assert term.final_stage == "broker"
    assert "scope" in term.reason.lower()


def test_prohibited_capability_rejected():
    """§14.6(4): prohibited capability class denied even when broker allows.

    Overlap with the allowed list is itself malformed (contradiction),
    so a prohibited capability is rejected on both grounds.
    """
    with pytest.raises(ScopeError):
        _walking_skeleton_scope(prohibited_capabilities=("fixture.inspect",))
    scope = _walking_skeleton_scope(prohibited_capabilities=("nmap",))
    ok, reason = scope.covers(
        "system_info.name", "safe_proving_capability", "nmap"
    )
    assert not ok
    assert "prohibited" in reason


def test_unlisted_capability_rejected_at_runtime():
    """Capability outside the declared set fails at the broker stage."""
    rt = RaphaelRuntime()
    scope = _walking_skeleton_scope(allowed_capabilities=("other.inspect",))
    ctx = RuntimeContext(
        mission_id="m", objective_id="inspect",
        view={"target": "system_info.name"}, scope=scope,
    )
    _, term = rt.step(ctx)
    assert term.terminated
    assert term.final_stage == "broker"
    assert "scope" in term.reason.lower()


def test_prohibited_action_type_rejected():
    with pytest.raises(ScopeError):
        _walking_skeleton_scope(
            prohibited_action_types=("safe_proving_capability",),
        )
    scope = _walking_skeleton_scope(prohibited_action_types=("exploit",))
    ok, reason = scope.covers(
        "system_info.name", "exploit", "fixture.inspect"
    )
    assert not ok
    assert "prohibited" in reason


# ── Positive: in-scope succeeds; scope never authorizes ───────────

def test_valid_in_scope_declaration_succeeds():
    traces, term = RaphaelRuntime().run_episode(
        MissionContext(
            mission_id="scope-test", name="scope-test",
            objectives=["inspect"], scope=_walking_skeleton_scope(),
        )
    )
    assert term.terminated
    assert term.final_stage == "replan"
    stages = [e.get("stage") for t in traces for e in t.entries]
    assert "pep" in stages  # PEP still reached: scope did not replace it


def test_valid_scope_does_not_bypass_broker_denial():
    """§14.6: scope-valid + broker-denied => denied (scope is not allow)."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker

    deny_all = CapabilityBroker(BrokerPolicy(engagement_id="scope-test-deny"))
    rt = RaphaelRuntime(broker=deny_all)
    scope = ScopeV0(
        mission_id="scope-test",
        targets=("*",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",),
    )
    ctx = RuntimeContext(
        mission_id="m", objective_id="inspect",
        view={"target": "system_info.name"}, scope=scope,
    )
    trace, term = rt.step(ctx)
    assert term.terminated
    assert term.final_stage == "broker"
    assert "scope" not in term.reason.lower()  # broker denied, not scope
    assert "denied by real broker" in term.reason.lower()
    assert all(e.get("stage") != "pep" for e in trace.entries)


def test_scope_covers_is_deterministic_and_bounded():
    scope = _walking_skeleton_scope(targets=("10.0.0.0/24",))
    first = scope.covers("10.0.0.5", "safe_proving_capability", "fixture.inspect")
    assert first == scope.covers(
        "10.0.0.5", "safe_proving_capability", "fixture.inspect"
    )
    assert first[0] is True
    assert scope.covers(
        "10.0.1.5", "safe_proving_capability", "fixture.inspect"
    )[0] is False
    # Empty allow-lists deny rather than permit.
    narrow = ScopeV0(mission_id="m", targets=("*",))
    assert narrow.covers("x", "anything", "anything")[0] is False


def test_serialization_roundtrip_stable():
    scope = _walking_skeleton_scope()
    clone = ScopeV0.from_dict(scope.to_dict())
    assert clone == scope
    assert clone.scope_hash() == scope.scope_hash()
    other = _walking_skeleton_scope(targets=("*",))
    assert other.scope_hash() != scope.scope_hash()


# ── Scope cannot be widened by runtime mutation ───────────────────

def test_scope_immutable_after_validation():
    scope = _walking_skeleton_scope()
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.targets = ("*",)
    with pytest.raises(dataclasses.FrozenInstanceError):
        scope.mission_id = "attacker"
    assert not hasattr(scope.targets, "append")
    mutable = ["system_info.name"]
    scope2 = ScopeV0(
        mission_id="m", targets=mutable,
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    )
    mutable.append("*")  # post-construction mutation of the input: no effect
    assert scope2.targets == ("system_info.name",)
    assert scope2.covers("10.99.99.99", "safe_proving_capability",
                         "fixture.inspect")[0] is False


# ── Anti-bypass surface ───────────────────────────────────────────

def test_scope_module_is_pure_contract():
    """Scope performs no execution, issues no authorization, owns no path."""
    import ast

    tree = ast.parse((SRC_ROOT / "orchestrator" / "runtime" / "scope.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {
        "fnmatch", "hashlib", "ipaddress", "json", "dataclasses", "typing",
        "__future__",
    }, f"scope.py must stay stdlib-only, imports: {sorted(imported)}"
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for forbidden in ("execute", "inspect", "authorize", "approve", "emit",
                      "run", "record_authorization", "propose_action"):
        assert forbidden not in names, f"Scope must not define {forbidden}()"
    assert "ScopeV0" in {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def test_scope_does_not_touch_worldmodel_or_broker():
    scope = _walking_skeleton_scope()
    assert not hasattr(scope, "world_model")
    assert not hasattr(scope, "broker")
    assert not hasattr(scope, "receipt_store")


# ── max_impact enforcement (Option-B remediation) ───────────────────

def test_over_max_impact_denied():
    """Impact strictly above max_impact is denied with an impact reason."""
    scope = _walking_skeleton_scope(max_impact=0.0)
    ok, reason = scope.covers(
        "system_info.name", "safe_proving_capability", "fixture.inspect",
        impact_estimate=0.5,
    )
    assert ok is False
    assert reason == "Scope v0: impact exceeds declared max"


def test_exact_max_impact_allowed():
    """Impact exactly equal to max_impact is allowed (strict-greater denial)."""
    scope = _walking_skeleton_scope(max_impact=0.0)
    ok, _ = scope.covers(
        "system_info.name", "safe_proving_capability", "fixture.inspect",
        impact_estimate=0.0,
    )
    assert ok is True
    bounded = _walking_skeleton_scope(max_impact=1.0)
    ok, _ = bounded.covers(
        "system_info.name", "safe_proving_capability", "fixture.inspect",
        impact_estimate=1.0,
    )
    assert ok is True
    ok, _ = bounded.covers(
        "system_info.name", "safe_proving_capability", "fixture.inspect",
        impact_estimate=1.5,
    )
    assert ok is False


def test_stage_fails_closed_without_impact_estimate():
    """Stage-level estimate resolution: absent estimate denies, never 0.0-passes."""
    import types
    from orchestrator.brain.capability_broker import ActionProposalStatus
    from orchestrator.runtime.stages import stage_broker
    from orchestrator.runtime.types import ActionRequest

    receipt = types.SimpleNamespace(
        status=ActionProposalStatus.AUTHORIZED,
        action_id="act_stub",
        reason="stub allow",
        metadata={},  # no impact_estimate recorded: must fail closed
    )

    class _StubBroker:
        def propose_action(self, **kwargs):
            return receipt

    ctx = {
        "broker": _StubBroker(),
        "capability_name": "fixture.inspect",
        "planner_request": {
            "request": ActionRequest(
                action_type="safe_proving_capability",
                target="system_info.name",
            )
        },
        "scope": _walking_skeleton_scope(),
    }
    result = stage_broker(ctx)
    assert result.success is False
    assert "no impact estimate available" in (result.error or "")
