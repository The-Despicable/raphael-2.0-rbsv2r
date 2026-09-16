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


def test_scope_denies_out_of_scope_action():
    """§14.3 / §14.9: a Broker-allowed action outside the declared Scope is
    denied at the broker stage and never reaches the PEP."""
    rt = RaphaelRuntime()  # bootstrap broker allows "*" targets
    scope = _walking_skeleton_scope(targets=("system_info.name",))
    ctx = RuntimeContext(
        mission_id="scope-denies", objective_id="inspect",
        view={"target": "out.of.scope.example"}, scope=scope,
    )
    outputs: dict = {}
    trace, term = rt.step(ctx, stage_outputs=outputs)

    assert term.terminated
    assert term.final_stage == "broker"
    assert "outside declared scope" in term.reason
    # Negative path: no execution event, no capability invocation.
    assert "pep" not in {e["stage"] for e in trace.entries}
    assert rt._capability.invocation_count == 0
    assert "pep" not in outputs


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


# ── Real impact data flow: candidate -> Broker -> Scope ─────────────

def _impact_mission(candidate, scope, mission_id="impact-flow"):
    return MissionContext(
        mission_id=mission_id, name=mission_id, objectives=["inspect"],
        constraints={
            "candidates": {"0": [candidate]},
            "default_target": "system_info.name",
            "objective_id": "impact-objective",
        },
        scope=scope,
    )


def _impact_candidate(**overrides):
    base = dict(
        action_id="impact-cand-001",
        action_type="safe_proving_capability",
        target="system_info.name",
        capability="fixture.inspect",
        method="inspect",
        args={"read_only": True},
        rationale="impact flow probe",
        confidence=1.0,
        impact_estimate=0.0,
    )
    base.update(overrides)
    return base


def _impact_broker(max_impact_per_action):
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker

    return CapabilityBroker(BrokerPolicy(
        engagement_id="impact-flow",
        allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
        max_impact_per_action=max_impact_per_action,
    ))


def test_candidate_impact_over_scope_max_denied_before_pep():
    """The real candidate impact reaches Scope: 9.9 > max_impact=0.0 denied."""
    rt = RaphaelRuntime(broker=_impact_broker(10.0))
    scope = _walking_skeleton_scope(max_impact=0.0)
    mission = _impact_mission(_impact_candidate(impact_estimate=9.9), scope)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "broker"
    assert "impact exceeds declared max" in term.reason
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}
    # The staged decision records the actual estimate, not 0.0.
    decision = outputs[0]["broker"]["decision"]
    stored = rt._broker.receipt_store[decision.decision_id]
    assert stored.metadata["impact_estimate"] == 9.9
    assert outputs[0]["broker"]["auth_context"].impact_estimate == 9.9


def test_candidate_impact_equal_scope_max_allowed_and_recorded():
    """impact == max_impact stays allowed; the receipt records the real value."""
    rt = RaphaelRuntime(broker=_impact_broker(0.5))
    scope = _walking_skeleton_scope(max_impact=0.5)
    mission = _impact_mission(_impact_candidate(impact_estimate=0.5), scope)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "replan"
    assert rt._capability.invocation_count == 1
    assert "pep" in {e["stage"] for e in traces[0].entries}
    receipt = outputs[0]["broker"]["receipt"]
    assert receipt.metadata["impact_estimate"] == 0.5
    assert receipt.metadata["impact_estimate"] != 0.0


def test_candidate_missing_impact_fails_closed_before_pep():
    """A candidate with no impact estimate fails closed (never 0.0-passes)."""
    rt = RaphaelRuntime()
    scope = _walking_skeleton_scope(max_impact=0.0)
    candidate = _impact_candidate()
    candidate.pop("impact_estimate")
    mission = _impact_mission(candidate, scope)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "broker"
    assert "no impact estimate available" in term.reason
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}


def test_candidate_invalid_impact_fails_closed_before_pep():
    """A non-numeric impact estimate fails closed (no fabricated value)."""
    rt = RaphaelRuntime()
    scope = _walking_skeleton_scope(max_impact=0.0)
    mission = _impact_mission(_impact_candidate(impact_estimate="high"), scope)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "broker"
    assert "malformed impact estimate" in term.reason
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}


def test_regression_impact_9_9_max_impact_0_never_executes():
    """R-1 regression: candidate impact 9.9 with max_impact=0.0 must not run."""
    rt = RaphaelRuntime()  # bootstrap broker: max_impact_per_action=0.0
    scope = _walking_skeleton_scope(max_impact=0.0)
    mission = _impact_mission(_impact_candidate(impact_estimate=9.9), scope)
    outputs: list = []
    traces, term = rt.run_episode(mission, episode_outputs=outputs)
    assert term.final_stage == "broker"
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}
    decision = outputs[0]["broker"]["decision"]
    assert decision.decision == "deny"
    stored = rt._broker.receipt_store[decision.decision_id]
    assert stored.metadata["impact_estimate"] == 9.9


