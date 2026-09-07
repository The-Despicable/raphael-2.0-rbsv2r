"""
receipt_store.py — Durable local receipt persistence (P4.4 §15).

File-backed JSONL store for broker ActionReceipts with P4.3 mission
bindings. File writes live here because exec/ is the only package
permitted file primitives (INV-1). This store persists records; it
adjudicates nothing:

- no authorization decisions (a persisted receipt cannot allow/deny;
  the live Broker receipt_store remains the sole PDP input)
- no execution (records cannot run anything)
- no belief writes, no falsification, no replanning, no learning
- no overwrite API, no delete API (durable means durable)

Authority model: the Broker's in-memory authorization record is the
security authority. This store is a durable REPRESENTATION of that
record plus its mission traceability. Loading a receipt here never
inserts it into any Broker; _check_receipt consults only the live
Broker store, so disk state can never authorize execution.

Fail-closed rules (mirroring the §14.5 EvidenceStore convention):
- missing file -> empty store (not an error)
- malformed/corrupt/truncated lines on load -> ReceiptStoreError
  (whole load refused; no partial index)
- receipt hash mismatch on load/append -> corrupt, refused
- envelope binding mismatch (receipt <-> mission) -> corrupt, refused
- unknown schema version -> refused
- duplicate action_id + identical content -> idempotent OK
- duplicate action_id + different content -> conflict rejected
- oversized serialized record -> rejected
- more than max_records -> StoreFull rejected

One JSON object per line (canonical bytes: sort_keys, compact
separators, ensure_ascii).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from orchestrator.hardening.action_receipt import (
    ActionProposalStatus,
    ActionReceipt,
)

RECEIPT_SCHEMA_VERSION = 1
STORE_FILENAME = "receipts.jsonl"
MAX_RECORD_BYTES = 131072
MAX_RECORDS = 10000


class ReceiptStoreError(Exception):
    """Durable receipt store misuse, corruption, or capacity failure (fail-closed)."""
    pass


@dataclass(frozen=True)
class StoredReceipt:
    """A persisted receipt with its mission traceability bindings.

    Frozen data: describes a durable record; authorizes nothing.
    """
    receipt: ActionReceipt
    mission_id: str = ""
    mission_digest: str = ""
    scope_hash: str = ""


def _canonical_bytes(payload: dict) -> bytes:
    """Deterministic serialization: sorted keys, compact, ASCII."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    ).encode("utf-8")


def _receipt_from_dict(data: dict) -> ActionReceipt:
    """Strict reconstruction of an ActionReceipt (fail-closed).

    Content fields are preserved VERBATIM (no type coercion): the
    integrity hash is type-sensitive (json default=str distinguishes
    0.0 from "0.0"), so any coercion would break legitimate receipts.
    Only status (str->enum), authorized_argv (list->tuple), and
    evidence_ids (->list) are normalized, all hash-neutral under the
    canonical serialization.
    """
    if not isinstance(data, dict):
        raise ReceiptStoreError("receipt store: receipt payload must be a mapping")
    try:
        status = ActionProposalStatus(data.get("status", ""))
    except ValueError:
        raise ReceiptStoreError(
            f"receipt store: unknown receipt status {data.get('status')!r}"
        )
    argv = data.get("authorized_argv", ())
    if argv is None:
        argv = ()
    try:
        argv_tuple = tuple(argv)
    except TypeError:
        raise ReceiptStoreError("receipt store: malformed authorized_argv")
    evidence_ids = data.get("evidence_ids", [])
    if evidence_ids is None:
        evidence_ids = []
    if not isinstance(evidence_ids, list):
        raise ReceiptStoreError("receipt store: malformed evidence_ids")
    try:
        return ActionReceipt(
            schema_version=data.get("schema_version", 1),
            action_id=data.get("action_id", ""),
            proposal_hash=data.get("proposal_hash", ""),
            target=data.get("target", ""),
            capability=data.get("capability", ""),
            method=data.get("method", ""),
            impact_estimate=data.get("impact_estimate", "unknown"),
            action_type=data.get("action_type", ""),
            authorized_argv=argv_tuple,
            status=status,
            decision=data.get("decision", ""),
            reason=data.get("reason", ""),
            policy_version=data.get("policy_version", ""),
            authorized_by=data.get("authorized_by", ""),
            started_at=data.get("started_at", 0.0),
            completed_at=data.get("completed_at", 0.0),
            result=data.get("result", ""),
            evidence_ids=evidence_ids,
            prev_hash=data.get("prev_hash", ""),
            audit_hash=data.get("audit_hash", ""),
        )
    except (TypeError, ValueError, AssertionError) as exc:
        raise ReceiptStoreError(f"receipt store: malformed receipt payload: {exc}")


def _record_hash(action_id: str, mission_id: str, mission_digest: str,
                 scope_hash: str, receipt_dict: dict) -> str:
    """Bind receipt content to its mission traceability (masquerade detection)."""
    return hashlib.sha256(_canonical_bytes({
        "action_id": action_id,
        "mission_id": mission_id,
        "mission_digest": mission_digest,
        "scope_hash": scope_hash,
        "receipt": receipt_dict,
    })).hexdigest()


