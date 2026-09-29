#!/usr/bin/env python3
import os, sys, signal, time, logging, uuid, threading
import subprocess
from datetime import datetime
from typing import Optional, Dict

from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# AM-4 W-14 (R3.0-P23) weld dependency: broker mediation lives in the
# canonical tree. Hard import (no fallback): the service fails closed at
# startup when the canonical tree is absent.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized

sys.path.insert(0, os.getenv("RAPHAEL_PATH", str(Path.home() / ".raphael")))
try:
    from orchestrator.proxy_guard import ProxyGuard
    HAS_PROXY_GUARD = True
except ImportError:
    HAS_PROXY_GUARD = False

ATTACK_METHODS = {
    # Layer 7 — HTTP flood methods
    "GET": "HTTP GET flood",
    "POST": "HTTP POST flood",
    "OVH": "OVH bypass",
    "RHEX": "Random HEX payload",
    "STOMP": "STOMP protocol",
    "STRESS": "Stress testing",
    "DGB": "DGB attack",
    "HEART": "Heartbleed attack",
    "NULL": "Null user-agent",
    "TOR": "Tor exit node flood",
    "BYPASS": "Cloudflare bypass",
    "HEAD": "HTTP HEAD flood",
    "PUT": "HTTP PUT flood",
    "PATCH": "HTTP PATCH flood",
    "DELETE": "HTTP DELETE flood",
    "OPTIONS": "HTTP OPTIONS flood",
    "CONNECT": "HTTP CONNECT flood",
    "TRACE": "HTTP TRACE flood",
    "PPS": "Packets per second",
    "EVEN": "Even method",
    "GSB": "Google Shield bypass",
    "DYN": "Dynamic method",
    "SLOW": "Slowloris",
    "SLOWBODY": "Slow body read",
    "SLOWREAD": "Slow read attack",
    "BOTNET": "Botnet simulation",
    "HIT": "Hit method",
    "COOKIE": "Cookie flood",
    "RANDOM": "Random method rotation",
    "DOWNLOAD": "Download flood",
    "RANGE": "Range request flood",
    "THREAD": "Thread flood",
    "HTTPSPOOF": "HTTP spoofing",
    "CFBYPASS": "Cloudflare bypass v2",
    "CFBUAM": "Cloudflare UAM bypass",
    "BROWSER": "Browser emulation",
    "API": "API endpoint flood",
    # Layer 4 — Network flood methods
    "TCP": "TCP flood",
    "UDP": "UDP flood",
    "SYN": "SYN flood",
    "ICMP": "ICMP flood",
    "IGMP": "IGMP flood",
    "ARP": "ARP flood",
    "RST": "RST flood",
    "XMAS": "XMAS scan flood",
    "FIN": "FIN flood",
    "ACK": "ACK flood",
    "NUL": "NULL scan flood",
    "MAIMP": "MAIMP flood",
    "POD": "Ping of death",
    "SMURF": "Smurf attack",
    "FRAGGLE": "Fraggle attack",
    "LAND": "LAND attack",
    "TARSPRAY": "Tar spray",
    "WIFIHOP": "WiFi hop",
    "BLUEBORNE": "BlueBorne attack",
}

# Config
MHDPATH = os.getenv("MHDPATH", "/app/mhdos.py")
TOR_PROXY = os.getenv("TOR_PROXY", "socks5h://127.0.0.1:9050")
TOR_CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
MHDDOS_PYTHON = os.getenv("MHDDOS_PYTHON", "python3")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "3300"))

attacks: Dict[str, dict] = {}
_attacks_lock = threading.Lock()

app = FastAPI(title="MHDDoS Service", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="[MHDDoS] %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("mhddos")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.3f}s)")
    return response


class AttackRequest(BaseModel):
    target: str
    method: str
    threads: int = 1000
    duration: int = 60
    proxy: bool = True


class StopRequest(BaseModel):
    target: Optional[str] = None
    pid: Optional[int] = None


@app.get("/")
async def list_methods():
    return {"methods": ATTACK_METHODS, "count": len(ATTACK_METHODS)}


