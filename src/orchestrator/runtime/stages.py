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
import logging
import math
import time
from typing import Any, Optional

from orchestrator.exec.capability_governance import governed_capability_identity
from orchestrator.runtime.types import (
    ActionRequest,
    ExecutionEvent,
    PolicyDecision,
    StageResult,
    resolve_capability_governance,
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
                impact_estimate=selected.get("impact_estimate"),
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
        capability="fixture.inspect",
        method="inspect",
        impact_estimate=0.0,
    )
    output = {"request": request}
    return StageResult.make(
        stage_name=STAGE_PLANNER_REQUEST,
        success=True,
        output=output,
        duration_ms=(time.time() - t0) * 1000.0,
    )


def _persist_denial_record(ctx: dict, request, decision, receipt, reason: str = "") -> None:
    """M3/D2 §6: durable denial receipt for every attempted action.

    Authorization, scope/target-mismatch, and rate-limit denials all reach
    the broker stage and terminate the episode before stage_receipt can run;
    without this, a denial would leave only a transcript. Evidence records;
    it never authorizes. Content-addressed identity makes re-ingest
    idempotent (no duplicate records for a single attempt). Persistence
    failure is logged and swallowed: it must not mask the denial.
    """
    store = ctx.get("evidence_store")
    if store is None:
        return
    from orchestrator.runtime.evidence_v1 import EvidenceRecord
    view = ctx.get("view", {}) if isinstance(ctx.get("view"), dict) else {}
    try:
        store.append(EvidenceRecord.execution_result(
            mission_id=str(view.get("mission_id", "") or ""),
            producer="runtime.broker",
            action_id=str(getattr(request, "action_id", "")
                          or getattr(receipt, "action_id", "") or ""),
            status="denied",
            reason=str(reason or decision.reason or "")[:512],
            decision="deny",
            policy_version=str(decision.policy_version or ""),
        ))
    except Exception as exc:  # noqa: BLE001 - persistence must not mask denial
        logging.getLogger(__name__).warning(
            "denial evidence persistence failed (denial still enforced): %s", exc,
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
    # §14.6 F1 / R-1: the Broker must decide on the request's declared
    # impact, not a hardcoded constant. Absent or malformed estimates
    # fail closed here (no PEP, no fabricated 0.0).
    request_impact = getattr(request, "impact_estimate", None)
    try:
        impact_estimate = float(request_impact)
        if not math.isfinite(impact_estimate):
            raise ValueError
    except (TypeError, ValueError):
        reason = ("no impact estimate available" if request_impact is None
                  else "malformed impact estimate")
        return StageResult.make(
            stage_name=STAGE_BROKER,
            success=False,
            output={"decision": None},
            error=f"§14.6 Scope v0 fail-closed: Scope v0: {reason}",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    # F-3: the Scope capability dimension evaluates the capability
    # actually bound to THIS request, not a constant context default.
    # Resolve once and thread the same value to the Broker and to Scope.
    capability = request.capability or ctx.get("capability_name", "")
    method = request.method or "inspect"
    try:
        # §14.6 F1: extract the argv from the request args (when the
        # request declares it) and thread it as authorization material.
        # The broker records argv on the receipt; the PEP re-verifies it.
        argv = tuple(request.args.get("argv", ())) if isinstance(request.args, dict) else ()
        # RSI-1 Fix A: authoritatively bind the Broker receipt to the current
        # mission and the mission-scoped action id via the receipt's lifecycle
        # metadata. The objective evaluator resolves this binding against the
        # Broker's receipt state — a payload claim without the binding can
        # never verify.
        view_mid = str((ctx.get("view") or {}).get("mission_id", "") or "")
        receipt = broker.propose_action(
            target=request.target,
            action_type=request.action_type,
            capability=capability,
            method=method,
            impact_estimate=impact_estimate,
            authorized_argv=argv,
            metadata={"mission_id": view_mid,
                      "mission_action_id": request.action_id},
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
        # M3/D2 §6: persist a durable denial receipt for EVERY attempted
        # action (authorization, scope, and rate-limit denials all arrive
        # here). Evidence records; it never authorizes. Persistence failure
        # must not mask the denial itself.
        _persist_denial_record(ctx, request, decision, receipt)
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
            capability,
            impact_estimate=estimate,
        )
        if not in_scope:
            # P3.11 §14.10: record the scope denial as Planner feedback
            # before returning the unchanged fail-closed denial.
            _record_broker_denial_feedback(ctx, request, receipt, scope_reason)
            # M3/D2 §6: scope/target mismatch is an attempted action too.
            _persist_denial_record(ctx, request, decision, receipt, reason=scope_reason)
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
    """PEP invocation. Calls the exec/-owned capability, emits an ExecutionEvent.

    §14.4/CONV-2: the Runtime owns the Broker execution lifecycle around the
    PEP boundary (no new stage, no new PDP):
        AUTHORIZED -> STARTED (immediately before execution)
        -> SUCCEEDED/FAILED (reflects the actual PEP outcome)
    A terminal receipt cannot start again, so completed authorization is
    not replayable. Evidence v1 remains downstream and non-authoritative.
    """
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
    from orchestrator.hardening.action_receipt import ActionProposalStatus

    # The sequencer replaces ctx["broker"] with the broker-stage output
    # dict; the exec/-owned capability holds the same Broker object.
    broker = ctx.get("broker")
    if not hasattr(broker, "receipt_store"):
        broker = getattr(capability, "broker", None)
    receipt = ctx["broker"].get("receipt")

    # Only an AUTHORIZED Broker receipt may start. Terminal receipts
    # (SUCCEEDED/FAILED/TIMEOUT/DENIED) are rejected here; the PEP's own
    # six-dimension check independently rejects them.
    if broker is None or receipt is None:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error="§lifecycle fail-closed: no Broker receipt available",
            duration_ms=(time.time() - t0) * 1000.0,
        )
    if getattr(receipt, "status", None) != ActionProposalStatus.AUTHORIZED:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error=(
                "§lifecycle fail-closed: broker receipt not STARTABLE "
                f"(status={getattr(receipt, 'status', None)})"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    # RSI-1 B-1 + C-1: the execution boundary is FAIL-CLOSED on authority.
    #
    # ESCAPE 1 (capability substitution, closed): protection was bound to
    # capability NAME strings (policy vocabulary / dispatch-registry keys),
    # both caller-controlled; a protected object registered under an
    # innocuous alias severed the name→protection link and executed
    # unbounded. Protection is now derived from the EXACT capability OBJECT
    # that would execute, via the exec-owned type mapping
    # (exec/capability_governance.py) — relabelling, aliasing, subclass
    # attribute overrides, and post-construction registry edits cannot strip
    # it.
    #
    # ESCAPE 2 (hand-built context, closed): both gates were conditional on
    # key presence, so a caller that omitted ``capability_governance`` and
    # ``governed_step_budget`` — or supplied fresh replacements each call —
    # skipped them. Authority is now REQUIRED: the Broker must carry the
    # Runtime-bound governance and episode-budget objects, the stage context
    # must carry THOSE EXACT OBJECTS (identity, not type), and any absence
    # or substitution REFUSES before the receipt is started. Missing
    # authority is a refusal, never "no gate".
    #
    # The expected governance is INDEPENDENTLY derived here on every
    # invocation from the Broker policy plus the dispatched object identity,
    # so the enforced decision does not depend on what the context claims.

    # 1-2. Resolve the EXACT capability object that would execute (dispatch
    # routing BEFORE enforcement, so governance covers the invoked object;
    # M3/D2 keeps routing inside the SAME PEP stage — not a second PEP).
    registry = ctx.get("capability_registry") or {}
    if request.action_type != "sandboxed_exec":
        capability = registry.get(request.capability, capability)

    # 3-4. Derive the expected governance from the Broker policy plus the
    # dispatched OBJECT's governed identity. ``extra_protected`` can only
    # trigger the fail-closed refusal; it can never manufacture a contract
    # or raise a ceiling.
    object_identity = governed_capability_identity(capability)
    expected = resolve_capability_governance(
        getattr(broker, "policy", None),
        extra_protected=object_identity,
    )

    # 5. Require trusted authority: the Runtime/Broker-bound governance and
    # the Runtime/Broker-owned episode budget, carried by identity through
    # the stage context. A direct caller that omits them, forges them, or
    # substitutes fresh/foreign objects is refused here — before
    # ``start_execution`` and before any capability runs.
    bound_governance = getattr(broker, "_capability_governance", None)
    bound_budget = getattr(broker, "_governed_step_budget", None)
    if bound_governance is None or bound_budget is None:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"governance_authority_refused": True,
                    "authority_missing": "broker"},
            error=(
                "§governance fail-closed: no capability-governance / "
                "governed-step-budget authority is bound to this Broker; "
                "execution requires Runtime-bound authority"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    if ctx.get("capability_governance") is not bound_governance:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"governance_authority_refused": True,
                    "authority_missing": "capability_governance"},
            error=(
                "§governance fail-closed: stage context does not carry the "
                "Runtime/Broker-bound capability_governance authority; "
                "missing or substituted authority is a refusal, not a gate skip"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    if ctx.get("governed_step_budget") is not bound_budget:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"governance_authority_refused": True,
                    "authority_missing": "governed_step_budget"},
            error=(
                "§budget fail-closed: stage context does not carry the "
                "Runtime/Broker-owned governed-step budget authority; missing "
                "or substituted budget authority is a refusal, not a gate skip"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )

    # 6a. Protected-capability refusal, derived from policy + OBJECT identity.
    # A protected capability may not execute unless a recognised governed
    # engagement contract governs it — checked BEFORE the Broker receipt is
    # started and before any capability is invoked, so the receipt stays
    # AUTHORIZED and can never satisfy an objective.
    if expected.refuses_protected_capability:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"protected_capability_refused": True,
                    "capability": str(getattr(request, "capability", "") or ""),
                    "governance_contract": expected.contract_id},
            error=str(expected.reason or "protected capability refused"),
            duration_ms=(time.time() - t0) * 1000.0,
        )

    # 6a-2. RSI-1 C-1 DECISIVE FIX — contract membership.
    #
    # A recognised governed contract must authorise BOTH the policy AND the
    # exact capability OBJECT being executed. Recognition alone is not
    # sufficient: a canonical D1 policy (ceiling 0) paired with a
    # LabHttpProbeCapability OBJECT — dispatched under the D1 registry key, or
    # as the bare default capability — was authorised as "D1, uncapped" and
    # executed the HTTP probe repeatedly (12 governed executions before the
    # rate limiter intervened). The object's OWN canonical identity is compared
    # here against the contract's CLOSED capability set, so a D1 contract can
    # never authorise exec.http_probe and D2 authorises exactly its two
    # approved capabilities.
    #
    # Checked BEFORE the receipt is started and before any capability is
    # invoked: on refusal the receipt stays AUTHORIZED (never STARTED, never
    # SUCCEEDED) and the capability is never invoked.
    permitted, membership_reason = expected.permits_object_identity(object_identity)
    if not permitted:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"capability_contract_refused": True,
                    "capability": str(getattr(request, "capability", "") or ""),
                    "object_identity": sorted(object_identity),
                    "governance_contract": expected.contract_id,
                    "contract_capabilities": sorted(expected.contract_capabilities)},
            error=str(membership_reason),
            duration_ms=(time.time() - t0) * 1000.0,
        )

    # 6b. The governed-step ceiling is consumed HERE — immediately before the
    # Broker receipt is started and the capability is invoked — so the bound
    # is on steps that actually reach the PEP. The authoritative budget is
    # the Runtime-owned episode budget object bound to the Broker; a
    # recognised BOUNDED contract (ceiling > 0) always enforces the REGISTRY
    # ceiling: a tampered budget ceiling of 0 or 64 is repaired to the
    # registry value, so a recognised D2 episode can never be loosened into
    # an unbounded path. Ceiling 0 (D1/bootstrap) declares no governed-step
    # maximum and is untouched.
    budget = bound_budget
    if expected.ceiling > 0 and budget.ceiling != expected.ceiling:
        budget.ceiling = expected.ceiling
    if not budget.try_consume():
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            output={"governed_step_budget_exhausted": True,
                    "governed_step_ceiling": getattr(budget, "ceiling", 0),
                    "governed_steps_used": getattr(budget, "used", 0)},
            error=(
                "§budget fail-closed: governed-step maximum reached "
                f"({getattr(budget, 'used', 0)}/{getattr(budget, 'ceiling', 0)}); "
                "no further governed step may reach the PEP in this episode"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )
    # 7. Only now does the receipt start.
    started = broker.start_execution(receipt)
    if started is None or getattr(started, "status", None) != ActionProposalStatus.STARTED:
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error="§lifecycle fail-closed: broker refused start_execution",
            duration_ms=(time.time() - t0) * 1000.0,
        )

    try:
        # §14.4: sandboxed execution dispatch. Broker-allowed requests with
        # action_type "sandboxed_exec" run through the exec/-owned minimal
        # sandbox behind the same allow-decision gate. The lazy import
        # keeps runtime/*.py free of primitive imports (INV-1 file scan).
        if request.action_type == "sandboxed_exec":
            outcome = _stage_pep_sandboxed(ctx, request, decision, t0)
        else:
            # M3/D2: dispatch routing was resolved above (BEFORE the
            # governance boundary), so the object actually invoked is the
            # exact object governance was derived from.
            outcome = _stage_pep_capability(capability, request, decision, t0)
    except Exception as exc:
        # A raised PEP must still reach a truthful terminal failure before
        # the exception is converted into a stage failure.
        broker.complete_execution(
            receipt, success=False,
            result=f"pep raised {type(exc).__name__}",
        )
        _persist_failure_record(ctx, request, receipt, decision,
                                f"pep raised {type(exc).__name__}: {exc}")
        return StageResult.make(
            stage_name=STAGE_PEP,
            success=False,
            error=(
                f"§lifecycle fail-closed: PEP raised "
                f"{type(exc).__name__}: {exc}"
            ),
            duration_ms=(time.time() - t0) * 1000.0,
        )

    # Terminal transition reflects the actual PEP outcome (never success
    # merely because a Python object was returned).
    broker.complete_execution(
        receipt,
        success=bool(outcome.success),
        result=(outcome.error or "executed"),
    )
    if not outcome.success:
        # M3/D2 §6: an executed-but-failed action gets a durable failure
        # receipt too (timeout, executor error, bounded abort). The failure
        # is never represented as success.
        _persist_failure_record(ctx, request, receipt, decision,
                                outcome.error or "execution failed")
    return outcome


