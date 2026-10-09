"""tests/test_rsi1_production_adoption_registry.py — adoption authority is absent.

The independent Phase 3 readiness audit found that the committed
`evaluations/adoption/production_adoption_registry.json` carried six fabricated
"digests" — ``aabbccddeeff…``, 72 characters of ``abcd``, sequential hex, and
free text such as ``baseline_policy_digest_20261009`` — named the TEST FIXTURE
campaign ``pi-campaign``, used a schema the resolver cannot parse, and was pinned
by nothing. It is deleted.

Path A is taken deliberately: no real adopted campaign configuration, policy
manifest, evaluator identity, or policy artifact set can be verified from
committed bytes, so no replacement registry is created. ``UNADOPTED_CONFIG`` is
the correct state and must persist until an operator adopts a real campaign.

Every assertion below is behavioural. Refusal paths are exercised against
synthetic registries built from REAL digests of synthetic files under
``tmp_path`` — the same trust model as ``test_rsi1_config_adoption.py`` — so the
tests verify the resolver rather than the presence of keys in a JSON file.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
REGISTRY_REL = "evaluations/adoption/production_adoption_registry.json"
sys.path.insert(0, str(REPO / "src"))

from orchestrator.rsi import evaluation_gate as eg  # noqa: E402
from orchestrator.rsi.evaluation_gate import (  # noqa: E402
    ADOPTION_ADOPTED, ADOPTION_FAILURE_STATUSES, ADOPTION_REGISTRY_MALFORMED,
    ADOPTION_REGISTRY_TAMPERED, ADOPTION_UNADOPTED, STATE_PROMOTION_ELIGIBLE,
    HOLDOUT_VERIFIED, AnchorSet, EvaluationDecisionRecord, GateConfig,
    classify_promotion_eligibility, resolve_config_adoption,
)

CAMPAIGN = "synthetic-adoption-campaign"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry(cfg: GateConfig, *, adoption_id="synthetic-1", status="ACTIVE") -> dict:
    """An entry in EXACTLY the schema ``resolve_config_adoption`` requires."""
    return {"adoption_id": adoption_id, "campaign_id": cfg.campaign_id,
            "version": 1, "status": status,
            "config_digest": cfg.config_digest, "config": cfg.to_dict()}


def _cfg(**overrides) -> GateConfig:
    base = dict(config_id="synthetic-adopted", campaign_id=CAMPAIGN,
                min_runs_per_arm=20, min_effect_size=0.05)
    base.update(overrides)
    return GateConfig(**base)


def _install(monkeypatch, tmp_path, entries, *, raw_bytes=None):
    """Create a synthetic repo and point the gate module at it.

    ``_read_pinned_json`` resolves pinned paths against
    ``evaluation_gate._REPO_ROOT``. Without installing the synthetic root there,
    the resolver would read the REAL repository and these tests would silently
    verify nothing.
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    raw = raw_bytes if raw_bytes is not None else json.dumps(
        {"schema_version": 1, "entries": entries},
        sort_keys=True, separators=(",", ":")).encode()
    rel = "evaluations/campaign/synthetic_configs.json"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    anchors = AnchorSet(holdout_anchor_file="evaluations/campaign/absent.json",
                        holdout_anchor_sha256="0" * 64,
                        adopted_config_registry_file=rel,
                        adopted_config_registry_sha256=_sha(raw))
    return root, anchors


# ══════════════════════════════════════════════════════════════════════
# 1. No production registry exists, and none is pinned
# ══════════════════════════════════════════════════════════════════════

def test_no_production_adoption_registry_file_exists():
    assert not (REPO / REGISTRY_REL).exists(), (
        f"{REGISTRY_REL} was removed as fabricated provenance; it must not be "
        "reintroduced without real digest-verified artifacts behind it")


