"""KaliBridge — HTTP client for the Kali tools execution API at localhost:3800."""
import asyncio
import json
import logging
import os
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger("raphael.kali_bridge")


class KaliBridge:
    """
    Wraps HTTP calls to the orchestrator's Kali tools bridge and raw /run endpoint.
    Falls back to subprocess if the API is unavailable.
    """

    def __init__(self, api_url: str = "http://localhost:3800"):
        self._api_url = api_url
        self._available: Optional[bool] = None
        self._session = None

    async def _ensure_session(self):
        if self._session is None or self._session.is_closed:
            import httpx
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(600.0),
                limits=httpx.Limits(max_keepalive_connections=5),
            )

    async def check_health(self) -> bool:
        """Check if the API is reachable."""
        try:
            await self._ensure_session()
            resp = await self._session.get(f"{self._api_url}/health", timeout=5)
            if resp.status_code == 200:
                self._available = True
                return True
        except Exception:
            pass
        self._available = False
        return False

    async def run(self, tool: str, args: str, timeout: int = 120) -> dict:
        """
        Run a tool via the Kali bridge.
        Tries /run endpoint first, falls back to subprocess.
        """
        await self._ensure_session()

        # Try API first
        if self._available is None:
            self._available = await self.check_health()

        if self._available:
            try:
                result = await self._api_run(tool, args, timeout)
                if result and result.get("returncode") is not None:
                    if result.get("returncode") >= 0:
                        return result
                    if result.get("error"):
                        logger.debug(f"API returned error ({result['error']}), falling back to subprocess")
                        self._available = False
            except Exception as e:
                logger.debug(f"Kali bridge API call failed: {e}, falling back to subprocess")
                self._available = False

        # SUB-14 welded: subprocess fallback removed
        raise RuntimeError(
            "Executor._subprocess_fallback() is removed in WELD-SUB14. "
            "All execution must go through the broker-gated capability."
        )