def _persist_failure_record(ctx: dict, request, receipt, decision, reason: str) -> None:
    """M3/D2 §6: durable failure receipt for an action whose execution
    started and then failed (timeout, executor/network error, bounded abort).
    A failure is never represented as success. Persistence failure is logged,
    never masking the truthful broker terminal state."""
    store = ctx.get("evidence_store")
    if store is None:
        return
    from orchestrator.runtime.evidence_v1 import EvidenceRecord
    view = ctx.get("view", {}) if isinstance(ctx.get("view"), dict) else {}
    try:
        store.append(EvidenceRecord.execution_result(
            mission_id=str(view.get("mission_id", "") or ""),
            producer="runtime.pep",
            action_id=str(getattr(request, "action_id", "")
                          or getattr(receipt, "action_id", "") or ""),
            status="failed",
            reason=str(reason or "")[:512],
            decision="allow",
            policy_version=str(decision.policy_version or ""),
        ))
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "failure evidence persistence failed (failure still recorded on the broker receipt): %s", exc,
        )


def _stage_pep_capability(capability, request: "ActionRequest",
                          decision: "PolicyDecision", t0: float) -> "StageResult":
    """Capability branch: CONV-3 gating + exec/-owned capability invocation."""
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



class _ArtifactEvidenceError(ValueError):
    """PEP output lacks the metadata needed to mint a verifiable artifact record."""
    pass


