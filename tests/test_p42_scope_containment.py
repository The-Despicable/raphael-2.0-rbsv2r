"""
P4.2 declarative Scope containment tests (§15.2).

Proves the declarative containment model over the single canonical
evaluator: rules-as-data, machine-readable verdicts, per-dimension
semantics, fail-closed validation, and covers()/check() equivalence.
No second evaluator, no authority: Scope remains a constraint.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime.scope import ScopeContainment, ScopeError, ScopeRule, ScopeV0
from orchestrator.runtime.mission_spec import Scope


def _scope(**overrides):
    base = dict(
        mission_id="p42-test",
        targets=("system_info.name", "10.0.0.0/24", "*.example.com"),
        allowed_action_types=("safe_proving_capability",),
        prohibited_action_types=("reverse_shell",),
        allowed_capabilities=("fixture.inspect",),
        prohibited_capabilities=("shell.exec",),
        max_impact=0.0,
    )
    base.update(overrides)
    return ScopeV0(**base)


# ── Declarative rules as data ────────────────────────────

def test_rules_expose_declared_containment():
    scope = _scope()
    rules = scope.rules()
    assert isinstance(rules, tuple)
    assert all(isinstance(r, ScopeRule) for r in rules)
    # 3 targets + 1 prohibited action + 1 allowed action +
    # 1 prohibited cap + 1 allowed cap + 1 impact cap = 8 rules.
    assert len(rules) == 8
    by_origin = {}
    for r in rules:
        by_origin.setdefault(r.origin, []).append(r)
    assert [r.pattern for r in by_origin["targets"]] == [
        "system_info.name", "10.0.0.0/24", "*.example.com"]
    assert by_origin["prohibited_action_types"][0].effect == "deny"
    assert by_origin["allowed_action_types"][0].effect == "allow"
    assert by_origin["max_impact"][0].pattern == "0.0"
    assert by_origin["max_impact"][0].dimension == "impact"


def test_rules_are_frozen_data_without_authority():
    assert dataclasses.is_dataclass(ScopeRule)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ScopeRule(dimension="target", pattern="x", effect="allow",
                  origin="targets").effect = "deny"  # type: ignore[misc]
    assert not hasattr(ScopeRule, "covers")
    assert not hasattr(ScopeRule, "check")
    assert not hasattr(ScopeRule, "authorize")
    d = ScopeRule(dimension="target", pattern="h", effect="allow",
                  origin="targets", index=0).to_dict()
    assert d == {"dimension": "target", "pattern": "h", "effect": "allow",
                 "origin": "targets", "index": 0}


def test_canonical_scope_name_is_single_model():
    assert Scope is ScopeV0
    assert Scope("m", targets=("t",)).mission_id == "m"


# ── Verdict semantics per dimension ──────────────────────

def test_check_accepts_inside_scope_with_matched_rules():
    scope = _scope()
    v = scope.check("system_info.name", "safe_proving_capability", "fixture.inspect", 0.0)
    assert isinstance(v, ScopeContainment)
    assert v.allowed is True
    assert v.dimension == "impact"
    assert v.matched_rule is not None and v.matched_rule.origin == "max_impact"
    assert "inside declared scope" in v.reason


def test_check_target_exact_cidr_wildcard():
    scope = _scope()
    assert scope.check("system_info.name", "safe_proving_capability", "fixture.inspect").allowed is True
    assert scope.check("10.0.0.7", "safe_proving_capability", "fixture.inspect").allowed is True
    assert scope.check("web.example.com", "safe_proving_capability", "fixture.inspect").allowed is True
    v = scope.check("prod.db.internal", "safe_proving_capability", "fixture.inspect")
    assert v.allowed is False and v.dimension == "target"
    assert v.matched_rule is None
    assert "outside declared scope" in v.reason


def test_check_prohibited_wins_and_names_rule():
    scope = _scope()
    v = scope.check("system_info.name", "reverse_shell", "fixture.inspect")
    assert v.allowed is False and v.dimension == "action_type"
    assert v.matched_rule is not None
    assert v.matched_rule.effect == "deny"
    assert v.matched_rule.pattern == "reverse_shell"
    assert "explicitly prohibited" in v.reason
    v = scope.check("system_info.name", "safe_proving_capability", "shell.exec")
    assert v.allowed is False and v.dimension == "capability"
    assert v.matched_rule is not None and v.matched_rule.effect == "deny"


def test_check_unlisted_denied_and_empty_allowlist_denied():
    scope = _scope()
    v = scope.check("system_info.name", "port_scan", "fixture.inspect")
    assert v.allowed is False and v.dimension == "action_type"
    assert "not in declared scope" in v.reason
    v = scope.check("system_info.name", "safe_proving_capability", "nmap")
    assert v.allowed is False and v.dimension == "capability"
    bare = ScopeV0(mission_id="m", targets=("t",),
                   allowed_action_types=(), allowed_capabilities=())
    assert bare.check("t", "anything", "anything").dimension == "action_type"
    assert "empty allowed list" in bare.check("t", "anything", "anything").reason


def test_check_impact_boundary():
    scope = _scope(max_impact=5.0)
    assert scope.check("system_info.name", "safe_proving_capability", "fixture.inspect", 5.0).allowed is True
    v = scope.check("system_info.name", "safe_proving_capability", "fixture.inspect", 5.01)
    assert v.allowed is False and v.dimension == "impact"
    assert v.matched_rule is not None and v.matched_rule.origin == "max_impact"
    assert v.reason == "Scope v0: impact exceeds declared max"
    v = scope.check("system_info.name", "safe_proving_capability", "fixture.inspect", "high")
    assert v.allowed is False and v.reason == "Scope v0: malformed impact estimate"


def test_check_malformed_request_fail_closed():
    scope = _scope()
    for bad in ("", None, 123):
        v = scope.check(bad, "safe_proving_capability", "fixture.inspect")
        assert v.allowed is False and v.dimension == "request"
        assert v.matched_rule is None
        assert v.reason == "Scope v0: missing target"


def test_check_verdict_serializes():
    scope = _scope()
    d = scope.check("system_info.name", "safe_proving_capability", "fixture.inspect").to_dict()
    assert d["allowed"] is True
    assert d["matched_rule"]["origin"] == "max_impact"
    d = scope.check("nope", "safe_proving_capability", "fixture.inspect").to_dict()
    assert d["allowed"] is False and d["matched_rule"] is None


# ── One evaluator: covers()/check() equivalence ──────────

def test_covers_delegates_to_check_identically():
    scope = _scope()
    cases = [
        ("system_info.name", "safe_proving_capability", "fixture.inspect", 0.0),
        ("10.0.0.7", "safe_proving_capability", "fixture.inspect", 0.0),
        ("web.example.com", "safe_proving_capability", "fixture.inspect", 0.0),
        ("prod.db.internal", "safe_proving_capability", "fixture.inspect", 0.0),
        ("system_info.name", "reverse_shell", "fixture.inspect", 0.0),
        ("system_info.name", "port_scan", "fixture.inspect", 0.0),
        ("system_info.name", "safe_proving_capability", "shell.exec", 0.0),
        ("system_info.name", "safe_proving_capability", "nmap", 0.0),
        ("system_info.name", "safe_proving_capability", "fixture.inspect", 99.0),
        ("system_info.name", "safe_proving_capability", "fixture.inspect", "high"),
        ("", "safe_proving_capability", "fixture.inspect", 0.0),
    ]
    for target, action, cap, impact in cases:
        allowed, reason = scope.covers(target, action, cap, impact)
        verdict = scope.check(target, action, cap, impact)
        assert allowed == verdict.allowed, (target, action, cap, impact)
        assert reason == verdict.reason, (target, action, cap, impact)


def test_construction_conflicts_still_rejected():
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=("t",),
                allowed_action_types=("a",), prohibited_action_types=("a",))
    with pytest.raises(ScopeError):
        ScopeV0(mission_id="m", targets=())
    with pytest.raises(ScopeError):
        ScopeV0.from_dict({"mission_id": "m", "targets": ["t"], "nope": 1})


# ── Roadmap §15.3 scope tests ─────────────────────────────

def test_scope_rejects_out_of_mission():
    """§15.3: out-of-mission target denied with target dimension."""
    scope = _scope()
    v = scope.check("attacker.controlled", "safe_proving_capability", "fixture.inspect")
    assert v.allowed is False and v.dimension == "target"


def test_no_scope_capability_denied():
    """§15.3: unlisted capability denied with capability dimension."""
    scope = _scope()
    v = scope.check("system_info.name", "safe_proving_capability", "c2.beacon")
    assert v.allowed is False and v.dimension == "capability"
