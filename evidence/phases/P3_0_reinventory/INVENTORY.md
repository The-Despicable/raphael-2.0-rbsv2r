# P3.0 Re-inventory — Full Execution-Path Inventory (post-P2 Runtime, v4.1 AM-1)

**HEAD:** `ff602982aa9d81460a54162f1d417a56e9e3880c` (branch `weld-sub10-evidence`)
**Schema:** same as P0 §11.3 (`evidence/phases/P0/02_execution_inventory/execution_paths.md` +
`subprocess_sites.md`): entry point → import/call chain → primitive call site,
with per-route authorization.
**Method:** read-only static trace (AST import walk + source read). No legacy/offensive
code executed, no network touched. Reproduced by `probe_reinventory.py` in this directory.
**Scope:** every execution path reachable from **any** entry point in the post-P2/P3 tree
(canonical + deployed service surface + standalone planes).

---

## 1. Entry-point census (post-P2)

| EP ID | Entry point | Type | Mounts / dispatches to |
|---|---|---|---|
| E-CANON | `src/orchestrator/runtime/loop.py` `RaphaelRuntime.run_episode` | canonical sequencer | `stages.py` 10 stages → `broker.propose_action` → `exec/` PEP |
| E-CLI | `src/raphael/main.py` `main()` | production CLI caller | canonical `RaphaelRuntime` (default); legacy `RaphaelOrganism` iff `RAPHAEL_USE_LEGACY=1` |
| E-API | `src/orchestrator/api/main.py` `app` | deployed FastAPI service | mounts `agent_router`, `tools_router`, `tools_bridge_router`, `session_router`; `GET /health`, `GET /api/personas` |
| E-TOOLS | `src/orchestrator/api/tools.py` `POST /api/tools/{tool_name}` (+ `/nmap/scan`, `/sqlmap/scan`, `/crackmapexec/enum`) | deployed router | `chains/tool_registry.execute_*` |
| E-BRIDGE-TOOLS | `src/orchestrator/api/tools_bridge.py` `POST /api/tools/nmap`, `POST /api/tools/recon` | deployed router (**no auth dependency**) | `httpx` POST `http://localhost:3800/run` (kali-tools server) |
| E-AGENT | `src/orchestrator/api/agent.py` `POST /api/agent/execute`, `/execute-sync` | deployed router | `orchestrator.agents.engage.run_agent_engage` |
| E-CI | `src/orchestrator/api/ci.py` `POST /v1/ci/engage`, `/scan`, `/agent-engage` | deployed router | `modes/autonomous.handle` (`/scan`), `agents/engage.run_agent_engage` (`/agent-engage`), `engagement_queue` (`/engage`) |
| E-BRIDGE | `src/bridge/raphael_bridge.py` JSON-RPC `mode.*`, `kali.*`, `c2.*`, `agent.*`, `exploit.*` | deployed IPC bridge (`__main__` stdio loop) | `modes/*`, `agents/*`, `c2/*`, `kali_tools_client.kali`, `exploit/*`, `harvester/*` |
| E-AUTO | `src/orchestrator/modes/autonomous.py` `handle()` | legacy orchestrator (library + reachable) | `brain/phases.PHASE_EXECUTORS`, `chains/credential_spray.spray`, `chains/ad_kill_chain.run_chain` |
| E-KALI | `src/kali-tools/server.py` `POST /run` | deployed runner service (**no auth**) | `subprocess.run(cmd)` |
| E-STANDALONE | `src/recon-pipeline/main.py`, `src/sword/phase_0_recon.py`, `src/agent/modules/executor.py`, `src/orchestrator/weaponizer/weaponizer_engine.py` | standalone planes | no deployed caller (see P14) |

Auth notes (service surface, verified by source read):
- `api/tools.py`, `api/agent.py`, `api/ci.py`, `api/session.py` use `Depends(require_scope(...))`.
- `api/tools_bridge.py` (`run_nmap`, `run_recon`) declares **no** `Depends` — unauthenticated at the app layer.
- `src/kali-tools/server.py` declares **no** auth on `/run`, `/tools`, `/health` — `subprocess.run(shlex.split(f"{tool} {args}"))`, unauthenticated.
- `api/main.py` sets `CORSMiddleware allow_origins=["*"]` with `allow_credentials=True`.
- `bridge/raphael_bridge.py` performs no authorization check before dispatch (`handle_request` → `self.methods[method](**params)`).

---

## 2. Path inventory (same schema as P0 §11.3)

Columns: Path ID | Entry → chain → primitive site | Primitive | Broker gate? | Classification.

### Broker-mediated (3)

