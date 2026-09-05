"""
belief_transition_policy.py — Brain-owned Protocol for D-5 belief transitions.

GLM §4: ADD (brain) — A Protocol covering exactly the surface of the one
runtime call (conceptually `BeliefTransitionPolicy`). Signature-only; no
default implementation; no arena import; no runnable policy logic.

GLM §4: P2 RUNTIME COMPOSITION — The port is deliberately unbound in the
walking skeleton. Born unbound-and-raising is the correct birth state.

GLM §4: TICKETS — P5-BIND-1: the canonical brain-side binding of this
port is a P5 deliverable. The port must never accumulate a brain-side
policy implementation before P5.
"""
from typing import Protocol, Tuple
from orchestrator.brain.defeater_types import DefeaterOutcome


class BeliefTransitionPolicy(Protocol):
    """Protocol for the D-5 V2 belief-update policy.

    The single method signature matches the D-5 V2 policy contract
    (frozen in arena/defeater.py:172, unchanged). The implementation
    lives in arena/defeater.py (P5-BIND-1 ticket). Brain depends only
    on this signature; arena implements it via the adapter.
    """

    def apply_belief_transition(
        self,
        prior_state: str,
        prior_confidence: float,
        outcome: DefeaterOutcome,
    ) -> Tuple[float, str]:
        """Apply the frozen belief-update policy.

        Args:
            prior_state: Current hypothesis state string.
            prior_confidence: Current confidence value.
            outcome: The DefeaterOutcome.

        Returns:
            (posterior_confidence, posterior_state)

        Raises:
            ValueError if outcome is unrecognized.
            BeliefTransitionPolicyNotBound if the port is not bound.
        """
        ...


class BeliefTransitionPolicyNotBound(Exception):
    """Raised when the BeliefTransitionPolicy port is not bound.

    GLM §4: DEFAULT BEHAVIOR — Unbound port raises, with a named error.
    Never a silent no-op. Fail-closed is the house style.
    """
    pass
