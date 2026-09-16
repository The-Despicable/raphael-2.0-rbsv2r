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

INV-1: process/network/file primitives are confined to exec/. The
inv1_guard module provides static AST verification over the declared
G3 canonical perimeter (runtime/** + the loaded canonical brain
control-plane modules + exec/**). It is invoked by the gate/test suite
(tests/test_p2_guardrail_inv1.py); it is NOT executed at exec/ package
load time (an import-time full-perimeter scan would be an expensive
per-process side effect and would raise at import on a violation). The
authoritative assertion is at gate/test time.

The INV-1 primitive lexicon (enforced by inv1_guard):
- subprocess (import or any call form)
- asyncio.create_subprocess_exec / _shell, asyncio.subprocess
- os.system, os.popen, os.exec*, os.spawn*
- socket, requests, httpx, aiohttp, paramiko, docker
- urllib.request, http.client, http.server
- os.remove, os.unlink, os.rmdir, shutil.rmtree
- open(..., 'w'/'a'/'x'/'+')
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
from orchestrator.exec.inv1_guard import (
    INV1_VIOLATION,
    canonical_perimeter_modules,
    verify_inv1_primitive_confinement,
)

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
    "canonical_perimeter_modules",
    "INV1_VIOLATION",
]
