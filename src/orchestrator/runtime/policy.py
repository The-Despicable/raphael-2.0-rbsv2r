"""
policy.py — bootstrap-v0 policy loader and CapabilityBroker factory (CONV-1)

Per v4.1 AM-13.2: "define and commit a minimal named, versioned policy
artifact (bootstrap-v0) that the P2 Broker-mediated mock path and the
P2.4 safe capability authorize against."

CONV-1 (P3.0): BootstrapPolicy is RETIRED from the decision role.
The Runtime now uses the real brain CapabilityBroker as the single
canonical PDP. This module retains the bootstrap-v0 JSON loader and
provides a factory for constructing a CapabilityBroker with a
BrokerPolicy derived from bootstrap-v0 rules.

bootstrap-v0 rules (from policies/bootstrap-v0.json):
- BOOT-001: mock_capability (allow, read-only, no_subprocess)
- BOOT-002: safe_proving_capability (allow, read_only_fixture_inspection)
- BOOT-003: stage_observation (allow, no_execution)
- BOOT-004: worldmodel_read (allow, read-only)
- BOOT-005: receipt_emission (allow, decision_id_required)
- default_decision: deny

The CapabilityBroker uses its own authorization dimensions
(target, action_type, capability, method, impact_estimate, rate,
scope) per v4 §5.2. The bootstrap-v0 rules are mapped to BrokerPolicy
fields:
- allowed_action_types: from BOOT rule action_classes
- allowed_capabilities: derived from the capability used at runtime
- allowed_targets: ["*"] (all targets allowed in the walking skeleton)
- max_impact_per_action: 0.0 (read-only capabilities have zero impact)

Per GLM authorization: "BootstrapPolicy retired from the *decision
role* (loader/policy-input mechanics are the lane's; physical
deletion is P9)."
"""
import json
from pathlib import Path
from typing import Optional

from orchestrator.brain.capability_broker import (
    BrokerPolicy,
    CapabilityBroker,
)


POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "bootstrap-v0.json"


class BootstrapPolicy:
    """Loader for bootstrap-v0 JSON. CONV-1: not the decision source.

    This class is retained for the loader/policy-input mechanics
    (extracting the bootstrap-v0 JSON into a BrokerPolicy). It is
    NOT the decision source — the CapabilityBroker is.
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or POLICY_PATH
        self._data = self._load()
        self.name: str = self._data.get("policy_name", "bootstrap-v0")
        self.version: str = self._data.get("version", "0")
        self._rules = {r["action_class"]: r for r in self._data.get("rules", [])}

    def _load(self) -> dict:
        with open(self._path) as f:
            return json.load(f)

    @property
    def allowed_action_types(self) -> list:
        """Action classes that bootstrap-v0 allows (for BrokerPolicy)."""
        return [
            action_class
            for action_class, rule in self._rules.items()
            if rule.get("decision") == "allow"
        ]

    def to_broker_policy(
        self,
        engagement_id: str = "bootstrap-v0",
        allowed_capabilities: Optional[list] = None,
        allowed_targets: Optional[list] = None,
        max_impact_per_action: float = 0.0,
    ) -> BrokerPolicy:
        """Construct a BrokerPolicy from bootstrap-v0 rules.

        Args:
            engagement_id: Engagement identifier for the BrokerPolicy.
            allowed_capabilities: Capabilities to allow. If None, derived
                from the runtime capability name.
            allowed_targets: Targets to allow. If None, defaults to ["*"]
                (all targets, matching bootstrap-v0's no-scope-check).
            max_impact_per_action: Maximum impact per action (0-10 scale).
                Default 0.0 for read-only capabilities.
        """
        return BrokerPolicy(
            schema_version=1,
            engagement_id=engagement_id,
            allowed_targets=allowed_targets or ["*"],
            allowed_action_types=self.allowed_action_types,
            allowed_capabilities=allowed_capabilities or ["*"],
            max_impact_per_action=max_impact_per_action,
        )


def make_broker_from_bootstrap(
    capability_name: str = "fixture.inspect",
    engagement_id: str = "bootstrap-v0",
) -> CapabilityBroker:
    """Factory: create a CapabilityBroker from bootstrap-v0 rules.

    CONV-1: this is the single canonical PDP factory for the Runtime.
    The Runtime's stage_broker calls broker.propose_action() on the
    returned broker.
    """
    bp = BootstrapPolicy()
    broker_policy = bp.to_broker_policy(
        engagement_id=engagement_id,
        allowed_capabilities=[capability_name, "*"],
        allowed_targets=["*"],
    )
    return CapabilityBroker(broker_policy)
