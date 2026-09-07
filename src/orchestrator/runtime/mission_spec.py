"""
mission_spec.py — P4.1 first-class mission modeling (§15.1, P4.1 Mission model).

Provides MissionSpec (mission identity, objectives, target envelope,
constraints, halt conditions), the canonical P4 Scope name, and the
per-decision AuthorizationContext.

Architecture notes (frozen topology preserved):
- These are data/modeling structures and integration contracts, NOT a
  control plane. Nothing here authorizes, executes, or mutates policy.
- Scope enforcement stays in ScopeV0.covers(), consulted at the broker
  stage as a conjunction. ``Scope`` is the canonical P4 name for that
  same proven implementation — one model, not two evaluators.
- AuthorizationContext is derived fresh per Broker decision from the
  current Mission + Scope + ActionSpec. It is frozen data subordinate
  to the Broker's stored authorization decision; it carries no
  allow/deny methods and cannot authorize anything.
- No primitives, no I/O, no Arena imports: this module is INV-1 safe
  (dataclasses + stdlib only).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from orchestrator.runtime.scope import ScopeV0

# Canonical P4 Scope name (§15.1, P4.2 entry). This is the SAME proven
# ScopeV0 implementation under its P4 canonical name — one model, one
# evaluator (ScopeV0.covers at the broker stage). ScopeV0 remains the
# versioned implementation name; new code should reference Scope.
Scope = ScopeV0


def _freeze_str_tuple(name: str, values: Any) -> tuple:
    """Validate a list/tuple of non-empty strings into a tuple."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"MissionSpec: '{name}' must be a list/tuple of strings")
    frozen = tuple(v for v in values)
    if not frozen:
        raise ValueError(f"MissionSpec: '{name}' must declare at least one entry")
    for v in frozen:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"MissionSpec: '{name}' entries must be non-empty strings")
    return frozen


@dataclass(frozen=True)
class HaltConditions:
    """Declarative episode halt conditions (P4.1 mission model)."""
    max_iterations: int = 1
    action_cap: int = 1
    require_scope: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.max_iterations, bool) or not isinstance(self.max_iterations, int):
            raise ValueError("HaltConditions: 'max_iterations' must be an int")
        if self.max_iterations < 1:
            raise ValueError("HaltConditions: 'max_iterations' must be >= 1")
        if isinstance(self.action_cap, bool) or not isinstance(self.action_cap, int):
            raise ValueError("HaltConditions: 'action_cap' must be an int")
        if self.action_cap < 1:
            raise ValueError("HaltConditions: 'action_cap' must be >= 1")
        if not isinstance(self.require_scope, bool):
            raise ValueError("HaltConditions: 'require_scope' must be a bool")

    def to_dict(self) -> dict:
        return {
            "max_iterations": self.max_iterations,
            "action_cap": self.action_cap,
            "require_scope": self.require_scope,
        }

    @staticmethod
    def from_dict(data: Mapping) -> "HaltConditions":
        if not isinstance(data, Mapping):
            raise ValueError("HaltConditions: serialized halt must be a mapping")
        unknown = set(data.keys()) - {"max_iterations", "action_cap", "require_scope"}
        if unknown:
            raise ValueError(f"HaltConditions: unknown halt fields: {sorted(unknown)}")
        return HaltConditions(
            max_iterations=data.get("max_iterations", 1),
            action_cap=data.get("action_cap", 1),
            require_scope=data.get("require_scope", False),
        )


