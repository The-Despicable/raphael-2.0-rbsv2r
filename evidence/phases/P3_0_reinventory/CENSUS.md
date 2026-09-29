# P3.0 Re-inventory — Authoritative Effect Census (001R2)

**HEAD:** `3b2e22db3d952622150d271c12c41d9ed21e81fd`
**Lexicon (authoritative, not invented):** `src/orchestrator/exec/inv1_guard.py` —
`scan_source()` over `src/**/*.py` (verbatim output: `raw/effect_census.txt`).
**Categories:** `P` = process execution (subprocess/asyncio-subprocess/os.exec-spawn) ·
`N` = network (socket/requests/httpx/aiohttp/paramiko/docker/urllib/http-server) ·
`F` = destructive-file (os.remove-unlink-rmdir/shutil.rmtree/open-write).
Per FIRST INSPECTION: a bare import with no effectful use is recorded as import-only
(no weld). Census = 150 files (post-AM-4-R2: 54 files bear process hits · 77 network ·
51 destructive-file; categories overlap). AM-4-R2 branch deletions removed 5
category letters across 5 files (rows #1, #4, #23, #46, #55); row count unchanged.
**Reachability:** AST import graph (function-level + parent-package edges), BFS from 25 live
+ 12 service + verifier-CLI entries (`raw/importer_tool.py` reproduces it;
per-file traces: `raw/importers_final.txt`).
**Disposition key:** `Pxx <label>` = path R3.0-Pxx + label
(welded (AM-4) / mediated / dead / note; `welded` supersedes the pre-AM-4
`not-yet` label on all 15 WELD_SET paths).

## A. Live entries → welded (AM-4 WELD_SET paths; see WELD_SET.md post-weld status)

| # | File | Cats | Key sites | Reachability → sink | Disp |
|---|---|---|---|---|---|
| 1 | `src/orchestrator/chains/tool_registry.py` | F | :67 `create_subprocess_exec` DELETED (AM-4-R2 W-01 branch deletion); :341 `Path(rc_file).write_text` retained (001R5 rule find; dead behind gate) | api/tools (live) | P04 welded |
| 2 | `src/orchestrator/api/tools_bridge.py` | N | httpx hop | E-BRIDGE-TOOLS (live) | P05 welded |
| 3 | `src/orchestrator/agents/exploit.py` | N | requests ×2; kali/scanner fan-out | engage (live) | P06 welded |
| 4 | `src/orchestrator/sandbox.py` | P | :25 `run(python3 tmp)` DELETED + :39 `Path(tmppath).unlink` DELETED (AM-4-R2 W-10 branch deletion); `import subprocess` retained | agents/exploit `custom_payload` (live) | P16 welded |
| 5 | `src/orchestrator/postex/winrm_exploit.py` | N | httpx (exec via WinRM) | agents/postex, sword, c2-server | P06 welded |
| 6 | `src/orchestrator/postex/ladon_scanner.py` | N,P | socket (subprocess import-only) | agents/postex, sword | P06 welded |
| 7 | `src/orchestrator/scanners/nmap_scanner.py` | N | raw sockets | agents, pipelines, recon/sword/cai services | P06 welded |
| 8 | `src/orchestrator/scanners/nuclei_scanner.py` | N | httpx→kali-tools | agents, pipelines, services | P06 welded |
| 9 | `src/orchestrator/scanners/whatweb_scanner.py` | N | requests | agents, pipelines, services | P06 welded |
| 10 | `src/orchestrator/brain/phases/cicd_executor.py` | N | urllib metadata probing | autonomous (live) | P07 welded |
| 11 | `src/orchestrator/cicd/token_harvester.py` | N | file reads (token harvest) | cicd_executor (live) | P07 welded |
| 12 | `src/orchestrator/cicd/runner_fingerprinter.py` | N,P | ssh `check_output` ×7 | cicd_executor (live) | P07 welded |
| 14 | `src/orchestrator/ml_attack/hf_hub_api_client.py` | F,N | requests/urllib + model `open-wb` | ml_executor (live) | P07 welded |
| 15 | `src/orchestrator/ml_attack/pickle_payload_factory.py` | P,F | :571 test-exec; payload files (153 template literal) | ml_executor (live) | P07 welded |
| 16 | `src/orchestrator/cloud_abuse/cloud_enum.py` | N | `socket.getaddrinfo` | cloud_executor (live) | P07 welded |
| 17 | `src/orchestrator/cloud_abuse/metadata_abuse.py` | N | `urllib.urlopen` cloud metadata | cloud_executor (live) | P07 welded |
| 18 | `src/orchestrator/container_escape/docker_escape.py` | N,P | open/socket (subprocess import-only) | container_executor (live) | P07 welded |
| 19 | `src/orchestrator/container_escape/k8s_escape.py` | N | open (urllib import-only) | container_executor (live) | P07 welded |
| 20 | `src/orchestrator/container_escape/sandbox_detection.py` | P | :337 `run` | container_executor (live) | P07 welded |
| 21 | `src/orchestrator/brain/target_profiler.py` | N,P | :18 nmap `run` | autonomous + bridge (live) | P20 welded |
| 22 | `src/orchestrator/kali_tools_client.py` | N,P | httpx client (subprocess import-only, welded) | bridge/chains/ad (live) | P10 welded |
| 23 | `src/orchestrator/c2/sliver_backend.py` | P | :93,119 exec + unlink DELETED (AM-4-R2 W-08 branch deletion); `import subprocess` retained | c2.manager ← bridge/chains (live) | P11 welded |
| 24 | `src/orchestrator/c2/implant_builder.py` | P,F | :342,477,529 exec; :599 `run(shell)` | native_backend ← manager (live) | P11 welded |
| 25 | `src/orchestrator/c2/beacon.py` | N | aiohttp C2 HTTP server | c2 pkg ← manager (live) | P11 welded |
| 26 | `src/orchestrator/c2/dga.py` | N | `getaddrinfo` | native_backend (live) | P11 welded |
| 27 | `src/kali-tools/server.py` | P | :23 `run` (no auth) | deployed runner (live root) | P12 welded |
| 28 | `src/orchestrator/audit_trail.py` | F | `open-a` audit log | api routes + autonomous (live) | P04 shared (welded AM-4 W-01) |
| 29 | `src/orchestrator/exploit/relay_chain.py` | N | raw-socket RCE relay (:246 payload literal) | agents/exploit + bridge (live) | P16 welded |
| 30 | `src/orchestrator/exploit/mcp_bridge.py` | N | `HTTPServer(127.0.0.1)` + pipeline | bridge `mcp_start` (live) | P18 welded |
| 31 | `src/orchestrator/exploit/nettacker_exploit.py` | N | requests + socket | exploit pipeline ← bridge (live) | P18 welded |
| 32 | `src/orchestrator/exploit/sqlmap_wrapper.py` | N | httpx→kali-tools | pipelines ← bridge (live) | P18 welded |
| 33 | `src/orchestrator/exploit/ssrf_scanner.py` | N | requests + socket | agents ← engage (live) | P16 welded |
| 34 | `src/orchestrator/exploit/xss_scanner.py` | N | requests | agents (live) | P16 welded |
| 35 | `src/orchestrator/harvester/cve_feeds.py` | N | httpx feeds | student/autonomous/bridge (live) | P20 welded |
| 36 | `src/orchestrator/harvester/github_scraper.py` | N | httpx | same | P20 welded |
| 37 | `src/orchestrator/harvester/technique_extractor.py` | N | httpx | same | P20 welded |
| 38 | `src/orchestrator/harvester/web_feeds.py` | N | httpx | same | P20 welded |
| 39 | `src/orchestrator/modes/deep_research.py` | N | httpx OSINT | bridge (live) | P19 welded |
| 40 | `src/orchestrator/providers.py` | N | aiohttp LLM APIs | bridge/agents (live) | P19 welded |
| 41 | `src/orchestrator/student/research_scheduler.py` | N | httpx CVE scan | student/autonomous (live) | P19 welded |
| 42 | `src/orchestrator/ad/toolkit.py` | N | `httpx.get` | ad_kill_chain (live) | P09 welded |
| 43 | `src/orchestrator/proxy_guard.py` | N | requests/socket verify | scan mode, mhddos, pipelines (live) | P19 welded |

## B. Standalone service entries → welded (W-14 gated; P9-delete ruling owed per D-1)

| # | File | Cats | Key sites | Service entry | Disp |
|---|---|---|---|---|---|
| 46 | `src/mhddos-service/main.py` | P | :149 `Popen(mhddos)` (run_real branch DELETED AM-4-R2 W-14; `import subprocess` retained); raw-socket Tor fallback DELETED | own FastAPI+uvicorn | P23 welded |
| 47 | `src/recon-pipeline/main.py` | P | :89 subfinder exec | own FastAPI `:3503` | P23 welded |
| 48 | `src/sword/api.py` | P | :55 `popen(which)` — gated route (AM-4-R2: deletion would drop this sole-hit row → §2-deferred with rationale; route denies) | own FastAPI | P23 welded |
| 49 | `src/sword/phase_0_recon.py` | N,P | :115,153,192 exec | pipeline ← sword/api | P23 welded |
| 50 | `src/sword/phase_1_scan.py` | N | httpx | pipeline ← sword/api | P23 welded |
| 51 | `src/sword/report.py` | F | report `open-w` ×4 | sword/api | P23 welded |
| 52 | `src/orchestrator/exfil/bulk_exfil.py` | N | aiohttp/urllib tunnels | sword phase_4 ← sword/api | P23 welded |
| 53 | `src/orchestrator/exfil/dns_tunnel.py` | N | socket tunnel | sword phase_4 ← sword/api | P23 welded |
| 54 | `src/orchestrator/exfil/bounceback.py` | P,F | pgrep/pkill | sword phase_4 ← sword/api | P23 welded |
| 55 | `src/agent/agent.py` | N | :77 `run(shell)` + :106 `rmtree` DELETED (AM-4-R2 W-14 execute_task/uninstall branch deletion); `import httpx/subprocess` retained | own `__main__` implant loop | P23 welded |
| 56 | `src/agent/modules/stealth.py` | N,P,F | runs + requests | implant ← agent.agent | P23 welded |
| 57 | `src/agent/modules/exfil.py` | N,P | runs + httpx | implant | P23 welded |
| 58 | `src/agent/modules/persistence.py` | P,F | runs + unlink | implant | P23 welded |
| 59 | `src/agent/modules/lateral.py` | N,P,F | runs + unlink | implant | P23 welded |
| 60 | `src/agent/modules/credtheft.py` | P,F | runs + unlink | implant | P23 welded |
| 61 | `src/agent/modules/audit.py` | F | `open-a/wb` logs | implant | P23 welded |
| 62 | `src/orchestrator/egress/router.py` | N | httpx/requests/socket | implant ← agent.agent | P23 welded |
| 63 | `src/cloak-service/main.py` | N | httpx; FastAPI+uvicorn routes | own service | P23 welded |
| 64 | `src/cloak-service/cloakbrowser.py` | N | httpx transport | cloak main | P23 welded |
| 65 | `src/orchestrator/phishing/evilginx.py` | P,F | :69 `run`; config `open-w` | phishing/main service | P23 welded |
| 66 | `src/orchestrator/phishing/gophish.py` | N | urllib API client | phishing/main service | P23 welded |
| 67 | `src/orchestrator/phishing/set_wrapper.py` | P | :10 `run(which)` | phishing/main service | P23 welded |
| 69 | `src/raphael/exploit_factory/delivery.py` | N | aiohttp client | factory pkg ← `__main__` CLI | P23 welded |
| 71 | `src/raphael/techniques/vhost_enum/enumerators.py` | N | aiohttp/sockets/open | factory core/`__main__` CLI | P23 welded |
| 72 | `src/raphael/verifier/channels.py` | N | aiohttp.web server | verifier `__main__` CLI | P23 welded |
| 73 | `src/raphael/verifier/core.py` | F | :313 unlink | verifier `__main__` CLI | P23 welded |

## C. Broker-mediated (sole PDP + PEP)

| # | File | Cats | Note | Disp |
|---|---|---|---|---|
| 74 | `src/orchestrator/exec/sandbox.py` | P,F | Authorized PEP (receipt re-verify) | P01 mediated |
| 76 | `src/orchestrator/exec/evidence_store.py` | F | PEP store | P01 mediated |
| 78 | `src/orchestrator/capabilities/interactive_shell/listener_manager.py` | N | Broker-exclusive listener provisioning | P13 mediated |
| 79 | `src/orchestrator/capabilities/interactive_shell/reverse_shell.py` | N | Gated ctors (:444/445 payload-string literals) | P13 mediated |
| 80 | `src/orchestrator/capabilities/interactive_shell/session.py` | F | Broker-held session persistence | P13 mediated |
| 81 | `src/orchestrator/capabilities/interactive_shell/ssh_shell.py` | N | Gated ctors (paramiko) | P13 mediated |

## D. Reachable, no executable effect (traced notes, no weld)

| # | File | Cats | Why no weld | Disp |
|---|---|---|---|---|
| 82 | `src/orchestrator/agents/skill_agent.py` | P | `import subprocess` never used (dead import) | P17 note |
| 83 | `src/orchestrator/cloud_abuse/api_gateway_exploit.py` | N | imports unused (no calls) | P17 note |
| 85 | `src/orchestrator/sandbox/docker_client.py` | N | `docker.from_env` use, uninvoked (session never instantiated live in-tree) | P17 note |
| 87 | `src/bridge/raphael_bridge.py` | N | dispatch file itself (httpx used by `mcp_exploit`) | P18 note |

## E. Dead — no live/service entry edge, with importer proof (29 files)

| # | File | Cats | Importer proof | Disp |
|---|---|---|---|---|
| 88 | `src/orchestrator/weaponizer/weaponizer_engine.py` | P,F | only `weaponizer/__init__` re-export | P14 dead |
| 89 | `src/orchestrator/student/scihub.py` | N,P,F | none | P24 dead |
| 90 | `src/orchestrator/propagation/propagation_engine.py` | P | none | P24 dead |
| 91 | `src/orchestrator/reversing/binary_analyzer.py` | P,F,N | none (283 detector-string literal) | P24 dead |
| 92 | `src/orchestrator/survivability/survivability_engine.py` | N,P,F | only `survivability/__init__` | P24 dead |
| 93 | `src/agent/dependency_check.py` | P | none, no `__main__` | P24 dead |
| 94 | `src/agent/modules/executor.py` | P | none (SUB-12 orphan; implant never imports it) | P24 dead |
| 95 | `src/agent/modules/cleanup.py` | P,F | none, no `__main__` | P24 dead |
| 96 | `src/agent/audit.py` | P,F | none (`agent.agent` imports `agent.modules.audit`, a different file) | P24 dead |
| 97 | `src/orchestrator/mesh/mesh_engine.py` | N | none | P24 dead |
| 98 | `src/orchestrator/nvidia_provider.py` | N | none | P24 dead |
| 99 | `src/orchestrator/tactics/anonymous_ttp.py` | N | none | P24 dead |
| 100 | `src/orchestrator/utils/retry.py` | N | none (import-only httpx) | P24 dead |
| 101 | `src/orchestrator/brain/waf_detector.py` | N | none | P24 dead |
| 102 | `src/raphael/scripts/blind_probe_runner.py` | N | none | P24 dead |
| 103 | `src/orchestrator/social/social_engine.py` | N,F | only `social/__init__` (pkg unimported) | P24 dead |
| 104 | `src/orchestrator/privesc/privesc_engine.py` | N,P | only `privesc/__init__` (pkg unimported) | P24 dead |
| 105 | `src/orchestrator/modes/postmortem.py` | F | `modes/__init__` side-effect import only; `handle()` zero callers | P24 dead |
| 106 | `src/orchestrator/ad/hashcat_wrapper.py` | F | `ad/planner.py` only (planner unimported) | P24 dead |
| 107 | `src/orchestrator/webhook.py` | N | `api/ci.py` only (router unmounted) | P24 dead |
| 108 | `src/raphael/cognitive/episodic_memory.py` | F | legacy-internal only; effects on legacy branch only (P03) | P24 dead |
| 109 | `src/raphael/cognitive/hypothesizer.py` | N | legacy-internal only | P24 dead |
| 110 | `src/raphael/cortex/hypothesizer.py` | N | WELDED: `hypothesize()` was ← planner:217,272 ← Organism.run ← legacy branch; the main.py legacy branch is DELETED (AM-4 W-15) so no live caller remains (`:62 httpx.post` effect confined to dead code; `:202` second post uninvoked) | P27 welded |
| 112 | `src/raphael/hippocampus/episode_store.py` | F | WELDED: `store()` was ← main:315 `shutdown()` ← legacy `run()`; the main.py legacy branch is DELETED (AM-4 W-15) so no live caller remains (`:75 open(w)` confined to dead code) | P27 welded |
| 113 | `src/raphael/techniques/ad1_xor_sweep.py` | F | none | P24 dead |
| 114 | `src/raphael/techniques/cmdi_check.py` | P | none (registry data-only) | P24 dead |
| 115 | `src/raphael/techniques/directory_brute.py` | P | none | P24 dead |
| 116 | `src/raphael/techniques/lfi_check.py` | P | none | P24 dead |
| 117 | `src/raphael/techniques/open_redirect.py` | P | none | P24 dead |
| 118 | `src/raphael/techniques/sqli_check.py` | P | none | P24 dead |
| 119 | `src/raphael/techniques/ssrf_check.py` | P | none | P24 dead |
| 120 | `src/raphael/techniques/subdomain_enum.py` | F,P | none (+:65 unlink) | P24 dead |
| 121 | `src/raphael/techniques/tech_detect.py` | P | none | P24 dead |
| 122 | `src/raphael/techniques/waf_detect.py` | P | none | P24 dead |
| 124 | `src/mcp-hub/tools/exploit/metasploit.py` | P,F | M-1 (dead-as-committed package) | P24 dead |
| 125 | `src/mcp-hub/tools/web/gobuster.py` | P | M-1 | P24 dead |
| 126 | `src/mcp-hub/tools/web/sqlmap.py` | P | M-1 | P24 dead |
| 127 | `src/mcp-hub/tools/web/nuclei.py` | P | M-1 | P24 dead |
| 128 | `src/mcp-hub/tools/c2/pupy.py` | P | M-1 | P24 dead |
| 129 | `src/mcp-hub/tools/recon/subfinder.py` | P | M-1 | P24 dead |
| 130 | `src/mcp-hub/tools/recon/nmap.py` | P | M-1 | P24 dead |
| 131 | `src/mcp-hub/tools/forensics/volatility.py` | P | M-1 | P24 dead |
| 132 | `src/mcp-hub/tools/cloud/prowler.py` | P | M-1 | P24 dead |
| 133 | `src/mcp-hub/core/registry.py` | F | M-1 (dead package; `open-w` registry export) | P24 dead |
| 134 | `src/mcp-hub/core/security.py` | F | M-1 (`open-a` audit log) | P24 dead |
| 135 | `src/mcp-hub/tests/test_server.py` | N | M-1 (dead-package test) | P24 dead |
| 136 | `src/orchestrator/exfil/redcloud.py` | P | `exfil/pipeline.py` only (pipeline entry-less) | P25 dead |
| 137 | `src/arena/ablation_runner.py` | F | test-harness plane (result `open-w`); zero production edges | P24 dead |
| 138 | `src/arena/d10_falsification_defeater_diagnostic.py` | F | test-harness plane | P24 dead |
| 139 | `src/arena/d11_regression_test.py` | F | test-harness plane | P24 dead |
| 140 | `src/arena/d13_diagnostic_runner.py` | F | test-harness plane | P24 dead |
| 141 | `src/arena/d16_holdout_runner.py` | F | test-harness plane | P24 dead |
| 142 | `src/arena/d6_manifest.py` | F | test-harness plane | P24 dead |
| 143 | `src/arena/d7_r1_gemma_retest.py` | F | test-harness plane | P24 dead |
| 144 | `src/arena/d9_regression_test.py` | F | test-harness plane | P24 dead |
| 145 | `src/arena/diagnostic.py` | F | test-harness plane | P24 dead |
| 146 | `src/arena/llm_service.py` | N | test-harness plane (requests) | P24 dead |
| 147 | `src/arena/llm_transport.py` | N | test-harness plane (requests) | P24 dead |
| 155 | `src/orchestrator/cicd/pipeline_poisoner.py` | F | :434 `write_text`; :494,:562,:606 `write_bytes`; :610 `unlink` (001R4 lexicon) | cicd_executor (live) | P07 welded |
| 156 | `src/orchestrator/exfil/smtp_tunnel.py` | N | `import smtplib` + :37,:40 `SMTP` (exfil MTA client) | sword phase_4 ← sword/api | P23 welded |
| 157 | `src/phishing/main.py` | F | :208 `write_text` (campaign template upload) | own FastAPI service | P23 welded |
| 158 | `src/sword/phase_5_phish.py` | F | :140 `write_text` (template creation) | sword pipeline ← sword/api | P23 welded |
| 159 | `src/orchestrator/egress/tls_manager.py` | F | :47,:52,:86,:91 `write_bytes` (key/cert material) BUT zero importers | none (dead) | P24 dead |
| 160 | `src/orchestrator/checkpoint.py` | F | :18 `write_text`; zero importers (llm's guarded import targets nonexistent `checkpoint.checkpoint_manager` package) | none (dead) | P24 dead |
| 161 | `src/raphael/exploit_factory/payload_templates.py` | F | :248 `write_text` (rendered payload to file; :154 Popen-tuple is a literal) | factory `__main__` CLI | P23 welded |
| 162 | `src/orchestrator/cloud_abuse/iam_pathfinder.py` | N | :269 `boto3.client("iam")` (guarded :27 import + single construction use; no Session/resource forms in-tree) | cloud_executor (live) | P07 welded |
| 163 | `src/raphael/techniques/fast_port_scan.py` | N | `asyncio.open_connection` port scan; runnable `__main__` argparse CLI (registry template + comment are NOT imports — but the CLI entry is real, so P23 not P24) | own CLI entry | P23 welded |
| 164 | `src/raphael/eventbus/core.py` | N | :154 `redis.from_url` (via `import redis.asyncio as redis` alias); :160/:661 `ping`; :328 `pipeline`; :302/:565/:336/:353/:355 `xadd` (incl. `pipe` via BoolOp-or + `self.redis` @property single-hop); full stream-op set (`xreadgroup`/`xack`/`xdel`/`xtrim`/`xrange`/`xinfo_*`/`xpending_*`/`xclaim`/`xgroup_*`/`scan_iter`/`close`/`info`/`execute`) — 33 findings, all receiver-proven. `redis.ResponseError/ConnectionError` except-attrs + `redis.Redis` annotation do NOT flag. Zero live-real drivers (harness pre-seeds FakeAsyncRedis so :114 `connect()` returns early; test mocks; planner/contracts wiring never constructed live with a real bus; vhost stores-but-never-uses) | none live (harness fake; mocks; dead planes) | P24 dead |
| 148 | `src/arena/d10_regression_test.py` | F | test-harness plane (result `open-w`) | P24 dead |
| 149 | `src/raphael/executor/kali_bridge.py` | N | WELDED: `run()` was ← `Executor.execute` ← legacy run loop (:228); the main.py legacy branch is DELETED (AM-4 W-15) and `run()` itself proposes to the Broker first (fail-closed WeldNotAuthorized) — httpx attempt unreachable without AUTHORIZED | P27 welded |
| 150 | `src/orchestrator/exec/artifact_store.py` | F | zero production importers (unused PEP store) | P24 dead |
| 151 | `src/orchestrator/exec/receipt_store.py` | F | zero production importers (unused PEP store) | P24 dead |

M-1 (mcp-hub dead-as-committed): hyphen dir vs `mcp_hub.*` imports
(`ModuleNotFoundError` reproduced in `raw/`); unresolvable absolute `tools.*` dynamic
load; nonexistent `config.paths` import; no `__main__` in tool files. Resurrect → W-14.

**Reconciliation:** 150/150 effect files in numbered rows above (gaps #13,#44,#45,#68,
#70,#84,#86,#111,#123 are non-census conduits/notes in §F). Dispositions: welded 78 files ·
mediated 6 · reachable notes 4 (skill_agent, api_gateway, docker_client, bridge) ·
dead 62 (P14:1 · P24:60 · P25:1). No unaccounted effect-bearing files remain.
(AM-4: all 15 WELD_SET paths welded; former not-yet rows now read `Pxx welded`.)

## F. Conduits & non-census notes (no lexicon hit — not counted in the 150)

- `src/orchestrator/scanners/pipeline.py` — conduit for P19 (scan mode ← bridge).
- `src/orchestrator/exploit/pipeline.py` — conduit for P18 (mcp_bridge ← bridge).
- `src/orchestrator/postex/pipeline.py` — conduit for P23 (cai-service entry).
- `src/orchestrator/sandbox/session_manager.py` — conduit; docker exec never invoked with
  a live session in-tree (pipelines default `sandbox=None`) — P17 note.
- `src/orchestrator/brain/phases/models.py` — 9 stub executors (P26) + 4 lazy real
  (P07/P09); phase table in CLASSIFICATION.md §4.
- `src/raphael/cortex/planner.py` — legacy-internal invoked dispatcher (calls hypothesizer
  :217,272 and model_refiner), no lexicon hit (P27-adjacent conduit).
- `src/raphael/techniques/payloads/fabric.py` — literal-only SSTI list, no lexicon hit,
  zero importers (P24-adjacent).

## G. Residual lexicon boundary (explicitly out of census — Q1/Q2/Q3 CLOSED by GLM,
see `EFFECT_SCOPE_RULING_REQUEST.md` §4 and `GLM_GOVERNANCE_VERDICT.md`; no longer
"owed", recorded as decided: reads OUT, mkdir OUT, dual-layer bounded model)

No lexicon hit, hence no row, by construction (minimal 001R4 change):
- `Path.mkdir` / `os.mkdir` / `os.makedirs` (no governed equivalent; `mkdir` creation
  effects in checkpoint/phishing/tls_manager ride their rows' other hits where present).
- `open()`-read / `Path.read_text` / `json.load` (reads; doctrine is file-MUTATION).
- `email.mime` (message construction, no I/O), `ssl` contexts (handshake inside
  smtplib/urllib use), `sqlite3` (session/audit persistence noted in path traces),
  `shutil.which` (read-only lookup), `tempfile` (scoped temp files).
- `src/orchestrator/exfil/smtp_tunnel.py` — NOW CENSUS ROW #149 (001R4 `smtplib`).
- `src/orchestrator/cicd/pipeline_poisoner.py` — NOW CENSUS ROW #148 (001R4
  `write_text`/`write_bytes`/`unlink`; :203/:205 remain payload-string literals).
- `src/raphael/exploit_factory/payload_templates.py` — NOW CENSUS ROW #154 (001R4:
  real `:248 write_text`; the :154 Popen-tuple remains a literal).
