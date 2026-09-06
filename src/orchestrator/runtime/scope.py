"""
scope.py — Scope v0 mission-boundary contract (§14.6).

Scope v0 makes the mission boundary explicit before execution:
  1. what mission is being executed (mission_id)
  2. what targets/resources are in scope (targets)
  3. what action/capability classes are permitted (allowed_* lists)
  4. what action/capability classes are prohibited or absent (prohibited_* lists)
  5. relevant scope constraints for the Broker/PEP path (max_impact)
  6. deterministic validation of whether an operation is inside or
     outside the declared scope (covers())
  7. fail-closed behavior for missing, malformed, or out-of-scope scope

Scope is NOT authorization. Correct relationship:

    Mission Scope (declared boundary)
        -> Broker evaluates capability request (sole PDP)
        -> PEP enforces authorized execution (sole enforcement point)

A scope-valid action is NOT automatically allowed. A Broker-approved
action must still be constrained by the scope (conjunction at the
broker stage). Scope defines the boundary; the Broker decides.

Design notes:
- Frozen dataclass + tuples: a validated scope cannot be widened by
  runtime mutation (no setters, no append, defensive copies).
- stdlib only: Scope never touches subprocess/network/files, never
  issues authorization, never calls the Broker/PEP/WorldModel.
- Fail-closed: empty allow-lists deny; prohibited wins over allowed;
  malformed declarations raise ScopeError at construction.
"""

from __future__ import annotations

import fnmatch
import hashlib
import ipaddress
import json
from dataclasses import dataclass, field
from typing import Any, Optional

SCOPE_VERSION = "v0"


class ScopeError(Exception):
    """Raised when a Scope v0 declaration is missing or malformed (fail-closed)."""
    pass


def _freeze_str_list(name: str, values: Any) -> tuple:
    """Validate a string-list field and return it as a tuple (defensive copy)."""
    if values is None:
        return ()
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        raise ScopeError(f"Scope v0: '{name}' must be a list/tuple of strings")
    frozen = []
    for entry in values:
        if not isinstance(entry, str) or not entry.strip():
            raise ScopeError(f"Scope v0: '{name}' entries must be non-empty strings")
        frozen.append(entry.strip())
    return tuple(frozen)


def _target_matches(target: str, pattern: str) -> bool:
    """Match a target against a scope pattern (exact, CIDR, wildcard)."""
    if target == pattern:
        return True
    if "/" in pattern:
        try:
            return ipaddress.ip_address(target) in ipaddress.ip_network(
                pattern, strict=False
            )
        except ValueError:
            return False
    if "*" in pattern:
        return fnmatch.fnmatch(target, pattern)
    return False


