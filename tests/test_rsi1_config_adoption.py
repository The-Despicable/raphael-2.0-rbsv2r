"""Phase 2 — configuration-adoption separation.

EXPERIMENTAL CONFIGURATION != ADOPTED AUTHORITATIVE CONFIGURATION.

A caller-created ``GateConfig`` stays a fully valid research configuration. It
becomes promotion-authoritative only when an INDEPENDENTLY resolved,
source-pinned adoption registry says so.

Production state is asserted to be UNADOPTED: this repository has adopted no
evaluation configuration, and none was invented to make a positive test pass.

Every test that exercises a positive adoption path is labelled
``SYNTHETIC-AUTHORITY``: those registries live only under pytest ``tmp_path``,
are pinned inside the test harness, and are NOT promotion evidence.

No GRPO, learning loop, measurement derivation, snapshot change, promotion,
deployment, or statistical protocol is implemented or exercised here.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from orchestrator.rsi import evaluation_gate as eg
from orchestrator.rsi.evaluation_gate import (
    ADOPTION_ADOPTED, ADOPTION_BINDING_MISMATCH, ADOPTION_REGISTRY_MALFORMED,
    ADOPTION_REGISTRY_TAMPERED, ADOPTION_REGISTRY_UNAVAILABLE, ADOPTION_UNADOPTED,
    STATE_LOCAL_REPLAY, STATE_PROMOTION_ELIGIBLE, STATUS_PASS, STATUS_REFUSE,
    AnchorSet, ConfigAdoption, DecisionLedger, EvaluationDecisionRecord,
    EvaluationGateError, EvaluatorIdentity, GateConfig, PROMOTION_REQUIREMENTS,
    build_authority, classify_promotion_eligibility, resolve_config_adoption,
)

REPO = Path(eg._REPO_ROOT)
CAMPAIGN = "phase2-synthetic-campaign"
ADOPT = GateConfig(config_id="adopted-synthetic", campaign_id=CAMPAIGN,
                   min_runs_per_arm=20, min_effect_size=0.05)


# ══════════════════════════════════════════════════════════════════════════
# SYNTHETIC-AUTHORITY fixture builder (tmp_path only, never production)
# ══════════════════════════════════════════════════════════════════════════

def _sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _entry(cfg: GateConfig, *, adoption_id="synthetic-adoption-1", version=1,
           status="ACTIVE") -> dict:
    return {"adoption_id": adoption_id, "campaign_id": cfg.campaign_id,
            "version": version, "status": status,
            "config_digest": cfg.config_digest, "config": cfg.to_dict()}


def _write_registry(root: Path, entries: list, relpath: str,
                    *, raw_bytes: bytes | None = None) -> tuple:
    """Write a SYNTHETIC registry and return (relpath, digest-of-written-bytes)."""
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    if raw_bytes is not None:
        target.write_bytes(raw_bytes)
    else:
        target.write_text(json.dumps({"schema_version": 1, "entries": entries},
                                     sort_keys=True, separators=(",", ":")),
                          encoding="utf-8")
    return relpath, _sha(target.read_bytes())


def _synthetic_repo(tmp_path, name, entries, *, raw_bytes=None,
                    relpath="evaluations/campaign/synthetic_configs.json",
                    pin_digest=None):
    """SYNTHETIC-AUTHORITY: a throwaway repo whose registry is pinned here."""
    root = tmp_path / name
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    # Copy the real holdout anchor so the anchor gate resolves LOADED. Its pinned
    # digest still matches, and the holdout DATASET stays absent, so no holdout
    # authority is created here.
    holdout_anchor = REPO / eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file
    if holdout_anchor.is_file():
        dst = root / eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(holdout_anchor, dst)
    rel, real_digest = _write_registry(root, entries, relpath, raw_bytes=raw_bytes)
    anchors = AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file=rel,
        adopted_config_registry_sha256=pin_digest if pin_digest else real_digest)
    return root, anchors


def _adopted_repo(tmp_path, monkeypatch, name="adopted", **kwargs):
    root, anchors = _synthetic_repo(tmp_path, name, [_entry(ADOPT)], **kwargs)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    return root, anchors


# ══════════════════════════════════════════════════════════════════════════
# A. PRODUCTION STATE — no adoption, and none invented
# ══════════════════════════════════════════════════════════════════════════

def test_a1_no_production_adoption_registry_is_pinned():
    anchors = eg.AUTHORITATIVE_ANCHORS
    assert anchors.adopted_config_registry_file is None
    assert anchors.adopted_config_registry_sha256 is None
    assert anchors.config_registry_adopted() is False


def test_a2_no_production_registry_artifact_exists_in_the_repo():
    """No adopted-configuration artifact exists outside this test module."""
    assert not (REPO / "evaluations/campaign/adopted_evaluation_configs.json").exists()
    # search source/config/evidence trees only: the test module itself matches
    for tree in ("src", "policies", "configurations", "evaluations", "evidence",
                 "scripts"):
        base = REPO / tree
        if not base.is_dir():
            continue
        for candidate in base.rglob("*config*adopt*"):
            assert not candidate.is_file(), f"unexpected adoption artifact: {candidate}"
        for candidate in base.rglob("*adopted*config*.json"):
            assert not candidate.is_file(), f"unexpected adoption artifact: {candidate}"


def test_a3_production_resolves_unadopted():
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_UNADOPTED
    assert adoption.adopted is False
    assert "no evaluation-configuration adoption registry" in adoption.detail


def test_a4_weak_config_stays_unadopted():
    weak = GateConfig(config_id="weak", campaign_id=CAMPAIGN)
    adoption = resolve_config_adoption(weak)
    assert adoption.status == ADOPTION_UNADOPTED
    assert not adoption.adopted


def test_a5_zero_threshold_config_stays_unadopted():
    """Zero thresholds are NOT declared invalid here. The roadmap defines no
    statistical rule, so a zero-threshold config stays a valid EXPERIMENTAL
    config; it simply has no adopted authority."""
    zero = GateConfig(config_id="zero", campaign_id=CAMPAIGN,
                      min_runs_per_arm=0, min_effect_size=0.0,
                      max_exclusion_fraction=0.0)
    assert zero.config_digest                       # internally consistent
    assert resolve_config_adoption(zero).status == ADOPTION_UNADOPTED
    # Experimental adequacy still works: zero thresholds are simply adopted by
    # this research config. No statistical rule is declared here.
    report = eg.assess_statistical_adequacy(runs_candidate=1, runs_baseline=1,
                                            effect=0.0, config=zero)
    assert report.status == "ADEQUATE", report.detail


def test_a6_experimental_analysis_is_not_blocked_by_unadopted_status():
    """Only the AUTHORITATIVE path needs adoption; research use is untouched."""
    report = eg.assess_statistical_adequacy(runs_candidate=40, runs_baseline=40,
                                            effect=0.5, config=ADOPT)
    assert report.status == "ADEQUATE"
    assert resolve_config_adoption(ADOPT).adopted is False   # yet unadopted


def test_a7_disabled_promotion_requirements_are_not_authoritative():
    disabled = GateConfig(config_id="off", campaign_id=CAMPAIGN,
                          require_safety_pass=False)
    assert disabled.require_safety_pass is False            # constructible
    assert resolve_config_adoption(disabled).status == ADOPTION_UNADOPTED
    authority = build_authority(disabled)
    assert authority.config_adoption.adopted is False


def test_a8_self_consistent_identity_without_adoption_still_refuses():
    """Matching digest + matching evaluator identity is NOT enough."""
    rec = _finalised(ADOPT)
    derived = classify_promotion_eligibility(rec, ADOPT)
    assert derived.gate("gate_config_matches") == STATUS_PASS
    assert derived.gate("evaluator_identity_current") == STATUS_PASS
    assert derived.gate("configuration_adopted") == STATUS_REFUSE
    assert derived.state != STATE_PROMOTION_ELIGIBLE


def test_a9_requirement_flags_must_be_real_booleans():
    for name in PROMOTION_REQUIREMENTS:
        with pytest.raises(EvaluationGateError, match="must be a bool"):
            GateConfig(config_id="x", campaign_id="y", **{name: 1})


# ══════════════════════════════════════════════════════════════════════════
# B. SYNTHETIC-AUTHORITY positive path
# ══════════════════════════════════════════════════════════════════════════

def test_b6_valid_synthetic_registry_resolves_adopted(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_ADOPTED
    assert adoption.adopted is True
    assert adoption.adoption_id == "synthetic-adoption-1"
    assert adoption.campaign_id == CAMPAIGN
    assert adoption.version == 1
    assert adoption.config_digest == ADOPT.config_digest
    assert _is_sha(adoption.registry_digest)


def _is_sha(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and \
        all(c in "0123456789abcdef" for c in value)


def test_b7_exact_campaign_match_passes(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    assert resolve_config_adoption(ADOPT).campaign_id == CAMPAIGN


def test_b8_exact_config_digest_match_passes(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.config_digest == ADOPT.config_digest


def test_b9_exact_canonical_payload_match_passes(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    entry = _entry(ADOPT)
    assert entry["config"] == ADOPT.to_dict()
    assert resolve_config_adoption(ADOPT).adopted is True


def test_b10_correct_active_version_passes(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(
        tmp_path, "versions",
        [_entry(ADOPT, version=1, status="SUPERSEDED"),
         _entry(ADOPT, version=2, status="ACTIVE", adoption_id="synthetic-v2")])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.adopted is True
    assert adoption.version == 2
    assert adoption.adoption_id == "synthetic-v2"


def test_b11_adopted_config_passes_the_authority_gate(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    derived = classify_promotion_eligibility(_finalised(ADOPT), ADOPT)
    assert derived.gate("configuration_adopted") == STATUS_PASS
    assert derived.gate("configuration_adoption_status") == ADOPTION_ADOPTED


def test_b12_adoption_id_is_derived_not_caller_supplied(tmp_path, monkeypatch):
    """resolve_config_adoption accepts no adoption id / digest / path."""
    import inspect
    params = set(inspect.signature(resolve_config_adoption).parameters)
    assert params == {"config", "anchors"}
    for forbidden in ("adoption_id", "registry_digest", "registry_path",
                      "adopted", "trust"):
        assert forbidden not in params


def test_b13_classifier_and_build_authority_take_no_adoption_input():
    import inspect
    assert set(inspect.signature(classify_promotion_eligibility).parameters) == {
        "record", "config", "blocking_conditions"}
    assert "config_adoption" not in inspect.signature(build_authority).parameters


# ══════════════════════════════════════════════════════════════════════════
# C. TAMPERING / NEGATIVE ADOPTION RESOLUTION
# ══════════════════════════════════════════════════════════════════════════

def test_c11_wrong_registry_digest_refuses(tmp_path, monkeypatch):
    root, _ = _synthetic_repo(tmp_path, "wrongdigest", [_entry(ADOPT)])
    anchors = AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="evaluations/campaign/synthetic_configs.json",
        adopted_config_registry_sha256="0" * 64)          # deliberately wrong
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_TAMPERED
    assert not adoption.adopted


def test_c12_registry_byte_modification_after_pinning_refuses(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(tmp_path, "modified", [_entry(ADOPT)])
    registry = root / anchors.adopted_config_registry_file
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["entries"][0]["adoption_id"] = "tampered-after-pinning"
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_REGISTRY_TAMPERED


def test_c13_wrong_config_refuses(tmp_path, monkeypatch):
    """A registry adopting a DIFFERENT config must not adopt this one."""
    other = GateConfig(config_id="different", campaign_id=CAMPAIGN,
                       min_runs_per_arm=99)
    root, anchors = _synthetic_repo(tmp_path, "wrongcfg", [_entry(other)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_BINDING_MISMATCH
    assert not adoption.adopted


def test_c14_wrong_campaign_refuses(tmp_path, monkeypatch):
    """Same config, different campaign => no ACTIVE adoption for this campaign."""
    other = GateConfig(config_id=ADOPT.config_id, campaign_id="other-campaign",
                       min_runs_per_arm=20, min_effect_size=0.05)
    root, anchors = _synthetic_repo(tmp_path, "wrongcampaign", [_entry(other)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_UNADOPTED
    assert "no ACTIVE adoption" in adoption.detail


def test_c15_revoked_entry_refuses(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(
        tmp_path, "revoked", [_entry(ADOPT, status="REVOKED")])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_UNADOPTED


def test_c16_superseded_entry_refuses(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(
        tmp_path, "superseded", [_entry(ADOPT, status="SUPERSEDED")])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_UNADOPTED


def test_c17_duplicate_active_campaign_refuses(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(
        tmp_path, "dupactive",
        [_entry(ADOPT, adoption_id="a", version=1),
         _entry(ADOPT, adoption_id="b", version=2)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_MALFORMED
    assert "ACTIVE" in adoption.detail


def test_c18_duplicate_campaign_version_refuses(tmp_path, monkeypatch):
    root, anchors = _synthetic_repo(
        tmp_path, "dupver",
        [_entry(ADOPT, adoption_id="a", version=1),
         _entry(ADOPT, adoption_id="b", version=1)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_REGISTRY_MALFORMED


@pytest.mark.parametrize("version", [0, -1, True, 1.0, "1", None])
def test_c18b_invalid_version_refuses(tmp_path, monkeypatch, version):
    entry = _entry(ADOPT)
    entry["version"] = version
    root, anchors = _synthetic_repo(tmp_path, f"badver{version}", [entry])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_REGISTRY_MALFORMED


@pytest.mark.parametrize("digest", ["", "zz", "0" * 63, 123, None])
def test_c18c_invalid_config_digest_refuses(tmp_path, monkeypatch, digest):
    entry = _entry(ADOPT)
    entry["config_digest"] = digest
    root, anchors = _synthetic_repo(tmp_path, f"baddigest{digest}", [entry])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert resolve_config_adoption(ADOPT).status == ADOPTION_REGISTRY_MALFORMED


def test_c19_malformed_registry_refuses(tmp_path, monkeypatch):
    for name, payload in (
            ("notjson", b"{not json"),
            ("notobject", json.dumps([1, 2, 3]).encode()),
            ("extrakey", json.dumps({"schema_version": 1, "entries": [],
                                     "extra": 1}).encode()),
            ("badschema", json.dumps({"schema_version": 2, "entries": []}).encode()),
            ("entriesnotlist", json.dumps({"schema_version": 1,
                                           "entries": {}}).encode()),
            ("entrykeyset", json.dumps({"schema_version": 1, "entries": [
                {"adoption_id": "x", "campaign_id": "c"}]}).encode()),
            ("badstatus", json.dumps({"schema_version": 1, "entries": [
                dict(_entry(ADOPT), status="WHATEVER")]}).encode()),
    ):
        root, anchors = _synthetic_repo(tmp_path, name, [],
                                        raw_bytes=payload)
        monkeypatch.setattr(eg, "_REPO_ROOT", root)
        monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
        assert resolve_config_adoption(ADOPT).status == ADOPTION_REGISTRY_MALFORMED, name


def test_c19b_duplicate_json_keys_refuse(tmp_path, monkeypatch):
    payload = (b'{"schema_version": 1, "entries": [], '
               b'"entries": [{"adoption_id": "x"}]}')
    root, anchors = _synthetic_repo(tmp_path, "dupkeys", [], raw_bytes=payload)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_MALFORMED
    assert "duplicate JSON key" in adoption.detail


def test_c20_missing_registry_is_unavailable(tmp_path, monkeypatch):
    root, _ = _synthetic_repo(tmp_path, "missingfile", [_entry(ADOPT)])
    anchors = AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="evaluations/campaign/never_written.json",
        adopted_config_registry_sha256="1" * 64)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_UNAVAILABLE
    assert not adoption.adopted


def test_c20b_no_pinned_registry_at_all_is_unadopted(tmp_path, monkeypatch):
    root, _ = _synthetic_repo(tmp_path, "nopin", [_entry(ADOPT)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256))
    assert resolve_config_adoption(ADOPT).status == ADOPTION_UNADOPTED


def test_c21_absolute_path_refuses(tmp_path, monkeypatch):
    root, _ = _synthetic_repo(tmp_path, "abspath", [_entry(ADOPT)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="/etc/passwd",
        adopted_config_registry_sha256="2" * 64))
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_TAMPERED
    assert "repository-relative" in adoption.detail


def test_c22_repository_escape_refuses(tmp_path, monkeypatch):
    root, _ = _synthetic_repo(tmp_path, "escape", [_entry(ADOPT)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="../outside/registry.json",
        adopted_config_registry_sha256="3" * 64))
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_TAMPERED
    assert "escapes the repository" in adoption.detail


def test_c23_sibling_substitution_refuses(tmp_path, monkeypatch):
    """A byte-identical registry in a sibling directory must NOT be found."""
    root, anchors = _synthetic_repo(tmp_path, "sibling", [_entry(ADOPT)])
    pinned = root / anchors.adopted_config_registry_file
    sibling = root / "evaluations/campaign/nested/synthetic_configs.json"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pinned, sibling)
    pinned.unlink()
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(ADOPT)
    assert adoption.status == ADOPTION_REGISTRY_UNAVAILABLE
    assert not adoption.adopted


def test_c24_disabled_requirement_in_adopted_config_refuses(tmp_path, monkeypatch):
    """An adopted config that disables a promotion-lock control is refused."""
    weak = GateConfig(config_id="adopted-synthetic", campaign_id=CAMPAIGN,
                      min_runs_per_arm=20, min_effect_size=0.05,
                      require_rollback_target=False)
    root, anchors = _synthetic_repo(tmp_path, "weakadopted", [_entry(weak)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    adoption = resolve_config_adoption(weak)
    assert adoption.status == ADOPTION_BINDING_MISMATCH
    assert "promotion-lock requirement" in adoption.detail


def test_c25_malformed_pinned_path_refuses():
    anchors = AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="", adopted_config_registry_sha256="0" * 64)
    assert resolve_config_adoption(ADOPT, anchors).status == ADOPTION_REGISTRY_TAMPERED
    anchors = AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file="x.json", adopted_config_registry_sha256="nope")
    assert resolve_config_adoption(ADOPT, anchors).status == ADOPTION_REGISTRY_TAMPERED


# ══════════════════════════════════════════════════════════════════════════
# D. Integration with Phase 1 containment
# ══════════════════════════════════════════════════════════════════════════

def _draft(cfg, **overrides):
    identity = EvaluatorIdentity.compute_current(cfg).identity
    base = dict(
        decision_id="p2", campaign_id=cfg.campaign_id, evaluator_identity=identity,
        evaluator_label="phase2", gate_config_digest=cfg.config_digest,
        inputs_digest="", holdout_id="", holdout_status="NOT_APPLICABLE",
        holdout_sha256="", holdout_evaluation_refs=(), replay_evaluation_refs=(),
        evidence_refs=(), selection_history_refs=(), parent_lineage=("parent-v1",),
        rollback_target="policy-v1", baseline_policy_hash="b" * 64,
        candidate_policy_hash="c" * 64, protocol_id="", metrics_frozen_digest="",
        reviewer_authority="", runs_candidate=0, runs_baseline=0, exclusions=0,
        effect=None, replay_evidence_complete=False, safety_passed=False,
        final_state="")
    base.update(overrides)
    return EvaluationDecisionRecord.mint(**base)


def _finalised(cfg, **overrides):
    """Record whose state/gates/inputs_digest equal freshly derived authority."""
    draft = _draft(cfg, **overrides)
    authority = build_authority(
        cfg, runs_candidate=draft.runs_candidate, runs_baseline=draft.runs_baseline,
        exclusions=draft.exclusions, effect=draft.effect)
    derived = classify_promotion_eligibility(draft, cfg)
    payload = {k: v for k, v in draft.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [list(g) for g in derived.gates]
    payload["final_state"] = derived.state
    payload["inputs_digest"] = eg.derive_evaluation_inputs_digest(draft, authority)
    return EvaluationDecisionRecord.mint(**payload)


def test_d24_adopted_plus_correct_local_replay_is_admitted(tmp_path, monkeypatch):
    """SYNTHETIC-AUTHORITY positive control: adoption does not break Phase 1."""
    _adopted_repo(tmp_path, monkeypatch)
    rec = _finalised(ADOPT, decision_id="p2-ok")
    assert rec.final_state == STATE_LOCAL_REPLAY
    DecisionLedger(tmp_path / "ledger.jsonl").append(rec, ADOPT)


def test_d25_adopted_plus_forged_eligible_still_rejected(tmp_path, monkeypatch):
    """Adoption must NOT mask the Phase 1 state-mismatch control."""
    _adopted_repo(tmp_path, monkeypatch)
    good = _finalised(ADOPT, decision_id="p2-good")
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["final_state"] = STATE_PROMOTION_ELIGIBLE
    forged = EvaluationDecisionRecord.mint(**payload)
    derived = classify_promotion_eligibility(forged, ADOPT)
    assert derived.gate("configuration_adopted") == STATUS_PASS     # adopted...
    assert derived.state == STATE_LOCAL_REPLAY                      # ...still replay
    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, ADOPT)


def test_d26_adopted_plus_dropped_gate_still_rejected(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    good = _finalised(ADOPT, decision_id="p2-gates")
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [["parent_lineage", "PASS"]]
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="gate_outcomes mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, ADOPT)


def test_d27_adopted_plus_wrong_inputs_digest_still_rejected(tmp_path, monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    good = _finalised(ADOPT, decision_id="p2-digest")
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["inputs_digest"] = "0" * 64
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="inputs_digest mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, ADOPT)


def test_d28_duplicate_gate_names_still_rejected_under_adoption(tmp_path,
                                                                  monkeypatch):
    _adopted_repo(tmp_path, monkeypatch)
    good = _finalised(ADOPT, decision_id="p2-dup")
    gates = list(good.gate_outcomes)
    dup = EvaluationDecisionRecord.mint(**{
        **{k: v for k, v in good.to_dict().items() if k != "content_hash"},
        "gate_outcomes": gates + [gates[0]]})
    with pytest.raises(EvaluationGateError, match="duplicate gate name"):
        DecisionLedger(tmp_path / "l.jsonl").append(dup, ADOPT)


def test_d29_unadopted_config_with_self_consistent_identity_refused(tmp_path):
    """No adoption anchor at all: identity matches, yet refused."""
    rec = _finalised(ADOPT, decision_id="p2-unadopted")
    derived = classify_promotion_eligibility(rec, ADOPT)
    assert derived.gate("evaluator_identity_current") == STATUS_PASS
    assert derived.gate("configuration_adopted") == STATUS_REFUSE
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(rec, ADOPT)


def test_d30_changed_adopted_config_changes_identity_and_binding(tmp_path,
                                                                  monkeypatch):
    """A DIFFERENT adopted config yields a different identity AND no binding."""
    other = GateConfig(config_id="adopted-synthetic", campaign_id=CAMPAIGN,
                       min_runs_per_arm=21, min_effect_size=0.05)
    root, anchors = _synthetic_repo(tmp_path, "changed", [_entry(other)])
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    assert EvaluatorIdentity.compute_current(ADOPT).identity != \
        EvaluatorIdentity.compute_current(other).identity
    assert resolve_config_adoption(ADOPT).status == ADOPTION_BINDING_MISMATCH
    assert resolve_config_adoption(other).status == ADOPTION_ADOPTED


def test_d31_old_identity_is_historical_only(tmp_path, monkeypatch):
    """Phase 1A identity transition still holds once adoption changes anchors."""
    _adopted_repo(tmp_path, monkeypatch)
    rec = _finalised(ADOPT, decision_id="p2-current")
    path = tmp_path / "ledger.jsonl"
    DecisionLedger(path).append(rec, ADOPT)
    payload = {k: v for k, v in rec.to_dict().items() if k != "content_hash"}
    payload["decision_id"] = "p2-stale"
    payload["evaluator_identity"] = "0" * 63 + "1"
    stale = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(path).append(stale, ADOPT)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(eg._stable(stale.to_dict()) + "\n")
    ledger = DecisionLedger(path)
    assert ledger.get("p2-stale") is not None              # readable
    assert ledger.current_authority("p2-stale", ADOPT) is None   # not authority


# ══════════════════════════════════════════════════════════════════════════
# E. Identity binding + scope guards
# ══════════════════════════════════════════════════════════════════════════

def test_e1_identity_binds_the_full_anchor_identity():
    a = eg.AnchorSet(holdout_anchor_file="h.json", holdout_anchor_sha256="a" * 64)
    b = eg.AnchorSet(holdout_anchor_file="h.json", holdout_anchor_sha256="a" * 64,
                     evidence_index_file="i.json", evidence_index_sha256="b" * 64)
    c = eg.AnchorSet(holdout_anchor_file="h.json", holdout_anchor_sha256="a" * 64,
                     adopted_config_registry_file="r.json",
                     adopted_config_registry_sha256="c" * 64)
    assert a.anchor_identity() != b.anchor_identity() != c.anchor_identity()
    assert a.anchor_identity() != c.anchor_identity()


def test_e2_evidence_index_identity_is_not_collapsed_to_a_flag():
    """Two different pinned index identities must not share one anchor digest."""
    one = eg.AnchorSet(holdout_anchor_file="h", holdout_anchor_sha256="a" * 64,
                       evidence_index_file="i", evidence_index_sha256="1" * 64)
    two = eg.AnchorSet(holdout_anchor_file="h", holdout_anchor_sha256="a" * 64,
                       evidence_index_file="i", evidence_index_sha256="2" * 64)
    assert one.anchor_identity() != two.anchor_identity()


def test_e3_no_phase3_or_phase4_symbols_exist():
    for symbol in ("derive_measurement", "MeasurementDerivation",
                   "classify_snapshot_replay", "verify_snapshot_origin",
                   "evaluator_metadata"):
        assert not hasattr(eg, symbol), f"{symbol} must not exist in Phase 2"
    assert not (Path(eg.__file__).parent / "measurement.py").exists()


def test_e4_snapshot_schema_unchanged_and_no_promotion_entry_point():
    from orchestrator.rsi import snapshot as snap
    assert snap.SCHEMA_VERSION == 1
    src = Path(eg.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("def promote", "def deploy", "def rollback_policy",
                      "per_run_observations"):
        assert forbidden not in src, forbidden


def test_e5_decision_schema_unchanged():
    assert eg.SCHEMA_VERSION == 2


def test_e6_production_authority_state_untouched():
    """Real repository remains: no holdout, no evidence index, no adoption."""
    assert not (REPO / "evaluations/campaign/rbs_v4_holdout.jsonl").exists()
    assert eg.verify_authoritative_holdout().status == "MISSING"
    assert eg.load_evidence_index().status == "NO_AUTHORITATIVE_INDEX"
    assert resolve_config_adoption(ADOPT).status == ADOPTION_UNADOPTED