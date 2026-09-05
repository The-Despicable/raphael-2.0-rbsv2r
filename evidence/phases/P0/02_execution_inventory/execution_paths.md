## P0 — Execution Paths Inventory (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Canonical Runtime entry point

**NONE.** `RaphaelRuntime` does not exist at canonical. `from orchestrator.runtime import RaphaelRuntime` raises `ImportError`.

The `src/orchestrator/runtime/` package exists but contains different contents (see §5.5 Probe B of the evidence package):
- `caido_bootstrap.py` (5303 bytes)
- `docker_client.py`
- `session_manager.py`
- empty `__init__.py`

These files are unrelated to the runtime orchestration layer. They belong to a different feature surface (Caido proxy integration, Docker session management).

### Canonical CLI entry → execution chain

```
[CLI] python -m raphael.main
       │
       ▼
src/raphael/main.py:312  async def main()
       │
       ▼
src/raphael/config.py    RaphaelConfig.from_env()
       │
       ▼
src/raphael/main.py:346  RaphaelOrganism(config)
       │
       ▼
src/raphael/main.py:114  RaphaelOrganism.__init__()
                          ├─ self.blackboard = Blackboard(config.db_path)
                          ├─ self.event_bus = EventBus()
                          ├─ self.planner = Planner()              [src/raphael/cortex/planner.py]
                          ├─ self.executor = Executor(event_bus, blackboard)
                          │                  [src/raphael/executor/executor.py]
                          ├─ self.spinal_reflex = SpinalReflex(executor)
                          ├─ self.hippocampus = get_hippocampus()
                          ├─ self.parallel_recon = ParallelRecon(executor)
                          └─ self.thermoregulator = Thermoregulator(...)
       │
       ▼
src/raphael/main.py:347  organism.initialize()
                          └─ blackboard.connect() [SQLite at config.db_path]
       │
       ▼
src/raphael/main.py:348  organism.run()         [src/raphael/main.py:160]
                          └─ while cycle < max_cycles:
                               ├─ parallel_recon.run_batch()        [src/raphael/limbic/parallel_recon.py]
                               └─ for each cycle:
                                    ├─ planner.select_next_step(state, affs, cons)  [src/raphael/cortex/planner.py:94]
                                    └─ if action is "execute":
                                         ├─ executor.execute(state, technique)         [src/raphael/executor/executor.py:90]
                                         │   └─ _tool_runner or _subprocess_fallback    [SUB-14, DIRECT, no broker]
                                         └─ if action is "acquire_capability":
                                              └─ state.capabilities.ensure_owned(target)
```

**Authorization on CLI route:** **NONE.** No `CapabilityBroker` instance is constructed on this path. `Executor._subprocess_fallback` (SUB-14) is a direct `create_subprocess_shell` call.

### Canonical Arena entry → execution chain

