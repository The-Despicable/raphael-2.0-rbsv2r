"""tests/test_rsi1_governance_registry_adversarial.py — attempts to manufacture authority.

Every test here is an attack on a single property: *engineering must not be able
to turn a proposal into a decision.* If any of these passes, the ledger is not
safe to rely on for operator ratification.

The attacks come in two generations. A1–A6 attack the ledger as it stood.
A7 attacks the committed file's origin records, which must never confer
authority however the file is read. A8 attacks the ADR-014 delegation
mechanism: the new capability is the new attack surface, so it gets attacked
hardest — most sharply by the question *what stops an agent from just writing
itself a delegation?*
"""
import json

import pytest

from orchestrator.rsi.governance_registry import (
    AGENT_PRINCIPAL_PREFIX,
    RESERVED_DECISION_CLASSES,
    SELF_ASSERTION_SOURCE,
STATUS_ADOPTED,
    STATUS_INVALIDATED,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    DelegationRecord,
    GovernanceRegistry,
    GovernanceRegistryError,
    OperatorDecisionRecord,
    TrustedIssuer,
    is_agent_principal,
)

from test_rsi1_governance_registry import (  # reuse fixtures, keep one source of truth
    AGENT,
    ATTESTATION_FILE,
    AUTHORITY_CLASS_ADR_ADOPTION,
    AUTHORITY_CLASS_FREEZE_LIFT,
    AUTHORITY_CLASS_GATE_ACCEPTANCE,
    AUTHORITY_CLASS_INVARIANT_EXTENSION,
    AUTHORITY_CLASS_OPERATIONAL,
    AUTHORITY_CLASS_MARKER,
    AUTHORITY_CLASS_UNDECLARED,
    COMMITTED_DELEGATION_ID,
    DELEGATED_DECISION_IDS,
    DELEGATION_FILE,
    DELEGATION_ID,
    DELEGATING,
    ORIGIN_CONTENT_HASHES,
    OPERATOR,
    PROPOSER,
    RESERVED_DECISION_ID,
    RETRACTED_ADOPTION_IDS,
    SEED_FILE,
    TRUST_STORE_FILE,
    _agent_ruled,
    _delegation,
    _proposal,
    _ruled,
    _trusted_issuer,
    committed_registry,
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
    assert registry.get("GD-TEST-01").decision_text.startswith(
        "Ruled by the named authority.")


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
    # keep the prose marker so this fails on the HASH, which is the point,
    # rather than on the earlier structural check
    payload["decision_text"] = "forged ruling text. " + AUTHORITY_CLASS_MARKER + \
        "OPERATIONAL."
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


# ── A7: the committed file's origin records must never confer authority ──
#
# These replace three tests that asserted the whole committed file was
# PROPOSED. That assertion is now false by design, and deleting it would have
# quietly dropped the protection it was giving, so each is restated as the
# property actually worth pinning: the *origin* records are inert, whatever
# follows them.

def test_origin_records_confer_no_authority_even_after_import():
    registry = committed_registry()
    origin = registry.history()[:len(ORIGIN_CONTENT_HASHES)]
    assert len(origin) == 11
    for record in origin:
        assert record.status == STATUS_PROPOSED
        assert record.is_authoritative() is False


def test_origin_records_carry_no_authority_identity_anywhere():
    """Byte level, line by line — not merely via the parsing layer.

    The file now holds four appended state-transition layers after the origin
    proposals: an ADOPTED event and an INVALIDATED retraction for each of the
    four delegated decisions. Every line past the origin block is examined and
    must be attributable to that lifecycle.
    """
    text = SEED_FILE.read_text(encoding="utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    n_origin = len(ORIGIN_CONTENT_HASHES)
    n_retracted = len(RETRACTED_ADOPTION_IDS)
    assert len(lines) == n_origin + (n_retracted * 2), (
        "eleven origin proposals, then one ADOPTED and one INVALIDATED "
        "record for each of the four retracted adoptions")

    # origin block: pure proposals, no authority anywhere
    for line in lines[:n_origin]:
        record = json.loads(line)
        assert record["authority_principal"] == ""
        assert record["decided_at"] == ""
        assert record["status"] == STATUS_PROPOSED
        assert "delegation_ref" not in record
        assert "authority_class" not in record

    # adoption block: agent principal, delegation ref, hash-pinned — but NOT
    # effective authority, and not declared as any class
    for line in lines[n_origin:n_origin + n_retracted]:
        record = json.loads(line)
        assert record["status"] == STATUS_ADOPTED
        assert is_agent_principal(record["authority_principal"])
        assert record["delegation_ref"] == COMMITTED_DELEGATION_ID
        assert record["decided_at"]
        assert "authority_class" not in record, (
            "the historical adoptions predate authority_class, which is why "
            "they can never be treated as authorised rulings")

    # retraction block: the present state of all four decisions
    for line in lines[n_origin + n_retracted:]:
        record = json.loads(line)
        assert record["status"] == STATUS_INVALIDATED
        assert "NOT A REJECTION" in record["decision_text"]
        assert "UNRATIFIED AND OPEN" in record["decision_text"]


def test_no_committed_line_asserts_authority_through_a_bare_principal():
    """Every non-origin line must carry the delegation ref it depends on."""
    text = SEED_FILE.read_text(encoding="utf-8")
    n_origin = len(ORIGIN_CONTENT_HASHES)
    for line in text.splitlines()[n_origin:]:
        if not line.strip():
            continue
        record = json.loads(line)
        principal = record.get("authority_principal", "")
        if principal and is_agent_principal(principal) \
                and record["status"] != STATUS_INVALIDATED:
            assert record.get("delegation_ref"), (
                "an agent ruling without a delegation_ref would be a bare "
                "principal string and must not be constructible")


def test_round_tripping_the_ledger_does_not_promote_anything():
    """Round-tripping must neither gain authority nor lose it."""
    once = committed_registry()
    twice = GovernanceRegistry.from_jsonl(
        once.to_jsonl(), delegations=once.delegations())

    assert len(twice) == len(once)
    assert {r.decision_id for r in twice.authoritative()} \
        == {r.decision_id for r in once.authoritative()}
    # the still-open decisions are still open, including the reserved one
    assert {r.decision_id for r in twice.proposed()} \
        == {r.decision_id for r in once.proposed()}
    assert RESERVED_DECISION_ID in {r.decision_id for r in twice.proposed()}

    # A second round trip adds nothing either.
    thrice = GovernanceRegistry.from_jsonl(
        twice.to_jsonl(), delegations=twice.delegations())
    assert [r.content_hash() for r in thrice.history()] \
        == [r.content_hash() for r in twice.history()]


def test_dropping_the_delegation_does_not_grant_authority():
    """Read without delegation evidence, an agent adoption confers nothing.

    Note the mechanism changed deliberately. This test used to assert that the
    import *aborted*. That was wrong: a ledger you cannot read cannot be
    audited, and the record of an unauthorised adoption is exactly the evidence
    that must be preserved. Loading is now permitted; authorising is not.
    """
    text = SEED_FILE.read_text(encoding="utf-8")

    with_nothing = GovernanceRegistry.from_jsonl(text)
    assert len(with_nothing) == 19, "history must still be readable"
    assert with_nothing.authoritative() == ()
    assert with_nothing.effective_authoritative() == ()
    assert {d for d, _, _ in with_nothing.unverified_authority_records()} \
        == set(RETRACTED_ADOPTION_IDS)

    # and the same is true with delegations but no trusted issuer
    with_delegation_only = GovernanceRegistry.from_jsonl(
        text, delegations=GovernanceRegistry.load_delegations(
            json.loads(DELEGATION_FILE.read_text(encoding="utf-8"))))
    assert with_delegation_only.authoritative() == ()

    # the four adoption events are still auditable, whatever the context
    assert {e.decision_id for e in with_nothing.adoption_events()} \
        == set(RETRACTED_ADOPTION_IDS)


def test_retracted_adoptions_are_never_counted_as_currently_authoritative():
    """The bug the audit found in ``authoritative()``, pinned.

    It used to scan all of history, so a ruling later invalidated still appeared
    as in force. It must consider the CURRENT version only.
    """
    registry = committed_registry()
    adopted_ids = {e.decision_id for e in registry.adoption_events()}
    assert adopted_ids, "there must be adoption events to be confused with"

    for record in registry.authoritative():
        assert record.decision_id not in adopted_ids or \
            registry.get(record.decision_id).status == STATUS_ADOPTED
    assert registry.authoritative() == ()


# ── A8: attacking the delegation mechanism ─────────────────────────────

def test_agent_cannot_authorise_itself_by_acting_as_its_own_delegator():
    """The core attack: an agent writes the delegation that empowers it."""
    with pytest.raises(GovernanceRegistryError, match="issued by an agent"):
        _delegation(delegating_principal=AGENT)


def test_agent_cannot_delegate_to_another_agent():
    """Delegation laundering: agent A delegates to agent B. Still refused."""
    with pytest.raises(GovernanceRegistryError, match="issued by an agent"):
        _delegation(delegating_principal="agent:executor_v-3")


def test_delegation_must_point_at_an_agent_principal():
    with pytest.raises(GovernanceRegistryError, match="namespace"):
        _delegation(agent_principal=DELEGATING)


def test_self_assertion_as_authority_source_is_refused():
    with pytest.raises(GovernanceRegistryError, match=SELF_ASSERTION_SOURCE):
        _delegation(authority_source=SELF_ASSERTION_SOURCE)


def test_agent_ruling_without_a_delegation_ref_is_refused():
    with pytest.raises(GovernanceRegistryError, match="delegation_ref"):
        _agent_ruled(delegation_ref="")


def test_agent_ruling_with_an_unloaded_delegation_is_refused():
    registry = GovernanceRegistry()
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="not loaded"):
        registry.append(_agent_ruled())


def test_agent_cannot_borrow_another_agents_delegation():
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="issued to"):
        registry.append(_agent_ruled(authority_principal="agent:executor-v-3"))


