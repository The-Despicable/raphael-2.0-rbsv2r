"""
defeater_types.py — Brain-owned Defeater data types (RC-B re-home).

Original location: src/arena/defeater.py (RC-B: brain has zero runtime
imports from arena per v4 INV-5).

These are pure data types and a pure function (apply_belief_transition)
with no Arena-specific logic. They belong in the brain closure because
they are cognitive contracts (D-5 defeater/counterfactual reasoning),
not Arena evaluation contracts.

Arena may import from this module (Arena already imports from brain
extensively). This breaks the brain→arena runtime import edge by moving
the types to brain, where they are owned by the cognitive layer that
produces and consumes them.

The original DefeaterResult/DefeaterOutcome/BeliefTransition/apply_belief_transition
in arena/defeater.py remain in place for backward compatibility but are
no longer the canonical import path.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import uuid


class DefeaterOutcome(str, Enum):
    """Seven-gate defeater outcome states."""
    TRIGGERED = "TRIGGERED"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_TESTABLE = "NOT_TESTABLE"


@dataclass
class DefeaterResult:
    """D-5 Defeater result artifact."""
    result_id: str
    hypothesis_id: str
    outcome: DefeaterOutcome
    reliability_condition_id: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    producer: str = "brain"

    @staticmethod
    def make(
        hypothesis_id: str,
        outcome: DefeaterOutcome,
        reliability_condition_id: Optional[str] = None,
        evidence_ids: Optional[List[str]] = None,
    ) -> "DefeaterResult":
        return DefeaterResult(
            result_id=f"DR_{uuid.uuid4().hex[:12]}",
            hypothesis_id=hypothesis_id,
            outcome=outcome,
            reliability_condition_id=reliability_condition_id,
            evidence_ids=evidence_ids or [],
            timestamp=0.0,
        )


@dataclass
class BeliefTransition:
    """D-5 belief transition artifact: defeater → hypothesis change."""
    transition_id: str
    hypothesis_id: str
    defeater_result_id: str
    prior_confidence: float
    post_confidence: float
    prior_state: str
    post_state: str
    timestamp: float = 0.0

    @staticmethod
    def make(
        hypothesis_id: str,
        defeater_result_id: str,
        prior_confidence: float,
        post_confidence: float,
        prior_state: str,
        post_state: str,
    ) -> "BeliefTransition":
        return BeliefTransition(
            transition_id=f"BT_{uuid.uuid4().hex[:12]}",
            hypothesis_id=hypothesis_id,
            defeater_result_id=defeater_result_id,
            prior_confidence=prior_confidence,
            post_confidence=post_confidence,
            prior_state=prior_state,
            post_state=post_state,
            timestamp=0.0,
        )


def apply_belief_transition(
    prior_confidence: float,
    outcome: DefeaterOutcome,
) -> tuple:
    """Apply the frozen V2 belief transition policy.

    Returns (post_confidence, post_state_str).

    V2 policy:
    - TRIGGERED: confidence drops to max(0, prior * 0.3)
    - NOT_TRIGGERED: confidence rises to min(1.0, prior + 0.1)
    - INCONCLUSIVE: no change
    - NOT_TESTABLE: no change
    """
    if outcome == DefeaterOutcome.TRIGGERED:
        return (max(0.0, prior_confidence * 0.3), "WEAKENED")
    elif outcome == DefeaterOutcome.NOT_TRIGGERED:
        return (min(1.0, prior_confidence + 0.1), "REINFORCED")
    else:
        return (prior_confidence, "UNCHANGED")
