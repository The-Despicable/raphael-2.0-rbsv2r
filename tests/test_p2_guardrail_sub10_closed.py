"""
P2 Guardrail Test 7: SUB-10 KaliToolsClient fail-closed proof (WELD-SUB10).

Per v4.1 AM-4 weld discipline:
- SUB-10 (KaliToolsClient local subprocess fallback) is WELDED.
- The welded KaliToolsClient.run must fail closed with the documented
  RuntimeError when the remote API is unavailable, instead of falling
  back to local subprocess execution.
- The legacy _run_local / authorize_local_bypass mechanism is removed.

This institutional test asserts both:
1. The legacy bypass symbols are gone.
2. KaliToolsClient.run raises the documented RuntimeError when the
   remote API is unavailable.
"""
import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))


def test_sub10_kali_client_fails_closed():
    """SUB-10: KaliToolsClient fail-closed after WELD-SUB10.

    Asserts:
    - _run_local is removed (no local subprocess fallback).
    - authorize_local_bypass is removed (module and instance).
    - KaliToolsClient.run raises RuntimeError("kali_tools_client._run_local
      is removed in WELD-SUB10. ...") when the remote API is unavailable.
    """
    from orchestrator import kali_tools_client
    from orchestrator.kali_tools_client import KaliToolsClient

    # 1. Legacy bypass symbols must be removed.
    assert not hasattr(kali_tools_client, "_run_local"), (
        "SUB-10: kali_tools_client._run_local must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "authorize_local_bypass"), (
        "SUB-10: authorize_local_bypass must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "KaliBypassNotAuthorized"), (
        "SUB-10: KaliBypassNotAuthorized must be removed after WELD-SUB10"
    )
    assert not hasattr(KaliToolsClient, "authorize_local_bypass"), (
        "SUB-10: KaliToolsClient.authorize_local_bypass must be removed after WELD-SUB10"
    )

    # 2. run() must raise the documented RuntimeError when the API is unavailable.
    # Use a local unused port (127.0.0.1:1) to force remote failure quickly.
    client = KaliToolsClient(base_url="http://127.0.0.1:1")
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(client.run("echo", "test", 5))

    error_msg = str(exc_info.value)
    assert "kali_tools_client._run_local is removed in WELD-SUB10" in error_msg, (
        f"SUB-10: RuntimeError message must include the documented weld text. Got: {error_msg}"
    )
    assert "All execution must go through the broker-gated capability" in error_msg, (
        f"SUB-10: RuntimeError message must include broker-gated requirement. Got: {error_msg}"
    )
