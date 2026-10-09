"""tests/test_historical_split_adjudication_package.py — package integrity.

Behavioural only. The package is an ADJUDICATION AID, not a ruling, so the
tests here are mostly guards against it drifting INTO being a ruling: no entry
may grant authority, none may claim ratification, and every proposed ruling must
survive a rescan of the real source tree.

The decisive test is ``test_census_matches_an_independent_rescan``: if any real
site supplying the legacy validation label is missing from the package, the
package fails.

Note on wording: this file deliberately avoids writing the legacy label in the
canonical assignment form, because doing so would register THIS file as a new
call site in the pre-existing census rescan
(``tests/test_rsi1_historical_call_site_rulings.py``). An adjudication package
must not perturb the census it reports on.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "evidence" / "historical_split_adjudication"
CENSUS = PKG / "call_site_census.json"
METHOD = PKG / "ADJUDICATION_METHOD.md"
REPORT = REPO / "reports" / "HISTORICAL_SPLIT_ADJUDICATION_PACKAGE_20261009.md"
SOURCE_CENSUS = REPO / "evidence" / "historical_validation_call_site_rulings.json"

VALID_RULINGS = {"DEV", "VAL", "HOLDOUT", "UNKNOWN"}
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT"}
REQUIRED_FIELDS = (
    "site_id", "repository_path", "line_or_symbol",
    "commit_or_evidence_reference", "literal_split_label", "evidence_references",
    "proposed_ruling", "confidence", "reviewer",
    "operator_ruling_status", "current_authority_granted",
)

CODE_ROOTS = ["scripts", "src", "tests", "evaluations", "cli", "benchmarks",
              "forge", "Report_Raphael"]
SKIP = {"__pycache__", ".venv", "node_modules", ".git"}
#: No self-exclusion. This file is rescanned like every other source file, so
#: adding the legacy label here would register this file as a real site and
#: fail the drift test. That is the intended behaviour: an adjudication package
#: must not be able to hide a site by excluding itself from the search.
PATTERNS = [
    re.compile(r"split\s*=\s*[\"']validation[\"']"),
    re.compile(r"split\s*:\s*str\s*=\s*[\"']validation[\"']"),
    re.compile(r"[\"']split[\"']\s*:\s*[\"']validation[\"']"),
]


def _pkg() -> dict:
    return json.loads(CENSUS.read_text(encoding="utf-8"))


def _rescan() -> set:
    found = set()
    for root in CODE_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(p in SKIP for p in path.parts):
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


def test_this_file_registers_no_census_site():
    """Guards against a future edit reintroducing the label here."""
    import os
    here = "tests/test_historical_split_adjudication_package.py"
    assert os.path.isfile(REPO / here)
    assert not [s for s in _rescan() if s.startswith(here + ":")], (
        "this test file now contains the legacy label and would appear as a "
        "census site; reword it instead of excluding this file from the rescan")
    assert not any(s["site_id"].startswith(here) for s in _pkg()["sites"])


# ══════════════════════════════════════════════════════════════════════
# 1. Every recorded path exists and is real
# ══════════════════════════════════════════════════════════════════════

def test_every_recorded_path_exists():
    missing = [s["site_id"] for s in _pkg()["sites"]
               if not (REPO / s["repository_path"]).is_file()]
    assert missing == [], f"package cites nonexistent files: {missing}"


def test_every_recorded_line_still_contains_a_match():
    drifted = []
    for s in _pkg()["sites"]:
        line_no = int(str(s["line_or_symbol"]).split()[-1])
        text = (REPO / s["repository_path"]).read_text(
            encoding="utf-8", errors="replace").splitlines()[line_no - 1]
        if not any(p.search(text) for p in PATTERNS):
            drifted.append(s["site_id"])
    assert drifted == [], f"cited line no longer matches the legacy label: {drifted}"


def test_no_duplicate_site_ids():
    ids = [s["site_id"] for s in _pkg()["sites"]]
    assert len(ids) == len(set(ids))


# ══════════════════════════════════════════════════════════════════════
# 2. The independent re-scan  ← catches a missing real site
# ══════════════════════════════════════════════════════════════════════

def test_census_matches_an_independent_rescan():
    """If a real legacy-label site is missing from the package, this fails."""
    recorded = {s["site_id"] for s in _pkg()["sites"]}
    actual = _rescan()
    assert recorded == actual, (
        f"census drift against source. missing={sorted(actual - recorded)} "
        f"stale={sorted(recorded - actual)}")


def test_package_census_agrees_with_the_source_census():
    source = json.loads(SOURCE_CENSUS.read_text(encoding="utf-8"))
    assert {s["site_id"] for s in _pkg()["sites"]} == \
        {s["id"] for s in source["sites"]}
    assert _pkg()["total_sites"] == source["total_sites"]


def test_no_site_records_the_wrong_label():
    for s in _pkg()["sites"]:
        assert s["literal_split_label"] == "validation", s["site_id"]


# ══════════════════════════════════════════════════════════════════════
# 3. Field validity
# ══════════════════════════════════════════════════════════════════════

def test_every_entry_has_every_required_field():
    for s in _pkg()["sites"]:
        for field in REQUIRED_FIELDS:
            assert field in s, f"{s['site_id']} missing {field}"


def test_every_proposed_ruling_is_valid():
    for s in _pkg()["sites"]:
        assert s["proposed_ruling"] in VALID_RULINGS, s["site_id"]


def test_every_confidence_is_valid():
    for s in _pkg()["sites"]:
        assert s["confidence"] in VALID_CONFIDENCE, s["site_id"]


def test_confidence_histogram_matches_the_entries():
    pkg = _pkg()
    computed = {}
    for s in pkg["sites"]:
        computed[s["confidence"]] = computed.get(s["confidence"], 0) + 1
    for level in VALID_CONFIDENCE:
        assert pkg["confidence_histogram"][level] == computed.get(level, 0), level


def test_ruling_histogram_matches_the_entries():
    pkg = _pkg()
    computed = {}
    for s in pkg["sites"]:
        computed[s["proposed_ruling"]] = computed.get(s["proposed_ruling"], 0) + 1
    for ruling in VALID_RULINGS:
        assert pkg["proposed_ruling_histogram"][ruling] == computed.get(ruling, 0)


def test_every_entry_carries_evidence_references():
    for s in _pkg()["sites"]:
        assert s["evidence_references"], s["site_id"]
        for e in s["evidence_references"]:
            assert e["ref"] and e["statement"] and e["establishes"]


def test_every_entry_records_a_commit_reference():
    for s in _pkg()["sites"]:
        ref = s["commit_or_evidence_reference"]
        assert ref and ref != "unknown", s["site_id"]
        assert re.fullmatch(r"[0-9a-f]{40} \d{4}-\d{2}-\d{2}", ref), \
            f"{s['site_id']}: {ref!r}"


# ══════════════════════════════════════════════════════════════════════
# 4. The package must not have become a ruling
# ══════════════════════════════════════════════════════════════════════

def test_no_entry_grants_current_authority():
    for s in _pkg()["sites"]:
        assert s["current_authority_granted"] is False, s["site_id"]
    assert _pkg()["current_authority_granted_anywhere"] is False


def test_all_entries_remain_pending_operator_ratification():
    for s in _pkg()["sites"]:
        assert s["operator_ruling_status"] == "PENDING_OPERATOR_RATIFICATION", \
            s["site_id"]
    assert _pkg()["operator_ruling_status"] == "PENDING_OPERATOR_RATIFICATION"
    assert _pkg()["operator_ratification_complete"] is False


def test_package_does_not_claim_phase3():
    assert _pkg()["phase3_authorized"] is False


def test_reviewer_is_not_an_operator():
    for s in _pkg()["sites"]:
        assert "operator" not in s["reviewer"].lower() or \
            "not an operator" in s["reviewer"].lower(), s["site_id"]


def test_no_site_claims_a_confirmed_ruling_without_ratification():
    """A non-UNKNOWN ruling would require ratification, which has not happened."""
    for s in _pkg()["sites"]:
        if s["proposed_ruling"] != "UNKNOWN":
            assert s["operator_ruling_status"] == "RATIFIED", \
                f"{s['site_id']} proposes {s['proposed_ruling']} unratified"


# ══════════════════════════════════════════════════════════════════════
# 5. Actual behaviour is separated from intent
# ══════════════════════════════════════════════════════════════════════

def test_actual_behaviour_is_established_even_though_intent_is_unknown():
    """The package's whole point: Q1 answered, Q2 not."""
    for s in _pkg()["sites"]:
        assert s["actual_historical_behavior"] in {"DEV", "VAL", "HOLDOUT"}, \
            s["site_id"]
        assert s["evidence_class"] == \
            "ACTUAL_BEHAVIOR_ESTABLISHED_INTENT_UNKNOWN", s["site_id"]


