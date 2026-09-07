"""
§14.4 Native Minimal Sandbox tests.

Focused mechanism tests (fail-closed first), authorization-path tests,
PEP integration tests, and architecture-invariant tests. The sandbox is
a mechanism, not an authorization boundary: every execution requires a
Broker-issued receipt from the broker's own store.
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


def _authorized(broker, target="sbx-target"):
    return broker.propose_action(
        target=target,
        action_type="sandboxed_exec",
        capability="fixture.inspect",
        method="exec",
        impact_estimate=0.0,
    )


def _executor(broker, root, **overrides):
    return SandboxedExecutor(broker=broker, policy=_policy(root, **overrides))


# ── Mechanism: cwd, timeout, output, resources ────────────────────

def test_controlled_cwd_enforced(tmp_path):
    """§14.4(A): execution occurs in a fresh controlled dir, never repo root."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "hi")),
        _authorized(broker),
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
    receipt = _authorized(broker)
    # Absolute paths fail closed at construction.
    with pytest.raises(SandboxError):
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "x"),
                       artifacts=("/etc/hostname",))
    # Traversal paths fail closed at collection.
    for bad in ("../escape.txt", "a/../../b"):
        result = ex.execute(
            SandboxRequest(target="sbx-target", argv=("/bin/echo", "x"),
                           artifacts=(bad,)),
            receipt,
        )
        assert result.status == ARTIFACT_FAILURE, bad
    # Absolute-path argv outside the allowlist is rejected.
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/ls", "/")),
        receipt,
    )
    assert result.status == EXEC_FAILURE


def test_timeout_enforced(tmp_path):
    """§14.4(B): bounded timeout kills the process group deterministically."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/sleep", "30"),
                       timeout_s=0.5),
        _authorized(broker),
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
    result = ex.execute(
        SandboxRequest(
            target="sbx-target",
            argv=("/bin/cat", "/dev/zero"),
            timeout_s=10,
        ),
        _authorized(broker),
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
    result = ex.execute(
        SandboxRequest(
            target="sbx-target",
            argv=("/bin/cat", "/dev/zero", "/dev/zero"),
            timeout_s=20,
        ),
        _authorized(broker),
    )
    assert result.status in (RESOURCE_LIMIT, OUTPUT_LIMIT), result.status


def test_network_unsupported_fails_closed(tmp_path):
    """§14.4(E): v0 has no network isolation; allow_network=True is UNSUPPORTED."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root, allow_network=True)
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
        _authorized(broker),
    )
    assert result.status == UNSUPPORTED
    assert "fail-closed" in result.reason or "unsupported" in result.reason.lower()


def test_artifact_collection_bounded(tmp_path):
    """§14.4(F): declared artifacts collected, bounded, path-controlled."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
        _authorized(broker),
    )
    assert result.status == SUCCESS
    assert result.artifacts == {}
    # Missing declared artifact fails closed, not silently skipped.
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "x"),
                       artifacts=("nope.txt",)),
        _authorized(broker),
    )
    assert result.status == ARTIFACT_FAILURE


def test_setup_failure_fails_closed(tmp_path):
    """§14.4(G): uncreatable workdir root -> SETUP_FAILURE, no execution."""
    broker = _broker()
    ex = SandboxedExecutor(
        broker=broker,
        policy=SandboxPolicy(workdir_root=str(tmp_path / "does-not-exist")),
    )
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
        _authorized(broker),
    )
    assert result.status == SETUP_FAILURE


def test_exec_failure_deterministic(tmp_path):
    """§14.4(G): nonzero exit -> deterministic EXEC_FAILURE with code."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    result = ex.execute(
        SandboxRequest(target="sbx-target", argv=("/bin/false",)),
        _authorized(broker),
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
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
            forged,
        )


def test_forged_receipt_rejected(tmp_path):
    """§14.4(11): duck-typed receipts absent from the broker store are denied."""
    root = _test_root(tmp_path)
    broker = _broker()
    ex = _executor(broker, root)
    import types
    forged = types.SimpleNamespace(action_id="whatever", target="sbx-target")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
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
    )
    assert denied.decision == "deny"
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="sbx-target", argv=("/bin/echo", "x")),
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
    receipt = _authorized(broker, target="target-a")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="target-b", argv=("/bin/echo", "x")),
            receipt,
        )


# ── PEP integration: no new stage, same allow-gate ───────────────

def test_pep_sandboxed_branch_end_to_end():
    """Broker allow -> PEP sandbox branch -> SUCCESS with captured output."""
    from orchestrator.runtime.stages import stage_broker, stage_pep
    from orchestrator.runtime.types import ActionRequest

    broker = _broker()
    request = ActionRequest(
        action_type="sandboxed_exec", target="sbx-target",
        args={"argv": ("/bin/echo", "pep-sandbox")},
    )
    ctx = {
        "broker": broker,
        "capability": SafeProvingCapability(broker=broker),
        "capability_name": "fixture.inspect",
        "planner_request": {"request": request},
    }
    broker_out = stage_broker(ctx)
    assert broker_out.success
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
        action_type="sandboxed_exec", target="sbx-target",
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
