# P1 — Test floor comparison (per C7)

Per C7: "Preserve the full P0 test floor with zero test edits, run the P1 test set, produce import-graph evidence, and complete the Evidence Package before the post-migration tag."

## Floor runs

### Pre-migration (before any P1 edit)

```
$ cd /home/yaser/external-audits/raphael-2
$ git rev-parse HEAD
7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0

$ PYTHONPATH=src python3 -m pytest tests/ --no-header -q
239 passed, 26 warnings, 3.78s
```

### Post-migration (after all P1 edits, before post-migration tag)

```
$ git status --short --branch
## main...origin/main
 M src/orchestrator/brain/action.py
 M src/orchestrator/exfil/pipeline.py
 M src/orchestrator/exploit/pipeline.py
 M src/orchestrator/kali_tools_client.py
 M src/orchestrator/phishing/pipeline.py
 M src/orchestrator/postex/pipeline.py
A  src/orchestrator/sandbox/__init__.py
R  src/orchestrator/runtime/caido_bootstrap.py -> src/orchestrator/sandbox/caido_bootstrap.py
R  src/orchestrator/runtime/docker_client.py -> src/orchestrator/sandbox/docker_client.py
R  src/orchestrator/runtime/session_manager.py -> src/orchestrator/sandbox/session_manager.py
 M src/orchestrator/scanners/pipeline.py
 M src/raphael/executor/executor.py
?? docs/adr/
?? evidence/

$ PYTHONPATH=src python3 -m pytest tests/ --no-header -q
239 passed, 26 warnings, 3.72s
```

## Comparison

| Metric | Pre-P1 (P0 baseline) | Post-P1 (working tree) | Delta |
|---|---|---|---|
| Passed | 239 | 239 | 0 |
| Failed | 0 | 0 | 0 |
| Skipped | 0 | 0 | 0 |
| xfailed | 0 | 0 | 0 |
| Warnings | 26 | 26 | 0 |
| Duration | 3.78s | 3.72s | -0.06s (within noise) |

**Floor is preserved.** No regressions. No new tests. No test edits.

## Floor-monotonicity (AM-6)

- No test was deleted, skipped, marked xfail, narrowed in assertion scope, or otherwise weakened.
- No test's import path was changed (the 5 pipeline files imported in `if TYPE_CHECKING:` blocks were updated, but those blocks are at the file's top and don't affect test behavior).
- The only test-touching change would have been the shell-capability quarantine, which broke one test; that quarantine was reverted (SD-1).

## Per-test verification (sanity)

The full test set was run, not just a subset. The canonical P0 inventory of test files is:

| Test file | P0 result | P1 result |
|---|---|---|
| `e1_interactive_shell_test.py` | 34 passed | 34 passed |
| `e2_shell_candidate_generation_test.py` | 36 passed | 36 passed |
| `test_budget_contract.py` | 6 passed | 6 passed |
| `test_cli_smoke.py` | 26 passed (warnings) | 26 passed (warnings) |
| `test_conclusion_infra.py` | 5 passed | 5 passed |
| `test_d5_preflight.py` | 10 passed | 10 passed |
| `test_d5_seven_gate_proof.py` | 1 passed | 1 passed |
| `test_debug_stderr_epipe.py` | 4 passed | 4 passed |
| `test_environment_determinism.py` | 4 passed | 4 passed |
| `test_evaluator_isolation.py` | 7 passed | 7 passed |
| `test_gate_b_action_accounting.py` | 10 passed | 10 passed |
| `test_llm_transport.py` | 20 passed | 20 passed |
| `test_noop_contract.py` | 8 passed | 8 passed |
| `test_prompted_agent_parity.py` | 6 passed | 6 passed |
| `test_prompted_agent_repair.py` | 10 passed | 10 passed |
| `test_rbs_v2_repairs.py` | 6 passed | 6 passed |
| `test_repair_gate.py` | 4 passed | 4 passed |
| `test_run_identity.py` | 7 passed | 7 passed |
| `test_safety_telemetry.py` | 5 passed | 5 passed |
| `test_stage1_invariants.py` | 14 passed | 14 passed |
| `test_token_telemetry.py` | 12 passed | 12 passed |
| `test_tool_failure_provenance.py` | 4 passed | 4 passed |
| **TOTAL** | **239 passed** | **239 passed** |

(Per-file counts derived from `pytest --collect-only` at canonical; P1's `--collect-only` produces the same 239 tests.)

## P1 introduces no new tests

P1 is a packaging + seam-quarantine phase. The seam work is verified by:
- Floor preservation (no regression),
- Import-graph evidence (post-migration dependency direction),
- Direct invocation tests in this session (e.g., `_run_local` raises `KaliBypassNotAuthorized` when `_BYPASS_AUTHORIZED=False`).

No P1-specific test file is created in P1. The next test creation happens in P2 (when Runtime is born and seam behavior needs pytest coverage per C7's "run the P1 test set" interpretation — but P1's test set is the unchanged P0 floor, since P1 introduces no new testable code paths beyond quarantine raises).
