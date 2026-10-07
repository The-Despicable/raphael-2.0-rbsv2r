"""
loop.py — RaphaelRuntime thin sequencer (P3.0 G3-EN-5 organ-wired)

Per v4 section 13.1: RaphaelRuntime must:
- own sequence and termination
- call stage handlers
- have no domain logic
- have no policy logic
- have no migration-seam dependency
- enter Broker/PEP for EXECUTE
- expose a stable trace interface

G3-EN-5: Planner, WorldModel (read + integrate), Student (recording
mode), and minimal contradiction/failure trigger are wired onto
the canonical Runtime path.

CONV-1: the Runtime accepts a brain CapabilityBroker as its
single canonical PDP.
CONV-2: PEP execution ownership is in orchestrator.exec/.
CONV-3: the capability is broker-gated.
"""
from __future__ import annotations
import time
from typing import Any, Optional

from orchestrator.brain.capability_broker import CapabilityBroker
from orchestrator.exec.capability_governance import governed_capability_identity
from orchestrator.exec.safe_capability import SafeProvingCapability

from orchestrator.runtime.types import (
    D2_APPROVED_MAX_EPISODE_STEPS,
    DecisionTrace,
    GovernedStepBudget,
    LoopTermination,
    MissionContext,
    PolicyDecision,
    RuntimeContext,
    StageResult,
    broker_policy_is_d2,
    resolve_capability_governance,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.stages import (
    STAGE_HANDLERS,
    STAGE_ORDER,
    artifact_roots_for,
)
from orchestrator.runtime.policy import make_broker_from_bootstrap
from orchestrator.runtime.organs import OrganBundle


class RaphaelRuntime:
    """Thin sequencer. Owns stage order, termination, stage contracts.

    Born-gated: Broker.propose_action -> PEP is the first usable
    execution path. No Runtime-wide OFF mode (v4 L8).

    G3-EN-5: organ-wired. Planner, WorldModel, Student, and
    ContradictionManager are invoked through the canonical stage
    handlers. No second cognitive loop. No new stages.
    """

    def __init__(self, broker: Optional[CapabilityBroker] = None,
                 capability: Optional[SafeProvingCapability] = None,
                 organs: Optional[OrganBundle] = None,
                 evidence_store: Optional[Any] = None,
                 capability_registry: Optional[dict] = None):
        self._broker = broker if broker is not None else make_broker_from_bootstrap(
            capability_name="fixture.inspect"
        )
        # CONV-2/3: capability lives in exec/ and is broker-gated.
        if capability is not None:
            self._capability = capability
        else:
            self._capability = SafeProvingCapability(broker=self._broker)
        # G3-EN-5: organ bundle (Planner, WorldModel, Student, Contradiction).
        self._organs = organs if organs is not None else OrganBundle(
            evidence_store=evidence_store
        )
        # §14.5 Evidence v1: allow the caller to bind a durable store to an
        # explicitly supplied organ bundle as well.
        if evidence_store is not None and getattr(self._organs, "evidence_store", None) is None:
            self._organs.evidence_store = evidence_store
        # M3/D2: PEP dispatch registry (capability name -> exec/-owned
        # capability). Multi-action episodes route an AUTHORIZED request to
        # the capability the Broker authorized; routing happens inside the
        # SAME PEP stage — no second PEP. Absent/empty registry preserves
        # exact legacy behavior.
        self._capability_registry = dict(capability_registry) if capability_registry else {}
        # RSI-1 Fix B: governed-step ceiling enforced AT the PEP boundary. The
        # approved D2 engagement may never execute more than
        # D2_APPROVED_MAX_EPISODE_STEPS governed steps, recognised STRUCTURALLY
        # so a renamed policy artifact or a hand-constructed BrokerPolicy with
        # a zero/six/64 cap cannot escape it. Other engagements get ceiling 0
        # (no bound declared) and are untouched — D1 behavior is unchanged.
        #
        # RSI-1 B-1: the ceiling and the protected-capability refusal come
        # from the canonical governance REGISTRY (types.GOVERNED_ENGAGEMENT_
        # CONTRACTS), not from policy identity labels. Deleting every identity
        # signal can therefore no longer produce an unbounded path: it produces
        # a refusal for the protected capability instead.
        #
        # RSI-1 C-1: governance is resolved over the capability OBJECTS this
        # Runtime would invoke (default capability + registry values), not
        # over caller-controlled names. The identity comes from the exec-owned
        # exact type mapping (exec/capability_governance.py), so an aliased
        # protected object — registered now or injected into the registry
        # later — still resolves as protected. The Runtime binds exactly ONE
        # governance decision and ONE episode budget, and binds them to the
        # BROKER as private authority references; stage_pep enforces against
        # those objects (identity, not type), so a hand-built stage context
        # can neither omit nor substitute the authority.
        self._protected_identity: frozenset = governed_capability_identity(self._capability)
        for _obj in self._capability_registry.values():
            self._protected_identity |= governed_capability_identity(_obj)
        self._governance = resolve_capability_governance(
            getattr(self._broker, "policy", None),
            extra_protected=self._protected_identity,
        )
        self._step_budget = GovernedStepBudget(self._governance.ceiling)
        try:
            self._broker._capability_governance = self._governance
            self._broker._governed_step_budget = self._step_budget
        except Exception:  # noqa: BLE001 — an unbindable broker simply fails closed at the PEP
            pass
        # Backwards-compatible alias for the world model.
        self._world_model = self._organs.world_model

    def step(self, ctx: RuntimeContext, stage_outputs: Optional[dict] = None) -> tuple:
        """One cognitive iteration.

        Returns (DecisionTrace, LoopTermination).

        P3.11 §14.10: when ``stage_outputs`` is a dict, each stage's
        output mapping is recorded under its stage name (best-effort;
        a stage output that is not a dict is stored as-is). The default
        None preserves the exact legacy contract.
        """
        trace = DecisionTrace(mission_id=ctx.mission_id)
        stage_ctx: dict = {
            "view": ctx.view,
            "world_model": self._world_model,
            "broker": self._broker,
            "capability": self._capability,
            "organs": self._organs,
            "capability_name": "fixture.inspect",
            "scope": ctx.scope,
            "evidence_store": getattr(self._organs, "evidence_store", None),
            "capability_registry": self._capability_registry,
            # RSI-1 Fix A: the authoritative Broker instance. stage_replan's
            # objective evaluation resolves claimed decision ids against THIS
            # object's receipt state — never against evidence-payload strings.
            "broker_authority": self._broker,
            # RSI-1 Fix B: the per-episode governed-step ceiling, consumed by
            # the PEP stage itself so the D2 five-step maximum holds for every
            # entry path, not only for the run_episode iteration clamp.
            "governed_step_budget": self._step_budget,
            # RSI-1 B-1: the resolved governance decision. The PEP stage
            # refuses a PROTECTED capability outright when no recognised
            # governed contract governs it.
            "capability_governance": self._governance,
        }
        # M3/D2 remediation: bind the exec/-owned artifact roots so the
        # objective evaluator can verify artifact digests against the ACTUAL
        # stored bytes (fail-closed when none are bound).
        stage_ctx["artifact_roots"] = artifact_roots_for(stage_ctx)

        for stage_name in STAGE_ORDER:
            handler = STAGE_HANDLERS[stage_name]
            result: StageResult = handler(stage_ctx)
            stage_ctx[stage_name] = result.output
            if stage_outputs is not None:
                stage_outputs[stage_name] = result.output
            trace.append({
                "stage": stage_name,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error,
            })
            if not result.success:
                return trace, LoopTermination(
                    terminated=True,
                    reason=f"Stage '{stage_name}' failed: {result.error}",
                    iterations=1,
                    final_stage=stage_name,
                )

        return trace, LoopTermination(
            terminated=True,
            reason="G3-EN-5 organ-wired walking skeleton: one iteration complete",
            iterations=1,
            final_stage=STAGE_ORDER[-1],
        )

    def run_episode(self, mission: MissionContext,
                     max_iterations: Optional[int] = None,
                     action_cap: Optional[int] = None,
                     require_scope: Optional[bool] = None,
                     episode_outputs: Optional[list] = None) -> tuple:
        """Full episode loop.

        P3.11 §14.10: when ``episode_outputs`` is a list, each
        iteration's stage-output mapping is appended (best-effort).
        The default None preserves the exact legacy contract.

        §14.6 Scope v0: when require_scope is True, a mission without a
        validated ScopeV0 fails closed before any stage executes. A
        non-ScopeV0 scope object also fails closed (no duck-typing).

        P3.11 §14.10: the mission may declare deterministic per-iteration
        candidate sets under ``mission.constraints["candidates"]`` (a
        mapping of iteration index -> candidate list). Each iteration's
        view carries its candidate set for the Planner stage. When an
        iteration terminates at the broker stage (denial) and iterations
        remain, the episode continues so denial feedback can drive a
        changed next decision (replan-at-episode-level). Single-iteration
        callers observe byte-identical behavior.
        P4.1 §15.1: explicit params win; when None, halt conditions ride
        from ``mission.constraints["halt"]`` (populated by
        MissionContext.from_spec); otherwise legacy defaults apply
        (max_iterations=1, action_cap=1, require_scope=False).
        M3/D2 remediation: the effective episode budget is clamped to the
        AUTHORITATIVE policy cap (``BrokerPolicy.max_episode_steps``, sourced
        from the validated engagement artifact, e.g.
        ``max_episode_steps: 5`` in policies/engagement-d2-v1.json). A
        caller-supplied ``max_iterations`` remains supported but can never
        raise the policy maximum. The cap covers the whole episode and is not
        reset by replanning, denial handling, or candidate fallback. Both the
        requested and effective budgets are reported truthfully.
        """
        constraints = mission.constraints if isinstance(mission.constraints, dict) else {}
        halt = constraints.get("halt", {})
        if not isinstance(halt, dict):
            halt = {}
        if max_iterations is None:
            max_iterations = halt.get("max_iterations", 1)
        if action_cap is None:
            action_cap = halt.get("action_cap", 1)
        if require_scope is None:
            require_scope = halt.get("require_scope", False)
        try:
            max_iterations = int(max_iterations)
        except (TypeError, ValueError):
            max_iterations = 1
        if max_iterations < 1:
            max_iterations = 1
        policy_cap = int(getattr(getattr(self._broker, "policy", None),
                                 "max_episode_steps", 0) or 0)
        requested_budget = max_iterations
        # RSI-1 Fix B + B-1. The effective ceiling is the STRICTER of the
        # cap the artifact declares and the canonical ceiling held in the
        # governance REGISTRY for the resolved contract. The registry is the
        # authority: a renamed/narrowed artifact can raise neither the
        # recognised D2 ceiling nor obtain an unbounded fallback (that case is
        # refused at the PEP boundary instead). 0 = the resolved contract
        # declares no governed-step maximum (D1/bootstrap unchanged).
        d2_recognized = broker_policy_is_d2(getattr(self._broker, "policy", None))
        ceiling = policy_cap if policy_cap > 0 else 0
        registry_ceiling = self._governance.ceiling
        if registry_ceiling > 0 and (ceiling == 0 or registry_ceiling < ceiling):
            ceiling = registry_ceiling
        effective_budget = requested_budget
        if ceiling > 0 and effective_budget > ceiling:
            effective_budget = ceiling
        budget_clamped = effective_budget < requested_budget
        max_iterations = effective_budget
        # Which bound actually governed the episode — reported truthfully so a
        # clamp driven by the registry is never presented as the artifact's own
        # declared cap.
        if ceiling <= 0:
            governing_bound = "no declared episode bound"
        elif ceiling == policy_cap:
            governing_bound = f"policy max_episode_steps {policy_cap}"
        else:
            governing_bound = (
                f"canonical {self._governance.contract_id} invariant "
                f"{registry_ceiling} (policy declared {policy_cap})"
            )
        # RSI-1 FINAL BLOCKER: the episode-boundary transition. There is NO
        # in-place reset — ``GovernedStepBudget.reset()`` always refuses. The
        # Runtime mints a NEW budget generation here, and re-binds it to the
        # Broker, so the previous episode's budget becomes stale and inert (the
        # PEP compares the stage-context budget to the Broker's by IDENTITY).
        # Exactly one authoritative budget exists per active episode, and only
        # this transition can produce a fresh allowance.
        self._step_budget = GovernedStepBudget.next_episode(
            self._step_budget, self._governance.ceiling)
        try:
            self._broker._governed_step_budget = self._step_budget
        except Exception:  # noqa: BLE001 — unbindable broker fails closed at the PEP
            pass
        scope = mission.scope
        if scope is not None and not isinstance(scope, ScopeV0):
            return [], LoopTermination(
                terminated=True,
                reason="§14.6 Scope v0 fail-closed: mission scope is not a ScopeV0",
                iterations=0,
                final_stage="scope",
            )
        if require_scope and scope is None:
            return [], LoopTermination(
                terminated=True,
                reason="§14.6 Scope v0 fail-closed: mission declares no scope",
                iterations=0,
                final_stage="scope",
            )
        candidates_by_iter = constraints.get("candidates", {})
        if not isinstance(candidates_by_iter, dict):
            candidates_by_iter = {}
        default_target = constraints.get("default_target", "system_info.name")
        objective_id = constraints.get("objective_id", mission.mission_id)
        all_traces = []
        for i in range(max_iterations):
            view = {"mission_name": mission.name, "mission_id": mission.mission_id,
                    "iteration": i, "target": default_target,
                    "objective_id": objective_id}
            # M3/D2 §7: thread the evidence-based objective contract (when the
            # mission declares one) so stage_replan can evaluate termination
            # against persisted records. Absent: legacy view, byte-identical.
            if "objective" in constraints:
                view["objective"] = constraints["objective"]
            # P4.3 §15: bind the actual MissionSpec object when the
            # mission carries one (from_spec). The broker stage derives
            # the AuthorizationContext from this spec authoritatively.
            if getattr(mission, "spec", None) is not None:
                view["mission_spec"] = mission.spec
            iter_candidates = candidates_by_iter.get(str(i), candidates_by_iter.get(i, None))
            if isinstance(iter_candidates, list) and iter_candidates:
                view["candidates"] = iter_candidates
            ctx = RuntimeContext(
                mission_id=mission.mission_id,
                objective_id=mission.objectives[0] if mission.objectives else "default",
                view=view,
                iteration=i,
                scope=scope,
            )
            iter_outputs: dict = {}
            trace, termination = self.step(ctx, stage_outputs=iter_outputs)
            all_traces.append(trace)
            if episode_outputs is not None:
                episode_outputs.append(iter_outputs)
            if termination.terminated:
                # P3.11 §14.10: a broker-stage denial with remaining
                # iterations continues the episode (denial feedback drives
                # the next decision). All other terminations break.
                if termination.final_stage == "broker" and (i + 1) < max_iterations:
                    termination = LoopTermination(
                        terminated=True,
                        reason=f"P3.11 §14.10: broker denial at iteration {i}; continuing to replanned iteration {i + 1}",
                        iterations=i + 1,
                        final_stage="broker",
                    )
                    all_traces[-1] = trace
                    continue
                # M3/D2 §7: evidence-based objective continuation. When the
                # replan stage evaluated a mission objective and the durable
                # evidence does not yet satisfy it, continue within the same
                # iteration budget (the next step's candidates are the
                # mission's predeclared remaining actions).
                replan_out = iter_outputs.get("replan")
                if (termination.final_stage == "replan"
                        and isinstance(replan_out, dict)
                        and replan_out.get("replanned")
                        and (i + 1) < max_iterations):
                    all_traces[-1] = trace
                    continue
                # M3/D2 §7: honest terminal reason when an objective was
                # evaluated — objective met, or not met (budget exhausted /
                # required evidence denied or missing). Never claims success
                # without the required evidence.
                if isinstance(replan_out, dict) and replan_out.get("objective_evaluated"):
                    termination = LoopTermination(
                        terminated=True,
                        reason=str(replan_out.get("reason", termination.reason)),
                        iterations=i + 1,
                        final_stage="replan",
                    )
                break
        # M3/D2: truthful budget reporting. A clamp is reported as a clamp and
        # never as permission to exceed the cap; an achieved objective stays an
        # achieved objective.
        termination.requested_budget = requested_budget
        termination.effective_budget = effective_budget
        termination.budget_clamped = budget_clamped
        termination.policy_max_episode_steps = policy_cap
        termination.governed_step_ceiling = self._step_budget.ceiling
        termination.governed_steps_used = self._step_budget.used
        termination.d2_recognized = d2_recognized
        termination.governance_contract = self._governance.contract_id
        termination.governance_refuses_protected = self._governance.refuses_protected_capability
        termination.governance_budget_epoch = self._step_budget.generation
        if budget_clamped:
            termination.reason += (
                f" [budget clamped: requested {requested_budget} steps > "
                f"{governing_bound}; effective {effective_budget}]"
            )
        elif (termination.final_stage == "replan"
              and termination.iterations >= effective_budget):
            # The permitted budget ended without completion.
            termination.reason += (
                f" [budget exhausted: {termination.iterations}/{effective_budget} "
                f"governed steps used]"
            )
        return all_traces, termination
