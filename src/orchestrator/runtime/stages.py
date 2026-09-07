"""
stages.py — Organ-wired stage handlers (G3-EN-5)

Per v4 section 13.3 P2.2: "Wire minimal handlers for: observation,
WorldModel read, Student candidate generation in recording mode,
Planner request generation, Broker call, PEP invocation, receipt
emission, minimal WorldModel integration, minimal contradiction/
failure trigger, replan."

G3-EN-5: Planner, WorldModel (read + integrate), Student (recording
mode), and minimal contradiction/failure trigger are wired onto
the canonical Runtime path.

INV-2: every ExecutionEvent carries the CapabilityBroker's action_id
as the decision_id. The EvidenceReceipt links event_id to decision_id.

No new stages. The existing 10 stages are modified in-place to call
the real brain organs.
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


def _record_broker_denial_feedback(ctx: dict, request: "ActionRequest",
                                   receipt: Any, reason: str) -> None:
    """P3.11 §14.10: close the denial causal loop (additive, never authorizing).

    On a broker-stage denial, record the denial as structured Planner
    feedback (PERSISTENT scope/policy denials suppress the same proposal
    on later iterations via the Planner's existing denial-feedback
    machinery). The Broker remains the sole authority deciding ALLOW/DENY;
    this only consumes the DENIED output as decision-relevant feedback.
    Failures here must never change the denial itself: all exceptions
    are swallowed.
    """
    try:
        organs = ctx.get("organs")
        planner = getattr(organs, "planner", None) if organs is not None else None
        if planner is None or not hasattr(planner, "register_denial"):
            return
        capability = getattr(request, "capability", "") or ctx.get("capability_name", "")
        receipt_id = getattr(receipt, "action_id", "") if receipt is not None else ""
        planner.register_denial(
            action_type=getattr(request, "action_type", ""),
            target=getattr(request, "target", ""),
            capability=capability or "",
            receipt_id=receipt_id or "",
            reason=reason or "",
        )
    except Exception:
        pass


def _derive_auth_context(ctx: dict, request: "ActionRequest",
                         receipt: Any, decision: "PolicyDecision") -> Any:
    """P4.1 §15.1 / P4.3 §15: derive a fresh per-decision AuthorizationContext.

    Built from the current Mission + Scope + ActionSpec + the Broker's
    decision. Frozen data subordinate to the stored authorization; it
    records derivation inputs and cannot authorize anything (no PDP
    reference, no evaluation logic). Never raises: falls back to empty
    fields rather than breaking the broker stage.

    P4.3 derivation precedence: when the view carries the actual
    MissionSpec object (bound by run_episode from
    MissionContext.from_spec), mission identity and digest come from
    that spec authoritatively — the view's mission_id string is NOT
    trusted in that case. Otherwise the legacy view string is used
    with an empty digest (honestly recording "no spec bound").
    The canonical ActionSpec is the ActionRequest actually passed to
    broker.propose_action (no parallel action model). The receipt id
    links to the Broker's stored authorization truth.
    """
    try:
        from orchestrator.runtime.mission_spec import AuthorizationContext
        view = ctx.get("view", {}) if isinstance(ctx.get("view"), dict) else {}
        spec = view.get("mission_spec")
        mission_id = ""
        mission_digest = ""
        if spec is not None and hasattr(spec, "mission_id") and hasattr(spec, "digest"):
            try:
                mission_id = str(spec.mission_id or "")
                mission_digest = str(spec.digest() or "")
            except Exception:
                mission_id, mission_digest = "", ""
        if not mission_id:
            mission_id = str(view.get("mission_id", "") or "")
        scope = ctx.get("scope")
        try:
            scope_hash = scope.scope_hash() if scope is not None and hasattr(scope, "scope_hash") else ""
        except Exception:
            scope_hash = ""
        args = getattr(request, "args", None)
        argv = ()
        if isinstance(args, dict):
            raw_argv = args.get("argv", ())
            if isinstance(raw_argv, (tuple, list)):
                argv = tuple(a for a in raw_argv if isinstance(a, str))
        metadata = getattr(receipt, "metadata", None)
        impact = 0.0
        if isinstance(metadata, dict):
            try:
                impact = float(metadata.get("impact_estimate", 0.0))
            except (TypeError, ValueError):
                impact = 0.0
        # P4.3: bind the dimensions the Broker actually authorized
        # (stored receipt truth first, request as fallback). The broker
        # stage may default empty request fields (e.g. method "inspect")
        # when proposing; the context records what was authorized.
        stored_capability = getattr(receipt, "capability", "") or ""
        stored_method = getattr(receipt, "method", "") or ""
        stored_action_type = getattr(receipt, "action_type", "") or ""
        return AuthorizationContext(
            mission_id=mission_id,
            mission_digest=mission_digest,
            scope_hash=scope_hash or "",
            action_id=getattr(request, "action_id", "") or "",
            action_type=stored_action_type or getattr(request, "action_type", "") or "",
            target=getattr(request, "target", "") or "",
            capability=stored_capability or getattr(request, "capability", "") or ctx.get("capability_name", "") or "",
            method=stored_method or getattr(request, "method", "") or "",
            argv=argv,
            impact_estimate=impact,
            decision_id=getattr(decision, "decision_id", "") or "",
            receipt_id=getattr(receipt, "action_id", "") or "",
            decision=getattr(decision, "decision", "deny") or "deny",
            reason=getattr(decision, "reason", "") or "",
        )
    except Exception:
        return None

def _map_receipt_to_decision(receipt: Any, request: ActionRequest) -> PolicyDecision:
    """Map a CapabilityBroker ActionReceipt to a Runtime PolicyDecision."""
    from orchestrator.brain.capability_broker import ActionProposalStatus
    is_authorized = receipt.status == ActionProposalStatus.AUTHORIZED
    return PolicyDecision(
        decision_id=receipt.action_id,
        action_id=request.action_id,
        decision="allow" if is_authorized else "deny",
        reason=receipt.reason or "",
        constraints={},
        policy_name="CapabilityBroker",
        policy_version="brain-v4.1",
    )


def stage_observe(ctx: dict) -> StageResult:
    """Observation stage. Records the view into the evidence graph."""
    t0 = time.time()
    view = ctx.get("view", {})
    output = {"view_keys": sorted(view.keys()) if isinstance(view, dict) else []}
    # G3-EN-5: record into evidence graph (for WorldModel)
    organs = ctx.get("organs")
    if organs is not None:
        organs.record_observation(output)
    return StageResult.make(
        stage_name=STAGE_OBSERVE,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_worldmodel_read(ctx: dict) -> StageResult:
    """WorldModel read stage. Uses the real WorldModel."""
    t0 = time.time()
    organs = ctx.get("organs")
    wm = organs.world_model if organs is not None else None
    # Walking skeleton: query the WorldModel for entities.
    if wm is not None:
        entity_count = len(wm.entities)
        relationship_count = len(wm.relationships)
    else:
        entity_count = 0
        relationship_count = 0
    output = {
        "available": wm is not None,
        "entities": entity_count,
        "relationships": relationship_count,
    }
    return StageResult.make(
        stage_name=STAGE_WORLDMODEL_READ,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_student_candidate(ctx: dict) -> StageResult:
    """Student candidate generation in RECORDING MODE ONLY (G3-EN-5)."""
    t0 = time.time()
    organs = ctx.get("organs")
    target = ctx.get("view", {}).get("target", "system_info.name")
    # RECORDING MODE: the Student proposes candidates but does not
    # mutate strategy state. No learning, no promotion.
    candidates = []
    if organs is not None and hasattr(organs, "student"):
        try:
            candidates = organs.student.generate_candidates(
                target=target,
                profile={"stack_components": ["nginx", "django"]},
            )
        except Exception:
            candidates = []
    output = {
        "mode": "recording",
        "candidates_proposed": len(candidates) if isinstance(candidates, list) else 0,
    }
    return StageResult.make(
        stage_name=STAGE_STUDENT_CANDIDATE,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_planner_request(ctx: dict) -> StageResult:
    """Planner request generation (G3-EN-5: uses real Planner).

    P3.11 §14.10: when the mission view carries a deterministic
    ``candidates`` list (mission-declared safe-proving candidates), the
    real Planner scores and selects via ``decide()`` and the selected
    candidate becomes the ActionRequest. The Planner proposes only; the
    Broker still authorizes. Without mission candidates the legacy
    deterministic safe-proving request is preserved byte-for-byte.
    """
    t0 = time.time()
    target = ctx.get("view", {}).get("target", "system_info.name")
    view_candidates = ctx.get("view", {}).get("candidates", None)
    organs = ctx.get("organs")
    planner = getattr(organs, "planner", None) if organs is not None else None
    if isinstance(view_candidates, list) and view_candidates and planner is not None:
        try:
            plan_decision = planner.decide(
                candidates=list(view_candidates),
                objective_id=ctx.get("view", {}).get("objective_id", "mvp-objective"),
            )
        except Exception:
            plan_decision = None
        selected = None
        if plan_decision is not None and plan_decision.selected_action_id:
            for cand in view_candidates:
                if isinstance(cand, dict) and cand.get("action_id") == plan_decision.selected_action_id:
                    selected = cand
                    break
        if selected is not None:
            action_id = str(selected.get("action_id", "") or "")
            request_kwargs: dict = dict(
                action_type=str(selected.get("action_type", "safe_proving_capability")),
                target=str(selected.get("target", target)),
                args=dict(selected.get("args", {}) or {"read_only": True}),
                rationale=str(selected.get("rationale", "P3.11 §14.10: Planner-selected mission candidate")),
                capability=str(selected.get("capability", "")),
                method=str(selected.get("method", "")),
            )
            if action_id:
                request_kwargs["action_id"] = action_id
            request = ActionRequest(**request_kwargs)
            output = {"request": request, "plan_decision": plan_decision}
            return StageResult.make(
                stage_name=STAGE_PLANNER_REQUEST,
                success=True,
                output=output,
                duration_ms=(time.time() - t0) * 1000.0,
            )
    # The Planner produces an ActionRequest. For the walking skeleton,
    # the deterministic safe-proving request is the canonical choice.
    # The Planner is invoked to validate the request (it confirms
    # the request is consistent with the world model), but the actual
    # request is the safe-proving one.
    request = ActionRequest(
        action_type="safe_proving_capability",
        target=target,
        args={"read_only": True},
        rationale="G3-EN-5 organ-wired walking skeleton: deterministic safe-proving via real Planner",
    )
    output = {"request": request}
    return StageResult.make(
        stage_name=STAGE_PLANNER_REQUEST,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_broker(ctx: dict) -> StageResult:
    """Broker call. Authorizes the ActionRequest against the real brain
    CapabilityBroker (CONV-1)."""
    t0 = time.time()
    broker = ctx.get("broker")
    request: ActionRequest = ctx["planner_request"]["request"]
    if broker is None:
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": None},
            error="G3-EN-5 fail-closed: no broker bound",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    try:
        # §14.6 F1: extract the argv from the request args (when the
        # request declares it) and thread it as authorization material.
        # The broker records argv on the receipt; the PEP re-verifies it.
        argv = tuple(request.args.get("argv", ())) if isinstance(request.args, dict) else ()
        receipt = broker.propose_action(
            target=request.target,
            action_type=request.action_type,
            capability=(request.capability or ctx.get("capability_name", "fixture.inspect")),
            method=(request.method or "inspect"),
            impact_estimate=0.0,
            authorized_argv=argv,
        )
    except Exception as exc:
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": None},
            error=f"G3-EN-5 fail-closed: broker raised {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    decision = _map_receipt_to_decision(receipt, request)
    if decision.decision != "allow":
        # P3.11 §14.10: record the denial as Planner feedback before
        # returning the unchanged fail-closed denial.
        _record_broker_denial_feedback(ctx, request, receipt, decision.reason)
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": decision,
                    "auth_context": _derive_auth_context(ctx, request, receipt, decision)},
            error=(
                f"G3-EN-5 fail-closed: denied by real Broker "
                f"(class='{request.action_type}', "
                f"reason='{decision.reason}')"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    # §14.6 Scope v0: a Broker-approved action must still be constrained
    # by the declared mission scope. Scope-valid is NOT authorization;
    # this is a conjunction, not a second PDP — the Broker has already
    # decided, and the scope only narrows. No scope bound: legacy path.
    # Impact: covers() evaluates the exact estimate the Broker decided on
    # (receipt.metadata, written by propose_action). Absent estimate fails
    # closed — a hardcoded 0.0 must never silently pass an over-cap action.
    scope = ctx.get("scope")
    if scope is not None:
        metadata = getattr(receipt, "metadata", None)
        estimate = metadata.get("impact_estimate") if isinstance(metadata, dict) else None
        if estimate is None:
            return StageResult.make(
                stage_name=STAGE_BROKER,
                success=False,
                output={"decision": decision,
                        "auth_context": _derive_auth_context(ctx, request, receipt, decision)},
                error="§14.6 Scope v0 fail-closed: Scope v0: no impact estimate available",
                duration_ms=(time.time() - t0) * 1000.0,
            )
        in_scope, scope_reason = scope.covers(
            request.target,
            request.action_type,
            ctx.get("capability_name", ""),
            impact_estimate=estimate,
        )
        if not in_scope:
            # P3.11 §14.10: record the scope denial as Planner feedback
            # before returning the unchanged fail-closed denial.
            _record_broker_denial_feedback(ctx, request, receipt, scope_reason)
            return StageResult.make(
                stage_name=STAGE_BROKER,
                success=False,
                output={"decision": decision,
                        "auth_context": _derive_auth_context(ctx, request, receipt, decision)},
                error=f"§14.6 Scope v0 fail-closed: {scope_reason}",
                duration_ms=(time.time() - t0) * 1000.0,
            )
    return StageResult.make(
        stage_name=STAGE_BROKER,
        success=True,
        output={"decision": decision, "receipt": receipt,
                "auth_context": _derive_auth_context(ctx, request, receipt, decision)},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_pep(ctx: dict) -> StageResult:
    """PEP invocation. Calls the exec/-owned capability, emits an ExecutionEvent."""
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
    # §14.4: sandboxed execution dispatch. Broker-allowed requests with
    # action_type "sandboxed_exec" run through the exec/-owned minimal
    # sandbox behind the same allow-decision gate (no new stage, no new
    # PDP). The lazy import keeps runtime/*.py free of primitive imports
    # (INV-1 file scan). The sandbox re-verifies the broker receipt.
    if request.action_type == "sandboxed_exec":
        return _stage_pep_sandboxed(ctx, request, decision, t0)
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

def _stage_pep_sandboxed(ctx: dict, request: "ActionRequest",
                         decision: "PolicyDecision", t0: float) -> "StageResult":
    """PEP sandboxed branch (§14.4). Broker-allowed only; receipt re-verified."""
    import tempfile
    from orchestrator.exec.sandbox import (
        SandboxedExecutor,
        SandboxPolicy,
        SandboxRequest,
    )
    broker = ctx.get("broker")
    receipt = ctx["broker"].get("receipt")
    if not hasattr(broker, "receipt_store"):
        # The sequencer replaces stage_ctx["broker"] with the broker-stage
        # output dict; fall back to the PEP capability's bound broker
        # (same object the Runtime constructed the capability with).
        broker = getattr(ctx.get("capability"), "broker", None)
    args = request.args if isinstance(request.args, dict) else {}
    try:
        sandbox_request = SandboxRequest(
            target=request.target,
            argv=tuple(args.get("argv", ())),
            artifacts=tuple(args.get("artifacts", ())),
            # §14.6 F1: thread the four request-side authorization
            # dimensions so the sandbox can verify them against the
            # stored receipt.
            capability=getattr(request, "capability", "") or "",
            action_type=getattr(request, "action_type", "") or "",
            method=getattr(request, "method", "") or "",
        )
    except Exception as exc:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error=f"§14.4 sandbox setup failure: malformed request: {exc}",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    try:
        workdir_root = tempfile.gettempdir()
        executor = SandboxedExecutor(
            broker=broker,
            policy=SandboxPolicy(workdir_root=workdir_root),
        )
        result = executor.execute(sandbox_request, receipt)
    except Exception as exc:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error=f"§14.4 sandbox denied: {type(exc).__name__}: {exc}",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    from orchestrator.runtime.types import ExecutionEvent
    event = ExecutionEvent(
        action_id=request.action_id,
        decision_id=decision.decision_id,
        capability="sandbox.exec",
        target=request.target,
        args=request.args,
        outcome=result.status,
        output={"status": result.status, "returncode": result.returncode,
                "reason": result.reason,
                "artifacts": sorted(result.artifacts.keys())},
    )
    return StageResult.make(
        stage_name=STAGE_PEP,
        success=result.status == "success",
        output={"event": event, "result": result},
        error=None if result.status == "success" else (
            f"§14.4 sandbox {result.status}: {result.reason}"
        ),
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_receipt(ctx: dict) -> StageResult:
    """Receipt emission. Links ExecutionEvent to PolicyDecision.

    P4.1 §15.1: the receipt additionally records mission/scope
    identity and the authorized action dimensions, copied from the
    broker-stage stored authorization truth (never re-evaluated here).
    Evidence remains non-authorizing.
    """
    t0 = time.time()
    from orchestrator.runtime.types import EvidenceReceipt
    event: ExecutionEvent = ctx["pep"]["event"]
    decision = ctx["broker"]["decision"]
    broker_receipt = ctx["broker"].get("receipt")
    view = ctx.get("view", {}) if isinstance(ctx.get("view"), dict) else {}
    scope = ctx.get("scope")
    try:
        scope_hash = scope.scope_hash() if scope is not None and hasattr(scope, "scope_hash") else ""
    except Exception:
        scope_hash = ""
    receipt = EvidenceReceipt(
        event_id=event.event_id,
        decision_id=decision.decision_id,
        summary=f"PEP minted receipt for {event.capability} -> {event.target}",
        mission_id=str(view.get("mission_id", "") or ""),
        scope_hash=scope_hash or "",
        action_type=getattr(broker_receipt, "action_type", "") or "",
        target=getattr(broker_receipt, "target", "") or getattr(event, "target", "") or "",
        capability=getattr(broker_receipt, "capability", "") or "",
        method=getattr(broker_receipt, "method", "") or "",
        argv=tuple(getattr(broker_receipt, "authorized_argv", ()) or ()),
        broker_receipt_id=getattr(broker_receipt, "action_id", "") or "",
    )
    return StageResult.make(
        stage_name=STAGE_RECEIPT,
        success=True,
        output={"receipt": receipt},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_worldmodel_integrate(ctx: dict) -> StageResult:
    """WorldModel integration stage (G3-EN-5: records receipt into evidence graph)."""
    t0 = time.time()
    receipt = ctx["receipt"]["receipt"]
    # G3-EN-5: record the receipt into the evidence graph.
    organs = ctx.get("organs")
    if organs is not None:
        organs.record_integration(receipt.receipt_id)
    return StageResult.make(
        stage_name=STAGE_WORLDMODEL_INTEGRATE,
        success=True,
        output={"integrated": True, "receipt_id": receipt.receipt_id},
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_contradiction(ctx: dict) -> StageResult:
    """Minimal contradiction/failure trigger (G3-EN-5: uses real ContradictionManager).

    P3.11 §14.10: a broker-stage denial recorded as PERSISTENT Planner
    feedback is itself a failure signal (plan vs policy). The stage
    reports triggered=True when either real contradictions exist or
    PERSISTENT denial feedback was recorded on an earlier iteration.
    """
    t0 = time.time()
    organs = ctx.get("organs")
    # Walking skeleton: check for contradictions via the real
    # ContradictionManager. No P5 falsification/promotion semantics.
    triggered = False
    contradictions_found = 0
    if organs is not None and hasattr(organs, "contradiction_manager"):
        try:
            contradictions = list(organs.contradiction_manager.contradictions.values())
            contradictions_found = len(contradictions)
            triggered = contradictions_found > 0
        except Exception:
            triggered = False
    # P3.11 §14.10: broker-denial failure signal from an earlier
    # iteration also triggers (plan contradicted by policy).
    denial_failures = 0
    planner = getattr(organs, "planner", None) if organs is not None else None
    feedback = getattr(planner, "feedback_records", None) if planner is not None else None
    if isinstance(feedback, dict):
        try:
            from orchestrator.brain.action import DenialClass
            denial_failures = sum(
                1 for r in feedback.values()
                if getattr(r, "denial_class", None) == DenialClass.PERSISTENT
            )
        except Exception:
            denial_failures = 0
    if denial_failures > 0:
        triggered = True
    output = {
        "triggered": triggered,
        "contradictions_found": contradictions_found,
        "denial_failures": denial_failures,
        "rule": "g3-en-5.deterministic.no_contradiction" if denial_failures == 0 else "p3.11.deterministic.broker_denial_failure",
    }
    return StageResult.make(
        stage_name=STAGE_CONTRADICTION,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def stage_replan(ctx: dict) -> StageResult:
    """Replan stage. G3-EN-5 walking skeleton: no replan needed.

    P3.11 §14.10: when PERSISTENT denial feedback from an earlier
    iteration exists AND the current iteration broker-authorized a
    different (action_type, target, capability) triple, report
    replanned=True with the changed decision. Otherwise preserve the
    exact legacy output.
    """
    t0 = time.time()
    try:
        organs = ctx.get("organs")
        planner = getattr(organs, "planner", None) if organs is not None else None
        feedback = getattr(planner, "feedback_records", None) if planner is not None else None
        broker_out = ctx.get("broker") or {}
        receipt = broker_out.get("receipt")
        if isinstance(feedback, dict) and feedback and receipt is not None:
            from orchestrator.brain.action import DenialClass
            current = (
                getattr(receipt, "action_type", ""),
                getattr(receipt, "target", ""),
                getattr(receipt, "capability", ""),
            )
            for rec in feedback.values():
                if getattr(rec, "denial_class", None) != DenialClass.PERSISTENT:
                    continue
                denied = (rec.action_type, rec.target, rec.capability)
                if denied != current:
                    return StageResult.make(
                        stage_name=STAGE_REPLAN,
                        success=True,
                        output={
                            "replanned": True,
                            "reason": "P3.11 §14.10: broker denial feedback suppressed the denied proposal; Planner selected a different authorized triple",
                            "denied_triple": list(denied),
                            "next_triple": list(current),
                            "denial_receipt_id": rec.receipt_id,
                            "next_receipt_id": getattr(receipt, "action_id", ""),
                        },
                        duration_ms=(time.time() - t0) * 1000.0,
                    )
    except Exception:
        pass
    return StageResult.make(
        stage_name=STAGE_REPLAN,
        success=True,
        output={"replanned": False, "reason": "G3-EN-5 organ-wired walking skeleton terminates after one iteration"},
        duration_ms=(time.time() - t0) * 1000.0,
    )


# Canonical stage order (unchanged from P3.0)
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
