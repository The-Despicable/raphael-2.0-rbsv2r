"""tests/test_rsi1_governance_registry.py — unit tests for the operator decision ledger.

Covers record validation, status-state transitions, the append-only API surface,
the JSONL round trip, and the bounded machine-agent delegation mechanism
introduced by ADR-014. Adversarial cases live in
``test_rsi1_governance_registry_adversarial.py``.

Two states of the committed ledger are deliberately distinguished, because
collapsing them is the mistake this workstream exists to prevent:

* the **eleven origin proposals** — immutable history, every one ``PROPOSED``,
  every one carrying no authority; and
* the **appended delegated transitions** that follow them, which are the only
  records in the file that confer authority, and only through a valid delegation.
"""
import json
from pathlib import Path

import pytest

from orchestrator.rsi.governance_registry import (
    AGENT_PRINCIPAL_PREFIX,
    ALLOWED_TRANSITIONS,
    ALL_STATUSES,
    AUTHORITY_CLASS_ADR_ADOPTION,
    AUTHORITY_CLASS_FREEZE_LIFT,
    AUTHORITY_CLASS_GATE_ACCEPTANCE,
    AUTHORITY_CLASS_INVARIANT_EXTENSION,
    AUTHORITY_CLASS_OPERATIONAL,
    AUTHORITY_CLASS_UNDECLARED,
    AUTHORITY_CLASSES,
    AUTHORITY_CLASS_MARKER,
    DELEGATION_SCHEMA_VERSION,
    RESERVED_AUTHORITY_CLASSES,
    RESERVED_DECISION_CLASSES,
    SCHEMA_VERSION,
    SELF_ASSERTION_SOURCE,
    STATUS_ADOPTED,
    STATUS_INVALIDATED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    STATUSES,
    TRUSTED_ISSUER_SCHEMA_VERSION,
    DelegationRecord,
    GovernanceRegistry,
    GovernanceRegistryError,
    OperatorDecisionRecord,
    TrustedIssuer,
    is_agent_principal,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl"
DELEGATION_FILE = (REPO_ROOT / "evidence" / "governance"
                   / "EXECUTOR_DELEGATION_20261011.json")
ATTESTATION_FILE = (REPO_ROOT / "evidence" / "provenance_correction"
                    / "OPERATOR_ATTESTATION.md")
TRUST_STORE_FILE = (REPO_ROOT / "evidence" / "governance"
                    / "TRUSTED_ISSUERS.json")

OPERATOR = "operator-principal"
PROPOSER = "engineering-originating-session"

AGENT = "agent:executor_v-2"
DELEGATING = "operator-role:test-delegator"
DELEGATION_ID = "DEL-TEST-01"

#: A non-agent issuer used only where a test needs one that *could* be trusted.
VERIFIED_ISSUER = "operator-role:independently-verified"

#: The committed delegation this workstream actually used.
COMMITTED_DELEGATION_ID = "DEL-2026-10-11-01"

#: The decision ids that delegation was scoped to. GD-2026-10-11-03 is absent
#: **by design**: it is a reserved decision class no delegation may reach.
DELEGATED_DECISION_IDS = (
    "GD-2026-10-11-01",
    "GD-2026-10-11-02",
    "GD-2026-10-11-04",
    "GD-2026-10-11-05",
)

#: Those same ids were ADOPTED in commit 36329f0ab and subsequently retracted.
#: The adoption events remain in history; their present effect is nil.
RETRACTED_ADOPTION_IDS = DELEGATED_DECISION_IDS

RESERVED_DECISION_ID = "GD-2026-10-11-03"

#: The eleven origin proposals, pinned by content hash. Read from the commit
#: that introduced them; any rewrite of history changes one of these.
ORIGIN_CONTENT_HASHES = (
    ("GD-2026-10-09-01", "ae0d1265c9fbf9f3cfc49e038e92d0c2519476fe61461d24416da19fc2108c6a"),
    ("GD-2026-10-09-02", "b93f5a62a55a7ce911fa6c851a8c326fcc976d4a9aa9fb3c15b943a5a52ae262"),
    ("GD-2026-10-09-03", "760f82bb5507047567f13618b3ca63c13c8f3a2920cea4264d484558705940fd"),
    ("GD-2026-10-09-04", "99eb72e24ee3f8bd413bcc47e9ab7f9e32be72935c3270b92e67e1d7046d6160"),
    ("GD-2026-10-09-05", "30bf9465ea19c570673c107a010e4f410c99cd3587c7329a31e11e79dc653d94"),
    ("GD-2026-10-09-06", "227289259d3d175d1b082d0bd0b8c35f4df341b7a5fbabe5e4de2aa04f4e1da8"),
    ("GD-2026-10-11-01", "26abb7094e9898e8f3f69d386f27e8f2981139a97def3f7fab706b43698496cd"),
    ("GD-2026-10-11-02", "61e0802f6cbf8217434d5ff513a83c264d455a5dbdac6f73e8803f013243ed2e"),
    ("GD-2026-10-11-03", "75766f9edb7265b3d525d45cc5963efbd0ca82c7ff04d95ba7e36ffceb294664"),
    ("GD-2026-10-11-04", "d5cdbb6a5f86c876114efc4e183e2472a102d15eb6347cd27f806ba83911efc0"),
    ("GD-2026-10-11-05", "d0cfb4a43c57b7ef504d3dfe5a3367758ce3c30d8441c757435fc4db98e2114e"),
)


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
    """A ruling by a named NON-agent principal.

    It declares ``OPERATIONAL`` and carries the matching prose marker, because
    an *undeclared* ruling is deliberately not authoritative (F7): the registry
    will not hand back a "yes this is in force" for a record that never said
    what kind of authority act it was.
    """
    kwargs = dict(
        decision_id=decision_id,
        topic="test-topic",
        question="What is the answer?",
        allowed_options=("option-a", "option-b"),
        status=status,
        proposer=PROPOSER,
        decision_text="Ruled by the named authority. "
                      "AUTHORITY CLASS: OPERATIONAL.",
        source_ref="test-source",
        affected_gate="G8",
        authority_principal=OPERATOR,
        decided_at="2026-10-09",
        evidence_refs=("evidence/example.json",),
        authority_class=AUTHORITY_CLASS_OPERATIONAL,
    )
    kwargs.update(overrides)
    # Keep the record self-consistent: if a caller overrode decision_text but
    # kept the default authority_class, re-attach the prose marker the registry
    # requires. Tests should assert on their own property, not on marker
    # plumbing. (The marker requirement itself is tested directly, below.)
    if kwargs["authority_class"].strip() \
            and kwargs["authority_class"].strip() != AUTHORITY_CLASS_UNDECLARED \
            and AUTHORITY_CLASS_MARKER not in kwargs["decision_text"]:
        kwargs["decision_text"] += f" AUTHORITY CLASS: {kwargs['authority_class']}."
    return OperatorDecisionRecord(**kwargs)


def _delegation(**overrides) -> DelegationRecord:
    """A minimal, valid delegation. Attack cases mutate it via ``overrides``."""
    kwargs = dict(
        delegation_id=DELEGATION_ID,
        agent_principal=AGENT,
        delegating_principal=DELEGATING,
        authority_source="explicit_delegation_in_active_operator_session",
        scope_decision_ids=("GD-TEST-01",),
        permitted_transitions=("PROPOSED->ADOPTED",),
        effective_from="2026-10-11T00:00:00Z",
        expires_at="2026-10-18T00:00:00Z",
        revoked=False,
        authored_by=AGENT,
        verification_status="UNVERIFIED_BY_THIRD_PARTY",
        decision="Bounded test delegation.",
        evidence_refs=("evidence/governance/test.json",),
    )
    kwargs.update(overrides)
    return DelegationRecord(**kwargs)


def _trusted_issuer(issuer_id=DELEGATING, **overrides) -> TrustedIssuer:
    """An issuer the trust store accepts.

    NOTE: constructing one does NOT mean the repository trusts anyone. This is a
    test fixture for the mechanism; the committed store is empty, and the tests
    that assert the committed state depend on that.
    """
    kwargs = dict(
        issuer_id=issuer_id,
        verification_method="independent_identity_verification",
        verified_by="human-authority-placeholder",
        verified_at="2026-10-11T00:00:00Z",
        evidence_refs=("evidence/governance/verification.json",),
        notes="test fixture",
    )
    kwargs.update(overrides)
    return TrustedIssuer(**kwargs)


def _agent_ruled(decision_id="GD-TEST-01", **overrides):
    kwargs = dict(
        decision_id=decision_id,
        topic="test-topic",
        question="What is the answer?",
        allowed_options=("option-a", "option-b"),
        status=STATUS_ADOPTED,
        proposer=PROPOSER,
        decision_text="Ruled by the delegated machine agent. "
                      "AUTHORITY CLASS: OPERATIONAL. Quarantine posture.",
        source_ref="test-source",
        affected_gate="G8",
        authority_principal=AGENT,
        decided_at="2026-10-11T12:00:00Z",
        evidence_refs=("evidence/example.json",),
        delegation_ref=DELEGATION_ID,
        authority_class=AUTHORITY_CLASS_OPERATIONAL,
    )
    kwargs.update(overrides)
    if kwargs["authority_class"].strip() \
            and kwargs["authority_class"].strip() != AUTHORITY_CLASS_UNDECLARED \
            and AUTHORITY_CLASS_MARKER not in kwargs["decision_text"]:
        kwargs["decision_text"] += f" AUTHORITY CLASS: {kwargs['authority_class']}."
    return OperatorDecisionRecord(**kwargs)


def committed_registry() -> GovernanceRegistry:
    """The committed ledger, loaded the way production must load it.

    Both halves of the authority context are supplied: the delegation record
    AND the trusted-issuer store. The store is empty, so every machine-agent
    ruling in this ledger is loaded as history and reported as unverified — it
    is never honoured.
    """
    import json

    delegations = GovernanceRegistry.load_delegations(
        json.loads(DELEGATION_FILE.read_text(encoding="utf-8")))
    trusted = GovernanceRegistry.load_trusted_issuers(
        json.loads(TRUST_STORE_FILE.read_text(encoding="utf-8"))
        ["trusted_issuers"])
    return GovernanceRegistry.from_jsonl(
        SEED_FILE.read_text(encoding="utf-8"), delegations=delegations,
        trusted_issuers=trusted)


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
    """Pin the whole table, and pin the property the old `or True` failed to.

    The previous form read
    ``assert STATUS_PROPOSED in ALLOWED_TRANSITIONS[STATUS_ADOPTED] or True``,
    which asserted nothing: ``or True`` swallows every outcome, so the suite
    stayed green whichever way the transition table was edited. It has been
    replaced by two non-vacuous assertions. This is in scope because the
    amended authorisation logic depends on exactly which transitions are legal:
    ``PROPOSED -> ADOPTED`` is the only escalation, and nothing may widen it.
    """
    assert set(ALLOWED_TRANSITIONS) == set(ALL_STATUSES)
    assert ALLOWED_TRANSITIONS[STATUS_SUPERSEDED] == ()
    assert ALLOWED_TRANSITIONS == {
        STATUS_PROPOSED: (STATUS_ADOPTED, STATUS_REJECTED),
        STATUS_ADOPTED: (STATUS_SUPERSEDED, STATUS_INVALIDATED),
        STATUS_REJECTED: (STATUS_SUPERSEDED,),
        STATUS_SUPERSEDED: (),
        # INVALIDATED may be re-adopted by a genuinely authorised principal,
        # but nothing may transition back INTO PROPOSED.
        STATUS_INVALIDATED: (STATUS_ADOPTED,),
    }

    # ADOPTED -> PROPOSED is NOT legal: a ruling can never be quietly relabelled
    # back into an open proposal, and no status may ever transition *into*
    # PROPOSED. (The old assertion's literal reading asked the opposite question
    # and got a vacuous pass either way.)
    for status, targets in ALLOWED_TRANSITIONS.items():
        assert STATUS_PROPOSED not in targets, (
            f"{status} must not be able to transition to PROPOSED")

    # INVALIDATED must be reachable from ADOPTED, and must not be reachable
    # from PROPOSED — retracting an adoption presupposes an adoption.
    assert STATUS_INVALIDATED in ALLOWED_TRANSITIONS[STATUS_ADOPTED]
    assert STATUS_INVALIDATED not in ALLOWED_TRANSITIONS[STATUS_PROPOSED]


def test_invalidated_is_not_a_way_to_reach_authority_from_a_proposal():
    """A proposal may not jump straight to INVALIDATED to dodge a ruling."""
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-J"))
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(OperatorDecisionRecord(
            decision_id="GD-J", topic="test-topic", question="What is the answer?",
            allowed_options=("option-a", "option-b"),
            status=STATUS_INVALIDATED, proposer=PROPOSER,
            decision_text="x", source_ref="test-source", affected_gate="G8",
            authority_principal=OPERATOR, decided_at="2026-10-11",
            evidence_refs=("evidence/example.json",)))


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


# ── the committed ledger: origin proposals vs retracted adoptions ─────────
#
# The old test here asserted the whole file was PROPOSED. That was true when
# the file was eleven untouched seeds, stopped being true when a ratification
# was appended, and is true again now only by a different route. The property
# worth protecting is the one all three states share: *nothing in this file
# grants authority by itself.*

def test_committed_ledger_exists_and_loads_with_its_delegation():
    assert SEED_FILE.is_file(), "run scripts/gen_governance_decision_seeds.py"
    assert DELEGATION_FILE.is_file(), "ADR-014 requires a delegation record"
    assert TRUST_STORE_FILE.is_file(), "ADR-014 section 3.1a requires a trust store"
    registry = committed_registry()
    assert len(registry) == 19
    assert len(registry.delegations()) == 1
    assert len(registry.trusted_issuers()) == 0, (
        "the committed trust store must be EMPTY: this repository has no trust "
        "root, so no delegation can confer effective authority")


def test_origin_proposals_are_immutable_and_still_confer_nothing():
    """The eleven origin records are history and are pinned by content hash."""
    registry = committed_registry()
    origin = registry.history()[:len(ORIGIN_CONTENT_HASHES)]

    assert len(origin) == len(ORIGIN_CONTENT_HASHES)
    assert [(r.decision_id, r.content_hash()) for r in origin] \
        == list(ORIGIN_CONTENT_HASHES), (
            "the eleven origin proposals must retain their exact content hashes; "
            "a change here means history was rewritten, not extended")

    for record in origin:
        assert record.status == STATUS_PROPOSED
        assert record.authority_principal == ""
        assert record.decided_at == ""
        assert record.delegation_ref == ""
        assert record.is_authoritative() is False


def test_no_committed_decision_is_effective_authority():
    """The headline property after the audit: the ledger grants nothing.

    Four ADOPTED records exist in history. They confer nothing, for two
    independent reasons — the trust store is empty, and the current version of
    each decision is INVALIDATED. Either alone would suffice.
    """
    registry = committed_registry()

    assert registry.authoritative() == (), (
        "no committed decision may be in force: no trusted issuer exists")
    assert registry.effective_authoritative() == ()
    assert len(registry.proposed()) == 7
    assert len(registry.invalidated()) == 4
    assert {r.decision_id for r in registry.invalidated()} \
        == set(RETRACTED_ADOPTION_IDS)


def test_retracted_adoptions_remain_discoverable_as_history():
    """F1: the adoption events were preserved, not deleted or rewritten."""
    registry = committed_registry()
    events = registry.adoption_events()

    assert len(events) == 4
    assert {e.decision_id for e in events} == set(RETRACTED_ADOPTION_IDS)
    for event in events:
        assert event.status == STATUS_ADOPTED
        assert event.authority_principal == AGENT
        assert event.delegation_ref == COMMITTED_DELEGATION_ID
        # an undeclared class is itself a reason it is not authoritative
        assert event.declared_authority_class() == AUTHORITY_CLASS_UNDECLARED
        assert event.is_authoritative() is False

    # each decision now has three versions: proposal, adoption, retraction
    for decision_id in RETRACTED_ADOPTION_IDS:
        versions = registry.versions(decision_id)
        assert [v.status for v in versions] == [
            STATUS_PROPOSED, STATUS_ADOPTED, STATUS_INVALIDATED]
        assert registry.get(decision_id).status == STATUS_INVALIDATED


def test_retraction_is_not_a_rejection_and_not_a_supersession():
    """INVALIDATED must not be mistaken for a ruling against the substance."""
    registry = committed_registry()
    for decision_id in RETRACTED_ADOPTION_IDS:
        record = registry.get(decision_id)
        assert record.status != STATUS_REJECTED
        assert record.status != STATUS_SUPERSEDED
        text = record.decision_text
        assert "NOT A REJECTION" in text
        assert "UNRATIFIED AND OPEN" in text
        # and no successor decision is asserted to exist
        assert "Successor decision:" not in text


def test_retracted_adoptions_are_reported_as_unverified_authority():
    """F2: unverified machine-agent rulings are surfaced, not silently dropped."""
    registry = committed_registry()
    faults = registry.unverified_authority_records()

    assert len(faults) == 4
    for decision_id, status, reason in faults:
        assert decision_id in RETRACTED_ADOPTION_IDS
        assert status == STATUS_ADOPTED
        assert "trusted-issuer store" in reason

    assert registry.authority_problems() == {}, (
        "no decision is currently ADOPTED, so there are no live authority "
        "problems — the retractions resolved them")


def test_invalidated_can_be_re_adopted_but_never_relabelled_proposed():
    registry = GovernanceRegistry()
    registry.append(_proposal("GD-R"))
    registry.append(_ruled("GD-R"))
    registry.append(OperatorDecisionRecord(
        decision_id="GD-R", topic="test-topic", question="What is the answer?",
        allowed_options=("option-a", "option-b"),
        status=STATUS_INVALIDATED, proposer=PROPOSER,
        decision_text="Adoption retracted; authority not established.",
        source_ref="test-source", affected_gate="G8",
        authority_principal=OPERATOR, decided_at="2026-10-11",
        evidence_refs=("evidence/example.json",)))

    assert registry.get("GD-R").status == STATUS_INVALIDATED
    assert registry.authoritative() == ()
    # a genuine re-ratification remains possible
    registry.append(_ruled("GD-R", decision_text="Re-adopted by a real authority"))
    assert registry.get("GD-R").status == STATUS_ADOPTED
    # but nothing may transition back INTO PROPOSED
    with pytest.raises(GovernanceRegistryError, match="illegal transition"):
        registry.append(_proposal("GD-R", question="a different question?"))


def test_reserved_decision_gd_03_stays_proposed_without_glm_concurrence():
    """GD-2026-10-11-03 needs an independent GLM ruling that does not exist.

    Its component 2 extends ADR-003 INV-2/INV-3 beyond their documented closure,
    which is an invariant-scope change reserved to the architecture authority. No
    delegation may reach it, so it keeps a single PROPOSED version.
    """
    registry = committed_registry()
    versions = registry.versions(RESERVED_DECISION_ID)

    assert len(versions) == 1, "GD-03 must have exactly one, still-PROPOSED version"
    assert versions[0].status == STATUS_PROPOSED
    assert versions[0].authority_principal == ""
    assert RESERVED_DECISION_ID not in {r.decision_id for r in registry.authoritative()}
    assert RESERVED_DECISION_ID in RESERVED_DECISION_CLASSES


def test_each_adoption_appends_and_preserves_the_original_proposal():
    """An adoption is a state transition, never a rewritten proposal."""
    registry = committed_registry()
    for decision_id in DELEGATED_DECISION_IDS:
        versions = registry.versions(decision_id)
        assert len(versions) == 3
        proposed, adopted, invalidated = versions

        assert proposed.status == STATUS_PROPOSED
        assert proposed.content_hash() in dict(ORIGIN_CONTENT_HASHES).values()
        assert adopted.status == STATUS_ADOPTED
        assert invalidated.status == STATUS_INVALIDATED

        # every field that carries decision content is carried over verbatim
        for field in ("topic", "question", "allowed_options", "proposer",
                      "source_ref", "affected_gate", "evidence_refs"):
            assert getattr(adopted, field) == getattr(proposed, field), (
                f"{decision_id}: {field} was altered by ratification")
        assert adopted.decision_text.startswith(proposed.decision_text), (
            f"{decision_id}: the original proposal text must be preserved "
            "verbatim, with the ruling appended after it")
        assert "ADOPTED BY:" in adopted.decision_text
        assert COMMITTED_DELEGATION_ID in adopted.decision_text


def test_committed_ledger_round_trips_without_gaining_or_losing_authority():
    """Serialisation is stable: no promotion, no loss, no re-hashing."""
    registry = committed_registry()
    again = GovernanceRegistry.from_jsonl(
        registry.to_jsonl(), delegations=registry.delegations(),
        trusted_issuers=registry.trusted_issuers())

    assert len(again) == len(registry)
    assert [r.content_hash() for r in again.history()] \
        == [r.content_hash() for r in registry.history()]
    assert again.authoritative() == registry.authoritative() == ()
    assert len(again.invalidated()) == len(registry.invalidated()) == 4
    assert len(registry.proposed()) == len(again.proposed())


def test_seed_generator_emits_proposals_only():
    """The generator cannot ratify, even after the ledger has been ratified."""
    import importlib.util

    def _load_generator():
        spec = importlib.util.spec_from_file_location(
            "gen_governance_decision_seeds",
            REPO_ROOT / "scripts" / "gen_governance_decision_seeds.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    registry = _load_generator().build()
    assert len(registry) == len(ORIGIN_CONTENT_HASHES)
    assert registry.authoritative() == ()
    assert len(registry.proposed()) == len(ORIGIN_CONTENT_HASHES)

    for record in registry.history():
        assert record.status == STATUS_PROPOSED
        assert record.authority_principal == ""
        assert record.decided_at == ""
        assert record.delegation_ref == ""
    # and the generated proposals are exactly the pinned origin records
    assert [(r.decision_id, r.content_hash()) for r in registry.history()] \
        == list(ORIGIN_CONTENT_HASHES)


def test_committed_ledger_has_diverged_from_the_seed_set():
    """The seeds alone no longer reproduce the ledger — and that is deliberate."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_governance_decision_seeds_divergence",
        REPO_ROOT / "scripts" / "gen_governance_decision_seeds.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    generated = module.build().to_jsonl()
    committed = SEED_FILE.read_text(encoding="utf-8")

    assert generated != committed, (
        "the committed ledger now differs from the generated seeds")
    assert committed.startswith(generated), (
        "the eleven origin proposals must still be a verbatim prefix of the "
        "ledger; later records are appended, never spliced in")
    assert len(committed.splitlines()) > len(generated.splitlines())


# ── seed-generator overwrite guard (F5) ──────────────────────────────────
#
# These never invoke the destructive path against the real ledger: the
# generator module is loaded, OUT_PATH is redirected to tmp_path, and the real
# committed file is only ever READ.

def _load_generator():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gen_governance_decision_seeds_guard",
        REPO_ROOT / "scripts" / "gen_governance_decision_seeds.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_refuses_to_overwrite_adopted_history(tmp_path, monkeypatch):
    module = _load_generator()
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(module, "OUT_PATH", target)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    # a ledger holding adoption + retraction history, copied verbatim
    target.write_text(SEED_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    before = target.read_bytes()

    assert module.main() == 2, "must refuse, not truncate"
    assert target.read_bytes() == before, (
        "a refused overwrite must leave the file byte-for-byte identical")
    assert len(target.read_text(encoding="utf-8").splitlines()) == 19


def test_generator_refuses_on_every_non_proposal_status(tmp_path, monkeypatch):
    """ADOPTED, REJECTED, SUPERSEDED and INVALIDATED must all block."""
    module = _load_generator()
    for status in module.NON_PROPOSAL_STATUSES:
        target = tmp_path / f"ledger-{status}.jsonl"
        monkeypatch.setattr(module, "OUT_PATH", target)
        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
        payload = {
            "affected_gate": "G8", "allowed_options": ["a"], "authority_principal": "x",
            "content_hash": "0" * 64, "decided_at": "2026-10-11", "decision_id": "GD-X",
            "decision_text": "t", "evidence_refs": ["e"], "proposer": "p",
            "question": "q?", "schema_version": 1, "source_ref": "s",
            "status": status, "topic": "t",
        }
        target.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        before = target.read_bytes()
        assert module.main() == 2, f"{status} must block an overwrite"
        assert target.read_bytes() == before


def test_generator_refuses_when_existing_data_is_malformed(tmp_path, monkeypatch):
    """Ambiguity is a reason to stop, not a reason to proceed."""
    module = _load_generator()
    for bad in ("{not json}\n", "[1,2,3]\n", '{"no":"status"}\n'):
        target = tmp_path / "bad.jsonl"
        monkeypatch.setattr(module, "OUT_PATH", target)
        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
        target.write_text(bad, encoding="utf-8")
        before = target.read_bytes()
        assert module.main() == 2, f"malformed data must block: {bad!r}"
        assert target.read_bytes() == before


def test_generator_refuses_on_a_proposal_carrying_authority_fields(
        tmp_path, monkeypatch):
    """A 'proposal' with authority is not an unratified seed proposal."""
    module = _load_generator()
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(module, "OUT_PATH", target)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    record = json.loads(module.build().to_jsonl().splitlines()[0])
    record["authority_principal"] = "agent:sneaky"
    record["content_hash"] = "0" * 64
    target.write_text(json.dumps(record) + "\n", encoding="utf-8")
    before = target.read_bytes()
    assert module.main() == 2
    assert target.read_bytes() == before


def test_generator_still_writes_a_clean_seed_ledger(tmp_path, monkeypatch):
    """Legitimate seed-only generation must keep working."""
    module = _load_generator()
    target = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(module, "OUT_PATH", target)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    assert module.main() == 0
    assert len(target.read_text(encoding="utf-8").splitlines()) \
        == len(ORIGIN_CONTENT_HASHES)
    # second run: identical content, clean no-op
    before = target.read_bytes()
    assert module.main() == 0
    assert target.read_bytes() == before


def test_generator_describe_existing_ledger_reports_blocking_ids():
    module = _load_generator()
    verdict, reasons, blocking = module.describe_existing_ledger(
        SEED_FILE.read_text(encoding="utf-8"))
    assert verdict == "refuse"
    assert set(blocking) == set(RETRACTED_ADOPTION_IDS)
    assert any("INVALIDATED" in r for r in reasons)
    assert any("ADOPTED" in r for r in reasons)

    verdict, _, _ = module.describe_existing_ledger("")
    assert verdict == "empty"


# ── delegation: structure ───────────────────────────────────────────────

def test_agent_principal_namespace_is_reserved_in_code():
    assert is_agent_principal("agent:executor_v-2")
    assert is_agent_principal("  agent:anything  ")   # padding is not a disguise
    assert not is_agent_principal("GLM")
    assert not is_agent_principal("operator-principal")
    assert not is_agent_principal("")
    assert not is_agent_principal(None)
    assert not is_agent_principal(42)
    assert AGENT_PRINCIPAL_PREFIX == "agent:"


def test_delegation_record_structure_round_trips():
    delegation = _delegation()
    payload = delegation.to_dict()
    assert payload["content_hash"] == delegation.content_hash()
    restored = DelegationRecord.from_dict(payload)
    assert restored.content_hash() == delegation.content_hash()
    assert restored.scope_decision_ids == delegation.scope_decision_ids
    assert DELEGATION_SCHEMA_VERSION == 1


def test_delegation_requires_enumerated_scope_transitions_and_a_window():
    with pytest.raises(GovernanceRegistryError, match="no enumerated scope"):
        _delegation(scope_decision_ids=())
    with pytest.raises(GovernanceRegistryError, match="permitted_transitions"):
        _delegation(permitted_transitions=())
    with pytest.raises(GovernanceRegistryError, match="strictly after"):
        _delegation(effective_from="2026-10-18T00:00:00Z",
                    expires_at="2026-10-11T00:00:00Z")
    with pytest.raises(GovernanceRegistryError, match="ISO-8601"):
        _delegation(effective_from="not-a-date")


def test_delegation_window_requires_an_explicit_offset():
    """A naive timestamp is refused rather than assumed-UTC."""
    with pytest.raises(GovernanceRegistryError, match="explicit UTC offset"):
        _delegation(effective_from="2026-10-11T00:00:00")


def test_delegation_predicates():
    delegation = _delegation()
    assert delegation.covers("GD-TEST-01")
    assert not delegation.covers("GD-TEST-02")
    assert delegation.permits_transition(STATUS_PROPOSED, STATUS_ADOPTED)
    assert not delegation.permits_transition(STATUS_ADOPTED, STATUS_ADOPTED)
    assert delegation.in_window("2026-10-11T12:00:00Z")
    assert delegation.in_window("2026-10-11T00:00:00Z")     # inclusive edges
    assert delegation.in_window("2026-10-18T00:00:00Z")
    assert not delegation.in_window("2026-10-10T23:59:59Z")
    assert not delegation.in_window("2026-10-18T00:00:01Z")


def test_delegation_rejects_a_tampered_scope():
    """Editing a delegation in place breaks its content hash."""
    payload = _delegation().to_dict()
    payload["scope_decision_ids"] = ["GD-TEST-01", "GD-TEST-02"]
    with pytest.raises(GovernanceRegistryError, match="content_hash mismatch"):
        DelegationRecord.from_dict(payload)


def test_delegation_may_not_scope_a_reserved_decision():
    with pytest.raises(GovernanceRegistryError, match="reserved decision"):
        _delegation(scope_decision_ids=(RESERVED_DECISION_ID,))


# ── delegation: the authorisation path works ────────────────────────────

def test_agent_adoption_succeeds_only_under_a_verified_delegation():
    """The success path needs BOTH halves: delegation AND a trusted issuer.

    This is the positive control for F2. Without it, "the guard always refuses"
    would also pass every test, which proves nothing about the mechanism.
    """
    registry = GovernanceRegistry(delegations=[_delegation()],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    registry.append(_agent_ruled())

    assert len(registry) == 2
    assert len(registry.authoritative()) == 1
    assert registry.get("GD-TEST-01").authority_principal == AGENT
    assert registry.get("GD-TEST-01").delegation_ref == DELEGATION_ID
    assert registry.authority_problems() == {}


def test_agent_adoption_fails_without_a_trusted_issuer():
    """Identical to the positive control above, minus the trust store."""
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())
    assert registry.authoritative() == ()


def test_agent_adoption_fails_with_a_trust_store_naming_a_different_issuer():
    """A trusted store that does not name THIS issuer is no help."""
    registry = GovernanceRegistry(
        delegations=[_delegation()],
        trusted_issuers=[_trusted_issuer(issuer_id="someone.else")])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())


def test_human_principal_needs_no_delegation_and_cannot_borrow_one():
    registry = GovernanceRegistry(delegations=[_delegation()],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    registry.append(_ruled())
    assert len(registry.authoritative()) == 1

    with pytest.raises(GovernanceRegistryError, match="may only be carried by"):
        _ruled(decision_id="GD-TEST-02", delegation_ref=DELEGATION_ID)


def test_loading_a_ledger_never_grants_authority_by_itself():
    """Loading and authorising are separate acts (F2/F6).

    The earlier design aborted the import when delegation evidence could not be
    verified. That was wrong in a subtle way: a ledger you cannot read cannot
    be audited, and the record of an unauthorised adoption is precisely the
    evidence that must be preserved. So the import succeeds, the record is
    reported as unverified, and every authority query withholds it.
    """
    text = committed_registry().to_jsonl()

    # no delegation context at all
    bare = GovernanceRegistry.from_jsonl(text)
    assert len(bare) == 19
    assert bare.authoritative() == ()
    faults = bare.unverified_authority_records()
    assert {d for d, _, _ in faults} == set(RETRACTED_ADOPTION_IDS)

    # delegation context but an empty trust store — the committed state
    partial = GovernanceRegistry.from_jsonl(
        text, delegations=GovernanceRegistry.load_delegations(json.loads(
            DELEGATION_FILE.read_text(encoding="utf-8"))))
    assert len(partial) == 19
    assert partial.authoritative() == ()

    # full context is identical, because the committed trust store is empty
    assert len(committed_registry()) == 19
    assert committed_registry().authoritative() == ()


def test_agent_principal_is_not_authoritative_without_a_delegation():
    """Constructing the record is possible; appending it is not."""
    registry = GovernanceRegistry()
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="not loaded"):
        registry.append(_agent_ruled())
    assert registry.authoritative() == ()


def test_human_principal_needs_no_delegation_and_cannot_borrow_one():
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal())
    registry.append(_ruled())
    assert len(registry.authoritative()) == 1

    with pytest.raises(GovernanceRegistryError, match="may only be carried by"):
        _ruled(decision_id="GD-TEST-02", delegation_ref=DELEGATION_ID)


def test_import_without_delegations_fails_closed_on_a_delegated_ledger():
    """Superseded: an import must not ABORT, but must grant nothing.

    Kept as a regression on the underlying security property — an
    unverifiable agent adoption contributes no authority — with the mechanism
    updated to match the corrected design. See
    ``test_loading_a_ledger_never_grants_authority_by_itself`` for the full
    statement of loading-versus-authorising.
    """
    text = committed_registry().to_jsonl()
    registry = GovernanceRegistry.from_jsonl(text)
    assert registry.authoritative() == ()
    assert registry.effective_authoritative() == ()
    assert len(registry) == 19


def test_reserved_decision_id_is_enumerated_with_a_stated_reason():
    assert RESERVED_DECISION_ID in RESERVED_DECISION_CLASSES
    assert RESERVED_DECISION_CLASSES[RESERVED_DECISION_ID].strip()
    assert COMMITTED_DELEGATION_ID  # sanity: the committed delegation exists
