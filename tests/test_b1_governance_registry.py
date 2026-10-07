"""test_b1_governance_registry.py — RSI-1 B-1 regression tests (2026-10-07).

B-1 root cause: the D2 five-step ceiling was attached to POLICY IDENTITY
(declared name, engagement id, capability/action vocabulary, lab contract). All
four are mutable, so removing them reclassified a still-protected capability as
"not D2" and the ceiling disappeared — the final independent audit measured 6, 9
and 12 unbounded governed executions of ``exec.d1_lab_probe``.

B-1 fix: the ceiling and the protected-capability refusal now come from the
canonical governance REGISTRY (``types.GOVERNED_ENGAGEMENT_CONTRACTS``), which
the Runtime owns. Recognition may only ever tighten or refuse; it can never
grant an unbounded fallback.

Every test instruments ACTUAL PEP/capability invocations. Hermetic: temporary
stores and artifacts only, injected runners/inspectors, no docker or network.
"""
import json
from pathlib import Path

import pytest

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime import types as RT
from orchestrator.runtime import stages as stages_mod
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D1_POLICY_PATH,
    D2_POLICY_PATH,
    PolicyLoadError,
    make_broker_from_policy,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext, RuntimeContext

CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
D2_ENG = "d2-bounded-episode"
FAKE_NMAP = "Starting Nmap 7.99\n80/tcp open  http\n"


def _runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def _inspector(container):
    return {"State": {"Running": True},
            "Config": {"Image": "vulnerables/web-dvwa:stable"},
            "NetworkSettings": {"Networks": {"raphael-m1_raphael-net":
                                             {"IPAddress": "172.19.0.4"}}}}


def _cand(action_id, action_type="recon_service_probe", capability=CAP_A):
    return {"action_id": action_id, "action_type": action_type, "target": "dvwa",
            "capability": capability,
            "method": "nmap" if capability == CAP_A else "curl",
            "impact_estimate": 2.0, "args": {"bounded": True},
            "rationale": "b1 regression"}


def build_runtime(tmp_path, broker):
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                 runner=_runner_a, inspector=_inspector)
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                   runner=_runner_a, inspector=_inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A: cap_a, CAP_B: cap_b})
    return runtime, {CAP_A: cap_a, CAP_B: cap_b}


def budget_mission(iters, mission_id=D2_ENG):
    return MissionContext(
        mission_id=mission_id, name="b1", objectives=["x"],
        scope=ScopeV0(mission_id=mission_id, targets=("dvwa",),
                      allowed_action_types=("recon_service_probe",),
                      allowed_capabilities=(CAP_A,), max_impact=2.0),
        constraints={"halt": {"max_iterations": iters, "action_cap": 1,
                              "require_scope": True},
                     "candidates": {str(i): [_cand(f"ACT-{i}")] for i in range(iters)},
                     "default_target": "dvwa",
                     "objective": {"requires_evidence": [f"NEVER-{i}"
                                                          for i in range(iters)]}})


def count_pep(runtime, mission, requested):
    """Run one episode; return (pep_invocations, capability_invocations, term)."""
    _t, term = runtime.run_episode(mission, max_iterations=requested)
    pep = term.governed_steps_used
    caps = sum(c.invocation_count for c in runtime._capability_registry.values())
    return pep, caps, term


def write_policy_copy(tmp_path, name, mutate):
    data = json.loads(D2_POLICY_PATH.read_text())
    mutate(data)
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


def manual_broker(cap, engagement_id="neutral", policy_name="neutral-policy",
                  action_types=("recon_service_probe",), capabilities=(CAP_A,)):
    """Hand-built BrokerPolicy with NO rate limiter."""
    return CapabilityBroker(BrokerPolicy(
        engagement_id=engagement_id, policy_name=policy_name,
        allowed_targets=["dvwa"], allowed_action_types=list(action_types),
        allowed_capabilities=list(capabilities),
        max_impact_per_action=2.0, max_episode_steps=cap))


