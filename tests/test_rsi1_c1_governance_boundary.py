"""test_rsi1_c1_governance_boundary.py — RSI-1 C-1 remediation (2026-10-07).

Closes the two execution-boundary escapes the final independent RSI-1 audit
found after the B-1 remediation:

ESCAPE 1 — capability substitution/aliasing. Governance was bound to
capability NAME strings (policy vocabulary, dispatch-registry keys), both
caller-controlled through the public RaphaelRuntime constructor. A protected
capability object exposed under an innocuous alias executed 25 times (real
``docker exec … nmap`` spawns) under a neutral policy with a declared budget
of 64. C-1 binds governance to the concrete capability TYPE via the
exec-owned exact mapping (orchestrator/exec/capability_governance.py):
aliasing, re-labelling, subclass metadata tampering, and post-construction
registry edits cannot strip protection.

ESCAPE 2 — direct stage_pep with a hand-built context. Both PEP gates were
conditional on context-key presence, so omitting ``capability_governance``
and ``governed_step_budget`` — or substituting fresh objects each call —
skipped them (12 executions). Authority is now REQUIRED and identity-bound:
the Runtime binds exactly one governance decision and one episode budget to
the Broker; stage_pep refuses absent, forged, or substituted authority
BEFORE ``broker.start_execution()``. Missing authority is a refusal, never
"no gate".

Boundary instrumentation: every adversarial case asserts receipt lifecycle
states from the live Broker receipt store — zero STARTED, zero SUCCEEDED,
zero capability invocations on refusal paths. All adversarial brokers run
with the rate limiter explicitly absent (None) so the tests prove
governance, not the limiter.

Hermetic: injected runners/inspectors; tmp_path stores; no docker, no
subprocess, no network.
"""
from collections import Counter

import pytest

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.capability_governance import governed_capability_identity
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.exec.safe_capability import SafeProvingCapability
from orchestrator.runtime import stages as stages_mod
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.stages import STAGE_PEP, stage_pep
from orchestrator.runtime.types import (
    CapabilityGovernance,
    GovernedStepBudget,
    MissionContext,
    RuntimeContext,
    resolve_capability_governance,
)

CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
ALIAS_A = "exec.lab_probe_alias"
ALIAS_B = "exec.http_probe_alias"
D2_ENG = "d2-bounded-episode"
D1_ENG = "d1-governed-action"

FAKE_NMAP = ("Starting Nmap 7.99\nNmap scan report for dvwa (172.19.0.4)\n"
             "PORT   STATE SERVICE\n80/tcp open  http\n")
FAKE_CURL = ("<html>login redirect</html>\n302|text/html|28|0.01|http://dvwa/login.php\n")


def _runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def _runner_b(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_CURL, ""
    return P()


def _inspector(container):
    net = "raphael-m1_raphael-net"
    images = {"dvwa": "vulnerables/web-dvwa:stable",
              "kali-tools": "raphael/kali-tools:latest"}
    assert container in images, container
    return {"State": {"Running": True},
            "Config": {"Image": images[container]},
            "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}


def _caps(tmp_path, broker):
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                 runner=_runner_a, inspector=_inspector)
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                   runner=_runner_b, inspector=_inspector)
    return cap_a, cap_b


def _runtime(tmp_path, broker, default_capability, registry=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(str(tmp_path / "evidence_store.jsonl"))
    return RaphaelRuntime(
        broker=broker,
        capability=default_capability,
        organs=OrganBundle(evidence_store=store),
        capability_registry=registry,
    )


def _manual_d2_broker(cap=64):
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id=D2_ENG, policy_name="engagement-d2-v1",
        allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe", "lab_http_probe"],
        allowed_capabilities=[CAP_A, CAP_B],
        max_impact_per_action=2.0, max_episode_steps=cap))
    assert broker.rate_limiter is None, "adversarial cases isolate governance from the limiter"
    return broker


def _neutral_broker(cap=64, capabilities=(ALIAS_A,)):
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="neutral", policy_name="neutral-policy",
        allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe", "lab_http_probe"],
        allowed_capabilities=list(capabilities),
        max_impact_per_action=2.0, max_episode_steps=cap))
    assert broker.rate_limiter is None, "adversarial cases isolate governance from the limiter"
    return broker


