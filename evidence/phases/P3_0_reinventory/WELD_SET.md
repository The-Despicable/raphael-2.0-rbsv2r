# P3.0 Re-inventory — AM-4 Weld Set (001R3, authoritative)

**Source:** `CLASSIFICATION.md` rows labeled `welded` (AM-4; pre-weld label
`not-yet-mediated`, 15 paths).
**Rule:** G3 does not pass while any path below remains un-welded (AM-4 §3).
"Welding closed" = seam fixed ON for that call path (permanently routed through Broker/PEP)
AND the legacy branch at that call site deleted, under a named versioned policy artifact.
**Non-goals here:** no welding performed; SHELL (P13, live-test gated) and welded stubs
(P03/P15) and dead paths (P14/P17/P21/P22/P24/P25/P26) are NOT in this set.
**Completeness:** every bridge method (40), API route (27), PHASE_EXECUTORS phase (13),
and effect file (150) reconciled in `CLASSIFICATION.md`/`CENSUS.md`; this set equals the
welded set exactly (asserted by probe + guardrail).

**AM-4 STATUS (reconciled 2026-10-09):** all 15 weld items carry a recorded `WELDED (gate…)`
claim from the implementing agent. **This is an engineering claim, not an AM-4-R3 execution
record and not a G3 gate acceptance.** The P9 deletion ruling for gated library code remains
owed (D-1). See "Post-weld status" below for the state-by-state reading guide.

**Open cross-document inconsistency, NOT resolved here — arithmetic reconciles, security
classification does not.** The 150-file effect census decomposes as
**150 = 78 + 6 + 4 + 62** (78 / 6 mediated / 4 reachable notes / 62 dead), and **the totals
reconcile across every artifact that records them**. What does **not** reconcile is the
*security classification of the first bucket*:

- this file's `U-3` (below) records those 78 files as **welded** — "the 78 formerly
  not-yet files now read `Pxx welded`";
- `evidence/g3_remediation/F2_PERIMETER_RECORD.md` (001R6) still presents the same 78 files in
  the **not-yet-mediated** column of the 150-file census;
- `reports/product-readiness/RAPHAEL_PRODUCT_READINESS_2026-10-09.md:267,567` records the same
  bucket as "**78 not-yet-mediated**", and `:168` lists it as an open **G9** item
  ("≈78 not-yet-mediated files still present").

**Arithmetic agreement is not Broker-mediation evidence.** The buckets sum to 150 in every
source, but that the counts *add up* says nothing about whether those 78 files are welded.
The same 78 files are described as welded in one artifact and as unmediated in others; only
architecture authority can settle which is true. This reconciliation therefore
**does not decide the 78-file question, does not execute or reconstruct AM-4-R3, does not
accept G3, and does not authorize P4/RSI implementation.** It is referred to the architecture
authority as part of the G3 adjudication. The claim itself is preserved unchanged at `U-3` and
is flagged as disputed, not overwritten.

## Weld set (15)

