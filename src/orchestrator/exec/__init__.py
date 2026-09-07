"""
orchestrator/exec/ — PEP package (CONV-2 + CONV-3)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

CONV-2: PEP execution ownership moves to exec/. The Runtime's
stage_pep delegates to exec/-owned capabilities.

CONV-3: SafeProvingCapability relocates from
orchestrator.runtime.safe_proving_capability to
orchestrator.exec.safe_capability. Constructor gating: the
capability requires a CapabilityBroker reference; inspect()
verifies broker authorization before performing the read.

INV-1 goes live: process/network/file primitives are confined to
exec/. The inv1_guard module provides static import-graph
verification at exec/ package load time.

The standing note defines the broadened INV-1 primitive lexicon:
- subprocess (any form)
- os.system, os.popen, os.exec*, os.spawn*
- socket.*
- urllib.*, http.client, http.server
- requests
- open(..., 'w'), open(..., 'a'), open(..., 'x')
- os.remove, os.unlink, os.rmdir, shutil.rmtree
"""
from orchestrator.exec.safe_capability import (
    SafeProvingCapability,
    CapabilityResult,
)
from orchestrator.exec.sandbox import (
    SandboxedExecutor,
    SandboxPolicy,
    SandboxRequest,
    SandboxResult,
    SandboxError,
    SandboxNotAuthorized,
)
from orchestrator.exec.evidence_store import EvidenceStore

__all__ = [
    "SafeProvingCapability",
    "CapabilityResult",
    "SandboxedExecutor",
    "SandboxPolicy",
    "SandboxRequest",
    "SandboxResult",
    "SandboxError",
    "SandboxNotAuthorized",
    "EvidenceStore",
    "verify_inv1_primitive_confinement",
    "INV1_VIOLATION",
]
