"""tests/test_rsi1_governance_registry_adversarial.py — attempts to manufacture authority.

Every test here is an attack on a single property: *engineering must not be able
to turn a proposal into a decision.* If any of these passes, the ledger is not
safe to rely on for operator ratification.
"""
import json

import pytest

from orchestrator.rsi.governance_registry import (
    STATUS_ADOPTED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    GovernanceRegistry,
    GovernanceRegistryError,
    OperatorDecisionRecord,
)

from test_rsi1_governance_registry import (  # reuse fixtures, keep one source of truth
    OPERATOR,
    PROPOSER,
    SEED_FILE,
    _proposal,
    _ruled,
)


# ── A1: self-adoption ───────────────────────────────────────────────────

def test_authority_equal_to_proposer_is_refused():
    with pytest.raises(GovernanceRegistryError, match="self-adopted"):
        _ruled(authority_principal=PROPOSER)


def test_authority_whitespace_variant_of_proposer_is_refused():
    """Padding must not smuggle a proposer past the equality check."""
    with pytest.raises(GovernanceRegistryError, match="self-adopted"):
        _ruled(authority_principal=f"  {PROPOSER}  ")


def test_whitespace_only_authority_is_refused():
    with pytest.raises(GovernanceRegistryError, match="requires a non-empty"):
        _ruled(authority_principal="   ")


def test_non_string_authority_is_refused():
    with pytest.raises(GovernanceRegistryError):
        _ruled(authority_principal=["operator"])


# ── A2: authority smuggled into a proposal ──────────────────────────────

def test_proposal_carrying_authority_is_refused():
    with pytest.raises(GovernanceRegistryError):
        _proposal(authority_principal=OPERATOR)


def test_proposal_carrying_a_decision_date_is_refused():
    with pytest.raises(GovernanceRegistryError):
        _proposal(decided_at="2026-10-09")


def test_proposal_carrying_authority_and_date_together_is_refused():
    with pytest.raises(GovernanceRegistryError):
        _proposal(authority_principal=OPERATOR, decided_at="2026-10-09")


def test_case_variant_status_is_not_accepted():
    with pytest.raises(GovernanceRegistryError):
        _proposal(status="proposed")
    with pytest.raises(GovernanceRegistryError):
        _proposal(status="Adopted")


# ── A3: skipping the proposal entirely ──────────────────────────────────

def test_cannot_enter_the_ledger_already_ruled():
    for status in (STATUS_ADOPTED, STATUS_REJECTED, STATUS_SUPERSEDED):
        registry = GovernanceRegistry()
        with pytest.raises(GovernanceRegistryError, match="no prior PROPOSED"):
            registry.append(_ruled(status=status,
                                   authority_principal=OPERATOR if status != STATUS_SUPERSEDED else OPERATOR,
                                   decided_at="2026-10-09"))


# ── A4: rewriting history ───────────────────────────────────────────────

def test_identical_duplicate_is_refused():
    registry = GovernanceRegistry()
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="duplicate decision_id"):
        registry.append(_proposal())


def test_conflicting_record_under_same_id_is_refused():
    registry = GovernanceRegistry()
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_proposal(question="a different question?"))


def test_conflicting_ruling_does_not_replace_the_original():
    registry = GovernanceRegistry()
    registry.append(_proposal())
    registry.append(_ruled())
    first_ruling = registry.get("GD-TEST-01").content_hash()

    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_ruled(decision_text="a different ruling"))
    assert registry.get("GD-TEST-01").content_hash() == first_ruling
    assert registry.get("GD-TEST-01").decision_text == "Ruled by the named authority."


def test_append_rejects_non_record_objects():
    registry = GovernanceRegistry()
    with pytest.raises(GovernanceRegistryError, match="expects an OperatorDecisionRecord"):
        registry.append({"decision_id": "GD-X", "status": STATUS_ADOPTED})


# ── A5: gaining authority through supersede ─────────────────────────────

def test_supersede_cannot_be_performed_by_the_proposer():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-S"))
    registry.append(_ruled("GD-S"))
    with pytest.raises(GovernanceRegistryError, match="distinct from the original"):
        registry.supersede("GD-S", successor_id="GD-S2", authority_principal=PROPOSER,
                            decided_at="2026-10-10", reason="self")


