# P3.0 Re-inventory — P0 Diff (post-P2 inventory vs P0 inventory)

**P0 baseline:** `evidence/phases/P0/02_execution_inventory/execution_paths.md` (157 lines) +
`subprocess_sites.md` (48 lines) at canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
(17 `asyncio.create_subprocess_*` sites SUB-01…SUB-17 across 13 files; 2 LEGACY_REACHABLE,
15 UNREACHABLE_FROM_CANONICAL).
**Post-P2 HEAD:** `ff602982aa9d81460a54162f1d417a56e9e3880c`.
**Canonical change since P0:** `RaphaelRuntime` now exists (`runtime/loop.py`, `stages.py`,
10 stages); production CLI (`raphael/main.py`) calls it by default with a bound ScopeV0;
`exec/` owns primitives behind Broker/PEP; SUB-10/SUB-13/SUB-14 welded away; SHELL gated.

## 1. Added (present post-P2, absent from P0 inventory)

| # | New path / site | Why absent at P0 | Evidence |
|---|---|---|---|
| A1 | `RaphaelRuntime.run_episode` canonical path (R3.0-P01) + production CLI caller (R3.0-P02) | Runtime did not exist at P0 ("NONE. RaphaelRuntime does not exist") | `src/orchestrator/runtime/loop.py`, `src/raphael/main.py:394-409` |
| A2 | Deployed service surface: `api/main.py` mounts 4 routers; `POST /api/tools/{tool}` (+3 convenience endpoints); `POST /api/tools/nmap`, `/recon` (**no auth**); `POST /api/agent/execute[-sync]`; `POST /v1/ci/engage|scan|agent-engage`, `GET /v1/ci/report|health`; JSON-RPC `bridge/raphael_bridge.py` (`mode.*`, `kali.*`, `c2.*`, …); unauthenticated `kali-tools/server.py POST /run` | P0 inventoried CLI+Arena+broken-bridge only; never enumerated the FastAPI routers, the bridge method table, or the kali-tools runner | `src/orchestrator/api/*.py`, `src/bridge/raphael_bridge.py:47-105`, `src/kali-tools/server.py` |
| A3 | `kali-tools/server.py:23 subprocess.run(shlex.split(...))` primitive sink (R3.0-P12) | Not in the 17-site P0 list (P0 counted only `asyncio.create_subprocess_*`; the `subprocess.*` plane was a 40-file footnote) | `src/kali-tools/server.py:19-33` |
| A4 | Network-hop execution branch `kali.run → httpx POST :3800/run → subprocess.run` (R3.0-P05/P06/P10) | P0 `_run_local` model was direct-subprocess; post-weld the live branch is remote-HTTP-to-subprocess | `src/orchestrator/kali_tools_client.py:52-82`, `src/kali-tools/server.py` |
| A5 | `implant_builder.py:599 subprocess.run(shell=True)` (inside test/utility path of the builder) | P0 listed only the three `create_subprocess_exec` sites (SUB-07/08/09) in that file | `src/orchestrator/c2/implant_builder.py:599` |
| A6 | SHELL gating (`require_shell_authorization`, `ShellNotAuthorized`) — new Broker-mediated control (R3.0-P13) | P0/SEAM_SITES recorded SHELL as deferred/ungated | `src/orchestrator/capabilities/interactive_shell/capability.py:19-85`, WELD-SHELL evidence |

## 2. Removed (in P0, absent post-P2)

| # | Removed site | Disposition |
|---|---|---|
| R1 | SUB-10 `kali_tools_client._run_local` (`create_subprocess_exec`) + `KaliBypassNotAuthorized` / `_BYPASS_AUTHORIZED` / `authorize_local_bypass` | WELDED (WELD-SUB10, `a099ba460`): symbols deleted; `run()` fail-closed `RuntimeError`. Group R3.0-P15. |
| R2 | SUB-13 `raphael/executor/kali_bridge._subprocess_run` (`create_subprocess_shell`) | WELDED (WELD-SUB14 fold-in, `740861f2e`): method deleted; `run()` fail-closed `RuntimeError`. Group R3.0-P03/P15. |
| R3 | SUB-14 `raphael/executor/executor._subprocess_fallback` (`create_subprocess_shell`) + `BypassNotAuthorized` / `_bypass_authorized` / `authorize_bypass` | WELDED (`740861f2e`): symbols deleted; `_tool_runner` now defaults to `kali_bridge.run`. Group R3.0-P03/P15. |
| R4 | P0 "canonical CLI → direct subprocess" route (`RaphaelOrganism → Executor._subprocess_fallback`, `KaliBridge._subprocess_run`) | No longer executable: both sinks raise. Legacy branch preserved only behind `RAPHAEL_USE_LEGACY=1` as a dead migration path (R3.0-P03). |
| R5 | P0 "bridge hard-codes /home/yaser/raphael-2.0, cannot import" claim | STALE: bridge still carries the stale `sys.path.insert` line, but the module graph it names (`modes.*`, `agents.*`, `c2.*`, `kali_tools_client`, …) resolves inside this repo; reachability is proven by import-edge, not by executing the stdio loop. |

