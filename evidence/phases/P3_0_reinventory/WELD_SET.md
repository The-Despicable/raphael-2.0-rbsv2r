# P3.0 Re-inventory — AM-4 Weld Set (authoritative input to the follow-on weld task)

**Source:** `CLASSIFICATION.md` rows labeled `not-yet-mediated` (9 paths).
**Rule:** G3 does not pass while any path below remains un-welded (AM-4 §3).
"Welding closed" = seam fixed ON for that call path (permanently routed through Broker/PEP)
AND the legacy branch at that call site deleted, under a named versioned policy artifact.
Partial welding is a G3 FAIL, not a partial pass.
**Non-goals here:** no welding performed in P3.0; SHELL (P13, gated) and welded stubs
(P03/P15) and dead standalone planes (P14) are NOT in this set.

## Weld set (9)

| Weld item | Path | Call site(s) to weld (route through Broker/PEP + delete legacy branch) |
|---|---|---|
| W-01 | R3.0-P04 | `src/orchestrator/api/tools.py:159 execute_tool` + convenience endpoints → `src/orchestrator/chains/tool_registry.py:57-115 _run_command` (`create_subprocess_exec`). Delete direct-subprocess branch at the call site. |
| W-02 | R3.0-P05 | `src/orchestrator/api/tools_bridge.py:133 run_nmap`, `:156 run_recon` → `_run_in_kali` httpx hop. Authenticate + broker-gate (or delete) the bridge routes; the shared sink is W-09. |
| W-03 | R3.0-P06 | `src/orchestrator/api/agent.py:43 execute_agent`, `:176 execute_agent_sync` → `agents/engage.run_agent_engage` fan-out (`scanners/*`, `ad/*` → `kali.run`). Route every tool invocation through Broker/PEP; delete unbrokered fan-out at the call sites. |
| W-04 | R3.0-P07 | `src/orchestrator/api/ci.py:146 quick_scan` → `modes/autonomous.handle`. Broker-gate the CI→autonomous call path; downstream sinks are W-06/W-08. |
| W-05 | R3.0-P08 | `src/orchestrator/api/ci.py:181 agent_engage` (and queued `POST /v1/ci/engage` → `handle`). Same treatment as W-03/W-04 at these call sites. |
| W-06 | R3.0-P09 | `src/bridge/raphael_bridge.py:119 mode_autonomous` (+ `mode.student/scan`, `agent.*`) → `modes/autonomous.handle` → `chains/ad_kill_chain.run_chain`, `chains/credential_spray.spray` → `kali.run` / `get_c2()`. Broker-gate each bridge method; delete unbrokered chain branches. |
| W-07 | R3.0-P10 | `src/bridge/raphael_bridge.py:202-218 kali_*` → `kali_tools_client.KaliToolsClient.run` remote branch (httpx → `:3800/run`). Broker-gate or delete; shared sink is W-09. SUB-10 weld covered only the local branch. |
| W-08 | R3.0-P11 | `c2` plane: `c2/manager.py` (lazy `SliverBackend`/`NativeC2Backend`) → `c2/sliver_backend.py:93,119`, `c2/implant_builder.py:342,477,529` (`create_subprocess_exec`), `:599 subprocess.run(shell=True)`. Broker-gate every builder/backend entry; delete unbrokered branches (covers corrected SUB-05…09). |
| W-09 | R3.0-P12 | `src/kali-tools/server.py:19 POST /run` → `:23 subprocess.run`. Authenticate + broker-gate (or delete/isolate) the runner; this is the shared sink of W-02/W-03/W-07. Unauthenticated arbitrary-command execution until welded. |

## Explicitly NOT in the weld set

- R3.0-P01/P02 (canonical Runtime + CLI caller): already Broker-mediated — control, not work.
- R3.0-P13 (SHELL): already gated by `require_shell_authorization` (WELD-SHELL) — verify, do not re-weld here.
- R3.0-P03/P15 (SUB-10/13/14 welded stubs): symbols deleted — verify absence, do not re-weld.
- R3.0-P14 (dead standalone: SUB-01/02/03, SUB-11, SUB-12, SUB-15/16/17): P9 deletion candidates, not AM-4 welds. Deleting them is out of scope for the weld task (AM-4 welds the 9 live paths above; P9 owns dead-code deletion after zero-reference proof).

## Uncertainty recorded (per hard-stop rule: ambiguous → not-yet-mediated)

- U-1: `POST /v1/ci/engage` enqueues rather than executes inline; the queued worker is `modes/autonomous.handle` (same sink as W-04) — listed under W-05 rather than as a separate item. If the queue has another consumer, it joins W-04/W-05.
- U-2: `api/session.py` router is session CRUD (no primitive observed); if a follow-on trace finds a primitive behind it, it joins the set as W-10.
- U-3: `mcp-hub/tools/*`, `mhddos-service`, `sword/*` (beyond phase_0), `agent/*` (beyond modules/executor) contain `subprocess.*` call sites outside the P0 SUB schema; they have no live-entry importer at HEAD (hence dead by the P0 rule), but any deployment manifest that serves them promotes the serving path into this set.