```
[Arena test runner] AblationRunner(template, config, seed, split).run()
       │
       ▼
src/arena/ablation_runner.py:718  def run()
       │
       ▼
src/arena/ablation_runner.py:732  self._run_raphael()        [the only cognitive path at canonical]
       │
       ▼  (980-line inlined cognitive loop, summarized below)
src/arena/ablation_runner.py:880  _run_raphael()
   1. Build ArenaRunner via _build_traced_runner()  [src/arena/ablation_runner.py:813]
       ├─ evidence_graph = EvidenceGraph()
       ├─ world_model = WorldModel(eg)
       ├─ hypothesis_manager = HypothesisManager(eg, wm)
       ├─ contradiction_manager = create_contradiction_manager(eg, hm, wm)
       ├─ planner = RealPlanner(...)                [src/orchestrator/brain/action.py:649]
       ├─ broker = CapabilityBroker(scenario.policy) [src/orchestrator/brain/capability_broker.py:266]
       └─ runner = ArenaRunner(scenario, eg, wm, hm, cm, broker, planner)
   2. env = ScenarioEnvironment(self.scenario)        [src/arena/environment.py:89]
   3. Initial observations → evidence_graph.add_evidence(ev)
   4. WorldModel entity seeding from engagement_view().starting_assets
   5. ShellCandidateGenerator + StudentCandidateGenerator constructed
   6. while iteration < ITERATION_BUDGET and actions_dispatched < ACTION_CAP:
        ├─ LLM semantic inference (gated on config.llm_enabled)
        ├─ Hypothesis formation (gated on config.hypothesis_enabled)
        ├─ Defeater trigger generation (gated on config.defeater_enabled)
        ├─ WorldModel.query(...)
        ├─ _generate_candidates(view, runner, world_query_result)  [src/arena/ablation_runner.py:1870]
        ├─ if config.planner_enabled:
        │     plan_decision = runner.planner.decide(candidates, objective_id, ...)
        │     └─ action.py:839 Planner.decide()
        │        └─ scores candidates; **action.py:1109: allowed = True  # HARDCODED ALLOW**
        │        └─ returns selected_action_id (SCORING ONLY, not authorization)
        ├─ runner.propose_action(...)                    [src/arena/runner.py:285]
        │     └─ self.broker.propose_action(...)           [src/orchestrator/brain/capability_broker.py:308]
        │        └─ returns ActionReceipt(decision="allow"|"deny")
        ├─ if receipt.decision != "allow":
        │     runner.planner.register_denial(...)
        │     continue
        ├─ env.handle_action(target, action_type, capability, method, receipt_id)
        │     └─ returns simulated observations (NOT real subprocess)
        ├─ for obs in observations:
        │     evidence_graph.add_evidence(ev)
        │     world_model.ingest_shell_evidence(ev)
        ├─ runner.detect_contradictions()                 [src/arena/runner.py:380]
        ├─ if selected._is_falsification:
        │     runner.execute_discriminator(...)
        │     runner.contradiction_manager.produce_falsification_result(...)
        └─ hypothesis_manager.update_confidence(...)
   7. Save episode records
```

**Authorization on Arena route:** **YES (Broker-mediated).** The Arena's `runner.propose_action` calls `CapabilityBroker.propose_action` which is a real, deny-by-default, 5-dimension authorization gate.

**However:** `Planner.decide()` at `src/orchestrator/brain/action.py:1109` hardcodes `allowed = True` for the **selection step**. This is not authorization (Broker is still called for authorization), but it is a misleading comment that reads like a bypass. Selection != authorization.

### Bridge entry point (broken/dead)

```
src/bridge/raphael_bridge.py:15  sys.path.insert(0, "/home/yaser/raphael-2.0")
src/bridge/raphael_bridge.py:311 if __name__ == "__main__": asyncio.run(main())
```

The bridge hard-codes `/home/yaser/raphael-2.0` (target directory absent). Bridge cannot import successfully on this host.

### Modes

```
src/orchestrator/modes/
├── autonomous.py    handle() → PHASE_EXECUTORS (9 of 13 are NOT_IMPLEMENTED stubs)
├── student.py       handle() → StudentCandidateGenerator (proposal_only)
├── scan.py
├── debate.py
├── community.py
├── deep_research.py
└── rsi.py, postmortem.py
```

`autonomous.handle()` and `student.handle()` are exposed as mode handlers. The arena does not invoke them; the bridge does (broken).

### Per-route authorization summary

| Route | Authorization | Evidence |
|---|---|---|
| Canonical CLI → `RaphaelOrganism.run` → `Executor._subprocess_fallback` (SUB-14) | NONE (direct subprocess) | `src/raphael/main.py:160–262`; `src/raphael/executor/executor.py:67–89` |
| Canonical Arena → `runner.propose_action` → `broker.propose_action` | BROKER (5-dim deny-by-default) | `src/arena/ablation_runner.py:1504`; `src/orchestrator/brain/capability_broker.py:308` |
| Canonical CLI → `RaphaelOrganism` → `KaliBridge._subprocess_run` (SUB-13) | NONE (direct subprocess) | `src/raphael/executor/kali_bridge.py:152` |
| Planner `decide` selection | LOCAL (selection-only; `allowed = True` hardcoded but no execution) | `src/orchestrator/brain/action.py:1109` |

### What P0 did NOT establish

- No canonical Runtime entry point exists (P1 work).
- No positive interface for any seam (P1 work).
- No closure of the unbrokered CLI paths (P3 work).
- No Phase-2 quarantine on `Executor._subprocess_fallback` (Phase 2 quarantine lives in stashed orphan state).
