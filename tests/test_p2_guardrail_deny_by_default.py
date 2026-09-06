"""
P2 Guardrail Test 4: deny-by-default SUB-10/SUB-14 (v4.1 AM-4 + v4 L8)

Per v4 master roadmap:
- v4 L8: Runtime execution is Broker-mediated from the first usable Runtime
  commit. No Runtime-wide OFF mode exists.
- v4.1 AM-4.2: seam OFF by default; welding is P3 work
- evidence/phases/P1/03_seam_work/SEAM_SITES.md: SUB-10 and SUB-14 are
  WRAPPED (OFF by default per C6)

This test verifies that:
1. SUB-10 (kali_tools_client._run_local) is removed after WELD-SUB10
2. SUB-14 (executor._subprocess_fallback) is removed after WELD-SUB14
3. The opt-in functions (authorize_local_bypass, authorize_bypass) are removed after their welds
4. Both seams are OFF by construction after fresh import (SUB-10 and SUB-14 via removal)
"""
import asyncio
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))


def test_sub10_kali_bypass_removed():
    """SUB-10: kali_tools_client._run_local is removed after WELD-SUB10."""
    from orchestrator import kali_tools_client

    assert not hasattr(kali_tools_client, "_run_local"), (
        "SUB-10: kali_tools_client._run_local must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "KaliBypassNotAuthorized"), (
        "SUB-10: KaliBypassNotAuthorized must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "_BYPASS_AUTHORIZED"), (
        "SUB-10: _BYPASS_AUTHORIZED must be removed after WELD-SUB10"
    )


def test_sub14_executor_bypass_removed():
    """SUB-14: Executor._subprocess_fallback method is removed after WELD-SUB14."""
    from raphael.executor.executor import Executor

    # The _subprocess_fallback method should not exist on the class
    assert not hasattr(Executor, "_subprocess_fallback"), (
        "Executor should not have _subprocess_fallback method after WELD-SUB14"
    )


def test_sub10_authorize_local_bypass_removed():
    """SUB-10: authorize_local_bypass() opt-in is removed after WELD-SUB10."""
    from orchestrator import kali_tools_client
    from orchestrator.kali_tools_client import KaliToolsClient

    assert not hasattr(kali_tools_client, "authorize_local_bypass"), (
        "SUB-10: authorize_local_bypass() must be removed after WELD-SUB10"
    )
    assert not hasattr(KaliToolsClient, "authorize_local_bypass"), (
        "SUB-10: KaliToolsClient.authorize_local_bypass must be removed after WELD-SUB10"
    )


def test_sub14_authorize_bypass_removed():
    """SUB-14: Executor.authorize_bypass method is removed after WELD-SUB14."""
    from raphael.executor.executor import Executor

    assert not hasattr(Executor, "authorize_bypass"), (
        "Executor should not have authorize_bypass method after WELD-SUB14"
    )


def test_seam_state_consistent_across_imports():
    """SUB-10 seam: bypass symbols are removed (OFF by construction).
    SUB-14 seam: _subprocess_fallback method is removed (so OFF by construction)."""
    import importlib

    # Force reimport
    if "orchestrator.kali_tools_client" in sys.modules:
        importlib.reload(sys.modules["orchestrator.kali_tools_client"])
    if "raphael.executor.executor" in sys.modules:
        importlib.reload(sys.modules["raphael.executor.executor"])

    from orchestrator import kali_tools_client
    from raphael.executor.executor import Executor

    assert not hasattr(kali_tools_client, "_BYPASS_AUTHORIZED")
    assert not hasattr(kali_tools_client, "authorize_local_bypass")
    assert not hasattr(kali_tools_client, "_run_local")
    # The Executor seam is removed, so we check for the absence of the field/method
    assert not hasattr(Executor, "_bypass_authorized")
    assert not hasattr(Executor, "_subprocess_fallback")
