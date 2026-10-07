"""
artifact_verify.py — bounded artifact resolution + integrity verification (M3/D2 remediation).

File primitives live here because exec/ is the only package permitted
them (INV-1). This module READS already-persisted capability artifacts and
reports what is actually on disk. It adjudicates nothing:

- it does not authorize, deny, execute, or write evidence
- it never mutates or deletes anything
- it never follows a caller-supplied filesystem path outside the bound root

Two guarantees the objective evaluator depends on:

1. **Containment** — a relpath from an untrusted evidence record resolves
   only inside the caller-bound artifact root. Absolute paths, ``..``
   segments, and symlink escapes are refused (fail-closed).
2. **Integrity** — the returned ``sha256``/``size_bytes`` are recomputed
   from the ACTUAL stored bytes. A digest asserted by an evidence record
   is never trusted; it is compared against this measurement.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Optional, Union

# Bounded read: never load an unbounded file into memory.
MAX_VERIFY_BYTES = 131072  # matches ArtifactStore.MAX_ARTIFACTS ceiling class


class ArtifactVerificationError(RuntimeError):
    """Artifact reference is unsafe, missing, unreadable, or oversized."""


def _contained(root: Path, candidate: Path) -> Optional[Path]:
    """Return candidate when it really lives inside root, else None.

    resolve() collapses symlinks and '..' first, so a symlink pointing
    outside the root is refused just like a literal '..' segment.
    """
    try:
        resolved_root = root.resolve()
        resolved = candidate.resolve()
        resolved.relative_to(resolved_root)
    except (ValueError, OSError):
        return None
    return resolved


def resolve_artifact_path(artifact_root: Union[str, Path],
                          relpath: str) -> Path:
    """Resolve an evidence-declared relpath inside ``artifact_root``.

    The D2 capabilities persist under ``<artifacts_dir>/<name>`` while
    recording the relpath as ``artifacts/<name>``; both layouts are tried,
    in that order, and every candidate must be contained in the root.
    """
    if not isinstance(relpath, str) or not relpath.strip():
        raise ArtifactVerificationError("artifact ref must be a non-empty string")
    if relpath.startswith("/") or ".." in PurePosixPath(relpath).parts:
        raise ArtifactVerificationError(
            f"artifact ref must be a safe relative path: {relpath!r}"
        )
    root = Path(artifact_root)
    if not root.is_dir():
        raise ArtifactVerificationError(f"artifact root is not a directory: {root}")
    candidates = [root / relpath, root / PurePosixPath(relpath).name]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = _contained(root, candidate)
        if resolved is None:
            raise ArtifactVerificationError(
                f"artifact ref escapes the artifact root: {relpath!r}"
            )
        return resolved
    raise ArtifactVerificationError(
        f"artifact ref does not resolve to a stored file: {relpath!r}"
    )


def verify_artifact(artifact_root: Union[str, Path], relpath: str,
                    max_bytes: int = MAX_VERIFY_BYTES) -> dict:
    """Measure the ACTUAL stored bytes of one artifact.

    Returns ``{"relpath", "path", "sha256", "size_bytes"}`` where sha256 is
    recomputed from disk. Raises ArtifactVerificationError when the ref is
    unsafe, missing, or larger than the bounded read.
    """
    path = resolve_artifact_path(artifact_root, relpath)
    size = path.stat().st_size
    if size > max_bytes:
        raise ArtifactVerificationError(
            f"artifact {relpath!r} exceeds the bounded read ({size} > {max_bytes} bytes)"
        )
    data = path.read_bytes()
    return {
        "relpath": relpath,
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }