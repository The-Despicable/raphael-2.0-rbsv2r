"""
P2 Guardrail Test 8: SHELL privileged-constructor fail-closed proof (WELD-SHELL).

Per P3.5 / SD-1 weld discipline:
- Reverse-shell and SSH-shell privileged construction requires a valid
  Broker-issued execution context (SessionReceipt: authorized=True,
  authorized_by="capability_broker", unexpired).
- Direct construction without such a receipt must fail closed with the
  documented ShellNotAuthorized error.
- Broker-authorized construction must remain possible.

This single institutional test asserts all three directions.
"""
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))


def test_shell_privileged_construction_requires_broker_receipt():
    """SHELL: privileged construction requires a Broker-issued receipt.

    Asserts:
    1. Direct reverse-shell / SSH-shell / factory construction without
       authorization raises ShellNotAuthorized.
    2. Missing, unauthorized, wrong-issuer, and expired receipts are denied.
    3. Broker-authorized construction (reverse, SSH, factory) still works.
    """
    import asyncio

    from orchestrator.capabilities.interactive_shell.reverse_shell import (
        ReverseShellCapability,
        ReverseShellConnectionInfo,
    )
    from orchestrator.capabilities.interactive_shell.ssh_shell import (
        SSHShellCapability,
    )
    from orchestrator.capabilities.interactive_shell.capability import (
        ShellCapabilityFactory,
        ShellCapabilityType,
        ShellConnectionInfo,
        ShellNotAuthorized,
    )
    from orchestrator.capabilities.interactive_shell.session import (
        SessionReceipt,
        ShellSessionProposal,
        ShellSessionStatus,
    )

    reverse_info = ReverseShellConnectionInfo(
        capability_type=ShellCapabilityType.REVERSE_TCP,
        target="10.0.0.100",
        lhost="127.0.0.1",
        lport=4444,
        allowed_callback_cidrs=["10.0.0.0/8"],
    )
    ssh_info = ShellConnectionInfo(
        capability_type=ShellCapabilityType.SSH,
        target="10.0.0.5",
        username="admin",
        auth_method="password",
    )

    # 1. Direct construction without authorization fails closed.
    with pytest.raises(ShellNotAuthorized):
        ReverseShellCapability(connection_info=reverse_info)
    with pytest.raises(ShellNotAuthorized):
        SSHShellCapability(connection_info=ssh_info)
    with pytest.raises(ShellNotAuthorized):
        ShellCapabilityFactory.create(ssh_info)

    # 2. Forged / invalid receipts fail closed.
    def receipt(**overrides):
        base = dict(
            session_id="shell_test",
            authorized=True,
            status=ShellSessionStatus.AUTHORIZED,
            expires_at=time.time() + 3600,
            restrictions={},
            reason="test",
            policy_version="1.0",
            authorized_by="capability_broker",
        )
        base.update(overrides)
        return SessionReceipt(**base)

    for bad in (
        None,
        receipt(authorized=False),
        receipt(authorized_by="attacker"),
        receipt(expires_at=time.time() - 1),
    ):
        with pytest.raises(ShellNotAuthorized):
            ReverseShellCapability(
                connection_info=reverse_info, authorization=bad
            )

    # 3. Broker-authorized construction remains possible.
    sys.path.insert(0, "tests")
    from e1_interactive_shell_test import _create_test_broker

    broker = _create_test_broker()
    ssh_receipt = broker.authorize_shell_session(
        ShellSessionProposal(
            capability_type=ShellCapabilityType.SSH,
            target="10.0.0.5",
            username="admin",
            auth_method="password",
        )
    )
    assert ssh_receipt.authorized, f"Expected authorized receipt: {ssh_receipt.reason}"
    assert SSHShellCapability(
        connection_info=ssh_info, authorization=ssh_receipt
    ) is not None

    reverse_receipt = broker.authorize_shell_session(
        ShellSessionProposal(
            capability_type=ShellCapabilityType.REVERSE_TCP,
            target="10.0.0.100",
            lhost="127.0.0.1",
            lport=4446,
            metadata={"allowed_callback_cidrs": ["10.0.0.0/8"]},
        )
    )
    assert reverse_receipt.authorized, (
        f"Expected authorized receipt: {reverse_receipt.reason}"
    )
    assert ReverseShellCapability(
        connection_info=reverse_info, authorization=reverse_receipt
    ) is not None
    assert isinstance(
        ShellCapabilityFactory.create(ssh_info, authorization=ssh_receipt),
        SSHShellCapability,
    )
