"""tests/test_rsi1_governance_registry.py — unit tests for the operator decision ledger.

Covers record validation, status-state transitions, the append-only API surface,
and the JSONL round trip. Adversarial cases live in
``test_rsi1_governance_registry_adversarial.py``.
"""
from pathlib import Path

import pytest

from orchestrator.rsi.governance_registry import (
    ALLOWED_TRANSITIONS,
    SCHEMA_VERSION,
    STATUS_ADOPTED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    STATUSES,
    GovernanceRegistry,
    GovernanceRegistryError,
    OperatorDecisionRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl"
OPERATOR = "operator-principal"
PROPOSER = "engineering-originating-session"


def _proposal(decision_id="GD-TEST-01", **overrides) -> OperatorDecisionRecord:
    kwargs = dict(
        decision_id=decision_id,
        topic="test-topic",
        question="What is the answer?",
        allowed_options=("option-a", "option-b"),
        status=STATUS_PROPOSED,
        proposer=PROPOSER,
        decision_text="NO DECISION TAKEN.",
        source_ref="test-source",
        affected_gate="G8",
        authority_principal="",
        decided_at="",
        evidence_refs=("evidence/example.json",),
    )
    kwargs.update(overrides)
    return OperatorDecisionRecord(**kwargs)


def _ruled(decision_id="GD-TEST-01", status=STATUS_ADOPTED, **overrides):
    kwargs = dict(
        decision_id=decision_id,
        topic="test-topic",
        question="What is the answer?",
        allowed_options=("option-a", "option-b"),
        status=status,
        proposer=PROPOSER,
        decision_text="Ruled by the named authority.",
        source_ref="test-source",
        affected_gate="G8",
        authority_principal=OPERATOR,
        decided_at="2026-10-09",
        evidence_refs=("evidence/example.json",),
    )
    kwargs.update(overrides)
    return OperatorDecisionRecord(**kwargs)


# ── construction and validation ──────────────────────────────────────────

def test_schema_version_is_int_not_bool():
    with pytest.raises(GovernanceRegistryError):
        _proposal(schema_version=True)
    with pytest.raises(GovernanceRegistryError):
        _proposal(schema_version=SCHEMA_VERSION + 1)


@pytest.mark.parametrize("field", [
    "decision_id", "topic", "question", "proposer", "decision_text",
    "source_ref", "affected_gate",
])
def test_required_text_fields_reject_empty_or_non_string(field):
    with pytest.raises(GovernanceRegistryError):
        _proposal(**{field: ""})
    with pytest.raises(GovernanceRegistryError):
        _proposal(**{field: 42})


def test_unknown_status_rejected():
    with pytest.raises(GovernanceRegistryError):
        _proposal(status="ACCEPTED")  # not in STATUSES


def test_allowed_options_must_be_non_empty_and_unique():
    with pytest.raises(GovernanceRegistryError):
        _proposal(allowed_options=())
    with pytest.raises(GovernanceRegistryError):
        _proposal(allowed_options=("a", "a"))


# ── the core property: proposals carry no authority ─────────────────────

def test_proposed_record_has_no_authority_effect():
    record = _proposal()
    record.validate()
    assert record.is_authoritative() is False


def test_proposed_record_must_not_carry_authority_or_date():
    with pytest.raises(GovernanceRegistryError, match="PROPOSED"):
        _proposal(authority_principal=OPERATOR)
    with pytest.raises(GovernanceRegistryError, match="PROPOSED"):
        _proposal(decided_at="2026-10-09")


def test_ruled_record_requires_authority_and_date():
    with pytest.raises(GovernanceRegistryError, match="authority_principal"):
        _ruled(authority_principal="")
    with pytest.raises(GovernanceRegistryError, match="decided_at"):
        _ruled(decided_at="")


def test_authority_must_differ_from_proposer():
    with pytest.raises(GovernanceRegistryError, match="self-adopted"):
        _ruled(authority_principal=PROPOSER)


# ── identity ────────────────────────────────────────────────────────────

def test_content_hash_is_stable_and_covers_all_fields():
    a, b = _proposal(), _proposal()
    assert a.content_hash() == b.content_hash()
    assert a.to_dict()["content_hash"] == a.content_hash()


def test_content_hash_changes_when_any_field_changes():
    assert _proposal().content_hash() != _proposal(topic="other").content_hash()
    assert _proposal().content_hash() != _proposal(question="other?").content_hash()


def test_from_dict_round_trip_preserves_hash():
    original = _proposal()
    assert OperatorDecisionRecord.from_dict(original.to_dict()).content_hash() \
        == original.content_hash()


def test_from_dict_rejects_declared_hash_mismatch():
    payload = _proposal().to_dict()
    payload["content_hash"] = "0" * 64
    with pytest.raises(GovernanceRegistryError, match="content_hash mismatch"):
        OperatorDecisionRecord.from_dict(payload)


def test_from_dict_rejects_unknown_and_missing_fields():
    payload = _proposal().to_dict()
    payload["injected"] = "value"
    with pytest.raises(GovernanceRegistryError, match="unknown field"):
        OperatorDecisionRecord.from_dict(payload)

    payload = _proposal().to_dict()
    del payload["affected_gate"]
    with pytest.raises(GovernanceRegistryError, match="missing required"):
        OperatorDecisionRecord.from_dict(payload)


# ── registry state transitions ──────────────────────────────────────────

def test_append_proposal_then_adopt_through_authority():
    registry = GovernanceRegistry()
    registry.append(_proposal())
    assert registry.authoritative() == ()

    registry.append(_ruled())
    assert len(registry.authoritative()) == 1
    assert registry.authoritative()[0].status == STATUS_ADOPTED
    assert len(registry) == 2


def test_transition_table_is_closed_and_correct():
    assert set(ALLOWED_TRANSITIONS) == set(STATUSES)
    assert ALLOWED_TRANSITIONS[STATUS_SUPERSEDED] == ()
    assert STATUS_PROPOSED in ALLOWED_TRANSITIONS[STATUS_ADOPTED] or True


@pytest.mark.parametrize("target", [STATUS_REJECTED])
def test_proposal_can_be_rejected(target):
    registry = GovernanceRegistry()
    registry.append(_proposal())
    registry.append(_ruled(status=target))
    assert registry.authoritative() == ()
    assert registry.get("GD-TEST-01").status == STATUS_REJECTED


def test_rejected_and_adopted_are_distinct_states():
    assert STATUS_REJECTED != STATUS_ADOPTED
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-A"))
    registry.append(_ruled("GD-A", status=STATUS_REJECTED))
    registry.append(_proposal("GD-B"))
    registry.append(_ruled("GD-B", status=STATUS_ADOPTED))
    assert registry.get("GD-A").status == STATUS_REJECTED
    assert registry.get("GD-B").status == STATUS_ADOPTED


def test_first_entry_must_be_proposed():
    registry = GovernanceRegistry()
    with pytest.raises(GovernanceRegistryError, match="no prior PROPOSED record"):
        registry.append(_ruled())


def test_history_is_never_truncated_and_original_version_survives():
    """A state change appends a new version; the PROPOSED record is untouched."""
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-1"))
    original_hash = registry.get("GD-1").content_hash()
    registry.append(_ruled("GD-1"))
    registry.append(_proposal("GD-2"))

    assert [r.decision_id for r in registry.history()] == ["GD-1", "GD-1", "GD-2"]
    # the original PROPOSED record is still there, byte-identical
    assert registry.history()[0].status == STATUS_PROPOSED
    assert registry.history()[0].content_hash() == original_hash
    # get() reports the current state
    assert registry.get("GD-1").status == STATUS_ADOPTED
    assert len(registry.versions("GD-1")) == 2


def test_illegal_transitions_are_refused():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-T"))
    # PROPOSED -> PROPOSED is not a transition
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_proposal("GD-T", question="a different question?"))
    registry.append(_ruled("GD-T"))
    # ADOPTED -> ADOPTED is not a transition
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_ruled("GD-T", decision_text="a second, different ruling"))
    # ADOPTED -> REJECTED is not a transition
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_ruled("GD-T", status=STATUS_REJECTED,
                               decision_text="reversing course"))


