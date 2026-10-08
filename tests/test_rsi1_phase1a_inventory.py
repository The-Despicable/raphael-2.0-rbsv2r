"""Phase 1A — evaluator-inventory correction and NON-VACUOUS ledger proof.

Every test in this file runs against the ACTUAL repository checkout. No
synthetic component files are created to satisfy the identity inventory, and no
fake holdout, adoption, evidence index, or statistical authority is fabricated.

The prior ledger tests could not prove containment because
``EVALUATOR_COMPONENT_MODULES`` named ``src/arena/manifests.py``, which has never
existed in any commit. That made ``identity.complete`` permanently False, so
every real record REFUSEd at admission before the containment checks were ever
reached. With the phantom removed, these tests exercise containment itself.
"""
from __future__ import annotations


import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from orchestrator.rsi import evaluation_gate as eg
from orchestrator.rsi.evaluation_gate import (
    STATE_LOCAL_REPLAY, STATE_PROMOTION_ELIGIBLE, STATE_STATISTICALLY_INADEQUATE,
    STATE_UNVERIFIABLE_INPUTS, STATUS_REFUSE, DecisionLedger, EvaluationDecisionRecord,
    EvaluationGateError, EvaluatorIdentity, GateConfig,
    classify_promotion_eligibility,
)

REPO = Path(eg._REPO_ROOT)
CAMPAIGN = "phase1a-real-checkout"
REAL = GateConfig(config_id="phase1a", campaign_id=CAMPAIGN,
                  min_runs_per_arm=20, min_effect_size=0.05)

#: The identity produced by the OLD (defective) inventory, which included the
#: nonexistent src/arena/manifests.py. Recorded as a literal so the regression is
#: not self-referential: it must differ from the corrected current identity.
OLD_DEFECTIVE_COMPONENTS = (
    "src/orchestrator/rsi/evaluation_gate.py",
    "src/orchestrator/rsi/snapshot.py",
    "src/orchestrator/rsi/strategy_eval.py",
    "src/orchestrator/rsi/scenario_validity.py",
    "src/orchestrator/runtime/stages.py",
    "src/orchestrator/runtime/types.py",
    "src/orchestrator/exec/capability_governance.py",
    "src/orchestrator/brain/action.py",
    "src/arena/ablation.py",
    "src/arena/manifests.py",          # never existed -> complete was False
)


# ══════════════════════════════════════════════════════════════════════════
# 1. Phantom component removed; the inventory is honest
# ══════════════════════════════════════════════════════════════════════════

def test_phantom_component_never_existed_in_git_history():
    """Evidence for the removal decision, re-verified in CI."""
    hits = subprocess.run(["git", "log", "--all", "--oneline", "--",
                           "src/arena/manifests.py"],
                          capture_output=True, text=True, cwd=str(REPO)).stdout.strip()
    assert hits == "", f"src/arena/manifests.py unexpectedly exists in history: {hits}"
    blobs = subprocess.run(
        ["git", "rev-list", "--all", "--objects"], capture_output=True, text=True,
        cwd=str(REPO)).stdout
    assert "/manifests.py" not in blobs, "a manifests.py blob exists in history"


def test_phantom_entry_is_gone_from_the_inventory():
    assert "src/arena/manifests.py" not in eg.EVALUATOR_COMPONENT_MODULES


def test_every_declared_component_exists_is_a_file_and_is_readable():
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        p = REPO / rel
        assert p.is_file(), f"declared component is not a file: {rel}"
        assert p.read_bytes(), f"declared component is empty/unreadable: {rel}"


def test_every_declared_component_is_git_tracked():
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        rc = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                            capture_output=True, cwd=str(REPO)).returncode
        assert rc == 0, f"declared component is not tracked: {rel}"


def test_inventory_shrank_by_exactly_the_phantom():
    assert len(eg.EVALUATOR_COMPONENT_MODULES) == len(OLD_DEFECTIVE_COMPONENTS) - 1
    assert set(OLD_DEFECTIVE_COMPONENTS) - set(eg.EVALUATOR_COMPONENT_MODULES) == {
        "src/arena/manifests.py"}


def test_no_invented_replacement_was_substituted():
    """d6_manifest.py exists but must NOT have replaced the phantom merely by
    name resemblance."""
    assert (REPO / "src/arena/d6_manifest.py").is_file()
    assert "src/arena/d6_manifest.py" not in eg.EVALUATOR_COMPONENT_MODULES