# ══════════════════════════════════════════════════════════════════════════
# The registry itself: the single source of the D2 ceiling
# ══════════════════════════════════════════════════════════════════════════

def test_registry_is_the_single_source_of_the_d2_ceiling():
    assert RT.GOVERNED_ENGAGEMENT_CONTRACTS[D2_ENG]["max_episode_steps"] == 5
    assert RT.GOVERNED_ENGAGEMENT_CONTRACTS["d1-governed-action"]["max_episode_steps"] == 0
    assert RT.PROTECTED_GOVERNED_CAPABILITIES == frozenset({CAP_A, CAP_B})


def test_canonical_d2_artifact_resolves_to_the_registry_contract():
    broker = make_broker_from_policy(D2_POLICY_PATH)
    gov = RT.resolve_capability_governance(broker.policy)
    assert gov.contract_id == D2_ENG
    assert gov.ceiling == 5
    assert gov.refuses_protected_capability is False


def test_registry_ceiling_ignores_a_larger_declared_cap(tmp_path):
    """Even if the artifact declared 64, the registry ceiling governs."""
    broker = manual_broker(64, engagement_id=D2_ENG, policy_name="engagement-d2-v1")
    assert RT.resolve_capability_governance(broker.policy).ceiling == 5


# ══════════════════════════════════════════════════════════════════════════
# B1-A — pristine D2 policy, budget 99
# ══════════════════════════════════════════════════════════════════════════

def test_b1a_pristine_d2_policy_is_capped_at_five(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker)
    pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv
    assert pep == 5
    assert term.effective_budget == 5
    assert term.requested_budget == 99
    assert term.budget_clamped is True
    assert "objective met" not in term.reason


# ══════════════════════════════════════════════════════════════════════════
# B1-B — rename only
# ══════════════════════════════════════════════════════════════════════════

def test_b1b_rename_only_cannot_become_uncapped(tmp_path):
    path = write_policy_copy(tmp_path, "renamed.json",
                             lambda d: d.update(policy_name="totally-innocent"))
    try:
        broker = make_broker_from_policy(path)
    except PolicyLoadError as exc:
        assert "exactly 5" in str(exc)
        return  # rejected before execution — preferred outcome
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv
    assert term.governed_step_ceiling == 5


# ══════════════════════════════════════════════════════════════════════════
# B1-C — engagement identifier removed/changed
# ══════════════════════════════════════════════════════════════════════════

def test_b1c_engagement_id_change_cannot_become_uncapped(tmp_path):
    path = write_policy_copy(tmp_path, "eng.json",
                             lambda d: d.update(engagement_id="unrelated-engagement"))
    try:
        broker = make_broker_from_policy(path)
    except PolicyLoadError:
        return
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv


def test_b1c2_engagement_id_removed_from_a_manual_policy(tmp_path):
    """Empty engagement id + name, but the FULL D2 vocabulary is still D2."""
    broker = manual_broker(64, engagement_id="", policy_name="",
                           action_types=("recon_service_probe", "lab_http_probe"),
                           capabilities=(CAP_A, CAP_B))
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv == 5, inv
    # Vocabulary alone is enough to keep the D2 contract in force.
    assert term.governance_contract == D2_ENG
    assert term.governed_step_ceiling == 5


def test_b1c3_empty_identity_and_narrow_vocabulary_fails_closed(tmp_path):
    """No identity signal and no full vocabulary -> refused, not uncapped."""
    broker = manual_broker(64, engagement_id="", policy_name="")
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv == 0
    assert term.governance_refuses_protected is True


# ══════════════════════════════════════════════════════════════════════════
# B1-D — lab-contract signal removed
# ══════════════════════════════════════════════════════════════════════════

def test_b1d_lab_contract_removal_cannot_become_uncapped(tmp_path):
    path = write_policy_copy(tmp_path, "nolab.json",
                             lambda d: d["scope"]["lab"].pop("http", None))
    try:
        broker = make_broker_from_policy(path)
    except PolicyLoadError:
        return
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv
    assert term.governed_step_ceiling == 5


