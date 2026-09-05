"""
loop.py — RaphaelRuntime thin sequencer (P2.1 walking skeleton)

Per v4 §13.1: RaphaelRuntime must:
- own sequence and termination
- call stage handlers
- have no domain logic
- have no policy logic
- have no migration-seam dependency
- enter Broker/PEP for EXECUTE
- expose a stable trace interface

The Runtime uses Head 2 organs as handlers rather than rewriting their
internal logic.

P2.1 walking skeleton: one iteration, Broker-mediated mock path,
one safe proving capability, DecisionTrace emission, no Runtime-wide
OFF mode.
"""
from __future__ import annotations
import time
from typing import Any, Optional

from orchestrator.runtime.types import (
    DecisionTrace,
    LoopTermination,
    MissionContext,
    PolicyDecision,
    RuntimeContext,
    StageResult,
)
from orchestrator.runtime.stages import STAGE_ORDER, STAGE_HANDLERS
from orchestrator.runtime.policy import BootstrapPolicy
from orchestrator.runtime.safe_proving_capability import SafeProvingCapability


class RaphaelRuntime:
    """Thin sequencer. Owns stage order, termination, stage contracts.

    Born-gated: Broker.authorize -> PEP is the first usable execution
    path. No Runtime-wide OFF mode (v4 L8).
    """

    def __init__(self, policy: Optional[BootstrapPolicy] = None,
                 capability: Optional[SafeProvingCapability] = None):
        self._policy = policy if policy is not None else BootstrapPolicy()
        self._capability = capability if capability is not None else SafeProvingCapability()
        self._world_model = {"entities": {}, "facts": {}}

    def step(self, ctx: RuntimeContext) -> tuple:
        """One cognitive iteration.

        Returns (DecisionTrace, LoopTermination).
        """
        trace = DecisionTrace(mission_id=ctx.mission_id)
        # Mutable stage context: each stage writes its output here.
        stage_ctx: dict = {
            "view": ctx.view,
            "world_model": self._world_model,
            "policy": self._policy,
            "capability": self._capability,
        }

        for stage_name in STAGE_ORDER:
            handler = STAGE_HANDLERS[stage_name]
            result: StageResult = handler(stage_ctx)
            # Store under the canonical key for the NEXT stage.
            stage_ctx[stage_name] = result.output
            # Append to the trace.
            trace.append({
                "stage": stage_name,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error,
            })
            # Fail-closed: if any stage fails, stop.
            if not result.success:
                return trace, LoopTermination(
                    terminated=True,
                    reason=f"Stage '{stage_name}' failed: {result.error}",
                    iterations=1,
                    final_stage=stage_name,
                )

        return trace, LoopTermination(
            terminated=True,
            reason="P2.1 walking skeleton: one iteration complete",
            iterations=1,
            final_stage=STAGE_ORDER[-1],
        )

    def run_episode(self, mission: MissionContext,
                     max_iterations: int = 1,
                     action_cap: int = 1) -> tuple:
        """Full episode loop.

        P2.1 walking skeleton: max_iterations=1, action_cap=1.
        """
        all_traces = []
        for i in range(max_iterations):
            ctx = RuntimeContext(
                mission_id=mission.mission_id,
                objective_id=mission.objectives[0] if mission.objectives else "default",
                view={"mission_name": mission.name, "iteration": i},
                iteration=i,
            )
            trace, termination = self.step(ctx)
            all_traces.append(trace)
            if termination.terminated:
                break
        return all_traces, termination