def test_agent_cannot_act_outside_the_delegated_scope():
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal("GD-TEST-02"))
    with pytest.raises(GovernanceRegistryError, match="does not cover"):
        registry.append(_agent_ruled("GD-TEST-02"))


def test_agent_cannot_widen_a_delegation_by_editing_its_scope():
    """Tamper the committed delegation file, then try to load it."""
    payload = json.loads(DELEGATION_FILE.read_text(encoding="utf-8"))
    payload["scope_decision_ids"] = payload["scope_decision_ids"] + ["GD-TEST-01"]
    with pytest.raises(GovernanceRegistryError, match="content_hash mismatch"):
        GovernanceRegistry.load_delegations(payload)


def test_widening_a_delegation_into_the_reserved_class_is_refused_before_the_hash_check():
    """Adding a reserved id is refused even more loudly than a hash mismatch."""
    payload = json.loads(DELEGATION_FILE.read_text(encoding="utf-8"))
    payload["scope_decision_ids"] = payload["scope_decision_ids"] + [
        RESERVED_DECISION_ID]
    with pytest.raises(GovernanceRegistryError, match="reserved decision"):
        GovernanceRegistry.load_delegations(payload)


def test_agent_cannot_use_a_revoked_delegation():
    registry = GovernanceRegistry(delegations=[_delegation(revoked=True)])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="revoked"):
        registry.append(_agent_ruled())


