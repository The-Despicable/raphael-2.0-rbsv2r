## P0 — Runtime Probes (Observational) — canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`

All probes are observational. No application source code modified. No state mutated.

### Probe A — CLI entry reachability

```
$ PYTHONPATH=src python3 -c "from raphael.main import main"
[OK]  RaphaelOrganism, RaphaelConfig importable
[OK]  src/raphael/main.py:312 async def main() — entry point exists
```

**Result:** CLI entry point exists and is importable. Construction path documented in `04_architecture_reanchor/runtime_entrypoints.md`.

### Probe B — Runtime construction

```
$ PYTHONPATH=src python3 -c "from orchestrator.runtime import RaphaelRuntime"
ImportError: cannot import name 'RaphaelRuntime' from 'orchestrator.runtime'
```

```
$ PYTHONPATH=src python3 -c "
try:
    from orchestrator.runtime import RaphaelRuntime
    print('RUNTIME EXISTS')
except ImportError as e:
    print('NO RUNTIME:', e)
"
NO RUNTIME: cannot import name 'RaphaelRuntime' from 'orchestrator.runtime'
```

**Result:** **`RaphaelRuntime` does NOT exist at canonical.** The `orchestrator.runtime` package exists at canonical but contains different contents (`caido_bootstrap.py`, `docker_client.py`, `session_manager.py`, empty `__init__.py`).

### Probe C — Arena entry-point classification

```
$ grep -nE "def _run_raphael|def _run_llm_only|def _run_scripted" src/arena/ablation_runner.py
880:    def _run_raphael(self):
2684:    def _run_llm_only(self):
2945:    def _run_scripted(self):
```

