# G1 Corrections Evidence Package (RC-1 through RC-6)

Phase: P1 (canonical runtime packaging + seam work)
Repository root: `/home/yaser/external-audits/raphael-2`
HEAD (canonical, unchanged): `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
Working-tree state at G1 review: 22 unstaged, 4 staged (3 renames + 1 add), 2 untracked (`docs/adr/`, `evidence/`)
G1 verdict: **CONDITIONAL PASS** (per user's prior message). RC-1 through RC-6 below are the corrections submitted for G1 confirmation.

## RC-1 — WRAPPED vs WELDED status for every seam site
→ `evidence/g1_corrections/seam_status_WRAPPED_vs_WELDED.md`

**Verdict:** 2 WRAPPED (SUB-10, SUB-14), 0 WELDED (welding is P3), 1 DEFERRED (Weld-SHELL, SD-1, C7 conflict). 15 P0 subprocess sites are not seam sites (UNREACHABLE_FROM_CANONICAL, P9 cleanup).

## RC-2 — Reconcile 10 confirmed bypasses + 17 subprocess sites to P0 Path IDs
→ `evidence/g1_corrections/bypass_subprocess_reconciliation.md`

**Verdict:** 2 of 10 bypasses map to subprocess Path IDs and are WRAPPED (Candidate 1 → SUB-14, Candidate 2 → SUB-10). 1 of 10 maps to capability Path ID and is DEFERRED (Candidate 3 → Weld-SHELL). Remaining 7 are non-execution-site (comments, dormant classes, stubs) or infrastructure (broken symlinks, broken paths) — recorded, not seam-wrapped. All 17 subprocess sites are accounted for; no orphan seams.

## RC-3 — Real pre/post import graph
→ `evidence/g1_corrections/import_graph_pre.txt` (HEAD, 436 files)
→ `evidence/g1_corrections/import_graph_post.txt` (working tree, 440 files)
→ `evidence/g1_corrections/import_graph_diff.txt` (the 2-line unified diff of changed import lines)
→ `evidence/g1_corrections/import_graph_summary.md` (analysis)

**Verdict:** ADDED=4 (sandbox package), CHANGED=5 (5 single-line TYPE_CHECKING-block import updates), REMOVED=0. Dependency direction (per ADR-011) verified: `runtime/ → brain/ → capabilities/ → sandbox/` with no reverse deps.

## RC-4 — Legacy pytest --collect-only -q manifest + separate P1 test manifest
→ `evidence/g1_corrections/pytest_legacy_manifest.txt` (full 239-test collection, unfiltered)
→ `evidence/g1_corrections/pytest_p1_manifest.txt` (83-line subset filtered for P1 seam/broker/quarantine/authorize semantics)
→ `evidence/g1_corrections/pytest_manifests.md` (analysis)

**Verdict:** 239 tests collected in 0.92s, matching FLOOR(P0) and FLOOR(P1) per `evidence/phases/P1/05_test_floor/FLOOR_COMPARISON.md`. P1 introduces no new test files (per C7); the P1 manifest is a labeled subset of the legacy manifest.

## RC-5 — ADR-011
→ `evidence/g1_corrections/ADR-011-sandbox-layer-mechanisms-not-authorization.md` (full ADR copy)
→ `docs/adr/ADR-011-sandbox-layer-mechanisms-not-authorization.md` (canonical location, untracked)

**Verdict:** ADR-011 is the architectural decision record for P1.0 → P1.1 transition. Status: Accepted (per GLM correction C5). Establishes `src/orchestrator/sandbox/` as mechanisms-only (not the authorization boundary), `src/orchestrator/runtime/` as the orchestration layer, dependency direction `runtime/ → brain/ → capabilities/ → sandbox/`, and the P3 importer contraction from 5 → 1 SandboxSession sites.

## RC-6 — Durable orphan-preservation evidence
→ `evidence/g1_corrections/orphan_preservation.patch` (4041-line full `git diff`)
→ `evidence/g1_corrections/orphan_preservation_untracked.txt` (`git status --porcelain` at G1 review)
→ `evidence/g1_corrections/untracked_files.txt` (`git ls-files --others --exclude-standard`)
→ `evidence/g1_corrections/INDEX.md` (recovery procedure)

**Verdict:** Working-tree state captured durably as a patch + untracked-file inventory. Recovery procedure: `git apply orphan_preservation.patch` + restore untracked files from the `raphael-orphan-phase12-preserved` tag. Independent of `git stash` fragility.

## Files in this evidence package

```
evidence/g1_corrections/
├── EVIDENCE_INDEX.md                                   (this file)
├── seam_status_WRAPPED_vs_WELDED.md                    (RC-1)
├── bypass_subprocess_reconciliation.md                  (RC-2)
├── import_graph_pre.txt                                (RC-3, 880 lines)
├── import_graph_post.txt                               (RC-3, 880 lines)
├── import_graph_diff.txt                               (RC-3, 2 lines)
├── import_graph_summary.md                             (RC-3)
├── pytest_legacy_manifest.txt                          (RC-4, 241 lines, 239 tests)
├── pytest_p1_manifest.txt                              (RC-4, 83 lines)
├── pytest_manifests.md                                 (RC-4)
├── ADR-011-sandbox-layer-mechanisms-not-authorization.md  (RC-5, 178 lines)
├── orphan_preservation.patch                           (RC-6, 4041 lines)
├── orphan_preservation_untracked.txt                   (RC-6, 28 lines)
├── untracked_files.txt                                 (RC-6, 29 lines)
└── INDEX.md                                            (RC-6 recovery procedure)
```

## Stop.

G1 corrections (RC-1 through RC-6) complete. Evidence durably captured at `evidence/g1_corrections/`. Submitting for G1 confirmation. No modifications made to the repository beyond creating the new files in `evidence/g1_corrections/` (which is itself an untracked directory in the orphan state, so adding files to it does not affect the tracked source tree). No resets, checkouts, stashes, commits, or branch switches performed.