def _manual_d1_broker():
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id=D1_ENG, policy_name="engagement-d1-v1",
        allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe"],
        allowed_capabilities=[CAP_A],
        max_impact_per_action=2.0, max_episode_steps=0))
    assert broker.rate_limiter is None
    return broker


def _cand(action_id, action_type, capability, method):
    return {"action_id": action_id, "action_type": action_type, "target": "dvwa",
            "capability": capability, "method": method, "impact_estimate": 2.0,
            "args": {"bounded": True}, "rationale": "c1 adversarial test"}


def _mission(capability_name, action_type="recon_service_probe", method="nmap",
             max_it=9, mission_id="c1-episode"):
    scope = ScopeV0(mission_id=mission_id, targets=("dvwa",),
                    allowed_action_types=(action_type,),
                    allowed_capabilities=(capability_name,), max_impact=2.0)
    return MissionContext(
        mission_id=mission_id, name="c1", objectives=["governed probe"],
        scope=scope,
        constraints={
            "halt": {"max_iterations": max_it, "action_cap": 1, "require_scope": True},
            "candidates": {str(i): [_cand(f"ACT-{i}", action_type, capability_name, method)]
                           for i in range(max_it)},
            "default_target": "dvwa",
            "objective": {"requires_evidence": [f"ACT-NEVER-{i}" for i in range(max_it)]},
        })


def _receipt_lifecycle(broker) -> Counter:
    """Receipt lifecycle states from the LIVE Broker receipt store."""
    counts: Counter = Counter()
    for receipt in broker.receipt_store.values():
        status = getattr(receipt, "status", None)
        counts[getattr(status, "name", str(status))] += 1
    return counts


def _instrument_start_execution(broker):
    """Count broker.start_execution calls — the exact boundary a refusal must
    precede. A refusal case must show zero calls; a governed case exactly N."""
    calls = []
    real_start = broker.start_execution

    def counting_start(receipt):
        calls.append(receipt)
        return real_start(receipt)

    broker.start_execution = counting_start
    return calls


def _step_loop(runtime, n, mission_id, capability=CAP_A):
    scope = ScopeV0(mission_id=mission_id, targets=("dvwa",),
                    allowed_action_types=("recon_service_probe",),
                    allowed_capabilities=(capability,), max_impact=2.0)
    for i in range(n):
        view = {"mission_name": "c1", "mission_id": mission_id, "iteration": i,
                "target": "dvwa", "objective_id": "o",
                "candidates": [_cand(f"ACT-{i}", "recon_service_probe", capability, "nmap")]}
        runtime.step(RuntimeContext(mission_id=mission_id, objective_id="o",
                                    view=view, iteration=i, scope=scope))


def _capture_authorized_pep_ctx(tmp_path, monkeypatch, broker, cap_a, cap_b=None):
    """One real iteration; capture the PEP stage context BEFORE the PEP
    enforces (the wrapper returns a failure without running the real PEP, so
    the receipt stays AUTHORIZED and never started)."""
    registry = {CAP_A: cap_a}
    if cap_b is not None:
        registry[CAP_B] = cap_b
    runtime = _runtime(tmp_path, broker, cap_a, registry=registry)
    captured = {}

    def capturing_pep(ctx):
        if "planner_request" not in captured:
            for key in ("broker", "capability", "capability_registry", "scope",
                        "evidence_store", "view", "artifact_roots", "organs",
                        "planner_request", "capability_governance",
                        "governed_step_budget"):
                captured[key] = ctx.get(key)
        return stages_mod.StageResult.make(
            stage_name=STAGE_PEP, success=False,
            error="captured before PEP enforcement")

    monkeypatch.setitem(stages_mod.STAGE_HANDLERS, STAGE_PEP, capturing_pep)
    runtime.run_episode(_mission(CAP_A, "recon_service_probe", "nmap",
                                 max_it=1, mission_id="c1-capture"))
    assert captured.get("planner_request") is not None, "episode never reached the PEP"
    assert captured.get("broker") is not None
    return dict(captured)


# ══════════════════════════════════════════════════════════════════════════
# Governance identity: exact, exec-owned, tamper-resistant
# ══════════════════════════════════════════════════════════════════════════

