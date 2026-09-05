"""
plan_decision.py — Brain-owned PlanDecision data type (RC-B re-home).

Original location: src/arena/conclusion.py.
Re-homed to brain per RC-B: brain has zero runtime imports from arena (v4 INV-5).

This module is the CANONICAL home of PlanDecision. The copy in
src/arena/conclusion.py remains for backward compatibility but is
deprecated. Arena modules should import from this module.
"""
from dataclasses import dataclass, field
from typing import Tuple
import time
import uuid


@dataclass(frozen=True)
class PlanDecision:
    """
    Structured output of the Planner — the causal intermediate between
    candidate generation and action execution.
    Brain-owned (RC-B re-home from arena.conclusion).
    """
    decision_id: str = field(default_factory=lambda: f"PD_{uuid.uuid4().hex[:12]}")
    objective_id: str = ""

    # What was considered
    considered_action_ids: Tuple[str, ...] = ()
    rejected_action_ids: Tuple[str, ...] = ()
    selected_action_id: str = ""

    # Why this was chosen
    rationale_codes: Tuple[str, ...] = ()
    estimated_cost: float = 0.0
    estimated_risk: float = 0.0
    estimated_utility: float = 0.0

    # Supporting evidence
    supporting_evidence_ids: Tuple[str, ...] = ()
    supporting_world_query_ids: Tuple[str, ...] = ()
    supporting_hypothesis_ids: Tuple[str, ...] = ()

    # D-5: Defeater transition consumption tracking
    consumed_transition_ids: Tuple[str, ...] = ()

    # Metadata
    generated_at: float = field(default_factory=time.time)
    planner_invocation_id: str = ""

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "objective_id": self.objective_id,
            "considered_count": len(self.considered_action_ids),
            "rejected_count": len(self.rejected_action_ids),
            "selected_action_id": self.selected_action_id,
            "rationale_codes": list(self.rationale_codes),
            "estimated_cost": self.estimated_cost,
            "estimated_risk": self.estimated_risk,
            "estimated_utility": self.estimated_utility,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "supporting_world_query_ids": list(self.supporting_world_query_ids),
            "supporting_hypothesis_ids": list(self.supporting_hypothesis_ids),
            "consumed_transition_ids": list(self.consumed_transition_ids),
            "generated_at": self.generated_at,
            "planner_invocation_id": self.planner_invocation_id,
        }
