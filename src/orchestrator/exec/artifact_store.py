"""
artifact_store.py — Minimal content-addressed artifact storage (P4.5 §15).

File-backed content-addressed store for execution artifacts (e.g.
sandbox-produced artifact bytes). File writes live here because exec/
is the only package permitted file primitives (INV-1). This store
holds data; it adjudicates nothing:

- no authorization decisions (artifacts/refs cannot allow/deny)
- no execution (artifacts cannot run anything)
- no belief writes, no falsification, no replanning, no learning
- no overwrite API, no delete API (immutable means immutable)

Identity: artifact_id = "sha256:" + hex(sha256(content bytes)).
Identity depends ONLY on content bytes — never on metadata. Same
content always yields the same identity; different content yields a
different identity (up to sha256 collision resistance).

Layout (under root):
    sha256/<hh>/<rest>.bin    content bytes (verbatim)
    sha256/<hh>/<rest>.json   metadata envelope (canonical JSON)

Writes are atomic (temp file + os.replace + fsync). Every read
recomputes the content hash and refuses mismatches. Producer linkage
(receipt_id/action_id/mission_id) is descriptive traceability toward
the producing receipt; it confers no authority and is NOT part of
identity.

Fail-closed rules:
- missing content or metadata -> ArtifactStoreError
- content hash mismatch on read -> refused
- metadata identity/binding mismatch -> refused
- malformed ref or envelope, unknown schema -> refused
- conflicting content under an existing identity -> rejected
  (unrepresentable by construction unless the hash is broken or the
  files were hand-edited; verified on write)
- oversized content -> rejected
- more than max_artifacts -> StoreFull rejected
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ARTIFACT_ID_PREFIX = "sha256:"
ARTIFACT_SCHEMA_VERSION = 1
MAX_ARTIFACT_BYTES = 131072
MAX_ARTIFACTS = 10000


class ArtifactStoreError(Exception):
    """Artifact store misuse, corruption, or capacity failure (fail-closed)."""
    pass


def _content_id(content: bytes) -> tuple[str, str]:
    """Content-derived identity. Returns (artifact_id, hex_digest)."""
    if not isinstance(content, (bytes, bytearray)):
        raise ArtifactStoreError("artifact store: content must be bytes")
    digest = hashlib.sha256(bytes(content)).hexdigest()
    return ARTIFACT_ID_PREFIX + digest, digest


def _canonical_bytes(payload: dict) -> bytes:
    """Deterministic serialization: sorted keys, compact, ASCII."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    ).encode("utf-8")


@dataclass(frozen=True)
class ArtifactRef:
    """Immutable, deterministic reference to stored artifact content.

    Frozen data describing WHERE content lives by WHAT it hashes to.
    Authorizes nothing: no PDP/PEP/eval logic, no execution path.
    """
    artifact_id: str = ""
    byte_len: int = 0
    sha256: str = ""

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "byte_len": self.byte_len,
            "sha256": self.sha256,
        }

    @staticmethod
    def from_dict(data: dict) -> "ArtifactRef":
        """Strict reconstruction (fail-closed)."""
        if not isinstance(data, dict):
            raise ArtifactStoreError("artifact store: ref payload must be a mapping")
        allowed = {"artifact_id", "byte_len", "sha256"}
        unknown = set(data.keys()) - allowed
        if unknown:
            raise ArtifactStoreError(
                f"artifact store: unknown ref fields: {sorted(unknown)}"
            )
        artifact_id = data.get("artifact_id", "")
        sha256 = data.get("sha256", "")
        byte_len = data.get("byte_len", -1)
        if (not isinstance(artifact_id, str)
                or not artifact_id.startswith(ARTIFACT_ID_PREFIX)):
            raise ArtifactStoreError("artifact store: malformed artifact_id")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise ArtifactStoreError("artifact store: malformed sha256")
        try:
            int(sha256, 16)
        except ValueError:
            raise ArtifactStoreError("artifact store: malformed sha256")
        if (artifact_id != ARTIFACT_ID_PREFIX + sha256
                or not isinstance(byte_len, int)
                or isinstance(byte_len, bool)
                or byte_len < 0):
            raise ArtifactStoreError("artifact store: inconsistent ref")
        return ArtifactRef(artifact_id=artifact_id, byte_len=byte_len, sha256=sha256)


@dataclass(frozen=True)
class StoredArtifact:
    """Retrieved artifact content with its descriptive metadata.

    Frozen data; authorizes nothing.
    """
    ref: ArtifactRef
    content: bytes = b""
    media_type: str = ""
    producer_receipt_id: str = ""
    producer_action_id: str = ""
    mission_id: str = ""


