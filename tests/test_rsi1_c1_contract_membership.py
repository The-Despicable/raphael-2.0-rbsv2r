"""test_rsi1_c1_contract_membership.py — RSI-1 C-1 remediation tests (2026-10-07).

DECISIVE BLOCKER FIXED HERE. ``resolve_capability_governance()`` recognised the D1
contract from POLICY identity but never verified that the capability OBJECT
actually being dispatched belongs to the recognised contract's capability set.
So a canonical D1 policy (ceiling 0) paired with a ``LabHttpProbeCapability``
object — dispatched under D1's registry key, or as the bare default capability —
was authorised as "D1, uncapped" and executed the HTTP probe repeatedly.

A recognised governed contract must now authorise BOTH the policy AND the exact
capability object, decided from the object's own canonical identity
(``exec.capability_governance.governed_capability_identity``) and compared
against the contract's CLOSED capability set — never a registry key, a request
field, or a policy label.

SECONDARY: the episode budget is monotonic. There is no in-place rewind at all:
``used`` is read-only, every attribute except ``ceiling`` is frozen at
construction, and ``reset()`` refuses. The Runtime rotates the budget by minting
a NEW generation at its real episode boundary.

Every adversarial case disables the rate limiter, inspects the authoritative
Broker receipt store, and asserts 0 STARTED / 0 SUCCEEDED and zero capability
invocations on refusal. Hermetic: temporary stores/artifacts, injected runners
and inspectors, no docker and no network.
"""
import pytest

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.capability_governance import governed_capability_identity
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime import types as RT
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import D1_POLICY_PATH, D2_POLICY_PATH, make_broker_from_policy
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import GovernedStepBudget, MissionContext, RuntimeContext

CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
ALIAS = "exec.lab_probe_alias"
D1_ENG = "d1-governed-action"
D2_ENG = "d2-bounded-episode"
ACT_A = "recon_service_probe"
ACT_B = "lab_http_probe"

FAKE_NMAP = "Starting Nmap 7.99\n80/tcp open  http\n"
FAKE_CURL = "<html/>\n302|text/html|3|0.01|http://dvwa/login.php\n"


def _runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def _runner_b(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_CURL, ""
    return P()


def _inspector(container):
    return {"State": {"Running": True},
            "Config": {"Image": "vulnerables/web-dvwa:stable"},
            "NetworkSettings": {"Networks": {"raphael-m1_raphael-net":
                                             {"IPAddress": "172.19.0.4"}}}}


class _UnknownCapability:
    """A capability class the exec-owned governance registry does not know.

    Implements the full capability surface (including the ``broker`` attribute
    the PEP stage reads for the authoritative receipt), so a refusal is a
    GOVERNANCE decision rather than an incidental AttributeError.
    """

    def __init__(self, broker=None):
        self.invocation_count = 0
        self._broker = broker
        self._authorized = set()

    @property
    def broker(self):
        return self._broker

    def record_authorization(self, target):
        self._authorized.add(target)

    def inspect(self, target):
        self.invocation_count += 1
        raise RuntimeError("unknown capability executed — governance failed")

    @property
    def artifact_root(self):
        return None


# Rate limits are raised to a non-binding value and the RateLimiter component
# is removed entirely, so the ONLY thing that can bound these episodes is the
# governed-step ceiling under test.
RATE_CEILING = {"max_actions_per_minute": 10000, "max_actions_per_hour": 10000,
                "max_concurrent": 1000}


def _d1_broker(rate_ceiling=True):
    """Canonical D1 policy from the real artifact (fidelity), or a manual
    D1-identity BrokerPolicy with non-binding rate limits.

    Default is the manual, rate-unconstrained form so the governed-step ceiling
    is the only bound under test. ``rate_ceiling=False`` loads the REAL
    policies/engagement-d1-v1.json artifact, which is used once (test A) for
    fidelity.
    """
    if not rate_ceiling:
        return make_broker_from_policy(D1_POLICY_PATH)
    b = CapabilityBroker(BrokerPolicy(
        engagement_id=D1_ENG, policy_name="engagement-d1-v1",
        allowed_targets=["dvwa"], allowed_action_types=[ACT_A],
        allowed_capabilities=[CAP_A], max_impact_per_action=2.0,
        max_episode_steps=0, **RATE_CEILING))
    assert b.rate_limiter is None
    return b


def _d2_broker():
    """Manual D2-identity BrokerPolicy, NO rate limiter, non-binding rate limits."""
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id=D2_ENG, policy_name="engagement-d2-v1",
        allowed_targets=["dvwa"], allowed_action_types=[ACT_A, ACT_B],
        allowed_capabilities=[CAP_A, CAP_B], max_impact_per_action=2.0,
        max_episode_steps=5, **RATE_CEILING))
    assert broker.rate_limiter is None
    return broker


