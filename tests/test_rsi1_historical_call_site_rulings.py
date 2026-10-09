"""tests/test_rsi1_historical_call_site_rulings.py — verified census integrity.

Behavioural only. The independent Phase 3 readiness audit found the prior
version of this file asserted a census that was wrong three ways: it listed 25
sites when the prompt required 23, 10 of its 19 paths pointed at `scripts/` for
files that live in `src/arena/`, and every entry carried
``operator_ruling_pending: true`` with no ruling field at all, while the
accompanying document was titled a "ruling".

These tests re-derive the census independently and fail if the recorded one
drifts. A path that does not exist is a test failure, not a footnote.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
RULINGS = REPO / "evidence" / "historical_validation_call_site_rulings.json"
REPORT = REPO / "reports" / "HISTORICAL_VALIDATION_CALL_SITE_RULING_20261009.md"

CODE_ROOTS = ["scripts", "src", "tests", "evaluations", "cli", "benchmarks",
              "forge", "Report_Raphael"]
SKIP_PARTS = {"__pycache__", ".venv", "node_modules", ".git"}
PATTERNS = [
    re.compile(r"split\s*=\s*[\"']validation[\"']"),
    re.compile(r"split\s*:\s*str\s*=\s*[\"']validation[\"']"),
    re.compile(r"[\"']split[\"']\s*:\s*[\"']validation[\"']"),
]

sys.path.insert(0, str(REPO / "src"))
from orchestrator.rsi.evaluation_gate import (  # noqa: E402
    STATE_PROMOTION_ELIGIBLE, classify_promotion_eligibility,
    resolve_config_adoption, verify_authoritative_holdout,
)


def _data() -> dict:
    return json.loads(RULINGS.read_text(encoding="utf-8"))


def _independent_census() -> set:
    """Re-derive the call-site set from source, ignoring the recorded file."""
    found = set()
    for root in CODE_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(p in SKIP_PARTS for p in path.parts):
                continue
            rel = str(path.relative_to(REPO))
            try:
                lines = path.read_text(encoding="utf-8",
                                       errors="replace").splitlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, start=1):
                if any(p.search(line) for p in PATTERNS):
                    found.add(f"{rel}:{idx}")
    return found


# ══════════════════════════════════════════════════════════════════════
# 1. The census is accurate and complete
# ══════════════════════════════════════════════════════════════════════

def test_recorded_census_matches_an_independent_rescan():
    """The decisive check: nothing recorded that is not there, nothing omitted."""
    recorded = {s["id"] for s in _data()["sites"]}
    actual = _independent_census()
    assert recorded == actual, (
        f"census drift. missing={sorted(actual - recorded)} "
        f"stale={sorted(recorded - actual)}")


def test_total_sites_matches_the_entry_list():
    data = _data()
    assert data["total_sites"] == len(data["sites"])


def test_every_recorded_path_exists():
    """The audit's specific finding: paths pointed at files that do not exist."""
    missing = [s["id"] for s in _data()["sites"] if not (REPO / s["path"]).is_file()]
    assert missing == [], f"recorded sites point at nonexistent files: {missing}"


def test_every_recorded_line_still_contains_the_match():
    """Paths alone are not enough; the cited line must be the real one."""
    drifted = []
    for site in _data()["sites"]:
        lines = (REPO / site["path"]).read_text(encoding="utf-8",
                                                errors="replace").splitlines()
        actual = lines[site["line"] - 1].strip()
        if actual != site["symbol"]:
            drifted.append(f"{site['id']}: recorded={site['symbol']!r} "
                           f"actual={actual!r}")
    assert drifted == [], f"cited lines have drifted: {drifted}"


def test_no_duplicate_site_ids():
    ids = [s["id"] for s in _data()["sites"]]
    assert len(ids) == len(set(ids))


def test_historical_evidence_occurrences_are_reported_separately():
    """Run data records what happened; it is not a call site."""
    section = _data()["historical_evidence_occurrences_excluded_from_census"]
    assert section["occurrence_count"] > 0
    assert section["file_count"] > 0
    # They must NOT be double-counted as sites.
    assert all(not s["path"].startswith("arena/") for s in _data()["sites"])


# ══════════════════════════════════════════════════════════════════════
# 2. Rulings are truthful about their status
# ══════════════════════════════════════════════════════════════════════

def test_every_entry_has_a_ruling_status():
    for site in _data()["sites"]:
        assert site["ruling_status"] in (
            "PENDING_OPERATOR_RATIFICATION", "RATIFIED"), site["id"]


def test_no_entry_claims_an_operator_ruling_that_does_not_exist():
    """The prior file implied rulings while every entry was pending."""
    for site in _data()["sites"]:
        assert "operator_ruling" not in site or \
            site.get("operator_ruling_pending") is not True, site["id"]
        assert "ruling" not in site or site["ruling_status"] == "RATIFIED", \
            site["id"]