## 3. Reclassified (P0 label → post-P2 label) — corrections are expected outcomes

| P0 Path ID | P0 label | Post-P2 label | Reason |
|---|---|---|---|
| SUB-01, SUB-02, SUB-03 (`weaponizer_engine`) | dead (UNREACHABLE) | **dead — re-confirmed** (R3.0-P14) | Still zero importers from any live entry point; P1 deprecation markers present. |
| SUB-04 (`chains/tool_registry._run_command`) | dead (UNREACHABLE, "unreferenced") | **not-yet-mediated — CORRECTED** (R3.0-P04) | Reachable from deployed `POST /api/tools/{tool}` (`api/tools.py:22,219,266-281` + `api/main.py:20,87`). Direct `create_subprocess_exec`, no broker. |
| SUB-05, SUB-06 (`c2/sliver_backend`) | dead | **not-yet-mediated — CORRECTED** (R3.0-P11) | Reachable via `bridge c2.*` and via `chains/ad_kill_chain` + `credential_spray` → `c2.manager` (manager lazily loads `SliverBackend`/`NativeC2Backend`). No broker. |
| SUB-07, SUB-08, SUB-09 (`c2/implant_builder`) | dead | **not-yet-mediated — CORRECTED** (R3.0-P11) | Same `c2` reachability as above (`manager.generate_implant`, `native_backend.builder`, spray deploy paths). No broker. |
| SUB-10 (`kali_tools_client._run_local`) | DIRECT, canonical-NO / CLI-NO | **dead/welded-closed — reclassified by weld** (R3.0-P15) | Symbol deleted; local branch raises. Remote branch is P10 (not-yet-mediated), not SUB-10. |
| SUB-11 (`recon-pipeline/main.py`) | dead | **dead — re-confirmed** (R3.0-P14) | Standalone service; zero importers from live entries. |
| SUB-12 (`agent/modules/executor.py`) | dead | **dead — re-confirmed** (R3.0-P14) | Legacy agent module; zero importers from live entries. |
| SUB-13 (`KaliBridge._subprocess_run`) | LEGACY_REACHABLE, DIRECT | **dead/welded-closed — reclassified by weld** (R3.0-P03/P15) | Symbol deleted (`740861f2e`). |
| SUB-14 (`Executor._subprocess_fallback`) | LEGACY_REACHABLE, DIRECT | **dead/welded-closed — reclassified by weld** (R3.0-P03/P15) | Symbol deleted (`740861f2e`). |
| SUB-15, SUB-16, SUB-17 (`sword/phase_0_recon.py`) | dead | **dead — re-confirmed** (R3.0-P14) | Standalone pipeline; zero importers from live entries. |

**P0 classifications corrected (dead → not-yet-mediated): SUB-04, SUB-05, SUB-06, SUB-07, SUB-08, SUB-09 (6 sites).**
Reclassified by weld (reachable/direct → welded-closed): SUB-10, SUB-13, SUB-14 (3 sites).
Re-confirmed dead: SUB-01, SUB-02, SUB-03, SUB-11, SUB-12, SUB-15, SUB-16, SUB-17 (8 sites).

Line drift note (no semantic change): P1 deprecation-marker headers shifted some P0 line
numbers at HEAD — SUB-01/02/03 `94/152/199→121/179/226`, SUB-12 `:7→:16`,
SUB-15/16/17 `88/126/165→115/153/192` (verbatim post-P2 sites in
`raw/subprocess_sites_postp2.txt`). SUB-04 `:58→:67` for the same reason.

## 4. Changed semantics (same file, new meaning)

- `orchestrator/runtime/` at P0 was Caido/Docker/session files with empty `__init__`; post-P2 it is the
  canonical sequencer (`loop.py`, `stages.py`, `scope.py`, `policy.py`, `organs.py`, …). The P0→P1 name
  collision noted in the deletion inventory is resolved in favor of the Runtime (Caido/Docker/session
  files are gone from the package listing at HEAD).
- `raphael/main.py` at P0 was the unbrokered Head-1 loop; at HEAD its default path is the canonical
  Broker-mediated Runtime episode, with Head-1 preserved only as a `RAPHAEL_USE_LEGACY=1` dead branch.
- `kali_tools_client.py` at P0/SEAM_SITES was a quarantined bypass (opt-in flag); at HEAD the bypass
  is deleted and the live remote branch is an HTTP hop to an unauthenticated subprocess runner.
- `Planner.decide allowed=True` (P0 "misleading comment") is unchanged as selection-only semantics,
  but the canonical planner-request stage now routes mission candidates through the real Planner with
  the Broker as sole authorizer (`stages.py:stage_planner_request` + `stage_broker`).