def test_no_production_adoption_registry_is_tracked_in_git():
    proc = subprocess.run(["git", "-C", str(REPO), "ls-files", REGISTRY_REL],
                          capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == "", (
        f"{REGISTRY_REL} is tracked in git; the fabricated registry must not "
        "come back")


def test_authoritative_anchors_pin_no_adoption_registry():
    anchors = eg.AUTHORITATIVE_ANCHORS
    assert anchors.adopted_config_registry_file is None
    assert anchors.adopted_config_registry_sha256 is None
    assert anchors.config_registry_adopted() is False


def test_anchor_set_has_no_policy_or_adoption_registry_fields():
    import dataclasses
    names = {f.name for f in dataclasses.fields(eg.AnchorSet)}
    assert not [n for n in names if "adoption" in n or "policy" in n]


# ══════════════════════════════════════════════════════════════════════
# 2. Adoption resolves to UNADOPTED and stays there
# ══════════════════════════════════════════════════════════════════════

def test_real_repo_adoption_is_unadopted():
    result = resolve_config_adoption(_cfg())
    assert result.status == ADOPTION_UNADOPTED
    assert result.adopted is False


def test_no_campaign_is_adopted_against_the_real_repo():
    """No config in this repository can be adopted today."""
    for campaign in (CAMPAIGN, "pi-campaign", "rbs-v4-holdout", "c"):
        result = resolve_config_adoption(
            GateConfig(config_id="x", campaign_id=campaign))
        assert result.adopted is False, campaign


def test_unadopted_detail_names_the_missing_registry():
    assert "no evaluation-configuration adoption registry is pinned" in \
        resolve_config_adoption(_cfg()).detail


# ══════════════════════════════════════════════════════════════════════
# 3. The resolver's real behaviour (synthetic repos, real digests)
# ══════════════════════════════════════════════════════════════════════

def test_active_entry_resolves_to_adopted(monkeypatch, tmp_path):
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path, [_entry(cfg)])
    result = resolve_config_adoption(cfg, anchors)
    assert result.status == ADOPTION_ADOPTED
    assert result.adopted is True
    assert result.adoption_id == "synthetic-1"
    assert result.config_digest == cfg.config_digest
    assert result.registry_digest == anchors.adopted_config_registry_sha256


def test_registry_digest_is_verified_against_real_bytes(monkeypatch, tmp_path):
    """A registry altered after pinning is TAMPERED."""
    cfg = _cfg()
    root, anchors = _install(monkeypatch, tmp_path, [_entry(cfg)])
    target = root / anchors.adopted_config_registry_file
    target.write_bytes(target.read_bytes() + b" ")
    result = resolve_config_adoption(cfg, anchors)
    assert result.status == ADOPTION_REGISTRY_TAMPERED
    assert result.adopted is False


def test_revoked_entry_refuses(monkeypatch, tmp_path):
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path,
                              [_entry(cfg, status="REVOKED")])
    result = resolve_config_adoption(cfg, anchors)
    assert result.adopted is False
    assert result.status == ADOPTION_UNADOPTED


def test_superseded_entry_refuses(monkeypatch, tmp_path):
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path,
                              [_entry(cfg, status="SUPERSEDED")])
    assert resolve_config_adoption(cfg, anchors).adopted is False


def test_two_active_entries_for_one_campaign_are_malformed(monkeypatch, tmp_path):
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path,
                              [_entry(cfg, adoption_id="a"),
                               _entry(cfg, adoption_id="b")])
    result = resolve_config_adoption(cfg, anchors)
    assert result.status == ADOPTION_REGISTRY_MALFORMED
    assert result.adopted is False


def test_extra_keys_in_an_entry_are_malformed(monkeypatch, tmp_path):
    """The exact schema violation the fabricated registry carried."""
    cfg = _cfg()
    entry = _entry(cfg)
    entry["policy_manifest_digest"] = "0" * 64
    _root, anchors = _install(monkeypatch, tmp_path, [entry])
    result = resolve_config_adoption(cfg, anchors)
    assert result.status == ADOPTION_REGISTRY_MALFORMED
    assert result.adopted is False


def test_missing_required_config_key_is_malformed(monkeypatch, tmp_path):
    cfg = _cfg()
    entry = _entry(cfg)
    del entry["config"]
    _root, anchors = _install(monkeypatch, tmp_path, [entry])
    assert resolve_config_adoption(cfg, anchors).status == \
        ADOPTION_REGISTRY_MALFORMED


def test_config_digest_mismatch_refuses(monkeypatch, tmp_path):
    """A registry pinning a different config digest cannot adopt this config."""
    cfg = _cfg()
    entry = _entry(cfg)
    entry["config_digest"] = "0" * 64
    _root, anchors = _install(monkeypatch, tmp_path, [entry])
    assert resolve_config_adoption(cfg, anchors).adopted is False


def test_tampered_config_payload_refuses(monkeypatch, tmp_path):
    """Flipping a promotion-lock flag in the pinned payload breaks the binding."""
    cfg = _cfg()
    entry = _entry(cfg)
    entry["config"]["require_safety_pass"] = False
    _root, anchors = _install(monkeypatch, tmp_path, [entry])
    assert resolve_config_adoption(cfg, anchors).adopted is False


