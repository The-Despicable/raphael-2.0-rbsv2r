"""Adversarial regression tests for RSI-1 measurement-integrity authority.

Every test here is an ATTACK that must be refused before any promotion
eligibility is returned, or an explicit proof that the legitimate path still
works. The audit's decisive exploit — ordinary public API usage with a
fabricated record, fabricated holdout status, fabricated evaluator identity,
fabricated gate digest, and ``independent_holdout=True`` — is reproduced
verbatim in section E.

No test here fabricates, reconstructs, or substitutes the real protected
holdout. The real holdout remains absent and is asserted to be absent.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from orchestrator.rsi import evaluation_gate as eg
from orchestrator.rsi.evaluation_gate import (
    ADEQUATE, HOLDOUT_DIGEST_MISMATCH, HOLDOUT_DUPLICATE_ROWS,
    HOLDOUT_INVALID_ENCODING, HOLDOUT_MALFORMED, HOLDOUT_MISSING,
    HOLDOUT_ROW_COUNT_MISMATCH, HOLDOUT_SCHEMA_INVALID, HOLDOUT_UNEXPECTED_PATH,
    HOLDOUT_VERIFIED, INADEQUATE, INVALID_EVIDENCE, NOT_IMPLEMENTED,
    STATE_INDEPENDENT_HOLDOUT, STATE_LOCAL_REPLAY, STATE_PROMOTION_ELIGIBLE,
    STATE_STATISTICALLY_INADEQUATE, STATE_UNVERIFIABLE_INPUTS, STATUS_BLOCKED,
    STATUS_PASS, STATUS_REFUSE, UNSPECIFIED_THRESHOLD, AnchorSet, AdequacyReport,
    DecisionLedger, EvaluationDecisionRecord, EvaluationGateError, EvaluatorIdentity,
    GateConfig, SampleEvidence, assess_statistical_adequacy,
    build_authority, classify_promotion_eligibility, load_authoritative_anchor,
    verify_authoritative_holdout, verify_holdout,
)

ADOPTED = GateConfig(config_id="adopted", campaign_id="c",
                     min_runs_per_arm=20, min_effect_size=0.05)
WITH_ALPHA = GateConfig(config_id="with-alpha", campaign_id="c",
                        min_runs_per_arm=20, significance_level=0.05)
DEFAULT = GateConfig(config_id="default", campaign_id="c")


# ══════════════════════════════════════════════════════════════════════════
# Fixture repository: an entirely synthetic, self-consistent authority chain
# ══════════════════════════════════════════════════════════════════════════

def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _rows(n: int) -> list:
    return [{"run_id": f"run-{i:05d}", "score": 1.0, "campaign": "fix-holdout"}
            for i in range(n)]


def build_fixture_repo(tmp_path: Path, *, rows=None, n_rows=3,
                       mutate_dataset=None, include_evidence=True,
                       component_suffix="v1") -> tuple:
    """Create a synthetic repo whose authority chain fully verifies."""
    root = tmp_path / "repo"
    # every hashed evaluator component must exist or identity is incomplete
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# component {rel} {component_suffix}\n", encoding="utf-8")

    dataset_rows = _rows(n_rows) if rows is None else rows
    ds_bytes = "".join(json.dumps(r, sort_keys=True) + "\n"
                       for r in dataset_rows).encode("utf-8")
    if mutate_dataset is not None:
        ds_bytes = mutate_dataset(ds_bytes)      # raw BYTES, may be invalid UTF-8
    ds_rel = "evaluations/campaign/fix_holdout.jsonl"
    ds_path = root / ds_rel
    ds_path.parent.mkdir(parents=True, exist_ok=True)
    ds_path.write_bytes(ds_bytes)

    anchor_rel = "evaluations/campaign/fix_manifest.json"
    anchor_path = root / anchor_rel
    anchor_path.write_text(json.dumps({
        "campaign": "fix-holdout",
        "dataset": {"file": ds_rel, "total_rows": len(dataset_rows),
                    "sha256": _sha(ds_bytes)},
    }, sort_keys=True), encoding="utf-8")

    anchors = AnchorSet(holdout_anchor_file=anchor_rel,
                        holdout_anchor_sha256=_sha(anchor_path.read_bytes()),
                        holdout_required_row_keys=("run_id",))

    # SYNTHETIC-AUTHORITY: an adoption registry for the configs this suite
    # exercises, so Phase 2's adoption gate does not mask the Phase 1
    # containment controls under test. Lives only under tmp_path.
    adopted_configs = [
        GateConfig(config_id="adopted", campaign_id="c",
                   min_runs_per_arm=20, min_effect_size=0.05),
        GateConfig(config_id="with-alpha", campaign_id="with-alpha-campaign",
                   min_runs_per_arm=20, significance_level=0.05),
    ]
    adopt_rel = "evaluations/campaign/fixture_adopted_configs.json"
    adopt_path = root / adopt_rel
    adopt_path.parent.mkdir(parents=True, exist_ok=True)
    adopt_path.write_text(json.dumps({
        "schema_version": 1,
        "entries": [{"adoption_id": f"fixture-adopted-{i}",
                     "campaign_id": cfg.campaign_id, "version": 1,
                     "status": "ACTIVE", "config_digest": cfg.config_digest,
                     "config": cfg.to_dict()}
                    for i, cfg in enumerate(adopted_configs)],
    }, sort_keys=True), encoding="utf-8")

    if include_evidence:
        artefacts = {}
        for kind in eg.ATTESTATION_KINDS:
            rel = f"evidence/glm/{kind}.json"
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"kind": kind, "ok": True}, sort_keys=True),
                         encoding="utf-8")
            artefacts[kind] = {"file": rel, "sha256": _sha(p.read_bytes())}
        idx_rel = "evidence/glm/index.json"
        idx_path = root / idx_rel
        idx_path.write_text(json.dumps({"artefacts": artefacts}, sort_keys=True),
                            encoding="utf-8")
        anchors = AnchorSet(
            holdout_anchor_file=anchor_rel,
            holdout_anchor_sha256=_sha(anchor_path.read_bytes()),
            holdout_required_row_keys=("run_id",),
            evidence_index_file=idx_rel,
            evidence_index_sha256=_sha(idx_path.read_bytes()),
            adopted_config_registry_file=adopt_rel,
            adopted_config_registry_sha256=_sha(adopt_path.read_bytes()))

    return root, anchors, anchor_rel


def _anchor_without_evidence(anchors):
    """Drop ONLY the evidence-index anchor, keeping holdout + adoption pinned.

    Used to show that withdrawing the evidence index blocks the GLM-contract
    gates, independently of the adoption gate.
    """
    return AnchorSet(
        holdout_anchor_file=anchors.holdout_anchor_file,
        holdout_anchor_sha256=anchors.holdout_anchor_sha256,
        holdout_required_row_keys=anchors.holdout_required_row_keys,
        adopted_config_registry_file=anchors.adopted_config_registry_file,
        adopted_config_registry_sha256=anchors.adopted_config_registry_sha256)


def _anchor_without_adoption(anchors):
    """Drop ONLY the adoption anchor."""
    return AnchorSet(
        holdout_anchor_file=anchors.holdout_anchor_file,
        holdout_anchor_sha256=anchors.holdout_anchor_sha256,
        holdout_required_row_keys=anchors.holdout_required_row_keys,
        evidence_index_file=anchors.evidence_index_file,
        evidence_index_sha256=anchors.evidence_index_sha256)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root, anchors, anchor_rel = build_fixture_repo(tmp_path)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    return root, anchors


def _record(cfg, *, root=None, anchors=None, finalize=True, **overrides):
    """Mint a record whose claims match the DERIVED authority.

    ``finalize=True`` (the default) produces an ADMISSIBLE draft: the input
    binding, gate outcomes and final state are all derived, so the record is
    consistent with current authority and the ledger will accept it.

    ``finalize=False`` keeps the deliberately inconsistent draft shape used by
    the negative tests, so a mismatch can be introduced explicitly rather than
    by accident.
    """
    identity = EvaluatorIdentity.compute_current(cfg).identity
    runs = overrides.get("runs_candidate", 40)
    runs_b = overrides.get("runs_baseline", 40)
    auth = build_authority(cfg, runs_candidate=runs, runs_baseline=runs_b,
                           effect=overrides.get("effect", 0.2))
    base = dict(
        decision_id="d1", campaign_id=cfg.campaign_id, evaluator_identity=identity,
        evaluator_label="fixture", gate_config_digest=cfg.config_digest,
        inputs_digest="a" * 64,
        holdout_id="fix-holdout", holdout_status=auth.holdout.status,
        holdout_sha256=auth.holdout.expected_sha256,
        holdout_row_count=auth.holdout.measured_rows or 3,
        holdout_evaluation_refs=("ref-holdout",), replay_evaluation_refs=("ref-replay",),
        metrics=(("verified_rate", 0.9),), gate_outcomes=(),
        selection_history_refs=(), evidence_refs=("ref-ev",),
        parent_lineage=("parent",), rollback_target="parent",
        baseline_policy_hash="b" * 64, candidate_policy_hash="c" * 64,
        protocol_id="proto-1", metrics_frozen_digest="d" * 64,
        reviewer_authority="independent-reviewer",
        runs_candidate=40, runs_baseline=40, exclusions=0, effect=0.2,
        replay_evidence_complete=True, safety_passed=True,
        final_state=STATE_INDEPENDENT_HOLDOUT)
    base.update(overrides)
    record = EvaluationDecisionRecord.mint(**base)
    if not finalize:
        return record

    # Derive the authoritative fields exactly as admission will.
    derived = classify_promotion_eligibility(record, cfg)
    payload = {k: v for k, v in record.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [list(g) for g in derived.gates]
    payload["final_state"] = derived.state
    payload["inputs_digest"] = eg.derive_evaluation_inputs_digest(record, auth)
    return EvaluationDecisionRecord.mint(**payload)


def _fabricated_record(cfg, **overrides):
    """A maximally-credible FABRICATED record, evaluated against the REAL repo.

    Every field is filled in with a plausible-looking value; nothing here is
    derived, which is precisely the attack this suite must defeat.
    """
    base = dict(
        decision_id="fabricated", campaign_id=cfg.campaign_id,
        evaluator_identity="a" * 64, evaluator_label="independent-evaluator",
        gate_config_digest=cfg.config_digest, inputs_digest="f" * 64,
        holdout_id="rbs-v4-holdout", holdout_status=HOLDOUT_VERIFIED,
        holdout_sha256="2bf614f8eafa02533bfb522fa50ac1f1827acb0951eeeb42eff6b845a8e586b4",
        holdout_row_count=1200, holdout_evaluation_refs=("ev/holdout.json",),
        replay_evaluation_refs=("ev/replay.json",), evidence_refs=("ev/safety.json",),
        metrics=(("verified_rate", 0.99),), gate_outcomes=(("g", "PASS"),),
        selection_history_refs=(), parent_lineage=("parent-v1",),
        rollback_target="policy-v1", baseline_policy_hash="b" * 64,
        candidate_policy_hash="c" * 64, protocol_id="proto-1",
        metrics_frozen_digest="d" * 64, reviewer_authority="independent-reviewer",
        runs_candidate=1000, runs_baseline=1000, exclusions=0, effect=0.5,
        replay_evidence_complete=True, safety_passed=True, final_state="INDEPENDENT_HOLDOUT")
    base.update(overrides)
    return EvaluationDecisionRecord.mint(**base)


def _assert_not_eligible(assessment, why):
    assert assessment.state != STATE_PROMOTION_ELIGIBLE, \
        f"{why}: reached {assessment.state} — EXPLOIT STILL OPEN"
    assert assessment.hard_failures() or assessment.state in (
        STATE_UNVERIFIABLE_INPUTS, STATE_LOCAL_REPLAY,
        STATE_STATISTICALLY_INADEQUATE, STATE_INDEPENDENT_HOLDOUT), \
        f"{why}: unrecognised state {assessment.state}"


# ══════════════════════════════════════════════════════════════════════════
# A. Evaluator identity must be derived and bound, not asserted
# ══════════════════════════════════════════════════════════════════════════

def test_a1_placeholder_identity_id_refused(fixture):
    _assert_not_eligible(
        classify_promotion_eligibility(_record(ADOPTED, evaluator_identity="id"),
                                       ADOPTED), "placeholder 'id'")


def test_a2_zero_digest_identity_refused(fixture):
    _assert_not_eligible(
        classify_promotion_eligibility(_record(ADOPTED, evaluator_identity="0" * 64),
                                       ADOPTED), "zero digest")


def test_a3_malformed_identity_refused(fixture):
    for bad in ("", "unknown", "sha256:abc", "0" * 63, "g" * 64, "ID", "None"):
        _assert_not_eligible(
            classify_promotion_eligibility(_record(ADOPTED, evaluator_identity=bad),
                                           ADOPTED), f"malformed {bad!r}")


def test_a4_foreign_but_wellformed_identity_refused(fixture):
    _assert_not_eligible(
        classify_promotion_eligibility(_record(ADOPTED, evaluator_identity="a" * 64),
                                       ADOPTED), "foreign well-formed identity")


def test_a5_stale_identity_after_component_edit_refused(fixture, monkeypatch):
    """Editing an evaluator module after the record was minted invalidates it."""
    record = _record(ADOPTED)
    victim = eg._REPO_ROOT / eg.EVALUATOR_COMPONENT_MODULES[0]
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# tampered\n",
                      encoding="utf-8")
    assessment = classify_promotion_eligibility(record, ADOPTED)
    assert assessment.gate("evaluator_identity_current") == STATUS_REFUSE
    _assert_not_eligible(assessment, "stale identity after component edit")


def test_a6_gate_config_changed_after_record_refused(fixture):
    record = _record(ADOPTED)
    other = GateConfig(config_id="adopted", campaign_id="c", min_runs_per_arm=21,
                       min_effect_size=0.05)
    assessment = classify_promotion_eligibility(record, other)
    assert assessment.gate("gate_config_matches") == STATUS_REFUSE
    _assert_not_eligible(assessment, "gate config changed after record creation")


def test_a7_caller_cannot_supply_its_own_config_digest(fixture):
    record = _record(ADOPTED, gate_config_digest="f" * 64)
    _assert_not_eligible(classify_promotion_eligibility(record, ADOPTED),
                         "caller-supplied gate digest")


def test_a8_valid_current_identity_passes_identity_gate(fixture):
    assessment = classify_promotion_eligibility(_record(ADOPTED), ADOPTED)
    assert assessment.gate("evaluator_identity_current") == STATUS_PASS
    assert assessment.gate("gate_config_matches") == STATUS_PASS


def test_a9_record_hash_validity_is_not_authority():
    """In the REAL repo: a perfectly self-consistent fabricated record is refused.

    Its content hash is internally valid and its claims are plausible, but the
    anchored holdout is MISSING, so validity of the record proves nothing.
    """
    cfg = GateConfig(config_id="real", campaign_id="rbs-v4-holdout",
                     min_runs_per_arm=20, min_effect_size=0.05)
    rec = _fabricated_record(cfg)
    rebuilt = EvaluationDecisionRecord.from_dict(
        json.loads(json.dumps(rec.to_dict())))
    assert rebuilt.content_hash() == rec.content_hash(), "the record is self-consistent"
    assessment = classify_promotion_eligibility(rebuilt, cfg)
    assert assessment.gate("holdout_verification") != STATUS_PASS
    _assert_not_eligible(assessment, "valid content hash alone")


def test_a10_placeholder_detection_is_public_and_explicit():
    for bad in ("id", "0" * 64, "", "none", "N/A", "zz"):
        assert EvaluatorIdentity.is_placeholder(bad)
    assert not EvaluatorIdentity.is_placeholder("a" * 64)


# ══════════════════════════════════════════════════════════════════════════
# B. Holdout: anchored, fail-closed, unsearchable
# ══════════════════════════════════════════════════════════════════════════

def test_b0_the_exploit_parameter_no_longer_exists():
    """The decisive audit exploit's attack surface is gone at the signature."""
    import inspect
    params = inspect.signature(classify_promotion_eligibility).parameters
    assert "independent_holdout" not in params
    assert "adequacy" not in params
    assert "safety_outcomes" not in params
    assert set(params) == {"record", "config", "blocking_conditions"}