def test_identity_exact_types(tmp_path):
    broker = _neutral_broker()
    cap_a, cap_b = _caps(tmp_path, broker)
    assert governed_capability_identity(cap_a) == frozenset({CAP_A})
    assert governed_capability_identity(cap_b) == frozenset({CAP_B})
    assert governed_capability_identity(SafeProvingCapability(broker=broker)) == frozenset()
    assert governed_capability_identity(None) == frozenset()


def test_identity_attr_override_on_exact_type(tmp_path):
    """Instance-attribute tampering cannot strip a protected type's identity."""
    broker = _neutral_broker()
    cap_a, _cap_b = _caps(tmp_path, broker)
    cap_a.__dict__["CANONICAL_GOVERNED_CAPABILITIES"] = frozenset()
    assert governed_capability_identity(cap_a) == frozenset({CAP_A})


class _StealthyProbe(D1LabProbeCapability):
    """A subclass attempting to shed its governance identity."""

    CANONICAL_GOVERNED_CAPABILITIES = frozenset()


def test_identity_subclass_stays_governed(tmp_path):
    broker = _neutral_broker()
    stealthy = _StealthyProbe(broker=broker)
    assert governed_capability_identity(stealthy) == frozenset({CAP_A})


def test_identity_unknown_types_cannot_claim_or_shed_protection():
    class FakeProbe:
        CANONICAL_GOVERNED_CAPABILITIES = frozenset({CAP_A})

    # A lookalike type is NOT in the exec-owned mapping: it resolves empty.
    # It cannot claim protection, and — critically — a REAL protected
    # capability cannot shed protection through any attribute it owns.
    assert governed_capability_identity(FakeProbe()) == frozenset()


# ══════════════════════════════════════════════════════════════════════════
# ESCAPE 1 — capability substitution / aliasing
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("alias", [ALIAS_A, "probe", "fixture.recon"])
def test_a_alias_registered_protected_object_refused(tmp_path, alias):
    """ESCAPE 1 exact repro: D1LabProbeCapability under an innocuous alias,
    neutral policy, declared cap 64, rate limiter off → 0 capability calls,
    0 STARTED, 0 SUCCEEDED."""
    broker = _neutral_broker(cap=64, capabilities=(alias,))
    cap_a, _cap_b = _caps(tmp_path, broker)
    runtime = _runtime(tmp_path / "rt", broker, cap_a, registry={alias: cap_a})
    assert broker.rate_limiter is None
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(alias, "recon_service_probe", "nmap", max_it=9))
    assert cap_a.invocation_count == 0
    assert starts == [], "the refusal must precede broker.start_execution()"
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0
    assert lifecycle["SUCCEEDED"] == 0
    assert lifecycle["AUTHORIZED"] >= 1, "authorization-only receipts must never start"
    assert term.governance_refuses_protected is True
    assert term.final_stage == "pep"


def test_a2_direct_capability_injection_no_registry(tmp_path):
    """CONFIRM 2: a protected object as the bare default capability (no
    registry at all) under a neutral policy → 0 executions."""
    broker = _neutral_broker(cap=64, capabilities=(ALIAS_A,))
    cap_a, _cap_b = _caps(tmp_path, broker)
    runtime = _runtime(tmp_path / "rt", broker, cap_a, registry=None)
    assert runtime._governance.refuses_protected_capability is True
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(ALIAS_A, "recon_service_probe", "nmap", max_it=6))
    assert cap_a.invocation_count == 0
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert term.governance_refuses_protected is True


def test_a3_http_capability_alias_refused(tmp_path):
    """CONFIRM 4: LabHttpProbeCapability aliased under a neutral policy."""
    broker = _neutral_broker(cap=64, capabilities=(ALIAS_B,))
    _cap_a, cap_b = _caps(tmp_path, broker)
    runtime = _runtime(tmp_path / "rt", broker, cap_b, registry={ALIAS_B: cap_b})
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(ALIAS_B, "lab_http_probe", "curl", max_it=6))
    assert cap_b.invocation_count == 0
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert term.governance_refuses_protected is True


