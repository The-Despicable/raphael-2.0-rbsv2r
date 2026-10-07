"""snapshot.py — immutable experiment snapshots + read-only replay (RSI-1 B.1/B.2).

A snapshot binds an experiment's configuration, candidate identities, evidence
references, and evaluator version into one content-hashed record. "Replay" here
is RE-DERIVATION from persisted stores — it executes no live actions, touches
no historical records, and always labels itself as replay rather than a new
governed execution (roadmap L24: deterministic re-scoring is exactly what the
D2 hardened evaluator performs on persisted bytes).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCHEMA_VERSION = 1

#: Human-readable LABEL only. A label can assert anything and therefore proves
#: nothing. RSI-1 measurement-integrity rule: an artifact may only be trusted as
#: having been produced by a given evaluator when its recorded
#: ``evaluator_identity`` matches :func:`authoritative_evaluator_identity` —
#: a content digest over the real evaluator/gating modules plus the gate
#: configuration. This constant is retained for readability and for the
#: snapshot field default; it is NOT an authority and is NOT sufficient to
#: distinguish one evaluator definition from another.
EVALUATOR_VERSION = (
    "rsi-objective-evaluator (broker-authoritative-receipt + contract-membership "
    "+ episode-bound-budget); authoritative identity = "
    "rsi.evaluation_gate.EvaluatorIdentity"
)


def authoritative_evaluator_identity(gate_config=None):
    """The content-addressed identity of the evaluator that actually exists.

    Returns an :class:`orchestrator.rsi.evaluation_gate.EvaluatorIdentity`.
    Imported lazily so ``snapshot`` never pulls the gate machinery in at module
    import time.
    """
    from orchestrator.rsi.evaluation_gate import EvaluatorIdentity, GateConfig
    if gate_config is None:
        gate_config = GateConfig(config_id="default", campaign_id="unspecified")
    return EvaluatorIdentity.compute_current(gate_config)


class SnapshotError(ValueError):
    pass


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# NOTE: the authoritative EVALUATOR_VERSION label is defined once, above, next
# to :func:`authoritative_evaluator_identity`. A second free-text definition here
# previously shadowed it and advertised a weaker gate set than the code actually
# enforced; it has been removed so the label cannot drift from the identity.


@dataclass(frozen=True)
class ExperimentSnapshot:
    experiment_id: str
    candidate_hashes: Dict[str, str]        # policy_id -> content_hash
    evidence_store_paths: Tuple[str, ...]   # per-run persisted stores
    scenario_descriptions: Dict[str, str]
    evaluator_version: str = EVALUATOR_VERSION
    manifest_sha256: str = ""               # digest of the source manifest
    parent_experience_ids: Tuple[str, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def canonical_dict(self) -> Dict[str, Any]:
        return {
            "candidate_hashes": self.candidate_hashes,
            "evidence_store_paths": list(self.evidence_store_paths),
            "evaluator_version": self.evaluator_version,
            "experiment_id": self.experiment_id,
            "manifest_sha256": self.manifest_sha256,
            "parent_experience_ids": list(self.parent_experience_ids),
            "scenario_descriptions": self.scenario_descriptions,
            "schema_version": self.schema_version,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(_stable(self.canonical_dict()).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentSnapshot":
        declared = data.get("content_hash")
        fields = {k: v for k, v in data.items() if k != "content_hash"}
        snap = cls(**fields)
        if declared is not None and snap.content_hash() != declared:
            raise SnapshotError("content_hash mismatch")
        return snap

    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any], run_dir: Path) -> "ExperimentSnapshot":
        run_id = str(manifest.get("run_id") or "")
        if not run_id:
            raise SnapshotError("manifest carries no run_id")
        candidates = {pid: str(rec.get("content_hash", ""))
                      for pid, rec in (manifest.get("candidates") or {}).items()}
        if not candidates:
            raise SnapshotError("manifest carries no candidate records")
        store_paths = sorted(str(p.relative_to(run_dir)) for p in run_dir.rglob("evidence_store.jsonl"))
        return cls(
            experiment_id=f"rsi0-{run_id}",
            candidate_hashes=candidates,
            evidence_store_paths=tuple(store_paths),
            scenario_descriptions=dict(manifest.get("scenarios") or {}),
            manifest_sha256=hashlib.sha256(_stable(manifest).encode()).hexdigest(),
        )


def verify_snapshot(snapshot: ExperimentSnapshot, run_dir: Path,
                    broker_authority=None) -> Dict[str, Any]:
    """Read-only replay: re-derive each run's objective outcome from the
    persisted evidence stores with the canonical evaluator. No live actions,
    no historical mutation; every result is labelled replay-derived."""
    from orchestrator.exec.evidence_store import EvidenceStore
    from orchestrator.runtime.stages import _verify_objective_action

    results: List[Dict[str, Any]] = []
    for rel in snapshot.evidence_store_paths:
        store_path = run_dir / rel
        store = EvidenceStore(store_path)
        missions = sorted({r.mission_id for r in store.records()})
        for mission_id in missions:
            # derive the objective contract from the persisted execution rows:
            # verify every distinct action_id observed for this mission
            actions = sorted({str(dict(r.payload).get("action_id"))
                              for r in store.records()
                              if r.kind.value == "execution_result"
                              and dict(r.payload).get("action_id")})
            verdicts = {a: _verify_objective_action(store, {"mission_id": mission_id}, a,
                                                    (store_path.parent / "artifacts",),
                                                    broker_authority=broker_authority)
                        for a in actions}
            results.append({
                "replay": True,
                "store": rel,
                "mission_id": mission_id,
                "verified_actions": [a for a, v in verdicts.items() if v["ok"]],
                "unverified_actions": [a for a, v in verdicts.items() if not v["ok"]],
            })
    return {
        "snapshot_hash": snapshot.content_hash(),
        "evaluator_version": snapshot.evaluator_version,
        "replay_only": True,
        "runs": results,
    }
