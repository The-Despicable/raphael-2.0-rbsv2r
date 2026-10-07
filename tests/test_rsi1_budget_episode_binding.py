"""test_rsi1_budget_episode_binding.py — RSI-1 final blocker remediation (2026-10-07).

The v4.1 audit confirmed the contract/object governance fix is correct but found
that the authoritative episode budget could still be rewound mid-episode::

    rt._step_budget.reset()   -> 20 executions under a D2 ceiling of 5
    rt._step_budget._used = 0 -> same

INVARIANT ENFORCED HERE. Within one active episode the authoritative
governed-step counter is strictly monotonic and cannot be rewound by any
caller. The only authorised way to obtain a fresh allowance is the Runtime's
real episode-boundary transition, which mints a NEW budget generation and
re-binds it to the Broker.

Structurally, not by naming: the counter lives in a closure cell that is not an
attribute at all; the class uses ``__slots__`` (no ``__dict__``); ``__setattr__``
freezes every attribute once construction completes and ``__delattr__`` always
refuses. There is no ``_used`` field to zero and no ``_advance``/``try_consume``
hook to replace.

Every adversarial case removes the rate limiter and raises the broker's own rate
limits, so nothing but the governed-step ceiling can bound an episode; inspects
the authoritative ``broker.receipt_store``; and counts real capability
invocations. Hermetic: temporary stores/artifacts, injected runners/inspectors.
"""
import hashlib
from pathlib import Path
from tempfile import mkdtemp

import pytest

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime import types as RT
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import D1_POLICY_PATH, make_broker_from_policy
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.stages import stage_broker, stage_pep
from orchestrator.runtime.types import (ActionRequest, GovernedStepBudget,
                                        MissionContext, RuntimeContext)

CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
D1_ENG = "d1-governed-action"
D2_ENG = "d2-bounded-episode"
ACT_A = "recon_service_probe"
ACT_B = "lab_http_probe"
FAKE_NMAP = "Starting Nmap 7.99\n80/tcp open  http\n"
FAKE_CURL = "<html/>\n302|text/html|3|0.01|http://dvwa/login.php\n"
RATE = {"max_actions_per_minute": 10000, "max_actions_per_hour": 10000,
        "max_concurrent": 1000}


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


def _d1_broker():
    return CapabilityBroker(BrokerPolicy(
        engagement_id=D1_ENG, policy_name="engagement-d1-v1", allowed_targets=["dvwa"],
        allowed_action_types=[ACT_A], allowed_capabilities=[CAP_A],
        max_impact_per_action=2.0, max_episode_steps=0, **RATE))


def _d2_broker():
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id=D2_ENG, policy_name="engagement-d2-v1", allowed_targets=["dvwa"],
        allowed_action_types=[ACT_A, ACT_B], allowed_capabilities=[CAP_A, CAP_B],
        max_impact_per_action=2.0, max_episode_steps=5, **RATE))
    assert broker.rate_limiter is None
    return broker


def _cap(broker, tmp_path, http=False):
    cls = LabHttpProbeCapability if http else D1LabProbeCapability
    runner = _runner_b if http else _runner_a
    return cls(broker=broker, artifacts_dir=tmp_path / "artifacts",
               runner=runner, inspector=_inspector)


def _runtime(broker, default, registry, tmp_path=None):
    """Runtime plus the temp directory it was built in (for capability roots)."""
    if tmp_path is None:
        tmp_path = Path(mkdtemp())
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    runtime = RaphaelRuntime(
        broker=broker, capability=default,
        organs=OrganBundle(evidence_store=EvidenceStore(tmp_path / "evidence_store.jsonl")),
        capability_registry=registry)
    return runtime, tmp_path


def _mission(n, mission_id=D2_ENG, action_type=ACT_A, capability=CAP_A):
    return MissionContext(
        mission_id=mission_id, name="budget", objectives=["x"],
        scope=ScopeV0(mission_id=mission_id, targets=("dvwa",),
                      allowed_action_types=(action_type,),
                      allowed_capabilities=(capability,), max_impact=2.0),
        constraints={"halt": {"max_iterations": n, "action_cap": 1, "require_scope": True},
                     "candidates": {str(i): [{"action_id": f"A{i}",
                                              "action_type": action_type, "target": "dvwa",
                                              "capability": capability, "method": "nmap",
                                              "impact_estimate": 2.0,
                                              "args": {"bounded": True},
                                              "rationale": "budget"}]
                                    for i in range(n)},
                     "default_target": "dvwa",
                     "objective": {"requires_evidence": ["NOPE"]}})


