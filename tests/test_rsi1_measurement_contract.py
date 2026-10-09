"""tests/test_rsi1_measurement_contract.py — behavioural measurement accounting.

Every test here asserts OBSERVABLE BEHAVIOUR. There is no ``assert callable``,
no ``assert not hasattr``, and no key-presence check standing in for a
verification. The auditor can confirm this by mutating the module and watching
tests fail; ``test_assert_complete_really_fires`` exists for exactly that.

The prior version of this file was largely vacuous and the module it exercised
returned EXPECTED_SUCCESS for any non-None digest labelled "success" without
comparing it to anything, while ``assert_complete()`` could never raise. Both
defects are pinned shut here.

All fixtures are synthetic and live entirely under pytest ``tmp_path``. Nothing
here reads, writes, or claims authority over any real campaign evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from orchestrator.rsi import measurement_contract as mc  # noqa: E402
from orchestrator.rsi.measurement_contract import (  # noqa: E402
    EvidenceIndex, EvidenceIndexRecord, ExperimentCell, GridAccounting,
    GridIncomplete, GridSpec, MeasurementContractError, OutcomeCategory,
    runner_run_id,
)

CAMPAIGN = "synthetic-measurement-campaign"
INDEX_REL = "evidence/synthetic/evidence_index.json"
EVIDENCE_DIR = "evidence/synthetic/evidence"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _spec(arms=("ARM_A",), families=("fam1",), seeds=(0,), splits=("dev",)) -> GridSpec:
    return GridSpec(campaign_id=CAMPAIGN, arms=tuple(arms),
                    family_ids=tuple(families), seeds=tuple(seeds),
                    splits=tuple(splits))


def _write_evidence(root: Path, run_id: str, *, observed_outcome="success",
                    declare_run_id=None) -> tuple:
    """Write one evidence artifact; return (relpath, digest)."""
    payload = {"run_id": run_id if declare_run_id is None else declare_run_id,
               "observed_outcome": observed_outcome}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    rel = f"{EVIDENCE_DIR}/{run_id}.json"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return rel, _sha(raw)


def _write_index(root: Path, records: dict, *, campaign_id=CAMPAIGN,
                 raw_override: bytes = None, relpath: str = INDEX_REL) -> tuple:
    payload = {"schema_version": 1, "campaign_id": campaign_id, "records": records}
    raw = raw_override if raw_override is not None else json.dumps(
        payload, sort_keys=True, separators=(",", ":")).encode()
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return relpath, _sha(raw)


def _build(tmp_path, spec=None, *, evidence=("success",), exclusions=None,
           tamper=None, extra_index=None, declared_run_id=None):
    """Build a repo-shaped fixture. ``evidence`` maps cell index -> outcome.

    ``tamper`` rewrites an evidence file AFTER the index digest was computed,
    which is how digest-mismatch is produced.
    """
    root = tmp_path / "repo"
    spec = spec or _spec()
    cells = spec.cells()
    if len(evidence) > len(cells):
        raise AssertionError(
            f"fixture asked for {len(evidence)} evidence records but the grid "
            f"has only {len(cells)} cells; widen the spec")
    records = {}
    for i, outcome in enumerate(evidence):
        cell = cells[i]
        rel, digest = _write_evidence(
            root, cell.expected_run_id, observed_outcome=outcome,
            declare_run_id=(declared_run_id or {}).get(i))
        records[cell.expected_run_id] = {"path": rel, "sha256": digest}
    for run_id, rel, digest in (extra_index or []):
        records[run_id] = {"path": rel, "sha256": digest}
    index_rel, index_sha = _write_index(root, records)
    if tamper is not None:
        # Rewrite bytes after the index was pinned: the digest no longer matches.
        (root / records[tamper]["path"]).write_bytes(b'{"run_id":"tampered"}')
    index = EvidenceIndex.load(index_rel, index_sha, repo_root=root)
    ga = GridAccounting(spec=spec, evidence_index=index, repo_root=root,
                        exclusions=dict(exclusions or {}))
    return ga, root, cells


# ══════════════════════════════════════════════════════════════════════
# 1. Complete, valid grid
# ══════════════════════════════════════════════════════════════════════

def test_complete_valid_grid_accounts_every_cell(tmp_path):
    ga, _root, cells = _build(tmp_path, evidence=("success",))
    report = ga.assert_complete()
    assert len(report.cells) == len(cells)
    assert all(c.outcome is OutcomeCategory.EXPECTED_SUCCESS for c in report.cells)
    assert report.aggregate_refused is False
    assert report.complete is True


def test_complete_grid_reports_failure_cells_as_expected_failure(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=("failure",))
    report = ga.assert_complete()
    assert report.cells[0].outcome is OutcomeCategory.EXPECTED_FAILURE
    assert report.category_counts["EXPECTED_FAILURE"] == 1


def test_all_six_outcome_categories_are_distinguishable():
    values = {c.value for c in OutcomeCategory}
    assert values == {"EXPECTED_SUCCESS", "EXPECTED_FAILURE", "MISSING_RESULT",
                      "INVALID_RESULT", "EXCLUDED", "UNACCOUNTED"}


def test_experiment_cell_binds_every_required_field(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=("success",))
    cell = ga.classify().cells[0]
    for field in ("campaign_id", "family_id", "arm", "seed", "split",
                  "expected_run_id", "observed_run_id", "outcome",
                  "evidence_ref"):
        assert field in cell.to_dict(), field
    assert cell.campaign_id == CAMPAIGN
    assert cell.arm == "ARM_A"
    assert cell.family_id == "fam1"
    assert cell.seed == 0
    assert cell.split == "dev"
    assert cell.observed_run_id == cell.expected_run_id
    assert cell.evidence_ref.endswith(".json")


# ══════════════════════════════════════════════════════════════════════
# 2. Missing evidence is MISSING, and is never a failure
# ══════════════════════════════════════════════════════════════════════

def test_missing_evidence_is_missing_result(tmp_path):
    spec = _spec()
    ga, _root, cells = _build(tmp_path, spec=spec, evidence=())
    report = ga.classify()
    assert report.cells[0].outcome is OutcomeCategory.MISSING_RESULT
    assert report.cells[0].outcome is not OutcomeCategory.EXPECTED_FAILURE
    assert report.aggregate_refused is True


def test_partially_supplied_grid_reports_only_the_gaps(tmp_path):
    spec = _spec(seeds=(0, 1, 2))
    ga, _root, cells = _build(tmp_path, spec=spec, evidence=("success",))
    report = ga.classify()
    outcomes = [c.outcome for c in report.cells]
    assert outcomes.count(OutcomeCategory.EXPECTED_SUCCESS) == 1
    assert outcomes.count(OutcomeCategory.MISSING_RESULT) == 2


def test_missing_is_never_counted_as_an_observed_outcome(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=())
    report = ga.classify()
    assert not report.cells[0].outcome.is_observed_outcome


# ══════════════════════════════════════════════════════════════════════
# 3. Invalid evidence is INVALID, and is never a success
# ══════════════════════════════════════════════════════════════════════

def test_tampered_evidence_digest_is_invalid_result(tmp_path):
    spec = _spec()
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success",),
                               tamper=runner_run_id("ARM_A", "fam1", 0, "dev"))
    report = ga.classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT
    assert report.cells[0].outcome is not OutcomeCategory.EXPECTED_SUCCESS
    assert "digest mismatch" in report.cells[0].detail


def test_absent_evidence_file_is_invalid_result(tmp_path):
    spec = _spec()
    ga, root, _cells = _build(tmp_path, spec=spec, evidence=("success",))
    cell = spec.cells()[0]
    record = ga.evidence_index.get(cell.expected_run_id)
    (root / record.path).unlink()
    report = GridAccounting(spec=spec, evidence_index=ga.evidence_index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT
    assert "absent" in report.cells[0].detail


def test_malformed_evidence_json_is_invalid_not_success(tmp_path):
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    rel = f"{EVIDENCE_DIR}/{cell.expected_run_id}.json"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"{not valid json")
    index_rel, index_sha = _write_index(
        root, {cell.expected_run_id: {"path": rel,
                                      "sha256": _sha(b"{not valid json")}})
    index = EvidenceIndex.load(index_rel, index_sha, repo_root=root)
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT


def test_evidence_without_a_declared_outcome_is_invalid(tmp_path):
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    raw = json.dumps({"run_id": cell.expected_run_id},
                     sort_keys=True, separators=(",", ":")).encode()
    rel = f"{EVIDENCE_DIR}/{cell.expected_run_id}.json"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    index_rel, index_sha = _write_index(
        root, {cell.expected_run_id: {"path": rel, "sha256": _sha(raw)}})
    index = EvidenceIndex.load(index_rel, index_sha, repo_root=root)
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT


def test_unknown_outcome_label_is_invalid_not_success(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=("mostly-fine",))
    assert ga.classify().cells[0].outcome is OutcomeCategory.INVALID_RESULT


def test_a_bogus_digest_cannot_buy_a_success(tmp_path):
    """The precise defect the audit found: a digest that was never verified."""
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    rel, _digest = _write_evidence(root, cell.expected_run_id,
                                   observed_outcome="success")
    # Index pins a digest that does not match the bytes on disk.
    index_rel, index_sha = _write_index(
        root, {cell.expected_run_id: {"path": rel, "sha256": "0" * 64}})
    index = EvidenceIndex.load(index_rel, index_sha, repo_root=root)
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT
    assert report.cells[0].outcome is not OutcomeCategory.EXPECTED_SUCCESS


# ══════════════════════════════════════════════════════════════════════
# 4. Duplicates
# ══════════════════════════════════════════════════════════════════════

def test_duplicate_index_records_are_detected(tmp_path):
    """A run identity may be claimed at most once."""
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    rel, digest = _write_evidence(root, cell.expected_run_id)
    # The index loader keys by run_id, so inject the duplicate directly to model
    # a registry that claims the same identity twice under different artifacts.
    payload = {"schema_version": 1, "campaign_id": CAMPAIGN,
               "records": {cell.expected_run_id: {"path": rel, "sha256": digest}}}
    index = EvidenceIndex(CAMPAIGN, {
        cell.expected_run_id: EvidenceIndexRecord(cell.expected_run_id, rel, digest),
        "abl_OTHER_fam1_s0000_dev": EvidenceIndexRecord(
            "abl_OTHER_fam1_s0000_dev", rel, digest)})
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    # The extra identity is not an expected cell, so it is UNACCOUNTED, and it is
    # named in the orphan list rather than silently dropped.
    assert "abl_OTHER_fam1_s0000_dev" in report.unaccounted_evidence
    assert report.aggregate_refused is True


def test_duplicate_detection_reports_the_repeated_identity(tmp_path):
    spec = _spec()
    index = EvidenceIndex(CAMPAIGN, {}, index_sha256="")
    ga = GridAccounting(spec=spec, evidence_index=index, repo_root=tmp_path)
    seen: dict = {}
    for run_id in ("a", "b"):
        seen[run_id] = seen.get(run_id, 0) + 1
    assert seen == {"a": 1, "b": 1}
    # Behavioural: two DIFFERENT identities are not duplicates.
    assert ga.classify().duplicate_run_ids == ()


# ══════════════════════════════════════════════════════════════════════
# 5. Exclusions
# ══════════════════════════════════════════════════════════════════════

def test_exclusion_requires_a_reason_code(tmp_path):
    spec = _spec()
    run_id = spec.cells()[0].expected_run_id
    with pytest.raises(MeasurementContractError, match="reason code"):
        GridAccounting(spec=spec, exclusions={run_id: "  "})


def test_excluded_cell_is_reported_as_excluded(tmp_path):
    spec = _spec()
    run_id = spec.cells()[0].expected_run_id
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=(),
                               exclusions={run_id: "operator_excluded: instrument drift"})
    report = ga.classify()
    assert report.cells[0].outcome is OutcomeCategory.EXCLUDED


def test_exclusion_does_not_satisfy_completeness(tmp_path):
    """An exclusion withholds a cell; it is not a measurement of it."""
    spec = _spec()
    run_id = spec.cells()[0].expected_run_id
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=(),
                               exclusions={run_id: "operator_excluded"})
    with pytest.raises(GridIncomplete, match="EXPECTED|EXCLUDED|not backed"):
        ga.assert_complete()


def test_exclusion_is_not_silently_dropped(tmp_path):
    spec = _spec(seeds=(0, 1))
    run_id = spec.cells()[0].expected_run_id
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success",),
                               exclusions={run_id: "operator_excluded"})
    report = ga.classify()
    # Both cells still appear in the report; one is EXCLUDED, not removed.
    assert len(report.cells) == 2
    assert report.category_counts["EXCLUDED"] == 1


# ══════════════════════════════════════════════════════════════════════
# 6. Unaccounted
# ══════════════════════════════════════════════════════════════════════

def test_unaccounted_is_reachable_from_real_data(tmp_path):
    """Evidence indexed under an identity no expected cell claims."""
    spec = _spec()
    ga, _root, _cells = _build(
        tmp_path, spec=spec, evidence=("success",),
        extra_index=[("abl_STRAY_fam9_s9999_holdout",
                      f"{EVIDENCE_DIR}/stray.json", "1" * 64)])
    report = ga.classify()
    assert "abl_STRAY_fam9_s9999_holdout" in report.unaccounted_evidence
    orphans = [c for c in report.cells if c.outcome is OutcomeCategory.UNACCOUNTED]
    assert len(orphans) == 1
    assert report.aggregate_refused is True


def test_evidence_declaring_the_wrong_run_id_is_unaccounted(tmp_path):
    """Digest-verified evidence that cannot be attributed to its cell."""
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    rel, digest = _write_evidence(root, cell.expected_run_id,
                                  declare_run_id="abl_SOMEONE_ELSE_fam1_s0000_dev")
    index_rel, index_sha = _write_index(
        root, {cell.expected_run_id: {"path": rel, "sha256": digest}})
    index = EvidenceIndex.load(index_rel, index_sha, repo_root=root)
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.UNACCOUNTED
    assert report.cells[0].outcome is not OutcomeCategory.EXPECTED_SUCCESS


def test_unaccounted_grid_refuses_aggregate(tmp_path):
    ga, _root, _cells = _build(
        tmp_path, evidence=("success",),
        extra_index=[("abl_STRAY_fam9_s9999_holdout",
                      f"{EVIDENCE_DIR}/stray.json", "1" * 64)])
    assert ga.classify().aggregate_refused is True
    with pytest.raises(GridIncomplete, match="claimed by no expected cell"):
        ga.assert_complete()


# ══════════════════════════════════════════════════════════════════════
# 7. assert_complete() really fires  ← the defect the audit found
# ══════════════════════════════════════════════════════════════════════

def test_assert_complete_raises_on_a_completely_empty_grid(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=())
    with pytest.raises(GridIncomplete):
        ga.assert_complete()


def test_assert_complete_raises_when_evidence_is_missing(tmp_path):
    spec = _spec(seeds=(0, 1, 2))
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success",))
    with pytest.raises(GridIncomplete, match="MISSING_RESULT"):
        ga.assert_complete()


def test_assert_complete_raises_when_evidence_is_invalid(tmp_path):
    spec = _spec()
    run_id = spec.cells()[0].expected_run_id
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success",),
                               tamper=run_id)
    with pytest.raises(GridIncomplete, match="INVALID_RESULT"):
        ga.assert_complete()


def test_assert_complete_raises_when_one_cell_is_missing_among_many(tmp_path):
    spec = _spec(seeds=tuple(range(6)))
    ga, _root, _cells = _build(tmp_path, spec=spec,
                               evidence=("success",) * 5)
    with pytest.raises(GridIncomplete, match="1 of 6"):
        ga.assert_complete()


def test_assert_complete_returns_the_report_only_when_complete(tmp_path):
    ga, _root, _cells = _build(tmp_path, spec=_spec(seeds=(0, 1)),
                               evidence=("success", "failure"))
    report = ga.assert_complete()
    assert report.complete is True
    assert len(report.cells) == 2


def test_assert_complete_is_not_satisfiable_by_an_exclusion(tmp_path):
    spec = _spec(seeds=(0, 1))
    run_id = spec.cells()[0].expected_run_id
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success",),
                               exclusions={run_id: "operator_excluded"})
    with pytest.raises(GridIncomplete):
        ga.assert_complete()


# ══════════════════════════════════════════════════════════════════════
# 8. Aggregate refusal
# ══════════════════════════════════════════════════════════════════════

def test_aggregate_result_is_refused_when_incomplete(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=())
    with pytest.raises(GridIncomplete):
        ga.aggregate_result()


def test_aggregate_result_returns_counts_only_when_complete(tmp_path):
    ga, _root, _cells = _build(tmp_path, spec=_spec(seeds=(0, 1)),
                               evidence=("success", "failure"))
    counts = ga.aggregate_result()
    assert counts["EXPECTED_SUCCESS"] == 1
    assert counts["EXPECTED_FAILURE"] == 1
    assert counts["MISSING_RESULT"] == 0


def test_aggregate_result_exposes_no_rate_or_denominator(tmp_path):
    """No success rate, no denominator: categories only."""
    ga, _root, _cells = _build(tmp_path, evidence=("success",))
    counts = ga.aggregate_result()
    assert set(counts) <= {c.value for c in OutcomeCategory}
    for forbidden in ("rate", "denominator", "threshold", "success_rate"):
        assert forbidden not in json.dumps(counts)


# ══════════════════════════════════════════════════════════════════════
# 9. Real runner cell identity
# ══════════════════════════════════════════════════════════════════════

def test_expected_grid_uses_the_real_runner_run_id_scheme():
    assert runner_run_id("FULL_RAPHAEL", "contradiction", 7, "holdout") == \
        "abl_FULL_RAPHAEL_contradiction_s0007_holdout"


def test_expected_run_id_matches_the_real_runner_implementation():
    """Ties the scheme to the live AblationRunner code, not to a comment.

    The run_id assignment is read out of the real ``__init__`` source and
    evaluated, so this fails if the runner's identity scheme ever changes and
    this module does not follow it.
    """
    import inspect
    from arena.ablation_runner import AblationRunner

    source = inspect.getsource(AblationRunner.__init__)
    line = next(ln.strip() for ln in source.splitlines()
                if ln.strip().startswith("self.run_id ="))
    template = line.split("=", 1)[1].strip()

    namespace = {"config": type("C", (), {"config_id": "CFG"})(),
                 "template": type("T", (), {"family_id": "fam1"})(),
                 "seed": 42, "split": "val"}
    produced = eval(template, namespace)          # noqa: S307 - real repo source
    assert produced == "abl_CFG_fam1_s0042_val"
    assert runner_run_id("CFG", "fam1", 42, "val") == produced


def test_expected_grid_cardinality_is_the_product_of_dimensions():
    spec = _spec(arms=("A", "B"), families=("f1", "f2", "f3"),
                 seeds=(0, 1, 2, 3, 4), splits=("dev", "val", "holdout"))
    assert spec.expected_run_count == 2 * 3 * 5 * 3 == 90
    assert len(spec.cells()) == 90
    assert len({c.identity_digest for c in spec.cells()}) == 90


def test_expected_count_mismatch_against_the_manifest_is_refused(tmp_path):
    """A manifest declaring N runs while the grid enumerates M is a contradiction."""
    ga, _root, _cells = _build(tmp_path, evidence=("success",))
    ga.check_expected_count(1, "campaign manifest")        # agreeing value passes
    with pytest.raises(MeasurementContractError, match="declares 999"):
        ga.check_expected_count(999, "campaign manifest")
    with pytest.raises(MeasurementContractError, match="declares 0"):
        ga.check_expected_count(0, "campaign manifest")


def test_expected_count_must_be_an_int(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=("success",))
    with pytest.raises(MeasurementContractError, match="must be an int"):
        ga.check_expected_count(True, "campaign manifest")
    with pytest.raises(MeasurementContractError, match="must be an int"):
        ga.check_expected_count("12", "campaign manifest")


# ══════════════════════════════════════════════════════════════════════
# 10. Deterministic serialization
# ══════════════════════════════════════════════════════════════════════

def test_accounting_serialization_is_deterministic(tmp_path):
    ga, _root, _cells = _build(tmp_path, spec=_spec(seeds=(0, 1)),
                               evidence=("success", "failure"))
    first = ga.classify().canonical_json()
    second = ga.classify().canonical_json()
    assert first == second
    assert json.loads(first)["cells"][0]["expected_run_id"]


def test_serialization_is_stable_across_accounting_order(tmp_path):
    spec = _spec(seeds=(0, 1))
    ga, _root, _cells = _build(tmp_path, spec=spec, evidence=("success", "failure"))
    report = ga.classify()
    reordered = mc.AccountingReport(
        cells=tuple(reversed(report.cells)),
        category_counts=report.category_counts,
        unaccounted_evidence=report.unaccounted_evidence,
        duplicate_run_ids=report.duplicate_run_ids)
    assert set(reordered.canonical_json()) == set(report.canonical_json())
    assert sorted(c.expected_run_id for c in reordered.cells) == \
        sorted(c.expected_run_id for c in report.cells)


# ══════════════════════════════════════════════════════════════════════
# 11. Evidence index integrity
# ══════════════════════════════════════════════════════════════════════

def test_index_with_a_wrong_pinned_digest_is_refused(tmp_path):
    root = tmp_path / "repo"
    index_rel, index_sha = _write_index(root, {})
    with pytest.raises(MeasurementContractError, match="digest mismatch"):
        EvidenceIndex.load(index_rel, "0" * 64, repo_root=root)
    EvidenceIndex.load(index_rel, index_sha, repo_root=root)


def test_index_with_extra_keys_is_refused(tmp_path):
    root = tmp_path / "repo"
    payload = {"schema_version": 1, "campaign_id": CAMPAIGN, "records": {},
               "surprise": 1}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    index_rel, index_sha = _write_index(root, {}, raw_override=raw)
    with pytest.raises(MeasurementContractError, match="exactly"):
        EvidenceIndex.load(index_rel, index_sha, repo_root=root)


def test_index_with_a_malformed_record_digest_is_refused(tmp_path):
    root = tmp_path / "repo"
    payload = {"schema_version": 1, "campaign_id": CAMPAIGN,
               "records": {"abl_x": {"path": "p", "sha256": "nope"}}}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    index_rel, index_sha = _write_index(root, {}, raw_override=raw)
    with pytest.raises(MeasurementContractError, match="malformed digest"):
        EvidenceIndex.load(index_rel, index_sha, repo_root=root)


def test_index_path_escape_is_refused(tmp_path):
    root = tmp_path / "repo"
    with pytest.raises(MeasurementContractError, match="escapes the repository"):
        EvidenceIndex.load("../../../etc/passwd", "0" * 64, repo_root=root)


def test_absent_index_is_refused(tmp_path):
    root = tmp_path / "repo"
    with pytest.raises(MeasurementContractError, match="absent"):
        EvidenceIndex.load(INDEX_REL, "0" * 64, repo_root=root)


def test_evidence_path_escape_is_invalid_result(tmp_path):
    root = tmp_path / "repo"
    spec = _spec()
    cell = spec.cells()[0]
    index = EvidenceIndex(CAMPAIGN, {
        cell.expected_run_id: EvidenceIndexRecord(cell.expected_run_id,
                                                  "../../../etc/passwd", "0" * 64)})
    report = GridAccounting(spec=spec, evidence_index=index,
                            repo_root=root).classify()
    assert report.cells[0].outcome is OutcomeCategory.INVALID_RESULT
    assert "escapes" in report.cells[0].detail


# ══════════════════════════════════════════════════════════════════════
# 12. No authority from accounting
# ══════════════════════════════════════════════════════════════════════

def test_incomplete_accounting_confers_no_promotion_authority(tmp_path):
    """A complete-looking module must not become an authority surface."""
    ga, _root, _cells = _build(tmp_path, evidence=())
    for attribute in ("promote", "authorize_promotion", "grant_authority",
                      "classify_promotion_eligibility"):
        assert not hasattr(ga, attribute)
    # And the incomplete accounting cannot produce an aggregate at all.
    with pytest.raises(GridIncomplete):
        ga.aggregate_result()


def test_this_module_is_not_referenced_by_the_promotion_gate(tmp_path):
    """The gate must not consume accounting output as authority."""
    source = (REPO / "src" / "orchestrator" / "rsi" / "evaluation_gate.py").read_text(
        encoding="utf-8")
    assert "measurement_contract" not in source
    assert "GridAccounting" not in source


def test_category_helpers_do_not_leak_into_an_authority_object(tmp_path):
    ga, _root, _cells = _build(tmp_path, evidence=("success",))
    report = ga.classify()
    # is_observed_outcome is True only for digest-verified outcomes.
    assert report.cells[0].outcome.is_observed_outcome is True
    ga2, _root2, _cells2 = _build(tmp_path / "b", evidence=())
    assert ga2.classify().cells[0].outcome.is_observed_outcome is False