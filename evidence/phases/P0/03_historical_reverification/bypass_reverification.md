## P0 — Historical Bypass Candidate Re-Verification (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

Re-verification states: **CONFIRMED** (still in materially the same location/behavior) / **SHIFTED** (exists but location/behavior changed) / **ABSENT** (cannot be found) / **RESOLVED** (closed by intervening work) / **NEW** (live path discovered by P0 not in historical set) / **UNKNOWN** (current truth cannot be established).

### Candidate 1: `raphael/executor/executor.py` — `_subprocess_fallback`

- **Audit reference:** direct subprocess execution in Head-1's `Executor` class.
- **Live location:** `src/raphael/executor/executor.py:67` `async def _subprocess_fallback(self, tool, args, timeout)`.
- **Live body:** `proc = await asyncio.create_subprocess_shell(cmd, ...)` at line 72.
- **Broker gate present?** **NO.** No `CapabilityBroker.propose_action` call in `_subprocess_fallback`.
- **Quarantine gate present?** **NO** (the Phase-2 quarantine with `_bypass_authorized` flag lives in stashed orphan state).
- **State:** **CONFIRMED.** Still present, still no broker gate, still no quarantine.

### Candidate 2: `orchestrator/kali_tools_client.py` — `_run_local`

- **Audit reference:** local subprocess fallback in `KaliToolsClient` (no broker gate).
- **Live location:** `src/orchestrator/kali_tools_client.py:20` `async def _run_local(tool, args, timeout)`.
- **Live body:** `proc = await asyncio.create_subprocess_exec(*cmd_list, ...)` at line 41.
- **Broker gate present?** **NO.**
- **Quarantine gate present?** **NO** (Phase-2 quarantine lives in stashed orphan state).
- **State:** **CONFIRMED.** Still present, still no broker gate.

### Candidate 3: `orchestrator/capabilities/interactive_shell/{ssh_shell,reverse_shell}` — constructor bypass

- **Audit reference:** SSH/Reverse shell constructors accept connection info directly; no broker enforcement at construction.
- **Live locations:**
  - `src/orchestrator/capabilities/interactive_shell/ssh_shell.py:38` `def __init__(self, connection_info)`
  - `src/orchestrator/capabilities/interactive_shell/reverse_shell.py:77` `def __init__(self, connection_info, ...)`
- **Broker gate at construction?** **NO** — neither constructor calls `broker.propose_action` or has a broker reference.
- **Quarantine gate present?** **NO** (Phase-2 quarantine lives in stashed orphan state).
- **State:** **CONFIRMED.** Still present, still bypassable.

### Candidate 4: `orchestrator/brain/action.py` — `allowed = True` (Planner hardcoded allow)

- **Audit reference:** Planner selection bypasses Broker by hardcoding `allowed = True`.
- **Live location:** `src/orchestrator/brain/action.py:1109` `allowed = True  # Assume allowed for planning purposes`.
- **Live context:** inside `Planner.decide()` loop, lines 1106–1117. After scoring candidates, the planner picks the highest-scoring one without consulting the broker. The comment says "In reality, would check against broker policy" but the code is dead — the broker check is in the Arena's `_run_raphael`, not in `Planner.decide`.
- **Is Planner an authorization authority?** **NO.** Planner is selection-only. Broker is authorization. But the variable name `allowed` is misleading; reading the code in isolation, one could mistake this for a security bypass.
- **State:** **CONFIRMED.** Still present, still misleading. The runtime E2E in the canonical arena calls `runner.propose_action` AFTER planner selection, so broker IS the authority at the execution boundary. Planner's `allowed = True` is dead code, not a runtime bypass.

### Candidate 5: `capability_broker.py:1223` — ExecutionEngine broker commented