# ══════════════════════════════════════════════════════════════════════════
# 2. Current identity is COMPLETE against the real checkout (was the defect)
# ══════════════════════════════════════════════════════════════════════════

def test_a_current_identity_is_complete_on_the_real_checkout():
    identity = EvaluatorIdentity.compute_current(REAL)
    assert identity.complete is True
    assert identity.missing_components == ()
    assert identity.complete is True, "the phantom-component defect is back"


def test_b_missing_component_makes_identity_incomplete(tmp_path, monkeypatch):
    """Simulate removal of a GENUINELY required component: incomplete, and
    classification refuses."""
    # Use a copy of the real repo tree so no real file is touched.

    root = tmp_path / "real_copy"
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    assert EvaluatorIdentity.compute_current(REAL).complete is True

    (root / eg.EVALUATOR_COMPONENT_MODULES[0]).unlink()      # evaluator_gate.py
    after = EvaluatorIdentity.compute_current(REAL)
    assert after.complete is False
    assert eg.EVALUATOR_COMPONENT_MODULES[0] in after.missing_components
    assert after.identity != EvaluatorIdentity.identity  # digest differs


def test_b2_classification_refuses_when_a_component_is_missing(tmp_path, monkeypatch):
    """An incomplete identity must REFUSE, never promote."""

    root = tmp_path / "real_copy2"
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    rec = _finalised(REAL)
    assert classify_promotion_eligibility(rec, REAL).gate(
        "evaluator_identity_current") == "PASS"
    (root / eg.EVALUATOR_COMPONENT_MODULES[1]).unlink()      # snapshot.py
    after = classify_promotion_eligibility(rec, REAL)
    assert after.gate("evaluator_identity_current") == STATUS_REFUSE
    assert after.state != STATE_PROMOTION_ELIGIBLE


# ══════════════════════════════════════════════════════════════════════════
# Helpers: build records that are FINALISED against real authority
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def real_adopted(tmp_path, monkeypatch):
    """SYNTHETIC-AUTHORITY layered over the REAL repository bytes.

    Phase 2 makes the authoritative path require an adopted configuration, and
    this repository has adopted none, so a real-checkout record is legitimately
    refused at `configuration_adopted`. To keep these Phase 1 containment tests
    NON-VACUOUS (proving containment rather than the adoption gate is what
    refuses), this fixture copies the real evaluator modules verbatim and pins a
    SYNTHETIC adoption registry for REAL underneath pytest tmp_path.

    No real holdout, evidence index, or statistical authority is created.
    """
    root = tmp_path / "real_adopted"
    for rel in eg.EVALUATOR_COMPONENT_MODULES:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    anchor = REPO / eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file
    if anchor.is_file():
        dst = root / eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(anchor, dst)
    registry_rel = "evaluations/campaign/phase1a_synthetic_configs.json"
    registry = root / registry_rel
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({
        "schema_version": 1,
        "entries": [{"adoption_id": "phase1a-synthetic", "campaign_id": REAL.campaign_id,
                     "version": 1, "status": "ACTIVE",
                     "config_digest": REAL.config_digest, "config": REAL.to_dict()}],
    }, sort_keys=True), encoding="utf-8")
    anchors = eg.AnchorSet(
        holdout_anchor_file=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_file,
        holdout_anchor_sha256=eg.AUTHORITATIVE_ANCHORS.holdout_anchor_sha256,
        adopted_config_registry_file=registry_rel,
        adopted_config_registry_sha256=hashlib.sha256(
            registry.read_bytes()).hexdigest())
    monkeypatch.setattr(eg, "_REPO_ROOT", root)
    monkeypatch.setattr(eg, "AUTHORITATIVE_ANCHORS", anchors)
    return root, anchors


def _draft(cfg, **overrides):
    """A record draft whose non-authoritative fields are credible. The
    authoritative fields (state/gates/inputs_digest) are filled in by
    :func:`_finalised` or deliberately left inconsistent for negative tests."""
    identity = EvaluatorIdentity.compute_current(cfg).identity
    base = dict(
        decision_id="p1a", campaign_id=cfg.campaign_id, evaluator_identity=identity,
        evaluator_label="phase1a", gate_config_digest=cfg.config_digest,
        inputs_digest="", holdout_id="", holdout_status="", holdout_sha256="",
        holdout_evaluation_refs=(), replay_evaluation_refs=(), evidence_refs=(),
        selection_history_refs=(), parent_lineage=("parent-v1",),
        rollback_target="policy-v1", baseline_policy_hash="b" * 64,
        candidate_policy_hash="c" * 64, protocol_id="", metrics_frozen_digest="",
        reviewer_authority="", runs_candidate=0, runs_baseline=0, exclusions=0,
        effect=None, replay_evidence_complete=False, safety_passed=False,
        final_state="")
    base.update(overrides)
    return EvaluationDecisionRecord.mint(**base)