def _mission(n, action_type, capability, mission_id):
    return MissionContext(
        mission_id=mission_id, name="c1", objectives=["x"],
        scope=ScopeV0(mission_id=mission_id, targets=("dvwa",),
                      allowed_action_types=(action_type,),
                      allowed_capabilities=(capability,), max_impact=2.0),
        constraints={"halt": {"max_iterations": n, "action_cap": 1, "require_scope": True},
                     "candidates": {str(i): [{"action_id": f"A{i}",
                                              "action_type": action_type, "target": "dvwa",
                                              "capability": capability,
                                              "method": "nmap" if capability == CAP_A else "curl",
                                              "impact_estimate": 2.0,
                                              "args": {"bounded": True},
                                              "rationale": "c1"}]
                                    for i in range(n)},
                     "default_target": "dvwa",
                     "objective": {"requires_evidence": ["NOPE"]}})


def _build(tmp_path, broker, default_cap, registry, runner=None):
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    runtime = RaphaelRuntime(
        broker=broker, capability=default_cap,
        organs=OrganBundle(evidence_store=EvidenceStore(tmp_path / "evidence_store.jsonl")),
        capability_registry=registry)
    return runtime


def _states(broker):
    out = {}
    for receipt in broker.receipt_store.values():
        out[receipt.status.name] = out.get(receipt.status.name, 0) + 1
    return out


def _assert_refused(broker, cap, label):
    """Every refusal must leave the receipt AUTHORIZED and never invoke."""
    states = _states(broker)
    assert states.get("STARTED", 0) == 0, f"{label}: a receipt was STARTED {states}"
    assert states.get("SUCCEEDED", 0) == 0, f"{label}: a receipt SUCCEEDED {states}"
    assert states.get("AUTHORIZED", 0) > 0, f"{label}: authorization should precede refusal"
    assert cap.invocation_count == 0, f"{label}: capability was invoked {cap.invocation_count}x"


def _http_cap(broker, tmp_path):
    return LabHttpProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                  runner=_runner_b, inspector=_inspector)


def _d1_cap(broker, tmp_path):
    return D1LabProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                runner=_runner_a, inspector=_inspector)


# ══════════════════════════════════════════════════════════════════════════
# A — D1 policy + D1 object: ALLOWED, unchanged (uncapped D1 behaviour)
# ══════════════════════════════════════════════════════════════════════════

def test_a_d1_policy_with_d1_object_is_allowed_and_unchanged(tmp_path):
    # The REAL canonical D1 artifact, loaded from policies/engagement-d1-v1.json.
    broker = _d1_broker(rate_ceiling=False)
    broker.rate_limiter = None
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    _t, term = runtime.run_episode(_mission(6, ACT_A, CAP_A, D1_ENG), max_iterations=6)
    assert cap.invocation_count == 6
    assert term.governance_contract == D1_ENG
    assert term.governed_step_ceiling == 0, "D1 must keep its uncapped contract"
    assert term.governance_refuses_protected is False


# ══════════════════════════════════════════════════════════════════════════
# B — D1 policy + HTTP object: REFUSE
# ══════════════════════════════════════════════════════════════════════════

def test_b_d1_policy_with_http_object_is_refused(tmp_path):
    broker = _d1_broker()
    broker.rate_limiter = None
    cap = _http_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    _t, term = runtime.run_episode(_mission(12, ACT_A, CAP_A, D1_ENG), max_iterations=12)
    _assert_refused(broker, cap, "B")
    assert term.governance_contract == D1_ENG
    assert term.final_stage == "pep"


