import asyncio
import httpx
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from typing import Optional

KALI_TOOLS_URL = os.getenv("KALI_TOOLS_URL", "http://kali-tools:3800")
FORCE_LOCAL = os.getenv("RAPHAEL_FORCE_LOCAL", "0") == "1"
from orchestrator.hardening.timeout_guard import get_timeout_guard, TimeoutError as GuardTimeout
from orchestrator.hardening.rate_limiter import get_limiter

logger = logging.getLogger(__name__)


# ── P1 SEAM (per C6, AM-4) — WELDED in WELD-SUB10 ────────────────────────────
# Path ID: SUB-10 (canonical P0 inventory: evidence/phases/P0/02_execution_inventory/subprocess_sites.md)
# The local subprocess bypass (KaliBypassNotAuthorized, _BYPASS_AUTHORIZED,
# authorize_local_bypass, _run_local) has been removed entirely.
# All execution must go through the broker-gated capability (CapabilityBroker.propose_action →
# exec/safe_capability.py). Local subprocess fallback is no longer reachable.
# Weld ticket: Weld-SUB10 (P3).

class KaliToolsClient:
    def __init__(self, base_url: str = KALI_TOOLS_URL):
        self.base_url = base_url
        self._guard = get_timeout_guard()
        self._limiter = get_limiter()
        self._use_local = FORCE_LOCAL
        self._remote_available = None

    async def _check_remote(self) -> bool:
        if self._remote_available is not None:
            return self._remote_available
        if self._use_local:
            self._remote_available = False
            return False
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                resp = await c.get(f"{self.base_url}/health", timeout=3)
                self._remote_available = resp.status_code == 200
                return self._remote_available
        except Exception:
            self._remote_available = False
            logger.info("  kali-tools remote server unavailable, using local execution")
            return False

    async def run(self, tool: str, args: str = "", timeout: int = 300) -> dict:
        key = f"{tool}:{args[:60]}"
        await self._limiter.wait(key)

        use_remote = not self._use_local and await self._check_remote()

        if use_remote:
            try:
                actual_timeout = self._guard.get_timeout(f"kali_{tool}")
                effective_timeout = min(timeout, actual_timeout)
                async def _call():
                    async with httpx.AsyncClient() as c:
                        resp = await c.post(
                            f"{self.base_url}/run",
                            params={"tool": tool, "args": args, "timeout": effective_timeout},
                            timeout=effective_timeout + 10,
                        )
                    return resp.json()
                return await self._guard.run(key, _call(), timeout=effective_timeout + 5)
            except (GuardTimeout, httpx.ConnectError, Exception) as e:
                logger.debug(f"Remote execution failed for {tool}, no local fallback (WELD-SUB10): {e}")
                raise RuntimeError(
                    "kali_tools_client._run_local is removed in WELD-SUB10. "
                    "All execution must go through the broker-gated capability."
                )

        # SUB-10 welded: local subprocess fallback removed
        raise RuntimeError(
            "kali_tools_client._run_local is removed in WELD-SUB10. "
            "All execution must go through the broker-gated capability."
        )

    async def run_impacket(self, script: str, args: str = "", timeout: int = 120) -> dict:
        result = await self.run(f"impacket-{script}", args, timeout=timeout)
        if result.get("returncode") is not None and result.get("returncode") != -127:
            return result
        if result.get("error") and "not found" in result.get("error", "").lower():
            raise RuntimeError("Not implemented")
        return await self.run("python3", f"-m impacket.examples.{script} {args}", timeout=timeout)

    async def run_hashcat(self, args: str = "", timeout: int = 600) -> dict:
        return await self.run("hashcat", args, timeout=timeout)

    async def run_nuclei(self, target: str, templates: list = None,
                         severity: str = None, rate_limit: int = 50) -> dict:
        args = f"-u {target} -json -silent -rate-limit {rate_limit}"
        if templates:
            for t in templates:
                args += f" -t {t}"
        if severity:
            args += f" -severity {severity}"
        return await self.run("nuclei", args, timeout=600)

    async def run_sqlmap(self, url: str, args: str = "", timeout: int = 120) -> dict:
        return await self.run("sqlmap", f"-u {url} --batch --random-agent {args}", timeout=timeout)

    async def tools_list(self) -> list:
        try:
            async with httpx.AsyncClient() as c:
                resp = await c.get(f"{self.base_url}/tools", timeout=5)
                return resp.json().get("tools", [])
        except Exception:
            return ["local_mode"]

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient() as c:
                resp = await c.get(f"{self.base_url}/health", timeout=5)
                return resp.json()
        except Exception as e:
            return {"status": "local_fallback", "detail": str(e)}

    async def tools_available_locally(self, tool_list: list[str]) -> dict:
        result = {}
        for tool in tool_list:
            result[tool] = shutil.which(tool) is not None
        return result

    async def run_on_target(self, host: str, command: str,
                            user: str = "root", password: str = None,
                            timeout: int = 30) -> dict:
        quoted_cmd = command.replace("'", "'\\''")
        ssh_args = (
            f"-p {shlex.quote(password)} "
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
            f"{shlex.quote(user)}@{shlex.quote(host)} "
            f"'{quoted_cmd}'"
        ) if password else (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
            f"-i ~/.ssh/id_rsa "
            f"{shlex.quote(user)}@{shlex.quote(host)} "
            f"'{quoted_cmd}'"
        )
        tool = "sshpass" if password else "ssh"
        return await self.run(tool, ssh_args, timeout=timeout)


kali = KaliToolsClient()
