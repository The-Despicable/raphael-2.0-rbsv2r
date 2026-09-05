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

    def step(self, ctx: RuntimeContext) -> tuple:
        """One cognitive iteration.

        Returns (DecisionTrace, LoopTermination).
        """
        trace = DecisionTrace(mission_id=ctx.mission_id)
        stage_ctx: dict = {
            "view": ctx.view,
            "world_model": self._world_model,
            "broker": self._broker,
            "capability": self._capability,
            "organs": self._organs,
            "capability_name": "fixture.inspect",
        }

        for stage_name in STAGE_ORDER:
            handler = STAGE_HANDLERS[stage_name]
            result: StageResult = handler(stage_ctx)
            stage_ctx[stage_name] = result.output
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
                     max_iterations: int = 1,
                     action_cap: int = 1) -> tuple:
        """Full episode loop."""
        all_traces = []
        for i in range(max_iterations):
            ctx = RuntimeContext(
                mission_id=mission.mission_id,
                objective_id=mission.objectives[0] if mission.objectives else "default",
                view={"mission_name": mission.name, "iteration": i, "target": "system_info.name"},
                iteration=i,
            )
            trace, termination = self.step(ctx)
            all_traces.append(trace)
            if termination.terminated:
                break
        return all_traces, termination
