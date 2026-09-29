import asyncio
import base64
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .cloakbrowser import launch_async
from pydantic import BaseModel, Field

# AM-4 W-14 (R3.0-P23) weld dependency: broker mediation lives in the
# canonical tree. Hard import (no fallback): the service fails closed at
# startup when the canonical tree is absent.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized


def _weld_gate(target: str, method: str, argv: tuple = ()) -> None:
    """AM-4 W-14 (R3.0-P23) shared entry gate: fail-closed 403 unless AUTHORIZED."""
    try:
        enforce_broker_mediation(
            target=target,
            action_type="cloak_execute",
            capability="cloak",
            method=method,
            impact_estimate=7.0,
            argv=argv,
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
try:
    from stem import Signal
    from stem.control import Controller
    TOR_AVAILABLE = True
except ImportError:
    TOR_AVAILABLE = False

TOR_PROXY = os.environ.get("TOR_PROXY", "socks5h://tor-proxy:9050")
TOR_CONTROL = os.environ.get("TOR_CONTROL", "tor-proxy:9051")
TOR_PASSWORD = os.environ.get("TOR_PASSWORD", "")
PORT = int(os.environ.get("PORT", 3401))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1680, "height": 1050},
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cloak-service")

browser = None


class BrowseRequest(BaseModel):
    url: str
    wait_selector: Optional[str] = None
    timeout: int = 30000
    viewport: Optional[dict] = None


class BrowseResponse(BaseModel):
    url: str
    title: str
    html: str
    screenshot: str
    cookies: list
    headers: dict
    timing: float


class ScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True
    viewport: Optional[dict] = None


class ScreenshotResponse(BaseModel):
    screenshot: str
    url: str


class InteractRequest(BaseModel):
    url: str
    script: str
    wait_for: Optional[str] = None


class InteractResponse(BaseModel):
    result: Any
    url: str


class IdentityResponse(BaseModel):
    status: str
    new_ip: Optional[str] = None
    old_ip: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    tor_ip: Optional[str] = None
    browser_available: bool


class WaitStrategy:
    @staticmethod
    async def wait_for_navigation(page, timeout=30000):
        await page.wait_for_load_state("networkidle", timeout=timeout)

    @staticmethod
    async def wait_for_selector(page, selector, timeout=30000):
        await page.wait_for_selector(selector, timeout=timeout)

    @staticmethod
    async def wait_for_timeout(page, ms):
        await page.wait_for_timeout(ms)

    @staticmethod
    async def wait_for_network_idle(page, timeout=30000):
        await page.wait_for_load_state("networkidle", timeout=timeout)

    @staticmethod
    async def wait_for_function(page, js_expression, timeout=30000):
        await page.wait_for_function(js_expression, timeout=timeout)


async def apply_wait_strategy(page, req):
    if req.get("wait_selector"):
        await WaitStrategy.wait_for_selector(
            page, req["wait_selector"], req.get("timeout", 30000)
        )
    else:
        await WaitStrategy.wait_for_navigation(page, req.get("timeout", 30000))
    if req.get("wait_for"):
        await WaitStrategy.wait_for_function(
            page, req["wait_for"], req.get("timeout", 30000)
        )


