"""tests/test_rsi1_holdout_classification.py — holdout provenance classification.

Behavioural only. Every assertion here either executes repository code or reads
committed bytes and compares them against a recomputed value. The prior version
of this file ended in a bare ``pass`` and asserted a stale string; both are gone.

The independent Phase 3 readiness audit found that this classification asserted
the 3,240-row predecessor was ``QUARANTINED`` at a path that holds no artifact
and has no git object in any branch. These tests pin the corrected
``ABSENT_AND_UNVERIFIABLE`` status and refuse any silent regression of that
claim.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CAMPAIGN = REPO / "evaluations" / "campaign"
CLASSIFICATION_FILE = CAMPAIGN / "HOLDOUT_CLASSIFICATION_20261009.json"
HOLDOUT_CANONICAL = CAMPAIGN / "rbs_v4_holdout.jsonl"
PREDECESSOR = CAMPAIGN / "rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE.jsonl"
ANCHOR_MANIFEST = CAMPAIGN / "rbs_v4_reproducibility_manifest.json"

#: The digest pinned INSIDE evaluation_gate.py for the authoritative manifest.
#: If the manifest is edited to make missing evidence resolvable, this breaks.
PINNED_ANCHOR_MANIFEST_SHA256 = (
    "c26ed773ba57d43d53e150acb90db8299aa565f9ea7b2646a7820aa2c9775757")

sys.path.insert(0, str(REPO / "src"))
from orchestrator.rsi.evaluation_gate import (  # noqa: E402
    HOLDOUT_MISSING, HOLDOUT_VERIFIED, STATE_PROMOTION_ELIGIBLE,
    GateConfig, classify_promotion_eligibility, verify_authoritative_holdout,
)


def _data() -> dict:
    return json.loads(CLASSIFICATION_FILE.read_text(encoding="utf-8"))


# ── the canonical holdout remains missing and fail-closed ───────────────

def test_classification_file_exists():
    assert CLASSIFICATION_FILE.is_file(), f"missing: {CLASSIFICATION_FILE}"


def test_canonical_holdout_is_missing_on_disk():
    assert not HOLDOUT_CANONICAL.exists(), (
        f"canonical holdout unexpectedly present: {HOLDOUT_CANONICAL}")


def test_verify_authoritative_holdout_returns_missing():
    """Execute the real gate, do not reason about the source."""
    status = verify_authoritative_holdout().status
    assert status == HOLDOUT_MISSING
    assert status != HOLDOUT_VERIFIED


def test_classification_says_unverifiable_and_forbids_reconstruction():
    data = _data()
    assert data["classification"] == "UNVERIFIABLE"
    assert data["canonical_status"] == "MISSING"
    assert data["reconstruction_permitted"] is False


def test_no_promotion_authority_while_holdout_missing():
    """A record claiming PROMOTION_ELIGIBLE cannot be classified as such."""
    cfg = GateConfig(config_id="audit", campaign_id="holdout-audit")
    record_fields = dict(
        decision_id="audit-1", campaign_id=cfg.campaign_id,
        evaluator_identity="a" * 64, evaluator_label="audit",
        gate_config_digest=cfg.config_digest, inputs_digest="b" * 64,
        holdout_id="rbs-v4-holdout", holdout_status=HOLDOUT_VERIFIED,
        holdout_sha256="c" * 64, holdout_row_count=1200,
        holdout_evaluation_refs=("ev/holdout.json",),
        replay_evaluation_refs=("ev/replay.json",),
        evidence_refs=("ev/safety.json",),
        metrics=(("verified_rate", 0.99),), gate_outcomes=(),
        selection_history_refs=(), parent_lineage=("parent",),
        rollback_target="policy-v1", baseline_policy_hash="d" * 64,
        candidate_policy_hash="e" * 64, protocol_id="proto-1",
        metrics_frozen_digest="f" * 64, reviewer_authority="reviewer",
        runs_candidate=1000, runs_baseline=1000, exclusions=0, effect=0.5,
        replay_evidence_complete=True, safety_passed=True,
        final_state=STATE_PROMOTION_ELIGIBLE)
    from orchestrator.rsi.evaluation_gate import EvaluationDecisionRecord
    record = EvaluationDecisionRecord.mint(**record_fields)
    assessment = classify_promotion_eligibility(record, cfg)
    assert assessment.state != STATE_PROMOTION_ELIGIBLE


# ── the predecessor claim is withdrawn, not quietly re-asserted ─────────

def test_predecessor_is_classified_absent_and_unverifiable():
    data = _data()
    assert data["predecessor_dataset_status"] == "ABSENT_AND_UNVERIFIABLE"
    assert data["campaign_reconciliation"]["campaign_a_predecessor"]["status"] \
        == "ABSENT_AND_UNVERIFIABLE"


def test_no_digest_or_commit_is_claimed_for_the_predecessor():
    data = _data()
    assert data["predecessor_dataset_digest"] is None
    assert data["predecessor_dataset_commit"] is None
    assert data["predecessor_dataset_verifiable"] is False


def test_predecessor_row_count_claim_is_not_treated_as_verified():
    data = _data()
    assert data["predecessor_row_count_claim"] == "UNVERIFIABLE"
    assert data["historical_claim_status"] == "NOT_VERIFIABLE_FROM_REPOSITORY"


def test_classification_records_the_unverifiability_statement():
    text = _data()["predecessor_unverifiability_statement"]
    assert "does not contain sufficient evidence to verify the existence" in text
    assert "row count" in text
    assert "no historical claim about that dataset may be treated as verified" \
        in text.lower()


def test_predecessor_artifact_really_is_absent_from_the_worktree():
    """The classification and the filesystem must agree."""
    assert not PREDECESSOR.exists(), (
        f"predecessor artifact exists at {PREDECESSOR} but is classified "
        "ABSENT_AND_UNVERIFIABLE; the classification is stale")


def test_predecessor_artifact_has_no_git_object_in_any_branch():
    """Guards against a silent 'the quarantine file was restored' regression."""
    proc = subprocess.run(
        ["git", "-C", str(REPO), "rev-list", "--all", "--objects"],
        capture_output=True, text=True, check=True)
    assert "rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE" not in proc.stdout, (
        "the quarantined predecessor exists in git history; the ABSENT_AND_"
        "UNVERIFIABLE classification is stale and must be re-derived")


def test_quarantine_status_was_explicitly_withdrawn_not_silently_edited():
    data = _data()
    predecessor = data["campaign_reconciliation"]["campaign_a_predecessor"]
    assert predecessor.get("quarantine_status_withdrawn") is True
    assert data.get("revision_note", "")


def test_no_predecessor_artifact_was_fabricated_to_support_the_claim():
    """The correction must not have recreated the file it says is absent."""
    assert not PREDECESSOR.exists()
    raw = CLASSIFICATION_FILE.read_text(encoding="utf-8")
    assert '"status": "QUARANTINED"' not in raw


# ── constraints that must not have been broken to fix this ──────────────

def test_gitignore_still_blocks_campaign_jsonl():
    line = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()[86]
    assert line.strip() == "evaluations/campaign/*.jsonl"


def test_authoritative_anchor_manifest_was_not_modified():
    """Recomputed, not asserted: the manifest must still hash to the pinned value."""
    import hashlib
    measured = hashlib.sha256(ANCHOR_MANIFEST.read_bytes()).hexdigest()
    assert measured == PINNED_ANCHOR_MANIFEST_SHA256, (
        "the authoritative-anchor manifest has been modified; making missing "
        "evidence resolvable by editing the anchor is forbidden")


def test_anchor_manifest_still_verifies_through_the_real_loader():
    from orchestrator.rsi.evaluation_gate import load_authoritative_anchor
    anchor = load_authoritative_anchor()
    assert anchor.loaded, anchor.detail
    assert anchor.declaration is not None
    assert anchor.declaration.sha256 == (
        "2bf614f8eafa02533bfb522fa50ac1f1827acb0951eeeb42eff6b845a8e586b4")


def test_raw_telemetry_is_present_but_marked_non_authoritative():
    data = _data()
    assert data["raw_telemetry_status"] == "PRESENT_BUT_NONAUTHORITATIVE"
    assert data["raw_telemetry_path"] == "evaluations/campaign/holdout_runs/raw/"
    assert (REPO / data["raw_telemetry_path"]).is_dir()