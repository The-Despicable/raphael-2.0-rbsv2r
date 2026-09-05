"""
defeater_policy_adapter.py — Arena-side adapter implementing the brain-owned
BeliefTransitionPolicy port.

GLM §4: ADD (arena) — An adapter implementing the port by delegating to
arena.defeater.apply_belief_transition, bound at every arena-side
construction/wiring site of the hypothesis machinery.

The policy function, D-5 V2 tables, and all transition semantics STAY
byte-identical in arena/defeater.py. This adapter is a thin delegation
layer; it adds no semantics.
"""
from typing import Tuple
from orchestrator.brain.belief_transition_policy import BeliefTransitionPolicy
from orchestrator.brain.defeater_types import DefeaterOutcome
from arena import defeater as _arena_defeater


class DefeaterPolicyAdapter(BeliefTransitionPolicy):
    """Arena-side adapter implementing BeliefTransitionPolicy.

    Delegates to arena.defeater.apply_belief_transition (byte-identical
    to the D-5 V2 policy). The adapter is migration scaffolding;
    refinable/removable at P5/P7 per GLM §4.
    """

    def apply_belief_transition(
        self,
        prior_state: str,
        prior_confidence: float,
        outcome: DefeaterOutcome,
    ) -> Tuple[float, str]:
        return _arena_defeater.apply_belief_transition(
            prior_state=prior_state,
            prior_confidence=prior_confidence,
            outcome=outcome,
        )