async def get_tor_ip():
    # AM-4-R2 W-14 (R3.0-P23) internal-helper defense: direct httpx egress
    # is deleted as an executable path. Fail-closed unless AUTHORIZED.
    from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized
    try:
        enforce_broker_mediation(
            target="tor-egress",
            action_type="cloak_execute",
            capability="cloak",
            method="get_tor_ip",
            impact_estimate=7.0,
            argv=("get_tor_ip",),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    # AM-4-R2: legacy direct-egress branches (httpbin/ipify httpx calls)
    # DELETED. No fallback path to external IP oracles remains.
    raise WeldNotAuthorized(
        "AM-4 W-14 R3.0-P23: Tor-egress branch deleted; "
        "all execution routes through the broker-gated capability."
    )


def rotate_tor_identity():
    # AM-4-R2 W-14 (R3.0-P23) internal-helper defense: Tor control-port
    # signaling is deleted as an executable path. Fail-closed unless AUTHORIZED.
    from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized
    try:
        enforce_broker_mediation(
            target="tor-control",
            action_type="cloak_execute",
            capability="cloak",
            method="rotate_tor_identity",
            impact_estimate=7.0,
            argv=("rotate_tor_identity",),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    # AM-4-R2: legacy stem Controller signaling branch DELETED. No path to
    # the Tor control port remains.
    raise WeldNotAuthorized(
        "AM-4 W-14 R3.0-P23: Tor-control branch deleted; "
        "all execution routes through the broker-gated capability."
    )


@asynccontextmanager
async def get_browser_page(viewport=None):
    global browser
    if browser is None:
        raise HTTPException(status_code=503, detail="Browser not available")
    ua = random.choice(USER_AGENTS)
    vp = viewport or random.choice(VIEWPORTS)
    context = await browser.new_context(
        user_agent=ua,
        viewport=vp,
        proxy={"server": TOR_PROXY},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    try:
        yield page
    finally:
        await page.close()
        await context.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global browser
    logger.info("Starting cloak-service...")
    try:
        browser = await launch_async(
            headless=True,
            args=["--no-sandbox"],
        )
        logger.info("CloakBrowser launched successfully")
    except Exception as e:
        logger.error("Failed to launch CloakBrowser: %s", e)
        browser = None
    yield
    logger.info("Shutting down cloak-service...")
    if browser:
        await browser.close()


app = FastAPI(title="Cloak Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(
        "%s %s -> %s (%.3fs)", request.method, request.url.path, response.status_code, elapsed
    )
    return response


@app.post("/browse", response_model=BrowseResponse)
async def browse(req: BrowseRequest):
    _weld_gate(req.url, "browse", (req.url,))
    start = time.time()
    async with get_browser_page(req.viewport) as page:
        try:
            resp = await page.goto(req.url, wait_until="commit", timeout=req.timeout)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Navigation failed: {e}")
        await apply_wait_strategy(page, req.model_dump())
        title = await page.title()
        html = await page.content()
        screenshot_b64 = base64.b64encode(
            await page.screenshot(full_page=True, type="png")
        ).decode()
        cookies = await page.context.cookies()
        headers = dict(resp.headers) if resp else {}
        timing = time.time() - start
        return BrowseResponse(
            url=page.url,
            title=title,
            html=html,
            screenshot=screenshot_b64,
            cookies=cookies,
            headers=headers,
            timing=timing,
        )


@app.post("/screenshot", response_model=ScreenshotResponse)
async def screenshot(req: ScreenshotRequest):
    _weld_gate(req.url, "screenshot", (req.url,))
    async with get_browser_page(req.viewport) as page:
        try:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Navigation failed: {e}")
        img_b64 = base64.b64encode(
            await page.screenshot(full_page=req.full_page, type="png")
        ).decode()
        return ScreenshotResponse(screenshot=img_b64, url=page.url)


@app.post("/interact", response_model=InteractResponse)
async def interact(req: InteractRequest):
    _weld_gate(req.url, "interact", (req.url,))
    async with get_browser_page() as page:
        try:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Navigation failed: {e}")
        if req.wait_for:
            await WaitStrategy.wait_for_function(page, req.wait_for)
        result = await page.evaluate(req.script)
        return InteractResponse(result=result, url=page.url)


@app.get("/identities", response_model=IdentityResponse)
async def identities():
    _weld_gate("tor-control", "identities", ("rotate",))
    old_ip = await get_tor_ip()
    success = rotate_tor_identity()
    if not success:
        raise HTTPException(status_code=502, detail="Tor identity rotation failed")
    await asyncio.sleep(2)
    new_ip = await get_tor_ip()
    return IdentityResponse(
        status="rotated" if new_ip != old_ip else "unchanged",
        new_ip=new_ip,
        old_ip=old_ip,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    # AM-4-R2 W-14 (R3.0-P23): the legacy branch that dialed Tor on every
    # unauthenticated health scrape is DELETED. Liveness-only health: no
    # governed effect remains on this route, so no gate is required.
    browser_ok = browser is not None
    return HealthResponse(
        status="ok" if browser_ok else "degraded",
        tor_ip=None,
        browser_available=browser_ok,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
