# P3.0 Re-inventory — Classification (001R2 complete)

**Labels:** `Broker-mediated` = every side-effecting step passes `CapabilityBroker.propose_action`
(sole PDP) with PEP enforcement. `welded` (AM-4) = formerly not-yet-mediated: an effect from
the authoritative lexicon (process / network / destructive-file per `exec/inv1_guard.py`) was
reachable without the Broker; the path is now permanently routed through the Broker gate
(`enforce_broker_mediation`, fail-closed) with legacy unconditional branches deleted
(ADR-012 weld semantics; pre-weld call graph preserved in the row traces).
`dead` = no effect reachable from any entry
surface, with an explicit trace. Uncertainty rule: ambiguous → `welded` (pre-AM-4: not-yet).
**Probe:** `probe_reinventory.py` derives the census from the lexicon + source and asserts
every bridge method (40), every API route (27), every PHASE_EXECUTORS phase (13), and
every effect file (140) appears below.

## 0. Entry surfaces (all enumerated)

Deployed/live: E-CANON (`runtime/loop.py`), E-CLI (`raphael/main.py`),
E-CLI-LEGACY (`raphael/main.py` with `RAPHAEL_USE_LEGACY=1` — WELDED AM-4 W-15:
branch deleted, canonical Runtime only),
E-API (`api/main.py` app: agent/tools/tools_bridge/session routers),
E-TOOLS, E-BRIDGE-TOOLS, E-AGENT, E-CI-DEF (`api/ci.py`, defined but **unmounted**),
E-BRIDGE (`bridge/raphael_bridge.py`, 40 methods), E-AUTO (`modes/autonomous.py`),
E-KALI (`kali-tools/server.py`).
Standalone service entries (own server/`__main__`/CLI): mhddos, recon-pipeline, sword/api,
agent/agent (implant), phishing/main, cai-service, cloak-service, exploit_factory
`__main__`, verifier `__main__`, scan-mode `__main__`. (mcp-hub entry dead-as-committed.)
Conduit-only service (no lexicon hit, traced, no path): E-SVC-c2server
(`c2-server/main.py` imports postex modules at runtime; covered via P23-adjacent note).

## 1. Path inventory

### Broker-mediated (3)

| Path | Entry → chain → primitive site | Primitive | Gate |
|---|---|---|---|
| R3.0-P01 | E-CANON: `run_episode` → `stage_broker: broker.propose_action` → ScopeV0 conjunction → `stage_pep` → `stage_receipt`; PEP stores (`evidence_store`) act only behind broker decisions (`artifact_store`/`receipt_store` unused — P24) | `exec/` only | YES — Broker (5-dim) + scope + lifecycle |
| R3.0-P02 | E-CLI (default): `main()` → ScopeV0-bound mission → `run_episode(require_scope=True)` → P01 | same as P01 | YES — same broker |
| R3.0-P13 | SHELL: `broker.authorize_shell_session` → `SessionReceipt` → gated constructors + `ListenerManager` + broker-held `session.py` persistence, via `require_shell_authorization()` (registry-membership; receipt-bags rejected) | shell constructors / sockets / session files | YES — **live construction test** (probe S1–S4). No socket/PTY precedes the gate. |

### Welded (AM-4) — formerly not-yet-mediated (15 paths, all welded)

All 15 paths below are WELDED under Scope v0 (ADR-012: seam fixed ON =
permanently routed through Broker/PEP via `enforce_broker_mediation`, legacy
unconditional branches deleted; per-item tickets W-01…W-15 with post-weld
status in `WELD_SET.md`; denial proofs in `tests/test_am4_weld_gates.py`).
Row traces are preserved as the pre-weld call graph for audit reconstruction.