def test_b1d2_lab_contract_altered_cannot_become_uncapped(tmp_path):
    path = write_policy_copy(tmp_path, "badlab.json",
                             lambda d: d["scope"]["lab"].update(
                                 target_image_prefix="alpine"))
    try:
        broker = make_broker_from_policy(path)
    except PolicyLoadError:
        return
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, _term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv


# ══════════════════════════════════════════════════════════════════════════
# B1-E — capability vocabulary signal removed (smallest former escape)
# ══════════════════════════════════════════════════════════════════════════

def test_b1e_vocabulary_removal_cannot_become_uncapped(tmp_path):
    def mutate(d):
        d["policy_name"] = "totally-innocent"
        d["engagement_id"] = "unrelated"
        d["allowed"]["action_types"].remove("lab_http_probe")
        d["allowed"]["capabilities"].remove(CAP_B)
    path = write_policy_copy(tmp_path, "narrow.json", mutate)
    try:
        broker = make_broker_from_policy(path)
    except PolicyLoadError:
        return  # lab contract still signals D2 -> refused by the loader
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, inv


# ══════════════════════════════════════════════════════════════════════════
# B1-F — ALL FOUR signals removed: the decisive regression test
# ══════════════════════════════════════════════════════════════════════════

def _strip_all_four(d):
    d["policy_name"] = "totally-innocent"
    d["engagement_id"] = "unrelated-engagement"
    d["scope"]["lab"].pop("http", None)
    d["allowed"]["action_types"].remove("lab_http_probe")
    d["allowed"]["capabilities"].remove(CAP_B)
    d["max_episode_steps"] = 64


def test_b1f_all_four_signals_removed_is_the_decisive_regression(tmp_path):
    """The exact escape from the final independent audit.

    Before B-1 this produced 6 unbounded governed executions. It must now
    produce at most five — and preferably zero, because the protected
    capability is refused outright.
    """
    path = write_policy_copy(tmp_path, "escape.json", _strip_all_four)
    broker = make_broker_from_policy(path)          # loader accepts (cap 64 legal off-D2)
    assert broker.policy.max_episode_steps == 64
    # The protected capability is still authorised by the artifact ...
    assert CAP_A in broker.policy.allowed_capabilities
    # ... but no governed contract is recognised, so execution is refused.
    gov = RT.resolve_capability_governance(broker.policy)
    assert gov.contract_id == ""
    assert gov.ceiling == 0
    assert gov.refuses_protected_capability is True

    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv == 0, "a protected capability must not execute without a contract"
    assert inv <= 5
    assert term.governance_refuses_protected is True


def test_b1f2_all_four_signals_removed_via_step_loop(tmp_path):
    """Same escape driven directly through Runtime.step(), 40 attempts."""
    broker = make_broker_from_policy(
        write_policy_copy(tmp_path, "escape2.json", _strip_all_four))
    runtime, caps = build_runtime(tmp_path, broker)
    scope = ScopeV0(mission_id=D2_ENG, targets=("dvwa",),
                    allowed_action_types=("recon_service_probe",),
                    allowed_capabilities=(CAP_A,), max_impact=2.0)
    for i in range(40):
        runtime.step(RuntimeContext(
            mission_id=D2_ENG, objective_id="o", iteration=i, scope=scope,
            view={"mission_name": "x", "mission_id": D2_ENG, "iteration": i,
                  "target": "dvwa", "objective_id": "o",
                  "candidates": [_cand(f"S-{i}")]}))
    assert sum(c.invocation_count for c in caps.values()) == 0


def test_b1f3_refused_capability_never_starts_the_broker_lifecycle(tmp_path):
    """A refused protected capability leaves an AUTHORIZED-only receipt."""
    broker = make_broker_from_policy(
        write_policy_copy(tmp_path, "escape3.json", _strip_all_four))
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, _term = count_pep(runtime, budget_mission(9), 9)
    assert inv == 0
    states = {}
    for receipt in broker.receipt_store.values():
        states[receipt.status.name] = states.get(receipt.status.name, 0) + 1
    assert states.get("SUCCEEDED", 0) == 0
    assert states.get("STARTED", 0) == 0
    assert states.get("AUTHORIZED", 0) > 0, "authorization happened, execution did not"


