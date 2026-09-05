## P0 — Canonical Execution Graph (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

```
                  [CANONICAL]              [LEGACY]                  [UNREACHABLE_FROM_CANONICAL]
                  ───────────              ────────                  ───────────────────────────

  Operator / CLI
       │
       ▼
  python -m raphael.main                                    [LEGACY]
       │
       ▼
  RaphaelOrganism.run()                                    [LEGACY]
       │
       ├── Planner (cortex) ─── SELECTION ONLY ───┐
       │                                            │
       └── Executor.execute() ─── DIRECT ─────────│
            │                                       │
            └─ _subprocess_fallback(SUB-14)         │
                 │                                  │
                 └─ asyncio.create_subprocess_shell  │     [BROKER=GAP]


  Arena entry (test harness only)                    [CANONICAL]
       │
       ▼
  AblationRunner._run_raphael()  [INLINED 980-line loop]
       │
       ├─ LLM service (mocked in tests)
       ├─ Evidence ingestion (init observations)
       ├─ WorldModel entity seeding
       │
       └── while iteration:
            ├─ ShellCandidateGenerator + StudentCandidateGenerator
            ├─ runner.planner.decide(...)               [SELECTION, allowed=True hardcoded]
            ├─ runner.propose_action(...)               [BROKER, 5-dim deny-by-default]
            │     └─ self.broker.propose_action(...)   ← CapabilityBroker
            ├─ env.handle_action(...)                    [SIMULATED env, no real subprocess]
            ├─ evidence_graph.add_evidence(ev)
            ├─ world_model.ingest_shell_evidence(ev)
            ├─ contradiction_manager.detect_contradictions()
            └─ hypothesis_manager.update_confidence(...)


  BROKER GAP (canonical):
  ─────────────────────────
  Arena → Broker call is REAL and FUNCTIONAL.
  CLI → no Broker on its path (direct subprocess via _subprocess_fallback).

  Planner is NOT an authorization authority.
  Authorization = CapabilityBroker.propose_action only.
  Planner.decide() sets allowed=True for SELECTION; Broker is sole authorization.


  RaphaelRuntime                                                 [DOES NOT EXIST]
  ──────────────
  Not present at canonical commit.
  Phase 1 work created src/orchestrator/runtime/loop.py + types.py and
  modified src/orchestrator/runtime/__init__.py, but that work lives in
  the stashed orphan state, not the canonical artifact.
```

### Legend

- `[CANONICAL]` — reachable from the canonical entry point and follows the documented architecture
- `[LEGACY]` — reachable from a canonical entry point but uses non-canonical mechanisms (Head-1 CLI)
- `[UNREACHABLE_FROM_CANONICAL]` — exists in the tree but no canonical caller invokes it
- `[DOES NOT EXIST]` — claimed in v4 documentation / prior Phase 1 work, but absent from canonical artifact

### Critical observations

1. **No Runtime exists at canonical.** v4.1's "ONE RUNTIME" architecture is not yet realized. The Phase 1 work that created `RaphaelRuntime` is in the orphan stash.

2. **The CLI is the unbrokered path.** `RaphaelOrganism.run()` does not invoke `CapabilityBroker`. The Planner's `allowed=True` at `action.py:1109` is selection-only, not authorization; the actual authorization gap is at `Executor._subprocess_fallback` (SUB-14) which is a direct `create_subprocess_shell` call.

3. **The Arena is broker-mediated but Planner has a misleading comment.** The Arena's `runner.propose_action` is real and functional. But `Planner.decide()` at `action.py:1109` hardcodes `allowed = True` with the comment "In reality, would check against broker policy" — dead code that could be misread as a bypass if read in isolation.

4. **15 of 17 subprocess sites are unreachable from canonical entry points.** They sit in code that isn't wired into the Arena or CLI (`weaponizer`, `chains/tool_registry`, `c2/*`, `recon-pipeline`, `agent/modules/executor`, `sword/phase_0_recon`). Phase 3's bypass-closure work must address the 2 reachable sites first (SUB-13, SUB-14) and may also delete or quarantine the 15 unreachable sites.

5. **Phase 1+2 orphan stash conflicts with canonical.** `src/orchestrator/runtime/__init__.py` exists at canonical as an empty file; the orphan stash contains a populated export list. `src/orchestrator/runtime/loop.py` and `types.py` are orphan-only; `caido_bootstrap.py`, `docker_client.py`, `session_manager.py` are canonical-only. P1 must reconcile this path before popping the stash.