class ArtifactStore:
    """Append-only bounded content-addressed artifact store."""

    def __init__(self, root: str | Path, max_artifacts: int = MAX_ARTIFACTS,
                 max_bytes: int = MAX_ARTIFACT_BYTES):
        self._root = Path(root)
        self._max_artifacts = max_artifacts
        self._max_bytes = max_bytes

    @property
    def root(self) -> Path:
        return self._root

    def _paths(self, digest: str) -> tuple[Path, Path]:
        shard = self._root / "sha256" / digest[:2]
        return shard / (digest[2:] + ".bin"), shard / (digest[2:] + ".json")

    def count(self) -> int:
        """Number of stored artifacts (metadata files present)."""
        if not self._root.exists():
            return 0
        return sum(1 for _ in self._root.rglob("*.json"))

    def put(self, content: bytes, media_type: str = "",
            producer_receipt_id: str = "", producer_action_id: str = "",
            mission_id: str = "") -> ArtifactRef:
        """Store artifact bytes. Returns the deterministic ArtifactRef.

        Idempotent: storing equivalent content returns the same ref
        without rewriting. Conflicting content under an existing
        identity is rejected (fail-closed).
        """
        if not isinstance(content, (bytes, bytearray)):
            raise ArtifactStoreError("artifact store: content must be bytes")
        content = bytes(content)
        if len(content) > self._max_bytes:
            raise ArtifactStoreError(
                f"artifact store: content exceeds {self._max_bytes} bytes"
            )
        artifact_id, digest = _content_id(content)
        ref = ArtifactRef(artifact_id=artifact_id, byte_len=len(content), sha256=digest)
        bin_path, meta_path = self._paths(digest)
        if bin_path.exists() or meta_path.exists():
            existing = self._read_pair(bin_path, meta_path, digest)
            if existing.content != content:
                raise ArtifactStoreError(
                    f"artifact store: conflicting content for '{artifact_id}'"
                )
            return existing.ref  # idempotent re-ingest
        if self.count() >= self._max_artifacts:
            raise ArtifactStoreError(
                f"artifact store: artifact cap {self._max_artifacts} reached (fail-closed)"
            )
        envelope = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "byte_len": len(content),
            "sha256": digest,
            "media_type": media_type or "",
            "producer_receipt_id": producer_receipt_id or "",
            "producer_action_id": producer_action_id or "",
            "mission_id": mission_id or "",
        }
        meta_bytes = _canonical_bytes(envelope)
        bin_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(bin_path, content)
        try:
            self._atomic_write(meta_path, meta_bytes)
        except Exception:
            try:
                bin_path.unlink()
            except OSError:
                pass
            raise
        return ref


    def get(self, ref: ArtifactRef | str) -> Optional[StoredArtifact]:
        """Retrieve by ref (None when absent). Hash re-verified on read."""
        if isinstance(ref, str):
            if not ref.startswith(ARTIFACT_ID_PREFIX):
                return None
            digest = ref[len(ARTIFACT_ID_PREFIX):]
            if len(digest) != 64:
                return None
            try:
                int(digest, 16)
            except ValueError:
                return None
            # byte_len unknown from a bare id: length is verified
            # against stored metadata on read.
            ref = ArtifactRef(artifact_id=ref, byte_len=0, sha256=digest)
        if not isinstance(ref, ArtifactRef):
            return None
        digest = ref.sha256
        bin_path, meta_path = self._paths(digest)
        if not bin_path.exists() or not meta_path.exists():
            return None
        try:
            return self._read_pair(bin_path, meta_path, digest)
        except ArtifactStoreError:
            return None

    def get_or_raise(self, ref: ArtifactRef | str) -> StoredArtifact:
        """Retrieve by ref, raising ArtifactStoreError when unavailable/corrupt."""
        stored = self.get(ref)
        if stored is None:
            raise ArtifactStoreError("artifact store: artifact unavailable or corrupt")
        return stored

    def _read_pair(self, bin_path: Path, meta_path: Path, digest: str) -> StoredArtifact:
        try:
            content = bin_path.read_bytes()
        except OSError as exc:
            raise ArtifactStoreError(f"artifact store: unreadable content: {exc}")
        try:
            envelope = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactStoreError(f"artifact store: unreadable metadata: {exc}")
        if not isinstance(envelope, dict):
            raise ArtifactStoreError("artifact store: malformed metadata envelope")
        if envelope.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise ArtifactStoreError(
                f"artifact store: unsupported schema version {envelope.get('schema_version')!r}"
            )
        if envelope.get("artifact_id") != ARTIFACT_ID_PREFIX + digest:
            raise ArtifactStoreError("artifact store: metadata identity mismatch")
        if hashlib.sha256(content).hexdigest() != digest:
            raise ArtifactStoreError("artifact store: content hash mismatch")
        if len(content) != int(envelope.get("byte_len", -1)):
            raise ArtifactStoreError("artifact store: byte length mismatch")
        ref = ArtifactRef(artifact_id=ARTIFACT_ID_PREFIX + digest,
                          byte_len=len(content), sha256=digest)
        return StoredArtifact(
            ref=ref, content=content,
            media_type=str(envelope.get("media_type", "") or ""),
            producer_receipt_id=str(envelope.get("producer_receipt_id", "") or ""),
            producer_action_id=str(envelope.get("producer_action_id", "") or ""),
            mission_id=str(envelope.get("mission_id", "") or ""),
        )

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        """Atomic durable write: temp file + fsync + os.replace."""
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
