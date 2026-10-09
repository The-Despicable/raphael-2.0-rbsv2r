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
    ADOPTION_ADOPTED, ADOPTION_BINDING_MISMATCH, PROMOTION_REQUIREMENTS,
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


# Campaign ids must be unique per fixture registry: the adoption resolver
# allows only ONE ACTIVE adoption per campaign, and build_fixture_repo already
# registers campaign "c" for ADOPTED. Reusing "c" here would MALFORM the whole
# registry and mask the policy-identity gates under an adoption failure.
PI_ADOPTED = GateConfig(
    config_id="adopted-pi", campaign_id="pi-campaign",
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
    """Mint a record whose policy hashes match genuinely derived content.

    The record is finalized under the SAME identities admission will receive,
    so its declared gate outcomes and final state describe the verified path
    rather than the unbound one. Finalizing under () here would declare
    INDEPENDENT_HOLDOUT while a verified admission derives PROMOTION_ELIGIBLE,
    which is a record/authority contradiction, not a policy-identity defect.
    """
    import hashlib
    return _record(
        cfg,
        baseline_policy_hash=hashlib.sha256(BASELINE_BYTES).hexdigest(),
        candidate_policy_hash=hashlib.sha256(CANDIDATE_BYTES).hexdigest(),
        policy_identities=_matching_identities(),
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


def _forged_ledger_line(record) -> str:
    """Serialize a record exactly as DecisionLedger.append would."""
    return json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"


def _write_line_directly(path, record) -> None:
    """Simulate an attacker bypassing append() and writing the ledger file.

    This is the real persistence boundary: the ledger file is the durable
    artifact, and DecisionLedger.__init__ re-reads it. Anything the constructor
    accepts is what a restarted process will believe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(_forged_ledger_line(record))


# ══════════════════════════════════════════════════════════════════════════
# F. Persistence boundary: admission refusal must survive a direct file write
# ══════════════════════════════════════════════════════════════════════════
#
# A raise from append() is only half a control. The durable artifact is the
# JSONL file, and a restarted DecisionLedger re-reads it without re-running
# admission. These tests pin the two properties that make strict mode real:
#
#   F1  refused records never reach the file, even after a direct write, as
#       far as any AUTHORITATIVE reader is concerned;
#   F2  the stored claim stays readable as audit material but is excluded from
#       every re-derived authority surface.

def test_f1_refused_record_is_absent_from_the_ledger_file(pi_fixture, tmp_path):
    """append() raises AND writes nothing: no partial persistence."""
    path = tmp_path / "l.jsonl"
    record = _record(PI_ADOPTED)          # unbound -> admission must refuse
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(path).append(record, PI_ADOPTED)
    assert not path.exists()


def test_f2_direct_write_cannot_become_authority(pi_fixture, tmp_path):
    """THE bypass under test: write the refused record straight into the file.

    The reopened ledger must still surface no authoritative state for it. The
    stored claim remains readable through the explicitly audit-only accessors
    (get/historical_states), which is the honest behavior: the bytes exist, but
    they are a claim and not current authority.
    """
    path = tmp_path / "l.jsonl"
    record = _record(PI_ADOPTED)
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(path).append(record, PI_ADOPTED)

    _write_line_directly(path, record)
    assert path.exists(), "the attack must actually land, or this proves nothing"

    reopened = DecisionLedger(path)
    # Re-derived authority surfaces: both must refuse the unverified record.
    assert reopened.final_states(PI_ADOPTED) == {}
    assert reopened.current_authority(record.decision_id, PI_ADOPTED) is None

    # Audit-only surfaces may still show the bytes, and that is the point: the
    # ledger is append-only and honest about what it physically holds.
    stored = reopened.get(record.decision_id)
    assert stored is not None
    assert stored.content_hash() == record.content_hash()
    assert reopened.historical_states() == {
        record.candidate_policy_hash: record.final_state}


def test_f3_forged_promotion_claim_is_not_promoted_by_direct_write(
        pi_fixture, tmp_path):
    """A forged record claiming PROMOTION_ELIGIBLE must not gain that status.

    Exercises final_states() rather than admission's return value: this is the
    path a restarted process uses to ask "what do we currently believe?", and it
    re-derives instead of trusting the stored string.
    """
    path = tmp_path / "l.jsonl"
    forged = _record(PI_ADOPTED, final_state=STATE_PROMOTION_ELIGIBLE,
                     baseline_policy_hash="f" * 64, candidate_policy_hash="e" * 64,
                     finalize=False)
    _write_line_directly(path, forged)
    reopened = DecisionLedger(path)
    assert reopened.get("d1").final_state == STATE_PROMOTION_ELIGIBLE
    assert reopened.final_states(PI_ADOPTED) == {}
    assert reopened.current_authority("d1", PI_ADOPTED) is None


def test_f4_direct_write_cannot_suppress_a_later_honest_append(
        pi_fixture, tmp_path):
    """A planted record must not let a subsequent genuine decision slip past.

    _check_lineage reads the STORED index, so a planted record with the same
    candidate hash is the interesting case: it must not make the honest record
    admissible, nor corrupt the honest record's own authority.
    """
    path = tmp_path / "l.jsonl"
    planted = _record(PI_ADOPTED, decision_id="planted",
                      candidate_policy_hash="d" * 64, finalize=False)
    _write_line_directly(path, planted)

    honest = _record_with_real_hashes(PI_ADOPTED)
    ledger = DecisionLedger(path)
    assert ledger.final_states(PI_ADOPTED) == {}
    assert ledger.append(honest, PI_ADOPTED,
                         policy_identities=_matching_identities()) == "d1"

    # The planted record neither gains authority nor is displaced by the honest
    # one: it stays readable, unverified.
    assert ledger.get("planted") is not None
    assert ledger.current_authority("planted", PI_ADOPTED) is None


def test_f5_strict_records_are_not_re_readable_as_current_authority(
        pi_fixture, tmp_path):
    """KNOWN GAP, pinned deliberately: strict-mode records cannot be re-derived.

    :meth:`DecisionLedger.final_states` re-runs admission with NO policy
    identities, because it has no access to the policy artifacts. Under
    ``require_policy_identity=True`` that always yields BLOCKED gates, so an
    HONESTLY admitted record is excluded on re-read.

    This is fail-closed in the safe direction — a strict record never regains
    authority it cannot re-prove — but it is an over-restriction, not a
    correct answer. The remedy is to let the re-derivation be given the
    identities, which is an operator-visible API decision and is deliberately
    NOT made in this workstream. Pinned so the behaviour cannot change silently.
    """
    path = tmp_path / "l.jsonl"
    honest = _record_with_real_hashes(PI_ADOPTED)
    ledger = DecisionLedger(path)
    # Admitted and verified at append time...
    assert ledger.append(honest, PI_ADOPTED,
                         policy_identities=_matching_identities()) == "d1"
    # ...but not re-provable from stored state alone.
    assert ledger.final_states(PI_ADOPTED) == {}
    assert ledger.current_authority("d1", PI_ADOPTED) is None
    # The stored claim remains available as audit material.
    assert ledger.historical_states() == {
        honest.candidate_policy_hash: STATE_PROMOTION_ELIGIBLE}


# ══════════════════════════════════════════════════════════════════════════
# G. Mixed identity: derived baseline + asserted-only candidate
# ══════════════════════════════════════════════════════════════════════════
#
# The mixed case is the one that separates "one role verified" from "the
# binding holds". A verified baseline must not lend its authority to an
# unverified candidate.

def test_g1_mixed_identity_classifies_blocked_not_promotion_eligible(pi_fixture):
    record = _record_with_real_hashes(PI_ADOPTED)
    mixed = (
        derive_policy_identity("baseline", "baseline-policy", BASELINE_BYTES),
        asserted_policy_identity("candidate", "candidate-policy",
                                 record.candidate_policy_hash),
    )
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=mixed)
    # The derived role verifies on its own merit...
    assert assessment.gate("policy_identity_baseline") == STATUS_PASS
    # ...and the asserted echo, matching the record's own string exactly,
    # still cannot verify.
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED
    assert assessment.state == STATE_INDEPENDENT_HOLDOUT
    assert assessment.state != STATE_PROMOTION_ELIGIBLE
    assert assessment.blocked_gates() == ("policy_identity_candidate",)


def test_g2_mixed_identity_is_refused_at_admission(pi_fixture, tmp_path):
    """A verified baseline does not admit its unverified candidate."""
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    mixed = (
        derive_policy_identity("baseline", "baseline-policy", BASELINE_BYTES),
        asserted_policy_identity("candidate", "candidate-policy",
                                 record.candidate_policy_hash),
    )
    path = tmp_path / "l.jsonl"
    with pytest.raises(EvaluationGateError, match="policy_identity_candidate"):
        DecisionLedger(path).append(record, PI_ADOPTED, policy_identities=mixed)
    assert not path.exists()


def test_g3_mixed_identity_cannot_be_reintroduced_by_direct_write(
        pi_fixture, tmp_path):
    """Re-derive after the fact: the mixed binding is refused on re-read too."""
    path = tmp_path / "l.jsonl"
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    _write_line_directly(path, record)
    reopened = DecisionLedger(path)
    assert reopened.get("d1") is not None
    assert reopened.final_states(PI_ADOPTED) == {}
    assert reopened.current_authority("d1", PI_ADOPTED) is None


def test_g4_both_asserted_is_blocked_on_both_roles(pi_fixture):
    """The symmetric case, so neither role is quietly privileged."""
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    both_asserted = (
        asserted_policy_identity("baseline", "baseline-policy",
                                record.baseline_policy_hash),
        asserted_policy_identity("candidate", "candidate-policy",
                                 record.candidate_policy_hash),
    )
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=both_asserted)
    assert assessment.gate("policy_identity_baseline") == STATUS_BLOCKED
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED
    assert set(assessment.blocked_gates()) == {
        "policy_identity_baseline", "policy_identity_candidate"}


def test_g5_mixed_identity_does_not_leak_into_the_default_config(pi_fixture):
    """An asserted identity under a NON-requiring config still emits no gate.

    Confirms the strictness is scoped to the flag and does not silently become
    the experimental default.
    """
    record = _record(ADOPTED)
    asserted = (asserted_policy_identity("candidate", "candidate-policy",
                                         record.candidate_policy_hash),)
    assessment = eg.classify_promotion_eligibility(
        record, ADOPTED, policy_identities=asserted)
    assert not [g for g in assessment.gates if "policy_identity" in g[0]]


# ══════════════════════════════════════════════════════════════════════════
# H. config_digest regression: the flag is part of the committed identity
# ══════════════════════════════════════════════════════════════════════════

def test_h1_toggling_the_flag_changes_the_config_digest():
    """If the digest ignored the flag, an adopted entry could be replayed under
    the opposite enforcement mode."""
    off = GateConfig(config_id="x", campaign_id="c", require_policy_identity=False)
    on = GateConfig(config_id="x", campaign_id="c", require_policy_identity=True)
    assert off.config_digest != on.config_digest
    assert off.to_dict() != on.to_dict()


def test_h2_registry_pinned_to_the_old_digest_fails_closed(tmp_path, monkeypatch):
    """An adoption entry minted under the old digest must not bind the toggled
    config: the resolver reports a binding mismatch rather than adopting."""
    root, anchors, _ = build_fixture_repo(tmp_path)
    old = GateConfig(config_id="toggle", campaign_id="toggle-campaign",
                     min_runs_per_arm=20, require_policy_identity=False)
    new = GateConfig(config_id="toggle", campaign_id="toggle-campaign",
                     min_runs_per_arm=20, require_policy_identity=True)
    assert old.config_digest != new.config_digest

    registry = root / anchors.adopted_config_registry_file
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["entries"].append({
        "adoption_id": "toggle-entry", "campaign_id": old.campaign_id,
        "version": 1, "status": "ACTIVE",
        "config_digest": old.config_digest, "config": old.to_dict()})
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(
        eg, "AUTHORITATIVE_ANCHORS",
        replace(anchors, adopted_config_registry_sha256=_sha(registry.read_bytes())))

    # The old config still matches its own pinned entry...
    assert eg.resolve_config_adoption(old).status == ADOPTION_ADOPTED
    # ...but the toggled config does not inherit that authority.
    assert eg.resolve_config_adoption(new).status == ADOPTION_BINDING_MISMATCH


def test_h3_the_flag_is_not_a_promotion_lock_requirement():
    """PROMOTION_REQUIREMENTS must stay unchanged: adopting this flag for
    production is an operator decision, not an engineering side effect."""
    assert "require_policy_identity" not in PROMOTION_REQUIREMENTS
    # An experimental config may therefore legitimately hold the flag False.
    assert GateConfig(config_id="x", campaign_id="c").require_policy_identity is False


# ══════════════════════════════════════════════════════════════════════════
# I. The admission guard, pinned with non-vacuity
# ══════════════════════════════════════════════════════════════════════════
#
# Everything else in this file could pass while the admission guard was dead:
# classification would still report BLOCKED, and every BLOCKED-state assertion
# would still hold. Section I exists so that removing the guard is a TEST
# FAILURE, not a silent loss of enforcement.

def test_i1_blocked_policy_identity_is_the_sole_reason_for_refusal(pi_fixture):
    """Establishes the SOLO claim: nothing else about this record refuses.

    Every gate other than the two policy-identity gates is PASS, and the
    classification carries zero REFUSE gates. Admission therefore refuses on the
    policy-identity BLOCKED gates alone -- which is exactly what makes the guard
    load-bearing rather than redundant.
    """
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    assessment = eg.classify_promotion_eligibility(record, PI_ADOPTED)

    assert assessment.hard_failures() == ()
    assert assessment.blocked_gates() == ("policy_identity_baseline",
                                          "policy_identity_candidate")
    non_pass = [(n, s) for n, s in assessment.gates if s != STATUS_PASS]
    assert [n for n, _ in non_pass] == ["configuration_adoption_status",
                                        "policy_identity_baseline",
                                        "policy_identity_candidate"]
    # ADOPTED is a gate STATUS, not a failure: the config really is adopted.
    assert dict(non_pass)["configuration_adoption_status"] == ADOPTION_ADOPTED
    # The record is otherwise admissible, so only the guard can stop it.
    assert assessment.state == STATE_INDEPENDENT_HOLDOUT


def test_i2_admission_refuses_on_those_gates_alone(pi_fixture, tmp_path):
    """The refusal must name the policy-identity gates and write nothing."""
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    path = tmp_path / "l.jsonl"
    with pytest.raises(EvaluationGateError) as excinfo:
        DecisionLedger(path).append(record, PI_ADOPTED)
    message = str(excinfo.value)
    assert "refused at admission" in message
    assert "policy_identity_baseline" in message
    assert "policy_identity_candidate" in message
    assert not path.exists()


def test_i3_non_vacuity_removing_the_guard_admits_the_record(pi_fixture, tmp_path):
    """MUTATION DEMONSTRATION: neutralize policy-identity enforcement and the
    identical record is ADMITTED.

    This is what makes i1/i2 non-vacuous. A relaxed view of the very same config
    -- same config_digest, same authority chain, same record bytes -- is accepted
    by append(). The ONLY difference is that policy identity is no longer
    enforced, so if the guard were deleted, i2 would stop raising and this
    contrast would collapse. The test fails if the guard stops working.
    """
    class _RelaxedPolicyIdentityEnforcement:
        """Delegates everything to PI_ADOPTED except the flag under test.

        Frozen dataclasses cannot be mutated in place, and rebuilding the config
        would change config_digest and trip the digest gate instead, which would
        test the wrong control. Delegation isolates the single variable: same
        config_digest, same evaluator identity, same authority chain, same
        record content -- policy identity simply not enforced.
        """

        def __init__(self, config):
            self._config = config

        def __getattr__(self, name):
            if name == "require_policy_identity":
                return False
            return getattr(self._config, name)

    relaxed = _RelaxedPolicyIdentityEnforcement(PI_ADOPTED)
    # Mint the record so it is FULLY consistent with the relaxed derivation --
    # same declared policy hashes, but no policy-identity gates to satisfy.
    record = _record(relaxed, baseline_policy_hash="b" * 64,
                     candidate_policy_hash="c" * 64)

    admitted = eg.classify_promotion_eligibility(record, relaxed)
    assert not [g for g in admitted.gates if "policy_identity" in g[0]]
    assert admitted.state == STATE_PROMOTION_ELIGIBLE

    path = tmp_path / "l.jsonl"
    assert DecisionLedger(path).append(record, relaxed) == "d1"
    assert path.exists()

    # Contrast: the same record under the STRICT config is refused on the
    # policy-identity gates alone (established by i1/i2). The two branches differ
    # only in enforcement, so removing the guard collapses them.


def test_i4_the_guard_does_not_affect_the_non_strict_config(pi_fixture, tmp_path):
    """Control: the identical record under a NON-strict config is unaffected."""
    record = _record(ADOPTED)
    assert ADOPTED.require_policy_identity is False
    assert DecisionLedger(tmp_path / "l.jsonl").append(record, ADOPTED) == "d1"


# ══════════════════════════════════════════════════════════════════════════
# J. Classification semantics: BLOCKED policy identity -> INDEPENDENT_HOLDOUT
# ══════════════════════════════════════════════════════════════════════════
#
# The state ladder in _classify_with_authority is strictly ordered: REFUSE ->
# UNVERIFIABLE_INPUTS, no holdout claim -> LOCAL_REPLAY, holdout not verified ->
# UNVERIFIABLE_INPUTS, adequacy not ADEQUATE -> STATISTICALLY_INADEQUATE, ANY
# blocked gate -> INDEPENDENT_HOLDOUT, otherwise PROMOTION_ELIGIBLE. A blocked
# policy-identity gate therefore lands in the generic "open conditions" bucket.
#
# INDEPENDENT_HOLDOUT means "a verified holdout was evaluated and open
# conditions remain". It is NOT a promotion state: PROMOTION_ELIGIBLE requires
# zero blocked gates, and promotion is not implemented anywhere in src/.

def test_j1_blocked_policy_identity_yields_the_non_promotion_state(pi_fixture):
    """The BLOCKED candidate gate cannot coincide with PROMOTION_ELIGIBLE."""
    record = _record_with_real_hashes(PI_ADOPTED, finalize=False)
    mixed = (
        derive_policy_identity("baseline", "baseline-policy", BASELINE_BYTES),
        asserted_policy_identity("candidate", "candidate-policy",
                                 record.candidate_policy_hash),
    )
    assessment = eg.classify_promotion_eligibility(
        record, PI_ADOPTED, policy_identities=mixed)
    assert assessment.gate("policy_identity_candidate") == STATUS_BLOCKED
    assert assessment.state == STATE_INDEPENDENT_HOLDOUT
    assert assessment.state != STATE_PROMOTION_ELIGIBLE
    # Structural proof, not just an observed value: the ladder only returns
    # PROMOTION_ELIGIBLE on an empty blocked set.
    assert assessment.blocked_gates()
    assert "INDEPENDENT_HOLDOUT" not in (STATE_PROMOTION_ELIGIBLE,)


def test_j2_independent_holdout_cannot_be_laundered_into_promotion(pi_fixture,
                                                                  tmp_path):
    """A record claiming the weaker state cannot be admitted under a config whose
    fresh derivation is PROMOTION_ELIGIBLE."""
    verified = _record_with_real_hashes(PI_ADOPTED)
    assert verified.final_state == STATE_PROMOTION_ELIGIBLE

    # Re-mint the same record declaring the weaker state, consistently signed.
    payload = {k: v for k, v in verified.to_dict().items() if k != "content_hash"}
    downgraded = EvaluationDecisionRecord.mint(
        **{**payload, "final_state": STATE_INDEPENDENT_HOLDOUT})

    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(
            downgraded, PI_ADOPTED, policy_identities=_matching_identities())


def test_j3_no_production_consumer_treats_the_state_as_promotion():
    """INDEPENDENT_HOLDOUT has no consumer outside the gate module itself."""
    import pathlib
    src_root = pathlib.Path(eg.__file__).resolve().parents[2]   # .../src
    offenders = []
    for path in src_root.rglob("*.py"):
        if path.name == "evaluation_gate.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if STATE_INDEPENDENT_HOLDOUT in text or STATE_PROMOTION_ELIGIBLE in text:
            offenders.append(str(path.relative_to(src_root)))
    assert offenders == [], (
        f"classification states must not be consumed outside the authority "
        f"module: {offenders}")


# ══════════════════════════════════════════════════════════════════════════
# K. Campaign-scoped POLICY MANIFEST — the trusted re-derivation path
# ══════════════════════════════════════════════════════════════════════════
#
# SYNTHETIC-AUTHORITY throughout. Every manifest, artifact, adoption entry and
# repository root below lives under pytest tmp_path. Nothing here creates,
# adopts, or pins anything for a real campaign.
#
# Trust chain under test:
#   adopted-config-registry digest (pinned in the module)
#     -> entry.config.policy_manifest_{file,sha256}   (fields of config.to_dict)
#     -> manifest bytes                                (digest-verified)
#     -> artifact bytes                                (digest-verified)
#     -> PolicyIdentity(derived=True)

MANIFEST_REL = "evaluations/campaign/fixture_policy_manifest.json"
BASELINE_ARTIFACT_REL = "evaluations/campaign/fixture_policies/baseline.json"
CANDIDATE_ARTIFACT_REL = "evaluations/campaign/fixture_policies/candidate.json"
SOURCE_REVISION = "fixture-revision-0000"


def _policy_artifact_bytes(policy_id: str, order, retry_at_most) -> bytes:
    """Canonical exploration-policy artifact bytes.

    Exactly ``ExplorationPolicy.content_hash()``'s input: sorted keys, compact
    separators, ASCII, no trailing newline. Written this way so the digest of the
    committed bytes IS the policy identity, which is what lets one digest serve
    as both tamper-detection and identity without a second field.
    """
    payload = {
        "constraints": {"max_actions_per_minute": 6, "max_episode_steps": 5,
                        "objective_requires": ["ACT-D2-PROBE-0001",
                                               "ACT-D2-HTTP-0002"],
                        "target": "dvwa"},
        "created_by": "policy-identity-fixture",
        "evaluation_refs": [],
        "evidence_refs": [],
        "motivation": f"fixture {policy_id}",
        "parameters": {"order": list(order),
                       "retry": {"action": "A", "at_most": retry_at_most}},
        "parent_version": 0,
        "policy_id": policy_id,
        "schema_version": 1,
        "status": "experimental",
        "version": 1,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("utf-8")


def _manifest_payload(campaign_id, *, baseline=None, candidate=None,
                      source_revision=SOURCE_REVISION):
    """Manifest with both roles. Any argument may be overridden for an attack."""
    entries = []
    for role, spec in (("baseline", baseline), ("candidate", candidate)):
        if spec is None:
            spec = {
                "policy_id": f"{role}-policy",
                "artifact": BASELINE_ARTIFACT_REL if role == "baseline"
                            else CANDIDATE_ARTIFACT_REL,
                "sha256": "0" * 64,
                "policy_schema_version": 1,
            }
        entries.append({"role": role, **spec})
    return {"schema_version": 1, "campaign_id": campaign_id,
            "source_revision": source_revision, "policies": entries}


def _write_manifest(root, payload):
    target = root / MANIFEST_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(json.dumps(payload, sort_keys=True,
                                  separators=(",", ":")).encode("utf-8"))
    return target


def _install_adoption(root, anchors, monkeypatch, config, adoption_id="pm-adopted"):
    """Pin ``config`` as ADOPTED in the fixture registry and re-pin the anchors.

    Any pre-existing entry for the same campaign is REPLACED. The adoption
    resolver allows only one ACTIVE entry per campaign, so a second insert would
    malformed the whole registry and mask the control under test with an
    unrelated adoption failure.
    """
    registry = root / anchors.adopted_config_registry_file
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["entries"] = [e for e in payload["entries"]
                          if e["campaign_id"] != config.campaign_id]
    payload["entries"].append({
        "adoption_id": adoption_id, "campaign_id": config.campaign_id,
        "version": 1, "status": "ACTIVE",
        "config_digest": config.config_digest, "config": config.to_dict()})
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    new_anchors = replace(
        anchors, adopted_config_registry_sha256=_sha(registry.read_bytes()))
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", new_anchors)
    return new_anchors


class ManifestFixture:
    """A synthetic repo with committed artifacts, a manifest, and adoption."""

    def __init__(self, root, anchors, config, digests):
        self.root = root
        self.anchors = anchors
        self.config = config
        self.baseline_sha = digests["baseline"]
        self.candidate_sha = digests["candidate"]

    def write_artifact(self, rel, data: bytes):
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _manifest_fixture(tmp_path, monkeypatch, *, campaign_id="manifest-campaign",
                      manifest_payload=None):
    """Build the trusted chain end to end and return a ManifestFixture."""
    root, anchors, _ = build_fixture_repo(tmp_path)

    baseline_bytes = _policy_artifact_bytes("baseline-policy", ("A", "B"), 0)
    candidate_bytes = _policy_artifact_bytes("candidate-policy", ("B", "A"), 1)
    baseline_sha = _sha(baseline_bytes)
    candidate_sha = _sha(candidate_bytes)
    for rel, data in ((BASELINE_ARTIFACT_REL, baseline_bytes),
                      (CANDIDATE_ARTIFACT_REL, candidate_bytes)):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    payload = manifest_payload or _manifest_payload(
        campaign_id,
        baseline={"policy_id": "baseline-policy",
                  "artifact": BASELINE_ARTIFACT_REL,
                  "sha256": baseline_sha, "policy_schema_version": 1},
        candidate={"policy_id": "candidate-policy",
                   "artifact": CANDIDATE_ARTIFACT_REL,
                   "sha256": candidate_sha, "policy_schema_version": 1})
    manifest_path = _write_manifest(root, payload)
    manifest_sha = _sha(manifest_path.read_bytes())

    config = GateConfig(
        config_id="manifest-adopted", campaign_id=campaign_id,
        min_runs_per_arm=20, min_effect_size=0.05,
        require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=manifest_sha)
    new_anchors = _install_adoption(root, anchors, monkeypatch, config)
    return ManifestFixture(root, new_anchors, config,
                           {"baseline": baseline_sha, "candidate": candidate_sha})


def _record_for_manifest(fx, **overrides):
    """A record whose declared hashes are the pinned artifact digests."""
    return _record(
        fx.config, baseline_policy_hash=fx.baseline_sha,
        candidate_policy_hash=fx.candidate_sha, **overrides)


def _record_for_manifest_finalized(fx, **overrides):
    """Same, finalized under the TRUSTED resolution (no caller identities)."""
    authority = eg.build_authority(fx.config, runs_candidate=40,
                                   runs_baseline=40, exclusions=0, effect=0.2)
    record = _record(fx.config, baseline_policy_hash=fx.baseline_sha,
                     candidate_policy_hash=fx.candidate_sha, finalize=False,
                     **overrides)
    derived = eg._classify_with_authority(record, fx.config, authority,
                                          policy_identities=eg.resolve_policy_identities(
                                              fx.config).identities)
    payload = {k: v for k, v in record.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [list(g) for g in derived.gates]
    payload["final_state"] = derived.state
    payload["inputs_digest"] = eg.derive_evaluation_inputs_digest(record, authority)
    return EvaluationDecisionRecord.mint(**payload)


# ── K1. the resolver verifies the whole chain ────────────────────────────

def test_k1_resolver_verifies_manifest_and_artifacts(tmp_path, monkeypatch):
    fx = _manifest_fixture(tmp_path, monkeypatch)
    resolution = eg.resolve_policy_identities(fx.config)
    assert resolution.status == eg.POLICY_MANIFEST_VERIFIED
    assert resolution.campaign_id == "manifest-campaign"
    assert resolution.source_revision == SOURCE_REVISION
    assert {i.role: i.content_sha256 for i in resolution.identities} == {
        "baseline": fx.baseline_sha, "candidate": fx.candidate_sha}
    assert all(i.derived for i in resolution.identities)
    assert resolution.artifact_digests == {"baseline": fx.baseline_sha,
                                           "candidate": fx.candidate_sha}


def test_k2_resolver_takes_no_record_and_no_caller_identity(tmp_path, monkeypatch):
    """The trusted path cannot be aimed at a record or an asserted identity."""
    import inspect
    params = inspect.signature(eg.resolve_policy_identities).parameters
    assert set(params) == {"config", "anchors"}
    for forbidden in ("record", "ledger", "policy_identities", "digest",
                      "expected_sha256", "artifact", "policy_hash"):
        assert forbidden not in params


# ── K2. fail-closed matrix ───────────────────────────────────────────────

def test_k3_tampered_artifact_bytes_fail_closed(tmp_path, monkeypatch):
    fx = _manifest_fixture(tmp_path, monkeypatch)
    assert eg.resolve_policy_identities(fx.config).verified
    fx.write_artifact(CANDIDATE_ARTIFACT_REL,
                      _policy_artifact_bytes("candidate-policy", ("A", "B"), 0))
    resolution = eg.resolve_policy_identities(fx.config)
    assert resolution.status == eg.POLICY_ARTIFACT_TAMPERED
    assert resolution.identities == ()


def test_k4_tampered_baseline_artifact_also_fails_closed(tmp_path, monkeypatch):
    fx = _manifest_fixture(tmp_path, monkeypatch)
    fx.write_artifact(BASELINE_ARTIFACT_REL, b'{"policy_id":"evil"}')
    assert eg.resolve_policy_identities(fx.config).status == eg.POLICY_ARTIFACT_TAMPERED


def test_k5_changed_manifest_digest_fails_closed(tmp_path, monkeypatch):
    """Editing the manifest breaks the digest the adopted config pins."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    payload = json.loads((fx.root / MANIFEST_REL).read_text(encoding="utf-8"))
    payload["source_revision"] = "tampered-revision"
    _write_manifest(fx.root, payload)
    resolution = eg.resolve_policy_identities(fx.config)
    assert resolution.status == eg.POLICY_MANIFEST_TAMPERED
    assert resolution.identities == ()


def test_k6_wrong_campaign_fails_closed(tmp_path, monkeypatch):
    """A well-formed manifest pinned for another campaign is not evidence here."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    payload = json.loads((fx.root / MANIFEST_REL).read_text(encoding="utf-8"))
    payload["campaign_id"] = "some-other-campaign"
    _write_manifest(fx.root, payload)
    resolution = eg.resolve_policy_identities(fx.config)
    assert resolution.status == eg.POLICY_MANIFEST_TAMPERED   # digest first


def test_k7_campaign_mismatch_is_reported_when_the_digest_also_pins_it(
        tmp_path, monkeypatch):
    """The campaign check is a real control, not dead code behind the digest.

    A well-formed manifest pinned for campaign Y, attached to an ADOPTED config
    for campaign X, with a matching manifest digest. Nothing is tampered here, so
    the campaign binding is the only thing that can refuse it.
    """
    root, anchors, _ = build_fixture_repo(tmp_path)
    baseline_bytes = _policy_artifact_bytes("baseline-policy", ("A", "B"), 0)
    candidate_bytes = _policy_artifact_bytes("candidate-policy", ("B", "A"), 1)
    for rel, data in ((BASELINE_ARTIFACT_REL, baseline_bytes),
                      (CANDIDATE_ARTIFACT_REL, candidate_bytes)):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    payload = _manifest_payload(
        "campaign-FOREIGN",
        baseline={"policy_id": "baseline-policy",
                  "artifact": BASELINE_ARTIFACT_REL,
                  "sha256": _sha(baseline_bytes), "policy_schema_version": 1},
        candidate={"policy_id": "candidate-policy",
                   "artifact": CANDIDATE_ARTIFACT_REL,
                   "sha256": _sha(candidate_bytes), "policy_schema_version": 1})
    manifest_path = _write_manifest(root, payload)

    config = GateConfig(
        config_id="cross-campaign", campaign_id="campaign-DOMESTIC",
        min_runs_per_arm=20, require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(root, anchors, monkeypatch, config, "pm-cross")

    resolution = eg.resolve_policy_identities(config)
    assert resolution.status == eg.POLICY_MANIFEST_CAMPAIGN_MISMATCH
    assert resolution.identities == ()


def test_k8_swapped_baseline_and_candidate_roles_fail_closed(tmp_path, monkeypatch):
    """Roles swapped in the manifest must not verify a record.

    The bytes are the correct artifacts; only the labels moved. Under the honest
    manifest the baseline and candidate digests differ, so a swap makes each
    derived identity contradict the record's declared hash -> REFUSE.
    """
    fx = _manifest_fixture(tmp_path, monkeypatch)
    honest = {i.role: i.content_sha256
              for i in eg.resolve_policy_identities(fx.config).identities}
    assert honest["baseline"] != honest["candidate"]

    payload = json.loads((fx.root / MANIFEST_REL).read_text(encoding="utf-8"))
    by_role = {e["role"]: e for e in payload["policies"]}
    # Swap the CONTENT fields while each entry keeps its own role label --
    # swapping whole entries would swap the "role" value too and silently
    # reproduce the honest manifest.
    for field in ("policy_id", "artifact", "sha256"):
        by_role["baseline"][field], by_role["candidate"][field] = (
            by_role["candidate"][field], by_role["baseline"][field])
    manifest_path = _write_manifest(fx.root, payload)
    swapped = GateConfig(
        config_id=fx.config.config_id, campaign_id=fx.config.campaign_id,
        min_runs_per_arm=20, min_effect_size=0.05, require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(fx.root, fx.anchors, monkeypatch, swapped, "pm-swapped")

    resolution = eg.resolve_policy_identities(swapped)
    assert resolution.verified              # bytes are genuine...
    assert {i.role: i.content_sha256 for i in resolution.identities} == {
        "baseline": honest["candidate"],    # ...but each role names the other's
        "candidate": honest["baseline"],    #    artifact
    }

    # Against a record declaring the honest roles, the swap is a REFUSE.
    record = _record(fx.config, baseline_policy_hash=fx.baseline_sha,
                     candidate_policy_hash=fx.candidate_sha, finalize=False)
    assessment = eg.classify_promotion_eligibility(record, swapped)
    assert assessment.gate("policy_identity_baseline") == STATUS_REFUSE
    assert assessment.gate("policy_identity_candidate") == STATUS_REFUSE
    assert assessment.state != STATE_PROMOTION_ELIGIBLE


def test_k9_missing_artifact_fails_closed(tmp_path, monkeypatch):
    fx = _manifest_fixture(tmp_path, monkeypatch)
    (fx.root / CANDIDATE_ARTIFACT_REL).unlink()
    resolution = eg.resolve_policy_identities(fx.config)
    assert resolution.status == eg.POLICY_ARTIFACT_ABSENT
    assert resolution.identities == ()


def test_k10_missing_manifest_fails_closed(tmp_path, monkeypatch):
    fx = _manifest_fixture(tmp_path, monkeypatch)
    (fx.root / MANIFEST_REL).unlink()
    assert eg.resolve_policy_identities(fx.config).status == eg.POLICY_MANIFEST_ABSENT


def test_k11_unadopted_config_cannot_read_a_manifest(tmp_path, monkeypatch):
    """THE gate. A manifest pinned only by a NON-adopted config is not trusted.

    Without this check the 'binding' would be a caller-chosen string and the
    whole path would be a trust-laundering mechanism.
    """
    fx = _manifest_fixture(tmp_path, monkeypatch)
    orphan = GateConfig(
        config_id="not-adopted", campaign_id=fx.config.campaign_id,
        min_runs_per_arm=20, min_effect_size=0.05, require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=fx.config.policy_manifest_sha256)
    resolution = eg.resolve_policy_identities(orphan)
    assert resolution.status == eg.POLICY_MANIFEST_CONFIG_NOT_ADOPTED
    assert resolution.identities == ()


def test_k12_config_without_a_manifest_binding_is_unpinned(tmp_path, monkeypatch):
    """PI_ADOPTED pins no manifest, so it stays BLOCKED however it is asked."""
    assert eg.resolve_policy_identities(PI_ADOPTED).status == eg.POLICY_MANIFEST_UNPINNED


def test_k13_malformed_manifests_fail_closed(tmp_path, monkeypatch):
    cases = {
        "not_an_object": ["nope"],
        "extra_key": {**_manifest_payload("c"), "surprise": 1},
        "missing_key": {k: v for k, v in _manifest_payload("c").items()
                        if k != "source_revision"},
        "bad_schema_version": {**_manifest_payload("c"), "schema_version": 2},
        "empty_policies": {**_manifest_payload("c"), "policies": []},
        "blank_revision": {**_manifest_payload("c"), "source_revision": "  "},
    }
    for label, payload in cases.items():
        root, anchors, _ = build_fixture_repo(tmp_path / label)
        manifest_path = _write_manifest(root, payload)
        config = GateConfig(
            config_id="m", campaign_id="c", require_policy_identity=True,
            policy_manifest_file=MANIFEST_REL,
            policy_manifest_sha256=_sha(manifest_path.read_bytes()))
        _install_adoption(root, anchors, monkeypatch, config, f"pm-{label}")
        resolution = eg.resolve_policy_identities(config)
        assert resolution.status in eg.POLICY_MANIFEST_FAILURE_STATUSES, label
        assert resolution.identities == (), label


def test_k14_duplicate_or_missing_role_fails_closed(tmp_path, monkeypatch):
    payload = _manifest_payload("c")
    payload["policies"] = [payload["policies"][0], payload["policies"][0]]
    root, anchors, _ = build_fixture_repo(tmp_path / "dup")
    manifest_path = _write_manifest(root, payload)
    config = GateConfig(
        config_id="m", campaign_id="c", require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(root, anchors, monkeypatch, config, "pm-dup")
    assert eg.resolve_policy_identities(config).status == eg.POLICY_MANIFEST_ROLE_INVALID

    payload = _manifest_payload("c")
    payload["policies"] = [p for p in payload["policies"] if p["role"] != "candidate"]
    root, anchors, _ = build_fixture_repo(tmp_path / "missing")
    manifest_path = _write_manifest(root, payload)
    config = GateConfig(
        config_id="m", campaign_id="c", require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(root, anchors, monkeypatch, config, "pm-missing")
    assert eg.resolve_policy_identities(config).status == eg.POLICY_MANIFEST_ROLE_INVALID


def test_k15_artifact_path_escape_is_refused(tmp_path, monkeypatch):
    root, anchors, _ = build_fixture_repo(tmp_path)
    manifest_path = _write_manifest(root, _manifest_payload(
        "c", baseline={"policy_id": "baseline-policy",
                       "artifact": "../../../etc/passwd",
                       "sha256": "a" * 64, "policy_schema_version": 1}))
    config = GateConfig(
        config_id="m", campaign_id="c", require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(root, anchors, monkeypatch, config, "pm-escape")
    resolution = eg.resolve_policy_identities(config)
    assert resolution.status == eg.POLICY_ARTIFACT_UNPARSABLE
    assert resolution.identities == ()


def test_k16_artifact_that_lies_about_itself_is_refused(tmp_path, monkeypatch):
    """Well-formed bytes whose declared content_hash is not their own digest."""
    payload = _manifest_payload("c")
    bad = json.loads(_policy_artifact_bytes("baseline-policy", ("A", "B"), 0))
    bad["content_hash"] = "b" * 64
    root, anchors, _ = build_fixture_repo(tmp_path)
    (root / BASELINE_ARTIFACT_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / BASELINE_ARTIFACT_REL).write_bytes(
        json.dumps(bad, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    digest = _sha((root / BASELINE_ARTIFACT_REL).read_bytes())
    manifest_path = _write_manifest(root, _manifest_payload(
        "c", baseline={"policy_id": "baseline-policy",
                       "artifact": BASELINE_ARTIFACT_REL, "sha256": digest,
                       "policy_schema_version": 1}))
    config = GateConfig(
        config_id="m", campaign_id="c", require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=_sha(manifest_path.read_bytes()))
    _install_adoption(root, anchors, monkeypatch, config, "pm-selflie")
    assert eg.resolve_policy_identities(config).status == eg.POLICY_ARTIFACT_UNPARSABLE


# ── K3. caller input cannot launder authority through the trusted path ────

def test_k17_asserted_identity_cannot_satisfy_a_bound_config(tmp_path, monkeypatch):
    """An asserted echo is ignored when a trusted manifest is available.

    The record declares the real artifact digests, so it verifies -- but only
    because the artifacts were independently read, not because the caller
    asserted the right strings. The control for this is k20: with no manifest the
    very same asserted strings stay BLOCKED.
    """
    fx = _manifest_fixture(tmp_path, monkeypatch)
    record = _record_for_manifest(fx, finalize=False)
    asserted = (
        asserted_policy_identity("baseline", "baseline-policy", fx.baseline_sha),
        asserted_policy_identity("candidate", "candidate-policy", fx.candidate_sha),
    )
    assessment = eg.classify_promotion_eligibility(
        record, fx.config, policy_identities=asserted)
    assert assessment.gate("policy_identity_baseline") == STATUS_PASS
    assert assessment.gate("policy_identity_candidate") == STATUS_PASS


def test_k18_caller_identity_contradicting_the_artifact_is_refused(
        tmp_path, monkeypatch):
    """A caller derivation that disagrees with trusted bytes is a contradiction."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    record = _record(fx.config, finalize=False)
    rogue = (derive_policy_identity("candidate", "candidate-policy", b"rogue"),)
    with pytest.raises(EvaluationGateError, match="contradicts the digest"):
        DecisionLedger(tmp_path / "l.jsonl").append(record, fx.config,
                                                    policy_identities=rogue)
    assert not (tmp_path / "l.jsonl").exists()


def test_k19_caller_identity_matching_the_artifact_is_accepted(
        tmp_path, monkeypatch):
    """Agreement is not a conflict: the honest caller path still works."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    record = _record_for_manifest_finalized(fx)
    honest = (derive_policy_identity("candidate", "candidate-policy",
                                     (fx.root / CANDIDATE_ARTIFACT_REL).read_bytes()),)
    assert DecisionLedger(tmp_path / "l.jsonl").append(
        record, fx.config, policy_identities=honest) == "d1"


def test_k20_unbound_config_still_refuses_asserted_identity(pi_fixture, tmp_path):
    """With no manifest the asserted path is BLOCKED, exactly as before."""
    record = _record(PI_ADOPTED)
    asserted = (
        asserted_policy_identity("baseline", "b", "b" * 64),
        asserted_policy_identity("candidate", "c", "c" * 64),
    )
    with pytest.raises(EvaluationGateError, match="policy_identity"):
        DecisionLedger(tmp_path / "l.jsonl").append(record, PI_ADOPTED,
                                                    policy_identities=asserted)


# ── K4. strict-mode re-read after restart — the POSITIVE path ────────────

def test_k21_honest_record_regains_authority_after_restart(tmp_path, monkeypatch):
    """THE positive proof required by the operator ruling.

    Admit honestly, drop every in-memory object, reopen the ledger from disk, and
    ask for current authority with NO caller input at all. The record is readable
    again because the policy identities were re-derived from digest-verified
    artifacts named by the adopted config.
    """
    fx = _manifest_fixture(tmp_path, monkeypatch)
    path = tmp_path / "l.jsonl"
    record = _record_for_manifest_finalized(fx)
    assert record.final_state == STATE_PROMOTION_ELIGIBLE
    DecisionLedger(path).append(record, fx.config)     # no policy_identities

    # "Restart": a brand new ledger object reading only the file.
    restarted = DecisionLedger(path)
    assert restarted.get("d1") is not None
    assert restarted.final_states(fx.config) == {
        record.candidate_policy_hash: STATE_PROMOTION_ELIGIBLE}
    assessment = restarted.current_authority("d1", fx.config)
    assert assessment is not None
    assert assessment.state == STATE_PROMOTION_ELIGIBLE
    assert assessment.gate("policy_identity_baseline") == STATUS_PASS
    assert assessment.gate("policy_identity_candidate") == STATUS_PASS


def test_k22_re_read_fails_closed_once_the_artifact_is_tampered(tmp_path, monkeypatch):
    """The positive path is not a permanent grant: break the bytes, lose authority."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    path = tmp_path / "l.jsonl"
    record = _record_for_manifest_finalized(fx)
    DecisionLedger(path).append(record, fx.config)
    assert DecisionLedger(path).final_states(fx.config) != {}

    fx.write_artifact(CANDIDATE_ARTIFACT_REL,
                      _policy_artifact_bytes("candidate-policy", ("A", "B"), 0))
    assert DecisionLedger(path).final_states(fx.config) == {}
    assert DecisionLedger(path).current_authority("d1", fx.config) is None


def test_k23_re_read_fails_closed_once_adoption_is_withdrawn(tmp_path, monkeypatch):
    """Authority flows THROUGH adoption, so withdrawing adoption removes it."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    path = tmp_path / "l.jsonl"
    record = _record_for_manifest_finalized(fx)
    DecisionLedger(path).append(record, fx.config)
    assert DecisionLedger(path).final_states(fx.config) != {}

    registry = fx.root / fx.anchors.adopted_config_registry_file
    payload = json.loads(registry.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        if entry["campaign_id"] == fx.config.campaign_id:
            entry["status"] = "REVOKED"
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(
        eg, "AUTHORITATIVE_ANCHORS",
        replace(fx.anchors,
                adopted_config_registry_sha256=_sha(registry.read_bytes())))
    assert DecisionLedger(path).final_states(fx.config) == {}


def test_k24_direct_injected_record_still_cannot_beat_the_manifest(
        tmp_path, monkeypatch):
    """Injection does not get better because a manifest now exists."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    path = tmp_path / "l.jsonl"
    DecisionLedger(path).append(_record_for_manifest_finalized(fx), fx.config)

    forged = _record(fx.config, decision_id="forged",
                     candidate_policy_hash="e" * 64, finalize=False)
    _write_line_directly(path, forged)
    restarted = DecisionLedger(path)
    assert restarted.get("forged") is not None
    assert restarted.final_states(fx.config) == {
        fx.candidate_sha: STATE_PROMOTION_ELIGIBLE}
    assert "e" * 64 not in restarted.final_states(fx.config)


def test_k25_manifest_binding_is_part_of_the_config_digest(tmp_path, monkeypatch):
    """Adoption pins the manifest binding transitively, via config_digest."""
    fx = _manifest_fixture(tmp_path, monkeypatch)
    unbound = GateConfig(config_id=fx.config.config_id,
                         campaign_id=fx.config.campaign_id,
                         min_runs_per_arm=20, min_effect_size=0.05,
                         require_policy_identity=True)
    rebound = GateConfig(
        config_id=fx.config.config_id, campaign_id=fx.config.campaign_id,
        min_runs_per_arm=20, min_effect_size=0.05, require_policy_identity=True,
        policy_manifest_file=MANIFEST_REL,
        policy_manifest_sha256=fx.config.policy_manifest_sha256)
    assert unbound.config_digest != rebound.config_digest
    assert rebound.to_dict()["policy_manifest_file"] == MANIFEST_REL
    assert rebound.to_dict()["policy_manifest_sha256"] == \
        fx.config.policy_manifest_sha256
    # The adopted entry therefore commits to the manifest binding.
    assert eg.resolve_config_adoption(rebound).adopted
    assert eg.resolve_config_adoption(unbound).status != ADOPTION_ADOPTED


def test_k26_anchor_set_has_no_policy_anchor():
    """Operator ruling: no per-campaign policies in AnchorSet."""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(eg.AnchorSet)}
    assert not [f for f in fields if "policy" in f]
    # and the binding is reached only through adoption
    assert eg.resolve_policy_identities(
        GateConfig(config_id="x", campaign_id="c")).status == \
        eg.POLICY_MANIFEST_UNPINNED


def test_k27_partial_manifest_binding_is_refused():
    for file_value, digest_value in ((MANIFEST_REL, ""), ("", "a" * 64)):
        with pytest.raises(EvaluationGateError, match="set together"):
            GateConfig(config_id="x", campaign_id="c",
                       policy_manifest_file=file_value,
                       policy_manifest_sha256=digest_value)
    with pytest.raises(EvaluationGateError, match="64-char lowercase hex"):
        GateConfig(config_id="x", campaign_id="c", policy_manifest_file=MANIFEST_REL,
                   policy_manifest_sha256="nope")


def test_k28_defaults_unchanged():
    """require_policy_identity stays False, empty manifest binding, no promotion lock."""
    cfg = GateConfig(config_id="x", campaign_id="c")
    assert cfg.require_policy_identity is False
    assert cfg.policy_manifest_file == ""
    assert cfg.policy_manifest_sha256 == ""
    assert "require_policy_identity" not in PROMOTION_REQUIREMENTS
    assert "policy_manifest_file" not in PROMOTION_REQUIREMENTS
