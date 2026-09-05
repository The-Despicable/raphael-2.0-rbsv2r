## P0 — Architecture Re-anchor: Runtime and Arena Entry Points (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Runtime entry points (canonical)

**NONE.** `RaphaelRuntime` does not exist at canonical.

```
$ PYTHONPATH=src python3 -c "from orchestrator.runtime import RaphaelRuntime"
ImportError: cannot import name 'RaphaelRuntime' from 'orchestrator.runtime'
```

The `orchestrator.runtime` package exists but contains different contents:
- `caido_bootstrap.py` (5303 bytes, unrelated — Caido proxy integration)
- `docker_client.py` (Docker session client, unrelated)
- `session_manager.py` (session manager, unrelated)
- `__init__.py` (empty)

### Arena entry points (canonical)

**Single cognitive loop:** `AblationRunner._run_raphael()` at `src/arena/ablation_runner.py:880`. 980-line inlined cognitive loop.

**Other entry points:**
- `AblationRunner._run_llm_only()` at `src/arena/ablation_runner.py:2684` (LLM-only baseline)
- `AblationRunner._run_scripted()` at `src/arena/ablation_runner.py:2945` (scripted baseline)

**Dispatcher:** `AblationRunner.run()` at `src/arena/ablation_runner.py:718` selects which path to run based on `self.config.baseline_type`.

### CLI entry points (canonical)

**Single:** `src/raphael/main.py:312` `async def main()`.

### CLI → execution chain (canonical, no Runtime)

```
src/raphael/main.py:312 main()
   └─ RaphaelConfig.from_env()
   └─ RaphaelOrganism(config)            [src/raphael/main.py:346]
      └─ .initialize()                     [src/raphael/main.py:130]
      └─ .run()                            [src/raphael/main.py:160]
         └─ planner = Planner()           [src/raphael/cortex/planner.py]
         └─ executor = Executor(...)      [src/raphael/executor/executor.py]
            └─ _tool_runner = self._subprocess_fallback  [SUB-14, DIRECT]
         └─ while cycle:
              └─ planner.select_next_step(state, affs, cons)  [SELECTION ONLY, no Broker]
              └─ if action == "execute":
                   └─ executor.execute(state, technique)
                      └─ _tool_runner(target, args, timeout)
                         └─ await asyncio.create_subprocess_shell(cmd)  [SUB-14]
```

No `CapabilityBroker` is constructed on the CLI path. `Planner` is selection-only.

### Arena → execution chain (canonical)

```
src/arena/ablation_runner.py:718 AblationRunner.run()
   └─ self._run_raphael()                 [src/arena/ablation_runner.py:880]
      └─ _build_traced_runner()           [src/arena/ablation_runner.py:813]
         └─ evidence_graph = EvidenceGraph()
         └─ world_model = WorldModel(eg)
         └─ hypothesis_manager = HypothesisManager(eg, wm)
         └─ contradiction_manager = create_contradiction_manager(eg, hm, wm)
         └─ planner = RealPlanner(...)    [src/orchestrator/brain/action.py:649]
         └─ broker = CapabilityBroker(scenario.policy)  [BROKER PRESENT]
         └─ runner = ArenaRunner(...)
      └─ env = ScenarioEnvironment(self.scenario)        [SIMULATED, no real subprocess]
      └─ while iteration < ITERATION_BUDGET and actions_dispatched < ACTION_CAP:
           └─ runner.planner.decide(...)                  [SELECTION, allows=True hardcoded]
           └─ runner.propose_action(...)                  [BROKER]
           └─ env.handle_action(...)                       [SIMULATED]
           └─ runner.evidence_graph.add_evidence(ev)
           └─ runner.world_model.ingest_shell_evidence(ev)
           └─ runner.detect_contradictions()
           └─ hypothesis_manager.update_confidence(...)
```

`runner.propose_action` calls `broker.propose_action` (BROKER-MEDIATED). `env.handle_action` returns simulated observations (no real subprocess).

### Modes entry points (canonical)

```
src/orchestrator/modes/
├── autonomous.py    handle(target, phases=None, ...) → PHASE_EXECUTORS
├── student.py       handle(target, target_type, ...) → StudentCandidateGenerator (proposal_only)
├── scan.py
├── debate.py
├── community.py
├── deep_research.py
└── rsi.py, postmortem.py
```

No canonical Arena or CLI entry point invokes these mode handlers. The bridge does (broken).
