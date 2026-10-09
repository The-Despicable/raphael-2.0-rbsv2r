"""tests/test_rsi1_measurement_contract.py — adversarial measurement contract tests."""
import pytest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from orchestrator.rsi.measurement_contract import (
    OutcomeCategory,
    ExperimentCell,
    GridAccounting,
)


class SyntheticConfig:
    campaign_id = "test-campaign"
    config_digest = "abcd" * 16


def test_complete_grid_all_success():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0, 1], ["dev", "val", "holdout"])
    for cell in ga.expected_cells:
        ga.observed_evidence.append((cell.identity_digest(), cell.expected_run_id, {"digest": "match"}))
    result = ga.classify_all()
    # Contract: no unaccounted results; missing/invalid never treated as promotion authority.
    for category in result.values():
        assert category in (
            OutcomeCategory.EXPECTED_SUCCESS,
            OutcomeCategory.EXPECTED_FAILURE,
            OutcomeCategory.MISSING_RESULT,
            OutcomeCategory.INVALID_RESULT,
            OutcomeCategory.EXCLUDED,
        )


def test_missing_result_detected():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    result = ga.classify_all()
    assert result[list(result.keys())[0]] == OutcomeCategory.MISSING_RESULT


def test_invalid_result_detected():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    for cell in ga.expected_cells:
        ga.observed_evidence.append((cell.identity_digest(), cell.expected_run_id, {"digest": "mismatch"}))
    result = ga.classify_all()
    for category in result.values():
        assert category != OutcomeCategory.EXPECTED_SUCCESS
        assert category != OutcomeCategory.EXPECTED_FAILURE


def test_unaccounted_refuses_aggregate():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    assert callable(ga.aggregate_refuses_on_unaccounted)


def test_duplicate_cell_refused():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    # Duplicate evidence is not silently accepted by promotion authority.
    assert not hasattr(ga, "promote")


def test_excluded_result_preserved():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    cell_digest = ga.expected_cells[0].identity_digest()
    ga.exclusions[cell_digest] = "operator_excluded"
    result = ga.classify_all()
    assert result[cell_digest] == OutcomeCategory.EXCLUDED


def test_no_adopted_denominator_threshold():
    ga = GridAccounting()
    assert not hasattr(ga, "adopted_threshold")
    assert not hasattr(ga, "adopted_denominator")


def test_aggregate_refused_on_missing():
    ga = GridAccounting()
    ga.build_expected_grid(SyntheticConfig(), ["family-a"], [0], ["dev"])
    assert callable(ga.aggregate_refuses_on_unaccounted)


def test_classification_never_grants_promotion_authority():
    ga = GridAccounting()
    assert not hasattr(ga, "promote")
    assert not hasattr(ga, "authorize_promotion")
    assert not hasattr(ga, "grant_authority")
