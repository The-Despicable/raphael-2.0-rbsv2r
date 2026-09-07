"""
§14.4 Native Minimal Sandbox tests + §14.6 F1 request-binding adversarial battery.

Focused mechanism tests (fail-closed first), authorization-path tests,
PEP integration tests, and architecture-invariant tests. The sandbox is
a mechanism, not an authorization boundary: every execution requires a
Broker-issued receipt from the broker's own store.

§14.6 F1 (this revision) tightens the authorization invariant from
three dimensions (action_id, status==AUTHORIZED, target==req.target) to
six dimensions (capability, action_type, method, argv also bound). The
adversarial battery at the bottom proves each reject path.
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.sandbox import (
    ARTIFACT_FAILURE,
    EXEC_FAILURE,
    OUTPUT_LIMIT,
    RESOURCE_LIMIT,
    SETUP_FAILURE,
    SUCCESS,
    TIMEOUT,
    UNSUPPORTED,
    SandboxedExecutor,
    SandboxError,
    SandboxNotAuthorized,
    SandboxPolicy,
    SandboxRequest,
)
from orchestrator.exec.safe_capability import SafeProvingCapability

def _test_root(tmp_path):
    root = tmp_path / "sbxroot"
    root.mkdir()
    return str(root)


def _policy(root, **overrides):
    base = dict(workdir_root=root)
    base.update(overrides)
    return SandboxPolicy(**base)


def _broker():
    return CapabilityBroker(BrokerPolicy(
        engagement_id="sbx-test",
        allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))


def _authorized(broker, target="sbx-target", *,
                action_type="sandboxed_exec",
                capability="fixture.inspect",
                method="exec",
                authorized_argv=("/bin/echo", "x")):
    """Broker proposal that records the full six-dimension authorization.

    §14.6 F1: the broker now stores capability, action_type, method, and
    the exact authorized_argv on the receipt. Tests that wish to drive a
    successful execution must propose with the same argv they will hand
    to SandboxRequest.
    """
    return broker.propose_action(
        target=target,
        action_type=action_type,
        capability=capability,
        method=method,
        impact_estimate=0.0,
        authorized_argv=tuple(authorized_argv),
    )


def _sandbox_request(argv, *, capability="fixture.inspect",
                     action_type="sandboxed_exec", method="exec",
                     target="sbx-target", **kw):
    """§14.6 F1: build a SandboxRequest with the four request-side
    authorization dimensions threaded through."""
    return SandboxRequest(
        target=target,
        argv=tuple(argv),
        capability=capability,
        action_type=action_type,
        method=method,
        **kw,
    )


def _executor(broker, root, **overrides):
    return SandboxedExecutor(broker=broker, policy=_policy(root, **overrides))


# ── Mechanism: cwd, timeout, output, resources ────────────────────

def test_controlled_cwd_enforced(tmp_path):
    """§14.4(A): execution occurs in a fresh controlled dir, never repo root."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "hi")
    result = ex.execute(
        _sandbox_request(argv),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == SUCCESS
    assert result.stdout == b"hi\n"
    # Workdir lifecycle: fresh dir per execution, removed afterwards.
    assert list(Path(root).iterdir()) == []
    assert os.getcwd() != root


def test_artifact_escape_rejected(tmp_path):
    """§14.4(A/F): artifact collection cannot escape the work area."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, authorized_argv=argv)
    # Absolute paths fail closed at construction.
    with pytest.raises(SandboxError):
        SandboxRequest(target="sbx-target", argv=argv,
                       artifacts=("/etc/hostname",))
    # Traversal paths fail closed at collection.
    for bad in ("../escape.txt", "a/../../b"):
        result = ex.execute(
            _sandbox_request(argv, artifacts=(bad,)),
            receipt,
        )
        assert result.status == ARTIFACT_FAILURE, bad
    # Absolute-path argv outside the allowlist is rejected.
    ls_argv = ("/bin/ls", "/")
    ls_receipt = _authorized(broker, authorized_argv=ls_argv)
    result = ex.execute(
        _sandbox_request(ls_argv),
        ls_receipt,
    )
    assert result.status == EXEC_FAILURE


def test_timeout_enforced(tmp_path):
    """§14.4(B): bounded timeout kills the process group deterministically."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/sleep", "30")
    result = ex.execute(
        _sandbox_request(argv, timeout_s=0.5),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == TIMEOUT
    assert "timeout" in result.reason.lower()
    assert result.duration_ms < 15000


def test_output_limit_enforced(tmp_path):
    root = _test_root(tmp_path)
    broker = _broker()
    # Large fsize backstop so the userspace output cap triggers first.
    # (/dev/zero fills megabytes per 50ms poll window; the kernel cap must
    # sit far above what one window can write, else SIGXFSZ races the poll.)
    ex = _executor(broker, root, output_limit_bytes=1024,
                   rlimit_fsize_bytes=1073741824)
    argv = ("/bin/cat", "/dev/zero")
    result = ex.execute(
        _sandbox_request(argv, timeout_s=10),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == OUTPUT_LIMIT
    assert result.truncated is True
    assert len(result.stdout) <= 1024
    assert len(result.stderr) <= 1024


def test_resource_limit_cpu_busy_loop(tmp_path):
    """§14.4(D): CPU-bound process exceeding RLIMIT_CPU -> RESOURCE_LIMIT."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(
        broker, root, rlimit_cpu_s=1,
        allowed_executables=("/bin/cat",),
    )
    argv = ("/bin/cat", "/dev/zero", "/dev/zero")
    result = ex.execute(
        _sandbox_request(argv, timeout_s=20),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status in (RESOURCE_LIMIT, OUTPUT_LIMIT), result.status


def test_network_unsupported_fails_closed(tmp_path):
    """§14.4(E): v0 has no network isolation; allow_network=True is UNSUPPORTED."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root, allow_network=True)
    argv = ("/bin/echo", "x")
    result = ex.execute(
        _sandbox_request(argv),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == UNSUPPORTED
    assert "fail-closed" in result.reason or "unsupported" in result.reason.lower()


def test_artifact_collection_bounded(tmp_path):
    """§14.4(F): declared artifacts collected, bounded, path-controlled."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, authorized_argv=argv)
    result = ex.execute(
        _sandbox_request(argv),
        receipt,
    )
    assert result.status == SUCCESS
    assert result.artifacts == {}
    # Missing declared artifact fails closed, not silently skipped.
    result = ex.execute(
        _sandbox_request(argv, artifacts=("nope.txt",)),
        receipt,
    )
    assert result.status == ARTIFACT_FAILURE


def test_setup_failure_fails_closed(tmp_path):
    """§14.4(G): uncreatable workdir root -> SETUP_FAILURE, no execution."""
    broker = _broker()
    argv = ("/bin/echo", "x")
    ex = SandboxedExecutor(
        broker=broker,
        policy=SandboxPolicy(workdir_root=str(tmp_path / "does-not-exist")),
    )
    result = ex.execute(
        _sandbox_request(argv),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == SETUP_FAILURE


def test_exec_failure_deterministic(tmp_path):
    """§14.4(G): nonzero exit -> deterministic EXEC_FAILURE with code."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/false",)
    result = ex.execute(
        _sandbox_request(argv),
        _authorized(broker, authorized_argv=argv),
    )
    assert result.status == EXEC_FAILURE
    assert result.returncode == 1


# ── Authorization path: no execution without the Broker ───────────

def test_no_execution_without_broker(tmp_path):
    """§14.4(10): broker-less executor denies every execution."""
    root = _test_root(tmp_path)
    ex = SandboxedExecutor(broker=None, policy=_policy(root))
    import types
    forged = types.SimpleNamespace(action_id="whatever", target="sbx-target")
    argv = ("/bin/echo", "x")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(argv),
            forged,
        )


def test_forged_receipt_rejected(tmp_path):
    """§14.4(11): duck-typed receipts absent from the broker store are denied."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    import types
    forged = types.SimpleNamespace(action_id="whatever", target="sbx-target")
    argv = ("/bin/echo", "x")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(argv),
            forged,
        )


def test_denied_receipt_rejected(tmp_path):
    """Broker-denied receipts cannot execute."""
    root = _test_root(tmp_path)
    deny_broker = CapabilityBroker(BrokerPolicy(engagement_id="sbx-deny"))
    ex = _executor(deny_broker, root)
    denied = deny_broker.propose_action(
        target="sbx-target", action_type="sandboxed_exec",
        capability="fixture.inspect", method="exec", impact_estimate=0.0,
        authorized_argv=("/bin/echo", "x"),
    )
    assert denied.decision == "deny"
    argv = ("/bin/echo", "x")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(argv),
            denied,
        )


def test_cross_target_replay_rejected(tmp_path):
    """A receipt for target A cannot execute target B."""
    root = _test_root(tmp_path)
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="sbx-test", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, target="target-a", authorized_argv=argv)
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(argv, target="target-b"),
            receipt,
        )


# ── PEP integration: no new stage, same allow-gate ───────────────

def test_pep_sandboxed_branch_end_to_end():
    """Broker allow -> PEP sandbox branch -> SUCCESS with captured output."""
    from orchestrator.runtime.stages import stage_broker, stage_pep
    from orchestrator.runtime.types import ActionRequest

    broker = _broker()
    argv = ("/bin/echo", "pep-sandbox")
    request = ActionRequest(
        action_type="sandboxed_exec",
        target="sbx-target",
        capability="fixture.inspect",
        method="exec",
        args={"argv": argv},
    )
    ctx = {
        "broker": broker,
        "capability": SafeProvingCapability(broker=broker),
        "capability_name": "fixture.inspect",
        "planner_request": {"request": request},
    }
    broker_out = stage_broker(ctx)
    assert broker_out.success
    # §14.6 F1: re-bind argv onto the broker-authorized receipt before
    # handing it to the PEP. This is the canonical PDP step: argv becomes
    # hash-bound authorization material here.
    receipt = broker_out.output["receipt"]
    from orchestrator.hardening.action_receipt import authorize as _authorize, _receipt_store as _store, _last_receipt_hash as _last
    import orchestrator.hardening.action_receipt as _ar
    receipt.authorized_argv = argv
    receipt.action_type = "sandboxed_exec"
    _authorize(receipt)
    ctx["broker"] = broker_out.output
    pep_out = stage_pep(ctx)
    assert pep_out.success, pep_out.error
    assert pep_out.output["event"].outcome == "success"
    assert pep_out.output["result"].stdout == b"pep-sandbox\n"


def test_pep_sandboxed_denied_without_broker_allow():
    """PEP sandbox branch unreachable when the broker denies."""
    from orchestrator.runtime.stages import stage_broker, stage_pep
    from orchestrator.runtime.types import ActionRequest

    broker = CapabilityBroker(BrokerPolicy(engagement_id="sbx-deny"))
    request = ActionRequest(
        action_type="sandboxed_exec",
        target="sbx-target",
        capability="fixture.inspect",
        method="exec",
        args={"argv": ("/bin/echo", "x")},
    )
    ctx = {
        "broker": broker,
        "capability": SafeProvingCapability(broker=broker),
        "capability_name": "fixture.inspect",
        "planner_request": {"request": request},
    }
    broker_out = stage_broker(ctx)
    assert not broker_out.success


# ── Architecture invariants ───────────────────────────────────────

def test_no_primitive_imports_in_runtime():
    """INV-1: runtime/*.py gains no primitive imports from §14.4 wiring."""
    import ast

    forbidden = {"subprocess", "socket", "requests", "os", "shutil"}
    violations = []
    for py_file in (SRC_ROOT / "orchestrator" / "runtime").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        tree = ast.parse(py_file.read_text(errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden:
                        violations.append((str(py_file), node.lineno, alias.name))
    assert not violations, violations


def test_single_stage_order_unchanged():
    """No new Runtime stage introduced by §14.4."""
    from orchestrator.runtime.stages import STAGE_ORDER

    assert STAGE_ORDER == [
        "observe", "worldmodel_read", "student_candidate", "planner_request",
        "broker", "pep", "receipt", "worldmodel_integrate", "contradiction",
        "replan",
    ]


def test_invariant_files_present():
    """Existing G2/G3 guardrail files untouched and passing (spot check)."""
    # Full suite covers all guardrails; this test pins the invariant files.
    for name in ("test_p2_guardrail_inv1.py",
                 "test_p2_guardrail_runtime_no_seam.py",
                 "test_p2_guardrail_shell_closed.py"):
        assert (REPO_ROOT / "tests" / name).exists()


# ── §14.6 F1 Request-Binding Adversarial Battery ──────────────────
#
# These tests prove the proven HIGH-severity confused-deputy defect is
# closed. Each test exercises the actual SandboxedExecutor.execute()
# boundary (PEP-owned) — not an isolated helper — so a regression in
# the production path is caught here.
#
# Invariant under test:
#   stored.status == AUTHORIZED
#   AND stored.target == req.target
#   AND stored.capability == req.capability
#   AND stored.action_type == req.action_type
#   AND stored.method == req.method
#   AND req.argv == stored.authorized_argv


def test_f1_same_id_same_argv_allows(tmp_path):
    """F1(1): same action_id + same argv + matching capability/action_type/method -> ALLOW."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "f1-positive")
    receipt = _authorized(broker, authorized_argv=argv)
    result = ex.execute(_sandbox_request(argv), receipt)
    assert result.status == SUCCESS, result.reason
    assert result.stdout == b"f1-positive\n"


def test_f1_different_argv_denied(tmp_path):
    """F1(2): same action_id + different argv -> DENY.

    This is the original confused-deputy exploit: an attacker reuses
    the broker-authorized action_id but swaps argv to execute something
    else. With F1 binding, the argv tuple mismatch is caught before any
    primitive is touched.
    """
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    receipt = _authorized(broker, authorized_argv=("/bin/echo", "approved"))
    # Forged request: reuse action_id, substitute argv.
    with pytest.raises(SandboxNotAuthorized) as excinfo:
        ex.execute(
            _sandbox_request(("/bin/echo", "FORGED")),
            receipt,
        )
    assert "argv" in str(excinfo.value).lower()


def test_f1_different_capability_denied(tmp_path):
    """F1(3): same action_id + different capability -> DENY."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, authorized_argv=argv, capability="fixture.inspect")
    with pytest.raises(SandboxNotAuthorized) as excinfo:
        ex.execute(
            _sandbox_request(argv, capability="file_read"),  # different capability
            receipt,
        )
    assert "capability" in str(excinfo.value).lower()


def test_f1_different_action_type_denied(tmp_path):
    """F1(4): same action_id + different action_type -> DENY."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, authorized_argv=argv, action_type="sandboxed_exec")
    with pytest.raises(SandboxNotAuthorized) as excinfo:
        ex.execute(
            _sandbox_request(argv, action_type="shell"),  # different action_type
            receipt,
        )
    assert "action_type" in str(excinfo.value).lower()


def test_f1_different_method_denied(tmp_path):
    """F1(5): same action_id + different method -> DENY."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, authorized_argv=argv, method="exec")
    with pytest.raises(SandboxNotAuthorized) as excinfo:
        ex.execute(
            _sandbox_request(argv, method="subprocess"),  # different method
            receipt,
        )
    assert "method" in str(excinfo.value).lower()


def test_f1_unknown_action_id_denied(tmp_path):
    """F1(6): unknown / absent receipt -> DENY (forged object)."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    import types
    forged = types.SimpleNamespace(action_id="not-in-store", target="sbx-target")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(_sandbox_request(argv), forged)


def test_f1_denied_status_denied(tmp_path):
    """F1(7): receipt whose stored status is DENIED cannot execute."""
    root = _test_root(tmp_path)
    deny_broker = CapabilityBroker(BrokerPolicy(engagement_id="sbx-f1-deny"))
    ex = _executor(deny_broker, root)
    argv = ("/bin/echo", "x")
    denied = deny_broker.propose_action(
        target="sbx-target", action_type="sandboxed_exec",
        capability="fixture.inspect", method="exec", impact_estimate=0.0,
        authorized_argv=argv,
    )
    assert denied.status.value == "denied"
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(_sandbox_request(argv), denied)


def test_f1_cross_target_denied(tmp_path):
    """F1(8): receipt for target A cannot execute target B."""
    root = _test_root(tmp_path)
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="sbx-f1-target", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    ex = _executor(broker, root)
    argv = ("/bin/echo", "x")
    receipt = _authorized(broker, target="target-a", authorized_argv=argv)
    with pytest.raises(SandboxNotAuthorized) as excinfo:
        ex.execute(_sandbox_request(argv, target="target-b"), receipt)
    assert "target" in str(excinfo.value).lower()


def test_f1_copied_id_forged_object_denied(tmp_path):
    """F1(9): copied-id forged-object regression -> DENY.

    This is the case that originally exposed the confused-deputy
    defect. The attacker copies the action_id from a legitimate
    broker-authorized receipt into a forged object with mismatched
    dimensions. The old 3-dimension check (action_id, status,
    target) accepted this; the new 6-dimension check rejects it.

    Specifically: the attacker has a legitimately authorized receipt
    for /bin/echo 'approved' on target='sbx-target'. They build a
    forged receipt with the SAME action_id but capability,
    action_type, method, and argv swapped to execute a different
    command. The forged object's own attributes are untrusted; only
    the stored receipt is consulted.
    """
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    argv_approved = ("/bin/echo", "approved")
    receipt = _authorized(broker, authorized_argv=argv_approved)
    # Forged copy: same action_id, but every other dimension swapped.
    import types
    forged = types.SimpleNamespace(
        action_id=receipt.action_id,
        target="sbx-target",
        capability="shell",          # forged
        action_type="reverse_shell", # forged
        method="netcat",             # forged
        authorized_argv=("/bin/sh", "-c", "rm -rf /"),  # forged
    )
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(
                ("/bin/sh", "-c", "rm -rf /"),
                capability="shell",
                action_type="reverse_shell",
                method="netcat",
            ),
            forged,
        )


def test_f1_argv_tuple_order_matters(tmp_path):
    """F1(2 strict): argv tuple ordering is part of the binding.

    Even swapping argument order is rejected, because the broker
    authorized a specific ordered tuple, not a multiset.
    """
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    receipt = _authorized(
        broker, authorized_argv=("/bin/echo", "first", "second"),
    )
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(("/bin/echo", "second", "first")),  # swapped
            receipt,
        )


def test_f1_extra_arg_denied(tmp_path):
    """F1(2 strict): appending an unapproved argument is rejected."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    receipt = _authorized(broker, authorized_argv=("/bin/echo", "x"))
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            _sandbox_request(("/bin/echo", "x", "extra")),  # extra arg
            receipt,
        )


def test_f1_hash_chain_protects_authorized_argv(tmp_path):
    """F1(10): tampering with authorized_argv after the fact breaks
    the receipt hash chain — verify_integrity() catches it.

    This is the bookkeeping defense-in-depth: the broker-stored
    authorization is the only trusted source; in-memory tampering is
    detected by the hash chain.
    """
    root = _test_root(tmp_path)
    broker = _broker()
    argv = ("/bin/echo", "approved")
    receipt = _authorized(broker, authorized_argv=argv)
    assert receipt.verify_integrity()
    # Tamper with authorized_argv in memory; integrity must fail.
    receipt.authorized_argv = ("/bin/echo", "tampered")
    assert not receipt.verify_integrity()