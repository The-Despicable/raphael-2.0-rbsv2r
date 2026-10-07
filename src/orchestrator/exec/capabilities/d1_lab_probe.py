"""d1_lab_probe.py — the single bounded D1 execution capability (M2, 2026-10-04).

Authorizes exactly one operation: a fixed-argument ``nmap -Pn -sT -p 80``
service probe of the local DVWA lab container, executed inside the
``kali-tools`` lab container (where nmap actually lives), with the target
resolved from the declared lab identity — never from free-form input.

Contract (M2 task order §7):
- fixed, validated argument structure; no shell; no arbitrary executable
  path, targets, or flags from any request;
- the target identity is verified against the live compose lab before the
  probe runs (image prefix + shared network with the probe container);
- bounded execution time and output size;
- the raw tool output is captured as an artifact (relpath + sha256) so the
  receipt/evidence layer can bind it;
- a denied request never reaches this class (the Broker denies before the
  PEP stage), and this class additionally refuses any target other than
  the declared lab identity (defense in depth, not a second PDP);
- a failed or timed-out probe raises — the PEP records a truthful FAILED
  terminal state instead of a fabricated success.
"""
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from orchestrator.exec.safe_capability import (
    CapabilityNotGatedError,
    CapabilityResult,
)


class D1LabProbeError(RuntimeError):
    """Raised when the bounded probe cannot be executed truthfully."""


