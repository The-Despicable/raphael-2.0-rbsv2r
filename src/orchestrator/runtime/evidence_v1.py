"""
evidence_v1.py — Durable evidence substrate (§14.5).

Five canonical epistemic classes with explicit provenance, deterministic
identity, strict versioned serialization, and bounded records:

    Action / Execution
          ↓
    ExecutionResult / Artifact   (mechanism outputs, bounded)
          ↓
      Observation / Assertion    (recorded content / stated claims)
          ↓
        Finding                  (derived result; NO adjudication here)

Evidence is NOT belief, authorization, planning, or falsification.
Promotion/demotion, Refuted status, trust recalculation, contradiction
resolution, and replanning are LATER phases and MUST NOT leak in here.

Design notes:
- Frozen dataclasses; validation in __post_init__ (fail-closed EvidenceError).
- Identity: "ev1_" + sha256 over the canonical body. Identity-bearing
  fields: version, kind, mission_id, producer, parents, payload.
  observed_at is provenance, NOT identity (equivalent content observed at
  different times shares identity — idempotent ingest).
- Payload values restricted to JSON scalars + tuples (normalized from
  lists); bounded string lengths; bounded parents; no nesting beyond one
  level of tuples; no host paths smuggled (artifact refs are relative).
- stdlib only at top level. brain/exec imports are lazy inside
  to_legacy_evidence() so this module never drags the control plane into
  the Runtime closure and never touches WorldModel/beliefs.
- No authorize/allow/execute/emit-decision API anywhere in this module.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
EVIDENCE_VERSION = 1
IDENTITY_PREFIX = "ev1_"

MAX_TEXT_BYTES = 8192
MAX_OUTPUT_BYTES = 65536
MAX_PARENTS = 8
MAX_ARTIFACT_REFS = 16
MAX_FIELDS = 24


class EvidenceError(Exception):
    """Malformed, oversized, versioned-wrong, or conflicting evidence (fail-closed)."""
    pass


class EvidenceKind(str, Enum):
    ASSERTION = "assertion"
    OBSERVATION = "observation"
    EXECUTION_RESULT = "execution_result"
    ARTIFACT = "artifact"
    FINDING = "finding"


def _check_text(name: str, value: Any, limit: int = MAX_TEXT_BYTES) -> str:
    if not isinstance(value, str):
        raise EvidenceError(f"Evidence v1: '{name}' must be a string")
    if len(value.encode("utf-8")) > limit:
        raise EvidenceError(f"Evidence v1: '{name}' exceeds {limit} bytes")
    return value


def _check_id(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise EvidenceError(f"Evidence v1: '{name}' must be a 1..256 char string")
    return value


def _freeze_value(value: Any, depth: int = 0) -> Any:
    """Normalize JSON values into frozen, bounded forms (max one tuple level)."""
    if depth > 2:
        raise EvidenceError("Evidence v1: payload nesting too deep")
    if value is None or isinstance(value, (bool, int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise EvidenceError("Evidence v1: non-finite float rejected")
        return value
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise EvidenceError("Evidence v1: string value exceeds output bound")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(v, depth + 1) for v in value)
    raise EvidenceError(f"Evidence v1: unsupported payload type {type(value).__name__}")


def _freeze_payload(payload: Any) -> tuple:
    if not isinstance(payload, dict):
        raise EvidenceError("Evidence v1: payload must be a mapping")
    if len(payload) > MAX_FIELDS:
        raise EvidenceError(f"Evidence v1: payload exceeds {MAX_FIELDS} fields")
    frozen = []
    for key in sorted(payload.keys()):
        if not isinstance(key, str) or not key or len(key) > 128:
            raise EvidenceError("Evidence v1: payload keys must be 1..128 char strings")
        frozen.append((key, _freeze_value(payload[key])))
    return tuple(frozen)


def _canonical_body(version: int, kind: str, mission_id: str, producer: str,
                    parents: tuple, payload: tuple) -> str:
    body = {
        "version": version,
        "kind": kind,
        "mission_id": mission_id,
        "producer": producer,
        "parents": list(parents),
        "payload": {k: _to_jsonable(v) for k, v in payload},
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    return value


def _compute_identity(version: int, kind: str, mission_id: str, producer: str,
                      parents: tuple, payload: tuple) -> str:
    digest = hashlib.sha256(
        _canonical_body(version, kind, mission_id, producer, parents, payload).encode("utf-8")
    ).hexdigest()
    return IDENTITY_PREFIX + digest


@dataclass(frozen=True)
class EvidenceRecord:
    """One typed, provenance-linked, bounded evidence record (§14.5 v1)."""

    kind: EvidenceKind
    mission_id: str
    producer: str
    payload: tuple = ()
    parents: tuple = ()
    observed_at: float = field(default_factory=time.time)
    version: int = EVIDENCE_VERSION
    identity: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EvidenceKind):
            raise EvidenceError("Evidence v1: 'kind' must be an EvidenceKind")
        if self.version != EVIDENCE_VERSION:
            raise EvidenceError(
                f"Evidence v1: unsupported version {self.version!r}"
            )
        mission_id = _check_id("mission_id", self.mission_id)
        producer = _check_id("producer", self.producer)
        object.__setattr__(self, "mission_id", mission_id)
        object.__setattr__(self, "producer", producer)
        if not isinstance(self.parents, (tuple, list)):
            raise EvidenceError("Evidence v1: 'parents' must be a list/tuple of ids")
        parents = tuple(_check_id("parents[]", p) for p in self.parents)
        if len(parents) > MAX_PARENTS:
            raise EvidenceError(f"Evidence v1: more than {MAX_PARENTS} parents")
        if len(set(parents)) != len(parents):
            raise EvidenceError("Evidence v1: duplicate parent references")
        object.__setattr__(self, "parents", parents)
        payload = _freeze_payload(dict(self.payload) if isinstance(self.payload, dict) else self.payload)
        object.__setattr__(self, "payload", payload)
        if not isinstance(self.observed_at, (int, float)) or isinstance(self.observed_at, bool):
            raise EvidenceError("Evidence v1: 'observed_at' must be a number")
        if not self.observed_at >= 0:
            raise EvidenceError("Evidence v1: 'observed_at' must be >= 0")
        expected = _compute_identity(
            self.version, self.kind.value, mission_id, producer, parents, payload
        )
        if self.identity and self.identity != expected:
            raise EvidenceError("Evidence v1: identity does not match content")
        object.__setattr__(self, "identity", expected)
        self._check_kind_shape(dict(payload))

    def _check_kind_shape(self, payload: dict) -> None:
        kind = self.kind
        if kind == EvidenceKind.OBSERVATION:
            if "content" not in payload:
                raise EvidenceError("Evidence v1: observation requires 'content'")
            _check_text("content", payload["content"])
        elif kind == EvidenceKind.ASSERTION:
            if "claim" not in payload:
                raise EvidenceError("Evidence v1: assertion requires 'claim'")
            _check_text("claim", payload["claim"])
            if "claimant" not in payload:
                raise EvidenceError("Evidence v1: assertion requires 'claimant'")
            _check_text("claimant", payload["claimant"], limit=256)
        elif kind == EvidenceKind.EXECUTION_RESULT:
            for required in ("action_id", "status"):
                if required not in payload:
                    raise EvidenceError(
                        f"Evidence v1: execution_result requires '{required}'"
                    )
            _check_id("action_id", payload["action_id"])
            _check_text("status", payload["status"], limit=64)
        elif kind == EvidenceKind.ARTIFACT:
            for required in ("relpath", "size_bytes", "sha256"):
                if required not in payload:
                    raise EvidenceError(
                        f"Evidence v1: artifact requires '{required}'"
                    )
            relpath = payload["relpath"]
            if not isinstance(relpath, str) or not relpath:
                raise EvidenceError("Evidence v1: artifact 'relpath' must be non-empty")
            if relpath.startswith("/") or ".." in relpath.split("/"):
                raise EvidenceError("Evidence v1: artifact 'relpath' must stay relative")
            if len(relpath) > 512:
                raise EvidenceError("Evidence v1: artifact 'relpath' too long")
        elif kind == EvidenceKind.FINDING:
            if "statement" not in payload:
                raise EvidenceError("Evidence v1: finding requires 'statement'")
            _check_text("statement", payload["statement"])
            if not self.parents:
                raise EvidenceError(
                    "Evidence v1: finding requires at least one parent (derived_from)"
                )

    # ── Kind constructors (minimal required provenance per class) ──

    @staticmethod
    def observation(*, mission_id: str, producer: str, content: str,
                    target: str = "", source: str = "",
                    parents: tuple = (), observed_at: Optional[float] = None) -> "EvidenceRecord":
        payload = {"content": _check_text("content", content)}
        if target:
            payload["target"] = _check_text("target", target, limit=256)
        if source:
            payload["source"] = _check_text("source", source, limit=256)
        return EvidenceRecord(
            kind=EvidenceKind.OBSERVATION, mission_id=mission_id,
            producer=producer, payload=payload, parents=tuple(parents or ()),
            **({"observed_at": observed_at} if observed_at is not None else {}),
        )

    @staticmethod
    def assertion(*, mission_id: str, producer: str, claim: str, claimant: str,
                  parents: tuple = (), observed_at: Optional[float] = None) -> "EvidenceRecord":
        return EvidenceRecord(
            kind=EvidenceKind.ASSERTION, mission_id=mission_id,
            producer=producer,
            payload={"claim": _check_text("claim", claim),
                     "claimant": _check_text("claimant", claimant, limit=256)},
            parents=tuple(parents or ()),
            **({"observed_at": observed_at} if observed_at is not None else {}),
        )

    @staticmethod
    def execution_result(*, mission_id: str, producer: str, action_id: str,
                         status: str, returncode: Optional[int] = None,
                         stdout: str = "", stderr: str = "",
                         duration_ms: float = 0.0, reason: str = "",
                         decision: str = "", policy_version: str = "",
                         artifacts: tuple = (), parents: tuple = (),
                         observed_at: Optional[float] = None) -> "EvidenceRecord":
        if returncode is not None and not isinstance(returncode, int):
            raise EvidenceError("Evidence v1: 'returncode' must be int or omitted")
        payload = {
            "action_id": _check_id("action_id", action_id),
            "status": _check_text("status", status, limit=64),
            "stdout": _check_text("stdout", stdout, limit=MAX_OUTPUT_BYTES),
            "stderr": _check_text("stderr", stderr, limit=MAX_OUTPUT_BYTES),
            "duration_ms": float(duration_ms),
            "reason": _check_text("reason", reason),
        }
        if returncode is not None:
            payload["returncode"] = returncode
        if decision:
            payload["decision"] = _check_text("decision", decision, limit=16)
        if policy_version:
            payload["policy_version"] = _check_text("policy_version", policy_version, limit=64)
        if artifacts:
            refs = []
            for ref in artifacts:
                if not isinstance(ref, str) or not ref or ref.startswith("/") or ".." in ref.split("/"):
                    raise EvidenceError("Evidence v1: artifact refs must be safe relpaths")
                refs.append(ref)
            payload["artifacts"] = tuple(refs)
            if len(refs) > MAX_ARTIFACT_REFS:
                raise EvidenceError(
                    f"Evidence v1: more than {MAX_ARTIFACT_REFS} artifact refs"
                )
        return EvidenceRecord(
            kind=EvidenceKind.EXECUTION_RESULT, mission_id=mission_id,
            producer=producer, payload=payload, parents=tuple(parents or ()),
            **({"observed_at": observed_at} if observed_at is not None else {}),
        )

    @staticmethod
    def artifact(*, mission_id: str, producer: str, relpath: str,
                 size_bytes: int, sha256: str, execution_ref: str = "",
                 parents: tuple = (), observed_at: Optional[float] = None) -> "EvidenceRecord":
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise EvidenceError("Evidence v1: 'size_bytes' must be a non-negative int")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise EvidenceError("Evidence v1: 'sha256' must be a 64-char hex digest")
        payload = {"relpath": relpath, "size_bytes": size_bytes, "sha256": sha256}
        if execution_ref:
            payload["execution_ref"] = _check_id("execution_ref", execution_ref)
        return EvidenceRecord(
            kind=EvidenceKind.ARTIFACT, mission_id=mission_id,
            producer=producer, payload=payload, parents=tuple(parents or ()),
            **({"observed_at": observed_at} if observed_at is not None else {}),
        )

    @staticmethod
    def finding(*, mission_id: str, producer: str, statement: str,
                derived_from: tuple, method: str = "",
                observed_at: Optional[float] = None) -> "EvidenceRecord":
        if not derived_from:
            raise EvidenceError("Evidence v1: finding requires derived_from parents")
        payload = {"statement": _check_text("statement", statement)}
        if method:
            payload["method"] = _check_text("method", method, limit=256)
        return EvidenceRecord(
            kind=EvidenceKind.FINDING, mission_id=mission_id,
            producer=producer, payload=payload, parents=tuple(derived_from),
            **({"observed_at": observed_at} if observed_at is not None else {}),
        )

    # ── Serialization ──

    def to_dict(self) -> dict:
        """Stable serialization (fixed key order) for persistence/comparison."""
        return {
            "version": self.version,
            "kind": self.kind.value,
            "identity": self.identity,
            "mission_id": self.mission_id,
            "producer": self.producer,
            "observed_at": self.observed_at,
            "parents": list(self.parents),
            "payload": {k: _to_jsonable(v) for k, v in self.payload},
        }

    @staticmethod
    def from_dict(data: dict) -> "EvidenceRecord":
        """Strict reconstruction: unknown/wrong-version/mismatch fails closed."""
        if not isinstance(data, dict):
            raise EvidenceError("Evidence v1: serialized record must be a mapping")
        allowed = {"version", "kind", "identity", "mission_id", "producer",
                   "observed_at", "parents", "payload"}
        unknown = set(data.keys()) - allowed
        if unknown:
            raise EvidenceError(f"Evidence v1: unknown fields: {sorted(unknown)}")
        for required in ("version", "kind", "mission_id", "producer", "payload"):
            if required not in data:
                raise EvidenceError(f"Evidence v1: missing required field '{required}'")
        try:
            kind = EvidenceKind(data["kind"])
        except ValueError:
            raise EvidenceError(f"Evidence v1: unknown kind {data['kind']!r}")
        return EvidenceRecord(
            kind=kind,
            mission_id=data["mission_id"],
            producer=data["producer"],
            payload=data["payload"],
            parents=tuple(data.get("parents", ())),
            observed_at=data.get("observed_at", 0.0),
            version=data["version"],
            identity=data.get("identity", ""),
        )

    # ── Downstream adapters (structural; no control-plane imports) ──

    @staticmethod
    def execution_result_from_sandbox(*, mission_id: str, action_id: str,
                                      sandbox_result: Any, decision: str = "",
                                      policy_version: str = "",
                                      producer: str = "sandbox.exec",
                                      parents: tuple = ()) -> "EvidenceRecord":
        """Build an ExecutionResult record from a §14.4 SandboxResult (bounded)."""
        def as_text(value: Any) -> str:
            if isinstance(value, (bytes, bytearray)):
                return bytes(value[:MAX_OUTPUT_BYTES]).decode("utf-8", errors="replace")
            if isinstance(value, str):
                return value[:MAX_OUTPUT_BYTES]
            return ""

        return EvidenceRecord.execution_result(
            mission_id=mission_id, producer=producer,
            action_id=action_id,
            status=str(getattr(sandbox_result, "status", "unknown")),
            returncode=getattr(sandbox_result, "returncode", None),
            stdout=as_text(getattr(sandbox_result, "stdout", "")),
            stderr=as_text(getattr(sandbox_result, "stderr", "")),
            duration_ms=float(getattr(sandbox_result, "duration_ms", 0.0) or 0.0),
            reason=str(getattr(sandbox_result, "reason", ""))[:MAX_TEXT_BYTES],
            decision=decision, policy_version=policy_version,
            artifacts=tuple(getattr(sandbox_result, "artifacts", {}).keys()),
            parents=parents,
        )

    @staticmethod
    def artifact_records_from_sandbox(*, mission_id: str,
                                      sandbox_result: Any,
                                      execution_ref: str = "",
                                      producer: str = "sandbox.exec",
                                      parents: tuple = ()) -> list:
        """Build Artifact records from sandbox-produced bytes (never reads host)."""
        import hashlib as _hashlib

        records = []
        artifacts = getattr(sandbox_result, "artifacts", {}) or {}
        if not isinstance(artifacts, dict):
            raise EvidenceError("Evidence v1: sandbox artifacts must be a mapping")
        for relpath, content in artifacts.items():
            if not isinstance(content, (bytes, bytearray)):
                raise EvidenceError("Evidence v1: artifact content must be bytes")
            records.append(EvidenceRecord.artifact(
                mission_id=mission_id, producer=producer, relpath=relpath,
                size_bytes=len(content),
                sha256=_hashlib.sha256(bytes(content)).hexdigest(),
                execution_ref=execution_ref, parents=parents,
            ))
        return records

    def to_legacy_evidence(self) -> Any:
        """Export into the canonical brain EvidenceGraph (no new graph).

        Producer labels are preserved verbatim; student-origin producers map
        to MODEL_INFERENCE (no trust elevation). No WorldModel writes here.
        """
        from orchestrator.brain.evidence import Evidence as LegacyEvidence
        from orchestrator.brain.trust import TrustLevel

        trust = (TrustLevel.MODEL_INFERENCE
                 if self.producer.startswith("student.")
                 else TrustLevel.TOOL_OBSERVATION)
        return LegacyEvidence.create(
            raw_content=json.dumps(self.to_dict(), sort_keys=True),
            trust_level=trust,
            source_detail=f"v1:{self.kind.value}:{self.producer}",
            target=str(dict(self.payload).get("target", "")),
            evidence_type=f"v1:{self.kind.value}",
            description=f"v1:{self.identity}",
            collected_by=str(dict(self.payload).get("action_id", "")),
        )
