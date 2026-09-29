import os
import subprocess
import shlex
import shutil
import sys
from fastapi import FastAPI, Query, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized

app = FastAPI()

TOOLS_CACHE = {}

@app.on_event("startup")
async def cache_tools():
    paths = os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
    for d in paths.split(":"):
        if os.path.isdir(d):
            for f in os.listdir(d):
                fp = os.path.join(d, f)
                if os.path.isfile(fp) and os.access(fp, os.X_OK):
                    TOOLS_CACHE[f] = fp
    TOOLS_CACHE["nuclei"] = shutil.which("nuclei")

@app.post("/run")
def run_tool(tool: str = Query(...), args: str = "", timeout: int = 300):
    # AM-4 W-09 (R3.0-P12) WELDED under Scope v0: the unauthenticated /run
    # branch is deleted as an executable path. Execution requires a Broker
    # AUTHORIZED decision (fail-closed 403 otherwise).
    try:
        enforce_broker_mediation(
            target="kali-tools",
            action_type="tool_execute",
            capability="kali_tools",
            method="run_tool",
            impact_estimate=8.0,
            argv=(tool, args),
            path_id="R3.0-P12",
            weld_ticket="W-09",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    # AM-4-R2: legacy subprocess execution body DELETED (was
    # shlex.split + subprocess.run). No execution path remains past the gate.
    raise WeldNotAuthorized(
        "AM-4 W-09 R3.0-P12: /run execution branch deleted; "
        "all execution routes through the broker-gated capability."
    )

@app.get("/tools")
def list_tools():
    return {"tools": sorted(TOOLS_CACHE.keys()), "total": len(TOOLS_CACHE)}

@app.get("/health")
def health():
    return {"status": "ok", "tools": len(TOOLS_CACHE)}
