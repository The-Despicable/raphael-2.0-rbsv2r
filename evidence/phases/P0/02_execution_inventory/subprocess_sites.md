## P0 — Subprocess Sites Inventory (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Total: 17 `asyncio.create_subprocess_*` sites across 13 files.

| Path ID | File | Symbol | Reachable from canonical Arena? | Reachable from canonical CLI? | Authorization | Notes |
|---|---|---|---|---|---|---|
| SUB-01 | `src/orchestrator/weaponizer/weaponizer_engine.py:94` | `await asyncio.create_subprocess_exec(...)` | NO | NO (not invoked by `RaphaelOrganism`) | DIRECT | weaponizer module is unreferenced outside its own file |
| SUB-02 | `src/orchestrator/weaponizer/weaponizer_engine.py:152` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | same |
| SUB-03 | `src/orchestrator/weaponizer/weaponizer_engine.py:199` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | same |
| SUB-04 | `src/orchestrator/chains/tool_registry.py:58` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | unreferenced |
| SUB-05 | `src/orchestrator/c2/sliver_backend.py:75` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | bridge/CLI dead code; not exercised by canonical tests |
| SUB-06 | `src/orchestrator/c2/sliver_backend.py:101` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | same |
| SUB-07 | `src/orchestrator/c2/implant_builder.py:315` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | unreferenced |
| SUB-08 | `src/orchestrator/c2/implant_builder.py:450` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | unreferenced |
| SUB-09 | `src/orchestrator/c2/implant_builder.py:502` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | unreferenced |
| SUB-10 | `src/orchestrator/kali_tools_client.py:41` | `asyncio.create_subprocess_exec(...)` (inside `_run_local`) | NO (canonical path) — `KaliToolsClient.run()` calls `_run_local` only when remote fails or `FORCE_LOCAL=1` | NO (canonical CLI is Head-1, doesn't use kali_tools_client) | DIRECT (no broker gate) | `_run_local` is the historical bypass site |
| SUB-11 | `src/recon-pipeline/main.py:80` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | recon-pipeline is its own service; not wired into Arena or CLI |
| SUB-12 | `src/agent/modules/executor.py:7` | `proc = await asyncio.create_subprocess_shell(...)` | NO | NO | DIRECT | legacy agent module; not invoked by canonical Arena or CLI |
| SUB-13 | `src/raphael/executor/kali_bridge.py:152` | `await asyncio.create_subprocess_shell(...)` (inside `KaliBridge._subprocess_run`) | NO | LEGACY_REACHABLE — `RaphaelOrganism` constructs `KaliBridge` at init; falls back to `_subprocess_run` when HTTP API unavailable | DIRECT (no broker gate) | Head-1's Kali fallback |
| SUB-14 | `src/raphael/executor/executor.py:72` | `proc = await asyncio.create_subprocess_shell(...)` (inside `_subprocess_fallback`) | NO | LEGACY_REACHABLE — `RaphaelOrganism.run` → `Planner.select_next_step` → `Executor.execute` → `_tool_runner or _subprocess_fallback` | DIRECT (no broker gate) | Head-1's tool fallback; the historical bypass |
| SUB-15 | `src/sword/phase_0_recon.py:88` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | sword is its own pipeline; not wired into Arena or CLI |
| SUB-16 | `src/sword/phase_0_recon.py:126` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | same |
| SUB-17 | `src/sword/phase_0_recon.py:165` | `await asyncio.create_subprocess_exec(...)` | NO | NO | DIRECT | same |

### Sites that import `subprocess` (40 files)

A broader inventory covers files that import `subprocess` even if they don't use `asyncio.create_subprocess`. Notable:

- `src/mcp-hub/tools/*` — 9 MCP-tool files (metasploit, gobuster, sqlmap, nuclei, nmap, etc.). The MCP-Hub service is a separate FastAPI server (not wired into canonical Arena/CLI).
- `src/mhddos-service/main.py` — DDoS service, separate.
- `src/agent/modules/executor.py` — already in SUB-12.
- `src/orchestrator/kali_tools_client.py` — already in SUB-10.

### Critical observation

At canonical, **no subprocess site is reachable from the canonical Arena's `_run_raphael()`** because the arena's `env.handle_action()` is a simulated environment (returns fake observations, no real subprocess). The canonical arena does not execute real tools.

**Two subprocess sites are LEGACY_REACHABLE from the canonical CLI** (`RaphaelOrganism`):
- SUB-13 (`KaliBridge._subprocess_run`) — fires only when the Kali HTTP API is unreachable.
- SUB-14 (`Executor._subprocess_fallback`) — fires when the Planner selects a technique and the Executor executes it.

Neither site has Broker gating. **These are the canonical CLI's unbrokered execution paths.**

The remaining 15 sites are unreachable from canonical Runtime, CLI, or Arena entry points.

### Sites that ALSO have a direct `subprocess` import (40 files)

Counted separately. Listed in §5.6 of the evidence package summary.