def test_a4_alias_injected_after_construction_still_refused(tmp_path):
    """An alias added to the registry AFTER Runtime construction must remain
    governed: the PEP derives protection from the OBJECT at call time."""
    broker = _neutral_broker(cap=64, capabilities=(ALIAS_A,))
    cap_a, _cap_b = _caps(tmp_path, broker)
    runtime = _runtime(tmp_path / "rt", broker, SafeProvingCapability(broker=broker),
                       registry=None)
    runtime._capability_registry[ALIAS_A] = cap_a  # post-construction injection
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(ALIAS_A, "recon_service_probe", "nmap", max_it=4))
    assert cap_a.invocation_count == 0
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0


def test_a5_subclass_alias_still_governed(tmp_path):
    """A subclass of a governed type stays governed (MRO); subclass metadata
    stripped of the identity cannot buy the legacy unbounded budget path."""
    broker = _neutral_broker(cap=64, capabilities=(ALIAS_A,))
    stealthy = _StealthyProbe(broker=broker, artifacts_dir=tmp_path / "artifacts",
                              runner=_runner_a, inspector=_inspector)
    runtime = _runtime(tmp_path / "rt", broker, stealthy, registry={ALIAS_A: stealthy})
    assert governed_capability_identity(stealthy) == frozenset({CAP_A})
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(ALIAS_A, "recon_service_probe", "nmap", max_it=6))
    assert stealthy.invocation_count == 0
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert term.governance_refuses_protected is True


# ══════════════════════════════════════════════════════════════════════════
# ESCAPE 2 — direct stage_pep with hand-built / untrusted contexts
# ══════════════════════════════════════════════════════════════════════════

def test_e_missing_capability_governance_refuses(tmp_path, monkeypatch):
    """A direct stage_pep call whose context omits capability_governance is
    REFUSED before start_execution: missing authority is a refusal."""
    broker = _manual_d2_broker(cap=64)
    cap_a, cap_b = _caps(tmp_path / "e", broker)
    ctx = _capture_authorized_pep_ctx(tmp_path / "e", monkeypatch, broker, cap_a, cap_b)
    assert ctx["capability_governance"] is not None
    untrusted = dict(ctx)
    untrusted.pop("capability_governance")
    starts = _instrument_start_execution(broker)
    out = stage_pep(untrusted)
    assert out.success is False
    assert out.output.get("governance_authority_refused") is True
    assert out.output.get("authority_missing") == "capability_governance"
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert cap_a.invocation_count == 0


def test_f_missing_governed_step_budget_refuses(tmp_path, monkeypatch):
    """A direct stage_pep call whose context omits the governed-step budget
    authority is REFUSED before start_execution."""
    broker = _manual_d2_broker(cap=64)
    cap_a, cap_b = _caps(tmp_path / "f", broker)
    ctx = _capture_authorized_pep_ctx(tmp_path / "f", monkeypatch, broker, cap_a, cap_b)
    assert ctx["governed_step_budget"] is not None
    untrusted = dict(ctx)
    untrusted.pop("governed_step_budget")
    starts = _instrument_start_execution(broker)
    out = stage_pep(untrusted)
    assert out.success is False
    assert out.output.get("governance_authority_refused") is True
    assert out.output.get("authority_missing") == "governed_step_budget"
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert cap_a.invocation_count == 0


def test_g_replacement_fresh_budget_refused(tmp_path, monkeypatch):
    """A DIFFERENT budget object — even with the correct ceiling — is
    substituted authority: refused. Repeated direct drives with a fresh
    budget each time can never reset the cumulative ceiling."""
    broker = _manual_d2_broker(cap=64)
    cap_a, cap_b = _caps(tmp_path / "g", broker)
    ctx = _capture_authorized_pep_ctx(tmp_path / "g", monkeypatch, broker, cap_a, cap_b)
    bound_budget = ctx["governed_step_budget"]
    starts = _instrument_start_execution(broker)
    for _ in range(6):
        untrusted = dict(ctx)
        # A fresh budget object with the same nominal ceiling is still NOT
        # the authoritative episode budget.
        untrusted["governed_step_budget"] = GovernedStepBudget(bound_budget.ceiling)
        out = stage_pep(untrusted)
        assert out.success is False
        assert out.output.get("authority_missing") == "governed_step_budget"
    assert starts == [], "no substituted budget may ever start an execution"
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert cap_a.invocation_count == 0