| Weld item | Path | Call site(s) to weld |
|---|---|---|
| W-01 | R3.0-P04 | `api/tools.py:159 execute_tool` + 3 convenience endpoints → `chains/tool_registry.py:57-115 _run_command`; shared sink `audit_trail` append |
| W-02 | R3.0-P05 | `api/tools_bridge.py:133 run_nmap`, `:156 run_recon` (add auth) + kali-tools hop; shared sink `audit_trail` |
| W-03 | R3.0-P06 | `api/agent.py:43,176` → `agents/engage` fan-out: `scanners/*` (nmap sockets, nuclei/whatweb httpx), `ad/*` → `kali.run`; PostEx `winrm` (httpx exec) + `ladon` (sockets); shared sink `audit_trail` |
| W-04 | R3.0-P07 | `api/ci.py:146` (unmounted; weld the handler) → `autonomous.handle` → 13 `PHASE_EXECUTORS` (9 stubs → P26; `cicd` executor urllib + `token_harvester` + runner ssh recon + poisoner workflow writes; `ml_attack` pickle test-exec + `hf_hub` downloads; `cloud_abuse` socket/metadata network + `iam_pathfinder` boto3 enum; `container_escape` file/socket reads + `sandbox_detection`) + spray/ad-chain (`toolkit` httpx); shared sink `audit_trail` |
| W-05 | R3.0-P08 | `api/ci.py:181` + queued `/engage` → engage/autonomous sinks (with P22 queue wiring) |
| W-06 | R3.0-P09 | `bridge:119 mode_autonomous` → `autonomous.handle` → chains → `kali.run` / `get_c2()` (+ `docker/k8s_escape` reads) |
| W-07 | R3.0-P10 | `bridge kali.*` (6) → `KaliToolsClient.run` remote branch (httpx) |
| W-08 | R3.0-P11 | `bridge c2.*` (5) + chains/spray → `c2/manager` → sliver/native (`beacon` aiohttp server, `dga` sockets) / `implant_builder` (SUB-05…09 + `:599 shell=True`) |
| W-09 | R3.0-P12 | `kali-tools/server.py:19 POST /run` → `:23 subprocess.run` (authenticate + broker-gate or isolate; shared sink) |
| W-10 | R3.0-P16 | `ExploitAgent.execute`: `custom_payload` → `orchestrator/sandbox/__init__.py` `run_code` (arbitrary-code sink); `relay_chain`/`ad_kill_chain`/`llm_exploit`/`ssrf`/`xss`/`nuclei` tools (shared sinks P09/P18/P06) |
| W-11 | R3.0-P18 | `bridge exploit.*` (4 live): `llm_exploit_engine` (kali+LLM), `relay_chain` (socket RCE relay), `MCPBridge` listener (127.0.0.1:port, no auth) + `ExploitPipeline` (`sqlmap_wrapper` httpx, ssrf/nettacker), httpx `mcp_exploit` |
| W-12 | R3.0-P19 | `bridge mode.*` (5): community/debate/deep_research/scan/student — unbrokered LLM (`providers` aiohttp) / OSINT / socket-scan / kali-whatweb emission + `research_scheduler` httpx + `proxy_guard` verify (incl. `--direct`/`RAPHAEL_DEV_MODE` bypasses, student `proposal_only` + unbrokered profile) |
| W-13 | R3.0-P20 | `bridge harvester.*` (3, sqlite+httpx feeds), `model.call` (`providers` LLM APIs), `target.profile` (direct nmap subprocess) |
| W-14 | R3.0-P23 | Standalone service entries (31 census files: mhddos, recon-pipeline, sword/api+`phase_0`+`phase_1`+`report`+`bulk`/`dns`/`bounceback`+`smtp_tunnel`+`phase_5`, agent implant+5 modules+`modules/audit`+`egress`, phishing/main+evilginx+set+gophish, cloak×2, cai-service conduits, factory delivery+templates+vhost-enum, verifier channels+core, techniques `fast_port_scan` CLI). **Weld-or-P9-delete decision owed** (see below). |
| W-15 | R3.0-P27 | E-CLI-LEGACY (`RAPHAEL_USE_LEGACY=1`): planner → `cortex/hypothesizer.hypothesize` → unbrokered LLM post; `Executor` → `KaliBridge.run` → unbrokered httpx attempt (fail-closed); `shutdown()` → `hippocampus.store` → episode file write. Weld-or-delete the branch with its effects (P03 keeps the welded-subprocess record). |

## Post-weld status (AM-4)

> ### Reconciliation note — 2026-10-09 (G3 remediation task, engineering)
>
> This section previously appeared **twice**: a superseded copy followed by the current one.
> The superseded copy claimed `(26 tests)` and carried an **empty** status table; the current
> copy claims `(47 tests)` and carries the populated table. The stale copy has been removed
> here. The superseded text is not erased from the record — it remains in this file's git
> history (`git log -p -- evidence/phases/P3_0_reinventory/WELD_SET.md`).
>
> **Test-inventory count, reproduced:** `tests/test_am4_weld_gates.py` contains **47** test
> functions at this revision. `PROVEN` by static count.
>
> ### Reading the "WELDED" status correctly
>
> `WELDED` in the table below is an **engineering claim recorded by the implementing agent**.
> It is **not** a gate acceptance. The five distinct states below must not be collapsed:
>
> | State | Status at this revision | Label |
> |---|---|---|
> | Gate/deletion **code present** at the named call sites | recorded per item below | `REPORTED` |
> | Test **functions present** in `tests/test_am4_weld_gates.py` | 47 functions present | `PROVEN` (static count only) |
> | Tests **executed and passing** at this revision | not reproduced by the 2026-10-09 remediation task | `UNKNOWN` |
> | **Independent review** of the weld set (roadmap §14.12) | not performed; no GLM ruling artifact exists | `UNKNOWN` |
> | **Roadmap gate G3** | **NOT ACCEPTED** — see `evidence/g3_remediation/STATUS.md:17,54` and roadmap Appendix D | `PROVEN` (absence of ruling) |
>
> A count of 47 test functions is evidence that tests *exist*. It is **not** evidence that 47
> tests ran, that they passed, or that anyone reviewed them.

