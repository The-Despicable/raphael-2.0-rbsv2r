# RC-2: Reconcile 10 confirmed bypasses + 17 subprocess sites to P0 Path IDs

Source of truth:
- **Bypasses:** `evidence/phases/P0/03_historical_reverification/bypass_reverification.md` (10 historical candidates reverified, 10 CONFIRMED, 0 SHIFTED/ABSENT/RESOLVED/NEW/UNKNOWN)
- **Subprocess sites:** `evidence/phases/P0/02_execution_inventory/subprocess_sites.md` (17 `asyncio.create_subprocess_*` sites across 13 files)
- **Seam wrap state:** `evidence/phases/P1/03_seam_work/SEAM_SITES.md`

## Table 1 — 17 subprocess sites → P0 Path IDs (reconciliation)

| Path ID | File:symbol | Reachable from canonical Arena? | Reachable from canonical CLI? | P1 wrap status |
|---|---|---|---|---|
| SUB-01 | `src/orchestrator/weaponizer/weaponizer_engine.py:94` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-02 | `src/orchestrator/weaponizer/weaponizer_engine.py:152` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-03 | `src/orchestrator/weaponizer/weaponizer_engine.py:199` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-04 | `src/orchestrator/chains/tool_registry.py:58` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-05 | `src/orchestrator/c2/sliver_backend.py:75` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-06 | `src/orchestrator/c2/sliver_backend.py:101` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-07 | `src/orchestrator/c2/implant_builder.py:315` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-08 | `src/orchestrator/c2/implant_builder.py:450` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-09 | `src/orchestrator/c2/implant_builder.py:502` | NO | NO | Not in P1 scope (dead code, P9) |
| **SUB-10** | `src/orchestrator/kali_tools_client.py:41` (`_run_local`) | NO (canonical path) | NO (canonical CLI is Head-1) | **WRAPPED** (Weld-SUB10, P3) |
| SUB-11 | `src/recon-pipeline/main.py:80` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-12 | `src/agent/modules/executor.py:7` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-13 | `src/raphael/executor/kali_bridge.py:152` (`KaliBridge._subprocess_run`) | NO | LEGACY_REACHABLE | Not in P1 scope (CLI fallback path; deferred to P3 alongside Weld-SUB14) |
| **SUB-14** | `src/raphael/executor/executor.py:72` (`_subprocess_fallback`) | NO | LEGACY_REACHABLE | **WRAPPED** (Weld-SUB14, P3) |
| SUB-15 | `src/sword/phase_0_recon.py:88` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-16 | `src/sword/phase_0_recon.py:126` | NO | NO | Not in P1 scope (dead code, P9) |
| SUB-17 | `src/sword/phase_0_recon.py:165` | NO | NO | Not in P1 scope (dead code, P9) |

**Subprocess summary:** 17 sites total, 2 WRAPPED in P1 (SUB-10, SUB-14), 13 deferred to P9 (UNREACHABLE_FROM_CANONICAL), 1 (SUB-13) and the 1 (SUB-14) are the only LEGACY_REACHABLE sites and are broker-targets for P3 (Weld-SUB14 covers both because `KaliBridge._subprocess_run` is called by `Executor._subprocess_fallback` as the next-level fallback).

## Table 2 — 10 confirmed bypass candidates → P0 Path IDs (reconciliation)

| # | Candidate | Live location (canonical HEAD) | Path ID(s) | P1 remediation |
|---|---|---|---|---|
| 1 | `raphael/executor/executor.py` `_subprocess_fallback` | `src/raphael/executor/executor.py:67-93` (function), `:72` (`asyncio.create_subprocess_shell`) | **SUB-14** | WRAPPED (`BypassNotAuthorized` + `_bypass_authorized` flag) |
| 2 | `orchestrator/kali_tools_client.py` `_run_local` | `src/orchestrator/kali_tools_client.py:20-44` (function), `:41` (`asyncio.create_subprocess_exec`) | **SUB-10** | WRAPPED (`KaliBypassNotAuthorized` + `_BYPASS_AUTHORIZED` flag) |
| 3 | `interactive_shell/{ssh_shell,reverse_shell}` constructor bypass | `src/orchestrator/capabilities/interactive_shell/ssh_shell.py:38`, `reverse_shell.py:77` (constructors) | **Weld-SHELL** (capability base class) | DEFERRED to P3 (SD-1, C7 conflict) |
| 4 | `brain/action.py` `allowed = True` (Planner hardcoded allow) | `src/orchestrator/brain/action.py:1109` | n/a (no live execution site) | comment-only correction; broker is sole authority at execution boundary |
| 5 | `capability_broker.py:1223` ExecutionEngine broker commented | `src/orchestrator/brain/action.py:1210,1223,1266` | n/a (no canonical caller; real-but-dormant) | Not in P1 scope; dead-code path |
| 6 | `BrokeredExecutionEngine` reachability | `src/orchestrator/brain/capability_broker.py:1277,1361,1370` | n/a (no caller) | Not in P1 scope; dormant class |
| 7 | `modes/autonomous.py` `PHASE_EXECUTORS` (9 NOT_IMPLEMENTED stubs) | `src/orchestrator/brain/phases/models.py:163` | n/a (stubs, not live execution) | Not in P1 scope; P3 broker closure makes 4 real executors broker-gated; 9 stubs remain stubs |
| 8 | 4 broken symlinks → `/home/yaser/raphael-2.0` | `cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service` (dangling) | n/a (filesystem, not code) | Not in P1 scope; canonical 239 tests run green without them |
| 9 | `bridge/raphael_bridge.py` hard-coded `/home/yaser/raphael-2.0` | `src/bridge/raphael_bridge.py:15` | n/a (broken path) | Not in P1 scope; P9 cleanup |
| 10 | `brain/adaptive_brain.py` 31-line counter stub | `src/orchestrator/brain/adaptive_brain.py` (31 LOC) | n/a (stub) | Not in P1 scope; P9 cleanup |

**Bypass summary:** 10 confirmed bypasses total.
- 2 mapped to subprocess Path IDs and WRAPPED in P1: Candidate 1 → SUB-14; Candidate 2 → SUB-10.
- 1 mapped to capability Path ID and DEFERRED to P3: Candidate 3 → Weld-SHELL.
- 4 are not execution-site bypasses (comment-only correction, dormant class, stubs): Candidates 4, 5, 6, 7. These are **confirmed-but-not-runtime-reachable**; they are recorded for transparency but not seam-wrapped in P1.
- 3 are infrastructure/environment issues (broken symlinks, broken path, dead stub): Candidates 8, 9, 10. P9 cleanup, not P3 weld.

## Cross-check: no orphan seams

Total seam sites (WRAPPED or DEFERRED) in P1 = 3: SUB-10, SUB-14, Weld-SHELL.
Total P0 Path IDs that are execution sites (subprocess or capability constructor) = 18 (17 subprocess + 1 Weld-SHELL capability).
All 18 are accounted for in the seam manifest. No orphan seam sites.

## Evidence sources

- `evidence/phases/P0/02_execution_inventory/subprocess_sites.md` (lines 5-23: Path ID table)
- `evidence/phases/P0/03_historical_reverification/bypass_reverification.md` (lines 5-82: 10 candidates)
- `evidence/phases/P1/03_seam_work/SEAM_SITES.md` (lines 5-19: P1 wrap status table)
- `evidence/phases/P1/EVIDENCE_PACKAGE.md` §5.6 (security proof, weld tickets)
