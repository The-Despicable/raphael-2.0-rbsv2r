"""tests/test_rsi1_governance_registry_io.py — G1 read-only loader + status surface.

Covers the loader's contract (read-only, fail-closed, history-preserving) and
the status surface's output. Two properties receive the most attention because
they are the ones that were previously wrong:

* **loading is not authorising.** A valid historical ledger whose authority
  cannot be independently verified must remain fully inspectable; only an
  *invalid* artifact is an error. Conflating the two would make an unauthorised
  adoption unauditable.
* **failure is not "no authority".** A caller must never be able to read a
  load failure as an empty-but-valid registry.

Malformed-input cases use isolated ``tmp_path`` fixtures. The real repository
ledger is only ever read, and its bytes are asserted unchanged after every test
that touches the surface.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from orchestrator.rsi.governance_registry import (
    STATUS_ADOPTED,
    STATUS_INVALIDATED,
    STATUS_PROPOSED,
    GovernanceRegistryError,
)
from orchestrator.rsi.governance_registry_io import (
    AUTHENTICATION_LIMITATION,
    DELEGATION_RELPATH,
    LEDGER_RELPATH,
    OBSERVATION_DISCLAIMER,
    TRUST_STORE_RELPATH,
    GovernanceLoadError,
    load_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SURFACE = REPO_ROOT / "scripts" / "raphael_governance_status.py"
GD_03 = "GD-2026-10-11-03"
RETRACTED_IDS = ("GD-2026-10-11-01", "GD-2026-10-11-02",
                 "GD-2026-10-11-04", "GD-2026-10-11-05")

#: Bytes of the artifacts that must never change because of G1.
PROTECTED_ARTIFACTS = (
    REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl",
    REPO_ROOT / "evidence" / "governance" / "EXECUTOR_DELEGATION_20261011.json",
    REPO_ROOT / "evidence" / "governance" / "TRUSTED_ISSUERS.json",
    REPO_ROOT / "evidence" / "provenance_correction" / "OPERATOR_ATTESTATION.md",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def protected_digests():
    return {p: _digest(p) for p in PROTECTED_ARTIFACTS}


@pytest.fixture()
def snapshot():
    return load_ledger(REPO_ROOT)


def _load_surface():
    """Import the status script by path (it lives in scripts/, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "raphael_governance_status", SURFACE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── 1. a valid current ledger loads read-only ──────────────────────────

def test_valid_ledger_loads(snapshot):
    assert snapshot.record_count > 0
    assert snapshot.ledger_path == REPO_ROOT / LEDGER_RELPATH
    assert snapshot.delegation_artifact_present is True
    assert snapshot.trust_store_artifact_present is True
    assert [d.delegation_id for d in snapshot.delegations] == [
        "DEL-2026-10-11-01"]


def test_loader_does_not_mutate_any_artifact(protected_digests):
    load_ledger(REPO_ROOT)
    _load_surface().main([])
    for path, before in protected_digests.items():
        assert _digest(path) == before, f"{path} was modified by G1"


# ── 2. historical adoption events remain visible ───────────────────────

def test_all_historical_adoption_events_remain_visible(snapshot):
    events = snapshot.historical_adoption_events
    assert len(events) == 4
    assert sorted(e.decision_id for e in events) == sorted(RETRACTED_IDS)
    for event in events:
        assert event.status == STATUS_ADOPTED
        # a preserved event, never presented as in force
        assert event not in snapshot.effective_authoritative


def test_retracted_decisions_are_still_inspectable(snapshot):
    for decision_id in RETRACTED_IDS:
        versions = snapshot.registry.versions(decision_id)
        assert [v.status for v in versions] == [
            STATUS_PROPOSED, STATUS_ADOPTED, STATUS_INVALIDATED]
        assert snapshot.status_of(decision_id) == STATUS_INVALIDATED


# ── 3. the four invalidated decisions are not authoritative ────────────

def test_invalidated_decisions_are_not_authoritative(snapshot):
    assert snapshot.effective_authority_count == 0
    assert snapshot.effective_authoritative == ()
    for decision_id in RETRACTED_IDS:
        assert decision_id not in {
            r.decision_id for r in snapshot.effective_authoritative}


def test_structural_only_results_are_not_presented_as_effective(snapshot):
    """``is_authoritative()`` is structural; the snapshot must not use it alone.

    The four historical adoptions declare no authority_class, so the structural
    projection already returns False for them. A synthetic record that IS
    structurally authoritative must still be withheld by the contextual query.
    """
    for record in snapshot.historical_adoption_events:
        assert record.is_authoritative() is False

    structural_only = [
        r for r in snapshot.registry.current_records()
        if r.is_structurally_ruled() and not r.is_authoritative()]
    assert structural_only, "fixture should contain ruled but unclassified records"
    for record in structural_only:
        assert record not in snapshot.effective_authoritative


# ── 4. empty trust store => zero effective authority ───────────────────

def test_empty_trust_store_yields_zero_effective_authority(snapshot):
    assert snapshot.trusted_issuers == ()
    assert snapshot.trust_store_is_empty is True
    assert snapshot.effective_authority_count == 0


# ── 5. problems and unverified records are reported ────────────────────

def test_unverified_authority_is_reported_not_discarded(snapshot):
    faults = snapshot.unverified_authority
    assert len(faults) == 4
    for decision_id, status, reason in faults:
        assert decision_id in RETRACTED_IDS
        assert status == STATUS_ADOPTED
        assert "trusted-issuer store" in reason
    assert any("verified" in n for n in snapshot.notes)


def test_authority_problems_are_reported(snapshot):
    # none currently ADOPTED, so no live problems — but the mapping is exposed
    assert isinstance(snapshot.authority_problems, dict)
    for decision_id in snapshot.authority_problems:
        assert snapshot.authority_problems[decision_id]


def test_status_counts_are_derived_not_hardcoded(snapshot):
    counts = snapshot.status_counts()
    assert sum(counts.values()) == len(snapshot.registry.current_records())
    assert counts.get(STATUS_INVALIDATED) == 4
    assert counts.get(STATUS_PROPOSED) == 7
    assert snapshot.status_of(GD_03) == STATUS_PROPOSED


# ── 6-9. fail-closed behaviour on invalid artifacts ────────────────────

def _fixture_repo(tmp_path: Path, *, ledger: str = "",
                  delegation=None, trust_store=None) -> Path:
    root = tmp_path / "repo"
    (root / "evidence" / "governance").mkdir(parents=True)
    (root / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl").write_text(
        ledger, encoding="utf-8")
    if delegation is not None:
        (root / "evidence" / "governance" / DELEGATION_RELPATH.name).write_text(
            delegation, encoding="utf-8")
    if trust_store is not None:
        (root / "evidence" / "governance" / TRUST_STORE_RELPATH.name).write_text(
            trust_store, encoding="utf-8")
    return root


def test_missing_ledger_fails_closed(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(GovernanceLoadError) as exc:
        load_ledger(root)
    assert "missing" in str(exc.value)
    assert exc.value.path is not None


def test_malformed_ledger_fails_closed(tmp_path):
    root = _fixture_repo(tmp_path, ledger="{not json}\n")
    with pytest.raises(GovernanceLoadError, match="not valid JSON"):
        load_ledger(root)


def test_ledger_with_hash_mismatch_fails_closed(tmp_path):
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8").splitlines()
    tampered = json.loads(good[0])
    tampered["decision_text"] = "tampered"
    root = _fixture_repo(
        tmp_path, ledger=json.dumps(tampered) + "\n")
    with pytest.raises(GovernanceLoadError, match="invalid"):
        load_ledger(root)


def test_malformed_delegation_artifact_fails_closed(tmp_path):
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8")
    root = _fixture_repo(tmp_path, ledger=good, delegation="{ broken json")
    with pytest.raises(GovernanceLoadError, match="not valid JSON"):
        load_ledger(root)


def test_missing_delegation_artifact_withholds_authority_without_failing(tmp_path):
    """Absence of a delegation is meaningful state, not corruption."""
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8")
    root = _fixture_repo(tmp_path, ledger=good)
    snapshot = load_ledger(root)
    assert snapshot.delegation_artifact_present is False
    assert snapshot.effective_authority_count == 0
    assert len(snapshot.historical_adoption_events) == 4


def test_malformed_trust_store_fails_closed_and_grants_nothing(tmp_path):
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8")
    root = _fixture_repo(tmp_path, ledger=good, trust_store="{ not json")
    with pytest.raises(GovernanceLoadError, match="not valid JSON"):
        load_ledger(root)


def test_malformed_trust_store_entry_cannot_silently_grant_authority(tmp_path):
    """A structurally broken issuer entry is refused, not skipped."""
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8")
    trust = json.dumps({
        "trusted_issuers": [{
            "issuer_id": "agent:executor-v-2",          # forbidden namespace
            "verification_method": "self-assertion",
            "verified_by": "agent:executor-v-2",
            "verified_at": "2026-10-11T00:00:00Z",
            "evidence_refs": ["nope.json"],
        }]})
    root = _fixture_repo(tmp_path, ledger=good, trust_store=trust)
    with pytest.raises(GovernanceLoadError, match="invalid"):
        load_ledger(root)


def test_trust_store_without_issuer_array_fails_closed(tmp_path):
    good = (REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl") \
        .read_text(encoding="utf-8")
    root = _fixture_repo(tmp_path, ledger=good,
                         trust_store=json.dumps({"nope": []}))
    with pytest.raises(GovernanceLoadError, match="no issuer array"):
        load_ledger(root)


def test_non_directory_repo_root_fails_closed(tmp_path):
    target = tmp_path / "a-file"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(GovernanceLoadError, match="not a directory"):
        load_ledger(target)


# ── 14. valid-but-unverified is distinguishable from unreadable ────────

def test_valid_ledger_with_unverified_authority_stays_inspectable(snapshot):
    """The distinction G1 must preserve.

    ``load_ledger`` returned successfully (no exception), the records are all
    readable, and the unverified ones are *reported*. A caller can tell this
    apart from ``test_missing_ledger_fails_closed``, which raises.
    """
    assert snapshot.record_count == 19
    assert len(snapshot.unverified_authority) == 4
    assert snapshot.effective_authority_count == 0
    # the loader never invented authority to fill the gap
    assert snapshot.trusted_issuers == ()


# ── 10-12, 15. the status surface ──────────────────────────────────────

def test_surface_reports_the_audited_state(snapshot):
    module = _load_surface()
    report = module._build_report(snapshot)

    assert report["loaded"] is True
    assert report["record_count"] == snapshot.record_count
    assert report["effective_authority_count"] == 0
    assert report["effective_authority_ids"] == []
    assert report["unverified_authority_count"] == 4
    assert sorted(report["historical_adoption_event_ids"]) == sorted(RETRACTED_IDS)
    assert report["trusted_issuer_count"] == 0
    assert report["trusted_issuer_store_empty"] is True
    assert report["gd_03_status"] == STATUS_PROPOSED
    assert report["current_status_counts"].get(STATUS_INVALIDATED) == 4
    assert AUTHENTICATION_LIMITATION in report["authentication_limitation"]
    assert OBSERVATION_DISCLAIMER in report["disclaimer"]


def test_surface_exposes_no_mutating_operations():
    """The module must not offer append/adopt/invalidate/write paths."""
    module = _load_surface()
    source = SURFACE.read_text(encoding="utf-8")
    for forbidden in (".append(", "write_text", "open(", "invalidate(",
                      "trusted_issuers.append", "shutil", "requests",
                      "urllib", "subprocess"):
        assert forbidden not in source, f"status surface must not contain {forbidden!r}"
    # and it holds no registry instance of its own
    assert not hasattr(module, "registry")


def test_surface_cannot_write_to_the_trust_store(protected_digests):
    module = _load_surface()
    assert module.main([]) == module.EXIT_OK
    for path, before in protected_digests.items():
        assert _digest(path) == before


def test_surface_exit_codes_distinguish_observation_from_failure(tmp_path, capsys):
    module = _load_surface()
    ok = module.main(["--repo-root", str(REPO_ROOT)])
    assert ok == module.EXIT_OK

    broken = tmp_path / "repo"
    (broken / "evidence").mkdir(parents=True)
    # ledger absent -> fail closed
    bad = module.main(["--repo-root", str(broken)])
    assert bad == module.EXIT_ARTIFACT_FAILURE
    captured = capsys.readouterr()
    assert "GOVERNANCE LOAD FAILED" in captured.err
    assert "NOT the same as 'no authority'" in captured.err


def test_surface_json_mode_reports_failure_distinctly(tmp_path, capsys):
    module = _load_surface()
    broken = tmp_path / "repo"
    (broken / "evidence").mkdir(parents=True)
    assert module.main(["--repo-root", str(broken), "--json"]) \
        == module.EXIT_ARTIFACT_FAILURE
    payload = json.loads(capsys.readouterr().out)
    assert payload["loaded"] is False
    assert "NOT the same as 'no authority'" in payload["note"]
    assert "effective_authority_count" not in payload


def test_surface_runs_end_to_end_as_a_subprocess(protected_digests):
    """The command actually runs, exits 0, and changes nothing."""
    result = subprocess.run(
        [sys.executable, str(SURFACE), "--repo-root", str(REPO_ROOT)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stderr
    assert "effective authority     : 0" in result.stdout
    assert "GD-2026-10-11-03            : PROPOSED" in result.stdout
    for path, before in protected_digests.items():
        assert _digest(path) == before


def test_surface_does_not_import_protected_enforcement_modules():
    """G1 must not wire governance into Broker/PEP enforcement.

    Checked at the *import* level, not by string-matching the whole file: both
    modules legitimately *mention* the Broker in prose to say they leave it
    alone, and a substring test would flag that explanation as the violation.
    """
    import ast

    for path, protected in (
            (SURFACE, {"orchestrator.auth", "orchestrator.brain",
                       "orchestrator.exec", "orchestrator.runtime"}),
            (REPO_ROOT / "src/orchestrator/rsi/governance_registry_io.py",
             {"orchestrator.auth", "orchestrator.brain",
              "orchestrator.exec", "orchestrator.runtime"}),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for name in imported:
            assert not any(name.startswith(p) or name == p for p in protected), (
                f"{path.name} must not import the enforcement path: {name}")
        # also assert no dynamic import of the protected surface
        source = path.read_text(encoding="utf-8")
        for forbidden in ("importlib.import_module", "__import__",
                          "enforce_broker_mediation", "authorize("):
            assert forbidden not in source, (
                f"{path.name} must not dynamically reach enforcement: {forbidden}")

    # the loader's only orchestrator dependency is the registry itself
    loader_src = (REPO_ROOT / "src/orchestrator/rsi/governance_registry_io.py") \
        .read_text(encoding="utf-8")
    assert "from orchestrator.rsi.governance_registry import" in loader_src