def test_b2_d1_policy_with_http_object_reports_contract_refusal(tmp_path):
    broker = _d1_broker()
    broker.rate_limiter = None
    cap = _http_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    outs = []
    _t, term = runtime.run_episode(_mission(12, ACT_A, CAP_A, D1_ENG),
                                   max_iterations=12, episode_outputs=outs)
    pep = outs[-1]["pep"]
    assert pep["capability_contract_refused"] is True
    assert pep["object_identity"] == [CAP_B]
    assert pep["governance_contract"] == D1_ENG
    assert pep["contract_capabilities"] == [CAP_A]
    assert "NOT authorised" in str(term.reason) or "not authorised" in str(term.reason)


# ══════════════════════════════════════════════════════════════════════════
# C — D1 policy + HTTP object under an ALIAS: REFUSE
# ══════════════════════════════════════════════════════════════════════════

def test_c_d1_policy_with_http_object_via_alias_is_refused(tmp_path):
    """Alias the HTTP object under a non-protected key the D1 policy also allows."""
    broker = _d1_broker()
    broker.rate_limiter = None
    cap = _http_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {ALIAS: cap})
    # D1 must authorise the alias name for this to reach the PEP at all.
    broker.policy.allowed_capabilities = (CAP_A, ALIAS)
    broker.policy.allowed_action_types = (ACT_A,)
    _t, term = runtime.run_episode(_mission(12, ACT_A, ALIAS, D1_ENG), max_iterations=12)
    _assert_refused(broker, cap, "C")
    assert term.governance_contract == D1_ENG


# ══════════════════════════════════════════════════════════════════════════
# D — D1 policy + HTTP object via POST-CONSTRUCTION registry mutation: REFUSE
# ══════════════════════════════════════════════════════════════════════════

def test_d_post_construction_registry_mutation_is_refused(tmp_path):
    broker = _d1_broker()
    broker.rate_limiter = None
    d1_cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, d1_cap, {CAP_A: d1_cap})
    # Swapping the protected D1 object for the HTTP object AFTER construction.
    http_cap = _http_cap(broker, tmp_path)
    runtime._capability_registry[CAP_A] = http_cap
    _t, term = runtime.run_episode(_mission(12, ACT_A, CAP_A, D1_ENG), max_iterations=12)
    _assert_refused(broker, http_cap, "D")
    assert d1_cap.invocation_count == 0
    assert term.governance_contract == D1_ENG


def test_d2_post_construction_default_capability_swap_is_refused(tmp_path):
    """Swap the protected D1 object for the HTTP object in the DEFAULT slot.

    The registry entry is removed so dispatch genuinely falls back to
    ``ctx["capability"]`` — the Runtime's default capability, which is the other
    caller-controlled route by which a protected object can be substituted.
    """
    broker = _d1_broker()
    d1_cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, d1_cap, {CAP_A: d1_cap})
    http_cap = _http_cap(broker, tmp_path)
    runtime._capability_registry.pop(CAP_A, None)
    runtime._capability = http_cap
    _t, term = runtime.run_episode(_mission(12, ACT_A, CAP_A, D1_ENG), max_iterations=12)
    _assert_refused(broker, http_cap, "D2-default-swap")
    assert d1_cap.invocation_count == 0


# ══════════════════════════════════════════════════════════════════════════
# E / F — canonical D2 authorises BOTH approved capabilities, max 5
# ══════════════════════════════════════════════════════════════════════════

def test_e_canonical_d2_with_d1_object_is_allowed_max_five(tmp_path):
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    _t, term = runtime.run_episode(_mission(40, ACT_A, CAP_A, D2_ENG), max_iterations=40)
    assert cap.invocation_count == 5
    assert term.governed_step_ceiling == 5
    assert term.governance_contract == D2_ENG


def test_f_canonical_d2_with_http_object_is_allowed_max_five(tmp_path):
    broker = _d2_broker()
    cap = _http_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_B: cap})
    _t, term = runtime.run_episode(_mission(40, ACT_B, CAP_B, D2_ENG), max_iterations=40)
    assert cap.invocation_count == 5
    assert term.governed_step_ceiling == 5
    assert term.governance_contract == D2_ENG


def test_f2_canonical_d2_with_both_objects_is_allowed(tmp_path):
    broker = _d2_broker()
    cap_a = _d1_cap(broker, tmp_path)
    cap_b = _http_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap_a, {CAP_A: cap_a, CAP_B: cap_b})
    _t, term = runtime.run_episode(_mission(40, ACT_B, CAP_B, D2_ENG), max_iterations=40)
    assert cap_b.invocation_count == 5
    assert cap_a.invocation_count == 0
    assert term.governed_step_ceiling == 5


