"""experience.py — Evidence-backed ExperienceNode + trusted ingestion (RSI-1, v4.2 §15.2).

Distinct from EvidenceRecord (§15.1): EvidenceRecord answers provenance/authority;
an ExperienceNode records the DECISION/SEARCH context and outcome needed for later
improvement diagnosis — and must itself reference evidence that independently
resolves and verifies through the canonical mechanisms.

Ingestion trust rules (A.2):
- consumes only persisted, completed episode records from a real evidence store;
- objective-verified episodes must pass the hardened objective evaluator
  (mission-scoped, producer-allowlisted, artifact-chain verified);
- failed/incomplete episodes are ingested HONESTLY as failed experiences
  (never fabricated into successes, never silently dropped);
- fabricated / cross-episode / unverifiable records are rejected with a reason;
- duplicate ingestion is idempotent for identical content and refuses conflicts;
- historical evidence is never mutated.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from orchestrator.runtime.evidence_v1 import EvidenceRecord

SCHEMA_VERSION = 1
VALID_OUTCOMES = ("objective_met", "objective_not_met", "failed", "denied",
                  "incomplete", "unscorable")


class ExperienceError(ValueError):
    pass


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ExperienceNode:
    experience_id: str
    mission_id: str
    episode_id: str
    policy_id: str = ""
    policy_version: int = 0
    policy_content_hash: str = ""
    action_refs: Tuple[str, ...] = ()       # mission action_ids attempted, in order
    decision_refs: Tuple[str, ...] = ()     # broker receipt action_ids
    evidence_refs: Tuple[str, ...] = ()     # VERIFIED EvidenceRecord identities
    outcome: str = ""                       # VALID_OUTCOMES
    terminal_reason: str = ""
    steps_executed: int = 0
    denials: int = 0
    hard_violations: Tuple[str, ...] = ()
    wall_seconds: float = 0.0
    parent_experience_ids: Tuple[str, ...] = ()
    observed_at: float = field(default_factory=time.time)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.experience_id or not isinstance(self.experience_id, str):
            raise ExperienceError("experience_id required")
        if not self.mission_id or not self.episode_id:
            raise ExperienceError("mission_id and episode_id required")
        if self.outcome not in VALID_OUTCOMES:
            raise ExperienceError(f"outcome must be one of {VALID_OUTCOMES}")
        if self.schema_version != SCHEMA_VERSION:
            raise ExperienceError("unsupported schema_version")
        if self.outcome == "objective_met" and not self.evidence_refs:
            raise ExperienceError(
                "objective_met experiences must reference verified evidence")

    def canonical_dict(self) -> Dict[str, Any]:
        return {
            "action_refs": list(self.action_refs),
            "decision_refs": list(self.decision_refs),
            "denials": self.denials,
            "episode_id": self.episode_id,
            "evidence_refs": list(self.evidence_refs),
            "experience_id": self.experience_id,
            "hard_violations": list(self.hard_violations),
            "mission_id": self.mission_id,
            "observed_at": self.observed_at,
            "outcome": self.outcome,
            "parent_experience_ids": list(self.parent_experience_ids),
            "policy_content_hash": self.policy_content_hash,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "schema_version": self.schema_version,
            "steps_executed": self.steps_executed,
            "terminal_reason": self.terminal_reason,
            "wall_seconds": self.wall_seconds,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(_stable_json(self.canonical_dict()).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceNode":
        declared = data.pop("content_hash", None)
        node = cls(**data)
        node.validate()
        if declared is not None and declared != node.content_hash():
            raise ExperienceError("content_hash mismatch — identity refers to "
                                  "different experience content")
        return node


class ExperienceLog:
    """Append-only experience ledger (idempotent, conflict-refusing)."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._index: Dict[str, ExperienceNode] = {}
        if self._path.exists():
            for line in self._path.read_text().splitlines():
                if line.strip():
                    node = ExperienceNode.from_dict(json.loads(line))
                    self._index[node.experience_id] = node

    def append(self, node: ExperienceNode) -> str:
        existing = self._index.get(node.experience_id)
        if existing is not None:
            if existing.content_hash() == node.content_hash():
                return node.experience_id  # idempotent duplicate
            raise ExperienceError(
                f"conflicting duplicate experience {node.experience_id}")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(_stable_json(node.to_dict()) + "\n")
        self._index[node.experience_id] = node
        return node.experience_id

    def get(self, experience_id: str) -> Optional[ExperienceNode]:
        return self._index.get(experience_id)

    def all(self) -> List[ExperienceNode]:
        return list(self._index.values())


