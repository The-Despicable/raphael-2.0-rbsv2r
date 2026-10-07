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
            evidence_index_sha256=_sha(idx_path.read_bytes()))

    return root, anchors, anchor_rel


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root, anchors, anchor_rel = build_fixture_repo(tmp_path)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    return root, anchors


def _record(cfg, *, root=None, anchors=None, **overrides):
    """Mint a record whose claims match the DERIVED authority (legitimate shape)."""
    identity = EvaluatorIdentity.compute_current(cfg).identity
    auth = build_authority(cfg, runs_candidate=40, runs_baseline=40, effect=0.2)
    base = dict(
        decision_id="d1", campaign_id=cfg.campaign_id, evaluator_identity=identity,
        evaluator_label="fixture", gate_config_digest=cfg.config_digest,
        inputs_digest="a" * 64,
        holdout_id="fix-holdout", holdout_status=auth.holdout.status,
        holdout_sha256=auth.holdout.expected_sha256,
        holdout_row_count=auth.holdout.measured_rows or 3,
        holdout_evaluation_refs=("ref-holdout",), replay_evaluation_refs=("ref-replay",),
        metrics=(("verified_rate", 0.9),), gate_outcomes=(("g", "PASS"),),
        selection_history_refs=(), evidence_refs=("ref-ev",),
        parent_lineage=("parent",), rollback_target="parent",
        baseline_policy_hash="b" * 64, candidate_policy_hash="c" * 64,
        protocol_id="proto-1", metrics_frozen_digest="d" * 64,
        reviewer_authority="independent-reviewer",
        runs_candidate=40, runs_baseline=40, exclusions=0, effect=0.2,
        replay_evidence_complete=True, safety_passed=True,
        final_state="PENDING")
    base.update(overrides)
    return EvaluationDecisionRecord.mint(**base)


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


def test_d7_pass_after_blocked_on_same_inputs_refused(fixture, tmp_path):
    """A blocked decision cannot be superseded by re-labelling the same run."""
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    blocked = _record(ADOPTED, decision_id="d-blocked", final_state=STATE_UNVERIFIABLE_INPUTS,
                      evaluator_identity="a" * 64)
    with pytest.raises(EvaluationGateError):
        ledger.append(blocked, ADOPTED)
    # simulate a prior blocked decision landing in the ledger
    ledger._index[blocked.decision_id] = blocked
    ledger._lineage[blocked.candidate_policy_hash] = blocked.final_state
    supersede = _record(ADOPTED, decision_id="d-pass",
                        final_state=STATE_PROMOTION_ELIGIBLE, inputs_digest="a" * 64,
                        parent_lineage=("d-blocked",))
    with pytest.raises(EvaluationGateError, match="lineage violation"):
        ledger.append(supersede, ADOPTED)


def test_d8_superseding_requires_distinct_inputs_and_lineage(fixture, tmp_path):
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    blocked = _record(ADOPTED, decision_id="d-blocked",
                      final_state=STATE_STATISTICALLY_INADEQUATE)
    ledger._index[blocked.decision_id] = blocked
    ledger._lineage[blocked.candidate_policy_hash] = blocked.final_state
    good = _record(ADOPTED, decision_id="d-pass", final_state=STATE_PROMOTION_ELIGIBLE,
                   inputs_digest="e" * 64, parent_lineage=("d-blocked",))
    ledger.append(good, ADOPTED)          # legitimate supersession is allowed
    assert ledger.final_states()[good.candidate_policy_hash] == STATE_PROMOTION_ELIGIBLE


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
    cfg = GateConfig(config_id="f", campaign_id="c", min_runs_per_arm=20,
                     min_effect_size=0.05)
    rec = _record(cfg)
    a = classify_promotion_eligibility(rec, cfg)
    assert a.state == STATE_PROMOTION_ELIGIBLE, a.reasons
    for gate in ("safety", "replay_evidence_complete", "retention_result",
                 "transfer_result", "stability_result", "resource_budget",
                 "protocol_preregistered", "metrics_frozen", "reviewer_authority"):
        assert a.gate(gate) == STATUS_PASS, gate

    # a fresh record in a repo with NO adopted evidence index
    root2, anchors2, _ = build_fixture_repo(tmp_path / "second", include_evidence=False)
    monkeypatch.setattr(eg, "_REPO_ROOT", root2)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors2)
    rec2 = _record(cfg)
    b = classify_promotion_eligibility(rec2, cfg)
    assert b.state == STATE_INDEPENDENT_HOLDOUT, b.reasons
    assert b.gate("safety") == STATUS_BLOCKED
    assert b.gate("retention_result") == STATUS_BLOCKED
    assert b.gate("independent_holdout") == STATUS_PASS


def test_e3_legitimate_path_is_not_vacuously_blocked(fixture):
    """The remediation must not simply break everything."""
    a = classify_promotion_eligibility(_record(ADOPTED), ADOPTED)
    assert a.state == STATE_PROMOTION_ELIGIBLE, a.reasons
    assert all(s == STATUS_PASS for _, s in a.gates)


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