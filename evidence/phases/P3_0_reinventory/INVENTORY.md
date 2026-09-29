# P3.0 Re-inventory — Full Execution-Path Inventory (001R2 complete)

**HEAD:** `3b2e22db3d952622150d271c12c41d9ed21e81fd` (branch `weld-sub10-evidence`)
**Schema:** same as P0 §11.3: entry point → import/call chain → primitive site, with
per-route authorization.
**Lexicon (authoritative):** `src/orchestrator/exec/inv1_guard.py` `scan_source()` —
process + network + destructive-file effects (NOT process-only).
**Method:** read-only static trace (AST import graph over `src/**` incl. function-level
imports + parent-package `__init__` edges, BFS from live + service entries; source reads
for terminals). No legacy/offensive code executed, no network touched. Reproduced by
`probe_reinventory.py`. Census: `CENSUS.md` + `raw/effect_census.txt` (150 files).
**Scope:** every bridge dispatch method (40), every API route (27), every
PHASE_EXECUTORS phase (13), every effect file (150).

---

## 1. Entry-point census

| EP ID | Entry point | Type | Dispatches to |
|---|---|---|---|
| E-CANON | `orchestrator/runtime/loop.py` `RaphaelRuntime.run_episode` | canonical sequencer | 10 stages → broker → `exec/` PEP |
| E-CLI | `raphael/main.py` `main()` | production CLI | canonical Runtime (default); legacy `RaphaelOrganism` iff `RAPHAEL_USE_LEGACY=1` (→ E-CLI-LEGACY) |
| E-CLI-LEGACY | `raphael/main.py:387` `RAPHAEL_USE_LEGACY=1` branch | shipped runnable branch (NOT dead) | `RaphaelOrganism.run()` → planner → hypothesizer (network) / executor → kali_bridge (network attempt, fail-closed) / shutdown → hippocampus (file) |
| E-API | `orchestrator/api/main.py` `app` | deployed FastAPI | mounts agent/tools/tools_bridge/session routers (NOT ci); `GET /health`, `/api/personas` |
| E-TOOLS | `api/tools.py` 5 routes | deployed router | `chains/tool_registry` (4 exec) + list (pure) |
| E-BRIDGE-TOOLS | `api/tools_bridge.py` 2 routes | deployed router, **no auth** | httpx → kali-tools `/run` |
| E-AGENT | `api/agent.py` 4 routes | deployed router | `agents/engage` (2 exec) + 2 pure |
| E-SESSION | `api/session.py` 8 routes | deployed router | `session_manager` sqlite CRUD (no lexicon hit) |
| E-CI-DEF | `api/ci.py` 6 routes | defined, **never mounted** | handlers only (queue + autonomous + engage) |
| E-BRIDGE | `bridge/raphael_bridge.py` 40 methods | deployed IPC bridge, **no dispatch auth** | modes(6)/agents(4)/c2(5)/exploit(5)/kali(6)/harvester(3)/conductor+brain(5)/model+persona(3)/target+scope(3) |
| E-AUTO | `modes/autonomous.py` `handle()` | legacy orchestrator | 13 `PHASE_EXECUTORS`, spray, ad_kill_chain, harvester, profiler |
| E-KALI | `kali-tools/server.py` `POST /run` | deployed runner, **no auth** | `subprocess.run` |
| E-SVC-mhddos | `mhddos-service/main.py` (FastAPI+uvicorn) | standalone service | `/attack` → `Popen` / `/status` / `/stop` |
| E-SVC-recon | `recon-pipeline/main.py` (FastAPI `:3503`) | standalone service | `/recon/*` → subfinder exec + scanners |
| E-SVC-sword | `sword/api.py` (FastAPI) | standalone service | `/sword/run` → pipeline (all 6 phases) + report |
| E-SVC-agent | `agent/agent.py` (`__main__` implant loop) | standalone implant | `exec`-task shell + 5 modules + audit + egress |
| E-SVC-mcphub | `mcp-hub/main.py` + `core/server.py` | **dead-as-committed** (M-1) | nothing loads (`ModuleNotFoundError`) |
| E-SVC-phish | `phishing/main.py` (FastAPI) | standalone service | evilginx/set/gophish instances + campaigns |
| E-SVC-cai | `cai-service/main.py` | standalone service | postex+exploit pipelines (function-level) |
| E-SVC-cloak | `cloak-service/main.py` (FastAPI+uvicorn) | standalone service | `/browse`/`/screenshot`/`/interact` → browser automation |
| E-SVC-factory | `raphael/exploit_factory/__main__.py` | standalone CLI | payload generation + delivery + vhost-enum |
| E-SVC-verifier | `raphael/verifier/__main__.py` | standalone CLI | verify exploit delivery (channels server + core) |
| E-SVC-c2server | `c2-server/main.py` | standalone service, no lexicon hit (conduit) | postex modules at runtime (covered P23-adjacent) |
| E-SVC-scan | `modes/scan.py` (`__main__`) | standalone CLI | ScanPipeline (see P19) |

Auth notes: `tools.py`/`agent.py`/`session.py` use `require_scope` (not the Broker PDP);
`tools_bridge.py` (both routes), `kali-tools/server.py` (all routes), `bridge`
(dispatch) declare none; `api/main.py` + `phishing/main.py` + `mcp-hub/core/server.py`
set CORS `allow_origins=["*"]` (main.py with `allow_credentials=True`).

## 2. Path inventory (27 paths — full detail in CLASSIFICATION.md)

Broker-mediated (3): P01 canonical episode → `exec/` (evidence_store behind broker;
artifact/receipt stores unused → P24) ·
P02 CLI caller · P13 SHELL gated (live construction test S1–S4).
Welded (AM-4; 15, all WELD_SET paths): P04 tools→registry · P05 bridge-tools hop · P06 agent→engage
(+winrm/ladon/scanners) · P07 autonomous 13 phases (9 stubs→P26; cicd/ml/cloud/container
real) · P08 ci→engage · P09 bridge→autonomous→chains · P10 bridge→kali ·
P11 bridge/chains→c2 (+beacon/dga) · P12 kali `/run` sink · P16 agents→sandbox/relay/tools ·
P18 bridge `exploit.*` · P19 bridge `mode.*` (+providers/research/proxy) ·
P20 harvester/model/profile · P23 standalone services (+cloak/verifier/delivery/vhost/
egress/tunnels) · P27 legacy CLI branch (deleted; residual effects confined to dead code).
Seam fixed ON via `enforce_broker_mediation` (W-01…W-15); legacy branches deleted.
Dead, traced (9 groups): P03 welded subprocess stubs (effects → P27) · P14 weaponizer SUB-01–03 ·
P15 welded stubs · P17 reachable-no-effect notes · P21 session/sqlite ·
P22 unmounted ci + write-only queue (+webhook dead) · P24 orphans/chains/legacy/test-plane
(57 files) · P25 dead exfil/phishing pipelines + redcloud · P26 phase stubs (9).

## 3. Canonical INV-1 perimeter (declared = P01/P02 + P13 gate)

Static import closure rooted at `orchestrator.runtime` restricted to
`orchestrator.{runtime,brain,exec}` (`exec/inv1_guard`). Legacy/offensive packages outside
by construction.

## 4. Reproduction

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 evidence/phases/P3_0_reinventory/probe_reinventory.py
```
Read-only (lexicon census via the real `scan_source`, AST graph, one canonical episode,
SHELL construction negatives). `raw/` holds verbatim outputs;
`raw/effect_census.txt` is the census verbatim; `raw/phase_executors.txt` the 13 phases;
`raw/importer_tool.py` reproduces importer traces.