class ReceiptStore:
    """Append-only bounded JSONL store for broker ActionReceipts."""

    def __init__(self, path: str | Path, max_records: int = MAX_RECORDS):
        self._path = Path(path)
        self._max_records = max_records
        self._index: dict[str, StoredReceipt] = {}
        if self._path.exists():
            self._load()

    @property
    def path(self) -> Path:
        return self._path

    def __len__(self) -> int:
        return len(self._index)

    def append(self, receipt: ActionReceipt, mission_id: str = "",
               mission_digest: str = "", scope_hash: str = "") -> str:
        """Persist a receipt with mission traceability. Returns action_id.

        Fail-closed: non-receipts, integrity failures, binding
        mismatches, conflicts, oversize, and over-capacity raise
        ReceiptStoreError and persist nothing.
        """
        if not isinstance(receipt, ActionReceipt):
            raise ReceiptStoreError("receipt store: only ActionReceipt accepted")
        if not receipt.action_id:
            raise ReceiptStoreError("receipt store: receipt has no action_id")
        if not receipt.verify_integrity():
            raise ReceiptStoreError(
                f"receipt store: receipt '{receipt.action_id}' fails integrity; refused"
            )
        receipt_dict = receipt.to_dict()
        envelope = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "action_id": receipt.action_id,
            "mission_id": mission_id or "",
            "mission_digest": mission_digest or "",
            "scope_hash": scope_hash or "",
            "receipt": receipt_dict,
            "record_hash": _record_hash(
                receipt.action_id, mission_id or "", mission_digest or "",
                scope_hash or "", receipt_dict,
            ),
        }
        line = _canonical_bytes(envelope)
        if len(line) > MAX_RECORD_BYTES:
            raise ReceiptStoreError(
                f"receipt store: serialized record exceeds {MAX_RECORD_BYTES} bytes"
            )
        existing = self._index.get(receipt.action_id)
        if existing is not None:
            if (existing.receipt.to_dict() == receipt_dict
                    and existing.mission_id == (mission_id or "")
                    and existing.mission_digest == (mission_digest or "")
                    and existing.scope_hash == (scope_hash or "")):
                return receipt.action_id  # idempotent re-ingest
            raise ReceiptStoreError(
                f"receipt store: identity conflict for '{receipt.action_id}'"
            )
        if len(self._index) >= self._max_records:
            raise ReceiptStoreError(
                f"receipt store: record cap {self._max_records} reached (fail-closed)"
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line.decode("utf-8") + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._index[receipt.action_id] = StoredReceipt(
            receipt=receipt, mission_id=mission_id or "",
            mission_digest=mission_digest or "", scope_hash=scope_hash or "",
        )
        return receipt.action_id

    def get(self, action_id: str) -> Optional[StoredReceipt]:
        """Deterministic retrieval by action_id (None when absent)."""
        return self._index.get(action_id)

    def _load(self) -> None:
        index: dict[str, StoredReceipt] = {}
        with open(self._path, "r", encoding="utf-8") as handle:
            for lineno, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    envelope = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ReceiptStoreError(
                        f"receipt store: corrupt line {lineno}: {exc}"
                    )
                stored = self._parse_envelope(envelope, lineno)
                if stored.receipt.action_id in index:
                    prev = index[stored.receipt.action_id]
                    if (prev.receipt.to_dict() != stored.receipt.to_dict()
                            or prev.mission_id != stored.mission_id
                            or prev.mission_digest != stored.mission_digest
                            or prev.scope_hash != stored.scope_hash):
                        raise ReceiptStoreError(
                            f"receipt store: corrupt line {lineno}: identity "
                            f"conflict for '{stored.receipt.action_id}'"
                        )
                    continue
                index[stored.receipt.action_id] = stored
        self._index = index

    @staticmethod
    def _parse_envelope(envelope: dict, lineno: int) -> StoredReceipt:
        if not isinstance(envelope, dict):
            raise ReceiptStoreError(
                f"receipt store: corrupt line {lineno}: not an object"
            )
        if envelope.get("schema_version") != RECEIPT_SCHEMA_VERSION:
            raise ReceiptStoreError(
                f"receipt store: corrupt line {lineno}: unsupported schema "
                f"version {envelope.get('schema_version')!r}"
            )
        receipt = _receipt_from_dict(envelope.get("receipt", {}))
        action_id = envelope.get("action_id", "")
        mission_id = envelope.get("mission_id", "")
        mission_digest = envelope.get("mission_digest", "")
        scope_hash = envelope.get("scope_hash", "")
        if receipt.action_id != action_id:
            raise ReceiptStoreError(
                f"receipt store: corrupt line {lineno}: identity mismatch"
            )
        if not receipt.verify_integrity():
            raise ReceiptStoreError(
                f"receipt store: corrupt line {lineno}: receipt hash mismatch "
                f"for '{action_id}'"
            )
        expected = _record_hash(action_id, mission_id, mission_digest,
                                scope_hash, receipt.to_dict())
        if envelope.get("record_hash") != expected:
            raise ReceiptStoreError(
                f"receipt store: corrupt line {lineno}: mission-binding "
                f"mismatch for '{action_id}'"
            )
        return StoredReceipt(
            receipt=receipt, mission_id=mission_id,
            mission_digest=mission_digest, scope_hash=scope_hash,
        )