Weld mechanism (uniform, ADR-012): seam fixed ON via `enforce_broker_mediation`

Weld mechanism (uniform, ADR-012): seam fixed ON via `enforce_broker_mediation`
(`src/orchestrator/auth.py` — propose to the canonical Broker built by the
bootstrap-v0 factory; proceed iff AUTHORIZED; fail-closed WeldNotAuthorized
otherwise) + legacy execution branches DELETED at the welded call sites
(AM-4-R2). Named policy artifact: `policies/bootstrap-v0.json` via
`make_broker_from_bootstrap` (canonical PDP factory, CONV-1); Scope v0 governs
the canonical mission path. Under current policy all weld classes DENY
(verified live); the canonical fixture capability still AUTHORIZEs (gate is
not blanket-deny). Denial + deletion proofs per item in
`tests/test_am4_weld_gates.py` (47 tests). No second PDP/Runtime/loop/sandbox;
no OFF switch; imports retained (census rows stable at 150).

| Item | Path | Status | Weld evidence |
|---|---|---|---|
| W-01 | R3.0-P04 | WELDED (gate + deletion) | `tool_registry._run_command` subprocess body DELETED (gate + raise); `execute_tool` route + dispatcher `require`/`enforce` (403) |
| W-02 | R3.0-P05 | WELDED (gate) | `_run_in_kali` gated (covers both no-auth routes); httpx hop retained behind gate (shared lib, P9 domain) |
| W-03 | R3.0-P06 | WELDED (gate) | `run_agent_engage` gated + both `/execute` routes gated; fan-out inherits |
| W-04 | R3.0-P07 | WELDED (gate) | `autonomous.handle` gated (covers ci `/scan` + phase executors); ci route gated |
| W-05 | R3.0-P08 | WELDED (gate) | `run_agent_engage` gated (covers ci `/agent-engage`); ci route gated; queue untouched (no effect) |
| W-06 | R3.0-P09 | WELDED (gate) | bridge `mode.autonomous` in `_WELD_BRIDGE_METHODS` + `autonomous.handle` gated |
| W-07 | R3.0-P10 | WELDED (gate + deletion) | `KaliToolsClient.run` httpx body DELETED (gate + raise) + 6 `kali.*` bridge methods gated |
| W-08 | R3.0-P11 | WELDED (gate + deletion) | 5 `c2.*` bridge methods gated + `implant_builder.build` dispatch DELETED + sliver `generate_implant`/`_import_config` bodies DELETED + `beacon.start` bind DELETED + sliver/deploy/cleanup/dga helpers gated; `_build_*` leaves retained as dead code (P9) |
| W-09 | R3.0-P12 | WELDED (gate + deletion) | kali-tools `/run` subprocess body DELETED (gate + 403); sys.path bootstrap + hard orchestrator import |
| W-10 | R3.0-P16 | WELDED (gate + deletion) | `ExploitAgent.execute` dispatcher gated + `sandbox.run_code` body DELETED (gate + raise) |
| W-11 | R3.0-P18 | WELDED (gate + deletion) | 4 `exploit.*` bridge methods gated; `relay_chain.execute_chain` + `mcp_bridge.start` bodies DELETED (gate + raise); engines inherit (only bridge/mcp callers) |
| W-12 | R3.0-P19 | WELDED (gate) | 5 `mode.*` bridge methods gated + `scan.handle` (__main__ --direct), `student.handle`, `providers.call_model` gated (delegation bodies; no direct-hit statements to delete) |
| W-13 | R3.0-P20 | WELDED (gate) | 3 `harvester.*` + `model.call` + `target.profile` bridge methods gated + `run_full_cycle`/`search`/`run_continuous`/`profile_target`/`_nmap_scan` gated (delegation bodies) |
| W-14 | R3.0-P23 | WELDED (gate + deletion; P9-delete ruling still owed) | per-route matrix below: 5 named ungated routes repaired (3 gated + 2 branch-deleted); execution bodies deleted at mhddos rotate/attack, cloak helpers, agent exec/uninstall branches, recon subfinder, phishing status paths gated; W-14 libraries retained behind gates (P9 domain) |
| W-15 | R3.0-P27 | WELDED (branch deleted) | main.py legacy branch DELETED (canonical Runtime only) + `KaliBridge.run` gated; residual effects dead-code-confined |