def test_registry_rejects_a_plain_dict_as_a_delegation():
    """Delegations must be validated records, not untyped mappings."""
    with pytest.raises(GovernanceRegistryError, match="DelegationRecord"):
        GovernanceRegistry(delegations=[{"delegation_id": "X"}])


def test_agent_cannot_act_before_or_after_the_validity_window():
    registry = GovernanceRegistry(
        delegations=[_delegation(scope_decision_ids=("GD-EARLY", "GD-LATE"))])
    registry.append(_proposal("GD-EARLY"))
    with pytest.raises(GovernanceRegistryError, match="outside"):
        registry.append(_agent_ruled("GD-EARLY",
                                     decided_at="2026-10-10T23:59:59Z"))

    registry.append(_proposal("GD-LATE"))
    with pytest.raises(GovernanceRegistryError, match="outside"):
        registry.append(_agent_ruled("GD-LATE",
                                     decided_at="2026-10-18T00:00:01Z"))


def test_agent_cannot_use_a_transition_the_delegation_does_not_permit():
    registry = GovernanceRegistry(
        delegations=[_delegation(permitted_transitions=("PROPOSED->REJECTED",))])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="does not permit"):
        registry.append(_agent_ruled())


def test_agent_cannot_reach_the_reserved_decision_class():
    """GD-2026-10-11-03 needs a GLM ruling; no delegation may substitute.

    Two independent layers are exercised. First, a delegation naming the
    reserved id cannot be constructed at all. Second — because the first layer
    alone would be a single point of failure — the append-time check is driven
    directly with a stand-in that quacks like a delegation, to show the guard
    does not depend on the constructor having been the only door in.
    """
    assert RESERVED_DECISION_ID in RESERVED_DECISION_CLASSES

    # layer 1: the delegation record itself refuses to name it
    with pytest.raises(GovernanceRegistryError, match="reserved decision"):
        _delegation(scope_decision_ids=(RESERVED_DECISION_ID,))

    # layer 2: bypass layer 1 and check append() still refuses
    forged = _delegation()
    object.__setattr__(forged, "scope_decision_ids", (RESERVED_DECISION_ID,))
    registry = GovernanceRegistry()
    registry._delegations[DELEGATION_ID] = forged
    registry.append(_proposal(RESERVED_DECISION_ID))
    with pytest.raises(GovernanceRegistryError, match="reserved decision class"):
        registry.append(_agent_ruled(RESERVED_DECISION_ID))