| Path | Entry → chain → primitive site | Primitive | Gate |
|---|---|---|---|
| R3.0-P01 | E-CANON: `RaphaelRuntime.run_episode` → `stage_broker` (`broker.propose_action`) → `stage_pep` → `exec/safe_capability.SafeProvingCapability.inspect` or `exec/sandbox.SandboxedExecutor.execute` | `exec/` only (fixture read; sandbox `Popen` behind allow-decision + receipt re-verify) | YES — `CapabilityBroker.propose_action` (5-dim deny-by-default) + ScopeV0 conjunction + lifecycle `AUTHORIZED→STARTED→SUCCEEDED/FAILED` |
| R3.0-P02 | E-CLI (default): `raphael/main.py:main()` → `_canonical_mission` (ScopeV0 bound) → `RaphaelRuntime(evidence_store=...)` → `run_episode(require_scope=True)` → P01 | same as P01 | YES — same broker; scope fail-closed pre-stage |
| R3.0-P13 | SHELL: `CapabilityBroker.authorize_shell_session` → `SessionReceipt(authorized=True, authorized_by="capability_broker")` → `ReverseShellCapability.__init__` / `SSHShellCapability.__init__` / `ShellCapabilityFactory.create` / `create_from_listener` / `ListenerManager.*` via `require_shell_authorization()` | shell constructors (no direct subprocess; session/command auth in broker) | YES — construction requires valid broker-issued receipt (`ShellNotAuthorized` otherwise); WELD-SHELL welded at HEAD |

### Not-yet-mediated (9)

| Path | Entry → chain → primitive site | Primitive | Why not mediated |
|---|---|---|---|
| R3.0-P04 | E-API → E-TOOLS: `POST /api/tools/{tool}` → `_execute_tool_by_name` → `chains/tool_registry.execute_{nmap,sqlmap,bloodhound,metasploit,crackmapexec,chisel}` → `_run_command` (`tool_registry.py:67`) | `asyncio.create_subprocess_exec(*cmd)` (SUB-04) | No `broker.propose_action` on path. Persona/approval/scope checks (`check_tool_permission`, `default_scope.check`) are not the Broker PDP. |
| R3.0-P05 | E-API → E-BRIDGE-TOOLS: `POST /api/tools/nmap`, `/recon` → `_run_in_kali` → `httpx` POST `KALI_CONTAINER_URL (/run)` → E-KALI `subprocess.run` | network hop → `kali-tools/server.py:23 subprocess.run` | No broker on either hop; bridge-router hop itself unauthenticated. |
| R3.0-P06 | E-API → E-AGENT: `POST /api/agent/execute[-sync]` → `agents/engage.run_agent_engage` → `Recon/Scan/ExploitAgent` → `scanners/*_wrapper`, `ad/*_wrapper` → `kali.run` → httpx → E-KALI `subprocess.run` | network hop → `subprocess.run` (via `kali.run`) | No broker; persona filtering + `default_scope.check` are not the Broker PDP. Prefix persona escalation (`Ghost `/`Stealth `/`Full `) is string parsing, not authorization. |
| R3.0-P07 | E-CI: `POST /v1/ci/scan` → `modes/autonomous.handle` → `PHASE_EXECUTORS[target]` + `spray` + `run_ad_kill_chain` → `kali.run` / `c2/*` (see P09/P11 sinks) | `kali.run`→`subprocess.run`; `c2` subprocess sites | No broker; `default_scope.check` only. |
| R3.0-P08 | E-CI: `POST /v1/ci/agent-engage` → `agents/engage.run_agent_engage` → same sink as P06 | same as P06 | No broker; same non-PDP checks as P06. (`POST /v1/ci/engage` queues the same `handle` work via `engagement_queue`.) |
| R3.0-P09 | E-BRIDGE: `mode.autonomous` → `modes/autonomous.handle` → `chains/ad_kill_chain.run_chain`, `chains/credential_spray.spray` → `kali.run` (`kerbrute`, `bloodhound-python`, `netexec`, …) + `c2.manager.get_c2()` | `kali.run`→`subprocess.run`; `c2` sites | No broker; bridge performs zero authorization. Covers P0 SUB-04-adjacent `kali` fan-out. |
| R3.0-P10 | E-BRIDGE: `kali.run`, `kali.nuclei/sqlmap/hashcat/impacket/list_tools` → `kali_tools_client.KaliToolsClient.run` → httpx → E-KALI `subprocess.run` (or fail-closed `RuntimeError` when remote unavailable — still no broker on the success branch) | network hop → `subprocess.run` | No broker; SUB-10 weld removed only the *local* fallback, not this remote→subprocess branch. |
| R3.0-P11 | E-BRIDGE / P09 / spray: `c2.build_implant/deploy/list_beacons/task_beacon/sliver_connect`, `chains/*` → `c2.manager` → `sliver_backend` / `native_backend` → `implant_builder` | `sliver_backend.py:93,119 asyncio.create_subprocess_exec` (SUB-05/06); `implant_builder.py:342,477,529 asyncio.create_subprocess_exec` (SUB-07/08/09); `implant_builder.py:599 subprocess.run(shell=True)` | No broker on any of these constructions/executions. `C2Manager` rate-limit/session-cap is not the Broker PDP. |
| R3.0-P12 | E-KALI: `POST /run?tool=&args=&timeout=` → `run_tool` (`server.py:19-33`) | `server.py:23 subprocess.run(shlex.split(f"{tool} {args}"))` | No auth, no broker. Shared primitive sink for P05/P06/P10 (and any HTTP client of `:3800/run`). |

