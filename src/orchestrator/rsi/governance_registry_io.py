"""governance_registry_io.py — read-only loading of the governance registry (G1).

Purpose
-------
The independent audit classified the governance registry as ``DORMANT``: it had
no production consumer, so nothing in the runtime could observe what the ledger
actually says. G1 makes it **inspectable** — nothing more.

This module is the single reusable entry point for reading governance state from
disk. It resolves the ledger, delegation record and trusted-issuer store relative
to an explicitly supplied repository root, parses each through the canonical
registry implementation, and returns the inspectable registry together with a
structured account of what could not be authorised.

What this module is NOT
-----------------------
It is **observational only**. It:

* never appends, updates, invalidates, adopts, or otherwise mutates a decision;
* never writes, repairs, or reformats JSONL;
* never populates the trusted-issuer store or generates a delegation;
* never changes policy or capability configuration;
* never triggers an action or makes a network request.

No production authorization decision may depend on its result. A caller that
wants to *enforce* something must go through the canonical Broker/PEP path
(``src/orchestrator/brain/capability_broker.py`` and friends), which G1 leaves
untouched. Reading governance status authorises nothing.

Loading versus authorising
--------------------------
These are kept deliberately separate, because conflating them is what made the
registry untrustworthy in the first place:

* **Loading** reads the ledger into memory. A *valid historical* ledger whose
  delegation evidence cannot be independently verified still loads — otherwise
  the record of an unauthorised adoption would become unauditable, which is the
  opposite of what an audit trail is for.
* **Authorising** is what :meth:`GovernanceRegistry.effective_authoritative`
  computes. It re-runs the full delegation and trust-store checks and returns
  nothing when those checks fail.

An **invalid** artifact (missing, unreadable, malformed, hash-inconsistent) is a
different thing again, and is always a hard error: :class:`GovernanceLoadError`
is raised rather than an empty registry being substituted. The status surface
distinguishes these two states rather than conflating "failed" with "no
authority".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from orchestrator.rsi.governance_registry import (
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
)

__all__ = [
    "GovernanceLoadError",
    "GovernanceSnapshot",
    "load_ledger",
    "LEDGER_RELPATH",
    "DELEGATION_RELPATH",
    "TRUST_STORE_RELPATH",
]

#: Repository-relative locations of the three governance artifacts.
LEDGER_RELPATH = Path("evidence") / "GOVERNANCE_DECISIONS_20261009.jsonl"
DELEGATION_RELPATH = Path("evidence/governance/EXECUTOR_DELEGATION_20261011.json")
TRUST_STORE_RELPATH = Path("evidence/governance/TRUSTED_ISSUERS.json")

#: Reported verbatim by the status surface so the authentication limitation is
#: visible wherever governance state is inspected, not buried in an ADR.
AUTHENTICATION_LIMITATION = (
    "Independent issuer authentication is NOT available. "
    "evidence/governance/TRUSTED_ISSUERS.json is an empty list: this repository "
    "has no signature substrate, no identity provider, and no trust root. "
    "TrustedIssuer.validate() checks structure only - it does not authenticate a "
    "person, verify a signature, establish a trusted key, or confirm that "
    "evidence_refs targets exist. A content hash shows consistency with the "
    "hashed data, not who created or authorised it. Listing an issuer in the "
    "store is therefore a CLAIM, not authentication, and audit finding F2 "
    "(arbitrary-issuer authority minting) is not fully closed."
)

#: Emphasised by the status surface: observation confers nothing.
OBSERVATION_DISCLAIMER = (
    "Reading governance status is OBSERVATIONAL ONLY and authorises no action. "
    "G1 introduces no enforcement path, no capability grant, and no new "
    "decision authority. The production Broker/PEP path is unchanged."
)


class GovernanceLoadError(RuntimeError):
    """A required governance artifact is missing, unreadable, or invalid.

    Raised instead of returning an empty registry. A caller must never be able
    to mistake "the governance state could not be read" for "the governance
    state grants nothing" — the two demand different responses.
    """

    def __init__(self, message: str, *, path: Optional[Path] = None,
                 cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.path = path
        self.cause = cause

    def with_path(self, path: Path) -> "GovernanceLoadError":
        return GovernanceLoadError(
            f"{self.args[0]} (artifact: {path})", path=path, cause=self.cause)


@dataclass(frozen=True)
class GovernanceSnapshot:
    """Everything a read-only consumer needs to inspect governance state.

    ``registry`` is the live, canonical
    :class:`~orchestrator.rsi.governance_registry.GovernanceRegistry`. Every
    count below is derived from it — nothing here is hardcoded, so this stays
    truthful as the ledger evolves.
    """

    repo_root: Path
    ledger_path: Path
    delegation_path: Optional[Path]
    trust_store_path: Optional[Path]

    registry: GovernanceRegistry
    delegations: Tuple[DelegationRecord, ...]
    trusted_issuers: Tuple[TrustedIssuer, ...]

    #: ``(decision_id, status, reason)`` for every historical record whose
    #: machine-agent authority could not be verified. Preserved, not dropped.
    unverified_authority: Tuple[Tuple[str, str, str], ...]
    #: ``decision_id -> reason`` for decisions that are structurally adopted but
    #: not effectively authorised.
    authority_problems: Mapping[str, str]

    #: Set when the delegation artifact or trust store is absent. Absence is
    #: *not* an error: an empty or missing delegation set simply withholds
    #: agent authority, and the registry is still fully readable.
    delegation_artifact_present: bool
    trust_store_artifact_present: bool

    notes: Tuple[str, ...] = field(default_factory=tuple)

    # ── derived, always computed from the registry ────────────────────

    @property
    def record_count(self) -> int:
        return len(self.registry)

    def status_counts(self) -> Dict[str, int]:
        """Current-version counts keyed by status, derived from the registry."""
        counts: Dict[str, int] = {}
        for record in self.registry.current_records():
            counts[record.status] = counts.get(record.status, 0) + 1
        return counts

    @property
    def effective_authoritative(self) -> Tuple[OperatorDecisionRecord, ...]:
        """Contextual authority, never the structural-only projection."""
        return self.registry.effective_authoritative()

    @property
    def effective_authority_count(self) -> int:
        return len(self.effective_authoritative)

    @property
    def historical_adoption_events(self) -> Tuple[OperatorDecisionRecord, ...]:
        """Every ADOPTED event ever recorded, including retracted ones.

        History, not authority: use :attr:`effective_authoritative` for that.
        """
        return self.registry.adoption_events()

    @property
    def trust_store_is_empty(self) -> bool:
        return not self.trusted_issuers

    def status_of(self, decision_id: str) -> Optional[str]:
        record = self.registry.get(decision_id)
        return record.status if record is not None else None

    def describe(self) -> str:
        """Human-readable summary used by the status surface."""
        counts = self.status_counts()
        parts = [f"records={self.record_count}"]
        for status in (STATUS_PROPOSED, STATUS_ADOPTED, STATUS_INVALIDATED,
                       STATUS_REJECTED, STATUS_SUPERSEDED):
            if status in counts:
                parts.append(f"{status.lower()}={counts[status]}")
        return "  ".join(parts)


def _read_json(path: Path, *, required: bool, label: str) -> Optional[Any]:
    """Read and parse a JSON artifact. Never writes, never repairs."""
    if not path.is_file():
        if required:
            raise GovernanceLoadError(
                f"required {label} artifact is missing", path=path)
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GovernanceLoadError(
            f"{label} artifact could not be read: {exc}", path=path,
            cause=exc) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GovernanceLoadError(
            f"{label} artifact is not valid JSON: {exc}", path=path,
            cause=exc) from exc


def _extract_store_list(payload: Any, path: Path, label: str,
                        *keys: str) -> Any:
    """Pull the issuer list out of a store artifact without guessing its shape."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                value = payload[key]
                if not isinstance(value, list):
                    raise GovernanceLoadError(
                        f"{label} artifact field {key!r} must be a JSON array",
                        path=path)
                return value
        raise GovernanceLoadError(
            f"{label} artifact has no issuer array "
            f"(expected one of {list(keys)})", path=path)
    raise GovernanceLoadError(
        f"{label} artifact must be a JSON object or array", path=path)