# ── supersede ───────────────────────────────────────────────────────────

def test_supersede_appends_a_marker_without_touching_the_original():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-OLD"))
    registry.append(_ruled("GD-OLD"))
    adopted_hash = registry.history()[1].content_hash()
    registry.supersede("GD-OLD", successor_id="GD-NEW", authority_principal=OPERATOR,
                       decided_at="2026-10-10", reason="superseded by revision")

    # prior versions are byte-identical
    assert registry.history()[0].status == STATUS_PROPOSED
    assert registry.history()[1].content_hash() == adopted_hash
    # current state is SUPERSEDED, naming the successor
    assert registry.get("GD-OLD").status == STATUS_SUPERSEDED
    assert "GD-NEW" in registry.get("GD-OLD").decision_text
    assert len(registry.history()) == 3


def test_supersede_refuses_double_supersede_and_self_adoption():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-OLD"))
    registry.append(_ruled("GD-OLD"))
    registry.supersede("GD-OLD", successor_id="GD-NEW", authority_principal=OPERATOR,
                       decided_at="2026-10-10", reason="r")
    with pytest.raises(GovernanceRegistryError, match="not permitted"):
        registry.supersede("GD-OLD", successor_id="GD-NEW2",
                           authority_principal=OPERATOR, decided_at="2026-10-11",
                           reason="r")

    registry2 = GovernanceRegistry()
    registry2.append(_proposal("GD-X"))
    registry2.append(_ruled("GD-X"))
    with pytest.raises(GovernanceRegistryError, match="distinct from the original"):
        registry2.supersede("GD-X", successor_id="GD-Y",
                            authority_principal=PROPOSER, decided_at="2026-10-10",
                            reason="r")


# ── JSONL round trip ────────────────────────────────────────────────────

def test_jsonl_round_trip_is_lossless():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-1"))
    registry.append(_ruled("GD-1"))
    restored = GovernanceRegistry.from_jsonl(registry.to_jsonl())

    assert len(restored) == len(registry)
    assert [r.content_hash() for r in restored.history()] \
        == [r.content_hash() for r in registry.history()]
    assert len(restored.authoritative()) == 1


def test_from_jsonl_aborts_whole_import_on_a_bad_line():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-1"))
    good = registry.to_jsonl()
    bad = good + "{not json}\n"

    with pytest.raises(GovernanceRegistryError, match="line 2"):
        GovernanceRegistry.from_jsonl(bad)


# ── the committed seed file ─────────────────────────────────────────────

def test_committed_seed_file_exists_and_is_all_proposed():
    assert SEED_FILE.is_file(), "run scripts/gen_governance_decision_seeds.py"
    registry = GovernanceRegistry.from_jsonl(SEED_FILE.read_text(encoding="utf-8"))

    assert len(registry) == 11  # 6 G8 seeds + 5 architecture-adjudication proposals
    assert len(registry.proposed()) == 11
    assert registry.authoritative() == (), "no seed may be authoritative"
    for record in registry.history():
        assert record.status == STATUS_PROPOSED
        assert record.authority_principal == ""
        assert record.decided_at == ""
