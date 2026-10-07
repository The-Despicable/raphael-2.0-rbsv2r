"""hypothesis.py — ImprovementHypothesis + falsifiable evaluation records (RSI-1 A.3/B.3).

A hypothesis is a diagnosis + causal claim + falsification condition, backed by
experience/evidence references. It is NEVER an execution authorization, an
established fact, or permission to touch protected code. Status lifecycle:
proposed → under_evaluation → (supported | rejected | inconclusive).
Nothing self-promotes: only a recorded evaluation result (from the offline
evaluation framework) sets supported/rejected, and 'accepted-for-review' policy
status still requires the human promotion milestone that does not exist yet.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

SCHEMA_VERSION = 1
STATUSES = ("proposed", "under_evaluation", "supported", "rejected", "inconclusive")
PERMITTED_DIMENSIONS = ("candidate_order", "bounded_retry")  # ExplorationPolicy v0 surface


class HypothesisError(ValueError):
    pass


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ImprovementHypothesis:
    hypothesis_id: str
    problem: str                       # observed problem/opportunity
    causal_claim: str                  # "changing X will improve Y because Z"
    evidence_refs: Tuple[str, ...]     # ExperienceNode identities (must exist)
    permitted_dimensions: Tuple[str, ...]
    expected_effect: str               # measurable prediction
    falsification_condition: str       # decided BEFORE evaluation
    confounders: Tuple[str, ...] = ()
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.hypothesis_id or not self.problem or not self.causal_claim:
            raise HypothesisError("id, problem, and causal_claim are required")
        if not self.evidence_refs:
            raise HypothesisError(
                "a hypothesis must reference at least one experience node")
        if not self.falsification_condition:
            raise HypothesisError(
                "a falsification condition must be declared before evaluation")
        if self.status not in STATUSES:
            raise HypothesisError(f"status must be one of {STATUSES}")
        bad = [d for d in self.permitted_dimensions if d not in PERMITTED_DIMENSIONS]
        if bad:
            raise HypothesisError(
                f"dimensions {bad} are not permitted evolvable strategy parameters "
                f"(allowed: {PERMITTED_DIMENSIONS})")

    def canonical_dict(self) -> Dict[str, Any]:
        return {
            "causal_claim": self.causal_claim,
            "confounders": list(self.confounders),
            "created_at": self.created_at,
            "evidence_refs": list(self.evidence_refs),
            "expected_effect": self.expected_effect,
            "falsification_condition": self.falsification_condition,
            "hypothesis_id": self.hypothesis_id,
            "permitted_dimensions": list(self.permitted_dimensions),
            "problem": self.problem,
            "schema_version": self.schema_version,
            "status": self.status,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(_stable(self.canonical_dict()).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImprovementHypothesis":
        declared = data.pop("content_hash", None)
        h = cls(**data)
        h.validate()
        if declared is not None and declared != h.content_hash():
            raise HypothesisError("content_hash mismatch")
        return h

    def with_status(self, new_status: str) -> "ImprovementHypothesis":
        return ImprovementHypothesis(**{**self.canonical_dict(), "status": new_status})


@dataclass(frozen=True)
class FalsifiableEvaluation:
    """Records an evaluation against the hypothesis's pre-declared criterion.

    The verdict is a mechanical mapping from the evaluation report's fields —
    never an LLM narrative. `criterion_met=False` ⇒ supported only when the
    expected effect was measured; otherwise rejected/inconclusive per the
    declared rule below."""
    hypothesis_id: str
    experiment_id: str
    candidate_verified_rate: float
    baseline_verified_rate: float
    hard_violations: int
    exclusions: int
    criterion: str = ""
    decided_at: float = field(default_factory=time.time)

    RULE = ("supported iff candidate verified-rate > baseline AND hard_violations "
            "== 0; rejected iff criterion falsified (no improvement or any "
            "violation); inconclusive when exclusions dominate")

    def verdict(self) -> str:
        if self.hard_violations > 0:
            return "rejected"          # safety violations are never compensable
        if self.exclusions > 0 and self.candidate_verified_rate <= self.baseline_verified_rate:
            return "inconclusive"
        if self.candidate_verified_rate > self.baseline_verified_rate:
            return "supported"
        return "rejected"
