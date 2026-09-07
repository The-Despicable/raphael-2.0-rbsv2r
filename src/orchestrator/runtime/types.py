"""
types.py — Runtime type contracts (P2.1 walking skeleton)

Per v4 §13.2: at minimum, define conceptual contracts for:
- RuntimeContext
- MissionContext
- StageResult
- ActionRequest
- PolicyDecision
- ExecutionEvent
- EvidenceReceipt
- LoopTermination

These are the data shapes the Runtime sequencer passes between stages.
They are intentionally narrow and stable. Brain organs return these;
the Runtime emits them in the DecisionTrace.

No domain logic. No policy logic. No primitives.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List, TYPE_CHECKING
import time
import uuid

if TYPE_CHECKING:
    from orchestrator.runtime.scope import ScopeV0


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class RuntimeContext:
    """Immutable snapshot of the Runtime's environment at step start."""
    mission_id: str
    objective_id: str
    view: dict = field(default_factory=dict)
    iteration: int = 0
    started_at: float = field(default_factory=time.time)
    scope: Optional["ScopeV0"] = None

    @staticmethod
    def make(mission_id: str, objective_id: str, view: Optional[dict] = None) -> "RuntimeContext":
        return RuntimeContext(
            mission_id=mission_id,
            objective_id=objective_id,
            view=view or {},
        )


@dataclass
class MissionContext:
    """The mission this Runtime instance is executing."""
    mission_id: str
    name: str
    objectives: List[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    scope: Optional["ScopeV0"] = None
    # P4.3 §15: optional bound first-class MissionSpec. When present
    # (populated by from_spec), the broker stage derives the
    # AuthorizationContext from this actual spec object rather than
    # the view's mission_id string. Default None preserves legacy
    # hand-built missions. Not part of equality-sensitive identity.
    spec: Any = None
    @staticmethod
    def from_spec(spec: Any, extra_constraints: Optional[dict] = None) -> "MissionContext":
        """Build a Runtime MissionContext from a first-class MissionSpec.

        P4.1 §15.1: the spec's identity/objectives/target envelope/
        constraints/scope become the runtime context. The spec's halt
        conditions ride in constraints under the reserved "halt" key so
        run_episode can consume them; per-iteration candidate sets ride
        under the reserved "candidates" key. ``extra_constraints`` adds
        ephemeral caller keys (e.g. test-declared candidates) without
        mutating the spec. Reserved keys in extra_constraints fail
        closed rather than silently overriding the spec.
        """
        from orchestrator.runtime.mission_spec import MissionSpec as _MissionSpec
        if not isinstance(spec, _MissionSpec):
            raise ValueError("MissionContext.from_spec: 'spec' must be a MissionSpec")
        merged: dict = dict(spec.constraints)
        if extra_constraints:
            if not isinstance(extra_constraints, dict):
                raise ValueError("MissionContext.from_spec: 'extra_constraints' must be a mapping")
            for reserved in ("halt", "candidates"):
                if reserved in extra_constraints:
                    raise ValueError(
                        f"MissionContext.from_spec: reserved key '{reserved}' "
                        "must come from the MissionSpec, not extra_constraints"
                    )
            merged.update(extra_constraints)
        merged["halt"] = spec.halt.to_dict()
        return MissionContext(
            mission_id=spec.mission_id,
            name=spec.name,
            objectives=list(spec.objectives),
            constraints=merged,
            scope=spec.scope,
            spec=spec,
        )

@dataclass
class StageResult:
    """Output of a single stage. The Runtime sequencer consumes this."""
    stage_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    trace_id: str = field(default_factory=lambda: _new_id("STG"))

    @staticmethod
    def make(stage_name: str, success: bool, output: Any = None,
             error: Optional[str] = None, duration_ms: float = 0.0) -> "StageResult":
        return StageResult(
            stage_name=stage_name,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )


@dataclass
class ActionRequest:
    """What the Planner asks the Broker to authorize."""
    action_id: str = field(default_factory=lambda: _new_id("ACT"))
    action_type: str = ""
    target: str = ""
    args: dict = field(default_factory=dict)
    rationale: str = ""
    # §14.6 F1: optional planner-side capability/method metadata threaded
    # to the broker and the PEP. Existing planners that omit these get
    # the broker-stage default ("fixture.inspect" / "inspect") via the
    # capability_name context key.
    capability: str = ""
    method: str = ""

@dataclass
class PolicyDecision:
    """The Broker's allow/deny + constraints."""
    decision_id: str = field(default_factory=lambda: _new_id("PDC"))
    action_id: str = ""
    decision: str = "deny"  # "allow" | "deny"
    reason: str = ""
    constraints: dict = field(default_factory=dict)
    policy_name: str = ""
    policy_version: str = ""


@dataclass
class ExecutionEvent:
    """PEP-emitted record of a capability invocation."""
    event_id: str = field(default_factory=lambda: _new_id("EVT"))
    action_id: str = ""
    decision_id: str = ""
    capability: str = ""
    target: str = ""
    args: dict = field(default_factory=dict)
    outcome: str = ""
    output: Any = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvidenceReceipt:
    """Links an ExecutionEvent to its PolicyDecision and downstream consumers.

    P4.1 provenance depth (§15.1): the receipt additionally records the
    mission/scope identity, the authorized action dimensions (F1
    bindings, copied from the Broker's stored authorization truth —
    never re-evaluated here), and the Broker receipt id. All new fields
    default to empty so existing constructions are unchanged. Evidence
    remains non-authorizing: this object links and describes; it cannot
    permit execution.
    """
    receipt_id: str = field(default_factory=lambda: _new_id("RCP"))
    event_id: str = ""
    decision_id: str = ""
    hypothesis_id: Optional[str] = None
    summary: str = ""
    timestamp: float = field(default_factory=time.time)
    # P4.1 provenance linkage (all defaulted; populated by stage_receipt
    # from the broker-stage stored authorization + mission context).
    mission_id: str = ""
    scope_hash: str = ""
    action_type: str = ""
    target: str = ""
    capability: str = ""
    method: str = ""
    argv: tuple = ()
    broker_receipt_id: str = ""
    artifact_refs: tuple = ()

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "hypothesis_id": self.hypothesis_id,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "mission_id": self.mission_id,
            "scope_hash": self.scope_hash,
            "action_type": self.action_type,
            "target": self.target,
            "capability": self.capability,
            "method": self.method,
            "argv": list(self.argv),
            "broker_receipt_id": self.broker_receipt_id,
            "artifact_refs": list(self.artifact_refs),
        }


@dataclass
class LoopTermination:
    """Why and how the episode loop stopped."""
    terminated: bool = False
    reason: str = ""
    iterations: int = 0
    final_stage: str = ""


@dataclass
class DecisionTrace:
    """Append-only trace of a Runtime episode. Stable, inspectable."""
    trace_id: str = field(default_factory=lambda: _new_id("TRC"))
    mission_id: str = ""
    entries: List[dict] = field(default_factory=list)

    def append(self, entry: dict) -> None:
        self.entries.append(entry)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "mission_id": self.mission_id,
            "entries": list(self.entries),
        }