def test_b1_fabricated_verified_status_refused():
    """Claim VERIFIED on a record while the evaluator's own verification says
    MISSING: the claim is refused, and the derived status governs."""
    cfg = GateConfig(config_id="real", campaign_id="rbs-v4-holdout",
                     min_runs_per_arm=20, min_effect_size=0.05)
    rec = _fabricated_record(cfg, holdout_status=HOLDOUT_VERIFIED)
    auth = build_authority(cfg)
    assert auth.holdout.status == HOLDOUT_MISSING
    assessment = classify_promotion_eligibility(rec, cfg)
    assert assessment.gate("record_holdout_consistent") == STATUS_REFUSE
    _assert_not_eligible(assessment, "fabricated holdout_status")


def test_b2_verification_is_derived_not_asserted(fixture):
    """Deleting the dataset makes holdout verification MISSING on its own."""
    (eg._REPO_ROOT / "evaluations/campaign/fix_holdout.jsonl").unlink()
    assert verify_authoritative_holdout().status == HOLDOUT_MISSING
    assert build_authority(ADOPTED).holdout.verified is False


def test_b3_missing_canonical_holdout_is_missing_not_substituted(tmp_path,
                                                                  monkeypatch):
    root, anchors, _ = build_fixture_repo(tmp_path)
    (root / "evaluations/campaign/fix_holdout.jsonl").unlink()
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    v = verify_authoritative_holdout()
    assert v.status == HOLDOUT_MISSING
    assert v.substitution_performed is False


