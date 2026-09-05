"""
stages.py — minimal stage handlers (P2.1 walking skeleton)

Per v4 §13.3 P2.2: "Wire minimal handlers for: observation, WorldModel
read, Student candidate generation in recording mode, Planner request
generation, Broker call, PEP invocation, receipt emission, minimal
WorldModel integration, minimal contradiction/failure trigger, replan."

These are minimal, deterministic handlers for the P2.1 walking
skeleton. They compose Head 2 organs without rewriting them.

The Student is in recording mode only (P2.1 is not P6).
The contradiction/failure trigger is its own deterministic rule
(v4 §13.3 / §14.7) and does NOT exercise D-5 transitions.
The D-5 port remains unbound (GLM §4, P5-BIND-1).
"""
from __future__ import annotations
import time
from typing import Any, Optional

from orchestrator.runtime.types import (
    ActionRequest,
    ExecutionEvent,
    StageResult,
)


# Stage names (canonical, used in DecisionTrace)
STAGE_OBSERVE = "observe"
STAGE_WORLDMODEL_READ = "worldmodel_read"
STAGE_STUDENT_CANDIDATE = "student_candidate"
STAGE_PLANNER_REQUEST = "planner_request"
STAGE_BROKER = "broker"
STAGE_PEP = "pep"
STAGE_RECEIPT = "receipt"
STAGE_WORLDMODEL_INTEGRATE = "worldmodel_integrate"
STAGE_CONTRADICTION = "contradiction"
STAGE_REPLAN = "replan"


def stage_observe(ctx: dict) -> StageResult:
    """Observation stage. Reads the mission view."""
    t0 = time.time()
    view = ctx.get("view", {})
    output = {"view_keys": sorted(view.keys()) if isinstance(view, dict) else []}
    return StageResult.make(
        stage_name=STAGE_OBSERVE,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_worldmodel_read(ctx: dict) -> StageResult:
    """WorldModel read. Returns the current world view (read-only)."""
    t0 = time.time()
    wm = ctx.get("world_model")
    output = {"available": wm is not None, "entities": 0}
    return StageResult.make(
        stage_name=STAGE_WORLDMODEL_READ,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_student_candidate(ctx: dict) -> StageResult:
    """Student candidate generation in RECORDING MODE ONLY.

    P2.1 does not exercise Student learning. This stage records that
    Student was consulted but does not mutate strategy state.
    """
    t0 = time.time()
    output = {"mode": "recording", "candidates_proposed": 0}
    return StageResult.make(
        stage_name=STAGE_STUDENT_CANDIDATE,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_planner_request(ctx: dict) -> StageResult:
    """Planner request generation. Produces an ActionRequest.

    For the P2.1 walking skeleton, the Planner is exercised but the
    request is the deterministic safe-proving inspection request.
    No domain logic; no LLM.
    """
    t0 = time.time()
    request = ActionRequest(
        action_type="safe_proving_capability",
        target="system_info.name",
        args={"read_only": True},
        rationale="P2.1 walking skeleton: deterministic safe-proving inspection",
    )
    return StageResult.make(
        stage_name=STAGE_PLANNER_REQUEST,
        success=True,
        output={"request": request},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_broker(ctx: dict) -> StageResult:
    """Broker call. Authorizes the ActionRequest against bootstrap-v0."""
    t0 = time.time()
    policy = ctx.get("policy")
    request: ActionRequest = ctx["planner_request"]["request"]
    decision = policy.authorize(request) if policy is not None else None
    return StageResult.make(
        stage_name=STAGE_BROKER,
        success=decision is not None and decision.decision == "allow",
        output={"decision": decision},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_pep(ctx: dict) -> StageResult:
    """PEP invocation. Calls the capability, emits an ExecutionEvent."""
    t0 = time.time()
    capability = ctx.get("capability")
    decision = ctx["broker"]["decision"]
    request: ActionRequest = ctx["planner_request"]["request"]
    if capability is None or decision is None or decision.decision != "allow":
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error="Capability or decision not available",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    result = capability.inspect(request.target)
    event = ExecutionEvent(
        action_id=request.action_id,
        decision_id=decision.decision_id,
        capability=result.capability,
        target=result.target,
        args=request.args,
        outcome="ok" if result.output is not None else "not_found",
        output=result.output,
    )
    return StageResult.make(
        stage_name=STAGE_PEP,
        success=True,
        output={"event": event, "result": result},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_receipt(ctx: dict) -> StageResult:
    """Receipt emission. Links ExecutionEvent to PolicyDecision."""
    t0 = time.time()
    from orchestrator.runtime.types import EvidenceReceipt
    event: ExecutionEvent = ctx["pep"]["event"]
    decision = ctx["broker"]["decision"]
    receipt = EvidenceReceipt(
        event_id=event.event_id,
        decision_id=decision.decision_id,
        summary=f"PEP minted receipt for {event.capability} -> {event.target}",
    )
    return StageResult.make(
        stage_name=STAGE_RECEIPT,
        success=True,
        output={"receipt": receipt},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_worldmodel_integrate(ctx: dict) -> StageResult:
    """Minimal WorldModel integration. Appends the receipt to the trace.

    P2.1 does not implement WorldModel mutation; this stage records
    the integration intent.
    """
    t0 = time.time()
    receipt = ctx["receipt"]["receipt"]
    return StageResult.make(
        stage_name=STAGE_WORLDMODEL_INTEGRATE,
        success=True,
        output={"integrated": True, "receipt_id": receipt.receipt_id},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_contradiction(ctx: dict) -> StageResult:
    """Minimal contradiction/failure trigger (P2.1 deterministic rule).

    Per v4 §13.3 / §14.7: the P2 minimal contradiction/failure trigger
    is its own deterministic rule and does NOT exercise D-5 transitions.
    """
    t0 = time.time()
    output = {"triggered": False, "rule": "p2.1.deterministic.no_contradiction"}
    return StageResult.make(
        stage_name=STAGE_CONTRADICTION,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_replan(ctx: dict) -> StageResult:
    """Replan stage. P2.1 walking skeleton: no replan needed."""
    t0 = time.time()
    return StageResult.make(
        stage_name=STAGE_REPLAN,
        success=True,
        output={"replanned": False, "reason": "P2.1 walking skeleton terminates after one iteration"},
        duration_ms=(time.time() - t0) * 1000.0,
    )


# Canonical stage order (P2.1 walking skeleton)
STAGE_ORDER = [
    STAGE_OBSERVE,
    STAGE_WORLDMODEL_READ,
    STAGE_STUDENT_CANDIDATE,
    STAGE_PLANNER_REQUEST,
    STAGE_BROKER,
    STAGE_PEP,
    STAGE_RECEIPT,
    STAGE_WORLDMODEL_INTEGRATE,
    STAGE_CONTRADICTION,
    STAGE_REPLAN,
]


STAGE_HANDLERS = {
    STAGE_OBSERVE: stage_observe,
    STAGE_WORLDMODEL_READ: stage_worldmodel_read,
    STAGE_STUDENT_CANDIDATE: stage_student_candidate,
    STAGE_PLANNER_REQUEST: stage_planner_request,
    STAGE_BROKER: stage_broker,
    STAGE_PEP: stage_pep,
    STAGE_RECEIPT: stage_receipt,
    STAGE_WORLDMODEL_INTEGRATE: stage_worldmodel_integrate,
    STAGE_CONTRADICTION: stage_contradiction,
    STAGE_REPLAN: stage_replan,
}