# ══════════════════════════════════════════════════════════════════════════
# G — contract-membership resolver unit tests
# ══════════════════════════════════════════════════════════════════════════

def _gov(policy):
    return RT.resolve_capability_governance(policy)


def _policy(eng="neutral", name="neutral-policy", caps=(CAP_A,), cap=64,
            acts=None):
    return BrokerPolicy(engagement_id=eng, policy_name=name, allowed_targets=["dvwa"],
                        allowed_action_types=list(acts or [ACT_A]),
                        allowed_capabilities=list(caps),
                        max_impact_per_action=2.0, max_episode_steps=cap,
                        **RATE_CEILING)


def test_g1_resolved_contracts_expose_their_canonical_capability_set():
    d1 = _gov(_policy(eng=D1_ENG, name="engagement-d1-v1", caps=(CAP_A,), cap=0))
    d2 = _gov(_policy(eng=D2_ENG, name="engagement-d2-v1",
                      caps=(CAP_A, CAP_B), acts=(ACT_A, ACT_B), cap=5))
    assert d1.contract_id == D1_ENG
    assert d1.contract_capabilities == frozenset({CAP_A})
    assert d2.contract_id == D2_ENG
    assert d2.contract_capabilities == frozenset({CAP_A, CAP_B})


@pytest.mark.parametrize("contract_id", [D1_ENG, D2_ENG])
def test_g2_own_capability_is_a_member_of_its_own_contract(contract_id):
    gov = RT.CapabilityGovernance(
        contract_id=contract_id, ceiling=5,
        contract_capabilities=frozenset(
            RT.GOVERNED_ENGAGEMENT_CONTRACTS[contract_id]["capabilities"]))
    for cap_name in RT.GOVERNED_ENGAGEMENT_CONTRACTS[contract_id]["capabilities"]:
        permitted, _ = gov.permits_object_identity(frozenset({cap_name}))
        assert permitted is True, f"{contract_id} must authorise {cap_name}"


def test_g3_d1_contract_never_authorises_the_http_capability():
    gov = RT.resolve_capability_governance(_policy(eng=D1_ENG, name="engagement-d1-v1",
                                                   caps=(CAP_A,), cap=0))
    assert gov.contract_id == D1_ENG
    permitted, reason = gov.permits_object_identity(frozenset({CAP_B}))
    assert permitted is False
    assert CAP_B in reason and D1_ENG in reason


def test_g4_d2_contract_authorises_both_and_nothing_else():
    gov = RT.resolve_capability_governance(_policy(eng=D2_ENG, name="engagement-d2-v1",
                                                   caps=(CAP_A, CAP_B), cap=5))
    assert gov.permits_object_identity(frozenset({CAP_A}))[0] is True
    assert gov.permits_object_identity(frozenset({CAP_B}))[0] is True
    assert gov.permits_object_identity(frozenset({CAP_A, CAP_B}))[0] is True
    assert gov.permits_object_identity(frozenset({"exec.unlisted"}))[0] is False


def test_g5_membership_is_independent_of_registry_names():
    """Only identities present in the contract set can ever be members."""
    d1 = RT.resolve_capability_governance(_policy(eng=D1_ENG, name="engagement-d1-v1",
                                                  caps=(CAP_A,), cap=0))
    for fake in (ALIAS, "exec.d1_lab_probe ", "EXEC.D1_LAB_PROBE", CAP_A + "x"):
        assert d1.permits_object_identity(frozenset({fake}))[0] is False, fake


def test_g6_object_identity_resolution_is_type_keyed_not_name_keyed():
    d1_obj = D1LabProbeCapability(broker=None, artifacts_dir=None,
                                  runner=_runner_a, inspector=_inspector)
    http_obj = LabHttpProbeCapability(broker=None, artifacts_dir=None,
                                      runner=_runner_b, inspector=_inspector)
    assert governed_capability_identity(d1_obj) == frozenset({CAP_A})
    assert governed_capability_identity(http_obj) == frozenset({CAP_B})
    assert governed_capability_identity(None) == frozenset()