@dataclass(frozen=True)
class MissionSpec:
    """First-class operator mission specification (P4.1, §15.1).

    Identity + objectives + target envelope + constraints + halt
    conditions. Frozen (shallow: the constraints mapping itself is
    stored by reference and must be treated as read-only by callers,
    consistent with ActionRequest.args elsewhere in the codebase).
    """
    mission_id: str
    name: str = ""
    objectives: tuple = ()
    targets: tuple = ()
    constraints: Mapping = field(default_factory=dict)
    halt: HaltConditions = field(default_factory=HaltConditions)
    scope: Optional[ScopeV0] = None

    def __post_init__(self) -> None:
        if not isinstance(self.mission_id, str) or not self.mission_id.strip():
            raise ValueError("MissionSpec: 'mission_id' must be a non-empty string")
        object.__setattr__(self, "mission_id", self.mission_id.strip())
        if not isinstance(self.name, str):
            raise ValueError("MissionSpec: 'name' must be a string")
        object.__setattr__(self, "objectives", _freeze_str_tuple("objectives", self.objectives))
        object.__setattr__(self, "targets", _freeze_str_tuple("targets", self.targets))
        if not isinstance(self.constraints, Mapping):
            raise ValueError("MissionSpec: 'constraints' must be a mapping")
        if not isinstance(self.halt, HaltConditions):
            raise ValueError("MissionSpec: 'halt' must be a HaltConditions")
        if self.scope is not None and not isinstance(self.scope, ScopeV0):
            raise ValueError("MissionSpec: 'scope' must be a ScopeV0/Scope or None")

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "objectives": list(self.objectives),
            "targets": list(self.targets),
            "constraints": dict(self.constraints),
            "halt": self.halt.to_dict(),
            "scope": self.scope.to_dict() if self.scope is not None else None,
        }

    @staticmethod
    def from_dict(data: Mapping) -> "MissionSpec":
        """Strict reconstruction: unknown fields fail closed."""
        if not isinstance(data, Mapping):
            raise ValueError("MissionSpec: serialized mission must be a mapping")
        allowed = {"mission_id", "name", "objectives", "targets",
                   "constraints", "halt", "scope"}
        unknown = set(data.keys()) - allowed
        if unknown:
            raise ValueError(f"MissionSpec: unknown mission fields: {sorted(unknown)}")
        if "mission_id" not in data:
            raise ValueError("MissionSpec: 'mission_id' is required")
        scope = data.get("scope")
        if isinstance(scope, Mapping):
            scope = ScopeV0.from_dict(dict(scope))
        elif scope is not None and not isinstance(scope, ScopeV0):
            raise ValueError("MissionSpec: 'scope' must be a ScopeV0/Scope, mapping, or None")
        halt = data.get("halt", {})
        if isinstance(halt, Mapping):
            halt = HaltConditions.from_dict(halt)
        elif halt is None:
            halt = HaltConditions()
        constraints = data.get("constraints", {})
        if constraints is None:
            constraints = {}
        return MissionSpec(
            mission_id=data["mission_id"],
            name=data.get("name", ""),
            objectives=tuple(data.get("objectives", ())),
            targets=tuple(data.get("targets", ())),
            constraints=constraints,
            halt=halt,
            scope=scope,
        )


@dataclass(frozen=True)
class AuthorizationContext:
    """Per-decision authorization context (P4.1, §15.1).

    Derived fresh by the broker stage for EACH Broker decision from the
    current Mission + Scope + ActionSpec. Frozen data subordinate to the
    Broker's stored authorization decision.

    This object has NO allow/deny methods and performs NO evaluation:
    it records the derivation inputs and the Broker's decision so that
    mission → scope → request → decision → execution → evidence stays
    machine-traceable. It cannot authorize anything by construction
    (frozen dataclass, no PDP reference, no evaluation logic).
    """
    mission_id: str = ""
    scope_hash: str = ""
    action_id: str = ""
    action_type: str = ""
    target: str = ""
    capability: str = ""
    method: str = ""
    argv: tuple = ()
    impact_estimate: float = 0.0
    decision_id: str = ""
    decision: str = "deny"
    reason: str = ""
    derived_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "scope_hash": self.scope_hash,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target": self.target,
            "capability": self.capability,
            "method": self.method,
            "argv": list(self.argv),
            "impact_estimate": self.impact_estimate,
            "decision_id": self.decision_id,
            "decision": self.decision,
            "reason": self.reason,
            "derived_at": self.derived_at,
        }
