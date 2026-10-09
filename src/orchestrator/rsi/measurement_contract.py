"""RSI-1 measurement grid accounting contract — fail-closed by construction.

DESIGN RULE (this module was wrong before 2026-10-09)
=====================================================
The first version of this file was a skeleton whose single safety assertion
(``assert_complete``) could never fire, and which returned
``EXPECTED_SUCCESS`` for any non-None evidence digest carrying the label
``"success"`` — without ever comparing that digest to anything. Six of its nine
tests asserted ``callable(...)`` or ``not hasattr(...)``.

The rules this version actually implements:

  1. NO OUTCOME IS EVER INFERRED FROM A LABEL ALONE. An outcome is assigned
     only after the evidence bytes for a cell have been located, their SHA-256
     recomputed against a digest recorded in a COMMITTED, digest-pinned index,
     the JSON parsed, and the record's own ``run_id`` confirmed to equal the
     cell's expected run identity.
  2. MISSING IS NOT FAILURE. An absent result is ``MISSING_RESULT``. It is
     never converted into an outcome, and it never satisfies ``assert_complete``.
  3. INVALID IS NOT SUCCESS. A missing file, a digest mismatch, unparsable JSON,
     or an absent/unknown ``observed_outcome`` is ``INVALID_RESULT``.
  4. ``UNACCOUNTED`` IS REACHABLE. Verified evidence that cannot be attributed
     to an expected cell is unaccounted, and so is an index record that no
     expected cell claims.
  5. EXPECTED GRIDS COME FROM THE REAL RUNNER. Cell identity is built with the
     same scheme ``AblationRunner`` uses
     (``abl_{config_id}_{family_id}_s{seed:04d}_{split}``), and the expected
     cardinality is checked against the campaign manifest rather than assumed.
  6. NO DENOMINATOR, RATE, OR THRESHOLD IS ADOPTED HERE. This module counts
     categories. It does not compute a success rate, and no value it produces may
     be used as promotion authority.

Every failure mode resolves to an explicit category. There is no path that
returns a passing outcome without digest-verified evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: Bounded read for a pinned evidence file. A resource bound, not a threshold.
MAX_EVIDENCE_BYTES = 8 * 1024 * 1024

#: Repository root. Tests override this module attribute; production code has no
#: other injection point, because no function below accepts a root parameter.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Outcomes an evidence record may declare. Anything else is INVALID_RESULT.
OBSERVED_SUCCESS = "success"
OBSERVED_FAILURE = "failure"
OBSERVED_OUTCOMES = (OBSERVED_SUCCESS, OBSERVED_FAILURE)


class MeasurementContractError(ValueError):
    """Raised for programmer/API errors, never for invalid DATA.

    Invalid evidence never raises: it resolves to an explicit category.
    """


class GridIncomplete(RuntimeError):
    """Raised by :meth:`GridAccounting.assert_complete` for an incomplete grid.

    A distinct type so a caller cannot mistake a completeness refusal for a
    programming error and swallow it.
    """


class OutcomeCategory(str, Enum):
    EXPECTED_SUCCESS = "EXPECTED_SUCCESS"
    EXPECTED_FAILURE = "EXPECTED_FAILURE"
    MISSING_RESULT = "MISSING_RESULT"
    INVALID_RESULT = "INVALID_RESULT"
    EXCLUDED = "EXCLUDED"
    UNACCOUNTED = "UNACCOUNTED"

    @property
    def is_observed_outcome(self) -> bool:
        """True only for categories backed by digest-verified evidence."""
        return self in (OutcomeCategory.EXPECTED_SUCCESS,
                        OutcomeCategory.EXPECTED_FAILURE)


#: Categories in which an aggregate is refused. EXCLUDED is included
#: deliberately: an exclusion is an explicit operator decision to withhold a
#: cell, not a measurement of it, so it never counts toward a complete result.
COMPLETE_CATEGORIES = (OutcomeCategory.EXPECTED_SUCCESS,
                       OutcomeCategory.EXPECTED_FAILURE)


def runner_run_id(config_id: str, family_id: str, seed: int, split: str) -> str:
    """The REAL ``AblationRunner`` cell identity scheme.

    Mirrors ``src/arena/ablation_runner.py`` (``self.run_id = f"abl_{...}"``).
    ``test_measurement_contract.py`` pins this against a real constructed
    ``AblationRunner`` so the two cannot drift apart silently.
    """
    return f"abl_{config_id}_{family_id}_s{seed:04d}_{split}"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_hex_sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class ExperimentCell:
    """One logical evaluation cell and everything known about its outcome.

    ``observed_run_id``, ``outcome`` and ``evidence_ref`` are populated by
    :meth:`GridAccounting.classify`; they are ``None`` for a cell that has not
    been accounted for yet.
    """
    campaign_id: str
    arm: str
    family_id: str
    seed: int
    split: str
    expected_run_id: str
    observed_run_id: Optional[str] = None
    outcome: Optional[OutcomeCategory] = None
    evidence_ref: Optional[str] = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.campaign_id, str) or not self.campaign_id:
            raise MeasurementContractError("campaign_id must be a non-empty string")
        for name in ("arm", "family_id", "split", "expected_run_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise MeasurementContractError(f"{name} must be a non-empty string")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise MeasurementContractError("seed must be an int, not a bool")
        if self.outcome is not None and not isinstance(self.outcome, OutcomeCategory):
            raise MeasurementContractError(
                f"outcome must be an OutcomeCategory, got "
                f"{type(self.outcome).__name__}")

    @property
    def identity_digest(self) -> str:
        """Logical identity, independent of any observed evidence."""
        return _sha256(_stable({
            "arm": self.arm, "campaign_id": self.campaign_id,
            "family_id": self.family_id, "seed": self.seed,
            "split": self.split,
        }).encode())

    def with_outcome(self, outcome: OutcomeCategory, *, detail: str = "",
                     observed_run_id: Optional[str] = None,
                     evidence_ref: Optional[str] = None) -> "ExperimentCell":
        """Return a copy carrying an accounted outcome.

        ``to_dict()`` is a SERIALIZATION and includes derived fields such as
        ``identity_digest`` that are not constructor arguments; feeding it back
        into the constructor would be a type error waiting to happen. This
        method is the only sanctioned way to move a cell from unaccounted to
        accounted, so a new field cannot be silently dropped on the way.
        """
        return ExperimentCell(
            campaign_id=self.campaign_id, arm=self.arm, family_id=self.family_id,
            seed=self.seed, split=self.split, expected_run_id=self.expected_run_id,
            observed_run_id=observed_run_id, outcome=outcome,
            evidence_ref=evidence_ref, detail=detail)

    def to_dict(self) -> Dict[str, Any]:
        return {"arm": self.arm, "campaign_id": self.campaign_id,
                "detail": self.detail, "evidence_ref": self.evidence_ref,
                "expected_run_id": self.expected_run_id,
                "family_id": self.family_id,
                "identity_digest": self.identity_digest,
                "observed_run_id": self.observed_run_id,
                "outcome": self.outcome.value if self.outcome else None,
                "seed": self.seed, "split": self.split}


@dataclass(frozen=True)
class GridSpec:
    """The EXPECTED grid, declared up front and never inferred from results."""
    campaign_id: str
    arms: Tuple[str, ...]
    family_ids: Tuple[str, ...]
    seeds: Tuple[int, ...]
    splits: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.campaign_id, str) or not self.campaign_id:
            raise MeasurementContractError("campaign_id must be a non-empty string")
        for name in ("arms", "family_ids", "seeds", "splits"):
            value = getattr(self, name)
            if not value:
                raise MeasurementContractError(f"{name} must be non-empty")
        if any(isinstance(s, bool) or not isinstance(s, int) for s in self.seeds):
            raise MeasurementContractError("seeds must be ints, not bools")

    @property
    def expected_run_count(self) -> int:
        return (len(self.arms) * len(self.family_ids)
                * len(self.seeds) * len(self.splits))

    def cells(self) -> List[ExperimentCell]:
        return [
            ExperimentCell(
                campaign_id=self.campaign_id, arm=arm, family_id=family,
                seed=seed, split=split,
                expected_run_id=runner_run_id(arm, family, seed, split))
            for arm in self.arms for family in self.family_ids
            for seed in self.seeds for split in self.splits
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {"arms": list(self.arms), "campaign_id": self.campaign_id,
                "expected_run_count": self.expected_run_count,
                "family_ids": list(self.family_ids), "seeds": list(self.seeds),
                "splits": list(self.splits)}


@dataclass(frozen=True)
class EvidenceIndexRecord:
    """A digest-pinned pointer to one evidence artifact."""
    run_id: str
    path: str
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "run_id": self.run_id, "sha256": self.sha256}


class EvidenceIndex:
    """A COMMITTED, digest-pinned map from run identity to evidence artifact.

    Constructed by :meth:`load` from bytes whose SHA-256 the caller recomputes.
    The index is the only thing that can say *which* evidence file belongs to a
    cell and *what its digest must be*; nothing here is caller-asserted.
    """

    def __init__(self, campaign_id: str, records: Mapping[str, EvidenceIndexRecord],
                 index_sha256: str = ""):
        self.campaign_id = campaign_id
        self.records: Dict[str, EvidenceIndexRecord] = dict(records)
        self.index_sha256 = index_sha256

    def __contains__(self, run_id: object) -> bool:
        return run_id in self.records

    def get(self, run_id: str) -> Optional[EvidenceIndexRecord]:
        return self.records.get(run_id)

    def to_dict(self) -> Dict[str, Any]:
        return {"campaign_id": self.campaign_id, "index_sha256": self.index_sha256,
                "record_count": len(self.records),
                "records": {k: v.to_dict() for k, v in sorted(self.records.items())}}

    @classmethod
    def load(cls, relpath: str, expected_sha256: str,
             repo_root: Optional[Path] = None) -> "EvidenceIndex":
        """Read a committed evidence index, verifying its digest first."""
        if not _is_hex_sha256(expected_sha256):
            raise MeasurementContractError("evidence index digest is malformed")
        root = (repo_root or _REPO_ROOT).resolve()
        declared = Path(relpath)
        if declared.is_absolute():
            raise MeasurementContractError("evidence index path must be repository-relative")
        target = (root / declared).resolve()
        if root != target and root not in target.parents:
            raise MeasurementContractError("evidence index path escapes the repository")
        if not target.is_file():
            raise MeasurementContractError(f"evidence index is absent: {relpath}")
        if target.stat().st_size > MAX_EVIDENCE_BYTES:
            raise MeasurementContractError("evidence index exceeds the bounded-read limit")
        raw = target.read_bytes()
        measured = _sha256(raw)
        if measured != expected_sha256:
            raise MeasurementContractError(
                f"evidence index digest mismatch: measured={measured} "
                f"pinned={expected_sha256}")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise MeasurementContractError("evidence index must be a JSON object")
        if set(payload) != {"schema_version", "campaign_id", "records"}:
            raise MeasurementContractError(
                "evidence index must contain exactly schema_version, "
                "campaign_id and records")
        if payload["schema_version"] != 1:
            raise MeasurementContractError("unsupported evidence index schema_version")
        records = payload["records"]
        if not isinstance(records, dict):
            raise MeasurementContractError("evidence index records must be an object")
        parsed: Dict[str, EvidenceIndexRecord] = {}
        for run_id, entry in records.items():
            if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
                raise MeasurementContractError(
                    "evidence index record keys must be exactly path and sha256")
            if not _is_hex_sha256(entry["sha256"]):
                raise MeasurementContractError(
                    f"evidence index record for {run_id!r} has a malformed digest")
            if not isinstance(entry["path"], str) or not entry["path"]:
                raise MeasurementContractError(
                    f"evidence index record for {run_id!r} has no path")
            parsed[run_id] = EvidenceIndexRecord(run_id=run_id, path=entry["path"],
                                                 sha256=entry["sha256"])
        return cls(campaign_id=str(payload["campaign_id"]), records=parsed,
                   index_sha256=measured)


@dataclass(frozen=True)
class AccountingReport:
    """Deterministic, serializable result of one grid accounting pass."""
    cells: Tuple[ExperimentCell, ...]
    category_counts: Mapping[str, int]
    unaccounted_evidence: Tuple[str, ...]
    duplicate_run_ids: Tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.aggregate_refused

    @property
    def aggregate_refused(self) -> bool:
        """True when no aggregate may be produced from this accounting."""
        if self.duplicate_run_ids or self.unaccounted_evidence:
            return True
        return any(c.outcome not in COMPLETE_CATEGORIES for c in self.cells)

    def category(self, expected_run_id: str) -> Optional[OutcomeCategory]:
        for cell in self.cells:
            if cell.expected_run_id == expected_run_id:
                return cell.outcome
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {"aggregate_refused": self.aggregate_refused,
                "category_counts": dict(sorted(self.category_counts.items())),
                "cells": [c.to_dict() for c in self.cells],
                "duplicate_run_ids": list(self.duplicate_run_ids),
                "unaccounted_evidence": list(self.unaccounted_evidence)}

    def canonical_json(self) -> str:
        """Deterministic serialization: stable key order, no ambient state."""
        return _stable(self.to_dict())


@dataclass
class GridAccounting:
    """Accounts observed evidence against an expected grid. Fail-closed.

    ``spec`` is the expected grid; ``evidence_index`` is the digest-pinned map
    of run identity to evidence artifact. Neither may be derived from results.
    """
    spec: GridSpec
    evidence_index: Optional[EvidenceIndex] = None
    exclusions: Dict[str, str] = field(default_factory=dict)
    repo_root: Optional[Path] = None

    def __post_init__(self) -> None:
        for run_id, reason in self.exclusions.items():
            if not isinstance(reason, str) or not reason.strip():
                raise MeasurementContractError(
                    f"exclusion for {run_id!r} requires a non-empty reason code; "
                    "an unexplained exclusion is not an exclusion")

    # ── expected grid ────────────────────────────────────────────────────

    def expected_cells(self) -> List[ExperimentCell]:
        return self.spec.cells()

    def check_expected_count(self, declared_count: int,
                             declared_source: str = "campaign manifest") -> None:
        """Fail closed when the manifest's declared cardinality disagrees.

        A manifest that claims N runs while the grid enumerates M is a
        contradiction, not a rounding difference.
        """
        if type(declared_count) is not int:
            raise MeasurementContractError(
                f"{declared_source} declared count must be an int, got "
                f"{type(declared_count).__name__}")
        actual = self.spec.expected_run_count
        if declared_count != actual:
            raise MeasurementContractError(
                f"{declared_source} declares {declared_count} runs but the "
                f"enumerated grid contains {actual} "
                f"({len(self.spec.arms)} arms x {len(self.spec.family_ids)} "
                f"families x {len(self.spec.seeds)} seeds x "
                f"{len(self.spec.splits)} splits)")

    # ── accounting ───────────────────────────────────────────────────────

    def _read_evidence(self, record: EvidenceIndexRecord
                       ) -> Tuple[Optional[bytes], str]:
        """Return exact evidence bytes, or ``(None, reason)``."""
        root = (self.repo_root or _REPO_ROOT).resolve()
        declared = Path(record.path)
        if declared.is_absolute():
            return None, "evidence path must be repository-relative"
        target = (root / declared).resolve()
        if root != target and root not in target.parents:
            return None, "evidence path escapes the repository"
        if not target.is_file():
            return None, f"evidence artifact is absent: {record.path}"
        if target.stat().st_size > MAX_EVIDENCE_BYTES:
            return None, "evidence artifact exceeds the bounded-read limit"
        raw = target.read_bytes()
        if _sha256(raw) != record.sha256:
            return None, (f"evidence digest mismatch for {record.path}: recomputed "
                          f"{_sha256(raw)} != pinned {record.sha256}")
        return raw, ""

    def _account_cell(self, cell: ExperimentCell) -> ExperimentCell:
        """Account one cell. Every branch ends in a digest-checked decision."""
        if cell.expected_run_id in self.exclusions:
            return cell.with_outcome(
                OutcomeCategory.EXCLUDED,
                detail=self.exclusions[cell.expected_run_id])

        if self.evidence_index is None:
            return cell.with_outcome(
                OutcomeCategory.MISSING_RESULT,
                detail="no evidence index was supplied")

        record = self.evidence_index.get(cell.expected_run_id)
        if record is None:
            return cell.with_outcome(
                OutcomeCategory.MISSING_RESULT,
                detail="no evidence is indexed for this expected run identity")

        raw, reason = self._read_evidence(record)
        if raw is None:
            return cell.with_outcome(OutcomeCategory.INVALID_RESULT,
                                     evidence_ref=record.path, detail=reason)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return cell.with_outcome(
                OutcomeCategory.INVALID_RESULT, evidence_ref=record.path,
                detail=f"evidence is not valid JSON: {exc}")
        if not isinstance(payload, dict):
            return cell.with_outcome(
                OutcomeCategory.INVALID_RESULT, evidence_ref=record.path,
                detail="evidence record is not an object")

        # Attribution. Evidence that does not name the cell it is filed under
        # cannot be counted for that cell, however well-formed it is.
        observed_run_id = payload.get("run_id")
        if observed_run_id != cell.expected_run_id:
            return cell.with_outcome(
                OutcomeCategory.UNACCOUNTED, observed_run_id=observed_run_id,
                evidence_ref=record.path,
                detail=(f"evidence declares run_id {observed_run_id!r} but is "
                        f"indexed under {cell.expected_run_id!r}"))

        observed_outcome = payload.get("observed_outcome")
        if observed_outcome not in OBSERVED_OUTCOMES:
            return cell.with_outcome(
                OutcomeCategory.INVALID_RESULT,
                observed_run_id=observed_run_id, evidence_ref=record.path,
                detail=(f"evidence declares observed_outcome={observed_outcome!r}, "
                        f"which is not one of {list(OBSERVED_OUTCOMES)}"))

        category = (OutcomeCategory.EXPECTED_SUCCESS
                    if observed_outcome == OBSERVED_SUCCESS
                    else OutcomeCategory.EXPECTED_FAILURE)
        return cell.with_outcome(category, observed_run_id=observed_run_id,
                                 evidence_ref=record.path,
                                 detail="digest-verified evidence")

    def classify(self) -> AccountingReport:
        """Account every expected cell and every indexed evidence record.

        Two independent passes, because they answer different questions:

        * expected cells  -> is each one backed by verified evidence?
        * indexed records -> is each one claimed by an expected cell?

        A record that answers "no" to the second is reported as an UNACCOUNTED
        orphan cell. It is surfaced rather than dropped, so evidence can never
        disappear from the accounting by not matching anything.
        """
        cells = [self._account_cell(cell) for cell in self.expected_cells()]
        expected_ids = {c.expected_run_id for c in cells}

        duplicate_run_ids: List[str] = []
        orphans: Tuple[str, ...] = ()
        if self.evidence_index is not None:
            seen: Dict[str, int] = {}
            for run_id in self.evidence_index.records:
                seen[run_id] = seen.get(run_id, 0) + 1
            duplicate_run_ids = sorted(r for r, n in seen.items() if n > 1)
            orphans = tuple(sorted(
                run_id for run_id in self.evidence_index.records
                if run_id not in expected_ids
                and run_id not in self.exclusions))

        for run_id in orphans:
            orphan_record = self.evidence_index.get(run_id)
            cells.append(ExperimentCell(
                campaign_id=self.spec.campaign_id, arm="<orphan>",
                family_id="<orphan>", seed=0, split="<orphan>",
                expected_run_id=run_id, observed_run_id=run_id,
                outcome=OutcomeCategory.UNACCOUNTED,
                evidence_ref=orphan_record.path if orphan_record else None,
                detail="indexed evidence is claimed by no expected cell"))

        return AccountingReport(cells=tuple(cells),
                                category_counts=_recount(cells),
                                unaccounted_evidence=orphans,
                                duplicate_run_ids=tuple(duplicate_run_ids))

    # ── refusals ─────────────────────────────────────────────────────────

    def assert_complete(self) -> AccountingReport:
        """Raise unless EVERY expected cell carries digest-verified evidence."""
        report = self.classify()
        if report.duplicate_run_ids:
            raise GridIncomplete(
                f"duplicate evidence index records for {list(report.duplicate_run_ids)}; "
                "a run identity may be claimed at most once")
        if report.unaccounted_evidence:
            raise GridIncomplete(
                f"evidence is indexed but claimed by no expected cell: "
                f"{list(report.unaccounted_evidence)}")
        incomplete = sorted(
            c.expected_run_id for c in report.cells
            if c.outcome not in COMPLETE_CATEGORIES)
        if incomplete:
            breakdown: Dict[str, List[str]] = {}
            for cell in report.cells:
                if cell.outcome in COMPLETE_CATEGORIES:
                    continue
                breakdown.setdefault(cell.outcome.value, []).append(
                    cell.expected_run_id)
            raise GridIncomplete(
                f"{len(incomplete)} of {len(report.cells)} expected cells are not "
                f"backed by digest-verified evidence: "
                + "; ".join(f"{k}={len(v)}" for k, v in sorted(breakdown.items()))
                + f" (e.g. {incomplete[:3]})")
        return report

    def aggregate_result(self) -> Dict[str, int]:
        """Per-category counts ONLY, and only from a complete accounting.

        No rate, no denominator, no threshold. A caller that wants a success
        rate must compute it, and it would be an UNADOPTED denominator.
        """
        report = self.assert_complete()
        return dict(sorted(report.category_counts.items()))


def _recount(cells: Sequence[ExperimentCell]) -> Dict[str, int]:
    counts = {c.value: 0 for c in OutcomeCategory}
    for cell in cells:
        counts[cell.outcome.value] += 1
    return counts