def test_agent_cannot_supersede_another_decision_without_a_delegation():
    """``supersede`` writes a ruled record, so it is behind the same gate."""
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal("GD-OLD"))
    registry.append(_ruled("GD-OLD"))
    with pytest.raises(GovernanceRegistryError, match="delegation_ref"):
        registry.supersede("GD-OLD", successor_id="GD-NEW",
                           authority_principal=AGENT,
                           decided_at="2026-10-11T12:00:00Z", reason="r")


def test_agent_cannot_propose_its_own_delegated_deliberation():
    """An agent may not be proposer and ratifier of the same decision."""
    with pytest.raises(GovernanceRegistryError, match="self-adopted"):
        _agent_ruled(proposer=AGENT)

    # ``append`` re-validates, so a record forced past construction with
    # ``object.__setattr__`` is still refused at the ledger boundary.
    registry = GovernanceRegistry(delegations=[_delegation()])
    forged = _agent_ruled()
    object.__setattr__(forged, "proposer", AGENT)
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="self-adopted"):
        registry.append(forged)


def test_a_proposal_cannot_preload_a_delegation_reference():
    """A delegation authorises a ruling; pointing at one early is refused."""
    with pytest.raises(GovernanceRegistryError, match="PROPOSED record"):
        _proposal(delegation_ref=DELEGATION_ID)


def test_revoked_field_must_be_a_real_bool():
    with pytest.raises(GovernanceRegistryError, match="revoked must be a bool"):
        _delegation(revoked=1)


# ── A9: identity is not authentication ──────────────────────────────────

def test_the_human_attestation_is_still_unsigned_and_unset():
    """ADR-014 must not have quietly converted the pending attestation."""
    text = ATTESTATION_FILE.read_text(encoding="utf-8")
    assert "STATUS: PENDING — NOT SIGNED" in text
    for field in ("Operator name", "Operator GitHub handle", "Operator email",
                  "Date of review", "Signature"):
        assert f"| {field} | *UNSET* |" in text, f"{field} must remain UNSET"