# ══════════════════════════════════════════════════════════════════════════
# B1-G — manual BrokerPolicy, caps 0 / 6 / 64, no D2 labels, no rate limiter
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cap", [0, 6, 64])
def test_b1g_manual_broker_policy_cannot_bypass(tmp_path, cap):
    broker = manual_broker(cap)
    assert broker.rate_limiter is None, "the limiter must not be what stops us"
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
    assert inv <= 5, f"manual BrokerPolicy cap={cap} executed {inv} steps"
    assert term.governance_refuses_protected is True
    assert inv == 0


def test_b1g2_manual_policy_with_honest_d2_identity_is_capped_at_five(tmp_path):
    """Same object, but claiming the approved D2 contract -> runs, capped at 5."""
    for cap in (0, 6, 64):
        tmp = tmp_path / f"honest{cap}"
        tmp.mkdir()
        broker = manual_broker(cap, engagement_id=D2_ENG,
                              policy_name="engagement-d2-v1",
                              action_types=("recon_service_probe", "lab_http_probe"),
                              capabilities=(CAP_A, CAP_B))
        runtime, caps = build_runtime(tmp, broker)
        _pep, inv, term = count_pep(runtime, budget_mission(99), 99)
        assert inv == 5, f"cap={cap} produced {inv} invocations"
        assert term.governed_step_ceiling == 5
        assert term.governance_contract == D2_ENG


# ══════════════════════════════════════════════════════════════════════════
# B1-H — direct Runtime.step() against the protected capability
# ══════════════════════════════════════════════════════════════════════════

def test_b1h_direct_step_loop_under_d2_is_capped_at_five(tmp_path, monkeypatch):
    broker = manual_broker(64, engagement_id=D2_ENG, policy_name="engagement-d2-v1",
                           action_types=("recon_service_probe", "lab_http_probe"),
                           capabilities=(CAP_A, CAP_B))
    assert broker.rate_limiter is None
    runtime, caps = build_runtime(tmp_path, broker)
    scope = ScopeV0(mission_id=D2_ENG, targets=("dvwa",),
                    allowed_action_types=("recon_service_probe",),
                    allowed_capabilities=(CAP_A,), max_impact=2.0)
    for i in range(40):
        runtime.step(RuntimeContext(
            mission_id=D2_ENG, objective_id="o", iteration=i, scope=scope,
            view={"mission_name": "x", "mission_id": D2_ENG, "iteration": i,
                  "target": "dvwa", "objective_id": "o",
                  "candidates": [_cand(f"H-{i}")]}))
    inv = sum(c.invocation_count for c in caps.values())
    assert inv == 5, inv
    assert runtime._step_budget.used == 5


# ══════════════════════════════════════════════════════════════════════════
# B1-I — no rate limiter anywhere in the adversarial set
# ══════════════════════════════════════════════════════════════════════════

def test_b1i_five_step_invariant_holds_without_a_rate_limiter(tmp_path):
    """The invariant must come from the registry, never from the limiter."""
    for cap, identity in ((0, "neutral"), (6, "neutral"), (64, "neutral"),
                          (64, "d2"), (0, "d2")):
        tmp = tmp_path / f"rl{cap}{identity}"
        tmp.mkdir()
        if identity == "d2":
            broker = manual_broker(cap, engagement_id=D2_ENG,
                                  policy_name="engagement-d2-v1",
                                  action_types=("recon_service_probe", "lab_http_probe"),
                                  capabilities=(CAP_A, CAP_B))
        else:
            broker = manual_broker(cap)
        assert broker.rate_limiter is None
        runtime, caps = build_runtime(tmp, broker)
        _pep, inv, _term = count_pep(runtime, budget_mission(99), 99)
        assert inv <= 5, f"cap={cap} identity={identity} -> {inv} invocations"