def load_ledger(repo_root: Any) -> GovernanceSnapshot:
    """Load the governance ledger, delegations and trusted issuers, read-only.

    ``repo_root`` is required and explicit — there is no default and no
    search-up-the-tree, so a caller can never accidentally load a different
    repository's governance state.

    Fails closed: a missing, unreadable, malformed or hash-inconsistent
    *required* artifact raises :class:`GovernanceLoadError`. The delegation
    record and the trusted-issuer store are optional, because their absence is
    itself meaningful governance state (it withholds agent authority) and
    because a ledger without them must still be auditable.

    Never mutates anything on disk.
    """
    root = Path(repo_root).expanduser()
    if not root.is_dir():
        raise GovernanceLoadError(
            f"repository root is not a directory: {root}", path=root)

    ledger_path = root / LEDGER_RELPATH
    delegation_path = root / DELEGATION_RELPATH
    trust_store_path = root / TRUST_STORE_RELPATH

    # ── required: the ledger ───────────────────────────────────────────
    if not ledger_path.is_file():
        raise GovernanceLoadError(
            "required decision ledger is missing", path=ledger_path)
    try:
        ledger_text = ledger_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GovernanceLoadError(
            f"decision ledger could not be read: {exc}", path=ledger_path,
            cause=exc) from exc

    # ── optional: delegations ─────────────────────────────────────────
    delegations: Tuple[DelegationRecord, ...] = ()
    delegation_present = delegation_path.is_file()
    notes: List[str] = []
    if delegation_present:
        payload = _read_json(delegation_path, required=True,
                             label="delegation record")
        try:
            delegations = GovernanceRegistry.load_delegations(payload)
        except GovernanceRegistryError as exc:
            raise GovernanceLoadError(
                f"delegation record is invalid: {exc}", path=delegation_path,
                cause=exc) from exc
    else:
        notes.append(
            f"no delegation record at {delegation_path.relative_to(root)}; "
            "machine-agent authority is therefore withheld (absence is normal, "
            "not an error)")

    # ── optional: trusted issuers ─────────────────────────────────────
    trusted: Tuple[TrustedIssuer, ...] = ()
    trust_present = trust_store_path.is_file()
    if trust_present:
        payload = _read_json(trust_store_path, required=True,
                             label="trusted-issuer store")
        entries = _extract_store_list(payload, trust_store_path,
                                      "trusted-issuer store",
                                      "trusted_issuers", "issuers")
        try:
            trusted = GovernanceRegistry.load_trusted_issuers(entries)
        except GovernanceRegistryError as exc:
            raise GovernanceLoadError(
                f"trusted-issuer store is invalid: {exc}",
                path=trust_store_path, cause=exc) from exc

    # ── canonical parse ───────────────────────────────────────────────
    # The registry distinguishes an invalid ledger (raises) from a valid
    # ledger whose historical authority cannot be verified (loads, and is
    # reported through unverified_authority_records / authority_problems).
    try:
        registry = GovernanceRegistry.from_jsonl(
            ledger_text, delegations=delegations, trusted_issuers=trusted)
    except GovernanceRegistryError as exc:
        raise GovernanceLoadError(
            f"decision ledger is invalid: {exc}", path=ledger_path,
            cause=exc) from exc

    faults = tuple(registry.unverified_authority_records())
    problems = dict(registry.authority_problems())
    if faults:
        notes.append(
            f"{len(faults)} historical record(s) carry machine-agent authority "
            "that could not be independently verified; they are preserved and "
            "reported, not discarded")
    if problems:
        notes.append(
            f"{len(problems)} structurally-adopted decision(s) are not "
            "effectively authorised")

    return GovernanceSnapshot(
        repo_root=root,
        ledger_path=ledger_path,
        delegation_path=delegation_path if delegation_present else None,
        trust_store_path=trust_store_path if trust_present else None,
        registry=registry,
        delegations=delegations,
        trusted_issuers=trusted,
        unverified_authority=faults,
        authority_problems=problems,
        delegation_artifact_present=delegation_present,
        trust_store_artifact_present=trust_present,
        notes=tuple(notes),
    )