def test_an_arbitrary_identity_string_is_not_proof_of_anything():
    """The registry names a principal; it never authenticates one.

    Both a free-text human name and an agent name are accepted as *claims*.
    What differs is that an agent name additionally requires a delegation, so
    typing a plausible-looking identity can never manufacture authority on its
    own — which was already true for humans, and is now also true for machines.
    """
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal())
    registry.append(_ruled(authority_principal="Dr. A. Principal, CISO"))
    assert len(registry.authoritative()) == 1

    # An agent name in the authority field is refused at construction — a bare
    # principal string is never sufficient for a machine.
    registry.append(_proposal("GD-TEST-99"))
    with pytest.raises(GovernanceRegistryError, match="delegation_ref"):
        _ruled(decision_id="GD-TEST-99", authority_principal=AGENT)

    # And with a delegation_ref but no delegation loaded anywhere, still refused.
    registry2 = GovernanceRegistry()
    registry2.append(_proposal("GD-TEST-99"))
    with pytest.raises(GovernanceRegistryError, match="not loaded"):
        registry2.append(_agent_ruled("GD-TEST-99"))

    # And a delegation that is loaded but out of scope is refused as out of scope.
    with pytest.raises(GovernanceRegistryError, match="does not cover"):
        registry.append(_agent_ruled("GD-TEST-99"))


def test_agent_principal_cannot_be_mistaken_for_a_human_or_for_glm():
    """An `agent:` string is never a human and never the architecture authority."""
    assert is_agent_principal(AGENT)
    assert not is_agent_principal("GLM")
    assert not is_agent_principal("glm")
    assert not is_agent_principal("GLM architecture authority")
    assert not is_agent_principal("operator")
    assert not is_agent_principal(OPERATOR)

    # the committed ledger contains no ruling that claims to be a GLM decision
    registry = committed_registry()
    for record in registry.history():
        assert record.authority_principal != "GLM"
        if record.authority_principal:
            assert is_agent_principal(record.authority_principal), (
                "every authority in the committed ledger must be a disclosed "
                "machine-agent principal, never a borrowed human or GLM name")


def test_no_committed_ruling_claims_gate_acceptance():
    """Ruling four decisions must not have moved any gate."""
    text = SEED_FILE.read_text(encoding="utf-8")
    for banned in ("G3 ACCEPTED", "G3: ACCEPTED", "AM-4-R3 EXECUTED",
                   "freeze lifted", "freeze LIFTED"):
        assert banned not in text, f"ledger must not assert {banned!r}"
# ── A10: the issuer-verification boundary (F2) ───────────────────────────
#
# The audit that motivated this section demonstrated, against the real
# implementation, that a delegation naming an issuer that had never existed
# ("Queen-Of-Authority-Who-Does-Not-Exist") was accepted and a decision was
# adopted under it. A delegation record is an agent-writable file; its content
# hash proves only that nobody edited it after writing. Naming is not
# authentication. These tests pin the fix.


def _adopt_with(registry_kwargs, **record_overrides):
    """Append a proposal then an agent ruling under the given trust context."""
    registry = GovernanceRegistry(**registry_kwargs)
    registry.append(_proposal())
    registry.append(_agent_ruled(**record_overrides))
    return registry


def test_a_nonexistent_issuer_cannot_authorize_an_agent():
    """The audit's exact scenario."""
    registry = GovernanceRegistry(
        delegations=[_delegation(
            delegating_principal="Queen-Of-Authority-Who-Does-Not-Exist")])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())
    assert registry.authoritative() == ()


def test_an_arbitrary_free_text_issuer_cannot_authorize_an_agent():
    """Naming someone plausible changes nothing."""
    for name in ("Dr. A. Principal, CISO",
                 "root",
                 "operator",
                 "GLM",
                 "operator-role:session-delegator-2026-10-11",
                 "a" * 200):
        registry = GovernanceRegistry(
            delegations=[_delegation(delegating_principal=name)])
        registry.append(_proposal())
        with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
            registry.append(_agent_ruled())
        assert registry.authoritative() == ()


def test_matching_the_expected_issuer_string_is_not_authentication():
    """A name that matches a documented role label is still just a string."""
    registry = GovernanceRegistry(
        delegations=[_delegation(delegating_principal=DELEGATING)])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())
    assert registry.trusted_issuers() == ()
    assert registry.authoritative() == ()