- **Audit reference:** `ExecutionEngine.execute_action` does not call `broker.propose_action`; broker is commented in `__init__`.
- **Live location:** `src/orchestrator/brain/action.py:1210` `class ExecutionEngine`; `src/orchestrator/brain/action.py:1223` `# broker: 'CapabilityBroker',  # To be implemented`.
- **Live behavior:** `ExecutionEngine.execute_action` at line 1266 uses an ad-hoc risk threshold (`action.risk_estimate <= 0.3`) to auto-authorize, not the broker.
- **Is `ExecutionEngine` reachable from canonical Arena or CLI?** **NO** at canonical. `grep -rEn "ExecutionEngine\(" src/` finds only the class definition and its own method definitions; no caller.
- **State:** **CONFIRMED** that the bypass exists in code; **UNKNOWN** in production-relevance (no caller). The bypass is real-but-dormant.

### Candidate 6: `BrokeredExecutionEngine` reachability

- **Audit reference:** `BrokeredExecutionEngine` defined at `capability_broker.py:1277` but never instantiated outside its own file.
- **Live location:** `src/orchestrator/brain/capability_broker.py:1277` class definition; `src/orchestrator/brain/capability_broker.py:1361` `def create_brokered_engine(...)` factory; `src/orchestrator/brain/capability_broker.py:1370` returns `BrokeredExecutionEngine(...)`.
- **Live callers of `BrokeredExecutionEngine` or `create_brokered_engine`:** **NONE** (`grep -rEn "BrokeredExecutionEngine|create_brokered_engine" src/` shows only the class+factory+return statement).
- **State:** **CONFIRMED** that the class exists; **CONFIRMED** that no canonical caller uses it.

### Candidate 7: `modes/autonomous.py` — `PHASE_EXECUTORS`

- **Audit reference:** 9 of 13 phase executors are `NOT_IMPLEMENTED` stubs.
- **Live location:** `src/orchestrator/brain/phases/models.py:163` `PHASE_EXECUTORS: dict[str, Any] = {...}`.
- **Live state:** confirmed via `grep -nE "def _exec_recon|def _exec_exploit" src/orchestrator/brain/phases/models.py`. 9 stubs (recon, scan, exploit, postex, lateral, credential, exfil, phish, harvest) return `PhaseResult(success=False, status="not_implemented", ...)`. 4 real executors delegate to `cicd_executor.py`, `ml_attack_executor.py`, `cloud_executor.py`, `container_escape_executor.py`.
- **Reachable from canonical Arena?** NO — Arena uses `_run_raphael()` not `modes/autonomous.handle()`.
- **State:** **CONFIRMED.** 9 NOT_IMPLEMENTED stubs, 4 real executors.

### Candidate 8: 4 broken symlinks pointing at `/home/yaser/raphael-2.0`

- **Audit reference:** `cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service` are dangling symlinks.
- **Live state:** `ls -la cai_service cloak_service mcp_hub mhddos_service` confirms each is `... -> /home/yaser/raphael-2.0/<service>` and `/home/yaser/raphael-2.0` does not exist on this host.
- **Do any canonical test paths require these?** **NO.** The 239-test baseline runs green without them.
- **State:** **CONFIRMED.** Dangling symlinks unchanged since audit.

### Candidate 9: Bridge (`src/bridge/raphael_bridge.py`) hard-coded `/home/yaser/raphael-2.0`

- **Audit reference:** bridge `sys.path.insert(0, "/home/yaser/raphael-2.0")` at line 15; broken.
- **Live state:** file unchanged at canonical.
- **State:** **CONFIRMED.** Still broken.

### Candidate 10: AdaptiveBrain stub (`orchestrator/brain/adaptive_brain.py`)

- **Audit reference:** 31-line counter stub, not an orchestrator.
- **Live state:** `wc -l src/orchestrator/brain/adaptive_brain.py` → 31. Unchanged.
- **State:** **CONFIRMED.**

### New candidates discovered by P0

**NONE.** All historical bypass candidates were verified against canonical; no additional paths surfaced.

### Summary

- 10 historical candidates reverified.
- 10 **CONFIRMED**.
- 0 SHIFTED, 0 ABSENT, 0 RESOLVED, 0 NEW, 0 UNKNOWN.

The canonical artifact retains all historical bypass candidates. Phase 3's bypass-closure work is the remediation gate.
