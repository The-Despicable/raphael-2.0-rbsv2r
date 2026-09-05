"""
orchestrator/runtime/ — P2.1 walking skeleton (born-gated)

Per v4 L4: RaphaelRuntime is a thin sequencer.
Per v4 L8: Runtime execution is Broker-mediated from the first usable
Runtime commit. No Runtime-wide OFF mode.
Per v4 INV-5: Runtime does not import arena.
Per v4 INV-6: Runtime cannot import seam.

Public surface:
- RaphaelRuntime: thin sequencer (loop.py)
- BootstrapPolicy: bootstrap-v0 policy loader (policy.py)
- SafeProvingCapability: one safe, deterministic capability
  (safe_proving_capability.py)
- Stage contracts: STAGE_ORDER, STAGE_HANDLERS (stages.py)
- Type contracts: RuntimeContext, MissionContext, StageResult,
  ActionRequest, PolicyDecision, ExecutionEvent, EvidenceReceipt,
  LoopTermination, DecisionTrace (types.py)
"""
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.types import (
    RuntimeContext,
    MissionContext,
    StageResult,
    ActionRequest,
    PolicyDecision,
    ExecutionEvent,
    EvidenceReceipt,
    LoopTermination,
    DecisionTrace,
)
from orchestrator.runtime.policy import BootstrapPolicy
from orchestrator.runtime.safe_proving_capability import (
    SafeProvingCapability,
    CapabilityResult,
)
from orchestrator.runtime.stages import STAGE_ORDER, STAGE_HANDLERS

__all__ = [
    "RaphaelRuntime",
    "RuntimeContext",
    "MissionContext",
    "StageResult",
    "ActionRequest",
    "PolicyDecision",
    "ExecutionEvent",
    "EvidenceReceipt",
    "LoopTermination",
    "DecisionTrace",
    "BootstrapPolicy",
    "SafeProvingCapability",
    "CapabilityResult",
    "STAGE_ORDER",
    "STAGE_HANDLERS",
]
