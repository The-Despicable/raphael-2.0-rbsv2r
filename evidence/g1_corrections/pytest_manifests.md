# RC-4: Legacy pytest --collect-only -q manifest + separate P1 test manifest

Command run (read-only):
```
PYTHONPATH=src python3 -m pytest tests/ --collect-only -q
```

Result: **239 tests collected in 0.92s** (matches FLOOR(P0) and FLOOR(P1) per `evidence/phases/P1/05_test_floor/FLOOR_COMPARISON.md`).

## Artifacts

- `evidence/g1_corrections/pytest_legacy_manifest.txt` — full `pytest --collect-only -q` output, all 239 tests, unfiltered. This is the **legacy** manifest: it is the canonical P0 test floor preserved through P1, with zero test edits (per C7).
- `evidence/g1_corrections/pytest_p1_manifest.txt` — 83-line subset of the same collection output, filtered for P1-related test names. This is the **P1** manifest.

## P1 test manifest (filter rationale)

The P1 manifest is the subset of the 239-test floor whose names reference P1 seam/broker/quarantine/authorize semantics. Per C7, P1 introduces **no new test files**; the seam work is verified by floor preservation (no regression) plus the seam manifest. The filter is therefore a *labeling* of which existing tests are P1-relevant, not a separate test set.

Filter applied: case-insensitive match for any of: `broker|executor|seam|bypass|shell|quarantine|authorize|orchestrator`.

83 of 239 tests match. The P1 manifest is a superset of:
- `e1_interactive_shell_test.py` (34 tests; includes the Weld-SHELL candidate test `test_adversarial_unauthorized_callback` which broke when the shell quarantine was applied in P1 and caused SD-1)
- `e2_shell_candidate_generation_test.py` (36 tests; shell/SSH/reverse-shell candidate generation)
- `test_prompted_agent_parity.py` (6 tests; candidate generation parity)
- `test_prompted_agent_repair.py` (10 tests; candidate generation repair)
- plus 7 additional tests in other files that reference broker/authorize/executor

## P1 introduces zero new tests (per C7, per EVIDENCE_PACKAGE §5.4)

> "P1 is a packaging + seam-quarantine phase. The seam work is verified by:
>  - Floor preservation (no regression),
>  - Import-graph evidence (post-migration dependency direction),
>  - Direct invocation tests in this session (e.g., `_run_local` raises `KaliBypassNotAuthorized` when `_BYPASS_AUTHORIZED=False`).
> No P1-specific test file is created in P1."

The P1 manifest is therefore an annotated subset of the legacy manifest, not an independent set. The two manifests are identical in content modulo the filter.

## Floor comparison (from `evidence/phases/P1/05_test_floor/FLOOR_COMPARISON.md`)

| Metric | Pre-P1 (P0 baseline) | Post-P1 (working tree) | Delta |
|---|---|---|---|
| Passed | 239 | 239 | 0 |
| Failed | 0 | 0 | 0 |
| Skipped | 0 | 0 | 0 |
| xfailed | 0 | 0 | 0 |
| Warnings | 26 | 26 | 0 |
| Duration | 3.78s | 3.72s | -0.06s |

## Evidence sources

- `evidence/g1_corrections/pytest_legacy_manifest.txt` (239 lines)
- `evidence/g1_corrections/pytest_p1_manifest.txt` (83 lines)
- `evidence/phases/P1/05_test_floor/FLOOR_COMPARISON.md` (canonical P1 floor comparison)
- `evidence/phases/P1/EVIDENCE_PACKAGE.md` §5.4 (C7 test floor)
