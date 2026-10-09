# F-SPLIT-1 audit bundle — 2026-10-09

Bundle for the independent review of the split fail-closed correction and its
adjudication. Three patches apply in order onto the frozen baseline
`b6ef24bdb1bb7242613ccdcf6044121fcf3ae38f` (branch `offensive-restore`).

| # | Patch | Commit | Content |
|---|-------|--------|---------|
| 1 | `0001-...patch` | `bd1fcc10946ae18cd1652af66810e2eb7c7b9191` | Fail-closed split resolution (the candidate previously circulated for audit). Configured suite at this commit: 1211 passed / 6 failed (failures expected, see below). |
| 2 | `0002-...patch` | `b76639934` (full hash in SHA256SUMS-verified bundle) | Adjudication of `tests/test_run_identity.py`: helper moved to canonical `"val"`, legacy label refusal pinned at the historical call site. Suite 1218 passed / 0 failed. |
| 3 | `0003-...patch` | `8aebb5211` | Removal of dead `split_of()` seed-range heuristic (its own reviewed change). Suite 1218 passed / 0 failed. |

## Verify

```bash
sha256sum -c SHA256SUMS
git checkout -b review-f-split-1 b6ef24bdb1bb7242613ccdcf6044121fcf3ae38f
git am 0001-*.patch 0002-*.patch 0003-*.patch
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q     # expect 1218 passed
PYTHONPATH=src .venv/bin/python -m pytest tests/test_f_split_1_split_vocabulary.py -q   # expect 74 passed
```

## Questions the reviewer is asked to judge

1. Is the fail-closed change in patch 1 correct and complete (vocabulary derived
   from `ScenarioSplit`, exact-match, resolution first in `__init__`, no fallback
   in `_build_scenario`)?
2. Are valid-label run IDs byte-identical to the baseline? (Reviewer probe: 132
   (config, split, seed) cells compared baseline-vs-candidate, 132 identical —
   reproduce with any cell grid; the run_id format is
   `abl_<config>_<family>_s<seed:04d>_<split>`.)
3. Is the adjudication in patch 2 the right resolution of the six expected
   failures (test intent is logical-cell identity, not the legacy label)?
4. Do the 23 remaining historical `split="validation"` call sites (census in the
   adjudication commit message and in
   `reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md`) require
   operator-level intent adjudication before any rewrite, as recorded?

## Scope notes

- The historical holdout (1,200 vs 3,240 rows) is classified UNVERIFIABLE in
  `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json`; it is out of scope
  for this bundle.
- Policy identity, measurement contract, adoption/decision registry, snapshot
  binding, and F1/F4 are separate work (branch `governance/rsi-1-blockers`),
  not part of this bundle.
