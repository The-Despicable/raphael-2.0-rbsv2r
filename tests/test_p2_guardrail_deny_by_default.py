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
2. SUB-14 (executor._subprocess_fallback) is removed after WELD-SUB14
3. The opt-in functions (authorize_local_bypass, authorize_bypass) exist for SUB-10, but authorize_bypass is removed after WELD-SUB14
4. Both seams are OFF after fresh import (SUB-10 via flag, SUB-14 via removal)
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


def test_sub14_executor_bypass_removed():
    """SUB-14: Executor._subprocess_fallback method is removed after WELD-SUB14."""
    from raphael.executor.executor import Executor

    # The _subprocess_fallback method should not exist on the class
    assert not hasattr(Executor, "_subprocess_fallback"), (
        "Executor should not have _subprocess_fallback method after WELD-SUB14"
    )


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


def test_sub14_authorize_bypass_removed():
    """SUB-14: Executor.authorize_bypass method is removed after WELD-SUB14."""
    from raphael.executor.executor import Executor

    assert not hasattr(Executor, "authorize_bypass"), (
        "Executor should not have authorize_bypass method after WELD-SUB14"
    )


def test_seam_state_consistent_across_imports():
    """SUB-10 seam: _BYPASS_AUTHORIZED flag is OFF by default.
    SUB-14 seam: _subprocess_fallback method is removed (so OFF by construction)."""
    import importlib

    # Force reimport
    if "orchestrator.kali_tools_client" in sys.modules:
        importlib.reload(sys.modules["orchestrator.kali_tools_client"])
    if "raphael.executor.executor" in sys.modules:
        importlib.reload(sys.modules["raphael.executor.executor"])

    from orchestrator.kali_tools_client import _BYPASS_AUTHORIZED
    from raphael.executor.executor import Executor

    assert _BYPASS_AUTHORIZED is False
    # The Executor seam is removed, so we check for the absence of the field/method
    assert not hasattr(Executor, "_bypass_authorized")
    assert not hasattr(Executor, "_subprocess_fallback")
