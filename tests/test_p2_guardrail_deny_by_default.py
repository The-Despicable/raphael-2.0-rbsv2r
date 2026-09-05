"""
P2 Guardrail Test 4: deny-by-default SUB-10/SUB-14 (v4.1 AM-4 + v4 L8)

Per v4 master roadmap:
- v4 L8: Runtime execution is Broker-mediated from the first usable Runtime
  commit. No Runtime-wide OFF mode exists.
- v4.1 AM-4.2: seam OFF by default; welding is P3 work
- evidence/phases/P1/03_seam_work/SEAM_SITES.md: SUB-10 and SUB-14 are
  WRAPPED (OFF by default per C6)

This test verifies that:
1. SUB-10 (kali_tools_client._run_local) raises when called without opt-in
2. SUB-14 (executor._subprocess_fallback) raises when called without opt-in
3. The opt-in functions (authorize_local_bypass, authorize_bypass) exist
   but the flags are OFF by default
"""
import asyncio
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))


def test_sub10_kali_bypass_raises_when_not_authorized():
    """SUB-10: kali_tools_client._run_local raises KaliBypassNotAuthorized
    when _BYPASS_AUTHORIZED is False (default)."""
    from orchestrator.kali_tools_client import (
        _BYPASS_AUTHORIZED,
        KaliBypassNotAuthorized,
        _run_local,
    )

    # Verify default state
    assert _BYPASS_AUTHORIZED is False, (
        "SUB-10: _BYPASS_AUTHORIZED must default to False (v4.1 AM-4)"
    )

    # Verify _run_local raises when not authorized
    with pytest.raises(KaliBypassNotAuthorized):
        asyncio.run(_run_local("echo", "test", 5))


def test_sub14_executor_bypass_raises_when_not_authorized():
    """SUB-14: Executor._subprocess_fallback raises BypassNotAuthorized
    when _bypass_authorized is False (default)."""
    from raphael.executor.executor import BypassNotAuthorized, Executor

    # Verify default state
    assert Executor._bypass_authorized is False, (
        "SUB-14: Executor._bypass_authorized must default to False (v4.1 AM-4)"
    )

    # _subprocess_fallback is an instance method. Create a minimal Executor
    # instance (bypassing __init__) to test the quarantine gate.
    executor = Executor.__new__(Executor)
    # Verify _subprocess_fallback raises when not authorized
    with pytest.raises(BypassNotAuthorized):
        asyncio.run(executor._subprocess_fallback("echo", "test", 5))


def test_sub10_authorize_local_bypass_exists():
    """SUB-10: authorize_local_bypass() opt-in function exists.

    This is the only way to turn the seam ON. It logs a WARNING.
    """
    from orchestrator import kali_tools_client

    assert hasattr(kali_tools_client, "authorize_local_bypass"), (
        "SUB-10: authorize_local_bypass() opt-in function must exist"
    )
    sig = inspect.signature(kali_tools_client.authorize_local_bypass)
    assert "reason" in sig.parameters, (
        "SUB-10: authorize_local_bypass must accept a 'reason' parameter"
    )


def test_sub14_authorize_bypass_exists():
    """SUB-14: Executor.authorize_bypass() opt-in method exists."""
    from raphael.executor.executor import Executor

    assert hasattr(Executor, "authorize_bypass"), (
        "SUB-14: Executor.authorize_bypass() opt-in method must exist"
    )
    sig = inspect.signature(Executor.authorize_bypass)
    assert "reason" in sig.parameters, (
        "SUB-14: Executor.authorize_bypass must accept a 'reason' parameter"
    )


def test_seam_state_consistent_across_imports():
    """Both SUB-10 and SUB-14 seams must be OFF after fresh import.

    This catches any state leakage between test runs.
    """
    import importlib

    # Force reimport
    if "orchestrator.kali_tools_client" in sys.modules:
        importlib.reload(sys.modules["orchestrator.kali_tools_client"])
    if "raphael.executor.executor" in sys.modules:
        importlib.reload(sys.modules["raphael.executor.executor"])

    from orchestrator.kali_tools_client import _BYPASS_AUTHORIZED
    from raphael.executor.executor import Executor

    assert _BYPASS_AUTHORIZED is False
    assert Executor._bypass_authorized is False