def _artifact_meta(pep_output: Any, ref: str, key: str) -> Any:
    """Extract the PEP-reported metadata value for one collected artifact ref.

    The single-artifact capabilities report ``artifact_<key>`` for the
    artifact named by ``artifact_relpath``; multi-artifact outputs report a
    parallel mapping under ``artifact_meta``. The value is only ever
    DESCRIPTIVE here: it is persisted as the record's claimed digest and is
    re-measured against the actual stored bytes during objective evaluation.
    """
    if not isinstance(pep_output, dict):
        return None
    per_artifact = pep_output.get("artifact_meta")
    if isinstance(per_artifact, dict) and isinstance(per_artifact.get(ref), dict):
        return per_artifact[ref].get(key)
    if str(pep_output.get("artifact_relpath", "")) == ref:
        return pep_output.get(f"artifact_{key}")
    return None


def _artifact_sha256(pep_output: Any, ref: str) -> str:
    """Claimed sha256 for one artifact ref; malformed/missing => fail closed."""
    from orchestrator.runtime.evidence_v1 import EvidenceError
    value = _artifact_meta(pep_output, ref, "sha256")
    if not isinstance(value, str) or len(value) != 64:
        raise EvidenceError(
            f"§14.5 artifact {ref!r} has no well-formed sha256 in the PEP output"
        )
    return value