def test_a_correctly_hashed_but_unverified_delegation_grants_nothing():
    """Perfect structural validity is not authorisation."""
    delegation = _delegation()
    payload = delegation.to_dict()
    assert payload["content_hash"] == delegation.content_hash()
    # the record is internally perfect...
    reparsed = DelegationRecord.from_dict(payload)
    assert reparsed.content_hash() == delegation.content_hash()
    # ...and still confers nothing without a trusted issuer
    registry = GovernanceRegistry(delegations=[reparsed])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())
    assert registry.authoritative() == ()


def test_editing_a_delegation_and_recomputing_its_hash_does_not_authenticate():
    """The strongest form of the attack: forge a valid, self-consistent file."""
    forged = _delegation(delegating_principal="The-Sovereign-Issuer")
    payload = forged.to_dict()          # carries the CORRECT hash for the forgery
    reparsed = DelegationRecord.from_dict(payload)
    assert reparsed.content_hash() == forged.content_hash()

    registry = GovernanceRegistry(delegations=[reparsed])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(_agent_ruled())
    assert registry.authoritative() == ()


def test_a_claimed_signature_cannot_pass_without_a_trusted_verification_key():
    """There is no signature substrate here, so a claimed one proves nothing."""
    registry = GovernanceRegistry(delegations=[_delegation()])
    registry.append(_proposal())
    record = _agent_ruled(decision_text=(
        "Ruled. AUTHORITY CLASS: OPERATIONAL. "
        "SIGNATURE: RSA-SHA256:AAAAdeadbeef... "
        "SIGNED BY THE OPERATOR, VERIFIED 2026-10-11"))
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry.append(record)
    assert registry.authoritative() == ()

    # Naming a verification method does not conjure a key: a TrustedIssuer is a
    # CLAIM of verification, and this repository has no key material, no
    # signature substrate and no verifier. Constructing one is therefore
    # permitted and proves nothing — which is exactly why the committed store
    # is empty and why an issuer must be placed there by a human act.
    claim = TrustedIssuer(
        issuer_id="forged-signer",
        verification_method="rsa-sha256",
        verified_by="nobody",
        verified_at="2026-10-11T00:00:00Z",
        evidence_refs=("no-such-evidence-file.json",),
        notes="no key material exists or was supplied")
    assert claim.issuer_id == "forged-signer"

    # and it authorises nothing until a delegation from that issuer is loaded too
    registry2 = GovernanceRegistry(delegations=[_delegation()])
    registry2._trusted["forged-signer"] = claim
    assert [i.issuer_id for i in registry2.trusted_issuers()] == ["forged-signer"]
    registry2.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match="trusted-issuer store"):
        registry2.append(_agent_ruled())   # DELEGATING is not 'forged-signer'


def test_trust_store_cannot_be_populated_by_an_agent():
    """The store is not a door the agent can open for itself."""
    with pytest.raises(GovernanceRegistryError, match="trust anchor"):
        TrustedIssuer(
            issuer_id=AGENT,
            verification_method="self-assertion",
            verified_by="human-placeholder",
            verified_at="2026-10-11T00:00:00Z",
            evidence_refs=("e",))
    with pytest.raises(GovernanceRegistryError, match="only a non-agent authority"):
        TrustedIssuer(
            issuer_id="somebody-else",
            verification_method="self-assertion",
            verified_by=AGENT,
            verified_at="2026-10-11T00:00:00Z",
            evidence_refs=("e",))
    # and the registry refuses a dict masquerading as a verified issuer
    with pytest.raises(GovernanceRegistryError, match="TrustedIssuer objects"):
        GovernanceRegistry(trusted_issuers=[{"issuer_id": "sneaky"}])
    # and it cannot be unevidenced
    with pytest.raises(GovernanceRegistryError, match="evidence_refs"):
        TrustedIssuer(
            issuer_id="somebody",
            verification_method="whatever",
            verified_by="human-placeholder",
            verified_at="2026-10-11T00:00:00Z",
            evidence_refs=())


