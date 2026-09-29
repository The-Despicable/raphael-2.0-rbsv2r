import asyncio, json, sys, os, logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, "/app")

# AM-4 W-14 (R3.0-P23) weld dependency: broker mediation lives in the
# canonical tree. Hard import (no fallback): the service fails closed at
# startup when the canonical tree is absent.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized

from sword.pipeline import run_sword
from sword.report import SwordReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SWORD-API] %(levelname)s %(message)s")
log = logging.getLogger("sword-api")

app = FastAPI(title="Sword API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SwordRequest(BaseModel):
    target: str
    phases: Optional[list] = None
    config: Optional[dict] = None

class SwordStatus(BaseModel):
    task_id: str
    target: str
    status: str

_tasks = {}

@app.get("/")
async def root():
    return {"service": "Sword Offensive Pipeline", "version": "2.0", "phases": ["recon", "scan", "exploit", "postex", "exfil", "phish"]}

@app.post("/sword/run")
async def sword_run(req: SwordRequest):
    # AM-4 W-14 (R3.0-P23) WELDED under Scope v0: the sword pipeline entry
    # (phase_0 exec, phase_1 httpx, report writes, phase_4 tunnels) is deleted
    # as an unbrokered executable path (fail-closed 403).
    try:
        enforce_broker_mediation(
            target=req.target,
            action_type="sword_execute",
            capability="sword",
            method="sword_run",
            impact_estimate=9.0,
            argv=(req.target,),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    api_keys = {}
    for k in ["SHODAN_API_KEY", "CENSYS_API_KEY", "SPIDERFOOT_API_KEY"]:
        v = os.environ.get(k)
        if v:
            api_keys[k.lower().replace("_api_key", "")] = v
    try:
        result = await run_sword(req.target, api_keys, req.config or {}, req.phases)
        report = SwordReport(result)
        paths = report.save()
        result["_report_files"] = paths
        return result
    except Exception as e:
        log.error("sword run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sword/health")
async def health():
    # AM-4-R2 W-14 (R3.0-P23): gated (see route matrix). NOTE (§2-deferred):
    # the `os.popen` status probe is RETAINED behind the gate — replacing it
    # with read-only `shutil.which` would delete this file's sole lexicon hit
    # and drop CENSUS row #48 (150→149), which the AM-4 task explicitly
    # forbids ("change the 150-file effect census"). The route reaches the
    # primitive ONLY through the canonical authorization path (fail-closed
    # 403 under current policy). Branch deletion here needs a Lead ruling on
    # census-stability precedence; recorded, not silent.
    from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized
    try:
        enforce_broker_mediation(
            target="sword-health",
            action_type="sword_execute",
            capability="sword",
            method="health",
            impact_estimate=3.0,
            argv=("health",),
            path_id="R3.0-P23",
            weld_ticket="W-14",
        )
    except WeldNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    tools = {}
    for name in ["nmap", "nuclei", "subfinder", "whatweb"]:
        p = os.popen(f"which {name} 2>/dev/null")
        tools[name] = bool(p.read().strip())
        p.close()
    return {"status": "ok", "tools": tools}

@app.post("/sword/report")
async def generate_report(data: dict):
    report = SwordReport(data)
    md = report.generate_markdown()
    html = report.generate_html()
    return {"markdown": md, "html": html}