def test_missing_registry_file_refuses(monkeypatch, tmp_path):
    cfg = _cfg()
    root, anchors = _install(monkeypatch, tmp_path, [_entry(cfg)])
    (root / anchors.adopted_config_registry_file).unlink()
    result = resolve_config_adoption(cfg, anchors)
    assert result.adopted is False
    assert result.status in ADOPTION_FAILURE_STATUSES


def test_malformed_registry_bytes_refuse(monkeypatch, tmp_path):
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path, [],
                              raw_bytes=b"{not json at all")
    assert resolve_config_adoption(cfg, anchors).adopted is False


def test_registry_path_escape_is_refused(monkeypatch, tmp_path):
    cfg = _cfg()
    _install(monkeypatch, tmp_path, [_entry(cfg)])
    anchors = replace(
        eg.AnchorSet(holdout_anchor_file="x", holdout_anchor_sha256="0" * 64),
        adopted_config_registry_file="../../../etc/passwd",
        adopted_config_registry_sha256="0" * 64)
    assert resolve_config_adoption(cfg, anchors).adopted is False


def test_adopting_config_that_disables_a_promotion_lock_refuses(
        monkeypatch, tmp_path):
    """Toggling a requirement flag must not manufacture authority."""
    strict = _cfg()
    entry = _entry(strict)
    entry["config"]["require_safety_pass"] = False
    entry["config_digest"] = strict.config_digest   # digest still matches...
    _root, anchors = _install(monkeypatch, tmp_path, [entry])
    result = resolve_config_adoption(strict, anchors)
    assert result.adopted is False


# ══════════════════════════════════════════════════════════════════════
# 4. No caller-supplied authority
# ══════════════════════════════════════════════════════════════════════

def test_resolver_accepts_no_registry_path_or_authority():
    params = inspect.signature(resolve_config_adoption).parameters
    assert set(params) == {"config", "anchors"}
    for forbidden in ("registry_path", "adoption_path", "adopted", "authority",
                      "trust", "registry_sha256", "caller_digest"):
        assert forbidden not in params


def test_classifier_accepts_no_adoption_argument():
    params = inspect.signature(classify_promotion_eligibility).parameters
    assert "config_adoption" not in params
    assert "adopted" not in params


def test_no_boolean_flag_creates_adoption():
    """There is no switch: the real repository pins nothing, so nothing adopts."""
    for campaign in ("a", "b", "c"):
        assert resolve_config_adoption(
            GateConfig(config_id="x", campaign_id=campaign)).adopted is False


# ══════════════════════════════════════════════════════════════════════
# 5. Registry confers no promotion
# ══════════════════════════════════════════════════════════════════════

def test_registry_does_not_grant_promotion(monkeypatch, tmp_path):
    """Even a fully verified synthetic registry cannot reach PROMOTION_ELIGIBLE."""
    cfg = _cfg()
    _root, anchors = _install(monkeypatch, tmp_path, [_entry(cfg)])
    assert resolve_config_adoption(cfg, anchors).adopted is True
    record = EvaluationDecisionRecord.mint(**{
        "decision_id": "a1", "campaign_id": cfg.campaign_id,
        "evaluator_identity": "a" * 64, "evaluator_label": "audit",
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
    assessment = classify_promotion_eligibility(record, cfg)
    assert assessment.state != STATE_PROMOTION_ELIGIBLE


def test_every_failure_status_is_non_authoritative():
    for status in ADOPTION_FAILURE_STATUSES:
        assert status != ADOPTION_ADOPTED


# ══════════════════════════════════════════════════════════════════════
# 6. Restart safety
# ══════════════════════════════════════════════════════════════════════

def test_restart_does_not_grant_authority_without_verification(
        monkeypatch, tmp_path):
    """A fresh resolution consults the pinned bytes only, every time."""
    cfg = _cfg()
    root, anchors = _install(monkeypatch, tmp_path, [_entry(cfg)])
    assert resolve_config_adoption(cfg, anchors).adopted is True
    assert resolve_config_adoption(cfg, anchors).adopted is True
    # Remove the registry, as a fresh checkout without it would look:
    (root / anchors.adopted_config_registry_file).unlink()
    assert resolve_config_adoption(cfg, anchors).adopted is False