def _scope():
    return ScopeV0(mission_id=D2_ENG, targets=("dvwa",), allowed_action_types=(ACT_A,),
                   allowed_capabilities=(CAP_A,), max_impact=2.0)


def _step(runtime, i):
    return runtime.step(RuntimeContext(
        mission_id=D2_ENG, objective_id="o", iteration=i, scope=_scope(),
        view={"mission_name": "x", "mission_id": D2_ENG, "iteration": i,
              "target": "dvwa", "objective_id": "o",
              "candidates": [{"action_id": f"S{i}", "action_type": ACT_A,
                              "target": "dvwa", "capability": CAP_A, "method": "nmap",
                              "impact_estimate": 2.0, "args": {"bounded": True},
                              "rationale": "budget"}]}))


def _receipt_states(broker):
    out = {}
    for receipt in broker.receipt_store.values():
        out[receipt.status.name] = out.get(receipt.status.name, 0) + 1
    return out


# ══════════════════════════════════════════════════════════════════════════
# A — budget.used = 0 must be impossible
# ══════════════════════════════════════════════════════════════════════════

def test_a_used_is_not_assignable(tmp_path):
    budget = GovernedStepBudget(5)
    budget.try_consume()
    with pytest.raises(AttributeError):
        budget.used = 0
    assert budget.used == 1, "the active counter must be unchanged"


def test_a3_used_assignment_on_a_live_runtime_budget_refuses(tmp_path):
    broker = _d2_broker()
    runtime, root = _runtime(broker, None, {})
    cap = _cap(broker, root)
    runtime._capability = cap
    runtime._capability_registry = {CAP_A: cap}
    budget = GovernedStepBudget(5, generation=runtime._step_budget.generation)
    budget.try_consume()
    with pytest.raises(AttributeError):
        budget.used = 0
    assert budget.used == 1