def test_g7_subclass_inherits_protection_and_cannot_strip_it():
    class Sneaky(D1LabProbeCapability):
        capability_name = ALIAS          # attempt to relabel via an attribute
        artifact_root = None

    sneaky = Sneaky(broker=None, artifacts_dir=None, runner=_runner_a, inspector=_inspector)
    assert governed_capability_identity(sneaky) == frozenset({CAP_A})


# ══════════════════════════════════════════════════════════════════════════
# J — unknown capability class: explicit DENY-BY-DEFAULT
# ══════════════════════════════════════════════════════════════════════════

def test_j1_unknown_class_resolves_to_no_governed_identity():
    assert governed_capability_identity(_UnknownCapability()) == frozenset()


def test_j2_unknown_class_is_denied_by_default_under_a_governed_contract():
    for contract_id in (D1_ENG, D2_ENG):
        gov = RT.CapabilityGovernance(
            contract_id=contract_id, ceiling=5,
            contract_capabilities=frozenset(
                RT.GOVERNED_ENGAGEMENT_CONTRACTS[contract_id]["capabilities"]))
        permitted, reason = gov.permits_object_identity(frozenset())
        assert permitted is False, contract_id
        assert "deny-by-default" in reason


def test_j3_unknown_class_still_allowed_under_a_legacy_policy():
    """No governed contract -> the policy + Broker govern it (bootstrap surface)."""
    gov = _gov(_policy(caps=("fixture.inspect",), cap=0))
    assert gov.contract_id == ""
    assert gov.permits_object_identity(frozenset())[0] is True


def test_j4_unknown_class_is_refused_at_the_pep_boundary(tmp_path):
    """An unregistered capability class cannot execute under a D2 contract."""
    broker = _d2_broker()
    unknown = _UnknownCapability(broker)
    runtime = _build(tmp_path, broker, unknown, {CAP_A: unknown})
    _t, term = runtime.run_episode(_mission(12, ACT_A, CAP_A, D2_ENG), max_iterations=12)
    _assert_refused(broker, unknown, "J4")
    assert term.governance_contract == D2_ENG
    assert "deny-by-default" in str(term.reason)


# ══════════════════════════════════════════════════════════════════════════
# H / I — monotonic episode budget
# ══════════════════════════════════════════════════════════════════════════

def test_h1_used_is_read_only():
    budget = GovernedStepBudget(5)
    with pytest.raises(AttributeError):
        budget.used = 0
    assert budget.used == 0


def test_h2_rewinding_used_between_every_step_cannot_exceed_the_ceiling(tmp_path):
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    scope = ScopeV0(mission_id=D2_ENG, targets=("dvwa",), allowed_action_types=(ACT_A,),
                    allowed_capabilities=(CAP_A,), max_impact=2.0)
    rewinds = 0
    for i in range(20):
        try:
            runtime._step_budget.used = 0
            rewinds += 1
        except AttributeError:
            pass
        runtime.step(RuntimeContext(
            mission_id=D2_ENG, objective_id="o", iteration=i, scope=scope,
            view={"mission_name": "x", "mission_id": D2_ENG, "iteration": i,
                  "target": "dvwa", "objective_id": "o",
                  "candidates": [{"action_id": f"S{i}", "action_type": ACT_A,
                                  "target": "dvwa", "capability": CAP_A,
                                  "method": "nmap", "impact_estimate": 2.0,
                                  "args": {"bounded": True}, "rationale": "c1"}]}))
    assert rewinds == 0, "`used` must not be rewritable mid-episode"
    assert cap.invocation_count == 5, cap.invocation_count
    assert runtime._step_budget.ceiling == 5


def test_h3_budget_only_advances_through_try_consume():
    """There is no in-place rewind; a fresh allowance needs a new generation."""
    budget = GovernedStepBudget(2)
    assert budget.used == 0
    assert budget.try_consume() is True
    assert budget.try_consume() is True
    assert budget.try_consume() is False
    assert budget.used == 2
    with pytest.raises(RT.BudgetResetRefused):
        budget.reset()
    assert budget.used == 2, "a refused reset must not rewind"
    nxt = GovernedStepBudget.next_episode(budget, 2)
    assert nxt.used == 0 and nxt.generation == budget.generation + 1