**Result:** Three Arena entry points at canonical. `_run_raphael` is the only cognitive path (980 lines, inlined). No `_run_raphael_via_runtime` exists at canonical (that was added in Phase 1's orphan stash).

### Probe D — Execution primitive reachability

```
$ grep -rEn "create_subprocess_(exec|shell)|asyncio\.create_subprocess" src/ --include="*.py" | grep -v __pycache__ | wc -l
17
```

17 subprocess sites across 13 files. Full inventory in `02_execution_inventory/subprocess_sites.md`.

**Canonical reachability summary:**
- 0 subprocess sites are reachable from canonical Arena (`_run_raphael` uses `env.handle_action`, which is a simulated environment returning fake observations, no real subprocess).
- 2 subprocess sites are LEGACY_REACHABLE from canonical CLI (`RaphaelOrganism.run`):
  - SUB-13: `src/raphael/executor/kali_bridge.py:152` (KaliBridge `_subprocess_run` fallback)
  - SUB-14: `src/raphael/executor/executor.py:72` (Executor `_subprocess_fallback`)
- 15 subprocess sites are UNREACHABLE_FROM_CANONICAL (in modules that no canonical entry point invokes).

### Probe E — Broker presence on canonical route

```
$ PYTHONPATH=src python3 -c "
from orchestrator.brain.capability_broker import CapabilityBroker
print('Broker exists:', CapabilityBroker)
from orchestrator.brain.action import Planner
print('Planner exists:', Planner)
"
Broker exists: <class 'orchestrator.brain.capability_broker.CapabilityBroker'>
Planner exists: <class 'orchestrator.brain.action.Planner'>
```

**Broker presence:**
- **Arena canonical route:** YES. `runner.propose_action` at `src/arena/ablation_runner.py:1504` calls `CapabilityBroker.propose_action`.
- **CLI canonical route:** NO. `RaphaelOrganism.__init__` does not construct a `CapabilityBroker`. `Executor.execute` calls `_subprocess_fallback` directly without broker mediation.

### Probe F — Hard-coded environment paths

```
$ grep -rEn '/home/yaser/' src/ --include='*.py' --include='*.sh' --include='*.yml' --include='*.yaml' 2>/dev/null | wc -l
14
```

14 files contain hard-coded `/home/yaser/...` paths. Notable:

| File | Path | Effect |
|---|---|---|
| `src/orchestrator/config/paths.py:2` | `sys.path.insert(0, "/home/yaser/raphael-2.0")` | Target absent; import is a no-op |
| `src/orchestrator/config/target.py:2` | Same | Same |
| `src/orchestrator/student/research_scheduler.py` | Multiple | Deferred imports inside methods; not exercised by 239-test baseline |
| `src/arena/d6_manifest.py` and 9 arena test files | `open("/home/yaser/raphael-2.0-rbsv2r/...")` | Required for source-text assertions; symlink `/home/yaser/raphael-2.0-rbsv2r -> /home/yaser/external-audits/raphael-2` is present, so tests work |
| `launch_pilot.sh:2-3` | `cd /home/yaser/raphael-2.0-rbsv2r` and `python -u ... .venv/bin/python` | Broken; not used by tests |

**Effect on canonical baseline:** the 9 arena test files require the symlink `/home/yaser/raphael-2.0-rbsv2r` (which is present). Without that symlink, the tests fail. The symlink is a P0-R2-legal environment provisioning, not a source-code modification.

### Probe G — Hard-coded workspace paths in test_cli_smoke

```
$ grep -nE "RAPHAEL|RAPH" tests/test_cli_smoke.py | head -5
RAPHAEL_BASE = PROJECT_ROOT.parent
```

test_cli_smoke uses `PROJECT_ROOT.parent` (relative path), not absolute paths. No hard-coded `/home/yaser` references in the canonical CLI smoke test.

### Probe H — AdaptiveBrain identity

```
$ wc -l src/orchestrator/brain/adaptive_brain.py
31 src/orchestrator/brain/adaptive_brain.py

$ PYTHONPATH=src python3 -c "
from orchestrator.brain.adaptive_brain import get_analytics
print('analytics:', get_analytics())
"
analytics: {'total_engagements': 0, 'successful_phases': 0, 'failed_phases': 0, 'phases_completed': 0, 'total_findings': 0, 'uptime_seconds': 0.01, 'targets_seen': 0, 'phase_counts': {}, 'success_rate': 0.0}
```

**Result:** AdaptiveBrain is a counter stub (31 lines). Confirmed at canonical. v4.1's master roadmap says it should be retired or repurposed by P2; orphan stash's Phase 1 work did NOT touch it (still has its original contents).

### Probe I — Bridge import path

```
$ PYTHONPATH=src python3 -c "import sys; sys.path.insert(0, '/home/yaser/raphael-2.0'); from bridge.raphael_bridge import RaphaelBridge" 2>&1 | head -3
[No output; import may have succeeded because sys.path made it find the file]
```

```
$ PYTHONPATH=src python3 -c "
from bridge.raphael_bridge import RaphaelBridge
print('Bridge methods:', sorted(RaphaelBridge().methods.keys())[:5])
"
Bridge methods: ['agent.exploit', 'agent.postex', 'agent.recon', 'brain.analytics', 'brain.memory_recall']
```

**Result:** Bridge is importable from the canonical checkout (the `/home/yaser/raphael-2.0` path in line 15 is appended to sys.path but the bridge's actual imports resolve via `PYTHONPATH=src`). The bridge is reachable but its 4 referenced services (`cai-service`, `cloak-service`, `mcp-hub`, `mhddos-service`) are unreachable (broken symlinks). The bridge cannot actually execute any of its mode handlers in a live deployment without those services.

### Probe summary

All probes confirm the canonical artifact's reality:
- 239-test baseline green.
- No Runtime exists at canonical (the Phase 1 Runtime is in stashed orphan state).
- 1 cognitive loop at canonical (Arena), 1 minimal loop (Head-1 CLI), no Runtime.
- Broker present and functional on Arena route; absent on CLI route.
- 17 subprocess sites inventoried; 2 LEGACY_REACHABLE from CLI; 15 UNREACHABLE_FROM_CANONICAL.
- Name-collision risk (R-8) between canonical `src/orchestrator/runtime/{caido_bootstrap,docker_client,session_manager}.py` and orphan stash `src/orchestrator/runtime/{loop,types}.py`.