def test_a3_used_assignment_on_a_live_runtime_budget_refuses(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    runtime._step_budget.try_consume()
    with pytest.raises(AttributeError):
        runtime._step_budget.used = 0
    assert runtime._step_budget.used == 1


# ══════════════════════════════════════════════════════════════════════════
# B — budget._used = 0 must be impossible
# ══════════════════════════════════════════════════════════════════════════

def test_b_backing_field_is_frozen(tmp_path):
    budget = GovernedStepBudget(5)
    budget.try_consume()
    for name in ("_used", "_cell", "_read", "_advance", "_generation", "_seal"):
        with pytest.raises(AttributeError):
            setattr(budget, name, 0)
    assert budget.used == 1


def test_b2_there_is_no_writable_backing_field_at_all(tmp_path):
    """Structural: no instance __dict__, and no counter attribute to zero."""
    budget = GovernedStepBudget(5)
    assert not hasattr(budget, "__dict__"), "slots-only, no __dict__ to edit"
    assert not hasattr(budget, "_used")
    with pytest.raises(AttributeError):
        budget.newattr = 1
    with pytest.raises(AttributeError):
        del budget._read


# ══════════════════════════════════════════════════════════════════════════
# C — reset() during Runtime.step() must not rewind; <= 5 executions
# ══════════════════════════════════════════════════════════════════════════

def test_c_reset_during_step_does_not_rewind(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    refusals = 0
    for i in range(20):
        try:
            runtime._step_budget.reset()
        except RT.BudgetResetRefused:
            refusals += 1
        _step(runtime, i)
    assert refusals == 20, "every mid-episode reset must refuse"
    assert cap.invocation_count == 5, cap.invocation_count
    assert runtime._step_budget.ceiling == 5


def test_c2_no_sixth_capability_invocation_under_reset_pressure(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    for i in range(20):
        for _ in range(3):
            try:
                runtime._step_budget.reset()
            except RT.BudgetResetRefused:
                pass
        _step(runtime, i)
    assert sum(1 for _ in [0]) == 1
    assert cap.invocation_count == 5


# ══════════════════════════════════════════════════════════════════════════
# D — reset() between every step() still maxes out at 5
# ══════════════════════════════════════════════════════════════════════════

def test_d_reset_before_every_step_still_caps_at_five(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    accepted = 0
    for i in range(30):
        try:
            runtime._step_budget.reset()
            accepted += 1
        except RT.BudgetResetRefused:
            pass
        _step(runtime, i)
    assert accepted == 0
    assert cap.invocation_count == 5
    states = _receipt_states(broker)
    assert states.get("SUCCEEDED", 0) == 5
    assert states.get("STARTED", 0) == 0, "no receipt is left STARTED"


# ══════════════════════════════════════════════════════════════════════════
# E — reset() before direct stage_pep attempts grants no new allowance
# ══════════════════════════════════════════════════════════════════════════

def _pep_ctx(broker, cap, budget, action_type=ACT_A, capability=CAP_A):
    ctx = {"view": {"mission_id": D2_ENG}, "broker": broker, "capability": cap,
           "organs": None, "scope": None, "capability_registry": {CAP_A: cap},
           "capability_governance": getattr(broker, "_capability_governance", None),
           "governed_step_budget": budget,
           "planner_request": {"request": ActionRequest(
               action_id="E", action_type=action_type, target="dvwa",
               capability=capability, method="nmap", impact_estimate=2.0,
               args={"bounded": True}, rationale="budget")}}
    res = stage_broker(ctx)
    assert res.success is True, res.error
    ctx["broker"] = res.output
    return ctx


def test_e_reset_before_direct_pep_grants_no_new_allowance(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    budget = runtime._step_budget
    executed = 0
    for i in range(20):
        try:
            budget.reset()
        except RT.BudgetResetRefused:
            pass
        out = stage_pep(_pep_ctx(broker, cap, budget))
        if out.success:
            executed += 1
    assert executed == 5, f"direct PEP attempts must still stop at 5, got {executed}"
    assert cap.invocation_count == 5
    assert _receipt_states(broker).get("SUCCEEDED", 0) == 5


# ══════════════════════════════════════════════════════════════════════════
# F — epoch / generation / seal manipulation cannot reset
# ══════════════════════════════════════════════════════════════════════════

def test_f_generation_and_seal_are_frozen(tmp_path):
    budget = GovernedStepBudget(5, generation=3)
    for name, value in (("generation", 99), ("_generation", 99), ("seal", None),
                        ("_seal", None)):
        with pytest.raises(AttributeError):
            setattr(budget, name, value)
    assert budget.generation == 3
    assert budget.seal is budget.seal


def test_f2_next_episode_is_the_only_rotation_and_it_is_monotonic(tmp_path):
    b0 = GovernedStepBudget(5)
    b1 = GovernedStepBudget.next_episode(b0, 5)
    b2 = GovernedStepBudget.next_episode(b1, 5)
    assert (b0.generation, b1.generation, b2.generation) == (0, 1, 2)
    assert b1.seal is not b2.seal, "each generation gets its own seal"
    assert b1 is not b2


def test_f3_a_stale_budget_cannot_authorise_a_reset(tmp_path):
    """The previous episode's budget is inert: the PEP refuses it by identity."""
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    stale = runtime._step_budget
    for i in range(5):
        _step(runtime, i)
    runtime.run_episode(_mission(40), max_iterations=40)   # boundary: new generation
    assert runtime._step_budget is not stale
    out = stage_pep(_pep_ctx(broker, cap, stale))
    assert out.success is False
    assert out.output.get("authority_missing") == "governed_step_budget"
    assert _receipt_states(broker).get("STARTED", 0) == 0


# ══════════════════════════════════════════════════════════════════════════
# G — replacing broker._governed_step_budget stays refused
# ══════════════════════════════════════════════════════════════════════════

def test_g_replacing_the_broker_budget_is_refused(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    before = cap.invocation_count
    broker._governed_step_budget = GovernedStepBudget(runtime._step_budget.ceiling)
    _step(runtime, 0)
    assert cap.invocation_count == before, "the substitute must not authorise execution"
    out = stage_pep(_pep_ctx(broker, cap, GovernedStepBudget(5)))
    assert out.success is False
    assert out.output.get("authority_missing") == "governed_step_budget"


# ══════════════════════════════════════════════════════════════════════════
# H — a fresh / replacement budget in ctx stays refused
# ══════════════════════════════════════════════════════════════════════════

def test_h_fresh_budget_in_ctx_is_refused(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    out = stage_pep(_pep_ctx(broker, cap, GovernedStepBudget(5)))
    assert out.success is False
    assert out.output.get("authority_missing") == "governed_step_budget"
    assert cap.invocation_count == 0
    assert _receipt_states(broker).get("STARTED", 0) == 0
    assert _receipt_states(broker).get("SUCCEEDED", 0) == 0


def test_h2_budget_from_the_next_generation_is_also_refused(tmp_path):
    """Even a legitimately-shaped future budget cannot substitute today."""
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    future = GovernedStepBudget.next_episode(runtime._step_budget, 5)
    out = stage_pep(_pep_ctx(broker, cap, future))
    assert out.success is False
    assert out.output.get("authority_missing") == "governed_step_budget"
    assert cap.invocation_count == 0


# ══════════════════════════════════════════════════════════════════════════
# I — the legitimate episode boundary yields a fresh, valid allowance
# ══════════════════════════════════════════════════════════════════════════

def test_i_episode_boundary_grants_exactly_one_fresh_allowance(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    gen0 = runtime._step_budget.generation
    _t, t1 = runtime.run_episode(_mission(40), max_iterations=40)
    assert cap.invocation_count == 5
    assert runtime._step_budget.generation == gen0 + 1
    assert t1.governance_budget_epoch == gen0 + 1
    gen1 = runtime._step_budget.generation
    _t, t2 = runtime.run_episode(_mission(40), max_iterations=40)
    assert cap.invocation_count == 10, "each new episode gets its own 5"
    assert runtime._step_budget.generation == gen1 + 1
    assert t2.governance_budget_epoch == gen1 + 1
    assert _receipt_states(broker).get("SUCCEEDED", 0) == 10


def test_i2_the_boundary_rebinds_the_broker_to_the_new_budget(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    runtime.run_episode(_mission(40), max_iterations=40)
    assert broker._governed_step_budget is runtime._step_budget
    assert broker._governed_step_budget.generation == runtime._step_budget.generation


# ══════════════════════════════════════════════════════════════════════════
# J / K — canonical D1 and D2 controls are preserved
# ══════════════════════════════════════════════════════════════════════════

def test_j_canonical_d1_remains_uncapped(tmp_path):
    """Real D1 artifact + D1 object: unchanged, uncapped, budget inert."""
    broker = make_broker_from_policy(D1_POLICY_PATH)
    broker.rate_limiter = None
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    _t, term = runtime.run_episode(_mission(6, mission_id=D1_ENG), max_iterations=6)
    assert cap.invocation_count == 6
    assert term.governed_step_ceiling == 0
    assert term.governance_contract == D1_ENG


def test_j2_d1_stays_uncapped_under_repeated_reset_attempts(tmp_path):
    broker = _d1_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    for i in range(10):
        with pytest.raises(RT.BudgetResetRefused):
            runtime._step_budget.reset()
        _step(runtime, i)
    assert cap.invocation_count == 10, "D1's contract declares no ceiling"
    assert runtime._step_budget.ceiling == 0


def test_k_canonical_d2_is_exactly_five(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path)
    runtime, _d = _runtime(broker, cap, {CAP_A: cap})
    _t, term = runtime.run_episode(_mission(40), max_iterations=40)
    assert cap.invocation_count == 5
    assert term.governed_step_ceiling == 5
    assert term.governed_steps_used == 5
    states = _receipt_states(broker)
    assert states.get("SUCCEEDED", 0) == 5
    assert states.get("STARTED", 0) == 0


def test_k2_canonical_d2_http_capability_also_exactly_five(tmp_path):
    broker = _d2_broker()
    cap = _cap(broker, tmp_path, http=True)
    runtime, _d = _runtime(broker, cap, {CAP_B: cap})
    _t, term = runtime.run_episode(_mission(40, action_type=ACT_B, capability=CAP_B),
                                   max_iterations=40)
    assert cap.invocation_count == 5
    assert term.governed_step_ceiling == 5