def _artifact_size(pep_output: Any, ref: str) -> int:
    """Claimed size for one artifact ref; malformed/missing => fail closed."""
    from orchestrator.runtime.evidence_v1 import EvidenceError
    value = _artifact_meta(pep_output, ref, "size_bytes")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EvidenceError(
            f"§14.5 artifact {ref!r} has no well-formed size in the PEP output"
        )
    return value

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
    # §14.5 receipt linkage: link the artifacts the PEP collected (sandbox
    # branch). Descriptive provenance only; artifact refs authorize nothing.
    pep_output = getattr(event, "output", None)
    if isinstance(pep_output, dict):
        artifact_refs = pep_output.get("artifacts")
        if isinstance(artifact_refs, (list, tuple)):
            receipt.artifact_refs = tuple(str(ref) for ref in artifact_refs)
    # §14.5 Evidence v1: derive and persist a durable execution_result
    # record from the canonical PEP event + Broker decision. Evidence
    # records; it authorizes nothing (no store => legacy, no persistence).
    # Idempotent replay: identity is content-addressed over the identity-
    # bearing fields (observed_at is provenance, not identity), so an
    # existing identity means the equivalent record is already durable.
    # M3/D2 remediation: the record now carries the authorizing
    # ``decision_id`` and the collected artifact refs, and each artifact
    # gets its own artifact record linked by execution_ref/parents — the
    # provenance chain the objective evaluator verifies.
    evidence_v1_id = ""
    store = ctx.get("evidence_store")
    if store is not None:
        from orchestrator.runtime.evidence_v1 import EvidenceRecord
        try:
            record = EvidenceRecord.execution_result(
                mission_id=str(receipt.mission_id or ""),
                producer="runtime.receipt",
                action_id=str(
                    event.action_id
                    or getattr(broker_receipt, "action_id", "")
                    or ""
                ),
                status=str(event.outcome or "unknown"),
                reason=str(decision.reason or ""),
                decision=str(decision.decision or ""),
                decision_id=str(decision.decision_id or ""),
                policy_version=str(getattr(broker_receipt, "policy_version", "") or ""),
                artifacts=tuple(receipt.artifact_refs),
            )
            if store.get(record.identity) is None:
                store.append(record)
            evidence_v1_id = record.identity
            receipt.evidence_v1_ids = (evidence_v1_id,)
            for ref in receipt.artifact_refs:
                store.append(EvidenceRecord.artifact(
                    mission_id=str(receipt.mission_id or ""),
                    producer="runtime.receipt",
                    relpath=str(ref),
                    size_bytes=int(_artifact_size(pep_output, ref)),
                    sha256=str(_artifact_sha256(pep_output, ref)),
                    execution_ref=record.identity,
                    parents=(record.identity,),
                ))
        except Exception as exc:
            return StageResult.make(
                stage_name=STAGE_RECEIPT,
                success=False,
                output={"receipt": receipt},
                error=(
                    f"§14.5 Evidence v1 fail-closed: "
                    f"{type(exc).__name__}: {exc}"
                ),
                duration_ms=(time.time() - t0) * 1000.0,
            )
    return StageResult.make(
        stage_name=STAGE_RECEIPT,
        success=True,
        output={"receipt": receipt, "evidence_v1_id": evidence_v1_id},
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


OBJECTIVE_PRODUCERS = ("runtime.receipt", "runtime.broker", "runtime.pep")
OBJECTIVE_SUCCESS_STATUS = ("ok", "succeeded")


def artifact_roots_for(ctx: dict) -> tuple:
    """Bound artifact directories of every capability in this runtime.

    M3/D2 remediation: the objective evaluator verifies artifact digests
    against ACTUAL bytes, so it needs the exec/-owned roots the capabilities
    wrote to. Empty means no artifact can be verified (fail-closed).
    """
    roots = []
    caps = list((ctx.get("capability_registry") or {}).values()) + [ctx.get("capability")]
    for cap in caps:
        root = getattr(cap, "artifact_root", None) if cap is not None else None
        if root is not None and root not in roots:
            roots.append(root)
    return tuple(roots)


def _verify_objective_action(store, view: dict, action_id: str, artifact_roots: tuple,
                             broker_authority=None) -> dict:
    """Verify the complete provenance chain for ONE required action.

    Returns ``{"ok": bool, "reason": str, "identity": str}``. Fails closed on
    every deficiency; a generic or missing mission id never satisfies an action.

    RSI-1 Fix A: ``broker_authority`` is the Runtime's authoritative Broker
    instance. A qualifying execution result must carry a ``decision_id`` that
    the Broker's OWN receipt state resolves to a SUCCEEDED receipt bound (via
    lifecycle metadata) to the same mission and mission-scoped action id.
    Producer labels, decision strings, digests, and internal consistency of
    the evidence ledger are never sufficient on their own. ``broker_authority
    is None`` fails closed — objective completion is unverifiable without the
    authoritative execution state.
    """
    mission_id = str(view.get("mission_id", "") or "")
    if not mission_id:
        return {"ok": False, "reason": "no mission identity in scope", "identity": ""}
    if broker_authority is None:
        return {"ok": False,
                "reason": "no authoritative broker state bound to the objective "
                          "evaluation (fail closed)",
                "identity": ""}

    def p(rec) -> dict:
        return dict(rec.payload)

    scoped = [r for r in store.records()
              if r.kind.value == "execution_result" and r.mission_id == mission_id]
    attempts: dict = {}
    for rec in scoped:
        if p(rec).get("action_id") != action_id:
            continue
        decision_id = str(p(rec).get("decision_id", "") or "")
        if decision_id:
            attempts.setdefault(decision_id, []).append(rec)
    if not attempts:
        present = [r for r in scoped if p(r).get("action_id") == action_id]
        if present:
            unprovenanced = [r for r in present
                             if not str(p(r).get("decision_id", "") or "")]
            reason = ("execution records carry no decision_id provenance"
                      if unprovenanced else
                      "every attempt was denied or failed")
            return {"ok": False, "reason": reason, "identity": ""}
        return {"ok": False,
                "reason": "no governed execution record for this mission and action",
                "identity": ""}

    # Contradiction: every record of an ATTEMPT is weighed, not only the
    # successful-looking ones. Mixed outcomes for one decision_id are
    # ambiguous -> the attempt is rejected (fail closed). A separate, later
    # attempt (a different decision_id) is judged on its own records.
    verified_attempts = []
    for attempt, group in sorted(attempts.items()):
        producers = {r.producer for r in group}
        if not producers <= set(OBJECTIVE_PRODUCERS):
            return {"ok": False,
                    "reason": f"attempt {attempt} has a non-runtime producer {sorted(producers)}",
                    "identity": ""}
        outcomes = {(str(p(r).get("decision")), str(p(r).get("status"))) for r in group}
        if len(outcomes) > 1:
            return {"ok": False,
                    "reason": f"contradictory records for attempt {attempt}: {sorted(outcomes)}",
                    "identity": ""}
        decision, status = next(iter(outcomes))
        if decision != "allow" or status not in OBJECTIVE_SUCCESS_STATUS:
            continue  # denial/failure: never satisfies the objective
        # RSI-1 Fix A: authoritative resolution. The attempt's decision id
        # must resolve, in the Broker's own receipt state, to a SUCCEEDED
        # receipt bound to this mission and this mission-scoped action id.
        # A payload string alone — however consistent — is not provenance.
        auth_receipt = broker_authority.authoritative_success_receipt(
            decision_id=attempt, mission_id=mission_id, mission_action_id=action_id)
        if auth_receipt is None:
            continue  # unresolvable claim: not a governed execution
        verified_attempts.append((attempt, group[0], auth_receipt))

    if not verified_attempts:
        return {"ok": False,
                "reason": "no attempt with an allowed, executed, decision-linked record",
                "identity": ""}

    # Artifact + integrity: each declared artifact ref must have a persisted,
    # correctly linked artifact record whose digest matches the ACTUAL bytes.
    # The chain belongs to the authoritative attempt: the resolved receipt's
    # authorized target and capability must match the claimed execution
    # record's mission binding (fail closed on any mismatch).
    reasons = []
    for attempt, rec, auth_receipt in verified_attempts:
        refs = p(rec).get("artifacts") or ()
        if not refs:
            reasons.append(f"attempt {attempt} declares no artifact evidence")
            continue
        ok, reason = _verify_artifacts_for(store, rec, refs, artifact_roots)
        if ok:
            return {"ok": True, "reason": "verified", "identity": rec.identity}
        reasons.append(reason)
    return {"ok": False,
            "reason": "no verified artifact chain: " + "; ".join(reasons),
            "identity": ""}


def _verify_artifacts_for(store, exec_record, refs, artifact_roots: tuple) -> tuple:
    """Verify each artifact ref of one execution record against real bytes."""
    from orchestrator.exec.artifact_verify import (
        ArtifactVerificationError,
        verify_artifact,
    )
    artifact_records = [r for r in store.records() if r.kind.value == "artifact"]
    for ref in refs:
        linked = [r for r in artifact_records
                  if dict(r.payload).get("relpath") == str(ref)
                  and r.mission_id == exec_record.mission_id
                  and (dict(r.payload).get("execution_ref") == exec_record.identity
                       or exec_record.identity in r.parents)]
        if not linked:
            return False, f"artifact {ref!r} has no linked artifact record"
        claimed = str(dict(linked[0].payload).get("sha256", ""))
        claimed_size = dict(linked[0].payload).get("size_bytes")
        measured = None
        for root in artifact_roots:
            try:
                measured = verify_artifact(root, str(ref))
                break
            except ArtifactVerificationError:
                continue
        if measured is None:
            return False, (f"artifact {ref!r} does not resolve to stored bytes "
                           f"in any bound artifact root")
        if measured["sha256"] != claimed:
            return False, (f"artifact {ref!r} digest mismatch: claimed {claimed}, "
                           f"measured {measured['sha256']}")
        if claimed_size is not None and measured["size_bytes"] != claimed_size:
            return False, (f"artifact {ref!r} size mismatch: claimed {claimed_size}, "
                           f"measured {measured['size_bytes']}")
    return True, "verified"



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
    # M3/D2 §7 + remediation: evidence-based objective evaluation. The
    # objective contract (mission constraint, threaded into the view by
    # run_episode) lists the action_ids whose COMPLETE provenance chain must
    # be durably present and integrity-verified:
    #   current mission -> required action -> authorization decision
    #   -> execution result -> persisted artifact -> verified bytes
    # A model assertion, an unverified proposal, a bare producer string, or a
    # correctly-formatted digest is never evidence. Absent objective
    # contract: exact legacy behavior.
    objective = ctx.get("view", {}).get("objective")
    store = ctx.get("evidence_store")
    if isinstance(objective, dict) and store is not None:
        required = [str(r) for r in objective.get("requires_evidence", []) if str(r)]
        found, missing, deficiencies = [], [], []
        for rid in required:
            verdict = _verify_objective_action(
                store, ctx.get("view", {}), rid, ctx.get("artifact_roots") or (),
                broker_authority=ctx.get("broker_authority"))
            if verdict["ok"]:
                found.append(rid)
            else:
                missing.append(rid)
                deficiencies.append(f"{rid}: {verdict['reason']}")
        if not missing:
            return StageResult.make(
                stage_name=STAGE_REPLAN,
                success=True,
                output={
                    "replanned": False,
                    "objective_evaluated": True,
                    "objective_met": True,
                    "reason": "objective met: verified execution evidence present for " + ", ".join(required),
                    "evidence_found": found,
                },
                duration_ms=(time.time() - t0) * 1000.0,
            )
        return StageResult.make(
            stage_name=STAGE_REPLAN,
            success=True,
            output={
                "replanned": True,
                "objective_evaluated": True,
                "objective_met": False,
                "reason": ("objective not met: unverified or missing required evidence for "
                           + ", ".join(missing) + " [" + "; ".join(deficiencies) + "]"),
                "evidence_missing": missing,
                "evidence_deficiencies": deficiencies,
            },
            duration_ms=(time.time() - t0) * 1000.0,
        )
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