| Path | Entry → chain → terminal | Terminal |
|---|---|---|
| R3.0-P04 | E-API → `POST /api/tools/{tool}` (+3 convenience) → `tool_registry.execute_*` → `:67`; shared sink `audit_trail` append | `create_subprocess_exec` (SUB-04) + audit log write. No broker. |
| R3.0-P05 | E-API → `POST /api/tools/nmap`, `/recon` (no auth) → httpx → E-KALI; shared sink `audit_trail` | `kali-tools:23 subprocess.run`. No broker, no auth either hop. |
| R3.0-P06 | E-API → `POST /api/agent/execute[-sync]` → `engage` → Recon/Scan/Exploit/PostEx agents → `scanners/*` (nmap sockets, nuclei/whatweb httpx), `ad/*`, `kali.run` → E-KALI; PostEx `winrm` (httpx exec) + `ladon` (sockets); shared sink `audit_trail` | kali sink + direct sockets + WinRM network exec. Persona/scope checks are not the Broker PDP. |
| R3.0-P07 | E-CI-DEF `/scan` (entry-dead, P22) / queued `/engage` → `autonomous.handle` → 13 `PHASE_EXECUTORS` (§4): 9 stubs → P26; `cicd` (executor urllib probing, `token_harvester` reads, runner ssh `check_output`, poisoner workflow writes), `ml_attack` (pickle test-exec, `hf_hub` downloads), `cloud_abuse` (socket `getaddrinfo`, metadata `urlopen`, `iam_pathfinder` boto3 cloud-enum), `container_escape` (file/socket reads, `sandbox_detection` run); + spray/ad-chain; shared sink `audit_trail` | Mixed process/network/file effects (12 census files). No broker. |
| R3.0-P08 | E-CI-DEF `/agent-engage` (entry-dead) → `run_agent_engage` → P06 sink; `/engage` → write-only queue (P22) | same as P06. |
| R3.0-P09 | E-BRIDGE `mode.autonomous` → `autonomous.handle` → chains (`toolkit` httpx) → `kali.run` + `get_c2()`; `docker/k8s_escape` file/socket reads | kali sink + c2 sites. Bridge does zero authorization. |
| R3.0-P10 | E-BRIDGE `kali.*` (6) → `KaliToolsClient.run` (httpx; subprocess import-only since weld) → E-KALI | `subprocess.run` on remote branch. |
| R3.0-P11 | E-BRIDGE `c2.*` (5) / chains / spray → `c2/manager` → `sliver_backend` / `native_backend` (`beacon` aiohttp C2 server, `dga` sockets, `implant_builder`) | SUB-05/06 + SUB-07/08/09 exec; `:599 run(shell)`. Rate-limits are not the Broker PDP. |
| R3.0-P12 | E-KALI `POST /run` (no auth) → `run_tool` | `:23 subprocess.run(shlex.split(...))`. Shared sink of P05/P06/P10. |
| R3.0-P16 | E-AGENT/E-CI-DEF → `engage` → `ExploitAgent.execute`: `custom_payload` → `orchestrator/sandbox.py:25` (arbitrary `code`); `relay_chain` → socket RCE relay; `ad_kill_chain`/`llm_exploit`/`ssrf`/`xss`/`nuclei` tools → P09/P18/P06 sinks. **Correction:** `bridge.agent.exploit` does NOT reach here (no module `handle` → `AttributeError`); E-AGENT/E-CI-DEF only. | Arbitrary-code subprocess + network emission (HITL is not the Broker PDP). |
| R3.0-P18 | E-BRIDGE `exploit.generate` → `llm_exploit_engine` → `kali.run` + `call_model`; `exploit.relay_chain` → socket relay + RAT payloads; `exploit.mcp_start` → `MCPBridge HTTPServer(127.0.0.1)` + `ExploitPipeline` (`sqlmap_wrapper` httpx, ssrf/nettacker); `exploit.mcp_exploit` → httpx → pipeline | kali sink; RCE relay; unauthenticated local HTTP attack surface. No broker. |
| R3.0-P19 | E-BRIDGE `mode.community` → `call_model`; `mode.debate` → stub-`AttributeError` default / `call_model` if disabled; `mode.deep_research` → stub + httpx OSINT; `mode.scan` → `ScanPipeline` (sockets, `requests`, httpx→kali; `proxy_guard` network verify) / `--direct` CLI; `mode.student` → `kali.run(whatweb)` profile + `research_scheduler` httpx harvester, no broker (`proposal_only`; `_test_candidate_brokered` needs a caller broker that never comes) | Unbrokered LLM + OSINT + scan emission; kali sink. |
| R3.0-P20 | E-BRIDGE `harvester.*` → `HarvesterEngine` (sqlite + httpx feeds); `model.call` → `providers` aiohttp LLM APIs; `target.profile` → nmap `run` | Unbrokered network + direct subprocess. No broker. |
| R3.0-P23 | Standalone service entries (no broker anywhere): mhddos `/attack`→`Popen`; recon `/recon/*`→subfinder exec+scanners; sword/api `/sword/run`→`phase_0` exec+`popen` health, `phase_1` httpx, `report` writes, `phase_4`→`bulk/dns` tunnels+`BounceBack`; agent implant loop→`exec`-task shell+5 modules+`modules/audit`+`egress` transport; phishing/main→evilginx/set/gophish (+`main.py` template upload); cloak `/browse|/screenshot|/interact`→browser automation; cai-service→postex+exploit pipelines; factory CLI→delivery+vhost-enum payloads (+`templates` render-write); verifier CLI→channels server+core unlink; sword `phase_5` template-write + `smtp_tunnel` SMTP exfil; techniques `fast_port_scan` asyncio port-scan CLI | Process/network/file effects across 31 census files. **Weld-or-P9-delete per D-1** (mcp-hub portion already dead, CENSUS M-1). |
| R3.0-P27 | E-CLI-LEGACY (`RAPHAEL_USE_LEGACY=1` → `RaphaelOrganism.run()`): planner `select_next_step` → `cortex/hypothesizer.hypothesize` → `:62 httpx.post` (LLM network, unbrokered); `Executor.execute` → `KaliBridge.run` → httpx attempt then fail-closed raise (SUB-13/14 welded); `shutdown()` → `hippocampus.store` → `:75 open(w)` episode write; `parallel_recon` batch → executor (raises, contained); blackboard sqlite writes (out-of-lexicon effect, noted). P03 records the welded subprocess stubs on this same branch; P27 records its executing effects. | Unbrokered network + file-write effects on a shipped runnable branch. No broker anywhere on the chain. |

