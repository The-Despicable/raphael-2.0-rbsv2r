"""
P2 Guardrail Test 6: SUB-13 KaliBridge fail-closed proof (WELD-SUB13 fold-in)

Per v4.1 AM-4 weld discipline:
- SUB-13 (KaliBridge._subprocess_run) is CLOSED-BY-FOLD into WELD-SUB14.
- The welded KaliBridge.run must fail-closed with the documented RuntimeError
  when the API is unavailable, instead of falling back to subprocess.
- The legacy subprocess_run method must be removed.

This institutional test asserts both:
1. KaliBridge no longer has a _subprocess_run method.
2. KaliBridge.run raises the documented RuntimeError when the API is unavailable.
"""
import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))


def test_sub13_kali_bridge_fails_closed():
    """SUB-13: KaliBridge fail-closed after WELD-SUB13 fold-in.

    Asserts:
    - KaliBridge._subprocess_run method is removed (no opt-in subprocess).
    - KaliBridge.run raises RuntimeError("Executor._subprocess_fallback() is removed in WELD-SUB14. "
      "All execution must go through the broker-gated capability.") when the API is unavailable.
    """
    from raphael.executor.kali_bridge import KaliBridge

    # 1. _subprocess_run method must be removed
    assert not hasattr(KaliBridge, "_subprocess_run"), (
        "SUB-13: KaliBridge._subprocess_run must be removed after WELD-SUB13"
    )

    # 2. run() must raise the documented RuntimeError when the API is unavailable.
    # Use a local unused port (127.0.0.1:1) to force API failure quickly.
    bridge = KaliBridge(api_url="http://127.0.0.1:1")
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(bridge.run("echo", "test", 5))

    error_msg = str(exc_info.value)
    assert "Executor._subprocess_fallback() is removed in WELD-SUB14" in error_msg, (
        f"SUB-13: RuntimeError message must include the documented weld text. Got: {error_msg}"
    )
    assert "All execution must go through the broker-gated capability" in error_msg, (
        f"SUB-13: RuntimeError message must include broker-gated requirement. Got: {error_msg}"
    )
