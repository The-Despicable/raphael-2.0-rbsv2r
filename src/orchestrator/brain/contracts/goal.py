"""goal.py — PROPOSED goal contract with verified completion.

Why this exists
---------------
Today there is no goal type with a completion rule. The nearest structure
is ``Action`` (src/orchestrator/brain/action.py:149), which expresses
``impact_estimate: float`` as "expected impact on objective"
(src/orchestrator/brain/action.py:173) — a forward-looking estimate that
is never checked against anything, and whose satisfaction is nowhere
recorded. Nothing in the tree can mechanically answer "is this goal
actually done?", so the only available answer is an assertion.

That is the defect this module addresses.

INVARIANT: a goal is ``SATISFIED`` only when its predicate is verified from
evidence by a registered verifier. An LLM assertion of "done" never
satisfies a goal. Concretely, ``GoalStatus.SATISFIED`` requires
``GoalPredicate.requires_evidence`` to hold and the predicate to come back
``PredicateAssessment.ESTABLISHED`` with non-empty evidence; a model turn,
a heuristic score, or the absence of a contradicting observation is not
sufficient.

The module reuses ``PredicateRef`` from ``action_spec`` so that a goal's
success predicates and an action's expected effects are stated in one
vocabulary.

This module is a contract proposal. Nothing in the runtime stage graph
imports it.

Schema version: 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from orchestrator.brain.contracts.action_spec import PredicateRef


class GoalStatus(str, Enum):
    """Lifecycle of a goal. ``SATISFIED`` is evidence-gated, see module docstring."""

    PENDING = "pending"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class GoalPredicate:
    """One condition that must hold for a goal to be satisfied."""

    predicate_id: str
    statement: str
    assessment_criteria: str = ""     # what a verifier must check
    requires_evidence: bool = True    # False only for criteria no evidence could ever bear on
    validity_window: tuple = ()       # tuple[(start, end), ...]; empty means unbounded


@dataclass(frozen=True)
class Goal:
    """An objective with verified success predicates."""

    goal_id: str
    objective: str
    success_predicates: tuple = ()  # tuple[PredicateRef, ...]
    constraints: tuple = ()         # tuple[str, ...]
    priority: int = 0
    status: GoalStatus = GoalStatus.PENDING

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "objective": self.objective,
            "success_predicates": [
                {"subject_kind": p.subject_kind, "predicate": p.predicate, "value_kind": p.value_kind}
                for p in self.success_predicates
            ],
            "constraints": list(self.constraints),
            "priority": self.priority,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class GoalEvaluation:
    """Result of checking a goal against its predicates.

    ``all_established`` is the only input to ``GoalStatus.SATISFIED``;
    ``assessed_by`` MUST name a registered verifier, and each established
    predicate MUST carry evidence.
    """

    goal_id: str
    all_established: bool
    established_predicate_ids: tuple = ()  # tuple[str, ...]
    unestablished_predicate_ids: tuple = ()  # tuple[str, ...]
    evidence_ids: tuple = ()                 # tuple[str, ...]
    assessed_by: str = ""
    assessed_at: float = field(default_factory=time.time)
    notes: str = ""

    def satisfied_status(self) -> GoalStatus:
        """SATISFIED only on a full, evidence-backed establishment."""
        if self.all_established and self.assessed_by and self.evidence_ids:
            return GoalStatus.SATISFIED
        return GoalStatus.ACTIVE

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "all_established": self.all_established,
            "established_predicate_ids": list(self.established_predicate_ids),
            "unestablished_predicate_ids": list(self.unestablished_predicate_ids),
            "evidence_ids": list(self.evidence_ids),
            "assessed_by": self.assessed_by,
            "assessed_at": self.assessed_at,
            "notes": self.notes,
        }
