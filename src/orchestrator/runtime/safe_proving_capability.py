"""
safe_proving_capability.py — DEPRECATED location (CONV-3 re-export shim)

Originally at this path. Relocated to orchestrator.exec.safe_capability
per CONV-3. This file is retained as a re-export shim for backward
compatibility (the Runtime's __init__ and tests still reference
orchestrator.runtime.SafeProvingCapability).

Per GLM: "BootstrapPolicy retired from the decision role (loader/
policy-input mechanics are the lane's; physical deletion is P9)."
Same pattern applies here: the capability is relocated to exec/,
but this re-export shim remains for backward compatibility.

Physical deletion of this shim is P9 work.
"""
from orchestrator.exec.safe_capability import (
    SafeProvingCapability,
    CapabilityResult,
)

__all__ = ["SafeProvingCapability", "CapabilityResult"]
