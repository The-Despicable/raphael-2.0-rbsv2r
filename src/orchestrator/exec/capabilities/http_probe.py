"""http_probe.py — the D2 Action-B capability: fixed in-container HTTP GET (M3, 2026-10-05).

Authorizes exactly one operation per the operator-approved D2 scope: a
**GET** of the fixed constant ``http://dvwa/`` executed **inside the
kali-tools lab container** (so the target resolves through the lab's Docker
network — inside that context ``127.0.0.1`` would mean the probe container
itself and is never used).

Contract (D2 task order §2, §3):
- HTTP only, GET only, no HTTPS/host/port/path/query/method substitution —
  the URL is a fixed constant bound to the verified lab identity;
- redirects are NEVER followed (curl is invoked without ``-L`` and with
  ``--max-redirs 0``; a 3xx is recorded as an observation, never permission);
- no request body, no caller-supplied headers;
- bounded collection: ``--max-filesize`` aborts an oversized transfer during
  download, the runner timeout bounds wall clock, and a defensive post-cap
  truncates before any artifact is written;
- the raw response body is captured as an artifact (relpath + sha256);
- HTTP error statuses (3xx/4xx/5xx) are honest observations recorded on a
  SUCCEEDED execution receipt — a transport failure (refused connection,
  timeout, curl error) raises, producing a truthful FAILED receipt;
- identity is re-verified against the live compose containers before any
  request (running + image prefix + shared network), mirroring the D1 probe;
- CONV-3 gating: requires a bound CapabilityBroker and a prior
  ``record_authorization(target)`` from the canonical PEP stage.
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


class LabHttpProbeError(RuntimeError):
    """Raised when the bounded HTTP probe cannot be executed truthfully."""


class LabHttpProbeCapability:
    """D2 Action B: governed fixed HTTP GET of the lab DVWA service."""

    LAB_TARGET = "dvwa"
    PROBE_CONTAINER = "kali-tools"
    TARGET_IMAGE_PREFIX = "vulnerables/web-dvwa"
    URL = "http://dvwa/"
    RUNNER_TIMEOUT_SECONDS = 90
    CURL_MAX_TIME_SECONDS = 60
    MAX_ARTIFACT_BYTES = 65536

    # Fully fixed argv. No -L (redirects are never followed); --max-redirs 0
    # states the policy explicitly; --max-filesize enforces the artifact cap
    # during collection; -w appends machine-readable metadata after the body.
    HTTP_ARGV = (
        "docker", "exec", PROBE_CONTAINER, "curl",
        "--max-redirs", "0",
        "--max-time", str(CURL_MAX_TIME_SECONDS),
        "--max-filesize", str(MAX_ARTIFACT_BYTES),
        "-s", "-S", "-o", "-",
        "-w", "\n%{http_code}|%{content_type}|%{size_download}|%{time_total}|%{redirect_url}",
        URL,
    )

    def __init__(self,
                 broker: Optional[Any] = None,
                 artifacts_dir: Optional[Path] = None,
                 runner: Optional[Callable[..., Any]] = None,
                 inspector: Optional[Callable[[str], dict]] = None):
        self._broker = broker
        self._artifacts_dir = Path(artifacts_dir) if artifacts_dir else None
        self._runner = runner if runner is not None else self._subprocess_runner
        self._inspector = inspector if inspector is not None else self._docker_inspect
        self._broker_authorized_targets: set = set()
        self.invocation_count = 0

    @property
    def artifact_root(self) -> Optional[Path]:
        """Bound artifact directory (or None). M3/D2 remediation: the
        objective evaluator verifies persisted artifacts against these
        ACTUAL bytes through exec/artifact_verify."""
        return self._artifacts_dir

    # ── CONV-3 gating surface ────────────────────────────────────────────

    def gate_with_broker(self, broker) -> None:
        self._broker = broker

    def record_authorization(self, target: str) -> None:
        self._broker_authorized_targets.add(target)

    @property
    def broker(self):
        return self._broker

    # ── primitives (INV-1: live in exec/) ────────────────────────────────

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
            raise LabHttpProbeError(
                f"docker inspect {container} failed rc={proc.returncode}: "
                f"{proc.stderr.strip()[:200]}"
            )
        try:
            return json.loads(proc.stdout)[0]
        except (ValueError, IndexError) as exc:
            raise LabHttpProbeError(
                f"docker inspect {container}: unparseable output: {exc}"
            ) from None

    # ── the capability ───────────────────────────────────────────────────

    def inspect(self, target: str) -> CapabilityResult:
        """Run the one bounded HTTP probe. Gated by the broker (CONV-3)."""
        if self._broker is None:
            raise CapabilityNotGatedError(
                "LabHttpProbeCapability requires a bound CapabilityBroker "
                "(CONV-3 constructor gating)"
            )
        if target not in self._broker_authorized_targets:
            raise CapabilityNotGatedError(
                f"Target '{target}' not authorized by broker. The canonical "
                "PEP stage must call record_authorization(target) after an "
                "AUTHORIZED broker decision."
            )
        if target != self.LAB_TARGET:
            raise LabHttpProbeError(
                f"HTTP probe capability refuses non-lab target {target!r} "
                f"(authorized identity: {self.LAB_TARGET!r})"
            )
        self.invocation_count += 1

        target_info = self._verify_target_identity(target)
        argv = self.HTTP_ARGV
        t0 = time.time()
        try:
            proc = self._runner(argv, self.RUNNER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise LabHttpProbeError(
                f"HTTP probe exceeded {self.RUNNER_TIMEOUT_SECONDS}s bound: {exc}"
            ) from None
        duration_ms = (time.time() - t0) * 1000.0

        stdout = (proc.stdout or "")
        stderr = (proc.stderr or "")[:2048]
        if proc.returncode == 63:
            # curl --max-filesize exceeded during collection: bounded abort.
            raise LabHttpProbeError(
                "HTTP response exceeded the 64 KiB artifact limit during "
                "collection (bounded abort; nothing fabricated)"
            )
        if proc.returncode == 28:
            raise LabHttpProbeError("HTTP probe timed out (curl exit 28)")
        if proc.returncode != 0:
            raise LabHttpProbeError(
                f"HTTP probe failed rc={proc.returncode}: {stderr.strip()[:200]}"
            )

        # The -w metadata is the final line of stdout (robust to any
        # trailing newlines curl may or may not emit around the body).
        cleaned = stdout.rstrip("\n")
        body, _, meta_line = cleaned.rpartition("\n")
        if not meta_line:
            meta_line, body = cleaned, ""
        parts = (meta_line.strip().split("|") + ["", "", "", "", ""])[:5]
        http_code, content_type, size_download, time_total, redirect_url = parts
        body = body[: self.MAX_ARTIFACT_BYTES]
        relpath, sha256, size = self._store_artifact(body)

        output = {
            "returncode": proc.returncode,
            "url": self.URL,
            "http_status": int(http_code) if http_code.isdigit() else 0,
            "content_type": content_type,
            "size_download": int(size_download) if size_download.isdigit() else 0,
            "time_total_seconds": time_total,
            "redirect_url": redirect_url,
            "redirect_followed": False,
            "duration_ms": round(duration_ms, 2),
            "probe_argv": list(argv),
            "target_identity": target_info,
            "artifacts": [relpath],
            "artifact_relpath": relpath,
            "artifact_sha256": sha256,
            "artifact_size_bytes": size,
        }
        return CapabilityResult(
            capability="exec.http_probe",
            target=target,
            output=output,
            receipt_summary=(
                f"D2 bounded HTTP GET {self.URL} from {self.PROBE_CONTAINER} "
                f"(status {output['http_status']}, redirect_url={redirect_url or 'none'})"
            ),
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def _verify_target_identity(self, target: str) -> dict:
        """Identity check mirroring the D1 probe: running + image + shared net."""
        tgt = self._inspector(target)
        probe = self._inspector(self.PROBE_CONTAINER)

        def _running(info: dict, name: str) -> None:
            if (info.get("State") or {}).get("Running") is not True:
                raise LabHttpProbeError(
                    f"lab container {name} is not running (identity check fail-closed)"
                )

        _running(tgt, target)
        _running(probe, self.PROBE_CONTAINER)

        image = (tgt.get("Config") or {}).get("Image", "")
        if not image.startswith(self.TARGET_IMAGE_PREFIX):
            raise LabHttpProbeError(
                f"target container image mismatch: {image!r} does not start with "
                f"{self.TARGET_IMAGE_PREFIX!r} (identity check fail-closed)"
            )

        tgt_nets = set((tgt.get("NetworkSettings") or {}).get("Networks") or {})
        probe_nets = set((probe.get("NetworkSettings") or {}).get("Networks") or {})
        shared = sorted(tgt_nets & probe_nets)
        if not shared:
            raise LabHttpProbeError(
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

    def _store_artifact(self, body: str) -> tuple:
        data = body.encode("utf-8")[: self.MAX_ARTIFACT_BYTES]
        sha256 = hashlib.sha256(data).hexdigest()
        relpath = f"artifacts/http_probe_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{uuid.uuid4().hex[:8]}.txt"
        if self._artifacts_dir is None:
            raise LabHttpProbeError(
                "no artifacts_dir bound: refusing to produce unverifiable output"
            )
        path = self._artifacts_dir / Path(relpath).name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return relpath, sha256, len(data)