def test_b4_sibling_path_substitution_refused(tmp_path, monkeypatch):
    """A byte-identical sibling elsewhere must NOT be found."""
    root, anchors, _ = build_fixture_repo(tmp_path)
    ds = root / "evaluations/campaign/fix_holdout.jsonl"
    (root / "evaluations/campaign/holdout_runs").mkdir(parents=True, exist_ok=True)
    (root / "evaluations/campaign/holdout_runs/fix_holdout.jsonl").write_bytes(
        ds.read_bytes())
    ds.unlink()
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == HOLDOUT_MISSING, \
        "the evaluator searched for a matching sibling"


def test_b5_verify_holdout_accepts_no_search_paths():
    import inspect
    assert "search_paths" not in inspect.signature(verify_holdout).parameters


def test_b6_caller_supplied_digest_cannot_anchor_the_dataset(tmp_path, monkeypatch):
    """The real repo's holdout is absent; a caller cannot supply its own SHA."""
    anchor = load_authoritative_anchor()
    assert anchor.loaded and anchor.declaration is not None
    assert anchor.declaration.sha256 == (
        "2bf614f8eafa02533bfb522fa50ac1f1827acb0951eeeb42eff6b845a8e586b4")
    # planting a file with that content would require the anchored bytes, which
    # we cannot produce without the real dataset — and we do not fabricate it.
    assert verify_authoritative_holdout().status == HOLDOUT_MISSING


