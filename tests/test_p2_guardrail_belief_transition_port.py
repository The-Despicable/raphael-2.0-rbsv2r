"""
P2 Guardrail Test: BeliefTransitionPolicy port enforcement (GLM RC-B section 4)

Per GLM §4:
- ADD: unbound-port-raises (fail-closed proof)
- ADD: adapter-conforms-to-Protocol

GLM §4: DEFAULT BEHAVIOR — Unbound port raises, with a named error.
Never a silent no-op. Fail-closed is the house style.

GLM §4: TICKETS — P5-BIND-1: the canonical brain-side binding of this
port is a P5 deliverable. The port must never accumulate a brain-side
policy implementation before P5.
"""
import pytest


def test_unbound_port_raises():
    """GLM RC-B section 4: unbound port must raise BeliefTransitionPolicyNotBound.

    A HypothesisManager with belief_transition_policy=None must raise
    BeliefTransitionPolicyNotBound when apply_defeater_result is called.
    Never a silent no-op.
    """
    from orchestrator.brain.hypothesis import HypothesisManager
    from orchestrator.brain.evidence import EvidenceGraph
    from orchestrator.brain.world import WorldModel
    from orchestrator.brain.belief_transition_policy import BeliefTransitionPolicyNotBound
    from arena.defeater import DefeaterResult, DefeaterOutcome

    # Create HypothesisManager WITHOUT binding the port
    hm = HypothesisManager(
        evidence_graph=EvidenceGraph(),
        world_model=WorldModel(evidence_graph=EvidenceGraph()),
    )
    # Do NOT bind belief_transition_policy — it defaults to None

    # Create a minimal hypothesis
    hm.propose(
        statement="test",
        entity_ids=["e1"],
        evidence_ids=[],
        proposed_by="test",
    )
    h_id = list(hm.hypotheses.keys())[0]

    # Create a minimal defeater result
    dr = DefeaterResult(
        defeater_id="df_test",
        hypothesis_id=h_id,
        outcome=DefeaterOutcome.TRIGGERED,
    )

    # Calling apply_defeater_result with unbound port must raise
    with pytest.raises(BeliefTransitionPolicyNotBound):
        hm.apply_defeater_result(hypothesis_id=h_id, defeater_result=dr)


def test_adapter_conforms_to_protocol():
    """GLM RC-B section 4: adapter must conform to BeliefTransitionPolicy Protocol.

    The arena-side DefeaterPolicyAdapter must implement the
    BeliefTransitionPolicy Protocol surface.
    """
    from arena.defeater_policy_adapter import DefeaterPolicyAdapter
    from orchestrator.brain.belief_transition_policy import BeliefTransitionPolicy
    from orchestrator.brain.defeater_types import DefeaterOutcome

    adapter = DefeaterPolicyAdapter()

    # Verify the adapter has the required method
    assert hasattr(adapter, "apply_belief_transition"), (
        "DefeaterPolicyAdapter must implement apply_belief_transition"
    )

    # Verify the method signature matches the Protocol
    import inspect
    sig = inspect.signature(adapter.apply_belief_transition)
    params = list(sig.parameters.keys())
    assert "prior_state" in params, "Adapter must accept prior_state"
    assert "prior_confidence" in params, "Adapter must accept prior_confidence"
    assert "outcome" in params, "Adapter must accept outcome"

    # Verify the adapter delegates to arena.defeater (byte-identical policy)
    from arena import defeater as _arena_defeater
    test_cases = [
        ("POSTULATED", 0.3, DefeaterOutcome.TRIGGERED),
        ("POSTULATED", 0.7, DefeaterOutcome.TRIGGERED),
        ("DOUBTFUL", 0.2, DefeaterOutcome.NOT_TRIGGERED),
        ("DOUBTFUL", 0.5, DefeaterOutcome.NOT_TRIGGERED),
        ("ABANDONED", 0.1, DefeaterOutcome.TRIGGERED),
        ("POSTULATED", 0.5, DefeaterOutcome.INCONCLUSIVE),
    ]
    for prior_state, prior_conf, outcome in test_cases:
        adapter_result = adapter.apply_belief_transition(
            prior_state=prior_state, prior_confidence=prior_conf, outcome=outcome
        )
        arena_result = _arena_defeater.apply_belief_transition(
            prior_state=prior_state, prior_confidence=prior_conf, outcome=outcome
        )
        assert adapter_result == arena_result, (
            f"Adapter must delegate to arena.defeater exactly. "
            f"State={prior_state}, conf={prior_conf}, outcome={outcome}: "
            f"adapter={adapter_result}, arena={arena_result}"
        )


def test_bound_port_works():
    """GLM RC-B section 4: when the port IS bound, the policy works.

    Verify that binding the arena adapter to the port allows
    apply_defeater_result to produce a BeliefTransition.
    """
    from orchestrator.brain.hypothesis import HypothesisManager
    from orchestrator.brain.evidence import EvidenceGraph
    from orchestrator.brain.world import WorldModel
    from orchestrator.brain.defeater_types import BeliefTransition, DefeaterOutcome
    from arena.defeater import DefeaterResult
    from arena.defeater_policy_adapter import DefeaterPolicyAdapter

    hm = HypothesisManager(
        evidence_graph=EvidenceGraph(),
        world_model=WorldModel(evidence_graph=EvidenceGraph()),
        belief_transition_policy=DefeaterPolicyAdapter(),
    )

    # Create a minimal hypothesis
    hm.propose(
        statement="test",
        entity_ids=["e1"],
        evidence_ids=[],
        proposed_by="test",
    )
    h_id = list(hm.hypotheses.keys())[0]

    # Create a TRIGGERED defeater result
    dr = DefeaterResult(
        defeater_id="df_test",
        hypothesis_id=h_id,
        outcome=DefeaterOutcome.TRIGGERED,
    )

    # With port bound, apply_defeater_result should produce a BeliefTransition
    bt = hm.apply_defeater_result(hypothesis_id=h_id, defeater_result=dr)
    assert bt is not None, "With port bound, TRIGGERED should produce a BeliefTransition"
    assert isinstance(bt, BeliefTransition)
    assert bt.defeater_result_id == dr.result_id
