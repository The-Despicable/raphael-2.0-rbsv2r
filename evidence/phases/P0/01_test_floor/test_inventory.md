## P0 — Test Inventory (canonical commit `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Summary

- **Test files:** 22 in `tests/` + 1 in `src/arena/tests/` (the latter is the arena's internal regression suite, collected by pytest as well).
- **Total tests collected:** 239
- **Total tests passed:** 239
- **Total tests failed:** 0
- **Total tests skipped:** 0
- **Total xfailed:** 0
- **Total xpassed:** 0

### Test file → component → integration-level map (canonical)

| File | Tests | Component exercised | Integration level |
|---|---|---|---|
| `tests/e1_interactive_shell_test.py` | 34 | Interactive shell capability (filter, sessions, listener) | Unit (no live shell) |
| `tests/e2_shell_candidate_generation_test.py` | 36 | ShellCandidateGenerator + WorldModel + Hypothesis + Contradiction | Integration (no live shell) |
| `tests/test_budget_contract.py` | 6 | Arena runner iteration/action budgets | Unit (static analysis) |
| `tests/test_cli_smoke.py` | 26 | File presence, imports, environment | Smoke only |
| `tests/test_conclusion_infra.py` | 5 | Arena runner + adapters | Component wiring |
| `tests/test_d5_preflight.py` | 10 | Hypothesis/falsification logic | Unit logic |
| `tests/test_d5_seven_gate_proof.py` | 1 | End-to-end hypothesis pipeline | E2E (arena, mocked LLM) |
| `tests/test_debug_stderr_epipe.py` | 4 | Debug stderr | Unit |
| `tests/test_environment_determinism.py` | 4 | Arena environment | Determinism |
| `tests/test_evaluator_isolation.py` | 7 | Arena graph isolation | Integration |
| `tests/test_gate_b_action_accounting.py` | 10 | Broker accounting | E2E (arena, broker, mocked LLM) |
| `tests/test_llm_transport.py` | 20 | LLM HTTP transport | Unit |
| `tests/test_noop_contract.py` | 8 | NoOp parity | Unit |
| `tests/test_prompted_agent_parity.py` | 6 | LLM agent parity | E2E (arena, mocked LLM) |
| `tests/test_prompted_agent_repair.py` | 10 | Prompted agent loop | E2E (arena, mocked LLM) |
| `tests/test_rbs_v2_repairs.py` | 6 | Repair verification | Mixed |
| `tests/test_repair_gate.py` | 4 | Repair gate logic | Unit |
| `tests/test_run_identity.py` | 7 | Run ID identity | Unit |
| `tests/test_safety_telemetry.py` | 5 | Telemetry | Unit |
| `tests/test_stage1_invariants.py` | 14 | Stage 1 invariants | Unit |
| `tests/test_token_telemetry.py` | 12 | Token tracking | Unit |
| `tests/test_tool_failure_provenance.py` | 4 | Tool failure → evidence | Unit |

### What 239 passing tests prove

- The arena harness correctly wires WorldModel, HypothesisManager, ContradictionManager, Planner, CapabilityBroker.
- The CapabilityBroker correctly enforces authorization with proper accounting (10 broker tests).
- NoOp classes match the real ones by signature.
- Stage 1 contracts (trust provenance, scope, scenarios) are preserved.
- Token / telemetry counters work.
- The interactive shell capability modules pass their unit tests (no live SSH session exercised).

### What 239 passing tests do NOT prove

- That any of these components are reachable from a production entry point at canonical (no Runtime exists at canonical).
- That `python -m raphael.main` runs the cognitive loop (canonical CLI is Head-1, minimal).
- That real tools are actually executed (all execution is simulated in arena).
- That the documented architecture runs end-to-end.
- That any broker-mandatory enforcement exists (canonical Planner still has the `allowed = True` line at `action.py:1109`; the Phase-2 quarantine is in stashed orphan state).

### Tests that import from `raphael.*`

`grep -rEn "from raphael|import raphael" tests/` → **0 results**.

No canonical test exercises the raphael.* package. The arena's brain modules (`orchestrator.brain.*`) are tested; the raphael (Head-1) modules are not.

### Tests that import the Runtime

`grep -rEn "from orchestrator.runtime import RaphaelRuntime" tests/` → **0 results**.

No canonical test imports `RaphaelRuntime`. Confirms: no Runtime exists at canonical.