def test_b7_tampered_anchor_refused(tmp_path, monkeypatch):
    root, anchors, anchor_rel = build_fixture_repo(tmp_path)
    p = root / anchor_rel
    p.write_text(p.read_text(encoding="utf-8").replace("fix-holdout", "evil-holdout"),
                 encoding="utf-8")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == eg.HOLDOUT_ANCHOR_TAMPERED


def test_b8_malformed_jsonl_returns_status_never_raises(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(
        tmp_path, mutate_dataset=lambda b: b"{not json\n" + b)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == HOLDOUT_MALFORMED


def test_b9_invalid_utf8_returns_status_never_raises(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(
        tmp_path, mutate_dataset=lambda b: b + b"\xff\xfe\x00bad\n")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == HOLDOUT_INVALID_ENCODING


def test_b10_duplicate_rows_refused(tmp_path, monkeypatch):
    dup = _rows(3)
    root, anchors, _ = build_fixture_repo(tmp_path, rows=dup + [dup[0]])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == HOLDOUT_DUPLICATE_ROWS


def test_b11_row_count_mismatch_refused(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(tmp_path, n_rows=5)
    ds = root / "evaluations/campaign/fix_holdout.jsonl"
    anchor_rel = "evaluations/campaign/fix_manifest.json"
    ap = root / anchor_rel
    payload = json.loads(ap.read_text(encoding="utf-8"))
    payload["dataset"]["total_rows"] = 99
    ap.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", AnchorSet(
        holdout_anchor_file=anchor_rel, holdout_anchor_sha256=_sha(ap.read_bytes()),
        holdout_required_row_keys=("run_id",)))
    assert verify_authoritative_holdout().status == HOLDOUT_ROW_COUNT_MISMATCH


def test_b12_schema_mismatch_refused(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(
        tmp_path, rows=[{"nope": 1}, {"nope": 2}])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == HOLDOUT_SCHEMA_INVALID


def test_b13_empty_dataset_refused(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(tmp_path, rows=[])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == eg.HOLDOUT_EMPTY


def test_b14_arbitrary_local_dataset_fails_digest(tmp_path, monkeypatch):
    """An attacker-written dataset at the anchored path cannot pass the digest."""
    root, anchors, _ = build_fixture_repo(tmp_path)
    ds = root / "evaluations/campaign/fix_holdout.jsonl"
    ds.write_text(json.dumps({"run_id": "attacker"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    v = verify_authoritative_holdout()
    assert v.status == HOLDOUT_DIGEST_MISMATCH
    assert v.measured_sha256 != v.expected_sha256


def test_b15_campaign_mismatch_refused(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(
        tmp_path, rows=[{"run_id": "r1", "campaign": "other-campaign"}])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert verify_authoritative_holdout().status == eg.HOLDOUT_CAMPAIGN_MISMATCH


def test_b16_path_escape_refused(fixture):
    anchor = load_authoritative_anchor()
    escaped = eg.HoldoutDeclaration(
        holdout_id="x", campaign_id="c", path="../../../etc/passwd",
        sha256="a" * 64, row_count=1)
    v = verify_holdout(escaped)
    assert v.status == HOLDOUT_UNEXPECTED_PATH
    assert anchor.loaded


def test_b17_every_invalid_status_is_a_declared_constant():
    for status in eg.HOLDOUT_FAILURE_STATUSES:
        assert status != HOLDOUT_VERIFIED


def test_b18_record_claiming_wrong_holdout_identity_refused(fixture):
    record = _record(ADOPTED, holdout_sha256="9" * 64)
    assessment = classify_promotion_eligibility(record, ADOPTED)
    assert assessment.gate("holdout_identity_anchored") == STATUS_REFUSE
    _assert_not_eligible(assessment, "record holdout identity vs anchor")


def test_b19_replay_only_record_is_local_replay(fixture):
    record = _record(ADOPTED, holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    assessment = classify_promotion_eligibility(record, ADOPTED)
    assert assessment.state == STATE_LOCAL_REPLAY


# ══════════════════════════════════════════════════════════════════════════
# C. Statistical adequacy must fail closed
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -1, -50, 1.5, 0.5,
                                 None, True, False, "40", [], {}, object()])
def test_c1_unusable_counts_are_refused_not_compared(bad):
    for kwargs in ({"runs_candidate": bad, "runs_baseline": 40},
                   {"runs_candidate": 40, "runs_baseline": bad},
                   {"runs_candidate": 40, "runs_baseline": 40, "exclusions": bad}):
        report = assess_statistical_adequacy(effect=0.2, config=ADOPTED, **kwargs)
        assert report.status == INVALID_EVIDENCE, (bad, kwargs, report.status)
        assert report.adequate is False


def test_c2_nan_never_reaches_adequate_under_adopted_minimum():
    """Python's NaN comparisons make `nan < 20` False; validation must not."""
    report = assess_statistical_adequacy(runs_candidate=math.nan, runs_baseline=40,
                                         effect=0.2, config=ADOPTED)
    assert report.status == INVALID_EVIDENCE


def test_c3_negative_and_fractional_rejected():
    assert assess_statistical_adequacy(runs_candidate=-3, runs_baseline=40,
                                       effect=0.2, config=ADOPTED).status == INVALID_EVIDENCE
    assert assess_statistical_adequacy(runs_candidate=3.7, runs_baseline=40,
                                       effect=0.2, config=ADOPTED).status == INVALID_EVIDENCE


def test_c4_integer_valued_float_is_accepted_explicitly():
    assert SampleEvidence.validate(runs_candidate=40.0, runs_baseline=40.0) is not None
    assert SampleEvidence.validate(runs_candidate=40.5, runs_baseline=40.0) is None


def test_c5_unspecified_threshold_never_yields_adequate():
    for n in (0, 1, 2, 50, 99999):
        r = assess_statistical_adequacy(runs_candidate=n, runs_baseline=n,
                                        effect=0.9, config=DEFAULT)
        assert r.status == UNSPECIFIED_THRESHOLD and not r.adequate


def test_c6_adopted_significance_level_is_not_silently_ignored():
    """An adopted alpha that cannot be evaluated yields NOT_IMPLEMENTED."""
    r = assess_statistical_adequacy(runs_candidate=10000, runs_baseline=10000,
                                    effect=0.9, config=WITH_ALPHA)
    assert r.status == NOT_IMPLEMENTED
    assert r.adequate is False
    assert "significance_level" in r.detail


def test_c7_adopted_thresholds_are_enforced_when_evaluable():
    assert assess_statistical_adequacy(runs_candidate=2, runs_baseline=2, effect=0.9,
                                       config=ADOPTED).status == INADEQUATE
    assert assess_statistical_adequacy(runs_candidate=40, runs_baseline=40, effect=0.001,
                                       config=ADOPTED).status == INADEQUATE
    assert assess_statistical_adequacy(runs_candidate=40, runs_baseline=40, effect=0.5,
                                       config=ADOPTED).status == ADEQUATE


def test_c8_min_runs_cannot_be_manipulated_by_caller():
    lax = GateConfig(config_id="lax", campaign_id="c")
    assert lax.min_runs_per_arm is None
    # relaxing the config changes its digest, which invalidates the record
    record = _record(ADOPTED)
    assert classify_promotion_eligibility(record, lax).gate("gate_config_matches") \
        == STATUS_REFUSE


def test_c9_caller_cannot_supply_an_adequacy_report():
    import inspect
    assert "adequacy" not in inspect.signature(classify_promotion_eligibility).parameters
    assert "adequacy" not in inspect.signature(build_authority).parameters


def test_c10_no_confidence_or_p_value_is_fabricated():
    src = Path(eg.__file__).read_text(encoding="utf-8")
    for forbidden in ("p_value", "pvalue", "confidence_interval", "ci_",
                      "1.96", "1.645", "erf(", "norm.cdf"):
        assert forbidden not in src, forbidden


def test_c11_invalid_adequacy_status_refuses_the_classification(fixture):
    record = _record(ADOPTED, runs_candidate=math.nan, runs_baseline=math.nan)
    assessment = classify_promotion_eligibility(record, ADOPTED)
    assert assessment.gate("statistical_adequacy") == STATUS_REFUSE


# ══════════════════════════════════════════════════════════════════════════
# D. Ledger admission is verified against derived authority
# ══════════════════════════════════════════════════════════════════════════

def test_d1_append_without_config_is_refused(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    with pytest.raises(EvaluationGateError, match="requires the GateConfig"):
        ledger.append(_record(ADOPTED))


def test_d2_foreign_identity_record_refused(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    rec = _record(ADOPTED, evaluator_identity="a" * 64)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        ledger.append(rec, ADOPTED)


def test_d3_stale_identity_record_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    victim = eg._REPO_ROOT / eg.EVALUATOR_COMPONENT_MODULES[1]
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# stale\n",
                      encoding="utf-8")
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, ADOPTED)


def test_d4_fabricated_record_refused(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    rec = _record(ADOPTED, holdout_status=HOLDOUT_VERIFIED, holdout_sha256="0" * 64)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        ledger.append(rec, ADOPTED)


def test_d5_conflicting_record_same_id_refused(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    rec = _record(ADOPTED, evaluator_identity=EvaluatorIdentity.compute_current(
        ADOPTED).identity)
    ledger.append(rec, ADOPTED)
    clash = _record(ADOPTED, effect=0.9)
    with pytest.raises(EvaluationGateError, match="append-only"):
        ledger.append(clash, ADOPTED)


def test_d6_idempotent_re_ingest(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    rec = _record(ADOPTED)
    ledger.append(rec, ADOPTED)
    assert ledger.append(rec, ADOPTED) == rec.decision_id
    assert len(ledger.all()) == 1


def test_d7_local_replay_cannot_be_stored_as_eligible(fixture, tmp_path):
    """THE decisive containment exploit.

    derived LOCAL_REPLAY, submitted PROMOTION_ELIGIBLE -> REFUSE, and nothing is
    written. This is a containment test only: it does not assert that any real
    evaluation authority exists.
    """
    path = tmp_path / "ledger.jsonl"
    rec = _record(ADOPTED, finalize=False, holdout_evaluation_refs=(),
                  final_state=STATE_PROMOTION_ELIGIBLE)
    derived = classify_promotion_eligibility(rec, ADOPTED)
    assert derived.state == STATE_LOCAL_REPLAY
    assert not derived.hard_failures()
    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(path).append(rec, ADOPTED)
    assert not path.exists()


def test_d8_first_candidate_does_not_bypass_state_check(fixture, tmp_path):
    """derived BLOCKED/INADEQUATE, submitted ELIGIBLE -> REFUSE."""
    rec = _record(ADOPTED, finalize=False, runs_candidate=1, runs_baseline=1,
                  final_state=STATE_PROMOTION_ELIGIBLE)
    derived = classify_promotion_eligibility(rec, ADOPTED)
    assert derived.state == STATE_STATISTICALLY_INADEQUATE
    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(tmp_path / "ledger.jsonl").append(rec, ADOPTED)


def test_d9_refusal_still_blocks_false_eligible_state(fixture, tmp_path):
    """derived REFUSE, submitted ELIGIBLE -> REFUSE at the refusal gate."""
    rec = _record(ADOPTED, finalize=False, evaluator_identity="a" * 64,
                  final_state=STATE_PROMOTION_ELIGIBLE)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "ledger.jsonl").append(rec, ADOPTED)


def test_d10_gate_outcomes_mismatch_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    payload = {k: v for k, v in rec.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [["g", "PASS"]]
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="gate_outcomes mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, ADOPTED)


def test_d11_inputs_digest_mismatch_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    payload = {k: v for k, v in rec.to_dict().items() if k != "content_hash"}
    payload["inputs_digest"] = "0" * 64
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="inputs_digest mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, ADOPTED)


def test_d12_stale_config_append_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    other = GateConfig(config_id="adopted", campaign_id="c", min_runs_per_arm=21,
                       min_effect_size=0.05)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, other)


def test_d13_stale_evaluator_append_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    victim = eg._REPO_ROOT / eg.EVALUATOR_COMPONENT_MODULES[2]
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# stale\n",
                      encoding="utf-8")
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, ADOPTED)


def test_d14_valid_matching_state_is_accepted(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    rec = _record(ADOPTED)
    assert classify_promotion_eligibility(rec, ADOPTED).state == rec.final_state
    ledger.append(rec, ADOPTED)
    assert ledger.get(rec.decision_id) is not None
    assert path_exists(tmp_path / "l.jsonl")


def path_exists(p):
    return p.exists()


def test_d15_duplicate_reingest_is_revalidated(fixture, tmp_path):
    """An identical stored record must NOT bypass fresh authority checks."""
    path = tmp_path / "l.jsonl"
    rec = _record(ADOPTED)
    ledger = DecisionLedger(path)
    ledger.append(rec, ADOPTED)
    # evaluator changes AFTER a legitimate admission: re-ingest must now fail,
    # where the old code returned early on identical content.
    victim = eg._REPO_ROOT / eg.EVALUATOR_COMPONENT_MODULES[3]
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# drift\n",
                      encoding="utf-8")
    reloaded = DecisionLedger(path)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        reloaded.append(rec, ADOPTED)


def test_d16_record_altered_after_minting_refused(fixture, tmp_path):
    rec = _record(ADOPTED)
    assert rec.is_intact()
    object.__setattr__(rec, "rollback_target", "attacker-policy")
    assert not rec.is_intact()
    with pytest.raises(EvaluationGateError, match="changed after minting"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, ADOPTED)


def test_d17_non_state_final_string_refused(fixture, tmp_path):
    """BLOCKED/REFUSE are gate statuses, never final states."""
    rec = _record(ADOPTED, finalize=False, final_state="BLOCKED")
    with pytest.raises(EvaluationGateError, match="not an evaluation state"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, ADOPTED)


def test_d18_historical_record_remains_readable(fixture, tmp_path):
    """A record admitted legitimately stays readable after it stops being
    current authority. Historical information is never destroyed."""
    path = tmp_path / "l.jsonl"
    rec = _record(ADOPTED)
    DecisionLedger(path).append(rec, ADOPTED)
    victim = eg._REPO_ROOT / eg.EVALUATOR_COMPONENT_MODULES[4]
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# drift\n",
                      encoding="utf-8")
    stale = DecisionLedger(path)
    stored = stale.get(rec.decision_id)
    assert stored is not None                      # readable
    assert stored.final_state == rec.final_state   # history preserved verbatim
    assert stale.historical_states()[stored.candidate_policy_hash] == rec.final_state
    assert stale.current_authority(rec.decision_id, ADOPTED) is None   # not authority
    assert rec.final_state not in stale.final_states(ADOPTED).values()


def test_d19_final_states_requires_config(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    with pytest.raises(EvaluationGateError, match="historical claims"):
        ledger.final_states()


def test_d20_forged_eligibility_not_exposed_as_authority(fixture, tmp_path):
    """A hand-forged ledger file claiming eligibility must not surface it."""
    path = tmp_path / "l.jsonl"
    forged = _record(ADOPTED, finalize=False,
                     final_state=STATE_PROMOTION_ELIGIBLE)
    path.write_text(json.dumps(forged.to_dict(), sort_keys=True) + "\n",
                    encoding="utf-8")
    ledger = DecisionLedger(path)                 # readable
    stored = ledger.get(forged.decision_id)
    assert stored is not None
    assert stored.final_state == STATE_PROMOTION_ELIGIBLE   # the historical claim
    # ...but it is NOT current authority:
    assert ledger.current_authority(forged.decision_id, ADOPTED) is None
    assert STATE_PROMOTION_ELIGIBLE not in ledger.final_states(ADOPTED).values()


def test_d21_insertion_order_not_lexical_for_lineage(fixture, tmp_path):
    """Lineage must follow insertion order, not lexical decision_id order."""
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    first = _record(ADOPTED, decision_id="z-first")
    second = _record(ADOPTED, decision_id="a-second")
    ledger.append(first, ADOPTED)
    ledger.append(second, ADOPTED)
    assert ledger.insertion_order() == ("z-first", "a-second")
    assert ledger._latest_for_candidate("c" * 64).decision_id == "a-second"


# ══════════════════════════════════════════════════════════════════════════
# D-1. Lineage supersession controls (restored coverage)
#
# These three behaviours are enforced by
# ``DecisionLedger._check_lineage`` (roadmap INV-21, L26). They were exercised
# indirectly before; this section asserts each control explicitly so a future
# refactor cannot silently weaken lineage monotonicity.
#
# They run against the SYNTHETIC-AUTHORITY fixture (an adopted config under
# tmp_path) so that the Phase 2 adoption gate does not mask the lineage
# behaviour. No production adoption artifact is created.
# ══════════════════════════════════════════════════════════════════════════

def _superseding(cfg, decision_id, parent_lineage, **overrides):
    """A record that is fully FINALISED and therefore admissible on its own."""
    return _record(cfg, decision_id=decision_id,
                   parent_lineage=parent_lineage, **overrides)


def test_admission_derives_authority_exactly_once(fixture, tmp_path):
    """P1-1 regression: one admission reads pinned authority ONCE.

    ``DecisionLedger._derive`` must not build authority and then let the
    classifier build it again: two reads could observe different anchor bytes,
    so the state, gate and evaluation-input checks would not share one
    observation. Counting ``build_authority`` calls makes that verifiable.
    """
    import inspect
    assert "authority" not in inspect.signature(
        classify_promotion_eligibility).parameters, \
        "authority must never be a caller-supplied parameter"

    real_build = eg.build_authority
    calls = {"n": 0}

    def counting(*args, **kwargs):
        calls["n"] += 1
        return real_build(*args, **kwargs)

    # Build the record BEFORE counting: constructing a finalised record
    # classifies it, which is fixture work, not admission work.
    record = _record(ADOPTED, decision_id="authority-once")
    eg.build_authority = counting
    try:
        calls["n"] = 0
        DecisionLedger(tmp_path / "l.jsonl").append(record, ADOPTED)
        assert calls["n"] == 1, f"admission derived authority {calls['n']}x"

        calls["n"] = 0
        classify_promotion_eligibility(record, ADOPTED)
        assert calls["n"] == 1, f"classifier derived authority {calls['n']}x"
    finally:
        eg.build_authority = real_build


def test_legitimate_supersession_is_accepted(fixture, tmp_path):
    """POSITIVE CONTROL: a replay decision is superseded by a genuinely new
    evaluation that names its predecessor.

    The successor differs by a REAL evaluation input (a different frozen
    selection history), not merely by ``decision_id``, so the evaluation-input
    identity changes for the correct reason.

    Proves the lineage controls do not simply refuse everything.
    """
    path = tmp_path / "l.jsonl"
    ledger = DecisionLedger(path)
    replay = _record(ADOPTED, decision_id="A-replay", holdout_evaluation_refs=())
    assert replay.final_state == STATE_LOCAL_REPLAY
    ledger.append(replay, ADOPTED)

    successor = _superseding(ADOPTED, "B-eligible", ("A-replay",),
                             selection_history_refs=("sel-new-round",))
    assert successor.final_state == STATE_PROMOTION_ELIGIBLE
    assert successor.inputs_digest != replay.inputs_digest   # real input changed

    assert ledger.append(successor, ADOPTED) == "B-eligible"
    assert ledger.final_states(ADOPTED) == {
        successor.candidate_policy_hash: STATE_PROMOTION_ELIGIBLE}
    # the predecessor remains readable history
    assert ledger.get("A-replay") is not None
    assert ledger.insertion_order() == ("A-replay", "B-eligible")


def test_supersession_without_predecessor_is_refused(fixture, tmp_path):
    """A superseding decision that does not NAME its predecessor is refused.

    ISOLATED: the successor carries a genuinely DIFFERENT evaluation input, so
    the same-input guard cannot fire; predecessor naming is the only remaining
    reason for refusal.
    """
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    replay = _record(ADOPTED, decision_id="A-replay", holdout_evaluation_refs=())
    ledger.append(replay, ADOPTED)

    successor = _superseding(ADOPTED, "B-unlinked", ("some-other-parent",),
                             selection_history_refs=("sel-new-round",))
    assert successor.final_state == STATE_PROMOTION_ELIGIBLE
    assert successor.inputs_digest != replay.inputs_digest
    with pytest.raises(EvaluationGateError, match="does not name the superseded"):
        ledger.append(successor, ADOPTED)
    assert len(ledger.all()) == 1                     # nothing was written


def test_same_inputs_supersession_is_refused(fixture, tmp_path):
    """A blocked decision cannot be re-labelled as eligible on the SAME
    evaluation inputs.

    ISOLATED: the successor NAMES its predecessor, so predecessor validation
    passes and the same-input guard is the only possible reason for refusal.
    Only ``decision_id`` and the holdout evidence reference differ; every
    evaluation input is identical, so the evaluation-input digests match.
    """
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    replay = _record(ADOPTED, decision_id="A-blocked", holdout_evaluation_refs=())
    assert replay.final_state == STATE_LOCAL_REPLAY
    ledger.append(replay, ADOPTED)

    successor = _superseding(ADOPTED, "B-same-inputs", ("A-blocked",))
    assert successor.final_state == STATE_PROMOTION_ELIGIBLE
    assert successor.inputs_digest == replay.inputs_digest, \
        "precondition: identical evaluation inputs must share an input identity"
    assert tuple(successor.parent_lineage) == ("A-blocked",), \
        "precondition: predecessor naming is VALID, isolating the same-input guard"

    with pytest.raises(EvaluationGateError, match="SAME evaluation inputs"):
        ledger.append(successor, ADOPTED)
    assert len(ledger.all()) == 1


def test_decision_id_alone_does_not_change_evaluation_input_identity(fixture):
    """P1-2 regression: ``decision_id`` is record identity, not an evaluation
    input. Renaming a decision must not make identical inputs look like a
    different experiment."""
    auth = build_authority(ADOPTED, runs_candidate=40, runs_baseline=40, effect=0.2)
    left = _record(ADOPTED, decision_id="decision-one")
    right = _record(ADOPTED, decision_id="decision-two")
    assert left.decision_id != right.decision_id
    assert left.inputs_digest == right.inputs_digest


def test_meaningful_input_change_does_change_evaluation_input_identity(fixture):
    """The converse: a real evaluation input change MUST be visible."""
    base = _record(ADOPTED, decision_id="decision-one")
    changed_selection = _record(ADOPTED, decision_id="decision-one",
                                selection_history_refs=("sel-new",))
    changed_candidate = _record(ADOPTED, decision_id="decision-one",
                                candidate_policy_hash="9" * 64)
    assert base.inputs_digest != changed_selection.inputs_digest
    assert base.inputs_digest != changed_candidate.inputs_digest


def test_superseding_record_with_duplicate_decision_id_is_refused(fixture,
                                                                  tmp_path):
    """Reusing an existing decision_id with different content hits the
    append-only guard, which runs BEFORE the lineage rules."""
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    first = _record(ADOPTED, decision_id="B-eligible")
    ledger.append(first, ADOPTED)
    clash = _record(ADOPTED, decision_id="B-eligible", effect=0.9)
    with pytest.raises(EvaluationGateError, match="append-only"):
        ledger.append(clash, ADOPTED)


def test_lineage_predecessor_follows_insertion_order_not_lexical_id(fixture,
                                                                   tmp_path):
    """The predecessor is the most recently INSERTED decision for the candidate,
    even when a lexically LATER id exists earlier in the ledger."""
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    zzz = _record(ADOPTED, decision_id="zzz-first")     # lexically LAST, inserted FIRST
    aaa = _record(ADOPTED, decision_id="aaa-second")    # lexically FIRST, inserted LAST
    ledger.append(zzz, ADOPTED)
    ledger.append(aaa, ADOPTED)
    latest = ledger._latest_for_candidate("c" * 64)
    assert latest.decision_id == "aaa-second"           # insertion, not lexical
    assert max(["zzz-first", "aaa-second"]) == "zzz-first"   # lexical would differ
    assert latest.decision_id != "zzz-first"


def test_d9_tampered_ledger_line_is_detected(fixture, tmp_path):
    path = tmp_path / "l.jsonl"
    rec = _record(ADOPTED)
    path.write_text(json.dumps(rec.to_dict(), sort_keys=True) + "\n", encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["rollback_target"] = "attacker-policy"   # a real, detectable rewrite
    assert payload["content_hash"] == rec.content_hash()
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(EvaluationGateError, match="content_hash mismatch"):
        DecisionLedger(path)


def test_d10_unsigned_record_refused(fixture):
    payload = _record(ADOPTED).to_dict()
    payload.pop("content_hash")
    with pytest.raises(EvaluationGateError, match="no content_hash"):
        EvaluationDecisionRecord.from_dict(payload)


# ══════════════════════════════════════════════════════════════════════════
# E. The audit exploit itself
# ══════════════════════════════════════════════════════════════════════════

def test_e1_the_exact_audit_exploit_no_longer_compiles():
    """Ordinary public API call from the audit must be impossible."""
    cfg = GateConfig(config_id="c1", campaign_id="d2-bounded-episode")
    adq = AdequacyReport(observed_runs_candidate=50, observed_runs_baseline=50,
                         observed_exclusions=0, observed_effect=0.3,
                         min_runs_per_arm=20, min_effect_size=0.05,
                         significance_level=0.05, status="ADEQUATE", detail="")
    rec = EvaluationDecisionRecord.mint(
        decision_id="attack", campaign_id="d2-bounded-episode",
        evaluator_identity="id", evaluator_label="whatever",
        gate_config_digest=cfg.config_digest, inputs_digest="x",
        holdout_id="whatever", holdout_status=HOLDOUT_VERIFIED, holdout_sha256="b" * 64,
        metrics=(("verified_rate", 0.99),), gate_outcomes=(("g", "PASS"),),
        selection_history_refs=(), evidence_refs=("e",),
        parent_lineage=("p",), rollback_target="p",
        baseline_policy_hash="c" * 64, candidate_policy_hash="d" * 64,
        replay_evidence_complete=True, safety_passed=True,
        final_state="INDEPENDENT_HOLDOUT")
    # the audit's call shape now raises: the parameter is gone
    with pytest.raises(TypeError):
        classify_promotion_eligibility(rec, cfg, adq, independent_holdout=True)
    # and the honest call shape refuses the fabricated claims
    _assert_not_eligible(classify_promotion_eligibility(rec, cfg),
                         "verbatim audit exploit")


def test_e2_full_authority_reaches_eligible_then_evidence_index_withdrawal_blocks(
        tmp_path, monkeypatch):
    """With a pinned evidence index every gate verifies and eligibility is real;
    withdrawing the index blocks it again — the honest NOT-READY behaviour."""
    root, anchors, _ = build_fixture_repo(tmp_path, include_evidence=True)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    # ADOPTED is the SYNTHETIC-AUTHORITY config pinned by build_fixture_repo, so
    # the Phase 2 adoption gate passes here and the evidence-index withdrawal is
    # what actually blocks the second half of this test.
    cfg = ADOPTED
    rec = _record(cfg)
    a = classify_promotion_eligibility(rec, cfg)
    assert a.state == STATE_PROMOTION_ELIGIBLE, a.reasons
    assert a.gate("configuration_adopted") == STATUS_PASS
    for gate in ("safety", "replay_evidence_complete", "retention_result",
                 "transfer_result", "stability_result", "resource_budget",
                 "protocol_preregistered", "metrics_frozen", "reviewer_authority"):
        assert a.gate(gate) == STATUS_PASS, gate

    # Same synthetic repo, with ONLY the evidence-index anchor withdrawn.
    # Adoption stays pinned, so the GLM-contract gates are what block.
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", _anchor_without_evidence(anchors))
    rec2 = _record(cfg)
    b = classify_promotion_eligibility(rec2, cfg)
    assert b.state == STATE_INDEPENDENT_HOLDOUT, b.reasons
    assert b.gate("configuration_adopted") == STATUS_PASS      # adoption held
    assert b.gate("safety") == STATUS_BLOCKED                  # index withdrawn
    assert b.gate("retention_result") == STATUS_BLOCKED
    assert b.gate("independent_holdout") == STATUS_PASS

    # And with ONLY the adoption anchor withdrawn, the authoritative path refuses.
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", _anchor_without_adoption(anchors))
    c = classify_promotion_eligibility(_record(cfg), cfg)
    assert c.gate("configuration_adopted") == STATUS_REFUSE
    assert c.state == STATE_UNVERIFIABLE_INPUTS


def test_e3_legitimate_path_is_not_vacuously_blocked(fixture):
    """The remediation must not simply break everything."""
    a = classify_promotion_eligibility(_record(ADOPTED), ADOPTED)
    assert a.state == STATE_PROMOTION_ELIGIBLE, a.reasons
    # configuration_adoption_status is an informational gate reporting the
    # resolved adoption status, so it is not a PASS/REFUSE verdict.
    verdicts = [s for n, s in a.gates if n != "configuration_adoption_status"]
    assert all(s == STATUS_PASS for s in verdicts), a.gates
    assert a.gate("configuration_adoption_status") == "ADOPTED"


def test_e4_blocking_conditions_can_only_add_blocks(fixture):
    base = classify_promotion_eligibility(_record(ADOPTED), ADOPTED)
    blocked = classify_promotion_eligibility(
        _record(ADOPTED), ADOPTED, blocking_conditions=("methodology not archived",))
    assert base.state == STATE_PROMOTION_ELIGIBLE
    assert blocked.state == STATE_INDEPENDENT_HOLDOUT
    assert "blocking_condition:methodology not archived" in dict(blocked.gates)


def test_e5_real_repository_state_is_blocked_not_eligible():
    """In THIS repository: holdout absent, no threshold, no evidence index."""
    cfg = GateConfig(config_id="real", campaign_id="rbs-v4-holdout")
    auth = build_authority(cfg)
    assert auth.holdout.status == HOLDOUT_MISSING
    assert auth.adequacy.status == UNSPECIFIED_THRESHOLD
    assert auth.evidence.status == eg.EVIDENCE_INDEX_MISSING
    assert not auth.holdout.verified


def test_e6_no_promotion_or_rollback_entry_points_exist():
    src = Path(eg.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("def promote", "def rollback", "def deploy", "def accept"):
        assert forbidden not in src


def test_e7_classifier_is_pure_and_writes_nothing(fixture, tmp_path):
    rec = _record(ADOPTED)
    before = {p: p.stat().st_mtime_ns for p in (eg._REPO_ROOT).rglob("*")
              if p.is_file()}
    first = classify_promotion_eligibility(rec, ADOPTED)
    second = classify_promotion_eligibility(rec, ADOPTED)
    after = {p: p.stat().st_mtime_ns for p in (eg._REPO_ROOT).rglob("*")
             if p.is_file()}
    assert first.state == second.state and first.gates == second.gates
    assert before == after


def test_e8_recompute_matches_classification(fixture):
    rec = _record(ADOPTED)
    assert eg.recompute_gate_outcomes(rec, ADOPTED) == \
        classify_promotion_eligibility(rec, ADOPTED).gates