def test_i1_legitimate_episode_boundary_starts_a_new_episode(tmp_path):
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    before = runtime._step_budget.generation
    _t, t1 = runtime.run_episode(_mission(40, ACT_A, CAP_A, D2_ENG), max_iterations=40)
    assert cap.invocation_count == 5
    assert t1.governance_budget_epoch == before + 1
    mid = runtime._step_budget.generation
    _t, t2 = runtime.run_episode(_mission(40, ACT_A, CAP_A, D2_ENG), max_iterations=40)
    assert cap.invocation_count == 10, "a NEW episode gets a NEW budget"
    assert t2.governance_budget_epoch == mid + 1


def test_i2_reset_is_refused_and_the_generation_only_advances_at_a_boundary(tmp_path):
    """Mid-episode reset() refuses; only run_episode advances the generation."""
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    epoch0 = runtime._step_budget.generation
    with pytest.raises(RT.BudgetResetRefused):
        runtime._step_budget.reset()
    assert runtime._step_budget.generation == epoch0
    runtime.run_episode(_mission(40, ACT_A, CAP_A, D2_ENG), max_iterations=40)
    assert runtime._step_budget.generation == epoch0 + 1


def test_i3_ceiling_stays_writable_but_cannot_be_tampered_up(tmp_path):
    """The PEP repairs a tampered ceiling; a caller cannot raise it."""
    budget = GovernedStepBudget(5)
    budget.ceiling = 64
    assert budget.ceiling == 64
    budget.ceiling = -3
    assert budget.ceiling == 0
    budget.ceiling = "nonsense"
    assert budget.ceiling == 0


# ══════════════════════════════════════════════════════════════════════════
# K — the previously-shipped C-1 boundary invariants still hold
# ══════════════════════════════════════════════════════════════════════════

def test_k1_missing_authority_still_refuses(tmp_path):
    from orchestrator.runtime.stages import stage_broker, stage_pep
    from orchestrator.runtime.types import ActionRequest
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    ctx = {"view": {"mission_id": D2_ENG}, "broker": broker, "capability": cap,
           "organs": None, "scope": None, "capability_registry": {CAP_A: cap},
           "planner_request": {"request": ActionRequest(
               action_id="K1", action_type=ACT_A, target="dvwa", capability=CAP_A,
               method="nmap", impact_estimate=2.0, args={"bounded": True},
               rationale="c1")}}
    res = stage_broker(ctx)
    assert res.success is True
    untrusted = {"capability": cap, "broker": res.output,
                 "planner_request": ctx["planner_request"]}
    out = stage_pep(untrusted)
    assert out.success is False
    assert out.output.get("authority_missing") in ("broker", "capability_governance",
                                                   "governed_step_budget")
    assert cap.invocation_count == 0


def test_k2_substituted_budget_object_still_refuses(tmp_path):
    from orchestrator.runtime.stages import stage_broker, stage_pep
    from orchestrator.runtime.types import ActionRequest
    broker = _d2_broker()
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {CAP_A: cap})
    ctx = {"view": {"mission_id": D2_ENG}, "broker": broker, "capability": cap,
           "organs": None, "scope": None, "capability_registry": {CAP_A: cap},
           "capability_governance": runtime._governance,
           "governed_step_budget": GovernedStepBudget(runtime._step_budget.ceiling),
           "planner_request": {"request": ActionRequest(
               action_id="K2", action_type=ACT_A, target="dvwa", capability=CAP_A,
               method="nmap", impact_estimate=2.0, args={"bounded": True},
               rationale="c1")}}
    res = stage_broker(ctx)
    assert res.success is True
    ctx["broker"] = res.output
    out = stage_pep(ctx)
    assert out.success is False
    assert out.output.get("authority_missing") == "governed_step_budget"
    assert cap.invocation_count == 0


def test_k3_alias_escape_from_the_previous_audit_stays_closed(tmp_path):
    """B-1/C-1 alias escape: neutral policy + protected object under a new name."""
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="neutral", policy_name="neutral-policy", allowed_targets=["dvwa"],
        allowed_action_types=[ACT_A], allowed_capabilities=[ALIAS],
        max_impact_per_action=2.0, max_episode_steps=64))
    assert broker.rate_limiter is None
    cap = _d1_cap(broker, tmp_path)
    runtime = _build(tmp_path, broker, cap, {ALIAS: cap})
    _t, term = runtime.run_episode(_mission(40, ACT_A, ALIAS, "neutral"), max_iterations=40)
    _assert_refused(broker, cap, "K3-alias")
    assert term.governance_refuses_protected is True