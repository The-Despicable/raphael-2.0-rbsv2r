"""
stages.py — minimal stage handlers (P3.0 CONV-1: real CapabilityBroker)

Per v4 §13.3 P2.2: "Wire minimal handlers for: observation, WorldModel
read, Student candidate generation in recording mode, Planner request
generation, Broker call, PEP invocation, receipt emission, minimal
WorldModel integration, minimal contradiction/failure trigger, replan."

CONV-1 (P3.0): stage_broker now calls the real brain CapabilityBroker
via broker.propose_action(). The G2-C2 fail-closed hardening is
preserved (missing broker, exception, denial).

INV-2: every ExecutionEvent carries the CapabilityBroker's action_id
as the decision_id. The EvidenceReceipt links event_id to decision_id.
"""
from __future__ import annotations
import time
from typing import Any, Optional

from orchestrator.runtime.types import (
    ActionRequest,
    ExecutionEvent,
    PolicyDecision,
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


def _map_receipt_to_decision(receipt: Any, request: ActionRequest) -> PolicyDecision:
    """Map a CapabilityBroker ActionReceipt to a Runtime PolicyDecision.

    CONV-1: the CapabilityBroker is the single canonical PDP. Its
    ActionReceipt carries the decision_id (receipt.action_id) that
    INV-2 requires for event->decision linkage.
    """
    from orchestrator.brain.capability_broker import ActionProposalStatus, AuthorizationDecision
    is_authorized = receipt.status == ActionProposalStatus.AUTHORIZED
    return PolicyDecision(
        decision_id=receipt.action_id,  # INV-2: decision_id for linkage
        action_id=request.action_id,
        decision="allow" if is_authorized else "deny",
        reason=receipt.reason or "",
        constraints={},
        policy_name="CapabilityBroker",
        policy_version="brain-v4.1",
    )


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
    """Student candidate generation in RECORDING MODE ONLY."""
    t0 = time.time()
    output = {"mode": "recording", "candidates_proposed": 0}
    return StageResult.make(
        stage_name=STAGE_STUDENT_CANDIDATE,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_planner_request(ctx: dict) -> StageResult:
    """Planner request generation. Produces an ActionRequest."""
    t0 = time.time()
    request = ActionRequest(
        action_type="safe_proving_capability",
        target="system_info.name",
        args={"read_only": True},
        rationale="CONV-1 P3.0: deterministic safe-proving inspection via real Broker",
    )
    return StageResult.make(
        stage_name=STAGE_PLANNER_REQUEST,
        success=True,
        output={"request": request},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_broker(ctx: dict) -> StageResult:
    """Broker call. Authorizes the ActionRequest against the real brain
    CapabilityBroker (CONV-1).

    G2-C2 fail-closed hardening (preserved from P2.1, re-proven against
    the real Broker):
    - missing broker -> fail with explicit error
    - broker.propose_action() exception -> fail with explicit error
    - decision is None or != 'allow' -> fail with explicit error
    """
    t0 = time.time()
    broker = ctx.get("broker")
    request: ActionRequest = ctx["planner_request"]["request"]
    if broker is None:
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": None},
            error="CONV-1 G3-EN-4 fail-closed: no broker bound",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    try:
        receipt = broker.propose_action(
            target=request.target,
            action_type=request.action_type,
            capability=ctx.get("capability_name", "fixture.inspect"),
            method="inspect",
            impact_estimate=0.0,
        )
    except Exception as exc:
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": None},
            error=f"CONV-1 G3-EN-4 fail-closed: broker raised {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    decision = _map_receipt_to_decision(receipt, request)
    if decision.decision != "allow":
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": decision},
            error=(
                f"CONV-1 G3-EN-4 fail-closed: denied by real Broker "
                f"(class='{request.action_type}', "
                f"reason='{decision.reason}')"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    return StageResult.make(
        stage_name=STAGE_BROKER,
        success=True,
        output={"decision": decision, "receipt": receipt},
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
    # CONV-3 gating: record broker authorization before invoking the
    # capability. The capability checks that record_authorization was
    # called for this target; if not, it raises CapabilityNotGatedError.
    capability.record_authorization(request.target)
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
    """Minimal WorldModel integration."""
    t0 = time.time()
    receipt = ctx["receipt"]["receipt"]
    return StageResult.make(
        stage_name=STAGE_WORLDMODEL_INTEGRATE,
        success=True,
        output={"integrated": True, "receipt_id": receipt.receipt_id},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_contradiction(ctx: dict) -> StageResult:
    """Minimal contradiction/failure trigger (P2.1 deterministic rule)."""
    t0 = time.time()
    output = {"triggered": False, "rule": "p3.0.deterministic.no_contradiction"}
    return StageResult.make(
        stage_name=STAGE_CONTRADICTION,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_replan(ctx: dict) -> StageResult:
    """Replan stage. P3.0 walking skeleton: no replan needed."""
    t0 = time.time()
    return StageResult.make(
        stage_name=STAGE_REPLAN,
        success=True,
        output={"replanned": False, "reason": "P3.0 walking skeleton terminates after one iteration"},
        duration_ms=(time.time() - t0) * 1000.0,
    )


# Canonical stage order (P3.0 walking skeleton)
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
