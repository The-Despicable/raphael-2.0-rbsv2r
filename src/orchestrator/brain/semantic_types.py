"""
semantic_types.py — Brain-owned SemanticInferenceSuccess data type (RC-B re-home).

Original location: src/arena/semantic_inference.py (RC-B: brain has zero
runtime imports from arena per v4 INV-5).

This is a pure data class with no Arena-specific logic. It is the D-4
typed LLM semantic inference contract. It belongs in the brain closure
because it is a cognitive evidence input, not an Arena evaluation contract.

Arena may import from this module. The original SemanticInferenceSuccess
in arena/semantic_inference.py remains in place for backward compatibility
but is no longer the canonical import path.
"""
from dataclasses import dataclass, field
from typing import Optional, List
import uuid


@dataclass
class SemanticInferenceSuccess:
    """D-4 typed LLM semantic inference success artifact."""
    inference_id: str
    claim: str
    category: str
    confidence: float
    model_id: str = ""
    provider: str = ""
    evidence_ids: List[str] = field(default_factory=list)
    timestamp: float = 0.0

    @staticmethod
    def make(
        claim: str,
        category: str,
        confidence: float,
        model_id: str = "",
        provider: str = "",
        evidence_ids: Optional[List[str]] = None,
    ) -> "SemanticInferenceSuccess":
        return SemanticInferenceSuccess(
            inference_id=f"SI_{uuid.uuid4().hex[:12]}",
            claim=claim,
            category=category,
            confidence=confidence,
            model_id=model_id,
            provider=provider,
            evidence_ids=evidence_ids or [],
            timestamp=0.0,
        )
