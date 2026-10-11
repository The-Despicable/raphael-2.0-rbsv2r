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
principal. Closing that residual is a governance decision, not an engineering
default — see ``evidence/DEFECT_REGISTER.md`` DR-002 for the analogous recorded
residual in the evaluation ledger.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = 1

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

    # ── deterministic serialization + identity ──────────────────────────

    def canonical_dict(self) -> Dict[str, Any]:
        return {
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


class GovernanceRegistry:
    """In-memory decision ledger with an append-only API surface.

    Not thread-safe by design: mutation is expected to be a deliberate,
    reviewable act, not a concurrent process.
    """

    def __init__(self, records: Optional[Iterable[OperatorDecisionRecord]] = None) -> None:
        self._records: List[OperatorDecisionRecord] = []
        if records is not None:
            for record in records:
                self.append(record)

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
        self._records.append(record)
        return record

    def supersede(self, decision_id: str, *, successor_id: str,
                  authority_principal: str, decided_at: str,
                  reason: str) -> OperatorDecisionRecord:
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
        )
        self._records.append(marker)
        return marker

    # ── audit export / import ────────────────────────────────────────────

    def to_jsonl(self) -> str:
        return "".join(
            json.dumps(r.to_dict(), sort_keys=True, ensure_ascii=True) + "\n"
            for r in self._records)

    @classmethod
    def from_jsonl(cls, text: str) -> "GovernanceRegistry":
        """Re-import a JSONL export.

        Every line is re-validated, its content hash re-derived, and its
        lifecycle transition re-checked by replaying it through the same
        :meth:`append` path used for live writes. A line that fails any check
        aborts the whole import rather than being skipped: a partially-imported
        ledger is exactly the state this module exists to prevent. Records enter
        at their recorded status; a ``PROPOSED`` line still grants nothing after
        import.
        """
        if not isinstance(text, str):
            raise GovernanceRegistryError("from_jsonl expects text")
        registry = cls()
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