Remaining not-yet paths: none (0). Remaining WELD_SET members: 15/15 with a recorded
`WELDED (gate …)` claim.

**Two separate obligations must not be conflated.** *Welding* (route every governed
primitive at these call sites through the Broker and delete the legacy unconditional
branch) is claimed complete for all 15. *Deletion of the now-gated library code behind those
gates* is owned by **P9** and is **still owed** — recorded as D-1 below and in the W-14 row.
The previous single-phrase summary "ALL 15 WELDED" did not distinguish these, which is how a
"ruling still owed" row sat under an apparently unconditional header. Both statements are
retained above rather than reconciled away: the weld claim and the outstanding P9 deletion
ruling are independent obligations with different owners.

### W-14 route matrix (AM-4-R2 source audit; governed primitives only)

Columns: route · entry symbol · governed primitive · gate · canonical PEP/owner ·
deletion/replacement status · result.

mhddos-service/main.py:
- `POST /attack` → `launch_attack` → `subprocess.Popen` → route gate (403) → none (no PEP owner; deny under policy) → `run_real` Popen block DELETED (gate + raise) → WELDED
- `POST /proxy/rotate` → `rotate_proxy` → `socket.socket/connect/sendall` → route gate (403) added AM-4-R2 → raw-socket fallback block DELETED → WELDED
- `POST /stop` → `stop_attack` → `os.kill` (NOT governed: closed lexicon has no os.kill; Q3) → none required → CLEAN (documented out-of-lexicon)
- `GET /status`, `GET /` → dict reads → none required → CLEAN
recon-pipeline/main.py:
- `POST /recon/run` → `recon_run` → via `run_recon_chain` (exec) → route + chain gates (403) → chain bodies retained behind gates (shared fns; P9) → WELDED
- `POST /recon/deep` → `recon_deep` → via `run_deep_recon` → route + chain gates → WELDED
- `run_subfinder` (helper) → `asyncio.create_subprocess_exec` → helper gate added AM-4-R2 → WELDED
- `GET /health` → `check_tool` (`shutil.which`) + `.available` constants → no governed effect → CLEAN
- `GET /recon/status/{id}` → dict read → CLEAN
sword/api.py:
- `POST /sword/run` → `sword_run` → `run_sword` pipeline (gated choke) → route gate (403) → WELDED
- `GET /sword/health` → `health` → `os.popen` → route gate ADDED AM-4-R2; primitive RETAINED (deletion would drop CENSUS row #48 → forbidden census change; §2-deferred with rationale in source) → WELDED (gated; deletion deferred, Lead decision point)
- `POST /sword/report` → `generate_report` → pure markdown/html compute (writes only in `save()`, called solely from gated `sword_run`) → CLEAN (no governed effect on route)
- `GET /` → static → CLEAN
agent/agent.py:
- `__main__` implant loop → `main` → gate (denial) → WELDED
- `execute_task` (internal dispatcher) → `subprocess.run(shell=True)` + `shutil.rmtree` + installers → gate ADDED AM-4 + exec/uninstall branch BODIES DELETED → WELDED
- `heartbeat`/`register`/`submit_result` (httpx transport, called only from gated `main`) → covered-by-entry, same-process → WELDED (no independent entry)
cloak-service/main.py:
- `POST /browse`, `/screenshot`, `/interact` → gates (403) → WELDED
- `GET /identities` → `get_tor_ip` + `rotate_tor_identity` → route gate ADDED AM-4-R2 → WELDED
- `GET /health` → `get_tor_ip` DELETED from body (liveness-only now; no governed effect) → WELDED (branch deleted)
- helpers `get_tor_ip`/`rotate_tor_identity` → bodies DELETED (gate + raise) → WELDED
phishing/main.py:
- 6 effect routes (`/campaign/*`, `/evilginx/deploy`, `/set/*`, `/template/create`) → gates (403) → WELDED
- `GET /`, `GET /health` → `.status()` probes (`subprocess.run`, urllib) → gates ADDED AM-4-R2 → WELDED
- `GET /campaign/*/results`, `/templates` → dict/glob reads → CLEAN
cai-service/main.py (8 routes):
- `/agent/scan`, `/agent/exploit`, `/agent/forensic`, `/agent/audit` → gated sinks (scanners/pipelines) → inherit → WELDED
- `/agent/chat` → `call_model` (gated sink) → inherit → WELDED
- `/agent/recon` → karma/spiderfoot STUB wrappers (zero lexicon hits) → CLEAN (nothing to weld)
- `/agent/defend` → nonexistent `SastPipeline` (ImportError → error dict) → CLEAN
- `/agent/oracle` → `PayloadsDB` sqlite read (Q1-OUT) → CLEAN
factory/verifier/fast_port_scan CLIs → gates (denial) → WELDED
Shared W-14 libraries (agent modules, exfil tunnels, phishing libs, delivery,
enumerators, channels, verifier/core, sword phases, bulk/dns/bounceback/smtp,
egress/router, cloakbrowser, payload_templates): reachable ONLY via gated
entries (importer-verified); retained as dead code for owed P9 deletion (D-1).
No independent production entry → WELDED (covered-by-entry; P9 owns removal).

## Explicitly NOT in the weld set

- P01/P02 (control), P13 (SHELL, live-test gated), P03/P15 (welded stubs).
- P17 (reachable but no executable effect — import-only `skill_agent`/`api_gateway`, uninvoked `docker_client`, stubs/shims; nothing to weld).
- P21 (session sqlite CRUD — no lexicon effect).
- P22 (ci router unmounted + write-only queue — wire-or-remove decision, not a weld).
- P14/P24/P25 (dead — P9 deletion candidates after zero-reference proof).
- P26 (phase stubs — P5 implement-or-delete, no effect to weld).

## Decisions owed — RESOLVED as classified (001R2)

- D-1: W-14 WELDED (gated; per-service traces in P23); the mcp-hub portion is
  PROVEN dead-as-committed (CENSUS M-1, `ModuleNotFoundError` reproduced) and sits in P24,
  not W-14. The gated W-14 code is preserved (no deletion) — the Lead's delete ruling
  (Task 002) + P9 zero-reference/deployment proofs remain owed — recorded, not silent.
- D-2: RESOLVED — pickle file-writes ride the phase-executor welds (W-04/W-06,
  P07/P09 rows); poisoner workflow writes + templates render-write are census rows
  (W-04/W-14) under the extended lexicon; recorded as file-write terminals.
- D-3: RESOLVED — brokered helper proven gated but unreachable without a caller broker
  (bridge passes none); live student path is `proposal_only` + unbrokered profile (P19).
  No action unless a caller is wired.

## Uncertainty retained

- U-1 RESOLVED (P22): queue is write-only; consumers have zero callers.
- U-2 RESOLVED (P21): session plane is sqlite-only, zero lexicon hits.
- U-3 RESOLVED (CENSUS.md): full 150-file effect census reconciled (78 welded files ·
  6 mediated · 4 reachable notes · 62 dead). Bare-import files without effectful use
  (`ladon` has socket use → P06; true import-only files → P17 note/P24).
  (AM-4 note: the 78 formerly not-yet files now read `Pxx welded`.)
  > **DISPUTED CLASSIFICATION — the arithmetic above reconciles; the "welded" label on the 78
  > does not.** 78 + 6 + 4 + 62 = 150, and that total is consistent across artifacts. But the
  > first bucket is labelled **welded** here and **not-yet-mediated** in
  > `evidence/g3_remediation/F2_PERIMETER_RECORD.md` (001R6) and in
  > `reports/product-readiness/RAPHAEL_PRODUCT_READINESS_2026-10-09.md:267` (`:168` lists it as
  > an open G9 item). **A count that adds up is not evidence that the files are
  > Broker-mediated.** The text above is preserved verbatim and is **not** corrected here:
  > resolving it by inference would manufacture provenance. This note records the dispute and
  > refers it to architecture authority; it does not decide it.

> **Amendment 2026-10-04 (M0-A):** the former sibling module `src/orchestrator/sandbox.py` was permanently shadowed by the `orchestrator/sandbox/` package and broke 14 imports; its `PatchSandbox`/W-10 definition was merged into `src/orchestrator/sandbox/__init__.py` and the shadow file removed. Paths above updated accordingly; W-10 gate semantics unchanged (fail-closed stub, see tests/test_m0_clean_floor.py).