# ── Production CLI Scope binding + capability dimension (F-3) ────────

def test_production_cli_builds_scope_for_target():
    """The CLI canonical mission builder binds a ScopeV0 for the target."""
    from raphael import main as cli

    mission = cli._canonical_mission("cli-target.example")
    assert mission.scope is not None
    assert mission.scope.targets == ("cli-target.example",)
    assert mission.scope.allowed_action_types == ("safe_proving_capability",)
    assert mission.scope.allowed_capabilities == ("fixture.inspect",)
    assert mission.constraints.get("default_target") == "cli-target.example"


def test_production_cli_execution_has_non_none_scope(monkeypatch, capsys, tmp_path):
    """The real production entry runs with a bound Scope (not scope-less)."""
    import asyncio
    import raphael.main as cli

    monkeypatch.setenv("RAPHAEL_EVIDENCE_DIR", str(tmp_path))

    captured: dict = {}
    real_run = RaphaelRuntime.run_episode

    def spy(self, mission, **kwargs):
        captured["mission"] = mission
        captured["kwargs"] = kwargs
        return real_run(self, mission, **kwargs)

    monkeypatch.setattr(RaphaelRuntime, "run_episode", spy)
    monkeypatch.delenv("RAPHAEL_USE_LEGACY", raising=False)
    monkeypatch.setattr(sys, "argv", ["raphael", "cli-target.example"])

    asyncio.run(cli.main())

    mission = captured["mission"]
    assert mission.scope is not None
    assert mission.scope.targets == ("cli-target.example",)
    assert captured["kwargs"].get("require_scope") is True
    # All 10 stages ran: the scoped CLI execution was not denied.
    assert "Runtime trace: 10 stages" in capsys.readouterr().out


def test_run_episode_out_of_scope_target_denied_before_pep():
    """A non-None Scope denies an out-of-scope target before any PEP."""
    rt = RaphaelRuntime()
    scope = _walking_skeleton_scope(targets=("system_info.name",))
    mission = MissionContext(
        mission_id="scope-oos", name="scope-oos", objectives=["inspect"],
        constraints={"default_target": "out.of.scope.example"},
        scope=scope,
    )
    outputs: list = []
    traces, term = rt.run_episode(mission, require_scope=True, episode_outputs=outputs)
    assert term.final_stage == "broker"
    assert "outside declared scope" in term.reason
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}


def test_run_episode_allowed_target_reaches_pep():
    """An in-scope target with the canonical capability proceeds to PEP."""
    rt = RaphaelRuntime()
    scope = _walking_skeleton_scope(targets=("system_info.name",))
    mission = MissionContext(
        mission_id="scope-in", name="scope-in", objectives=["inspect"],
        constraints={"default_target": "system_info.name"},
        scope=scope,
    )
    traces, term = rt.run_episode(mission, require_scope=True)
    assert term.final_stage == "replan"
    assert rt._capability.invocation_count == 1
    assert "pep" in {e["stage"] for e in traces[0].entries}


def test_scope_capability_uses_request_capability_not_context_default():
    """A request-capability mismatch is denied even when fixture.inspect is
    allowed by the Scope and by the context capability_name."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    from orchestrator.runtime.stages import stage_broker
    from orchestrator.runtime.types import ActionRequest

    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="cap-dim",
        allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["other.inspect"],
    ))
    scope = _walking_skeleton_scope()  # allows only "fixture.inspect"
    request = ActionRequest(
        action_type="safe_proving_capability", target="system_info.name",
        capability="other.inspect", method="inspect", impact_estimate=0.0,
    )
    ctx = {
        "broker": broker,
        "capability_name": "fixture.inspect",
        "planner_request": {"request": request},
        "scope": scope,
    }
    out = stage_broker(ctx)
    assert out.success is False
    assert "capability not in declared scope" in (out.error or "")


def test_scope_capability_allows_matching_request_capability():
    """The same stage allows the request capability that the Scope permits."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    from orchestrator.runtime.stages import stage_broker
    from orchestrator.runtime.types import ActionRequest

    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="cap-dim-ok",
        allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    scope = _walking_skeleton_scope()
    request = ActionRequest(
        action_type="safe_proving_capability", target="system_info.name",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
    )
    ctx = {
        "broker": broker,
        "capability_name": "wrong.context.default",
        "planner_request": {"request": request},
        "scope": scope,
    }
    out = stage_broker(ctx)
    assert out.success is True