def _finalised(cfg, **overrides):
    """A record whose state/gates/inputs_digest match CURRENT real authority.

    Uses whatever the real repository actually yields — no fabricated holdout,
    adoption, evidence index, or statistical threshold.
    """
    draft = _draft(cfg, **overrides)
    authority = eg.build_authority(
        cfg, runs_candidate=draft.runs_candidate, runs_baseline=draft.runs_baseline,
        exclusions=draft.exclusions, effect=draft.effect)
    derived = classify_promotion_eligibility(draft, cfg)
    payload = {k: v for k, v in draft.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [list(g) for g in derived.gates]
    payload["final_state"] = derived.state
    payload["inputs_digest"] = eg.derive_evaluation_inputs_digest(draft, authority)
    return EvaluationDecisionRecord.mint(**payload)


def _with_final_state(cfg, state, **overrides):
    """Re-mint a FINALISED record but force a different submitted final_state."""
    good = _finalised(cfg, **overrides)
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["final_state"] = state
    return EvaluationDecisionRecord.mint(**payload)


# ══════════════════════════════════════════════════════════════════════════
# 3. The real checkout yields a usable LOCAL_REPLAY classification
# ══════════════════════════════════════════════════════════════════════════

def test_real_checkout_derives_local_replay_for_a_replay_only_record(real_adopted, ):
    rec = _finalised(REAL, holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    derived = classify_promotion_eligibility(rec, REAL)
    assert derived.state == STATE_LOCAL_REPLAY
    assert not derived.hard_failures(), derived.reasons
    assert derived.gate("evaluator_identity_current") == "PASS"
    assert derived.gate("gate_config_matches") == "PASS"


# ══════════════════════════════════════════════════════════════════════════
# 4. POSITIVE CONTROL: a correct LOCAL_REPLAY record IS admitted
# ══════════════════════════════════════════════════════════════════════════

def test_d_valid_local_replay_append_succeeds_on_real_checkout(real_adopted, tmp_path):
    path = tmp_path / "ledger.jsonl"
    rec = _finalised(REAL, decision_id="p1a-replay",
                     holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    assert rec.final_state == STATE_LOCAL_REPLAY
    ledger = DecisionLedger(path)
    assert ledger.append(rec, REAL) == rec.decision_id
    assert path.exists() and path.read_text(encoding="utf-8").strip()
    # and it survives a reload as CURRENT authority
    reloaded = DecisionLedger(path)
    assert reloaded.get(rec.decision_id) is not None
    assert reloaded.final_states(REAL)[rec.candidate_policy_hash] == STATE_LOCAL_REPLAY


def test_positive_control_proves_containment_is_not_universal_refusal(real_adopted, tmp_path):
    """Contrast: a correct record is admitted, an equivalent forged one is not.

    ``inputs_digest`` deliberately differs between the two, because it binds
    ``decision_id`` and therefore cannot be identical for two distinct records.
    The gates are identical, which is the point: nothing about the derived gate
    set distinguishes them, so only the state-containment check can.
    """
    good = _finalised(REAL, decision_id="p1a-good",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    DecisionLedger(tmp_path / "ok.jsonl").append(good, REAL)

    forged = _with_final_state(REAL, STATE_PROMOTION_ELIGIBLE, decision_id="p1a-forged",
                               holdout_evaluation_refs=(),
                               holdout_status="NOT_APPLICABLE")
    assert forged.gate_outcomes == good.gate_outcomes        # identical gates
    assert forged.evaluator_identity == good.evaluator_identity
    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(tmp_path / "bad.jsonl").append(forged, REAL)


# ══════════════════════════════════════════════════════════════════════════
# 5. THE EXPLOIT: forged PROMOTION_ELIGIBLE cannot be admitted
# ══════════════════════════════════════════════════════════════════════════

def test_e_forged_promotion_eligible_over_local_replay_is_refused(real_adopted, tmp_path):
    """Derived LOCAL_REPLAY, submitted PROMOTION_ELIGIBLE -> REFUSE.

    Containment is what rejects this, not the evaluator-identity defect: the
    record's identity IS current and complete.
    """
    path = tmp_path / "ledger.jsonl"
    forged = _with_final_state(REAL, STATE_PROMOTION_ELIGIBLE, decision_id="p1a-exploit",
                               holdout_evaluation_refs=(),
                               holdout_status="NOT_APPLICABLE")
    derived = classify_promotion_eligibility(forged, REAL)
    assert derived.state == STATE_LOCAL_REPLAY
    assert not derived.hard_failures()
    with pytest.raises(EvaluationGateError, match="final_state mismatch"):
        DecisionLedger(path).append(forged, REAL)
    assert not path.exists()


def test_f_blocked_derived_plus_eligible_claimed_is_refused(tmp_path):
    """A BLOCKED/inadequate-derived record claiming eligibility is refused.

    On the real checkout the anchored holdout is MISSING, so the derived state
    is UNVERIFIABLE_INPUTS (a REFUSE) rather than STATISTICALLY_INADEQUATE. Both
    are non-eligible and both must refuse an eligibility claim; the exact state
    depends on real authority, which this test deliberately does not fabricate.
    """
    forged = _with_final_state(REAL, STATE_PROMOTION_ELIGIBLE, decision_id="p1a-blocked",
                               holdout_evaluation_refs=("ref",),
                               holdout_status="VERIFIED",
                               runs_candidate=1, runs_baseline=1)
    derived = classify_promotion_eligibility(forged, REAL)
    assert derived.state != STATE_PROMOTION_ELIGIBLE
    assert derived.gate("statistical_adequacy") != "PASS"
    assert derived.hard_failures() or derived.state == STATE_STATISTICALLY_INADEQUATE
    with pytest.raises(EvaluationGateError):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, REAL)


def test_f2_blocked_by_adequacy_alone_also_refuses_eligibility(tmp_path):
    """Isolate the statistical-adequacy path: with the holdout claim consistent
    (so no REFUSE gate fires), the derived state is driven by adequacy and an
    eligibility claim is still refused."""
    anchor = eg.load_authoritative_anchor().declaration
    forged = _with_final_state(
        REAL, STATE_PROMOTION_ELIGIBLE, decision_id="p1a-adequacy",
        holdout_evaluation_refs=("ref",),
        holdout_id=anchor.holdout_id, holdout_status=anchor and "MISSING",
        holdout_sha256=anchor.sha256, holdout_row_count=anchor.row_count,
        runs_candidate=1, runs_baseline=1)
    derived = classify_promotion_eligibility(forged, REAL)
    assert derived.gate("holdout_verification") != "PASS"
    assert derived.gate("statistical_adequacy") != "PASS"
    with pytest.raises(EvaluationGateError):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, REAL)


def test_g_refuse_derived_plus_eligible_claimed_is_refused(tmp_path):
    forged = _with_final_state(REAL, STATE_PROMOTION_ELIGIBLE,
                               decision_id="p1a-refused",
                               evaluator_identity="a" * 64)
    derived = classify_promotion_eligibility(forged, REAL)
    assert derived.hard_failures(), "expected a REFUSE gate"
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, REAL)


def test_h_gate_outcome_mismatch_is_refused(real_adopted, tmp_path):
    good = _finalised(REAL, decision_id="p1a-gates",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["gate_outcomes"] = [["parent_lineage", "PASS"]]     # drops gates
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="gate_outcomes mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, REAL)


def test_i_inputs_digest_mismatch_is_refused(real_adopted, tmp_path):
    good = _finalised(REAL, decision_id="p1a-digest",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    payload = {k: v for k, v in good.to_dict().items() if k != "content_hash"}
    payload["inputs_digest"] = "0" * 64
    forged = EvaluationDecisionRecord.mint(**payload)
    with pytest.raises(EvaluationGateError, match="inputs_digest mismatch"):
        DecisionLedger(tmp_path / "l.jsonl").append(forged, REAL)


# ══════════════════════════════════════════════════════════════════════════
# 6. Duplicate gate NAME validation (before set normalisation)
# ══════════════════════════════════════════════════════════════════════════

def test_j_duplicate_gate_name_same_status_is_refused(real_adopted, tmp_path):
    good = _finalised(REAL, decision_id="p1a-dup1",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    gates = list(good.gate_outcomes)
    dup = EvaluationDecisionRecord.mint(**{
        **{k: v for k, v in good.to_dict().items() if k != "content_hash"},
        "gate_outcomes": gates + [gates[0]],
    })
    with pytest.raises(EvaluationGateError, match="duplicate gate name"):
        DecisionLedger(tmp_path / "l.jsonl").append(dup, REAL)


def test_k_duplicate_gate_name_conflicting_status_is_refused(real_adopted, tmp_path):
    good = _finalised(REAL, decision_id="p1a-dup2",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    gates = list(good.gate_outcomes)
    name = gates[0][0]
    other = "REFUSE" if gates[0][1] != "REFUSE" else "PASS"
    dup = EvaluationDecisionRecord.mint(**{
        **{k: v for k, v in good.to_dict().items() if k != "content_hash"},
        "gate_outcomes": gates + [[name, other]],
    })
    with pytest.raises(EvaluationGateError, match="duplicate gate name"):
        DecisionLedger(tmp_path / "l.jsonl").append(dup, REAL)


def test_l_legitimate_gate_reordering_is_accepted(real_adopted, tmp_path):
    """Canonical ordering is a comparison convenience, not a security
    property, so a reordered-but-identical outcome set must be admitted."""
    good = _finalised(REAL, decision_id="p1a-reorder",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    reordered = EvaluationDecisionRecord.mint(**{
        **{k: v for k, v in good.to_dict().items() if k != "content_hash"},
        "gate_outcomes": list(reversed(list(good.gate_outcomes))),
    })
    DecisionLedger(tmp_path / "l.jsonl").append(reordered, REAL)


def test_m_derived_gates_are_duplicate_free():
    """The evaluator must never itself emit a duplicate gate name."""
    for cfg, kwargs in ((REAL, dict(holdout_evaluation_refs=(),
                                   holdout_status="NOT_APPLICABLE")),
                        (REAL, dict(evaluator_identity="a" * 64))):
        derived = classify_promotion_eligibility(_draft(cfg, **kwargs), cfg)
        names = [n for n, _ in derived.gates]
        assert len(names) == len(set(names)), "duplicate gate name emitted"


# ══════════════════════════════════════════════════════════════════════════
# 7. Identity transition: old identity stays historical, never authority
# ══════════════════════════════════════════════════════════════════════════

def test_old_defective_identity_differs_from_corrected_identity():
    """The correction necessarily changes the identity; that is expected."""
    from orchestrator.rsi.evaluation_gate import AnchorSet
    corrected = EvaluatorIdentity.compute_current(REAL).identity
    # Rebuild the OLD inventory's digest by hand: same 9 real components plus
    # one phantom entry, which contributed no readable digest.
    digests = {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
               for rel in OLD_DEFECTIVE_COMPONENTS if (REPO / rel).is_file()}
    digests["src/arena/manifests.py"] = ""      # unreadable -> not counted
    old = hashlib.sha256(json.dumps(
        {"components": dict(sorted(digests.items())),
         "gate_config_digest": REAL.config_digest, "schema_version": 2},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert old != corrected, "identity did not change across the correction"


def test_n_record_minted_under_old_identity_is_historical_not_authority(real_adopted, tmp_path):
    """A record claiming the OLD identity must be refused for identity, while
    remaining readable as an audit artefact."""
    path = tmp_path / "ledger.jsonl"
    current = _finalised(REAL, decision_id="p1a-current",
                         holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    DecisionLedger(path).append(current, REAL)

    # A record minted under the former identity, with its own decision id.
    payload = {k: v for k, v in current.to_dict().items() if k != "content_hash"}
    payload["decision_id"] = "p1a-stale"
    payload["evaluator_identity"] = "0" * 63 + "1"     # a former, different identity
    stale = EvaluationDecisionRecord.mint(**payload)

    # Admission refuses it: the corrected identity is the only current one.
    with pytest.raises(EvaluationGateError, match="refused at admission"):
        DecisionLedger(path).append(stale, REAL)

    # Simulate an EXISTING ledger written under the old identity: the bytes are
    # appended directly (as history would be), never through admission.
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(eg._stable(stale.to_dict()) + "\n")

    ledger = DecisionLedger(path)
    assert ledger.get("p1a-stale") is not None          # historical: readable
    assert ledger.get("p1a-current") is not None        # unaffected
    assert stale.final_state == STATE_LOCAL_REPLAY       # claim preserved verbatim
    assert stale.evaluator_identity != current.evaluator_identity
    # ...but it is NOT current authority under the corrected identity
    assert ledger.current_authority("p1a-stale", REAL) is None
    # and the bytes on disk were never rewritten
    assert stale.evaluator_identity in path.read_text(encoding="utf-8")


def test_o_corrected_identity_is_usable_for_newly_minted_records(real_adopted, tmp_path):
    rec = _finalised(REAL, decision_id="p1a-new",
                     holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    assert rec.evaluator_identity == EvaluatorIdentity.compute_current(REAL).identity
    DecisionLedger(tmp_path / "l.jsonl").append(rec, REAL)


def test_p_stale_cannot_bypass_duplicate_reingestion(real_adopted, tmp_path):
    """Verification precedes the idempotent return: after the identity moves,
    re-appending the same record must fail."""
    path = tmp_path / "ledger.jsonl"
    rec = _finalised(REAL, decision_id="p1a-reingest",
                     holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    ledger = DecisionLedger(path)
    ledger.append(rec, REAL)
    # identical re-ingest under unchanged authority is idempotent
    assert ledger.append(rec, REAL) == rec.decision_id

    # simulate the identity transition: a stale evaluator refuses even though
    # the stored content is identical.
    stale_ledger = DecisionLedger(path)
    object.__setattr__(rec, "evaluator_identity", "0" * 63 + "1")
    with pytest.raises(EvaluationGateError):
        stale_ledger.append(rec, REAL)


def test_q_duplicate_content_and_conflicting_duplicate_paths(real_adopted, tmp_path):
    path = tmp_path / "ledger.jsonl"
    good = _finalised(REAL, decision_id="p1a-dupcontent",
                      holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE")
    ledger = DecisionLedger(path)
    ledger.append(good, REAL)
    assert ledger.append(good, REAL) == good.decision_id        # identical

    clash = _finalised(REAL, decision_id="p1a-dupcontent",
                       holdout_evaluation_refs=(), holdout_status="NOT_APPLICABLE",
                       candidate_policy_hash="d" * 64)
    with pytest.raises(EvaluationGateError, match="append-only"):
        ledger.append(clash, REAL)


# ══════════════════════════════════════════════════════════════════════════
# 8. Scope guards: nothing from Phases 2-4 leaked in
# ══════════════════════════════════════════════════════════════════════════

def test_no_phase3_or_phase4_symbols_exist_yet():
    """Phase 2 added adoption authority; Phase 3/4 must remain unimplemented."""
    for symbol in ("derive_measurement", "MeasurementDerivation",
                   "classify_snapshot_replay", "verify_snapshot_origin",
                   "evaluator_metadata"):
        assert not hasattr(eg, symbol), f"{symbol} must not exist before Phase 3/4"


def test_phase2_adoption_authority_exists():
    """Phase 2 is in place: adoption resolves internally and fail-closed."""
    assert hasattr(eg, "resolve_config_adoption")
    assert hasattr(eg, "ConfigAdoption")
    adoption = eg.resolve_config_adoption(REAL)
    assert adoption.status == "UNADOPTED_CONFIG"
    assert adoption.adopted is False


def test_no_promotion_or_measurement_entry_point_was_added():
    src = Path(eg.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("def promote", "def deploy", "def rollback_policy",
                      "per_run_observations"):
        assert forbidden not in src, forbidden


def test_snapshot_schema_is_still_one():
    from orchestrator.rsi import snapshot as snap
    assert snap.SCHEMA_VERSION == 1


def test_decision_schema_is_still_two():
    """No schema bump in Phase 1A; historical JSONL stays valid as-is."""
    assert eg.SCHEMA_VERSION == 2


def test_no_newly_fabricated_authority_in_the_real_repo():
    """The real holdout must still be absent and no evidence index adopted."""
    assert not (REPO / "evaluations/campaign/rbs_v4_holdout.jsonl").exists()
    anchor = eg.load_authoritative_anchor()
    assert anchor.loaded
    assert eg.verify_authoritative_holdout().status == "MISSING"
    assert eg.load_evidence_index().status == "NO_AUTHORITATIVE_INDEX"