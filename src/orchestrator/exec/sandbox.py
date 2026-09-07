"""
sandbox.py — Raphael-native minimal sandbox mechanism (§14.4).

Bounded, auditable execution primitive owned by exec/ (the PEP package,
per v4 L6). This module holds process/file primitives, which is permitted
ONLY inside exec/ (INV-1).

Conceptual chain (sandbox is a mechanism, NOT an authorization boundary):

    Mission Scope (constraint)
        -> CapabilityBroker (sole PDP: allow/deny)
        -> PEP / stage_pep (sole enforcement point)
        -> exec/ primitives (this module)
        -> SandboxResult (receipt-consumable outcome)

Authorization: execute() requires a Broker-issued ActionReceipt that is
present in the broker's own receipt_store with status AUTHORIZED and a
matching target. The STORED receipt's fields decide — the passed object
is only a lookup key. Absent/forged/denied/cross-target receipts raise
SandboxNotAuthorized (fail-closed, CONV-3 convention). No bypass flag,
no unsafe mode, no authorized=True convention, no new registry.

Enforced in v0 (honest matrix — see module docstring claims only):
- controlled cwd: mkdtemp under policy root; Popen(cwd=workdir); repo root
  never used; setup failure -> SETUP_FAILURE result.
- timeout: deadline + process-group kill (setsid/killpg) + bounded reap.
- output limit: combined stdout+stderr size polled during execution; kill
  on exceed -> OUTPUT_LIMIT; kernel backstop via RLIMIT_FSIZE.
- resource limits: RLIMIT_CPU + RLIMIT_FSIZE via preexec (setsid group).
  RLIMIT_AS/memory caps are NOT claimed in v0 (unreliable to size here).
- network: NO kernel isolation in v0. allow_network=True -> UNSUPPORTED
  fail-closed. Local-only posture via: no shell, argv[0] must resolve to
  an entry of the static executable allowlist, stdin DEVNULL, minimal
  scrubbed env. This mitigates unintended network access; it is NOT a
  network-isolation guarantee and is not presented as one.
- artifacts: declared relative paths only, realpath-contained in workdir,
  per-file size cap; missing/escaping/oversize -> ARTIFACT_FAILURE.
- results: deterministic SandboxResult (status, returncode, truncated
  outputs, artifacts, reason). No second receipt authority: the result
  feeds the existing ExecutionEvent/receipt path via stage_pep.

Single-threaded sequencer assumption: preexec_fn performs only
async-signal-safe syscalls (setsid, setrlimit). The canonical Runtime
loop is single-threaded; do not call execute() from worker threads.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import resource as _resource
except ImportError:  # pragma: no cover - non-POSIX platform
    _resource = None


# ── Statuses (mechanism outcomes, not authorization decisions) ──

SUCCESS = "success"
TIMEOUT = "timeout"
OUTPUT_LIMIT = "output_limit"
RESOURCE_LIMIT = "resource_limit"
SETUP_FAILURE = "setup_failure"
EXEC_FAILURE = "exec_failure"
ARTIFACT_FAILURE = "artifact_failure"
UNSUPPORTED = "unsupported"

_POLL_INTERVAL_S = 0.05
_REAP_TIMEOUT_S = 5.0
_MINIMAL_ENV = {"PATH": "/usr/bin:/bin"}

# Local-only executables (absolute paths; compared after realpath).
# These binaries do not initiate network access. No shell is ever used.
DEFAULT_ALLOWED_EXECUTABLES = (
    "/bin/true",
    "/bin/false",
    "/bin/echo",
    "/bin/sleep",
    "/bin/cat",
)


class SandboxError(Exception):
    """Mechanism misuse or internal failure (fail-closed)."""
    pass


class SandboxNotAuthorized(Exception):
    """Raised when execution lacks a valid Broker-issued receipt (CONV-3)."""
    pass


@dataclass(frozen=True)
class SandboxPolicy:
    """Static mechanism bounds. Not authorization; not per-request policy."""

    workdir_root: str = ""
    timeout_s: float = 10.0
    output_limit_bytes: int = 65536
    artifact_limit_bytes: int = 65536
    rlimit_cpu_s: int = 5
    rlimit_fsize_bytes: int = 262144
    allow_network: bool = False
    allowed_executables: tuple = DEFAULT_ALLOWED_EXECUTABLES

    def __post_init__(self) -> None:
        if not isinstance(self.workdir_root, str) or not self.workdir_root:
            raise SandboxError("SandboxPolicy: 'workdir_root' must be set")
        if not self.timeout_s > 0:
            raise SandboxError("SandboxPolicy: 'timeout_s' must be > 0")
        if not self.output_limit_bytes > 0:
            raise SandboxError("SandboxPolicy: 'output_limit_bytes' must be > 0")
        if not self.artifact_limit_bytes > 0:
            raise SandboxError("SandboxPolicy: 'artifact_limit_bytes' must be > 0")
        if not self.rlimit_cpu_s > 0:
            raise SandboxError("SandboxPolicy: 'rlimit_cpu_s' must be > 0")
        if not self.rlimit_fsize_bytes > 0:
            raise SandboxError("SandboxPolicy: 'rlimit_fsize_bytes' must be > 0")
        object.__setattr__(
            self, "allowed_executables", tuple(self.allowed_executables)
        )

@dataclass(frozen=True)
class SandboxRequest:
    """What to run. argv[0] allowlisted; no shell; relative artifact paths.

    §14.6 F1: the request carries the four request-side authorization
    dimensions (capability, action_type, method) plus argv. The PEP/sandbox
    MUST verify that every dimension matches the broker-stored
    authorization material before any primitive is touched.
    """

    target: str
    argv: tuple
    artifacts: tuple = ()
    timeout_s: Optional[float] = None
    # F1: request-side dimensions, threaded from the planner / broker
    # call. Compared element-wise against the stored receipt below.
    capability: str = ""
    action_type: str = ""
    method: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.target, str) or not self.target:
            raise SandboxError("SandboxRequest: 'target' must be non-empty")
        if not isinstance(self.argv, (tuple, list)) or not self.argv:
            raise SandboxError("SandboxRequest: 'argv' must be non-empty")
        if any(not isinstance(a, str) or not a for a in self.argv):
            raise SandboxError("SandboxRequest: argv entries must be non-empty strings")
        object.__setattr__(self, "argv", tuple(self.argv))
        object.__setattr__(self, "artifacts", tuple(self.artifacts or ()))
        for artifact in self.artifacts:
            if not isinstance(artifact, str) or not artifact:
                raise SandboxError("SandboxRequest: artifact paths must be strings")
            if os.path.isabs(artifact):
                raise SandboxError(
                    f"SandboxRequest: artifact must be relative: {artifact!r}"
                )

@dataclass
class SandboxResult:
    """Deterministic mechanism outcome for the receipt/evidence path."""

    status: str
    returncode: Optional[int] = None
    stdout: bytes = b""
    stderr: bytes = b""
    truncated: bool = False
    artifacts: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    reason: str = ""

def _check_receipt(broker: Any, request: "SandboxRequest", receipt: Any) -> None:
    """Verify Broker-issued authorization using the broker's own store.

    §14.6 F1 request-binding invariant (the proven HIGH-severity confused-
    deputy defect fix): the receipt is consulted only as a lookup handle,
    not as a self-authenticating object. The six-dimension authorization
    invariant is::

        stored.status == AUTHORIZED
        AND stored.target == req.target
        AND stored.capability == req.capability
        AND stored.action_type == req.action_type
        AND stored.method == req.method
        AND req.argv == stored.authorized_argv

    Raises SandboxNotAuthorized on: no broker, missing receipt, unknown
    action_id (forged), non-AUTHORIZED stored status, or any dimension
    mismatch. Only the STORED receipt's fields are trusted — the passed
    receipt object itself is treated as an untrusted lookup handle.
    """
    if broker is None:
        raise SandboxNotAuthorized("Sandbox: no broker bound; execution denied")
    action_id = getattr(receipt, "action_id", None)
    if not action_id:
        raise SandboxNotAuthorized("Sandbox: missing action receipt; denied")
    store = getattr(broker, "receipt_store", None)
    stored = store.get(action_id) if isinstance(store, dict) else None
    if stored is None:
        raise SandboxNotAuthorized(
            f"Sandbox: unknown action_id '{action_id}'; not Broker-issued"
        )
    from orchestrator.hardening.action_receipt import ActionProposalStatus

    if stored.status != ActionProposalStatus.AUTHORIZED:
        raise SandboxNotAuthorized(
            f"Sandbox: receipt '{action_id}' is not AUTHORIZED "
            f"(status={stored.status}); denied"
        )
    if stored.target != request.target:
        raise SandboxNotAuthorized(
            f"Sandbox: receipt target '{stored.target}' does not match "
            f"execution target '{request.target}'; denied"
        )
    # F1: bind capability. The broker recorded the authorized capability
    # at proposal time; the request must match.
    if stored.capability != request.capability:
        raise SandboxNotAuthorized(
            f"Sandbox: receipt capability '{stored.capability}' does not "
            f"match request capability '{request.capability}'; denied"
        )
    # F1: bind action_type. Previously stored only in receipt.metadata
    # (not hash-bound); now promoted to a top-level hash-bound field.
    if stored.action_type != request.action_type:
        raise SandboxNotAuthorized(
            f"Sandbox: receipt action_type '{stored.action_type}' does not "
            f"match request action_type '{request.action_type}'; denied"
        )
    # F1: bind method. nmap vs curl vs subprocess matters.
    if stored.method != request.method:
        raise SandboxNotAuthorized(
            f"Sandbox: receipt method '{stored.method}' does not match "
            f"request method '{request.method}'; denied"
        )
    # F1: bind argv. The exact argv tuple the broker authorized must
    # match the executing argv. Reject forged or tampered copies that
    # swap args while reusing the action_id (the original confused-deputy
    # exploit).
    if tuple(stored.authorized_argv) != tuple(request.argv):
        raise SandboxNotAuthorized(
            f"Sandbox: request argv {tuple(request.argv)!r} does not match "
            f"broker-authorized argv {tuple(stored.authorized_argv)!r}; denied"
        )


def _resolve_executable(argv0: str, allowed: tuple) -> str:
    """Resolve argv[0] against the static allowlist (realpath both sides)."""
    if os.path.basename(argv0) != argv0 and not os.path.isabs(argv0):
        raise SandboxError(f"Sandbox: executable must be absolute: {argv0!r}")
    candidate = os.path.realpath(argv0) if os.path.isabs(argv0) else argv0
    allowed_resolved = {os.path.realpath(p) for p in allowed}
    if candidate not in allowed_resolved:
        raise SandboxError(f"Sandbox: executable not allowlisted: {argv0!r}")
    if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
        raise SandboxError(f"Sandbox: executable not runnable: {candidate!r}")
    return candidate


def _preexec_limits(cpu_s: int, fsize_bytes: int):
    """preexec_fn: new session + rlimits. Syscalls only (fork-safe)."""
    os.setsid()
    if _resource is not None:
        _resource.setrlimit(_resource.RLIMIT_CPU, (cpu_s, cpu_s))
        _resource.setrlimit(_resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))


class SandboxedExecutor:
    """PEP-owned bounded execution mechanism (exec/ confined)."""

    def __init__(self, broker: Any, policy: SandboxPolicy):
        if not isinstance(policy, SandboxPolicy):
            raise SandboxError("SandboxedExecutor: policy must be a SandboxPolicy")
        self._broker = broker
        self._policy = policy

    @property
    def policy(self) -> SandboxPolicy:
        return self._policy

    def execute(self, request: SandboxRequest, receipt: Any) -> SandboxResult:
        """Run a Broker-authorized request inside the minimal sandbox.

        §14.6 F1: authorization is verified against the stored receipt
        across six dimensions before any primitive is touched.
        """
        t0 = time.time()
        _check_receipt(self._broker, request, receipt)
        policy = self._policy

        if policy.allow_network:
            # v0 has no kernel network isolation: granting network fails closed.
            return SandboxResult(
                status=UNSUPPORTED,
                duration_ms=(time.time() - t0) * 1000.0,
                reason="Sandbox v0: network isolation unavailable; "
                "allow_network=True is unsupported (fail-closed)",
            )
        if _resource is None:
            return SandboxResult(
                status=UNSUPPORTED,
                duration_ms=(time.time() - t0) * 1000.0,
                reason="Sandbox v0: POSIX resource limits unavailable (fail-closed)",
            )
        try:
            resolved = _resolve_executable(request.argv[0], policy.allowed_executables)
        except SandboxError as exc:
            return SandboxResult(
                status=EXEC_FAILURE,
                duration_ms=(time.time() - t0) * 1000.0,
                reason=str(exc),
            )

        timeout = request.timeout_s if request.timeout_s else policy.timeout_s
        try:
            workdir = Path(
                tempfile.mkdtemp(prefix="raphael-sbx-", dir=policy.workdir_root)
            )
        except OSError as exc:
            return SandboxResult(
                status=SETUP_FAILURE,
                duration_ms=(time.time() - t0) * 1000.0,
                reason=f"Sandbox: workdir setup failed: {exc}",
            )
        try:
            return self._run(
                resolved, request, policy, workdir, timeout, t0,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _run(
        self,
        resolved: str,
        request: SandboxRequest,
        policy: SandboxPolicy,
        workdir: Path,
        timeout: float,
        t0: float,
    ) -> SandboxResult:
        def elapsed_ms() -> float:
            return (time.time() - t0) * 1000.0

        stdout_path = workdir / "stdout.cap"
        stderr_path = workdir / "stderr.cap"
        try:
            out_f = open(stdout_path, "wb")
            err_f = open(stderr_path, "wb")
        except OSError as exc:
            return SandboxResult(
                status=SETUP_FAILURE, duration_ms=elapsed_ms(),
                reason=f"Sandbox: capture setup failed: {exc}",
            )
        try:
            proc = subprocess.Popen(
                [resolved, *request.argv[1:]],
                cwd=str(workdir),
                stdout=out_f,
                stderr=err_f,
                stdin=subprocess.DEVNULL,
                env=dict(_MINIMAL_ENV),
                preexec_fn=lambda: _preexec_limits(
                    policy.rlimit_cpu_s, policy.rlimit_fsize_bytes
                ),
            )
        except OSError as exc:
            out_f.close()
            err_f.close()
            return SandboxResult(
                status=EXEC_FAILURE, duration_ms=elapsed_ms(),
                reason=f"Sandbox: spawn failed: {exc}",
            )

        deadline = time.time() + timeout
        killed_for: Optional[str] = None
        returncode: Optional[int] = None
        while True:
            try:
                returncode = proc.wait(timeout=_POLL_INTERVAL_S)
                break
            except subprocess.TimeoutExpired:
                pass
            try:
                size = stdout_path.stat().st_size + stderr_path.stat().st_size
            except OSError:
                size = 0
            if size > policy.output_limit_bytes and killed_for is None:
                killed_for = OUTPUT_LIMIT
                self._kill_group(proc)
            if time.time() >= deadline and killed_for is None:
                killed_for = TIMEOUT
                self._kill_group(proc)
            if killed_for is not None and returncode is None:
                try:
                    returncode = proc.wait(timeout=_REAP_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    self._kill_group(proc, sig=signal.SIGKILL)
                    try:
                        returncode = proc.wait(timeout=_REAP_TIMEOUT_S)
                    except subprocess.TimeoutExpired:  # pragma: no cover
                        pass
                break
        out_f.close()
        err_f.close()

        stdout = self._read_capped(stdout_path, policy.output_limit_bytes)
        stderr = self._read_capped(stderr_path, policy.output_limit_bytes)
        truncated = killed_for == OUTPUT_LIMIT

        if killed_for == TIMEOUT:
            status = TIMEOUT
            reason = f"Sandbox: timeout after {timeout}s (process group killed)"
        elif killed_for == OUTPUT_LIMIT:
            status = OUTPUT_LIMIT
            reason = (
                f"Sandbox: combined output exceeded "
                f"{policy.output_limit_bytes} bytes (killed, truncated)"
            )
        elif returncode is None:  # pragma: no cover - reap failed
            status = EXEC_FAILURE
            reason = "Sandbox: process reap failed after kill"
        elif returncode < 0:
            status = RESOURCE_LIMIT
            reason = (
                f"Sandbox: process died by signal {-returncode} "
                f"(resource limit: cpu={policy.rlimit_cpu_s}s, "
                f"fsize={policy.rlimit_fsize_bytes}B)"
            )
        elif returncode != 0:
            status = EXEC_FAILURE
            reason = f"Sandbox: process exited with code {returncode}"
        else:
            status = SUCCESS
            reason = f"Sandbox: process exited 0 in {elapsed_ms():.1f}ms"

        artifacts: dict = {}
        if request.artifacts or status == SUCCESS:
            artifact_status = self._collect_artifacts(
                workdir, request.artifacts, policy, artifacts,
            )
            if artifact_status is not None:
                return SandboxResult(
                    status=ARTIFACT_FAILURE, returncode=returncode,
                    stdout=stdout, stderr=stderr, truncated=truncated,
                    duration_ms=elapsed_ms(), reason=artifact_status,
                )
        return SandboxResult(
            status=status, returncode=returncode, stdout=stdout,
            stderr=stderr, truncated=truncated, artifacts=artifacts,
            duration_ms=elapsed_ms(), reason=reason,
        )

    @staticmethod
    def _kill_group(proc: "subprocess.Popen", sig: int = signal.SIGKILL) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (OSError, ProcessLookupError):
            pass

    @staticmethod
    def _read_capped(path: Path, limit: int) -> bytes:
        try:
            with open(path, "rb") as handle:
                return handle.read(limit + 1)[:limit]
        except OSError:
            return b""

    @staticmethod
    def _collect_artifacts(
        workdir: Path,
        declared: tuple,
        policy: SandboxPolicy,
        sink: dict,
    ) -> Optional[str]:
        """Collect declared artifacts. Returns failure reason or None."""
        root = workdir.resolve()
        for relpath in declared:
            if relpath.startswith("/") or ".." in Path(relpath).parts:
                return f"Sandbox: artifact escapes workdir: {relpath!r}"
            candidate = (root / relpath).resolve()
            try:
                inside = candidate == root or root in candidate.parents
            except (OSError, RuntimeError):
                return f"Sandbox: artifact unresolvable: {relpath!r}"
            if not inside:
                return f"Sandbox: artifact escapes workdir: {relpath!r}"
            if not candidate.is_file():
                return f"Sandbox: artifact missing: {relpath!r}"
            try:
                if candidate.stat().st_size > policy.artifact_limit_bytes:
                    return f"Sandbox: artifact oversize: {relpath!r}"
                sink[relpath] = candidate.read_bytes()
            except OSError as exc:
                return f"Sandbox: artifact unreadable: {relpath!r}: {exc}"
        return None