@app.post("/attack")
async def launch_attack(req: AttackRequest):
    # AM-4 W-14 (R3.0-P23) WELDED under Scope v0: unauthenticated DDoS
    # launch is deleted as an executable path. Fail-closed 403 unless the
    # canonical Broker AUTHORIZEs.
    try:
        enforce_broker_mediation(
            target=req.target,
            action_type="ddos_attack",
            capability="mhddos",
            method="launch_attack",
            impact_estimate=10.0,
            argv=(req.target, req.method),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    method = req.method.upper()
    if method not in ATTACK_METHODS:
        raise HTTPException(400, f"Unknown method '{method}'. Available: {', '.join(ATTACK_METHODS)}")

    attack_id = uuid.uuid4().hex[:12]
    proxy_arg = TOR_PROXY if req.proxy else "off"

    def run_real():
        # AM-4-R2: the legacy real-execution branch (subprocess.Popen of the
        # mhddos binary) is DELETED. This closure is retained only so the
        # dispatch below documents the removed path; it must never launch.
        raise WeldNotAuthorized(
            "AM-4 W-14 R3.0-P23: real-attack execution branch deleted; "
            "all execution routes through the broker-gated capability."
        )

    def run_simulated():
        logger.info(f"[SIMULATED] Attacking {req.target} with {method} for {req.duration}s")
        deadline = time.time() + req.duration
        while time.time() < deadline:
            time.sleep(min(5, deadline - time.time()))
        with _attacks_lock:
            if attack_id in attacks:
                attacks[attack_id]["status"] = "completed"

    start_msg = f"Attack launched: {method} → {req.target} for {req.duration}s (threads={req.threads}, proxy={req.proxy})"

    with _attacks_lock:
        attacks[attack_id] = {
            "id": attack_id,
            "target": req.target,
            "method": method,
            "threads": req.threads,
            "duration": req.duration,
            "proxy": req.proxy,
            "pid": None,
            "started_at": datetime.utcnow().isoformat(),
            "status": "running",
        }

    if os.path.exists(MHDPATH):
        t = threading.Thread(target=run_real, daemon=True)
    else:
        logger.warning(f"{MHDPATH} not found — using simulated mode")
        t = threading.Thread(target=run_simulated, daemon=True)

    t.start()

    return {
        "status": "launched",
        "attack_id": attack_id,
        "pid": attacks[attack_id]["pid"],
        "message": start_msg,
    }


@app.post("/stop")
async def stop_attack(req: StopRequest):
    stopped = []
    with _attacks_lock:
        for aid, info in list(attacks.items()):
            if info["status"] != "running":
                continue
            if req.target and req.target in info["target"]:
                pass
            elif req.pid and info.get("pid") == req.pid:
                pass
            elif req.target is None and req.pid is None:
                pass
            else:
                continue
            pid = info.get("pid")
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            info["status"] = "stopped"
            stopped.append(aid)

    if not stopped:
        raise HTTPException(404, "No running attacks matched")

    return {"status": "stopped", "attacks_stopped": stopped}


@app.get("/status")
async def get_status():
    active = {}
    with _attacks_lock:
        for aid, info in attacks.items():
            if info["status"] == "running":
                active[aid] = info
    return {
        "running_count": len(active),
        "attacks": active,
    }


@app.post("/proxy/rotate")
async def rotate_proxy():
    # AM-4-R2 W-14 (R3.0-P23): the unauthenticated Tor-control route (both the
    # ProxyGuard branch and the raw-socket fallback, which perform governed
    # network effects) is deleted as an executable path. Fail-closed 403
    # unless the canonical Broker AUTHORIZEs.
    try:
        enforce_broker_mediation(
            target="tor-control",
            action_type="proxy_rotate",
            capability="mhddos",
            method="rotate_proxy",
            impact_estimate=7.0,
            argv=("rotate",),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if HAS_PROXY_GUARD:
        try:
            pg = ProxyGuard()
            circuit = pg.new_circuit()
            return {"status": "rotated", "circuit_id": circuit}
        except Exception as e:
            logger.warning(f"ProxyGuard rotation failed: {e}")
            raise HTTPException(502, f"Tor rotation failed: {e}")

    # AM-4-R2: the legacy raw-socket Tor-control fallback branch
    # (socket.socket/connect/sendall) is DELETED. No unauthenticated or
    # fallback path to the Tor control port remains on this route.


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
