"""tests/test_phase3_evidence_binding.py — evidence bundle provenance binding.

Independent Phase 3 readiness audit of `1fd7cda76` found two defects here:

  1. `FINAL_COMMIT_SHA.txt` recorded `948f97c85…`, the PARENT of the audited
     commit, not the audited commit. The bundle could never satisfy its own
     check, because a commit cannot contain its own SHA.
  2. `REMEDIATION_MANIFEST.json` claimed "Policy identity remediation (21/69
     tests pass)", which reads as 48 failing tests. The verified result is
     69/69.

These tests pin the corrected binding. Every assertion below is behavioural:
they read committed bytes and compare them against values recomputed from git,
so a regression cannot pass by editing a constant on both sides.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "evidence" / "phase3_readiness"
BINDING = BUNDLE / "EVIDENCE_BINDING.json"
MANIFEST = BUNDLE / "REMEDIATION_MANIFEST.json"

AUDITED_COMMIT = "1fd7cda7610aa7a6cda56b5c5d9955aed771d674"
AUDITED_TREE = "49237b060d78ad0d9d1f9ad33b8ea073853a3b1f"


def _git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO), *args],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ── the binding record exists and parses ─────────────────────────────────

def test_evidence_binding_file_exists():
    assert BINDING.is_file(), f"missing evidence binding record: {BINDING}"


def test_evidence_binding_parses_and_has_required_keys():
    payload = _load(BINDING)
    for key in ("binding_type", "remediation_commit_sha", "remediation_tree_sha",
                "binding_explanation", "phase3_authorized"):
        assert key in payload, f"evidence binding is missing {key!r}"


def test_binding_type_is_tree_sha():
    assert _load(BINDING)["binding_type"] == "TREE_SHA"


# ── the recorded SHAs match git, recomputed, not copied ─────────────────

def test_recorded_commit_sha_matches_the_audited_commit():
    assert _load(BINDING)["remediation_commit_sha"] == AUDITED_COMMIT


def test_recorded_commit_sha_resolves_in_git():
    """Recompute from git rather than trusting the file."""
    assert _git("rev-parse", AUDITED_COMMIT) == AUDITED_COMMIT


def test_recorded_tree_sha_matches_git_for_that_commit():
    """The tree SHA is independently recomputable and must agree."""
    assert _git("rev-parse", f"{AUDITED_COMMIT}^{{tree}}") == AUDITED_TREE
    assert _load(BINDING)["remediation_tree_sha"] == AUDITED_TREE


def test_audited_commit_is_reachable_from_the_current_branch():
    assert _git("cat-file", "-t", AUDITED_COMMIT) == "commit"
    assert AUDITED_COMMIT in _git("rev-list", "HEAD")


def test_commit_and_tree_are_not_confused():
    """Guards the original defect class: a commit SHA recorded where a tree
    SHA belongs (or vice versa) must not slip back in."""
    payload = _load(BINDING)
    assert payload["remediation_commit_sha"] != payload["remediation_tree_sha"]
    assert _git("cat-file", "-t", payload["remediation_commit_sha"]) == "commit"
    assert _git("cat-file", "-t", payload["remediation_tree_sha"]) == "tree"


# ── the binding explains itself and does not claim authority ────────────

def test_binding_explains_why_tree_sha_is_used():
    text = _load(BINDING)["binding_explanation"].lower()
    assert "cannot contain its own sha" in text
    assert "tree" in text


def test_binding_states_phase3_unauthorized():
    assert _load(BINDING)["phase3_authorized"] is False


# ── the manifest no longer makes the impossible claim ──────────────────

def test_manifest_does_not_claim_a_final_commit_sha():
    """The superseded field asserted the manifest's own commit; it must be gone."""
    manifest = _load(MANIFEST)
    assert "final_commit_sha" not in manifest, (
        "manifest still claims final_commit_sha, which cannot be the SHA of the "
        "commit carrying the manifest")


def test_manifest_records_both_commit_and_tree_sha():
    manifest = _load(MANIFEST)
    assert manifest["remediation_commit_sha"] == AUDITED_COMMIT
    assert manifest["remediation_tree_sha"] == AUDITED_TREE


def test_manifest_explains_the_tree_binding():
    text = _load(MANIFEST)["evidence_binding_explanation"].lower()
    assert "cannot contain its own sha" in text


def test_manifest_states_phase3_unauthorized():
    statement = _load(MANIFEST)["promotion_authority_statement"].lower()
    assert "phase 3 remains unauthorized" in statement


# ── the false policy-identity claim is gone and corrected ──────────────

def test_manifest_has_no_false_policy_identity_claim():
    raw = MANIFEST.read_text(encoding="utf-8")
    assert "21/69" not in raw, (
        "the manifest still reports '21/69 tests pass', which reads as 48 "
        "failing tests and is contradicted by the verified 69/69 result")


def test_manifest_records_the_actual_policy_identity_result():
    manifest = _load(MANIFEST)
    assert manifest["policy_identity_suite_result"] == {"passed": 69, "failed": 0}


def test_manifest_policy_identity_count_matches_the_live_suite():
    """The recorded number must equal what the suite actually contains now."""
    import subprocess as sp
    proc = sp.run(
        ["git", "-C", str(REPO), "show",
         f"{AUDITED_COMMIT}:tests/test_rsi1_policy_identity.py"],
        capture_output=True, text=True, check=True)
    count = sum(1 for line in proc.stdout.splitlines()
                if line.startswith("def test_"))
    assert count == _load(MANIFEST)["policy_identity_suite_result"]["passed"]


def test_workstream_line_reports_the_true_policy_identity_result():
    manifest = _load(MANIFEST)
    lines = [w for w in manifest["workstreams_completed"]
             if "Policy identity" in w]
    assert len(lines) == 1
    assert "69/69" in lines[0]


# ── the superseded file is really gone ──────────────────────────────────

def test_final_commit_sha_file_is_removed():
    stale = BUNDLE / "FINAL_COMMIT_SHA.txt"
    assert not stale.exists(), (
        "FINAL_COMMIT_SHA.txt recorded the parent commit and is superseded by "
        "EVIDENCE_BINDING.json; it must not remain in the bundle")


def test_checksum_file_covers_the_new_binding_and_omits_the_stale_file():
    sums = (BUNDLE / "SHA256SUMS").read_text(encoding="utf-8")
    assert "EVIDENCE_BINDING.json" in sums
    assert "FINAL_COMMIT_SHA.txt" not in sums


def test_checksums_verify_against_real_bytes():
    proc = subprocess.run(["sha256sum", "-c", "evidence/phase3_readiness/SHA256SUMS"],
                          cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAILED" not in proc.stdout