def test_baseline_fallback_is_cited_for_every_site():
    for s in _pkg()["sites"]:
        kinds = {e["kind"] for e in s["evidence_references"]}
        assert "baseline_source" in kinds, s["site_id"]
        assert "fsplit1_parent" in kinds, s["site_id"]


def test_baseline_citation_is_reproducible():
    """The cited baseline line must still say what the package claims."""
    pkg = _pkg()
    ref = next(e["ref"] for e in pkg["sites"][0]["evidence_references"]
               if e["kind"] == "baseline_source")
    blob, _, line_no = ref.partition(":src/arena/ablation_runner.py:")
    source = subprocess.run(["git", "-C", str(REPO), "show", f"{blob}:src/arena/ablation_runner.py"],
                            capture_output=True, text=True, check=True).stdout
    line = source.splitlines()[int(line_no) - 1]
    assert "split_map.get(self.split, ScenarioSplit.DEV)" in line, line


# ══════════════════════════════════════════════════════════════════════
# 6. Non-live sites are not adjudicated as call sites
# ══════════════════════════════════════════════════════════════════════

def test_non_live_sites_are_flagged_and_explained():
    pkg = _pkg()
    non_live = [s for s in pkg["sites"] if not s["is_live_call_site"]]
    assert len(non_live) == pkg["non_live_references"]
    for s in non_live:
        assert s["non_live_reason"], s["site_id"]