# ══════════════════════════════════════════════════════════════════════════
# B1-J — D1 regression: D1 must remain uncapped and must not become D2
# ══════════════════════════════════════════════════════════════════════════

def test_b1j_canonical_d1_is_uncapped_and_not_d2(tmp_path):
    broker = make_broker_from_policy(D1_POLICY_PATH)
    runtime, caps = build_runtime(tmp_path, broker)
    _pep, inv, term = count_pep(runtime, budget_mission(6, mission_id="d1-governed-action"),
                                6)
    assert term.d2_recognized is False
    assert term.governance_contract == "d1-governed-action"
    assert term.governed_step_ceiling == 0
    assert term.governance_refuses_protected is False
    assert inv == 6, "D1 keeps its own budget; B-1 must not turn D1 into D2"


def test_b1j2_d1_does_not_inherit_the_d2_ceiling():
    broker = make_broker_from_policy(D1_POLICY_PATH)
    gov = RT.resolve_capability_governance(broker.policy)
    assert gov.ceiling == 0
    assert gov.contract_id == "d1-governed-action"


def test_b1j3_d1_capability_surface_is_not_mistaken_for_d2(tmp_path):
    """A D1-shaped vocabulary WITHOUT D1 identity must fail closed, not run."""
    broker = manual_broker(64, engagement_id="neutral", policy_name="neutral-policy",
                           capabilities=(CAP_A,))
    assert RT.resolve_capability_governance(broker.policy).refuses_protected_capability is True


# ══════════════════════════════════════════════════════════════════════════
# Loader policy validation is preserved (section 8)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("bad", [6, 64, 0, -1, None, True, False, "5", 5.0, 5.5,
                                 [], 10 ** 9, "x"])
def test_loader_still_rejects_every_non_five_d2_cap(tmp_path, bad):
    path = write_policy_copy(tmp_path, "bad.json",
                             lambda d: d.update(max_episode_steps=bad))
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(path)


def test_loader_still_rejects_an_absent_d2_cap(tmp_path):
    path = write_policy_copy(tmp_path, "absent.json", lambda d: d.pop("max_episode_steps"))
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(path)


def test_canonical_d2_artifact_is_untouched_and_still_loads():
    """The real artifact declares exactly five and the loader accepts it."""
    policy = json.loads(D2_POLICY_PATH.read_text())
    assert policy["max_episode_steps"] == 5
    assert RT.GOVERNED_ENGAGEMENT_CONTRACTS[D2_ENG]["max_episode_steps"] == 5


# ══════════════════════════════════════════════════════════════════════════
# Unrelated engagement semantics must be untouched
# ══════════════════════════════════════════════════════════════════════════

def test_non_protected_capability_keeps_legacy_declared_budget(tmp_path):
    """Bootstrap / fixture.inspect style policies are unaffected by B-1."""
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="walk", policy_name="walk", allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
        max_impact_per_action=0.0, max_episode_steps=0))
    gov = RT.resolve_capability_governance(broker.policy)
    assert gov.refuses_protected_capability is False
    assert gov.contract_id == ""
    assert gov.ceiling == 0


def test_stage_pep_refusal_is_reported_as_a_stage_failure(tmp_path):
    """The refusal surfaces as an honest PEP-stage failure, not a success."""
    broker = make_broker_from_policy(
        write_policy_copy(tmp_path, "esc.json", _strip_all_four))
    runtime, caps = build_runtime(tmp_path, broker)
    outs = []
    _t, term = runtime.run_episode(budget_mission(9), max_iterations=9,
                                   episode_outputs=outs)
    assert "objective met" not in term.reason
    assert term.final_stage == "pep"
    # stage_outputs carries the stage's output mapping; the refusal is explicit.
    pep_out = outs[-1]["pep"]
    assert pep_out["protected_capability_refused"] is True
    assert pep_out["capability"] == CAP_A
    assert pep_out["governance_contract"] == ""
    assert "protected capability" in term.reason