### Dead — no effect reachable, traced (9 groups)

| Path | Trace | Basis |
|---|---|---|
| R3.0-P03 | E-CLI legacy branch, welded subprocess stubs: `Executor._subprocess_fallback` + `KaliBridge._subprocess_run` deleted (SUB-13/14); callers get fail-closed `RuntimeError`. The branch's REMAINING executing effects (network/file) are P27, not P03. | Welded-closed primitives; live effects moved to P27. |
| R3.0-P14 | `weaponizer_engine` (SUB-01/02/03): sole importer is `weaponizer/__init__` re-export | Dead. |
| R3.0-P15 | Welded stubs ex-SUB-10/13/14: 9 names absent as code definitions (AST) | Welded-closed. |
| R3.0-P17 | No-executable-effect terminals, each traced: `agent.*` bridge methods → `AttributeError`; `payload_db` → local sqlite read; `conductor.*` → pure stubs; `brain.analytics/memory` → counter/in-memory; `persona.*` → env-local; `target.set/scope.set` → `ImportError`; `skill_agent` → dead `import subprocess`, never used; `api_gateway_exploit` → imports unused; `session_manager`/`docker_client` → docker exec never invoked with a live session in-tree; pure API routes → list/check/stat | Dead-end, per-method probe proofs. |
| R3.0-P21 | Session router (8 routes) → `session_manager` sqlite CRUD (no lexicon hit) | U-2: no-effect terminal. |
| R3.0-P22 | `ci_router` imported nowhere → 6 routes entry-dead. `POST /engage` write-only (`handle_queue_loop`/`handle_multi` zero callers). `webhook.py` (httpx) ← ci only → dead with it. | Entry-dead + write-only queue (U-1). |
| R3.0-P24 | Dead files (CENSUS §E, per-file importer proof): orphans (scihub, propagation, binary_analyzer, survivability, dependency_check, executor.py, cleanup.py, agent/audit.py, mesh, nvidia, tactics, retry, waf, blind_probe, social, privesc, hashcat-chain, webhook); legacy Head-1 plane, effects on legacy branch only or never invoked (episodic, hypothesizers, cortex/planner-imports, postmortem-effect); techniques/* (registry data-only) + literal fabric note; mcp-hub M-1 (12 files + test); arena test-harness plane (13 files, incl. `d10_regression_test` and requests-based llm harness); unused PEP stores (`artifact_store`, `receipt_store`); `eventbus/core.py` (001R6: Redis client — sole live-real constructor `integration/harness.py:112` pre-seeds `fakeredis` so `connect()` returns early and never dials; `test_pipeline` mocks `from_url`; `blackboard/contracts`/`cortex/planner` wire a bus never constructed live; `vhost_enum` stores but never publishes; `main.py:128` is a different circulatory in-memory bus) | Dead, 60 files. |
| R3.0-P25 | Dead chains: `exfil/pipeline.py` + `phishing/pipeline.py` (zero importers) → `redcloud` | Dead-chain. (`bounceback`/tunnels live via sword → P23.) |
| R3.0-P26 | `PHASE_EXECUTORS` stub phases (9): harvest/recon/scan/exploit/postex/lateral/credential/exfil/phish — invoked by `autonomous.handle` but return `NOT_IMPLEMENTED` with zero effects | Dead-end stubs (P5 owns implement-or-delete). |

**Totals:** entry surfaces 23 (12 live incl. legacy branch + ci-def + 11 standalone) · bridge methods 40/40 ·
API routes 27/27 · phases 13/13 · census files 150/150 (welded 78 · mediated 6 · notes 4 · dead 62) ·
paths **27** · **Broker-mediated 3** · **welded 15** · **dead 9 groups**.

## 2. Bridge dispatch table (40/40 — every method → path)

| Method | Handler → first hop | Path |
|---|---|---|
| mode.autonomous | autonomous.handle | P09 |
| mode.community | call_model | P19 |
| mode.debate | SkillAgent (stub→AttributeError) / call_model | P19 (P17 note) |
| mode.deep_research | conductor stub + httpx | P19 |
| mode.scan | ScanPipeline | P19 |
| mode.student | student.handle (proposal_only + kali whatweb) | P19 |
| agent.recon / agent.exploit / agent.postex / agent.engage | missing module `handle` → AttributeError | P17 |
| c2.build_implant / c2.deploy / c2.list_beacons / c2.task_beacon / c2.sliver_connect | c2.manager / backends (beacon server, dga, builder) | P11 |
| exploit.generate / exploit.relay_chain / exploit.mcp_start / exploit.mcp_exploit | llm engine / relay sockets / MCP listener+pipeline / httpx | P18 |
| exploit.payload_db | local sqlite read | P17 |
| kali.run / kali.nuclei / kali.sqlmap / kali.hashcat / kali.impacket / kali.list_tools | KaliToolsClient.run → httpx | P10 |
| harvester.run_cycle / harvester.search_techniques / harvester.get_cves | HarvesterEngine (sqlite+httpx) | P20 |
| conductor.call / conductor.select_strategy | pure stubs | P17 |
| brain.analytics / brain.memory_store / brain.memory_recall | counter / in-memory store | P17 |
| model.call | providers aiohttp (LLM APIs) | P20 |
| persona.set / persona.resolve | env / override pure | P17 |
| target.set / scope.set | ImportError (broken shims) | P17 |
| target.profile | target_profiler nmap | P20 |

(Callee-attribute existence asserted per-method by the probe.)

## 3. API route table (27/27 — every route → path)

| Router (prefix) | Routes (every route literal) | Paths |
|---|---|---|
| tools `/api/tools` | `GET ""`, `POST "/{tool_name}"`, `POST "/nmap/scan"`, `POST "/sqlmap/scan"`, `POST "/crackmapexec/enum"` | P17 (list) + P04 (4 exec) |
| tools_bridge `/api/tools` | `POST "/nmap"`, `POST "/recon"` (no auth) | P05 |
| agent `/api/agent` | `POST "/execute"`, `POST "/execute-sync"`, `GET "/personas"`, `POST "/persona/{persona_id}/permission"` | P06+P16 (exec), P17 (pure) |
| session `/api/sessions` | `POST ""`, `GET ""`, `GET "/stats"`, `GET "/{session_id}"`, `PATCH "/{session_id}"`, `DELETE "/{session_id}"`, `GET "/{session_id}/messages"`, `POST "/{session_id}/messages"` | P21 |
| ci `/v1/ci` (UNMOUNTED) | `POST "/engage"`, `GET "/engage/{eng_id}"`, `GET "/report/{eng_id}"`, `POST "/scan"`, `POST "/agent-engage"`, `GET "/health"` | P22 (entry-dead; handlers P07/P08/P16; webhook P24) |
| main `/` | `GET "/health"`, `GET "/api/personas"` | P17 |

## 4. PHASE_EXECUTORS table (13/13 — every phase → path)

Executor targets from `brain/phases/models.py` (verbatim: `raw/phase_executors.txt`).

| Phase | Executor target | Effect-bearing sink | Path |
|---|---|---|---|
| harvest | `models._exec_harvest` | none (NOT_IMPLEMENTED stub) | P26 dead |
| recon | `models._exec_recon` | none (stub) | P26 dead |
| scan | `models._exec_scan` | none (stub; distinct from `modes/scan.py` ScanPipeline) | P26 dead |
| exploit | `models._exec_exploit` | none (stub) | P26 dead |
| postex | `models._exec_postex` | none (stub) | P26 dead |
| lateral | `models._exec_lateral` | none (stub) | P26 dead |
| credential | `models._exec_credential` | none (stub) | P26 dead |
| exfil | `models._exec_exfil` | none (stub) | P26 dead |
| phish | `models._exec_phish` | none (stub) | P26 dead |
| cicd | `models._exec_cicd` → `cicd_executor.exec_cicd_phase` | executor urllib probing; `token_harvester` reads; runner ssh recon; poisoner file-writes | P07 welded |
| ml_attack | `models._exec_ml_attack` → `ml_attack_executor.exec_ml_attack_phase` | pickle test-exec; `hf_hub` downloads | P07 welded |
| cloud_abuse | `models._exec_cloud_abuse` → `cloud_executor.exec_cloud_phase` | socket `getaddrinfo`; metadata `urlopen`; `iam_pathfinder` boto3 enum (incl. reachable network effects) | P07 welded |
| container_escape | `models._exec_container_escape` → `container_escape_executor.*` | file/socket reads; `sandbox_detection` run | P07 welded |

All 13 invoked (when listed) via `autonomous.handle` → `PHASE_EXECUTORS[phase](target, findings)`.
Stub phases return `success=False, NOT_IMPLEMENTED` with zero side effects (verified by source).

## 5. Canonical INV-1 perimeter (declared = P01/P02 + P13 gate)

Static import closure rooted at `orchestrator.runtime` restricted to
`orchestrator.{runtime,brain,exec}` (`inv1_guard`). Legacy/offensive packages outside by
construction. Reproduced by probe T4 (35 modules / 0 violations).

## 6. Reproduction

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 evidence/phases/P3_0_reinventory/probe_reinventory.py
```
Read-only: lexicon census via the real `inv1_guard.scan_source`, AST graph, one canonical
episode, SHELL construction negatives. `raw/` holds verbatim outputs;
`raw/effect_census.txt` is the census verbatim; `raw/phase_executors.txt` the 13 phases.