def test_pending_status_is_declared_explicitly_and_blocks_phase3():
    data = _data()
    assert data["operator_ratification_complete"] is False
    assert data["phase3_blocked_until_ratified"] is True
    assert data["current_authority_granted_by_default"] is False


def test_default_ruling_is_historical_only():
    assert _data()["default_ruling"] == "HISTORICAL_ONLY"


def test_no_entry_grants_current_authority():
    for site in _data()["sites"]:
        assert site["current_authority_granted"] is False, site["id"]
        assert site["historical_only"] is True, site["id"]


# ══════════════════════════════════════════════════════════════════════
# 3. JSON, Markdown and manifest agree
# ══════════════════════════════════════════════════════════════════════

def test_report_states_the_verified_count():
    text = REPORT.read_text(encoding="utf-8")
    assert f"Verified call sites: {len(_data()['sites'])}" in text


def test_report_does_not_claim_a_ruling_was_issued():
    text = REPORT.read_text(encoding="utf-8").upper()
    assert "PENDING OPERATOR RATIFICATION" in text
    assert "NO OPERATOR RULING HAS BEEN ISSUED" in text


def test_manifest_and_json_agree_on_the_site_count():
    manifest = json.loads(
        (REPO / "evidence" / "phase3_readiness"
         / "REMEDIATION_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["historical_call_sites"]["total_sites"] == \
        _data()["total_sites"]


def test_manifest_does_not_claim_sites_were_ruled():
    manifest = json.loads(
        (REPO / "evidence" / "phase3_readiness"
         / "REMEDIATION_MANIFEST.json").read_text(encoding="utf-8"))
    section = manifest["historical_call_sites"]
    assert section["default_ruling"] == "HISTORICAL_ONLY"
    assert section.get("ruling_status") == "PENDING_OPERATOR_RATIFICATION"


# ══════════════════════════════════════════════════════════════════════
# 4. Historical records confer no current authority
# ══════════════════════════════════════════════════════════════════════

def test_historical_records_do_not_reach_promotion_authority():
    from orchestrator.rsi.evaluation_gate import (
        EvaluationDecisionRecord, HOLDOUT_VERIFIED, GateConfig)
    cfg = GateConfig(config_id="census-audit", campaign_id="census")
    record = EvaluationDecisionRecord.mint(**{
        "decision_id": "h1", "campaign_id": cfg.campaign_id,
        "evaluator_identity": "a" * 64, "evaluator_label": "historical",
        "gate_config_digest": cfg.config_digest, "inputs_digest": "b" * 64,
        "holdout_id": "h", "holdout_status": HOLDOUT_VERIFIED,
        "holdout_sha256": "c" * 64, "holdout_row_count": 10,
        "holdout_evaluation_refs": ("r",), "replay_evaluation_refs": ("r",),
        "evidence_refs": ("r",), "metrics": (("m", 1.0),), "gate_outcomes": (),
        "selection_history_refs": (), "parent_lineage": ("p",),
        "rollback_target": "p", "baseline_policy_hash": "d" * 64,
        "candidate_policy_hash": "e" * 64, "protocol_id": "p",
        "metrics_frozen_digest": "f" * 64, "reviewer_authority": "r",
        "runs_candidate": 100, "runs_baseline": 100, "exclusions": 0,
        "effect": 0.5, "replay_evidence_complete": True, "safety_passed": True,
        "final_state": STATE_PROMOTION_ELIGIBLE})
    assert classify_promotion_eligibility(record, cfg).state != \
        STATE_PROMOTION_ELIGIBLE


def test_the_legacy_label_is_still_refused_by_the_runner():
    """The census exists because F-SPLIT-1 refuses this label at runtime."""
    from arena.ablation_runner import AblationRunner, InvalidScenarioSplit
    with pytest.raises(InvalidScenarioSplit):
        AblationRunner.__init__  # guard: the class must expose __init__
        _raise_on_validation()


def _raise_on_validation():
    from arena.ablation_runner import _resolve_scenario_split, InvalidScenarioSplit
    try:
        _resolve_scenario_split("validation")
    except InvalidScenarioSplit:
        raise
    raise AssertionError("the legacy 'validation' label was accepted")


def test_holdout_remains_unverifiable_so_no_authority_is_reachable():
    assert verify_authoritative_holdout().status == "MISSING"


def test_no_adoption_authority_exists():
    assert resolve_config_adoption(
        __import__("orchestrator.rsi.evaluation_gate", fromlist=["GateConfig"])
        .GateConfig(config_id="x", campaign_id="census")).adopted is False