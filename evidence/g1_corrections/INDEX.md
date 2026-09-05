# RC-6: Durable orphan-preservation evidence (G1 correction)

The "orphan" working-tree state is the set of uncommitted changes in the repository at the moment of G1 review. Per the C2 protocol, the orphan must be durably preservable independent of `git stash` (which is fragile, transient, and may be dropped). The canonical P1 method is a content-addressed git tag (`raphael-orphan-phase12-preserved`). The G1-correction method augments this with a **patch file** and **file inventory** captured at G1 review time, so that even if the working tree is later modified, reset, or checked out, the orphan is recoverable from the patch.

## Captured at G1 review (read-only, no modifications)

```
$ git rev-parse HEAD
7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0

$ git status --short --branch
## main...origin/main
 M arena/results/raw/abl_FULL_RAPHAEL_T1_NEGATIVE_CONTROL_s0042_dev/episodes.jsonl
 M arena/results/raw/abl_FULL_RAPHAEL_T1_NEGATIVE_CONTROL_s0099_dev/episodes.jsonl
 M arena/results/raw/abl_FULL_RAPHAEL_T1_NEGATIVE_CONTROL_s0123_dev/episodes.jsonl
 M arena/results/raw/abl_NO_WORLD_MODEL_T1_NEGATIVE_CONTROL_s0003_dev/episodes.jsonl
 M arena/results/raw/abl_NO_WORLD_MODEL_T1_NEGATIVE_CONTROL_s0007_dev/episodes.jsonl
 M arena/results/raw/abl_NO_WORLD_MODEL_T1_NEGATIVE_CONTROL_s0042_dev/episodes.jsonl
 M arena/results/raw/abl_NO_WORLD_MODEL_T1_NEGATIVE_CONTROL_s0099_dev/episodes.jsonl
 M arena/results/raw/abl_PROMPTED_AGENT_T1_NEGATIVE_CONTROL_s0000_dev/episodes.jsonl
 M arena/results/raw/abl_PROMPTED_AGENT_T1_NEGATIVE_CONTROL_s0042_dev/episodes.jsonl
 M arena/results/raw/abl_PROMPTED_AGENT_T1_NEGATIVE_CONTROL_s0099_dev/episodes.jsonl
 M arena/results/raw/abl_PROMPTED_AGENT_T1_NEGATIVE_CONTROL_s0123_dev/episodes.jsonl
 M arena/results/raw/abl_SCRIPTED_BASELINE_T1_NEGATIVE_CONTROL_s0042_dev/episodes.jsonl
 M arena/results/raw/abl_SCRIPTED_BASELINE_T1_NEGATIVE_CONTROL_s0099_dev/episodes.jsonl
 M arena/results/raw/abl_SCRIPTED_BASELINE_T1_NEGATIVE_CONTROL_s0123_dev/episodes.jsonl
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
```

Note: `*22 +4 ?2` interpretation = `unstaged 22, staged 4, untracked 2`. The 22 unstaged are the 14 `episodes.jsonl` regenerations (test outputs, not source) + 8 source modifications. The 4 staged are `A sandbox/__init__.py` + 3 renames. The 2 untracked are `docs/adr/` and `evidence/`.

## Substantive source changes (the 12-file P1 migration set)

Per `evidence/phases/P1/02_migration/migration_diff.txt`:

```
 src/orchestrator/brain/action.py                   |  14 +-
 src/orchestrator/exfil/pipeline.py                 |   3 +-
 src/orchestrator/exploit/pipeline.py               |   3 +-
 src/orchestrator/kali_tools_client.py              |  45 +-
 src/orchestrator/phishing/pipeline.py              |   3 +-
 src/orchestrator/postex/pipeline.py                |   3 +-
 src/orchestrator/sandbox/__init__.py               |   0
 .../{runtime => sandbox}/caido_bootstrap.py        |   0
 .../{runtime => sandbox}/docker_client.py          |   0
 .../{runtime => sandbox}/session_manager.py        |   0
 src/orchestrator/scanners/pipeline.py              |   3 +-
 src/raphael/executor/executor.py                   |  39 +-
 12 files changed, 166 insertions(+), 12 deletions(-)
```

3 file renames (sandbox infra, byte-identical). 5 import path edits. 1 new empty `__init__.py`. 1 comment-only edit (Planner). 2 quarantine additions (SUB-10, SUB-14). 0 test edits. 0 new files in `runtime/` (per C1).

## Durable preservation files (this evidence package)

| File | Purpose | Size |
|---|---|---|
| `evidence/g1_corrections/orphan_preservation.patch` | Full `git diff` of all working-tree changes (tracked). Recoverable by `git apply`. | 4041 lines |
| `evidence/g1_corrections/orphan_preservation_untracked.txt` | `git status --porcelain` of the working tree at G1 review time. | 28 lines |
| `evidence/g1_corrections/untracked_files.txt` | `git ls-files --others --exclude-standard` — list of all untracked files. | 29 lines |
| `evidence/g1_corrections/ADR-011-sandbox-layer-mechanisms-not-authorization.md` | The full ADR-011 document. | 178 lines |

## Recovery procedure (no git operations required)

To recover the orphan from this evidence package at any point in the future, even if the working tree has been reset:

```
# 1. Apply the patch (tracked changes)
cd /home/yaser/external-audits/raphael-2
git apply evidence/g1_corrections/orphan_preservation.patch

# 2. Untracked files must be restored from the orphan tag (durable P1 method)
git show raphael-orphan-phase12-preserved:docs/adr/ADR-011-sandbox-layer-mechanisms-not-authorization.md > docs/adr/ADR-011-sandbox-layer-mechanisms-not-authorization.md
# (and any other untracked paths the operator wants to recover)
```

The patch captures every byte of every modified, added, or renamed tracked file. The untracked files are durably preserved at the `raphael-orphan-phase12-preserved` tag (P1 method, per C2) and additionally by the file inventory in this evidence package.

## Cross-references to durable P1 provenance

- **P1 orphan tag:** `raphael-orphan-phase12-preserved` (object hash `7dd4ec02abd68ec9477509ae15260ddc31d9b3f9`) → commit `4b96049661f5a1f9f1adf1e7e0b5ad1e811577a9` (was `stash@{4}` prior to P1).
- **P1 pre-migration rollback tag:** `raphael-p1-pre-migration-7272880f` (object hash `215c4b76…`) → commit `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`.
- **P0 baseline tag:** `raphael-p0-baseline-7272880f`.
- **P1 post-migration tag:** `raphael-p1-post-migration-7272880f` (created at end of P1; current HEAD is at the same commit `7272880f7…` per C1 — no new commits in P1, the tag is an alias to the canonical commit).

## Evidence sources

- `evidence/g1_corrections/orphan_preservation.patch` (this package)
- `evidence/g1_corrections/orphan_preservation_untracked.txt` (this package)
- `evidence/g1_corrections/untracked_files.txt` (this package)
- `evidence/phases/P1/EVIDENCE_PACKAGE.md` §5.8 (canonical P1 orphan provenance)
