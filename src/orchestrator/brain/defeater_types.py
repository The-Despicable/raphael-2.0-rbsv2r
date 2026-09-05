"""
defeater_types.py — Brain-owned D-5 vocabulary types (RC-B GLM disposition).

GLM §4 binding: MOVE (verbatim) DefeaterOutcome and BeliefTransition
from arena/defeater.py to a brain-owned module. Byte-identical class
bodies. Only module path and imports change.

GLM §4 binding: arena/defeater.py re-imports them from brain
(arena → brain: the canonical driver direction, consistent with the
existing ablation_runner → orchestrator.brain edge).

The policy function apply_belief_transition, the D-5 V2 policy tables,
and all transition semantics STAY byte-identical in arena/defeater.py.
P5-BIND-1: the canonical brain-side binding of the policy port is a
P5 deliverable.

These types are vocabulary, not policy. Their shape is frozen by the
same D-5 tests. A verbatim move makes zero semantic decisions.
"""
from enum import Enum
from dataclasses import dataclass, field
import time
import uuid


# GLM RC-B §4: POLICY_VERSION is a vocabulary constant, moved here
# alongside the types it annotates. Its semantics remain P5-owned;
# P5-BIND-1 will move it deliberately when P5 begins.
POLICY_VERSION = "D5_V2_2026-07-26"


# ── Defeater Outcome ──────────────────────────────────────────

class DefeaterOutcome(str, Enum):
    """Outcome of a defeater evaluation against evidence."""
    NOT_TRIGGERED = "not_triggered"   # Evidence contradicts the defeating condition
    TRIGGERED = "triggered"           # Defeating condition observed
    INCONCLUSIVE = "inconclusive"     # Evidence cannot determine the condition
    NOT_TESTABLE = "not_testable"     # No authorized discriminating action exists


# ── BeliefTransition (typed causal artifact) ──────────────────

@dataclass(frozen=True)
class BeliefTransition:
    """A typed artifact proving a defeater-driven belief change.

    Every TRIGGERED or NOT_TRIGGERED outcome that changes hypothesis
    confidence or state produces exactly one BeliefTransition.

    INCONCLUSIVE outcomes MUST NOT produce a BeliefTransition.

    Causal chain:
      DefeaterResult → BeliefTransition → Hypothesis state change
        → Planner consumes post-transition state
    """
    transition_id: str = field(default_factory=lambda: f"bt_{uuid.uuid4().hex[:12]}")
    hypothesis_id: str = ""
    defeater_result_id: str = ""
    outcome: DefeaterOutcome = DefeaterOutcome.INCONCLUSIVE

    prior_confidence: float = 0.0
    posterior_confidence: float = 0.0
    prior_state: str = ""
    posterior_state: str = ""

    # Identifies the frozen policy that produced this transition
    policy_version: str = POLICY_VERSION

    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "transition_id": self.transition_id,
            "hypothesis_id": self.hypothesis_id,
            "defeater_result_id": self.defeater_result_id,
            "outcome": self.outcome.value,
            "prior_confidence": self.prior_confidence,
            "posterior_confidence": self.posterior_confidence,
            "prior_state": self.prior_state,
            "posterior_state": self.posterior_state,
            "policy_version": self.policy_version,
            "generated_at": self.generated_at,
        }
