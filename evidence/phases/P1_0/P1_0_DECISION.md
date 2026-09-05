# RAPHAEL P1.0 — Path/Layout Decision Record

Phase: P1.0 (P0.5 transition gate)
Authority: v4.1 master roadmap, AM-4 (seam discipline), AM-7 (invariant activation)
Status: DECISION RECORDED. P1 implementation may begin after this is reviewed.
Investigation: READ-ONLY. No source modified. No stash popped. Evidence in `collision_inventory.md`.

---

## Decision

**Selected option: Option A — split into `runtime/` (orchestration) and `sandbox/` (capability).**

```
src/orchestrator/
├── runtime/                ← P1.1+: CANONICAL ORCHESTRATION LAYER (RaphaelRuntime)
├── sandbox/                ← P1.1: CANONICAL CAPABILITY/SANDBOX LAYER (migrated from runtime/)
├── brain/                  ← unchanged
├── arena/                  ← unchanged
├── student/                ← unchanged
├── modes/                  ← unchanged
├── capabilities/           ← unchanged
├── api/                    ← unchanged (out-of-band FastAPI)
└── ...
```

**Migration strategy: Step 3b (reproduce orphan files from scratch; do NOT `git stash pop`).**

The orphan Phase 1+2 stash (`stash@{2}`) is used as a **read-only reference**. P1 reads the orphan's `loop.py`, `types.py`, and `__init__.py` to understand the design, then writes new files at the now-empty `src/orchestrator/runtime/` path. The orphan is never popped. P1 also reproduces the orphan's quarantine work in the 4 non-Runtime files (Phase 4a) and 2 Runtime-dependent files (Phase 4b) by re-creating the diffs in fresh edits, not by popping the stash.

---

## Why this option

| Criterion | Option A (chosen) | Option B | Option C | Option E (fallback) |
|---|---|---|---|---|
| Architectural fit | **High** — orchestration vs. capability are distinct layers | Medium | Medium-Low | Depends |
| Blast radius | 5 one-line import edits + 3 file moves | 4 file renames + 4 consumer updates | 7 files + pyproject.toml | 0 (discard orphan) |
| Risk to existing tests | **Zero** (canonical tests don't import the runtime package or the 5 sandbox pipelines) | Zero | Zero | Zero |
| Risk to existing code | **Low** (mechanical edits, no behavior change) | Low | Medium (package config change) | None |
| Honesty to v4.1 | **High** (L7: sandbox below broker — the path names reflect that) | Medium | Low (top-level collision risk) | High (no orphan work preserved) |
| Honesty to orphan | **High** (reproduces the orphan's Runtime work; sandbox preserved) | High | High | Low (discards work) |
| Risk of silent loss | **Zero** (git-mv preserves content; orphan never popped) | Zero | Zero | None (orphan discarded intentionally) |
| Implementation cost | ~2 hours of mechanical work | ~2 hours | ~3 hours | ~4 hours (rebuild from scratch) |

**Decision rationale:** Option A is the only option that simultaneously:
1. Maps to the architectural layer boundary the v4.1 design implies.
2. Preserves all canonical sandbox content (Caido/Docker/session) without silent loss.
3. Preserves the orphan's Runtime design without the git-stash pop risk.
4. Has the smallest behavioral risk and the smallest blast radius.

---

## Constraints honored

- **L1 (one unified cognitive core):** Runtime is the single orchestrator. ✓
- **L4 (Head 2 canonical cognition):** Brain unchanged. Runtime composes from it. ✓
- **L7 (capability/sandbox below broker):** Sandbox is now in `orchestrator.sandbox/`, clearly below the broker layer. ✓
- **L8 (single canonical execution boundary):** Runtime's `_authorize` is broker-only. Sandbox is reached through broker-gated capabilities. ✓
- **L12 (seam must be welded, not permanent):** Runtime is the destination, not the seam itself. P3 closes the seam. ✓
- **v4.1 AM-4 (positive interface + weld discipline):** the seam contract is recorded in §3 of `collision_inventory.md`. P3 will weld it.
- **v4.1 AM-7 (invariant activation phases):** the path decision is recorded before P1 implementation begins, satisfying the "invariant state explicit" requirement.

---

## Rollback point

**Pre-migration tag:** `raphael-p1-pre-migration-7272880f`
- Tag hash: `215c4b76f685e1c15b9161b974c3c5da458d5db7`
- Target commit: `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` (canonical P0 baseline, unchanged)
- Created: this P1.0 session

**Rollback procedure** (if migration goes wrong):
```
git reset --hard raphael-p1-pre-migration-7272880f
```

This restores the working tree to the exact P0-baseline state (no `runtime/{loop.py,types.py}`, no `sandbox/`, all 5 importers still pointing at the old path). Orphan stash is unaffected (stashes live outside the working tree).

---

## What P1.0 does NOT authorize

- P1.0 does NOT begin implementation.
- P1.0 does NOT pop the orphan stash.
- P1.0 does NOT modify any source file.
- P1.0 does NOT proceed to P2.

P1.0's deliverable is **the path/layout decision recorded above, the evidence inventory in `collision_inventory.md`, and the pre-migration tag for safe rollback**. P1 implementation (the work described in Steps 1–6 of the inventory) requires separate authorization.

---

## File summary

```
evidence/phases/P1_0/
├── P1_0_DECISION.md                (this file, top-level summary)
└── collision_inventory.md          (full evidence: 5 sections, 13 sections, 18 file operations)
```

---

## Reviewer checklist

Before approving P1 implementation to begin, the reviewer (GLM gate lane) should confirm:

- [ ] Option A's architectural fit has been considered against the v4.1 locked decisions (L1, L4, L7, L8, L12).
- [ ] The 5 sandbox importers have been individually verified to be unreachable from canonical entry points.
- [ ] The migration sequence (Steps 0–6 in `collision_inventory.md`) is acceptable.
- [ ] The "do NOT `git stash pop`" constraint is acceptable (i.e., reproducing orphan work is acceptable cost).
- [ ] The pre-migration tag (`raphael-p1-pre-migration-7272880f`) is acknowledged as the rollback point.
- [ ] The orphan stash (`stash@{2}`) may be retained as a reference for P1.1+, or may be dropped after P1 completes (operator decision).
- [ ] The 4 quarantine marker files (Phase 4a) and 2 runtime-dependent files (Phase 4b) are listed in the migration sequence, with their independence from Runtime noted.

If any item is rejected, the decision is reconsidered. P1.0 halts.