# ── trusted ingestion ────────────────────────────────────────────────────

@dataclass(frozen=True)
class IngestionResult:
    accepted: bool
    experience_id: str = ""
    reason: str = ""
    node: Optional[ExperienceNode] = None


def ingest_episode(store, run_record: Dict[str, Any],
                   episode_id: str,
                   evidence_roots: Tuple[Path, ...] = (),
                   broker_authority=None) -> IngestionResult:
    """Ingest one completed candidate-episode run record as an ExperienceNode.

    Trust rules: the run_record's claims are NOT trusted — outcome classification
    is re-derived from the persisted evidence store through the canonical
    objective evaluator; artifact chains are verified by it. A run_record that
    claims success without verifiable evidence is ingested as the honest,
    weaker outcome (or rejected when nothing resolves at all).
    """
    from orchestrator.runtime.stages import _verify_objective_action  # canonical

    mission_id = str(run_record.get("mission_id") or "")
    if not mission_id:
        return IngestionResult(False, reason="run record carries no mission identity")
    node = None
    required = run_record.get("objective_requires") or []
    if not required:
        return IngestionResult(False, reason="no objective contract on the run")

    view = {"mission_id": mission_id}
    verified_identities: List[str] = []
    unmet: List[str] = []
    for action_id in required:
        verdict = _verify_objective_action(store, view, action_id, evidence_roots,
                                           broker_authority=broker_authority)
        if verdict["ok"]:
            verified_identities.append(verdict["identity"])
        else:
            unmet.append(action_id)

    if hard := run_record.get("hard_violations") or []:
        outcome = "unscorable"  # safety-violating runs never rank as experience
    elif not unmet:
        outcome = "objective_met"
    else:
        rows_failed = [r for r in store.records()
                       if r.kind.value == "execution_result"
                       and r.mission_id == mission_id
                       and dict(r.payload).get("status") == "failed"]
        # A genuinely failed episode ingests as "failed" regardless of
        # authority availability; an unverifiable (no authoritative broker
        # state) unmet episode ingests conservatively as objective_not_met.
        # Neither is ever represented as a verified success.
        outcome = "failed" if rows_failed else "objective_not_met"

    node = ExperienceNode(
        experience_id=f"exp-{mission_id}-{episode_id}",
        mission_id=mission_id,
        episode_id=episode_id,
        policy_id=str(run_record.get("policy_id") or ""),
        policy_version=int(run_record.get("policy_version") or 0),
        policy_content_hash=str(run_record.get("policy_content_hash") or ""),
        action_refs=tuple(str(a) for a in run_record.get("action_refs") or ()),
        decision_refs=tuple(str(d) for d in run_record.get("decision_refs") or ()),
        evidence_refs=tuple(verified_identities),
        outcome=outcome,
        terminal_reason=str(run_record.get("terminal_reason") or "")[:512],
        steps_executed=int(run_record.get("steps_executed") or 0),
        denials=int(run_record.get("denials") or 0),
        hard_violations=tuple(str(h) for h in hard),
        wall_seconds=float(run_record.get("wall_seconds") or 0.0),
    )
    node.validate()
    return IngestionResult(True, node.experience_id, outcome, node=node)