class D1LabProbeCapability:
    """The one D1 capability: governed nmap service probe of local DVWA.

    CONV-3 constructor gating: requires a bound CapabilityBroker and a
    prior ``record_authorization(target)`` (issued by the canonical PEP
    stage after an AUTHORIZED broker decision) before ``inspect`` will run.
    """

    LAB_TARGET = "dvwa"
    PROBE_CONTAINER = "kali-tools"
    TARGET_IMAGE_PREFIX = "vulnerables/web-dvwa"
    TIMEOUT_SECONDS = 90
    MAX_OUTPUT_BYTES = 65536

    # Fully fixed probe argv. ``nmap`` runs inside the kali-tools container
    # (the only environment in the lab that has it); "dvwa" resolves via
    # docker DNS on the shared compose network. No shell, no interpolation
    # beyond the verified lab identity.
    PROBE_ARGV = (
        "docker", "exec", PROBE_CONTAINER, "nmap",
        "-Pn", "-sT", "-p", "80", "--host-timeout", "45s",
        LAB_TARGET,
    )

    def __init__(self,
                 broker: Optional[Any] = None,
                 artifacts_dir: Optional[Path] = None,
                 runner: Optional[Callable[..., Any]] = None,
                 inspector: Optional[Callable[[str], dict]] = None):
        self._broker = broker
        self._artifacts_dir = Path(artifacts_dir) if artifacts_dir else None
        # runner: argv + timeout -> object with returncode/stdout/stderr
        # (subprocess.CompletedProcess-shaped). Injectable for hermetic tests;
        # the default is the real subprocess with a fixed argv list (no shell).
        self._runner = runner if runner is not None else self._subprocess_runner
        # inspector: container name -> `docker inspect` mapping. Injectable.
        self._inspector = inspector if inspector is not None else self._docker_inspect
        self._broker_authorized_targets: set = set()
        self.invocation_count = 0

    # ── CONV-3 gating surface (mirrors SafeProvingCapability) ────────────

    def gate_with_broker(self, broker) -> None:
        self._broker = broker

    def record_authorization(self, target: str) -> None:
        """Called by the canonical PEP stage after an AUTHORIZED decision."""
        self._broker_authorized_targets.add(target)

    @property
    def broker(self):
        return self._broker


    @property
    def artifact_root(self) -> Optional[Path]:
        """Bound artifact directory (or None). M3/D2 remediation: the
        objective evaluator verifies persisted artifacts against these
        ACTUAL bytes through exec/artifact_verify."""
        return self._artifacts_dir

    # ── primitive runners (INV-1: live in exec/) ─────────────────────────

    @staticmethod
    def _subprocess_runner(argv, timeout):
        return subprocess.run(
            list(argv), capture_output=True, text=True, timeout=timeout,
        )

    @staticmethod
    def _docker_inspect(container: str) -> dict:
        proc = subprocess.run(
            ["docker", "inspect", container],
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode != 0:
            raise D1LabProbeError(
                f"docker inspect {container} failed rc={proc.returncode}: "
                f"{proc.stderr.strip()[:200]}"
            )
        try:
            return json.loads(proc.stdout)[0]
        except (ValueError, IndexError) as exc:
            raise D1LabProbeError(
                f"docker inspect {container}: unparseable output: {exc}"
            ) from None

    # ── the capability itself ────────────────────────────────────────────

    def inspect(self, target: str) -> CapabilityResult:
        """Run the one bounded D1 probe. Gated by the broker (CONV-3)."""
        if self._broker is None:
            # Unlike the read-only fixture capability, this class spawns
            # processes: an unbound broker is a hard error, not a legacy mode.
            raise CapabilityNotGatedError(
                "D1LabProbeCapability requires a bound CapabilityBroker "
                "(CONV-3 constructor gating)"
            )
        if target not in self._broker_authorized_targets:
            raise CapabilityNotGatedError(
                f"Target '{target}' not authorized by broker. The canonical "
                "PEP stage must call record_authorization(target) after an "
                "AUTHORIZED broker decision."
            )
        if target != self.LAB_TARGET:
            # Defense in depth: even with a mis-built broker policy, this
            # capability refuses to probe anything but the lab identity.
            raise D1LabProbeError(
                f"D1 capability refuses non-lab target {target!r} "
                f"(authorized identity: {self.LAB_TARGET!r})"
            )
        self.invocation_count += 1

        target_info = self._verify_target_identity(target)
        argv = self.PROBE_ARGV
        t0 = time.time()
        try:
            proc = self._runner(argv, self.TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise D1LabProbeError(
                f"probe exceeded {self.TIMEOUT_SECONDS}s bound: {exc}"
            ) from None
        duration_ms = (time.time() - t0) * 1000.0

        stdout = (proc.stdout or "")[: self.MAX_OUTPUT_BYTES]
        stderr = (proc.stderr or "")[: self.MAX_OUTPUT_BYTES]
        if proc.returncode != 0:
            # Truthful failure: never represent a failed tool run as success.
            raise D1LabProbeError(
                f"nmap probe failed rc={proc.returncode}: {stderr.strip()[:200]}"
            )

        relpath, sha256, size = self._store_artifact(stdout)
        output = {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": round(duration_ms, 2),
            "probe_argv": list(argv),
            "target_identity": target_info,
            "service_confirmed": "80/tcp open" in stdout,
            "artifacts": [relpath],
            "artifact_relpath": relpath,
            "artifact_sha256": sha256,
            "artifact_size_bytes": size,
        }
        return CapabilityResult(
            capability="exec.d1_lab_probe",
            target=target,
            output=output,
            receipt_summary=(
                f"D1 bounded nmap service probe of lab identity '{target}' "
                f"(rc=0, service_confirmed={output['service_confirmed']})"
            ),
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def _verify_target_identity(self, target: str) -> dict:
        """Resolve the lab identity to the real compose containers, fail-closed.

        Verifies: the target container exists and is running under the
        expected image; the probe container exists and is running; both
        share at least one docker network (so the probe's DNS name and
        route are real). Returns the identity provenance recorded on the
        artifact/evidence.
        """
        tgt = self._inspector(target)
        probe = self._inspector(self.PROBE_CONTAINER)

        def _running(info: dict, name: str) -> None:
            state = (info.get("State") or {}).get("Running")
            if state is not True:
                raise D1LabProbeError(
                    f"lab container {name} is not running (identity check fail-closed)"
                )

        _running(tgt, target)
        _running(probe, self.PROBE_CONTAINER)

        image = (tgt.get("Config") or {}).get("Image", "")
        if not image.startswith(self.TARGET_IMAGE_PREFIX):
            raise D1LabProbeError(
                f"target container image mismatch: {image!r} does not start with "
                f"{self.TARGET_IMAGE_PREFIX!r} (identity check fail-closed)"
            )

        tgt_nets = set((tgt.get("NetworkSettings") or {}).get("Networks") or {})
        probe_nets = set((probe.get("NetworkSettings") or {}).get("Networks") or {})
        shared = sorted(tgt_nets & probe_nets)
        if not shared:
            raise D1LabProbeError(
                "target and probe containers share no docker network "
                "(identity check fail-closed)"
            )
        ip = ""
        for net in shared:
            ip = (((tgt.get("NetworkSettings") or {}).get("Networks") or {})
                  .get(net, {}) or {}).get("IPAddress", "")
            if ip:
                break
        return {
            "identity": target,
            "container_image": image,
            "probe_container": self.PROBE_CONTAINER,
            "shared_networks": shared,
            "target_ip": ip,
            "verified_at": time.time(),
        }

    def _store_artifact(self, stdout: str) -> tuple:
        """Persist the raw tool output as an artifact; return (relpath, sha256, size)."""
        data = stdout.encode("utf-8")
        sha256 = hashlib.sha256(data).hexdigest()
        relpath = f"artifacts/d1_lab_probe_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{uuid.uuid4().hex[:8]}.txt"
        if self._artifacts_dir is None:
            raise D1LabProbeError(
                "no artifacts_dir bound: refusing to produce unverifiable output"
            )
        path = self._artifacts_dir / Path(relpath).name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return relpath, sha256, len(data)