def test_supersede_marker_requires_authority_and_date():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-S"))
    with pytest.raises(GovernanceRegistryError):
        registry.supersede("GD-S", successor_id="GD-S2", authority_principal="",
                            decided_at="2026-10-10", reason="r")
    with pytest.raises(GovernanceRegistryError):
        registry.supersede("GD-S", successor_id="GD-S2", authority_principal=OPERATOR,
                            decided_at="", reason="r")


def test_supersede_cannot_reuse_an_existing_successor_id():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-S"))
    registry.append(_ruled("GD-S"))
    registry.append(_proposal("GD-S2"))
    with pytest.raises(GovernanceRegistryError, match="already exists"):
        registry.supersede("GD-S", successor_id="GD-S2", authority_principal=OPERATOR,
                           decided_at="2026-10-10", reason="r")


def test_supersede_cannot_reuse_the_same_id():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-S"))
    registry.append(_ruled("GD-S"))
    with pytest.raises(GovernanceRegistryError, match="must differ"):
        registry.supersede("GD-S", successor_id="GD-S", authority_principal=OPERATOR,
                           decided_at="2026-10-10", reason="r")


def test_an_never_ruled_proposal_cannot_be_superseded():
    """PROPOSED -> SUPERSEDED is not a transition: nothing was decided yet.

    The correct route for a proposal the authority will not take is REJECTED,
    which keeps the proposal visible in history.
    """
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-U"))
    with pytest.raises(GovernanceRegistryError, match="not permitted"):
        registry.supersede("GD-U", successor_id="GD-U2", authority_principal=OPERATOR,
                           decided_at="2026-10-10", reason="r")
    registry.append(_ruled("GD-U", status=STATUS_REJECTED))
    assert registry.get("GD-U").status == STATUS_REJECTED


# ── A6: forged files ────────────────────────────────────────────────────

def test_tampered_record_fails_hash_check_on_import():
    payload = _ruled().to_dict()
    payload["decision_text"] = "forged ruling text"
    line = json.dumps(payload) + "\n"
    with pytest.raises(GovernanceRegistryError, match="content_hash mismatch"):
        GovernanceRegistry.from_jsonl(line)


def test_import_aborts_and_yields_nothing_when_a_later_line_is_corrupt():
    good = json.dumps(_proposal("GD-OK").to_dict()) + "\n"
    corrupt = '{"decision_id": "GD-BAD", "status": "PROPOSED"\n'
    with pytest.raises(GovernanceRegistryError):
        GovernanceRegistry.from_jsonl(good + corrupt)


def test_import_refuses_duplicate_ids_across_lines():
    line = json.dumps(_proposal("GD-DUP").to_dict()) + "\n"
    with pytest.raises(GovernanceRegistryError, match="duplicate decision_id"):
        GovernanceRegistry.from_jsonl(line + line)


def test_import_refuses_a_forged_second_ruling_in_the_middle_of_a_lifecycle():
    """A tampered file must not be able to replay a plausible-looking ruling."""
    proposed = _proposal("GD-FORGED")
    adopted = _ruled("GD-FORGED")
    forged = _ruled("GD-FORGED", decision_text="forged extra ruling")
    text = "".join(
        json.dumps(r.to_dict(), sort_keys=True) + "\n"
        for r in (proposed, adopted, forged))

    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        GovernanceRegistry.from_jsonl(text)


def test_record_declaring_a_status_outside_the_vocabulary_is_refused_on_import():
    payload = _proposal().to_dict()
    payload["status"] = "TRIED"
    with pytest.raises(GovernanceRegistryError):
        GovernanceRegistry.from_jsonl(json.dumps(payload) + "\n")


# ── A7: the committed seed file must never confer authority ─────────────

def test_committed_seeds_confer_no_authority_even_after_import():
    registry = GovernanceRegistry.from_jsonl(SEED_FILE.read_text(encoding="utf-8"))
    assert registry.authoritative() == ()
    assert all(r.status == STATUS_PROPOSED for r in registry.history())


def test_committed_seeds_carry_no_authority_identity_anywhere():
    text = SEED_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        assert record["authority_principal"] == ""
        assert record["decided_at"] == ""
        assert record["status"] == STATUS_PROPOSED


def test_round_tripping_the_seed_file_does_not_promote_anything():
    once = GovernanceRegistry.from_jsonl(SEED_FILE.read_text(encoding="utf-8"))
    twice = GovernanceRegistry.from_jsonl(once.to_jsonl())
    assert twice.authoritative() == ()
    assert len(twice) == len(once)
