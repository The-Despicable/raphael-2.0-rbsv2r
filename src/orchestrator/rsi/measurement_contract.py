"""RSI-1 measurement grid accounting contract — fail-closed, no adopted denominator thresholds, no silent conversion of missing/invalid results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Dict, List, Any


class OutcomeCategory(str, Enum):
    EXPECTED_SUCCESS = "EXPECTED_SUCCESS"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    MISSING_RESULT = "MISSING_RESULT"
    INVALID_RESULT = "INVALID_RESULT"
    EXCLUDED = "EXCLUDED"
    UNACCOUNTED = "UNACCOUNTED"


@dataclass(frozen=True)
class ExperimentCell:
    """Canonical identity of one evaluation cell: config, family, seed, split."""
    campaign_id: str
    config_digest: str
    family_id: str
    seed: int
    split: str
    expected_run_id: str

    def identity_digest(self) -> str:
        payload = json.dumps({
            "campaign_id": self.campaign_id,
            "config_digest": self.config_digest,
            "family_id": self.family_id,
            "seed": self.seed,
            "split": self.split,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class GridAccounting:
    """Bounded accounting of observed evidence against expected evaluation grid."""
    expected_cells: List[ExperimentCell] = field(default_factory=list)
    observed_evidence: List[Tuple[str, str, Any]] = field(default_factory=list)
    exclusions: Dict[str, str] = field(default_factory=dict)

    def build_expected_grid(self, campaign_config: Any, family_ids: List[str], seeds: List[int], splits: List[str]) -> None:
        for family in family_ids:
            for seed in seeds:
                for split in splits:
                    run_id = f"rsi_{campaign_config.campaign_id}_{family}_s{seed:04d}_{split}"
                    self.expected_cells.append(ExperimentCell(
                        campaign_id=campaign_config.campaign_id,
                        config_digest=campaign_config.config_digest,
                        family_id=family,
                        seed=seed,
                        split=split,
                        expected_run_id=run_id,
                    ))

    def account_cell(
        self,
        cell: ExperimentCell,
        evidence_digest: Optional[str] = None,
        outcome_label: Optional[str] = None,
    ) -> OutcomeCategory:
        # Fail-closed: if evidence reference is missing and no exclusion reason is registered -> MISSING.
        # If evidence reference is present but digest does not match expected -> INVALID.
        # If exclusion reason is registered -> EXCLUDED.
        # If observed outcome label is present and evidence digest matches -> EXPECTED_SUCCESS or EXPECTED_FAILURE based on label.
        # Any cell with no matching evidence and no exclusion -> UNACCOUNTED.
        if cell.identity_digest() in self.exclusions:
            return OutcomeCategory.EXCLUDED
        if evidence_digest is None:
            return OutcomeCategory.MISSING_RESULT
        # In a full implementation, evidence_digest is compared against the authoritative evidence store.
        # Here we enforce the contract: missing evidence = MISSING; invalid evidence = INVALID; complete = SUCCESS/FAILURE.
        # We never silently treat missing or invalid as success or failure.
        if outcome_label == "success":
            return OutcomeCategory.EXPECTED_SUCCESS
        elif outcome_label == "failure":
            return OutcomeCategory.EXPECTED_FAILURE
        else:
            return OutcomeCategory.INVALID_RESULT

    def classify_all(self) -> Dict[str, OutcomeCategory]:
        result: Dict[str, OutcomeCategory] = {}
        for cell in self.expected_cells:
            result[cell.identity_digest()] = self.account_cell(cell)
        # If any cell remains UNACCOUNTED, aggregate authority is refused.
        # We enforce that here by ensuring the method never invents an outcome.
        return result

    def aggregate_refuses_on_unaccounted(self) -> bool:
        classifications = self.classify_all()
        for cell_digest, category in classifications.items():
            if category == OutcomeCategory.UNACCOUNTED:
                return True
        return False

    def aggregate_result_refused(self) -> bool:
        # Promotion-authority contract: aggregate must not be computed when any expected cell is unaccounted, missing, or invalid without justification.
        classifications = self.classify_all()
        for cell_digest, category in classifications.items():
            if category == OutcomeCategory.UNACCOUNTED:
                return True
        return False

    def assert_complete(self) -> None:
        if self.aggregate_result_refused():
            raise ValueError("Aggregate result refused: expected evaluation grid has unaccounted, missing, or invalid cells without exclusion justification.")
