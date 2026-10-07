"""
evidence_store.py — Bounded durable evidence store (§14.5).

Repository-native JSONL persistence for v1 evidence records. File writes
live here because exec/ is the only package permitted file primitives
(INV-1). This store persists records; it adjudicates nothing:

- no authorization decisions (records cannot allow/deny anything)
- no execution (records cannot run anything)
- no belief writes, no falsification, no replanning, no learning
- no overwrite API, no delete API (durable means durable)

Fail-closed rules:
- malformed/corrupt lines on load -> EvidenceError (whole load refused)
- stored identity != recomputed identity -> corrupt
- unknown parent references on append -> rejected
- duplicate identity + identical content -> idempotent OK (same identity)
- duplicate identity + different content -> conflict rejected
- oversized serialized record -> rejected
- more than MAX_RECORDS -> StoreFull rejected

One JSON object per line: {"identity": ..., "record": {...}}.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from orchestrator.runtime.evidence_v1 import (
    EvidenceError,
    EvidenceRecord,
)

STORE_FILENAME = "evidence_v1.jsonl"
MAX_RECORD_BYTES = 131072
MAX_RECORDS = 10000


class EvidenceStore:
    """Append-only bounded JSONL store for EvidenceRecord v1."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._index: dict[str, EvidenceRecord] = {}
        if self._path.exists():
            self._load()

    @property
    def path(self) -> Path:
        return self._path

    def __len__(self) -> int:
        return len(self._index)

    def append(self, record: EvidenceRecord) -> str:
        """Persist a record. Returns its identity. Fail-closed on conflict."""
        if not isinstance(record, EvidenceRecord):
            raise EvidenceError("Evidence store: only EvidenceRecord v1 accepted")
        for parent in record.parents:
            if parent not in self._index:
                raise EvidenceError(
                    f"Evidence store: unknown parent reference '{parent}'"
                )
        if record.identity in self._index:
            existing = self._index[record.identity]
            if existing.to_dict() == record.to_dict():
                return record.identity  # idempotent re-ingest
            raise EvidenceError(
                f"Evidence store: identity conflict for '{record.identity}'"
            )
        if len(self._index) >= MAX_RECORDS:
            raise EvidenceError(
                f"Evidence store: record cap {MAX_RECORDS} reached (fail-closed)"
            )
        line = json.dumps(
            {"identity": record.identity, "record": record.to_dict()},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        )
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            raise EvidenceError(
                f"Evidence store: serialized record exceeds {MAX_RECORD_BYTES} bytes"
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._index[record.identity] = record
        return record.identity

    def get(self, identity: str) -> Optional[EvidenceRecord]:
        """Deterministic retrieval by identity (None when absent)."""
        return self._index.get(identity)

    def records(self) -> list:
        """All persisted records (M3/D2: read-side for objective evaluation
        and receipt verification). Order is insertion order; the list is a
        copy — mutating it does not affect the store."""
        return list(self._index.values())

    def _load(self) -> None:
        index: dict[str, EvidenceRecord] = {}
        with open(self._path, "r", encoding="utf-8") as handle:
            for lineno, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    envelope = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EvidenceError(
                        f"Evidence store: corrupt line {lineno}: {exc}"
                    )
                if not isinstance(envelope, dict):
                    raise EvidenceError(
                        f"Evidence store: corrupt line {lineno}: not an object"
                    )
                record = EvidenceRecord.from_dict(envelope.get("record", {}))
                if record.identity != envelope.get("identity"):
                    raise EvidenceError(
                        f"Evidence store: corrupt line {lineno}: identity mismatch"
                    )
                if record.identity in index:
                    if index[record.identity].to_dict() != record.to_dict():
                        raise EvidenceError(
                            f"Evidence store: corrupt line {lineno}: "
                            f"identity conflict for '{record.identity}'"
                        )
                    continue
                index[record.identity] = record
        self._index = index