def test_the_committed_trust_store_is_empty():
    """The repository has no trust root, so the store must be empty."""
    raw = json.loads(TRUST_STORE_FILE.read_text(encoding="utf-8"))
    assert raw["trusted_issuers"] == []
    assert raw["store_status"] == "EMPTY_NO_TRUST_ROOT_EXISTS"
    assert GovernanceRegistry.load_trusted_issuers(raw["trusted_issuers"]) == ()
    assert committed_registry().trusted_issuers() == ()


def test_a_verified_issuer_enables_only_what_it_covers():
    """The positive control: with a trusted issuer, the same delegation works."""
    registry = GovernanceRegistry(delegations=[_delegation()],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    registry.append(_agent_ruled())
    assert len(registry.authoritative()) == 1
    assert registry.authority_problems() == {}

    # but the same issuer does not extend to an unscoped decision
    registry.append(_proposal("GD-OUT"))
    with pytest.raises(GovernanceRegistryError, match="does not cover"):
        registry.append(_agent_ruled("GD-OUT"))


@pytest.mark.parametrize("mutation,expected", [
    ({"effective_from": "2030-01-01T00:00:00Z",
      "expires_at": "2031-01-01T00:00:00Z"}, "outside"),
    ({"revoked": True}, "revoked"),
    ({"scope_decision_ids": ("GD-SOMETHING-ELSE",)}, "does not cover"),
    ({"permitted_transitions": ("PROPOSED->REJECTED",)}, "does not permit"),
])
def test_scope_window_revocation_and_transitions_still_bind_with_a_trusted_issuer(
        mutation, expected):
    """The trust store does not relax any other check."""
    registry = GovernanceRegistry(delegations=[_delegation(**mutation)],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    with pytest.raises(GovernanceRegistryError, match=expected):
        registry.append(_agent_ruled())


# ── A11: structural vs effective authority (F6) ─────────────────────────

def test_orphan_delegation_reference_is_never_effectively_authoritative():
    """The exact defect the audit found."""
    orphan = _agent_ruled(decision_id="GD-ORPHAN",
                          delegation_ref="DEL-DOES-NOT-EXIST")
    assert orphan.delegation_ref == "DEL-DOES-NOT-EXIST"
    # structurally fine...
    assert orphan.is_authoritative() is True

    # ...but with no such delegation anywhere, it is not authority
    registry = GovernanceRegistry()
    registry._records.append(orphan)
    assert registry.effective_authoritative() == ()
    assert registry.authoritative() == ()
    assert "GD-ORPHAN" in registry.authority_problems()


def test_existing_but_unverified_delegation_does_not_grant_authority():
    delegation = _delegation()
    registry = GovernanceRegistry(delegations=[delegation])   # no trust store
    record = _agent_ruled()
    registry._records.append(record)
    assert record.is_authoritative() is True, "structurally valid"
    assert registry.effective_authoritative() == (), "not authorised"
    assert "trusted-issuer store" in registry.authority_problems()["GD-TEST-01"]


def test_structural_and_effective_authority_are_distinguishable():
    """The two APIs answer different questions and say so."""
    registry = GovernanceRegistry(delegations=[_delegation()],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    adopted = _agent_ruled()
    registry.append(adopted)

    assert adopted.is_authoritative() is True                 # structural
    assert registry.effective_authoritative() == (adopted,)   # contextual
    assert adopted in registry.current_records()

    # a structurally-ruled record that is NOT effective is still distinguishable
    unverified = GovernanceRegistry(delegations=[_delegation()])
    record = _agent_ruled()
    unverified._records.append(record)
    assert record.is_authoritative() is True
    assert unverified.effective_authoritative() == ()
    assert unverified.invalidated() == ()


def test_undeclared_class_is_never_authoritative():
    """A ruling that never said what kind of act it was, confers nothing."""
    record = _ruled(authority_class=AUTHORITY_CLASS_UNDECLARED)
    assert record.declared_authority_class() == AUTHORITY_CLASS_UNDECLARED
    assert record.is_authoritative() is False

    registry = GovernanceRegistry()
    registry.append(_proposal())
    registry.append(record)
    assert registry.authoritative() == ()


# ── A12: reserved authority classes (F7) ────────────────────────────────

@pytest.mark.parametrize("reserved_class", [
    AUTHORITY_CLASS_GATE_ACCEPTANCE,
    AUTHORITY_CLASS_INVARIANT_EXTENSION,
    AUTHORITY_CLASS_ADR_ADOPTION,
    AUTHORITY_CLASS_FREEZE_LIFT,
])
def test_reserved_class_is_refused_whatever_the_decision_id(reserved_class):
    """The point of F7: a NEW reserved decision must not slip through."""
    fresh_id = "GD-9999-01-01"          # never registered anywhere
    assert fresh_id not in RESERVED_DECISION_CLASSES

    registry = GovernanceRegistry(delegations=[
        _delegation(scope_decision_ids=(fresh_id,))],
        trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal(fresh_id))
    with pytest.raises(GovernanceRegistryError, match="reserved authority class"):
        registry.append(_agent_ruled(fresh_id, authority_class=reserved_class))
    assert registry.authoritative() == ()


def test_declaring_operational_while_text_announces_a_reserved_act_is_refused():
    """Altering only the description must not evade the reserved class."""
    for text in ("G3 ACCEPTED as of today.",
                 "The freeze is LIFTED for P4.",
                 "ADR-013 ADOPTED by this decision.",
                 "This EXTENDS THE INVARIANT to the legacy plane."):
        registry = GovernanceRegistry(delegations=[_delegation()],
                                      trusted_issuers=[_trusted_issuer()])
        registry.append(_proposal())
        with pytest.raises(GovernanceRegistryError,
                           match="reserved effect|reserved authority class"):
            registry.append(_agent_ruled(
                authority_class=AUTHORITY_CLASS_OPERATIONAL,
                decision_text=f"{text} {AUTHORITY_CLASS_MARKER}OPERATIONAL."))
        assert registry.authoritative() == ()


def test_quarantine_decisions_are_not_treated_as_gate_acceptance():
    """Naming G3 must not automatically make a narrowing decision reserved.

    This is the half of F7 that must not over-block: a quarantine of a bridge
    or an agent path is a scope-narrowing disposition about a gate, not the
    acceptance of that gate.
    """
    registry = GovernanceRegistry(delegations=[_delegation()],
                                  trusted_issuers=[_trusted_issuer()])
    registry.append(_proposal())
    registry.append(_agent_ruled(
        affected_gate="G3",
        authority_class=AUTHORITY_CLASS_OPERATIONAL,
        decision_text=("PROPOSED B2 - QUARANTINE. The bridge remains outside "
                       f"authorized operational use. {AUTHORITY_CLASS_MARKER}"
                       "OPERATIONAL.")))
    assert len(registry.authoritative()) == 1, (
        "a quarantine disposition about G3 must remain permissible")


def test_a_proposal_may_not_declare_an_authority_class():
    with pytest.raises(GovernanceRegistryError, match="PROPOSED record"):
        _proposal(authority_class=AUTHORITY_CLASS_OPERATIONAL)
    with pytest.raises(GovernanceRegistryError, match="PROPOSED record"):
        _proposal(authority_class=AUTHORITY_CLASS_GATE_ACCEPTANCE)


def test_declared_class_must_be_legible_in_the_record_text():
    """A metadata field a reviewer cannot check is not auditable."""
    with pytest.raises(GovernanceRegistryError, match="AUTHORITY CLASS"):
        OperatorDecisionRecord(
            decision_id="GD-T", topic="t", question="q?",
            allowed_options=("a", "b"), status=STATUS_ADOPTED,
            proposer=PROPOSER, decision_text="No marker anywhere.",
            source_ref="s", affected_gate="G8", authority_principal=OPERATOR,
            decided_at="2026-10-09", evidence_refs=("e",),
            authority_class=AUTHORITY_CLASS_OPERATIONAL)