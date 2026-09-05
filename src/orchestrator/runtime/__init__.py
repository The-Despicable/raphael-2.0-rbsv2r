"""
orchestrator/runtime/ — P3.0 CONV-1 walking skeleton (real Broker)

Per v4 L4: RaphaelRuntime is a thin sequencer.
Per v4 L8: Runtime execution is Broker-mediated from the first usable
Runtime commit. No Runtime-wide OFF mode.
Per v4 INV-5: Runtime does not import arena.
Per v4 INV-6: Runtime cannot import seam.

CONV-1: the Runtime's single canonical PDP is now the real brain
CapabilityBroker. The BootstrapPolicy placeholder is retired from
the decision role (retained as a loader/policy-input helper).

Public surface:
- RaphaelRuntime: thin sequencer (loop.py)
- make_broker_from_bootstrap: factory for CapabilityBroker from
  bootstrap-v0 rules (policy.py)
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
from orchestrator.runtime.policy import (
    BootstrapPolicy,
    make_broker_from_bootstrap,
)
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
    "make_broker_from_bootstrap",
    "SafeProvingCapability",
    "CapabilityResult",
    "STAGE_ORDER",
    "STAGE_HANDLERS",
]
