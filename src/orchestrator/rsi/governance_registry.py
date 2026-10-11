"""governance_registry.py — operator decision ledger (minimal, RSI-1).

Purpose
-------
Represent operator decisions **explicitly** so that "a decision was made" is
provable from repository content rather than inferred from a report. Records
carry a stable ``decision_id``, the topic, the source they came from, the gate
or invariant they affect, the candidate options visible in the source text,
the current status, and the authority that (may have) ruled.

Non-authority guarantees (the point of this module)
---------------------------------------------------
1. A ``PROPOSED`` record has **no** authority effect whatsoever. Nothing in this
   module treats a proposal as a decision.
2. A record may only reach ``ADOPTED`` through an explicit, supplied
   ``authority_principal`` that is non-empty and **distinct from the proposer**.
   The registry cannot self-adopt: there is no code path that fills in an
   authority identity, a signature, or an attestation date on the proposer's
   behalf.
3. ``REJECTED`` and ``SUPERSEDED`` are distinct terminal-ish states and are never
   collapsed into one another or into ``PROPOSED``.
4. Every load path re-validates structure *and* content hash. A malformed,
   duplicate, hash-mismatched, or transition-illegal operation raises
   :class:`GovernanceRegistryError` — it never degrades to a warning.
5. A **machine-agent principal** (one in the reserved ``agent:`` namespace) may
   appear as ``authority_principal`` only when a valid delegation record covers
   that exact decision — see "Bounded machine-agent delegation" below. No
   delegation set means no agent authority: the default is fail-closed.

Bounded machine-agent delegation (ADR-014)
-------------------------------------------
The operator role was ratifiable only by a named human, which the repository had
no honest way to supply; see ``evidence/provenance_correction/OPERATOR_ATTESTATION.md``.
ADR-014 (``docs/adr/ADR-014-bounded-operator-delegation-to-machine-agent.md``)
therefore permits an explicitly delegated, bounded machine agent to exercise
that role for enumerated decision ids, under enumerated conditions, inside an
enumerated validity window.

What that buys, concretely, in code:

* :data:`AGENT_PRINCIPAL_PREFIX` reserves the ``agent:`` namespace **in code**,
  not in a data file, so it cannot be edited away by removing a name from a
  registry. An ``agent:`` principal is never a human and never GLM.
* :data:`RESERVED_DECISION_CLASSES` names decision ids that **no** delegation
  may ever reach — decisions that change what the architecture authority owns
  (invariant-scope extensions, gate acceptance, ADR adoption, freeze lifting).
  The check is code-level for the same reason. It is an *enumerated* set, not a
  general classifier: adding a new reserved decision is a visible, reviewable
  code edit, which is the honest limit of a mechanical rule here.
* :class:`DelegationRecord` is content-hashed. Editing a delegation in place
  breaks its pin; a change requires a new record with a new id.
* A delegation cannot be **self-issued**: ``delegating_principal`` must be
  outside the agent namespace and must differ from ``agent_principal``.

What it does **not** buy — stated plainly, because this module is otherwise
about not overstating itself:

* It does **not** authenticate anyone. It checks that a delegation exists, is
  content-hash-pinned, is un-revoked, is in-window, is scoped to the decision,
  and was not self-issued. It cannot check that a real human exists behind
  ``delegating_principal``: there is no signature, identity substrate, or
  external notarisation here. That residual already existed for *human*
  principals — a free-text name has never been proof of anything — and ADR-014
  §7 makes it explicit for agent principals instead of hiding it.
* It does not let an agent satisfy a gate that requires a GLM ruling.
* It does not make an unsigned human attestation signed.

Scope honesty (read before relying on "append-only")
----------------------------------------------------
``append()`` is the only mutator; there is no update, edit, or delete API, and
``history()`` returns every record ever accepted. That is **append-only by API
surface**, which is what this implementation actually enforces. It is **not**
append-only by cryptographic chaining, and this module does not claim to be:
there is no hash chain, no signature, and no external notarisation. A file
written directly to the JSONL path is therefore not tamper-evident here; what
such a file *can* do is (a) fail validation loudly and (b) never grant
authority on its own, because a ``PROPOSED`` record grants nothing and an
``ADOPTED`` record is only honoured when it carries a distinct authority
principal — and, for an agent principal, a valid delegation. Closing that
residual is a governance decision, not an engineering default — see
``evidence/DEFECT_REGISTER.md`` DR-002 for the analogous recorded residual in
the evaluation ledger.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

SCHEMA_VERSION = 1

#: Schema version for :class:`DelegationRecord` (separate from the decision
#: record schema; a delegation is not a decision and can never satisfy
#: ``ALLOWED_TRANSITIONS``).
DELEGATION_SCHEMA_VERSION = 1

#: Raised, never swallowed. Every failure mode is fail-closed.
STATUS_PROPOSED = "PROPOSED"
STATUS_ADOPTED = "ADOPTED"
STATUS_REJECTED = "REJECTED"
STATUS_SUPERSEDED = "SUPERSEDED"
STATUSES = (STATUS_PROPOSED, STATUS_ADOPTED, STATUS_REJECTED, STATUS_SUPERSEDED)

#: The only legal status transitions. Anything else raises.
ALLOWED_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    STATUS_PROPOSED: (STATUS_ADOPTED, STATUS_REJECTED),
    STATUS_ADOPTED: (STATUS_SUPERSEDED,),
    STATUS_REJECTED: (STATUS_SUPERSEDED,),
    STATUS_SUPERSEDED: (),
}

_MAX_TEXT = 4000
_MAX_OPTIONS = 32
_MAX_REFS = 64

# ── principal taxonomy (ADR-014 §2) ──────────────────────────────────────

#: Reserved namespace for MACHINE-AGENT principals. This is a code-level
#: structural rule, not a configurable list: an ``agent:`` principal is a
#: machine principal by definition, whatever any data file claims, and the
#: namespace cannot be edited away by removing a name from a registry.
AGENT_PRINCIPAL_PREFIX = "agent:"


def is_agent_principal(principal: Any) -> bool:
    """True iff ``principal`` is in the reserved machine-agent namespace.

    Deliberately tolerant of surrounding whitespace, because every equality
    check elsewhere in this module tolerates it too: an authority principal of
    ``"  agent:executor-v2  "`` is the same principal as ``"agent:executor-v2"``
    and must get the same treatment.
    """
    return isinstance(principal, str) and principal.strip().startswith(
        AGENT_PRINCIPAL_PREFIX)


#: Decision ids that **no** delegation may ever reach, with the reason.
#:
#: These are the decisions that change what the architecture authority owns
#: under roadmap §1.1 — an invariant's scope, a gate decision, scope control.
#: A machine-agent delegation cannot manufacture a higher-authority decision,
#: so naming one of these ids in a delegation is a hard error rather than a
#: warning, and any decision record relying on such a delegation is refused.
#:
#: This is an **enumerated** set, not a general classifier: it is enforced
#: mechanically for the ids it lists, and extending it is a visible, reviewable
#: code edit. ADR-014 §7.5 states that limit rather than overclaiming.
RESERVED_DECISION_CLASSES: Dict[str, str] = {
    "GD-2026-10-11-03": (
        "invariant-scope extension reserved to the architecture authority: "
        "component 2 extends ADR-003 INV-2/INV-3 receipt binding into the "
        "legacy weld perimeter beyond its documented closure, and no GLM "
        "ruling exists (ADR-014 §2.3, §9)"
    ),
}

#: The literal refused value for ``DelegationRecord.authority_source``. An
#: agent asserting its own authority is the exact thing the delegation model
#: exists to prevent, so it is refused by name rather than merely discouraged.
SELF_ASSERTION_SOURCE = "agent_self_assertion"


class GovernanceRegistryError(ValueError):
    """Malformed, duplicate, conflicting, or unauthorized decision operation."""


def _require_text(value: Any, field: str, *, max_len: int = _MAX_TEXT,
                  allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise GovernanceRegistryError(f"{field} must be a string, got {type(value).__name__}")
    if not allow_empty and not value.strip():
        raise GovernanceRegistryError(f"{field} must be a non-empty string")
    if len(value) > max_len:
        raise GovernanceRegistryError(f"{field} exceeds {max_len} characters")
    return value


def _require_str_tuple(value: Any, field: str, *, limit: int) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise GovernanceRegistryError(f"{field} must be a list of strings")
    if len(value) > limit:
        raise GovernanceRegistryError(f"{field} exceeds {limit} entries")
    out = []
    for item in value:
        out.append(_require_text(item, f"{field} entry", max_len=512))
    return tuple(out)


@dataclass(frozen=True)
class OperatorDecisionRecord:
    """One operator decision (or proposal for one).

    ``authority_principal`` and ``decided_at`` are **caller-supplied and never
    defaulted to a real identity**. A ``PROPOSED`` record must leave both empty;
    the registry refuses to construct one that carries them, which makes
    "pre-filled operator authority" a hard error rather than a convention.

    ``delegation_ref`` names the delegation record that authorises a
    machine-agent principal to act (ADR-014). It is **omitted from the
    canonical form entirely when empty**, which is what keeps the content hash
    of every pre-ADR-014 record bit-for-bit identical to what it was before
    this field existed. See :meth:`canonical_dict`.
    """

    decision_id: str
    topic: str
    question: str
    allowed_options: Tuple[str, ...]
    status: str
    proposer: str
    decision_text: str
    source_ref: str
    affected_gate: str
    authority_principal: str
    decided_at: str
    evidence_refs: Tuple[str, ...]
    delegation_ref: str = ""
    schema_version: int = SCHEMA_VERSION

    # ── validation ────────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """Validate on construction.

        Without this, a record could be built in an invalid state and only be
        caught later — and several of the rules below (a PROPOSED record may not
        carry authority; an authority must differ from the proposer) exist
        precisely so that an invalid record cannot exist at all. ``from_dict``
        re-validates as well; validation is idempotent.
        """
        self.validate()

    def validate(self) -> None:
        _require_text(self.decision_id, "decision_id", max_len=128)
        _require_text(self.topic, "topic", max_len=256)
        _require_text(self.question, "question")
        _require_text(self.proposer, "proposer")
        _require_text(self.decision_text, "decision_text")
        _require_text(self.source_ref, "source_ref")
        _require_text(self.affected_gate, "affected_gate", max_len=256)

        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            # bool is rejected explicitly: isinstance(True, int) is True in Python.
            raise GovernanceRegistryError(
                f"unsupported schema_version {self.schema_version!r}")

        if self.status not in STATUSES:
            raise GovernanceRegistryError(
                f"status must be one of {STATUSES}, got {self.status!r}")

        opts = self.allowed_options
        if not isinstance(opts, (list, tuple)) or not opts:
            raise GovernanceRegistryError("allowed_options must be a non-empty list")
        if len(opts) > _MAX_OPTIONS:
            raise GovernanceRegistryError(
                f"allowed_options exceeds {_MAX_OPTIONS} entries")
        for o in opts:
            _require_text(o, "allowed_options entry", max_len=512)
        if len(set(opts)) != len(opts):
            raise GovernanceRegistryError("allowed_options contains duplicates")

        _require_str_tuple(self.evidence_refs, "evidence_refs", limit=_MAX_REFS)

        authority = _require_text(self.authority_principal, "authority_principal",
                                  max_len=256, allow_empty=True)
        decided = _require_text(self.decided_at, "decided_at", max_len=64,
                                allow_empty=True)

        if self.status == STATUS_PROPOSED:
            # A proposal may not carry authority or an attestation date. This is
            # the single most important rule in the module: it makes
            # "pre-filled operator authority" unrepresentable rather than merely
            # discouraged.
            if authority.strip() or decided.strip():
                raise GovernanceRegistryError(
                    "a PROPOSED record must not carry authority_principal or "
                    "decided_at; those are supplied only by the ratifying authority")
            if self.delegation_ref.strip():
                # A proposal names nothing it has not been given: pointing at a
                # delegation before there is a ruling would let a delegation
                # appear to pre-authorize a proposal that does not yet exist.
                raise GovernanceRegistryError(
                    "a PROPOSED record must not carry delegation_ref; a "
                    "delegation authorises a ruling, never a proposal")
        else:
            # Ruled states require a named, distinct authority. Whitespace does
            # not count as a name.
            if not authority.strip():
                raise GovernanceRegistryError(
                    f"status {self.status!r} requires a non-empty authority_principal")
            if not decided.strip():
                raise GovernanceRegistryError(
                    f"status {self.status!r} requires decided_at")
            if authority.strip() == self.proposer.strip():
                raise GovernanceRegistryError(
                    "authority_principal must be distinct from the proposer; "
                    "a decision cannot be self-adopted")

            if is_agent_principal(authority):
                # Structural floor only. Whether the delegation actually
                # covers *this* decision, *now*, is decided by
                # GovernanceRegistry._check_agent_authority, which needs the
                # delegation set and therefore cannot run at construction.
                if not self.delegation_ref.strip():
                    raise GovernanceRegistryError(
                        f"machine-agent authority_principal {authority!r} requires "
                        "a delegation_ref naming the delegation record that "
                        "authorises it (ADR-014); a bare agent name in "
                        "authority_principal is never sufficient")
                _require_text(self.delegation_ref, "delegation_ref", max_len=128)
            elif self.delegation_ref.strip():
                # One delegation per principal: a human record must not borrow
                # an agent delegation's authority, or an agent record must not
                # point at one that does not name it.
                raise GovernanceRegistryError(
                    "delegation_ref may only be carried by a machine-agent "
                    f"authority_principal; {authority!r} is not in the "
                    f"{AGENT_PRINCIPAL_PREFIX!r} namespace")

    # ── deterministic serialization + identity ──────────────────────────

    def canonical_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "affected_gate": self.affected_gate,
            "allowed_options": list(self.allowed_options),
            "authority_principal": self.authority_principal,
            "decided_at": self.decided_at,
            "decision_id": self.decision_id,
            "decision_text": self.decision_text,
            "evidence_refs": list(self.evidence_refs),
            "proposer": self.proposer,
            "question": self.question,
            "schema_version": self.schema_version,
            "source_ref": self.source_ref,
            "status": self.status,
            "topic": self.topic,
        }
        if self.delegation_ref.strip():
            # Omitted when empty so that every record written before ADR-014
            # still hashes to exactly the digest it was committed with. Adding
            # `"delegation_ref": ""` here would silently re-hash all of ledger
            # history and break the provenance this workstream exists to keep.
            payload["delegation_ref"] = self.delegation_ref
        return payload

    def content_hash(self) -> str:
        canonical = json.dumps(self.canonical_dict(), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperatorDecisionRecord":
        if not isinstance(data, dict):
            raise GovernanceRegistryError("record must be a JSON object")
        allowed_keys = set(cls.__dataclass_fields__) | {"content_hash"}
        unknown = set(data) - allowed_keys
        if unknown:
            raise GovernanceRegistryError(
                f"record has unknown field(s): {sorted(unknown)}")
        required = {"decision_id", "topic", "question", "allowed_options", "status",
                    "proposer", "decision_text", "source_ref", "affected_gate",
                    "authority_principal", "decided_at", "evidence_refs"}
        missing = required - set(data)
        if missing:
            raise GovernanceRegistryError(
                f"record missing required field(s): {sorted(missing)}")
        declared = data.get("content_hash")
        record = cls(
            decision_id=data["decision_id"], topic=data["topic"],
            question=data["question"],
            allowed_options=tuple(data["allowed_options"]),
            status=data["status"], proposer=data["proposer"],
            decision_text=data["decision_text"], source_ref=data["source_ref"],
            affected_gate=data["affected_gate"],
            authority_principal=data["authority_principal"],
            decided_at=data["decided_at"],
            evidence_refs=tuple(data["evidence_refs"]),
            delegation_ref=data.get("delegation_ref", ""),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
        record.validate()
        actual = record.content_hash()
        if declared is not None and declared != actual:
            raise GovernanceRegistryError(
                f"content_hash mismatch for {record.decision_id!r}: declared "
                f"{declared!r}, content hashes to {actual!r} — the same decision "
                "identity may never refer to different content")
        return record

    # ── authority projection ─────────────────────────────────────────────

    def is_authoritative(self) -> bool:
        """True only for a ruled record with a distinct named authority.

        ``PROPOSED`` is never authoritative. This is the property every caller
        should use instead of inspecting ``status`` directly.
        """
        return self.status == STATUS_ADOPTED and bool(self.authority_principal.strip())


def _parse_instant(value: Any, field: str) -> datetime:
    """Parse an ISO-8601 instant, requiring an explicit UTC offset.

    A naive timestamp is refused rather than assumed-UTC: ``decided_at`` and the
    delegation window are compared against each other, and silently guessing an
    offset would let a window be widened or missed by hours depending on where
    the reader's machine happens to be.
    """
    text = _require_text(value, field, max_len=64)
    normalized = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise GovernanceRegistryError(
            f"{field} must be an ISO-8601 instant, got {value!r}") from None
    if parsed.tzinfo is None:
        raise GovernanceRegistryError(
            f"{field} must carry an explicit UTC offset (e.g. "
            f"'2026-10-11T12:33:15Z'), got {value!r}")
    return parsed


def _parse_transition(token: str) -> Tuple[str, str]:
    from_status, sep, to_status = token.partition("->")
    if not sep or from_status not in STATUSES or to_status not in STATUSES:
        raise GovernanceRegistryError(
            f"permitted_transitions entry {token!r} must be 'FROM->TO' with both "
            f"statuses drawn from {list(STATUSES)}")
    return from_status, to_status


@dataclass(frozen=True)
class DelegationRecord:
    """A bounded, explicit delegation of the operator role to a machine agent.

    ADR-014 §3. This is **not** a decision record: it can never satisfy
    ``ALLOWED_TRANSITIONS``, it is never returned by
    :meth:`GovernanceRegistry.authoritative`, and appending it to a ledger is not
    possible — it lives in a separate set that only ever *authorises*.

    The four properties that make this more than a comment:

    1. **Non-self-issuance.** ``delegating_principal`` must be outside the
       ``agent:`` namespace and must differ from ``agent_principal``. An agent
       cannot manufacture the principal that delegated to it.
    2. **Enumerated scope.** Only ``scope_decision_ids`` may act under it, and
       only the transitions listed in ``permitted_transitions``.
    3. **Validity window.** ``effective_from <= decided_at <= expires_at``.
    4. **Content-hashed.** Editing a delegation in place changes its digest and
       breaks the pin on the next load; a change requires a new record with a
       new id, so delegation history is as auditable as decision history.

    What it is **not**: proof that a human exists behind
    ``delegating_principal``. There is no signature or identity substrate here,
    and this class does not pretend otherwise — see ADR-014 §7 and
    ``verification_status`` below.
    """

    delegation_id: str
    agent_principal: str
    delegating_principal: str
    authority_source: str
    scope_decision_ids: Tuple[str, ...]
    permitted_transitions: Tuple[str, ...]
    effective_from: str
    expires_at: str
    revoked: bool
    authored_by: str
    verification_status: str
    decision: str
    evidence_refs: Tuple[str, ...]
    authority_source_detail: str = ""
    delegating_principal_note: str = ""
    verification_note: str = ""
    revocation_procedure: str = ""
    completion_condition: str = ""
    reserved_and_excluded: str = ""
    schema_version: int = DELEGATION_SCHEMA_VERSION

    # ── validation ────────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _require_text(self.delegation_id, "delegation_id", max_len=128)
        _require_text(self.agent_principal, "agent_principal", max_len=256)
        _require_text(self.delegating_principal, "delegating_principal", max_len=256)
        _require_text(self.authority_source, "authority_source", max_len=256)
        _require_text(self.authored_by, "authored_by", max_len=256)
        _require_text(self.verification_status, "verification_status", max_len=128)
        _require_text(self.decision, "decision")

        if type(self.schema_version) is not int or \
                self.schema_version != DELEGATION_SCHEMA_VERSION:
            raise GovernanceRegistryError(
                f"unsupported delegation schema_version {self.schema_version!r}")

        if type(self.revoked) is not bool:
            # bool is checked exactly: isinstance(True, int) is True in Python.
            raise GovernanceRegistryError(
                f"revoked must be a bool, got {type(self.revoked).__name__}")

        # ── anti-self-delegation (ADR-014 §3, the load-bearing rule) ──
        if not is_agent_principal(self.agent_principal):
            raise GovernanceRegistryError(
                f"agent_principal {self.agent_principal!r} must be in the "
                f"{AGENT_PRINCIPAL_PREFIX!r} namespace; a delegation to a human "
                "principal is not this mechanism and must not borrow its rules")
        if is_agent_principal(self.delegating_principal):
            raise GovernanceRegistryError(
                f"delegating_principal {self.delegating_principal!r} is itself a "
                "machine-agent principal; a delegation cannot be issued by an "
                "agent — that is delegation laundering, not delegation "
                "(ADR-014 §3)")
        if self.delegating_principal.strip() == self.agent_principal.strip():
            raise GovernanceRegistryError(
                "delegating_principal must differ from agent_principal")
        if self.authority_source.strip() == SELF_ASSERTION_SOURCE:
            raise GovernanceRegistryError(
                f"authority_source {SELF_ASSERTION_SOURCE!r} is refused: an agent "
                "may not establish its own authority by asserting it")

        scope = self.scope_decision_ids
        if not isinstance(scope, (list, tuple)) or not scope:
            raise GovernanceRegistryError(
                "scope_decision_ids must be a non-empty list; a delegation with "
                "no enumerated scope would be a global grant")
        if len(scope) > _MAX_OPTIONS:
            raise GovernanceRegistryError(
                f"scope_decision_ids exceeds {_MAX_OPTIONS} entries")
        for entry in scope:
            _require_text(entry, "scope_decision_ids entry", max_len=128)
        if len(set(scope)) != len(scope):
            raise GovernanceRegistryError("scope_decision_ids contains duplicates")

        transitions = self.permitted_transitions
        if not isinstance(transitions, (list, tuple)) or not transitions:
            raise GovernanceRegistryError(
                "permitted_transitions must be a non-empty list")
        for token in transitions:
            _parse_transition(_require_text(
                token, "permitted_transitions entry", max_len=128))

        start = _parse_instant(self.effective_from, "effective_from")
        end = _parse_instant(self.expires_at, "expires_at")
        if end <= start:
            raise GovernanceRegistryError(
                "expires_at must be strictly after effective_from; an already "
                "expired or inverted window authorises nothing")

        _require_str_tuple(self.evidence_refs, "evidence_refs", limit=_MAX_REFS)

        for name in ("authority_source_detail", "delegating_principal_note",
                     "verification_note", "revocation_procedure",
                     "completion_condition", "reserved_and_excluded"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise GovernanceRegistryError(f"{name} must be a string")
            if len(value) > _MAX_TEXT:
                raise GovernanceRegistryError(f"{name} exceeds {_MAX_TEXT} characters")

        reserved = [d for d in scope if d in RESERVED_DECISION_CLASSES]
        if reserved:
            reasons = "; ".join(
                f"{d}: {RESERVED_DECISION_CLASSES[d]}" for d in reserved)
            raise GovernanceRegistryError(
                f"delegation {self.delegation_id!r} names reserved decision "
                f"class(es) {reserved}, which no delegation may reach: {reasons}. "
                "A delegation cannot manufacture a higher-authority decision "
                "(ADR-014 §2.3)")

    # ── deterministic serialization + identity ──────────────────────────

    def canonical_dict(self) -> Dict[str, Any]:
        # Every field that bears on authority MUST be covered by the content
        # hash: agent_principal above all, because a hash that did not cover it
        # would let the recipient of a delegation be swapped without breaking
        # the pin.
        return {
            "agent_principal": self.agent_principal,
            "authority_source": self.authority_source,
            "authority_source_detail": self.authority_source_detail,
            "authored_by": self.authored_by,
            "completion_condition": self.completion_condition,
            "decision": self.decision,
            "delegating_principal": self.delegating_principal,
            "delegating_principal_note": self.delegating_principal_note,
            "delegation_id": self.delegation_id,
            "effective_from": self.effective_from,
            "evidence_refs": list(self.evidence_refs),
            "expires_at": self.expires_at,
            "permitted_transitions": list(self.permitted_transitions),
            "reserved_and_excluded": self.reserved_and_excluded,
            "revocation_procedure": self.revocation_procedure,
            "revoked": self.revoked,
            "scope_decision_ids": list(self.scope_decision_ids),
            "schema_version": self.schema_version,
            "verification_note": self.verification_note,
            "verification_status": self.verification_status,
        }

    def content_hash(self) -> str:
        canonical = json.dumps(self.canonical_dict(), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelegationRecord":
        if not isinstance(data, dict):
            raise GovernanceRegistryError("delegation must be a JSON object")
        allowed_keys = set(cls.__dataclass_fields__) | {"content_hash"}
        unknown = set(data) - allowed_keys
        if unknown:
            raise GovernanceRegistryError(
                f"delegation has unknown field(s): {sorted(unknown)}")
        required = {"delegation_id", "agent_principal", "delegating_principal",
                    "authority_source", "scope_decision_ids",
                    "permitted_transitions", "effective_from", "expires_at",
                    "revoked", "authored_by", "verification_status", "decision",
                    "evidence_refs"}
        missing = required - set(data)
        if missing:
            raise GovernanceRegistryError(
                f"delegation missing required field(s): {sorted(missing)}")

        declared = data.get("content_hash")
        record = cls(
            delegation_id=data["delegation_id"],
            agent_principal=data["agent_principal"],
            delegating_principal=data["delegating_principal"],
            authority_source=data["authority_source"],
            scope_decision_ids=tuple(data["scope_decision_ids"]),
            permitted_transitions=tuple(data["permitted_transitions"]),
            effective_from=data["effective_from"],
            expires_at=data["expires_at"],
            revoked=data["revoked"],
            authored_by=data["authored_by"],
            verification_status=data["verification_status"],
            decision=data["decision"],
            evidence_refs=tuple(data["evidence_refs"]),
            authority_source_detail=data.get("authority_source_detail", ""),
            delegating_principal_note=data.get("delegating_principal_note", ""),
            verification_note=data.get("verification_note", ""),
            revocation_procedure=data.get("revocation_procedure", ""),
            completion_condition=data.get("completion_condition", ""),
            reserved_and_excluded=data.get("reserved_and_excluded", ""),
            schema_version=data.get("schema_version", DELEGATION_SCHEMA_VERSION),
        )
        record.validate()
        actual = record.content_hash()
        if declared is not None and declared != actual:
            raise GovernanceRegistryError(
                f"content_hash mismatch for delegation {record.delegation_id!r}: "
                f"declared {declared!r}, content hashes to {actual!r} — a "
                "delegation cannot be edited in place; issue a new record with a "
                "new id (ADR-014 §5)")
        return record

    # ── scope predicates ─────────────────────────────────────────────────

    def covers(self, decision_id: str) -> bool:
        return decision_id in self.scope_decision_ids

    def permits_transition(self, from_status: str, to_status: str) -> bool:
        return (from_status, to_status) in {
            _parse_transition(t) for t in self.permitted_transitions}

    def in_window(self, instant: str) -> bool:
        moment = _parse_instant(instant, "decided_at")
        return (_parse_instant(self.effective_from, "effective_from") <= moment
                <= _parse_instant(self.expires_at, "expires_at"))


class GovernanceRegistry:
    """In-memory decision ledger with an append-only API surface.

    Not thread-safe by design: mutation is expected to be a deliberate,
    reviewable act, not a concurrent process.

    ``delegations`` is the set of :class:`DelegationRecord` objects that may
    authorise a machine-agent principal (ADR-014). It defaults to **empty**, and
    empty means fail-closed: an ``agent:``-principal decision is refused unless a
    matching delegation is supplied. A caller that forgets to pass delegations
    gets no agent authority, not accidental agent authority.
    """

    def __init__(self, records: Optional[Iterable[OperatorDecisionRecord]] = None,
                 delegations: Optional[Iterable[DelegationRecord]] = None) -> None:
        self._records: List[OperatorDecisionRecord] = []
        self._delegations: Dict[str, DelegationRecord] = {}
        for delegation in (delegations or ()):
            if not isinstance(delegation, DelegationRecord):
                raise GovernanceRegistryError(
                    f"delegations expects DelegationRecord objects, got "
                    f"{type(delegation).__name__}")
            if delegation.delegation_id in self._delegations:
                raise GovernanceRegistryError(
                    f"duplicate delegation_id {delegation.delegation_id!r}")
            self._delegations[delegation.delegation_id] = delegation
        if records is not None:
            for record in records:
                self.append(record)

    def delegations(self) -> Tuple[DelegationRecord, ...]:
        """Every delegation loaded into this registry, in insertion order."""
        return tuple(self._delegations.values())

    # ── read ─────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._records)

    def history(self) -> Tuple[OperatorDecisionRecord, ...]:
        """Every record ever accepted, in append order. Never truncated.

        A decision's lifecycle is represented by successive records sharing one
        ``decision_id``; each of them stays here in its original form. Nothing is
        ever rewritten or removed.
        """
        return tuple(self._records)

    def versions(self, decision_id: str) -> Tuple[OperatorDecisionRecord, ...]:
        """Every record for one decision id, oldest first."""
        return tuple(r for r in self._records if r.decision_id == decision_id)

    def get(self, decision_id: str) -> Optional[OperatorDecisionRecord]:
        """The **current** record for a decision id (the most recent version)."""
        found: Optional[OperatorDecisionRecord] = None
        for record in self._records:
            if record.decision_id == decision_id:
                found = record
        return found

    def authoritative(self) -> Tuple[OperatorDecisionRecord, ...]:
        """Only records that carry real authority. PROPOSED records never appear.

        A decision id can hold at most one authoritative version, because
        ``ADOPTED -> ADOPTED`` is not a legal transition.
        """
        return tuple(r for r in self._records if r.is_authoritative())

    def proposed(self) -> Tuple[OperatorDecisionRecord, ...]:
        """Current-state records that are still awaiting a ruling."""
        current = {}
        for record in self._records:
            current[record.decision_id] = record
        return tuple(r for r in current.values() if r.status == STATUS_PROPOSED)

    # ── write (append only) ──────────────────────────────────────────────

    def append(self, record: OperatorDecisionRecord) -> OperatorDecisionRecord:
        """Append a record. This is the only mutator; there is no edit or delete.

        Lifecycle model: one real-world decision is one ``decision_id``; each
        state change appends a *new* record under that id rather than mutating
        the previous one. The previous version therefore remains intact in
        :meth:`history` with its original content hash.
        """
        if not isinstance(record, OperatorDecisionRecord):
            raise GovernanceRegistryError(
                f"append expects an OperatorDecisionRecord, got "
                f"{type(record).__name__}")
        record.validate()

        prior = self.get(record.decision_id)
        if prior is None:
            if record.status != STATUS_PROPOSED:
                raise GovernanceRegistryError(
                    f"decision {record.decision_id!r} entered at status "
                    f"{record.status!r} with no prior PROPOSED record; the ledger "
                    "requires the proposal to be visible before it is ruled on")
            self._records.append(record)
            return record

        if prior.content_hash() == record.content_hash():
            raise GovernanceRegistryError(
                f"duplicate decision_id {record.decision_id!r}: an identical "
                "record is already present (append-only; duplicates refused)")

        allowed = ALLOWED_TRANSITIONS[prior.status]
        if record.status not in allowed:
            raise GovernanceRegistryError(
                f"illegal transition for {record.decision_id!r}: "
                f"{prior.status} -> {record.status} is not permitted "
                f"(allowed from {prior.status}: {list(allowed)}). History is "
                "never rewritten.")

        # After the structural checks and before the record is accepted: a
        # machine-agent principal must be authorised *for this decision, by this
        # transition, at this instant*.
        if is_agent_principal(record.authority_principal):
            self._check_agent_authority(record, prior.status)

        self._records.append(record)
        return record

    # ── machine-agent authorisation (ADR-014 §3.1) ──────────────────────

    def _check_agent_authority(self, record: OperatorDecisionRecord,
                               from_status: str) -> None:
        """Fail closed unless a valid delegation authorises ``record``.

        Every branch raises. There is no warn-and-continue path and no default
        allow: the only way an ``agent:`` principal reaches ``ADOPTED`` is
        through all ten checks below.
        """
        ref = record.delegation_ref.strip()
        if not ref:
            raise GovernanceRegistryError(
                f"decision {record.decision_id!r} claims machine-agent authority "
                f"{record.authority_principal!r} but carries no delegation_ref")

        delegation = self._delegations.get(ref)
        if delegation is None:
            known = sorted(self._delegations) or ["<none loaded>"]
            raise GovernanceRegistryError(
                f"decision {record.decision_id!r} references delegation {ref!r}, "
                f"which is not loaded into this registry (known: {known}). "
                "Machine-agent authority is fail-closed: load the delegation "
                "record explicitly (ADR-014 §3.1)")

        if delegation.agent_principal.strip() != record.authority_principal.strip():
            raise GovernanceRegistryError(
                f"delegation {ref!r} is issued to "
                f"{delegation.agent_principal!r}, not to "
                f"{record.authority_principal!r}; a delegation cannot be borrowed")

        if record.decision_id in RESERVED_DECISION_CLASSES:
            raise GovernanceRegistryError(
                f"decision {record.decision_id!r} is a reserved decision class "
                f"({RESERVED_DECISION_CLASSES[record.decision_id]}). No machine-"
                "agent delegation may reach it, and a machine-agent principal "
                "can never satisfy a gate reserved to the architecture authority "
                "(ADR-014 §2.3)")

        if not delegation.covers(record.decision_id):
            raise GovernanceRegistryError(
                f"delegation {ref!r} does not cover decision "
                f"{record.decision_id!r} (scope: "
                f"{list(delegation.scope_decision_ids)})")

        if delegation.revoked:
            raise GovernanceRegistryError(
                f"delegation {ref!r} is revoked and authorises nothing")

        if not delegation.permits_transition(from_status, record.status):
            raise GovernanceRegistryError(
                f"delegation {ref!r} does not permit {from_status} -> "
                f"{record.status} (permitted: "
                f"{list(delegation.permitted_transitions)})")

        if not delegation.in_window(record.decided_at):
            raise GovernanceRegistryError(
                f"decision {record.decision_id!r} decided_at={record.decided_at!r} "
                f"is outside delegation {ref!r}'s validity window "
                f"[{delegation.effective_from}, {delegation.expires_at}]")

        if delegation.agent_principal.strip() == record.proposer.strip():
            raise GovernanceRegistryError(
                f"decision {record.decision_id!r} was proposed by the agent that "
                "now claims to rule on it")

    def supersede(self, decision_id: str, *, successor_id: str,
                  authority_principal: str, decided_at: str,
                  reason: str,
                  delegation_ref: str = "") -> OperatorDecisionRecord:
        """Retire a decision by appending a ``SUPERSEDED`` version of it.

        The earlier versions are **not** modified — they stay in ``history()``
        with their original status and content hash. This appends a new version
        under the same ``decision_id`` whose status is ``SUPERSEDED`` (a legal
        transition from the current state), naming the successor decision.

        Retiring via the status transition — rather than via a side table — is
        what makes a second supersede attempt detectable: ``SUPERSEDED`` has no
        outgoing transitions, so the attempt fails the same way any other
        illegal transition does.
        """
        _require_text(successor_id, "successor_id", max_len=128)
        _require_text(authority_principal, "authority_principal", max_len=256)
        _require_text(decided_at, "decided_at", max_len=64)
        _require_text(reason, "reason")

        target = self.get(decision_id)
        if target is None:
            raise GovernanceRegistryError(f"unknown decision_id {decision_id!r}")
        if target.status not in ALLOWED_TRANSITIONS or \
                STATUS_SUPERSEDED not in ALLOWED_TRANSITIONS[target.status]:
            raise GovernanceRegistryError(
                f"decision {decision_id!r} is in status {target.status!r}, from "
                "which superseding is not permitted")
        if authority_principal.strip() == target.proposer.strip():
            raise GovernanceRegistryError(
                "authority_principal must be distinct from the original proposer")
        if successor_id == decision_id:
            raise GovernanceRegistryError(
                "successor_id must differ from the decision being superseded")
        if successor_id in {r.decision_id for r in self._records}:
            raise GovernanceRegistryError(
                f"successor_id {successor_id!r} already exists in the ledger")

        marker = OperatorDecisionRecord(
            decision_id=target.decision_id,
            topic=target.topic,
            question=target.question,
            allowed_options=target.allowed_options,
            status=STATUS_SUPERSEDED,
            proposer=target.proposer,
            decision_text=(
                f"SUPERSEDES prior version of {target.decision_id}: {reason}. "
                f"Successor decision: {successor_id}. The superseded versions "
                "remain in history with their original status and hash."),
            source_ref=target.source_ref,
            affected_gate=target.affected_gate,
            authority_principal=authority_principal,
            decided_at=decided_at,
            evidence_refs=target.evidence_refs,
            # An agent principal must present its own delegation, exactly as it
            # would for any other ruling; it cannot ride on the target's.
            delegation_ref=delegation_ref,
        )
        # Routed through append() rather than self._records so that the
        # machine-agent authorisation check runs here too. Appending directly
        # would be a way to add a SUPERSEDED record — which is a ruled state,
        # and therefore an authority act — while skipping that check.
        self.append(marker)
        return marker

    # ── audit export / import ────────────────────────────────────────────

    def to_jsonl(self) -> str:
        return "".join(
            json.dumps(r.to_dict(), sort_keys=True, ensure_ascii=True) + "\n"
            for r in self._records)

    @classmethod
    def from_jsonl(cls, text: str,
                   delegations: Optional[Iterable[DelegationRecord]] = None
                   ) -> "GovernanceRegistry":
        """Re-import a JSONL export.

        Every line is re-validated, its content hash re-derived, and its
        lifecycle transition re-checked by replaying it through the same
        :meth:`append` path used for live writes. A line that fails any check
        aborts the whole import rather than being skipped: a partially-imported
        ledger is exactly the state this module exists to prevent. Records enter
        at their recorded status; a ``PROPOSED`` line still grants nothing after
        import.

        ``delegations`` must be supplied for a ledger that contains any
        machine-agent ruling. Omitting it does **not** skip the check — it makes
        the import fail, because an ``agent:`` principal with no loaded
        delegation has no authority (ADR-014 §3.1).
        """
        if not isinstance(text, str):
            raise GovernanceRegistryError("from_jsonl expects text")
        registry = cls(delegations=delegations)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GovernanceRegistryError(
                    f"line {lineno} is not valid JSON: {exc}") from None
            try:
                record = OperatorDecisionRecord.from_dict(payload)
            except GovernanceRegistryError as exc:
                raise GovernanceRegistryError(f"line {lineno}: {exc}") from None
            try:
                registry.append(record)
            except GovernanceRegistryError as exc:
                raise GovernanceRegistryError(f"line {lineno}: {exc}") from None
        return registry

    @classmethod
    def load_delegations(cls, data: Mapping[str, Any]
                         ) -> Tuple[DelegationRecord, ...]:
        """Parse a delegation artifact (a JSON object, or a list of them).

        Each entry is fully validated and its content hash re-derived and
        compared, so a hand-edited or tampered delegation is refused at load
        rather than at first use.
        """
        if isinstance(data, dict):
            payload: Any = data
        elif isinstance(data, list):
            payload = data
        else:
            raise GovernanceRegistryError(
                "delegation artifact must be a JSON object or a list of objects")
        items = payload if isinstance(payload, list) else [payload]
        out: List[DelegationRecord] = []
        seen = set()
        for index, item in enumerate(items):
            try:
                record = DelegationRecord.from_dict(item)
            except GovernanceRegistryError as exc:
                raise GovernanceRegistryError(
                    f"delegation entry {index}: {exc}") from None
            if record.delegation_id in seen:
                raise GovernanceRegistryError(
                    f"duplicate delegation_id {record.delegation_id!r}")
            seen.add(record.delegation_id)
            out.append(record)
        return tuple(out)
