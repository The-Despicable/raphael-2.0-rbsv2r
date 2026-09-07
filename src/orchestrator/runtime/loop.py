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
from orchestrator.exec.safe_capability import SafeProvingCapability

from orchestrator.runtime.types import (
    DecisionTrace,
    LoopTermination,
    MissionContext,
    PolicyDecision,
    RuntimeContext,
    StageResult,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.stages import STAGE_ORDER, STAGE_HANDLERS
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
                 organs: Optional[OrganBundle] = None):
        self._broker = broker if broker is not None else make_broker_from_bootstrap(
            capability_name="fixture.inspect"
        )
        # CONV-2/3: capability lives in exec/ and is broker-gated.
        if capability is not None:
            self._capability = capability
        else:
            self._capability = SafeProvingCapability(broker=self._broker)
        # G3-EN-5: organ bundle (Planner, WorldModel, Student, Contradiction).
        self._organs = organs if organs is not None else OrganBundle()
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
        }

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
                break
        return all_traces, termination