def test_g2_forged_governance_object_refused(tmp_path, monkeypatch):
    """A forged permissive CapabilityGovernance is refused: authority is the
    Broker-bound object, matched by identity, not by shape."""
    broker = _manual_d2_broker(cap=64)
    cap_a, cap_b = _caps(tmp_path / "g2", broker)
    ctx = _capture_authorized_pep_ctx(tmp_path / "g2", monkeypatch, broker, cap_a, cap_b)
    starts = _instrument_start_execution(broker)
    forged = dict(ctx)
    forged["capability_governance"] = CapabilityGovernance(
        contract_id="attacker", ceiling=64, refuses_protected_capability=False,
        reason="forged blessing")
    out = stage_pep(forged)
    assert out.success is False
    assert out.output.get("authority_missing") == "capability_governance"
    assert starts == []
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0


def test_i_neutral_protected_object_refused_even_with_bound_authority(tmp_path, monkeypatch):
    """Neutral policy + protected object: even the Runtime's OWN bound
    authority refuses (governance is derived from policy + object), and a
    forged permissive governance object is refused as untrusted."""
    broker = _neutral_broker(cap=64, capabilities=(ALIAS_A,))
    cap_a, _cap_b = _caps(tmp_path / "i", broker)
    runtime = _runtime(tmp_path / "i", broker, cap_a, registry=None)
    captured = {}

    def capturing_pep(ctx):
        if "planner_request" not in captured:
            for key in ("broker", "capability", "capability_registry", "scope",
                        "evidence_store", "view", "artifact_roots", "organs",
                        "planner_request", "capability_governance",
                        "governed_step_budget"):
                captured[key] = ctx.get(key)
        return stages_mod.StageResult.make(
            stage_name=STAGE_PEP, success=False, error="captured")

    monkeypatch.setitem(stages_mod.STAGE_HANDLERS, STAGE_PEP, capturing_pep)
    runtime.run_episode(_mission(ALIAS_A, "recon_service_probe", "nmap",
                                 max_it=1, mission_id="c1-i"))
    monkeypatch.undo()
    assert captured.get("planner_request") is not None
    # (a) true bound authority present, object-derived governance refuses:
    out = stage_pep(dict(captured))
    assert out.success is False
    assert out.output.get("protected_capability_refused") is True
    # (b) forged permissive governance is refused as substituted authority:
    forged = dict(captured)
    forged["capability_governance"] = CapabilityGovernance(
        contract_id="attacker", ceiling=64, refuses_protected_capability=False,
        reason="forged blessing")
    out2 = stage_pep(forged)
    assert out2.success is False
    assert out2.output.get("authority_missing") == "capability_governance"
    lifecycle = _receipt_lifecycle(broker)
    assert lifecycle["STARTED"] == 0 and lifecycle["SUCCEEDED"] == 0
    assert cap_a.invocation_count == 0


@pytest.mark.parametrize("tampered", [0, 64])
def test_h_tampered_budget_ceiling_cannot_loosen_d2(tmp_path, tampered):
    """Recognised D2 + tampered authoritative budget ceiling (0 or 64): the
    REGISTRY ceiling 5 always wins — 5 executions across 30 bare step()
    calls, never 5 per call."""
    broker = _manual_d2_broker(cap=64)
    cap_a, _cap_b = _caps(tmp_path / f"h{tampered}", broker)
    runtime = _runtime(tmp_path / f"h{tampered}", broker, cap_a)
    starts = _instrument_start_execution(broker)
    runtime._step_budget.ceiling = tampered
    _step_loop(runtime, 30, "c1-h")
    lifecycle = _receipt_lifecycle(broker)
    assert cap_a.invocation_count == 5, f"tampered {tampered} executed {cap_a.invocation_count}"
    assert len(starts) == 5 and lifecycle["SUCCEEDED"] == 5
    assert lifecycle["AUTHORIZED"] == 25, "the 25 refused steps stay authorization-only"
    assert runtime._step_budget.ceiling == 5, "the registry ceiling is repaired"


