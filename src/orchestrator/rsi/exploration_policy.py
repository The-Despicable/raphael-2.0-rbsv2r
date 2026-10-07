"""exploration_policy.py — ExplorationPolicy v0 (v4.2 §15.3, minimal RSI-0 form).

A first-class, validated, deterministically serializable candidate-strategy
record. v0 scope is deliberately tiny: a candidate may choose the **order**
of the two operator-approved D2 actions and whether **Action A** may be
retried once. Nothing else is representable — a candidate cannot alter
targets, authorization, capabilities, budgets, evaluation rules, or any
protected governance surface, because those fields do not exist here and the
runner never reads them from the policy.

Identity rule: ``content_hash`` is the SHA-256 of the canonical JSON of
every field *except* the hash itself. ``from_dict`` recomputes and refuses a
record whose declared hash does not match its content, so the same identity
can never silently refer to different policy content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

SCHEMA_VERSION = 1
STATUS_EXPERIMENTAL = "experimental"
# RSI-1 lifecycle (A.4): experimental -> evaluated -> accepted-for-review | rejected.
# Deliberately NO "active"/"promoted" status: nothing may bypass the (future,
# human-governed) promotion milestone.
STATUS_EVALUATED = "evaluated"
STATUS_ACCEPTED_FOR_REVIEW = "accepted-for-review"
STATUS_REJECTED = "rejected"
LIFECYCLE_STATUSES = (STATUS_EXPERIMENTAL, STATUS_EVALUATED,
                      STATUS_ACCEPTED_FOR_REVIEW, STATUS_REJECTED)

# The approved D2 action vocabulary (keys used inside policy parameters).
# Values are the exact action_type / capability / method / action_id prefix
# bound by the operator-approved D2 policy (policies/engagement-d2-v1.json).
ACTIONS: Dict[str, Dict[str, str]] = {
    "A": {"action_type": "recon_service_probe", "capability": "exec.d1_lab_probe",
          "method": "nmap", "action_id": "ACT-D2-PROBE-0001"},
    "B": {"action_type": "lab_http_probe", "capability": "exec.http_probe",
          "method": "curl", "action_id": "ACT-D2-HTTP-0002"},
}

# Frozen constraint echo: what every candidate inherits from the approved D2
# policy. Candidates declare this echo; the runner cross-checks it against the
# loaded policy and refuses a mismatched echo.
CONSTRAINT_ECHO = {
    "target": "dvwa",
    "max_episode_steps": 5,
    "max_actions_per_minute": 6,
    "objective_requires": ["ACT-D2-PROBE-0001", "ACT-D2-HTTP-0002"],
}


class ExplorationPolicyError(ValueError):
    """Raised for malformed, ambiguous, or out-of-scope policy definitions."""


@dataclass(frozen=True)
class ExplorationPolicy:
    policy_id: str
    version: int
    status: str
    created_by: str
    motivation: str
    parameters: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=lambda: dict(CONSTRAINT_ECHO))
    schema_version: int = SCHEMA_VERSION
    parent_version: int = 0
    evidence_refs: Tuple[str, ...] = ()
    evaluation_refs: Tuple[str, ...] = ()
    # RSI-1 lineage (optional; excluded from the identity hash when unset so
    # existing v0 policy identities are preserved byte-for-byte):
    parent_policy_hash: str = ""
    hypothesis_id: str = ""
    experiment_id: str = ""
    change_description: str = ""

    # ── validation ───────────────────────────────────────────────────────

    def validate(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ExplorationPolicyError("policy_id must be a non-empty string")
        if not isinstance(self.version, int) or self.version < 1:
            raise ExplorationPolicyError("version must be a positive integer")
        if self.schema_version != SCHEMA_VERSION:
            raise ExplorationPolicyError(
                f"unsupported schema_version {self.schema_version!r}")
        if self.status not in LIFECYCLE_STATUSES:
            raise ExplorationPolicyError(
                f"status must be one of {LIFECYCLE_STATUSES}, got {self.status!r}")
        params = self.parameters
        if not isinstance(params, dict):
            raise ExplorationPolicyError("parameters must be an object")
        order = params.get("order")
        if (not isinstance(order, list) or not order
                or sorted(order) != sorted(ACTIONS.keys())):
            raise ExplorationPolicyError(
                f"parameters.order must be a permutation of {sorted(ACTIONS.keys())}")
        retry = params.get("retry")
        if not isinstance(retry, dict):
            raise ExplorationPolicyError("parameters.retry must be an object")
        if retry.get("action") not in ACTIONS:
            raise ExplorationPolicyError("parameters.retry.action must be an approved action key")
        at_most = retry.get("at_most")
        if at_most not in (0, 1):
            raise ExplorationPolicyError("parameters.retry.at_most must be 0 or 1")
        if self.constraints != CONSTRAINT_ECHO:
            raise ExplorationPolicyError(
                "constraints must echo the approved D2 policy constraints verbatim; "
                "candidates cannot modify scope, budgets, or governance")

    # ── deterministic serialization + identity ──────────────────────────

    def canonical_dict(self) -> Dict[str, Any]:
        """Every identity-bearing field, sorted keys, no hash field.

        RSI-1 lineage fields are identity-bearing ONLY when set; unset fields
        are omitted so pre-RSI-1 v0 policies keep their exact hashes."""
        d = {
            "constraints": self.constraints,
            "created_by": self.created_by,
            "evidence_refs": list(self.evidence_refs),
            "evaluation_refs": list(self.evaluation_refs),
            "motivation": self.motivation,
            "parameters": self.parameters,
            "parent_version": self.parent_version,
            "policy_id": self.policy_id,
            "schema_version": self.schema_version,
            "status": self.status,
            "version": self.version,
        }
        if self.parent_policy_hash:
            d["parent_policy_hash"] = self.parent_policy_hash
        if self.hypothesis_id:
            d["hypothesis_id"] = self.hypothesis_id
        if self.experiment_id:
            d["experiment_id"] = self.experiment_id
        if self.change_description:
            d["change_description"] = self.change_description
        return d

    def content_hash(self) -> str:
        canonical = json.dumps(self.canonical_dict(), sort_keys=True,
                               separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = self.canonical_dict()
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplorationPolicy":
        declared = data.get("content_hash")
        known = data.pop("content_hash", None)
        try:
            policy = cls(
                policy_id=data["policy_id"], version=data["version"],
                status=data["status"], created_by=data["created_by"],
                motivation=data["motivation"], parameters=data["parameters"],
                constraints=data.get("constraints", dict(CONSTRAINT_ECHO)),
                schema_version=data.get("schema_version", SCHEMA_VERSION),
                parent_version=data.get("parent_version", 0),
                evidence_refs=tuple(data.get("evidence_refs", ())),
                evaluation_refs=tuple(data.get("evaluation_refs", ())),
                parent_policy_hash=str(data.get("parent_policy_hash", "") or ""),
                hypothesis_id=str(data.get("hypothesis_id", "") or ""),
                experiment_id=str(data.get("experiment_id", "") or ""),
                change_description=str(data.get("change_description", "") or ""),
            )
        except KeyError as exc:
            raise ExplorationPolicyError(f"policy missing field {exc}") from None
        policy.validate()
        actual = policy.content_hash()
        if known is not None and known != actual:
            raise ExplorationPolicyError(
                f"content_hash mismatch: declared {known!r}, content hashes to {actual!r} — "
                "the same identity may never refer to different policy content")
        return policy

    # ── derived mission material (the only thing a candidate influences) ─

    def ordered_action_keys(self) -> Tuple[str, ...]:
        """Action keys in the candidate's declared execution order, plus the
        single permitted retry step when the candidate declares one."""
        keys = tuple(self.parameters["order"])
        retry = self.parameters["retry"]
        if retry["at_most"] == 1:
            keys = keys + (retry["action"],)
        return keys