### Dead / welded-closed (3 groups covering all remaining P0 sites)

| Path | Entry → chain → primitive site | Primitive today | Basis |
|---|---|---|---|
| R3.0-P03 | E-CLI legacy branch (`RAPHAEL_USE_LEGACY=1`): `main()` → `RaphaelOrganism.run` → `Executor.execute` → `KaliBridge.run` | NONE reachable — `KaliBridge.run` raises fail-closed `RuntimeError` (WELD-SUB14); `Executor._subprocess_fallback` / `_subprocess_run` deleted | Welded-closed. P0 SUB-13/SUB-14 sites no longer exist in tree (verified by grep: zero `create_subprocess` under `src/raphael/`). |
| R3.0-P14 | Standalone planes — no deployed caller: `weaponizer_engine.py:121,179,226` (SUB-01/02/03); `recon-pipeline/main.py:89` (SUB-11); `agent/modules/executor.py:7` (SUB-12); `sword/phase_0_recon.py:115,153,192` (SUB-15/16/17) | primitives exist but unreachable | Dead, re-confirmed: zero importers from any of E-CANON/E-CLI/E-API/E-BRIDGE/E-AUTO/E-KALI (importer search in `raw/`). P1 deprecation markers present on `weaponizer`, `tool_registry` header, `sliver_backend` header. |
| R3.0-P15 | Welded stubs: ex-`SUB-10` (`kali_tools_client._run_local`, SUB-10), ex-`SUB-13/14` (above) | NONE — symbols deleted (`_run_local`, `KaliBypassNotAuthorized`, `_BYPASS_AUTHORIZED`, `authorize_local_bypass`, `_subprocess_fallback`, `_subprocess_run`, `authorize_bypass` all absent) | Welded-closed at HEAD (WELD-SUB10/SUB14 evidence in `evidence/phases/P3_0/`). `KaliToolsClient.run` local branch raises `RuntimeError`; `asyncio`/`subprocess` remain only as dead imports. |

**Totals:** entry points 11 (10 live + 1 standalone group) · paths **15** · **Broker-mediated 3** · **not-yet-mediated 9** · **dead/welded-closed 3 groups** (covering 3 welded sites + 9 dead-standalone sites).

---

## 3. Canonical INV-1 perimeter (declared, = Broker-mediated canonical set)

```
src/orchestrator/runtime/**          (RaphaelRuntime thin sequencer, stages, scope, policy, organs)
+ canonical brain control-plane it loads (broker, action/planner, world, student-recording, contradiction, evidence)
+ src/orchestrator/exec/**           (sole authorized primitive namespace: safe_capability, sandbox, guards, stores)
```

 Computed deterministically as the static import closure rooted at `orchestrator.runtime`
 restricted to `orchestrator.{runtime,brain,exec}` (`exec/inv1_guard.canonical_perimeter_modules`).
 `verify_inv1_primitive_confinement` scans that perimeter; `exec/` is the authorized namespace and
 is never reported. Legacy/offensive packages (`api/`, `bridge/`, `chains/`, `c2/`, `exploit/`,
 `scanners/`, `kali-tools/`, …) are outside the declared perimeter by construction.

## 4. How to reproduce

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 evidence/phases/P3_0_reinventory/probe_reinventory.py
```

Read-only: parses source (AST), never imports legacy/offensive modules, never touches the
network, never executes a primitive. The one canonical import it performs (`inv1_guard`,
`runtime` closure computation) is the same import the gate suite already performs.
`raw/` holds verbatim command outputs referenced by `P0_DIFF.md` / `CLASSIFICATION.md`.
