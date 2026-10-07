"""identity.py — PROPOSED identity contract for actions, attempts, and executions.

Why this exists
---------------
Three confirmed defects are addressed here.

1. Process identity is not unique across hosts. ``create_process`` sets
   ``primary_identifier=f"pid:{pid}"`` (src/orchestrator/brain/world.py:1271),
   so two processes with pid 1234 on two different hosts collapse onto the
   same primary identifier. ``make_process_identifier`` below produces a
   host-scoped form instead.

2. There is no attempt/execution identity, so an idempotent retry is
   indistinguishable from a new intentional operation. The receipt mints a
   fresh ``action_id`` per proposal (``field(default_factory=lambda:
   f"act_{uuid.uuid4().hex[:12]}")``, src/orchestrator/brain/action.py:157),
   which means "retry the same intended operation" and "do a new thing" are
   written the same way. ``ExecutionIdentity.logical_operation_id`` separates
   them: a retry of the same intended operation reuses the token; a genuinely
   new operation must mint a new one.

3. Failure cache keys are under-specified, so a cached failure suppresses
   attempts that had nothing to do with the recorded one. ``failure_key``
   binds the coarse ``ActionKey`` to the full ``AttemptContext`` — including
   the declared dependency values — so a record only applies to attempts
   that were materially the same attempt.

A failure record is a retry-decision aid, NOT an oracle of future failure.
Repeated failure becomes evidence, never ontology. Hard suppression is
reserved for conditions actually established by evidence — a record exists
because something was observed, and an observation licenses a narrower next
step, not a permanent "this can never work" claim. Records expire
(``expires_at``, ``retry_after``) and carry
``suppression_policy_version`` so a policy change is mechanically visible
rather than silently reinterpreting old records.

Secrets: ``AttemptContext.normalized_param_fingerprints`` holds digests of
normalized values, never the values. A parameter marked ``is_secret`` in
``action_spec.ParameterSpec`` MUST be represented here by an opaque ref so
secrets cannot leak into cache keys, logs, or records.

This module is a contract proposal. Nothing in the runtime stage graph
imports it.

Schema version: 1
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field


def make_process_identifier(host: str, pid: int) -> str:
    """Host-scoped process identifier.

    Replaces the bare ``f"pid:{pid}"`` form at
    src/orchestrator/brain/world.py:1271, which is only unique within a
    single host.
    """
    host_part = str(host).strip() or "unknown-host"
    return f"proc:{host_part}:{int(pid)}"


@dataclass(frozen=True)
class ActionKey:
    """Coarse identity: WHAT operation is requested.

    Deliberately excludes environment, dependency values, and budget. Two
    attempts sharing an ``ActionKey`` are the same request, not necessarily
    the same attempt — that is ``AttemptContext``'s job.
    """

    action_spec_id: str
    spec_version: int
    canonical_target_identity: str
    normalized_param_fingerprints: tuple = ()  # tuple[str, ...], never raw values

    def to_dict(self) -> dict:
        return {
            "action_spec_id": self.action_spec_id,
            "spec_version": self.spec_version,
            "canonical_target_identity": self.canonical_target_identity,
            "normalized_param_fingerprints": list(self.normalized_param_fingerprints),
        }


@dataclass(frozen=True)
class AttemptContext:
    """Full context of one attempt.

    ``dependency_values`` is a tuple of ``(name, truth_state,
    freshness_state)`` triples, one per name declared in
    ``ActionSpec.declared_dependencies``. A name declared but absent here
    means the cache key cannot be computed for this attempt — callers should
    refuse to consult the failure cache rather than guess.
    """

    action_spec_id: str
    spec_version: int
    capability_impl_version: str = ""
    canonical_target_identity: str = ""
    normalized_param_fingerprints: tuple = ()  # tuple[str, ...] — NEVER raw secrets
    dependency_values: tuple = ()                # tuple[tuple[str, str, str], ...]
    scope_fingerprint: str = ""
    budget_snapshot_hash: str = ""
    evidence_refs: tuple = ()                    # tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "action_spec_id": self.action_spec_id,
            "spec_version": self.spec_version,
            "capability_impl_version": self.capability_impl_version,
            "canonical_target_identity": self.canonical_target_identity,
            "normalized_param_fingerprints": list(self.normalized_param_fingerprints),
            "dependency_values": [list(t) for t in self.dependency_values],
            "scope_fingerprint": self.scope_fingerprint,
            "budget_snapshot_hash": self.budget_snapshot_hash,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ExecutionIdentity:
    """Identity of one dispatched execution.

    ``logical_operation_id`` is the idempotency token. Re-dispatching the
    SAME intended operation reuses it; a new intentional operation mints a
    NEW token. Reuse is what makes a retry safe to deduplicate; minting a
    new token is what stops a retry from being silently absorbed into an
    earlier one.
    """

    execution_id: str
    logical_operation_id: str
    dispatch_context_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "logical_operation_id": self.logical_operation_id,
            "dispatch_context_hash": self.dispatch_context_hash,
        }


def failure_key(action_key: ActionKey, attempt_context: AttemptContext) -> str:
    """Cache key for a failure record.

    Binds the coarse request identity to the full attempt context, so a
    record can only suppress an attempt that was materially the same one.
    Derived, deterministic, and free of raw parameter values.

    Both arguments are required. A failure record without an attempt
    context cannot be invalidated correctly, so refusing to build a key is
    safer than keying on action identity alone.
    """
    if action_key is None:
        raise TypeError("failure_key requires an ActionKey, got None")
    if attempt_context is None:
        raise TypeError(
            "failure_key requires an AttemptContext, got None; a failure "
            "record cannot be context-bound without one"
        )
    payload = {
        "action_key": action_key.to_dict(),
        "attempt_context": attempt_context.to_dict(),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FailureRecord:
    """A recorded failed attempt.

    A retry-decision aid, not an oracle. See the module docstring: hard
    suppression is reserved for conditions established by evidence, and
    these records always expire.
    """

    action_key: ActionKey
    attempt_context: AttemptContext
    failure_class: str = ""
    evidence_refs: tuple = ()  # tuple[str, ...]
    attempt_count: int = 1
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    expires_at: float = 0.0    # 0.0 means "already expired" — never "never expires"
    retry_after: float = 0.0
    suppression_policy_version: str = ""

    def is_expired(self, now: float) -> bool:
        """True when the record may no longer constrain a retry decision."""
        return self.expires_at <= now

    def to_dict(self) -> dict:
        return {
            "action_key": self.action_key.to_dict(),
            "attempt_context": self.attempt_context.to_dict(),
            "failure_class": self.failure_class,
            "evidence_refs": list(self.evidence_refs),
            "attempt_count": self.attempt_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "expires_at": self.expires_at,
            "retry_after": self.retry_after,
            "suppression_policy_version": self.suppression_policy_version,
        }