def test_live_and_non_live_counts_add_up():
    pkg = _pkg()
    assert pkg["live_call_sites"] + pkg["non_live_references"] == pkg["total_sites"]


# ══════════════════════════════════════════════════════════════════════
# 7. Documents agree with the JSON
# ══════════════════════════════════════════════════════════════════════

def test_report_states_the_verified_count():
    assert f"| Total sites | **{_pkg()['total_sites']}** |" in \
        REPORT.read_text(encoding="utf-8")


def test_report_states_no_ratification_has_occurred():
    text = REPORT.read_text(encoding="utf-8").upper()
    assert "NO OPERATOR RATIFICATION HAS OCCURRED" in text


def test_method_states_the_evidence_hierarchy():
    text = METHOD.read_text(encoding="utf-8")
    assert "Evidence hierarchy" in text
    assert "Current code behavior is not proof of historical intent" in text


def test_method_states_the_unknown_default():
    text = METHOD.read_text(encoding="utf-8").lower()
    assert "missing or contradictory evidence defaults to unknown" in text


def test_method_states_unknown_sites_are_excluded():
    text = METHOD.read_text(encoding="utf-8").lower()
    assert "excluded from current authoritative evaluation" in text


def test_method_records_the_seed_band_finding():
    text = METHOD.read_text(encoding="utf-8")
    assert "2,394" in text and "1,000 higher" in text


# ══════════════════════════════════════════════════════════════════════
# 8. The package changed no historical evidence
# ══════════════════════════════════════════════════════════════════════

def test_no_historical_script_or_test_was_modified_by_the_package():
    changed = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--name-only", "HEAD", "--",
         "scripts", "src/arena", "tests/test_run_identity.py",
         "tests/test_f_split_1_split_vocabulary.py",
         "evaluations/campaign/rbs_v4_reproducibility_manifest.json"],
        capture_output=True, text=True, check=True).stdout.strip()
    assert changed == "", f"package modified protected paths: {changed}"


def test_authoritative_anchor_manifest_is_untouched():
    import hashlib
    measured = hashlib.sha256(
        (REPO / "evaluations" / "campaign"
         / "rbs_v4_reproducibility_manifest.json").read_bytes()).hexdigest()
    assert measured == \
        "c26ed773ba57d43d53e150acb90db8299aa565f9ea7b2646a7820aa2c9775757"


def test_canonical_holdout_classification_is_untouched():
    data = json.loads((REPO / "evaluations" / "campaign"
                       / "HOLDOUT_CLASSIFICATION_20261009.json")
                      .read_text(encoding="utf-8"))
    assert data["classification"] == "UNVERIFIABLE"
    assert data["canonical_status"] == "MISSING"
    assert data["predecessor_dataset_status"] == "ABSENT_AND_UNVERIFIABLE"
    assert data["reconstruction_permitted"] is False


def test_no_adoption_registry_was_created():
    assert not (REPO / "evaluations" / "adoption"
                / "production_adoption_registry.json").exists()


def test_f_split_1_suite_still_refuses_the_legacy_label():
    """The runner still fails closed; the package changes no runtime behavior."""
    from arena.ablation_runner import InvalidScenarioSplit, _resolve_scenario_split
    try:
        _resolve_scenario_split("validation")
    except InvalidScenarioSplit:
        return
    raise AssertionError("the legacy label was accepted")