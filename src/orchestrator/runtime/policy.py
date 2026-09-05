"""
policy.py — bootstrap-v0 policy loader (P2.1 walking skeleton)

Per v4.1 AM-13.2: "define and commit a minimal named, versioned policy
artifact (bootstrap-v0) that the P2 Broker-mediated mock path and the
P2.4 safe capability authorize against."

The Runtime loads bootstrap-v0 at construction and uses it to make
Broker-mediated authorization decisions.

bootstrap-v0 rules (from policies/bootstrap-v0.json):
- BOOT-001: mock_capability (allow, read-only, no_subprocess)
- BOOT-002: safe_proving_capability (allow, read_only_fixture_inspection)
- BOOT-003: stage_observation (allow, no_execution)
- BOOT-004: worldmodel_read (allow, read-only)
- BOOT-005: receipt_emission (allow, decision_id_required)
- default_decision: deny
"""
import json
from pathlib import Path
from typing import Optional

from orchestrator.runtime.types import ActionRequest, PolicyDecision


POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "bootstrap-v0.json"


class BootstrapPolicy:
    """In-memory representation of bootstrap-v0."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or POLICY_PATH
        self._data = self._load()
        self.name: str = self._data.get("policy_name", "bootstrap-v0")
        self.version: str = self._data.get("version", "0")
        self.default_decision: str = self._data.get("default_decision", "deny")
        self._rules = {r["action_class"]: r for r in self._data.get("rules", [])}

    def _load(self) -> dict:
        with open(self._path) as f:
            return json.load(f)

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        """Make an authorization decision for the given request.

        Per bootstrap-v0: match request.action_type against rules.
        If matched and constraints satisfied -> allow.
        Otherwise -> deny.
        """
        rule = self._rules.get(request.action_type)
        decision = PolicyDecision(
            action_id=request.action_id,
            decision=self.default_decision,
            reason=f"No rule for action_class='{request.action_type}' (default: deny)",
            policy_name=self.name,
            policy_version=self.version,
        )
        if rule is not None and rule.get("decision") == "allow":
            decision.decision = "allow"
            decision.reason = f"bootstrap-v0 rule {rule['rule_id']} allows '{request.action_type}'"
            decision.constraints = dict(rule.get("constraints", {}))
        return decision