def test_g3_authoritative_budget_is_cumulative_across_direct_drives(tmp_path):
    """No fresh-budget reset: 30 bare step() calls share ONE episode budget
    and stop at exactly 5 governed steps."""
    broker = _manual_d2_broker(cap=64)
    cap_a, _cap_b = _caps(tmp_path / "g3", broker)
    runtime = _runtime(tmp_path / "g3", broker, cap_a)
    starts = _instrument_start_execution(broker)
    _step_loop(runtime, 30, "c1-g3")
    lifecycle = _receipt_lifecycle(broker)
    assert cap_a.invocation_count == 5
    assert len(starts) == 5 and lifecycle["SUCCEEDED"] == 5
    assert runtime._step_budget.used == 5


# ══════════════════════════════════════════════════════════════════════════
# Canonical controls — D1 unchanged, D2 exactly five
# ══════════════════════════════════════════════════════════════════════════

def test_k_d1_canonical_uncapped(tmp_path):
    broker = _manual_d1_broker()
    cap_a, _cap_b = _caps(tmp_path / "d1", broker)
    runtime = _runtime(tmp_path / "d1", broker, cap_a)
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(CAP_A, "recon_service_probe", "nmap", max_it=6, mission_id="c1-d1"))
    assert cap_a.invocation_count == 6, "D1 remains uncapped at the PEP"
    lifecycle = _receipt_lifecycle(broker)
    assert len(starts) == 6 and lifecycle["SUCCEEDED"] == 6
    assert term.d2_recognized is False
    assert term.governed_step_ceiling == 0
    assert term.governance_contract == D1_ENG
    assert term.governance_refuses_protected is False


def test_k2_d1_direct_step_loop_uncapped(tmp_path):
    broker = _manual_d1_broker()
    cap_a, _cap_b = _caps(tmp_path / "d1s", broker)
    runtime = _runtime(tmp_path / "d1s", broker, cap_a)
    starts = _instrument_start_execution(broker)
    _step_loop(runtime, 8, "c1-d1")
    lifecycle = _receipt_lifecycle(broker)
    assert cap_a.invocation_count == 8
    assert len(starts) == 8 and lifecycle["SUCCEEDED"] == 8


def test_l_canonical_d2_control_exactly_five(tmp_path):
    broker = _manual_d2_broker(cap=64)
    cap_a, _cap_b = _caps(tmp_path / "d2", broker)
    runtime = _runtime(tmp_path / "d2", broker, cap_a)
    starts = _instrument_start_execution(broker)
    _traces, term = runtime.run_episode(
        _mission(CAP_A, "recon_service_probe", "nmap", max_it=9, mission_id="c1-d2"))
    assert cap_a.invocation_count == 5
    lifecycle = _receipt_lifecycle(broker)
    assert len(starts) == 5 and lifecycle["SUCCEEDED"] == 5
    assert term.d2_recognized is True
    assert term.governed_step_ceiling == 5
    assert term.governance_contract == D2_ENG


# ══════════════════════════════════════════════════════════════════════════
# Resolver unit contract: extra_protected only ever tightens
# ══════════════════════════════════════════════════════════════════════════

def test_resolver_extra_protected_never_manufactures_contracts():
    neutral = BrokerPolicy(engagement_id="neutral", policy_name="neutral-policy",
                           allowed_targets=["dvwa"], allowed_action_types=["x"],
                           allowed_capabilities=[ALIAS_A],
                           max_impact_per_action=2.0, max_episode_steps=64)
    gov = resolve_capability_governance(neutral)
    assert gov.refuses_protected_capability is False
    assert gov.ceiling == 64 and gov.contract_id == ""
    # A protected OBJECT under the same neutral policy fails closed...
    gov2 = resolve_capability_governance(neutral, extra_protected=frozenset({CAP_A}))
    assert gov2.refuses_protected_capability is True
    assert gov2.ceiling == 0 and gov2.contract_id == ""
    # ...and extra_protected can never mint a D1/D2 contract or raise a ceiling.
    unrecognised = BrokerPolicy(engagement_id="x", policy_name="x",
                                allowed_targets=["*"], allowed_action_types=["a"],
                                allowed_capabilities=["c"],
                                max_impact_per_action=1.0, max_episode_steps=1)
    forged = resolve_capability_governance(unrecognised,
                                           extra_protected=frozenset({CAP_A, CAP_B}))
    assert forged.contract_id == ""
    assert forged.refuses_protected_capability is True
    assert forged.ceiling == 0