@dataclass(frozen=True)
class ScopeV0:
    """Immutable, validated mission-boundary contract (§14.6 Scope v0)."""

    mission_id: str
    targets: tuple = ()
    allowed_action_types: tuple = ()
    prohibited_action_types: tuple = ()
    allowed_capabilities: tuple = ()
    prohibited_capabilities: tuple = ()
    max_impact: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.mission_id, str) or not self.mission_id.strip():
            raise ScopeError("Scope v0: 'mission_id' must be a non-empty string")
        object.__setattr__(self, "mission_id", self.mission_id.strip())

        targets = _freeze_str_list("targets", self.targets)
        if not targets:
            raise ScopeError("Scope v0: 'targets' must declare at least one target")
        for entry in targets:
            if "/" in entry:
                try:
                    ipaddress.ip_network(entry, strict=False)
                except ValueError:
                    raise ScopeError(f"Scope v0: malformed CIDR target: {entry!r}")
        object.__setattr__(self, "targets", targets)

        allowed_actions = _freeze_str_list("allowed_action_types", self.allowed_action_types)
        prohibited_actions = _freeze_str_list(
            "prohibited_action_types", self.prohibited_action_types
        )
        allowed_caps = _freeze_str_list("allowed_capabilities", self.allowed_capabilities)
        prohibited_caps = _freeze_str_list(
            "prohibited_capabilities", self.prohibited_capabilities
        )
        overlap = set(allowed_actions) & set(prohibited_actions)
        if overlap:
            raise ScopeError(
                f"Scope v0: contradictory action types (allowed and prohibited): "
                f"{sorted(overlap)}"
            )
        overlap = set(allowed_caps) & set(prohibited_caps)
        if overlap:
            raise ScopeError(
                f"Scope v0: contradictory capabilities (allowed and prohibited): "
                f"{sorted(overlap)}"
            )
        object.__setattr__(self, "allowed_action_types", allowed_actions)
        object.__setattr__(self, "prohibited_action_types", prohibited_actions)
        object.__setattr__(self, "allowed_capabilities", allowed_caps)
        object.__setattr__(self, "prohibited_capabilities", prohibited_caps)

        if isinstance(self.max_impact, bool) or not isinstance(
            self.max_impact, (int, float)
        ):
            raise ScopeError("Scope v0: 'max_impact' must be a number")
        if not self.max_impact >= 0:
            raise ScopeError("Scope v0: 'max_impact' must be >= 0")
        object.__setattr__(self, "max_impact", float(self.max_impact))

    def covers(
        self,
        target: str,
        action_type: str,
        capability: str,
        impact_estimate: float = 0.0,
    ) -> "tuple[bool, str]":
        """Deterministic inside/outside-scope check. Pure: no I/O, no state change."""
        if not isinstance(target, str) or not target:
            return False, "Scope v0: missing target"
        if not any(_target_matches(target, allowed) for allowed in self.targets):
            return False, f"Scope v0: target outside declared scope: {target}"
        if action_type in self.prohibited_action_types:
            return False, f"Scope v0: action type explicitly prohibited: {action_type}"
        if not self.allowed_action_types:
            return False, "Scope v0: no action types allowed (empty allowed list)"
        if action_type not in self.allowed_action_types:
            return False, f"Scope v0: action type not in declared scope: {action_type}"
        if capability in self.prohibited_capabilities:
            return False, f"Scope v0: capability explicitly prohibited: {capability}"
        if not self.allowed_capabilities:
            return False, "Scope v0: no capabilities allowed (empty allowed list)"
        if capability not in self.allowed_capabilities:
            return False, f"Scope v0: capability not in declared scope: {capability}"
        try:
            impact = float(impact_estimate)
        except (TypeError, ValueError):
            return False, "Scope v0: malformed impact estimate"
        if impact > self.max_impact:
            return False, "Scope v0: impact exceeds declared max"
        return True, f"Scope v0: operation inside declared scope ({self.mission_id})"

    def to_dict(self) -> dict:
        """Stable serialization (fixed key order) for evidence comparison."""
        return {
            "scope_version": SCOPE_VERSION,
            "mission_id": self.mission_id,
            "targets": list(self.targets),
            "allowed_action_types": list(self.allowed_action_types),
            "prohibited_action_types": list(self.prohibited_action_types),
            "allowed_capabilities": list(self.allowed_capabilities),
            "prohibited_capabilities": list(self.prohibited_capabilities),
            "max_impact": self.max_impact,
        }

    @staticmethod
    def from_dict(data: dict) -> "ScopeV0":
        """Strict reconstruction: unknown or missing fields fail closed."""
        if not isinstance(data, dict):
            raise ScopeError("Scope v0: serialized scope must be a mapping")
        allowed_keys = {
            "scope_version",
            "mission_id",
            "targets",
            "allowed_action_types",
            "prohibited_action_types",
            "allowed_capabilities",
            "prohibited_capabilities",
            "max_impact",
        }
        unknown = set(data.keys()) - allowed_keys
        if unknown:
            raise ScopeError(f"Scope v0: unknown scope fields: {sorted(unknown)}")
        version = data.get("scope_version", SCOPE_VERSION)
        if version != SCOPE_VERSION:
            raise ScopeError(f"Scope v0: unsupported scope version: {version!r}")
        if "mission_id" not in data or "targets" not in data:
            raise ScopeError("Scope v0: 'mission_id' and 'targets' are required")
        kwargs = {k: v for k, v in data.items() if k != "scope_version"}
        return ScopeV0(**kwargs)

    def scope_hash(self) -> str:
        """Deterministic hash of the canonical serialization."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
