"""Adversarial regression tests for the RSI-1 POLICY IDENTITY binding.

C1/C2 finding: ``EvaluationDecisionRecord.baseline_policy_hash`` and
``candidate_policy_hash`` were caller-supplied strings with no binding to the
loaded policy artifact. The remediation (evaluation_gate section 2c) hashes
artifact CONTENT inside the authority module and compares the derived digest
against the record:

  * a derived-vs-declared MISMATCH refuses unconditionally (fabrication);
  * with ``require_policy_identity=True`` an asserted-only or missing binding
    is BLOCKED and can never reach PROMOTION_ELIGIBLE;
  * with the flag False (experimental default) the historical behavior is
    preserved unchanged;
  * no function accepts a caller-computed digest as authority.

Every test here is an attack or a proof; the fixture repository is entirely
synthetic (tmp_path). No real holdout is fabricated or used.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from orchestrator.rsi import evaluation_gate as eg
from orchestrator.rsi.evaluation_gate import (
    DecisionLedger, EvaluationGateError, EvaluationDecisionRecord,
    EvaluatorIdentity, GateConfig, PolicyIdentity, STATE_INDEPENDENT_HOLDOUT,
    STATE_PROMOTION_ELIGIBLE, STATUS_BLOCKED, STATUS_PASS, STATUS_REFUSE,
    asserted_policy_identity, derive_policy_identity, verify_policy_identity,
)

# Reuse the synthetic authority-chain fixture from the measurement-integrity
# suite: same trust model, one fixture definition.
from test_rsi1_measurement_integrity import (   # noqa: E402
    ADOPTED, _record, _sha, build_fixture_repo,
)


PI_ADOPTED = GateConfig(
    config_id="adopted-pi", campaign_id="c",
    min_runs_per_arm=20, min_effect_size=0.05,
    require_policy_identity=True)

CANDIDATE_BYTES = b"exploration-policy-v0 canonical json content: candidate"
BASELINE_BYTES = b"exploration-policy-v0 canonical json content: baseline"


@pytest.fixture
def pi_fixture(tmp_path, monkeypatch):
    """The standard fixture, plus PI_ADOPTED pinned into the adopted registry."""
    root, anchors, _ = build_fixture_repo(tmp_path)
    registry = root / anchors.adopted_config_registry_file
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["entries"].append({
        "adoption_id": "fixture-adopted-pi",
        "campaign_id": PI_ADOPTED.campaign_id, "version": 1,
        "status": "ACTIVE", "config_digest": PI_ADOPTED.config_digest,
        "config": PI_ADOPTED.to_dict()})
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    new_anchors = replace(
        anchors, adopted_config_registry_sha256=_sha(registry.read_bytes()))
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", new_anchors)
    return root, new_anchors


def _matching_identities():
    """Identities derived from the SAME content the fixture record declares."""
    return (
        derive_policy_identity("baseline", "baseline-policy", BASELINE_BYTES),
        derive_policy_identity("candidate", "candidate-policy", CANDIDATE_BYTES),
    )


def _record_with_real_hashes(cfg, **overrides):
    """Mint a record whose policy hashes match genuinely derived content."""
    import hashlib
    return _record(
        cfg,
        baseline_policy_hash=hashlib.sha256(BASELINE_BYTES).hexdigest(),
        candidate_policy_hash=hashlib.sha256(CANDIDATE_BYTES).hexdigest(),
        **overrides)


# ══════════════════════════════════════════════════════════════════════════
# A. Mechanism construction: content is hashed HERE, never accepted as a digest
# ══════════════════════════════════════════════════════════════════════════

def test_a1_derive_hashes_actual_bytes():
    import hashlib
    ident = derive_policy_identity("candidate", "p", b"content-bytes")
    assert ident.content_sha256 == hashlib.sha256(b"content-bytes").hexdigest()
    assert ident.derived is True


def test_a2_derive_refuses_non_bytes_content():
    for not_bytes in ("hex-string", None, 42, {"k": "v"}, [1, 2]):
        with pytest.raises(EvaluationGateError, match="must be bytes"):
            derive_policy_identity("candidate", "p", not_bytes)


def test_a3_derive_takes_no_digest_parameter():
    """The whole point: no function accepts a caller-computed digest."""
    import inspect
    assert "digest" not in inspect.signature(derive_policy_identity).parameters
    assert "sha256" not in inspect.signature(derive_policy_identity).parameters
    assert "hash" not in inspect.signature(derive_policy_identity).parameters


def test_a4_asserted_identity_requires_hex_sha256():
    with pytest.raises(EvaluationGateError, match="64-char lowercase hex"):
        asserted_policy_identity("candidate", "p", "validation")
    with pytest.raises(EvaluationGateError, match="64-char lowercase hex"):
        asserted_policy_identity("candidate", "p", "c" * 63)


def test_a5_identity_field_validation():
    with pytest.raises(EvaluationGateError, match="role"):
        PolicyIdentity(role="student", policy_id="p", content_sha256="a" * 64)
    with pytest.raises(EvaluationGateError, match="hex"):
        PolicyIdentity(role="candidate", policy_id="p", content_sha256="zz")
    with pytest.raises(EvaluationGateError, match="policy_id"):
        PolicyIdentity(role="candidate", policy_id="", content_sha256="a" * 64)
    with pytest.raises(EvaluationGateError, match="bool"):
        PolicyIdentity(role="candidate", policy_id="p", content_sha256="a" * 64,
                       derived=1)


def test_a6_duplicate_roles_are_ambiguous_and_refused():
    dup = (derive_policy_identity("candidate", "p1", b"one"),
           derive_policy_identity("candidate", "p2", b"two"))
    record = _record(ADOPTED)
    with pytest.raises(EvaluationGateError, match="duplicate policy identity"):
        verify_policy_identity(record, dup)


# ══════════════════════════════════════════════════════════════════════════
# B. Flag False (experimental default): historical behavior, but contradictions
#    still refuse
# ══════════════════════════════════════════════════════════════════════════

def test_b1_no_binding_no_gate_when_not_required(pi_fixture):
    """Records classified without identities carry no policy_identity gates:
    the asserted-hash status quo is preserved for experimental use."""
    record = _record(ADOPTED)
    assessment = eg.classify_promotion_eligibility(record, ADOPTED)
    assert not [g for g in assessment.gates if "policy_identity" in g[0]]


def test_b2_derived_mismatch_refuses_even_when_not_required(pi_fixture):
    """THE fabrication attack: the record declares hash H for the candidate;
    the artifact supplied for verification hashes to something else. Refused
    UNCONDITIONALLY — a contradiction is not a missing control."""
    record = _record(ADOPTED)   # declares "c" * 64 as candidate hash
    forged = derive_policy_identity("candidate", "impostor", b"other content")
    assessment = eg.classify_promotion_eligibility(
        record, ADOPTED, policy_identities=(forged,))
    assert assessment.gate("policy_identity_candidate") == STATUS_REFUSE
    assert assessment.state != STATE_PROMOTION_ELIGIBLE
    assert assessment.hard_failures()


def test_b3_baseline_mismatch_refuses_even_when_not_required(pi_fixture):
    record = _record(ADOPTED)
    forged = derive_policy_identity("baseline", "impostor", b"other baseline")
    assessment = eg.classify_promotion_eligibility(
        record, ADOPTED, policy_identities=(forged,))
    assert assessment.gate("policy_identity_baseline") == STATUS_REFUSE


def test_b4_matching_binding_passes_even_when_not_required(pi_fixture):
    record = _record_with_real_hashes(ADOPTED)
    assessment = eg.classify_promotion_eligibility(
        record, ADOPTED, policy_identities=_matching_identities())
    assert assessment.gate("policy_identity_candidate") == STATUS_PASS
    assert assessment.gate("policy_identity_baseline") == STATUS_PASS


# ══════════════════════════════════════════════════════════════════════════
# C. Flag True (require_binding): asserted-only and missing bindings are BLOCKED
# ══════════════════════════════════════════════════════════════════════════

def test_c1_unbound_record_cannot_reach_promotion_eligible(pi_fixture):
    """The C1/C2 gap, closed at the gate: a record whose policy hashes are
    pure assertions is BLOCKED below PROMOTION_ELIGIBLE when the adopted
    config requires the binding — everything else about it is honest."""
    record = _record(PI_ADOPTED)     # full honest fixture, hashes unbound
    assessment = eg.classify_promotion_eligibility(record, PI_ADOPTED)
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED
    assert assessment.gate("policy_identity_baseline") == STATUS_BLOCKED
    assert assessment.state == STATE_INDEPENDENT_HOLDOUT
    assert assessment.state != STATE_PROMOTION_ELIGIBLE


def test_c2_verified_binding_restores_full_classification(pi_fixture):
    """The honest path: record hashes match content-derived identities and the
    classification returns to exactly what an unbound-but-honest record gets."""
    record = _record_with_real_hashes(PI_ADOPTED)
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=_matching_identities())
    assert assessment.gate("policy_identity_candidate") == STATUS_PASS
    assert assessment.gate("policy_identity_baseline") == STATUS_PASS
    assert assessment.state == STATE_PROMOTION_ELIGIBLE


def test_c3_asserted_identity_can_never_verify(pi_fixture):
    """asserted_policy_identity() exists to RECORD the non-authoritative mode,
    never to satisfy the gate."""
    record = _record(PI_ADOPTED)
    asserted = (
        asserted_policy_identity("baseline", "b", "b" * 64),
        asserted_policy_identity("candidate", "c", "c" * 64),
    )
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=asserted)
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED
    assert assessment.state != STATE_PROMOTION_ELIGIBLE


def test_c4_missing_record_hash_is_blocked_not_imputed(pi_fixture):
    record = _record(PI_ADOPTED, candidate_policy_hash="")
    assessment = eg.classify_promotion_eligibility(record, PI_ADOPTED)
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED


def test_c5_mismatched_binding_cannot_be_smuggled_past_the_flag(pi_fixture):
    """A wrong-artifact binding under a requiring config still REFUSES (the
    unconditional contradiction rule), not merely blocks."""
    record = _record(PI_ADOPTED)
    wrong = (derive_policy_identity("candidate", "p", b"wrong"),)
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=wrong)
    assert assessment.gate("policy_identity_candidate") == STATUS_REFUSE


# ══════════════════════════════════════════════════════════════════════════
# D. Ledger admission enforces the binding
# ══════════════════════════════════════════════════════════════════════════

def test_d1_ledger_accepts_verified_binding(pi_fixture, tmp_path):
    record = _record_with_real_hashes(PI_ADOPTED)
    ledger = DecisionLedger(tmp_path / "l.jsonl")
    assert ledger.append(record, PI_ADOPTED,
                         policy_identities=_matching_identities()) == record.decision_id


def test_d2_ledger_refuses_unbound_record_when_required(pi_fixture, tmp_path):
    record = _record(PI_ADOPTED)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(record, PI_ADOPTED)


def test_d3_ledger_refuses_forged_binding(pi_fixture, tmp_path):
    record = _record(ADOPTED)
    forged = (derive_policy_identity("candidate", "impostor", b"nope"),)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(
            record, ADOPTED, policy_identities=forged)


def test_d4_ledger_without_identities_still_accepts_legacy_config(
        pi_fixture, tmp_path):
    """Config does not require the binding -> append behavior unchanged."""
    record = _record(ADOPTED)
    DecisionLedger(tmp_path / "l.jsonl").append(record, ADOPTED)


# ══════════════════════════════════════════════════════════════════════════
# E. Adopted configurations must not disable the requirement silently
# ══════════════════════════════════════════════════════════════════════════

def test_e1_require_policy_identity_is_a_strict_bool():
    with pytest.raises(EvaluationGateError, match="require_policy_identity"):
        GateConfig(config_id="x", campaign_id="c", require_policy_identity=1)


def test_e2_adopted_registry_entry_carries_the_flag():
    """The pinned registry payload embeds config.to_dict(), so an adopted
    config's require_policy_identity value is part of what the digest pins."""
    cfg = GateConfig(config_id="x", campaign_id="c", require_policy_identity=True)
    assert cfg.to_dict()["require_policy_identity"] is True
    assert ADOPTED.to_dict()["require_policy_identity"] is False
