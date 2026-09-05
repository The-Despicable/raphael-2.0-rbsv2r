# RAPHAEL P1.0 — `src/orchestrator/runtime/` Collision Evidence Inventory

Phase: P1.0 (path/layout decision before P1 implementation)
Authority: v4.1 master roadmap (G0=PASS, FOLOR(P0)=239, baseline tag `raphael-p0-baseline-7272880f`)
Status: READ-ONLY INVESTIGATION. No source modified. No stash popped. No new files outside `evidence/phases/P1_0/`.

---

## 1. The collision in one table

The orphan Phase 1+2 stash (`stash@{2}`) and the canonical checkout (`7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`) target the same directory `src/orchestrator/runtime/` with disjoint contents.

| Path (under `src/orchestrator/runtime/`) | Canonical (`7272880f7`) | Orphan stash (`stash@{2}`) | Conflict type |
|---|---|---|---|
| `__init__.py` | Empty (0 bytes, blob `e69de29b`) | Populated, 63 lines, exports `RaphaelRuntime`, `EnvironmentAdapter`, `ComponentBundle`, `BrokerRequiredError`, etc. (blob `c25d647c`) | **MODIFY** — the populated version imports `loop` and `types`; canonical's empty version is harmless but the orphan's version requires siblings. |
| `loop.py` | absent | NEW, 773 lines — `RaphaelRuntime` class | **ADD** — requires `orchestrator.runtime` package to mean "orchestration". |
| `types.py` | absent | NEW, ~57 lines — `ComponentBundle` dataclass | **ADD** — same. |
| `caido_bootstrap.py` | present, 130 lines (blob `b6c4c7d6`) | absent | **DELETE-if-orphan-pops-wholesale** — silent loss unless explicitly migrated first. |
| `docker_client.py` | present, 132 lines (blob `18a646c0`) | absent | **DELETE-if-orphan-pops-wholesale** — silent loss. |
| `session_manager.py` | present, 116 lines (blob `968467e4`) | absent | **DELETE-if-orphan-pops-wholesale** — silent loss. |

**Net effect of `git stash pop` (if it were applied):** Caido bootstrap, Docker client, and Session manager are silently removed from the working tree. They are not tracked by git history after the canonical commit (the only commit touching the path is `7272880f7` itself), so they are not recoverable from git alone once gone.

---

## 2. Inventory: canonical-side dependents of `runtime/{caido_bootstrap,docker_client,session_manager}.py`

### Direct importers (canonical)

```
src/orchestrator/postex/pipeline.py:5     from ..runtime.session_manager import SandboxSession
src/orchestrator/exploit/pipeline.py:5    from ..runtime.session_manager import SandboxSession
src/orchestrator/scanners/pipeline.py:4   from ..runtime.session_manager import SandboxSession
src/orchestrator/exfil/pipeline.py:5      from ..runtime.session_manager import SandboxSession
src/orchestrator/phishing/pipeline.py:4   from ..runtime.session_manager import SandboxSession
```

5 importers, all from sub-pipelines. None import `runtime.caido_bootstrap` or `runtime.docker_client` directly (those are internal to `session_manager.py`).

### Transitive consumers of the pipelines (canonical)

```
src/orchestrator/exploit/mcp_bridge.py:4     from .pipeline import ExploitPipeline
src/orchestrator/exploit/mcp_bridge.py:20    self.pipeline = ExploitPipeline(pg)
src/orchestrator/modes/scan.py:2              from ..scanners.pipeline import ScanPipeline
src/orchestrator/modes/scan.py:26             pipeline = ScanPipeline(pg)
src/cai-service/main.py:131, 158, 201        uses ExploitPipeline, PostExploitPipeline
```

Three of these consumers:
- `src/orchestrator/exploit/mcp_bridge.py` — referenced by `mcp-bridge` service (broken symlink target)
- `src/orchestrator/modes/scan.py` — referenced by `bridge.raphael_bridge` (broken import path)
- `src/cai-service/main.py` — `cai-service` (broken symlink target)

All three are at the ends of broken symlinks (`/home/yaser/raphael-2.0/{mcp-hub,cai-service}`) or broken by `bridge.raphael_bridge`'s hard-coded path. They are reachable in source but no live process executes them.

**Reachability classification (canonical):**
- `runtime.session_manager.SandboxSession` is imported by 5 sub-pipelines.
- The 5 sub-pipelines are only consumed by services behind broken symlinks.
- **Effectively UNREACHABLE from any live canonical entry point** (Arena, Head-1 CLI, modes).

### Package-level `orchestrator.runtime` import (canonical)

```
$ grep -rEn "import orchestrator\.runtime|from orchestrator\.runtime|from orchestrator import runtime" src/ tests/
# (no output)
```

**Zero direct package imports of `orchestrator.runtime`** at canonical. All canonical code that uses the runtime package does so via specific submodules (`from ..runtime.session_manager import ...`). The canonical `runtime/__init__.py` is empty and inert.

---

## 3. Inventory: orphan-side dependents of `runtime/{loop.py,types.py,__init__.py}`

### Direct importers (orphan)

```
src/arena/ablation_runner.py:1870-1874    from orchestrator.runtime import (
                                          RaphaelRuntime, ComponentBundle,
                                          EpisodeState, EnvironmentAdapter,
                                          )
src/raphael/main.py:372-376                from orchestrator.runtime import (
                                            RaphaelRuntime, ComponentBundle,
                                            EpisodeState, EnvironmentAdapter,
                                            )
tests/test_runtime_phase1.py:24-32        from orchestrator.runtime import (...)
tests/test_broker_mandatory_phase2.py:33  from orchestrator.runtime import (...)
```

4 importers (2 source, 2 test), all at module-load time. The orphan's `__init__.py` runs `from orchestrator.runtime.loop import RaphaelRuntime` at package import — so any `import orchestrator.runtime` from any code path will trigger the `loop.py`/`types.py` load.

### Internal dependencies of the orphan's Runtime

```
src/orchestrator/runtime/loop.py:7   from orchestrator.runtime.types import ComponentBundle
src/orchestrator/runtime/types.py:4  (no internal deps)
src/orchestrator/runtime/__init__.py: imports loop + types
```

The orphan's Runtime is self-contained: no arena, no Head-1, no Caido, no Docker dependencies. Only the standard library and `ComponentBundle`.

### Behavioral surface of the orphan's Runtime

The orphan's `RaphaelRuntime`:
- `__init__(components, environment=None, tracer=None, metrics=None)`
- `step(state, view=None, objective_id=None) -> StepResult` — one cognitive iteration
- `run_episode(state, view=..., max_iterations, action_cap) -> EpisodeResult` — full episode loop
- Owns iteration bookkeeping, action history, stop-reason semantics
- Composes (does NOT implement) Planner/Broker/WorldModel/Hypothesis/Contradiction
- Hard-fails on broker absence (`BrokerRequiredError`) per the orphan's Phase 2 hardening

---

## 4. v4.1 architectural constraints

Per the v4.1 master roadmap (locked L1–L20 decisions):

| Constraint | Source | Implication for path choice |
|---|---|---|
| L1 — One unified cognitive core | §1.2 | The Runtime is the single canonical orchestrator. No second orchestrator may exist. |
| L4 — Head 2 (brain) is canonical cognition | §1.4 | `orchestrator/brain/*` (Planner, Broker, WorldModel, etc.) is unchanged. Runtime composes from it, not replaces it. |
| L7 — Capability/sandbox layer below the broker | §5.2, §9 | Caido/Docker/session infrastructure lives below the broker — i.e., in the capability layer (NOT the orchestration layer). |
| L8 — Single canonical execution boundary | §5.2 | The Runtime's `_authorize` is the broker-only path. Sandbox infra must not be reachable from Runtime without going through the broker. |
| L12 — Migration seam must be welded, not permanent | v4.1 AM-4 | The seam is temporary scaffolding; at P3 close it. The Runtime itself is NOT the seam — it is the destination. |
| L15 — Mission/scope/evidence as first-class | §5.5 | New types in P4 attach to Mission objects, not to Runtime. The Runtime's `EpisodeState` is not the same as the future `Mission` object. |

**Architectural read:**

The orphan's `RaphaelRuntime` is the **orchestration layer** (above the brain).
The canonical `caido_bootstrap.py`/`docker_client.py`/`session_manager.py` are the **capability/sandbox layer** (below the broker).

These are **distinct architectural layers**. Their current collision on the same path is a **packaging mistake**, not an architectural one. The right resolution is to **move them to different paths that reflect their architectural role**.

---

## 5. Viable canonical-layout options

Five options for resolving the collision, each evaluated against the v4.1 constraints:

### Option A — Runtime at `src/orchestrator/runtime/`; Caido/Docker/session migrated to `src/orchestrator/sandbox/`

- **Runtime path:** `src/orchestrator/runtime/{__init__.py, loop.py, types.py}` (matches orphan)
- **Sandbox path:** `src/orchestrator/sandbox/{caido_bootstrap.py, docker_client.py, session_manager.py}`
- **Migration cost:** 5 importers need their import paths updated (`from ..runtime.session_manager import SandboxSession` → `from ..sandbox.session_manager import SandboxSession`).
- **Architectural fit:** high. Runtime = orchestration, sandbox = capability below broker — the path names match the layer names.
- **Risk:** low. All 5 importers are inside the `orchestrator` package, so the relative-import rewrite is mechanical. Sandbox content is byte-identical; only the path changes.
- **Test impact:** zero. No test imports `runtime` as a package. The 5 pipeline files are imported by services that are themselves behind broken symlinks (UNREACHABLE from canonical entry points).
- **Verdict:** RECOMMENDED.

### Option B — Runtime at `src/orchestrator/cognition/`; sandbox stays at `src/orchestrator/runtime/`

- **Runtime path:** `src/orchestrator/cognition/{__init__.py, runtime.py, types.py}` (collapsed to fewer files)
- **Sandbox path:** `src/orchestrator/runtime/{__init__.py, caido_bootstrap.py, docker_client.py, session_manager.py}` (unchanged)
- **Migration cost:** orphan's `loop.py` and `types.py` are renamed to `cognition/runtime.py` and `cognition/types.py`. Orphans' `__init__.py` updated.
- **Architectural fit:** MEDIUM. "Cognition" is broader than orchestration (cognition could include the brain too). Naming a sub-package `cognition` invites confusion with `orchestrator.brain`.
- **Risk:** LOW for collision resolution. Naming overlap with `brain` is a long-term concern.
- **Verdict:** acceptable but not preferred.

### Option C — Runtime at top-level `src/runtime/`; sandbox stays at `src/orchestrator/runtime/`

- **Runtime path:** `src/runtime/{__init__.py, loop.py, types.py}`
- **Sandbox path:** `src/orchestrator/runtime/...` (unchanged)
- **Migration cost:** orphan's files moved up one level. Orphans' consumers (`arena/ablation_runner.py`, `raphael/main.py`, two test files) updated to `from src.runtime import ...` or with new package layout.
- **Architectural fit:** MEDIUM-LOW. `src/runtime/` is too generic — multiple sub-systems could claim it.
- **Risk:** MEDIUM. Top-level paths are visible in pip-install scenarios; an unqualified `runtime` name could collide with third-party packages.
- **Verdict:** NOT RECOMMENDED.

### Option D — Runtime absorbed into `orchestrator.brain` as a sub-module

- **Runtime path:** `src/orchestrator/brain/runtime/{__init__.py, loop.py, types.py}` or `src/orchestrator/brain/runtime.py` (single file)
- **Sandbox path:** `src/orchestrator/runtime/...` (unchanged)
- **Migration cost:** orphan's `loop.py`+`types.py` move to `orchestrator.brain.runtime`.
- **Architectural fit:** LOW. Violates L4 (Head 2 is canonical cognition; Runtime is the orchestrator that composes cognition — they are different layers).
- **Risk:** HIGH. Conflating orchestration with cognition breaks L1 and L4.
- **Verdict:** VIOLATES LOCKED DECISIONS. NOT AN OPTION.

### Option E — Runtime stays in orphan stash; canonical sandbox stays as-is; P1 builds Runtime elsewhere from scratch

- **Runtime path:** TBD (P1 designer picks a path that avoids collision)
- **Sandbox path:** `src/orchestrator/runtime/...` (unchanged)
- **Migration cost:** orphan work is rejected in its current form. P1 must rebuild `RaphaelRuntime` from scratch at a new path. ~1000 lines of orphan code is discarded.
- **Architectural fit:** depends on path choice — but discarding orphan work is wasteful.
- **Risk:** HIGH (lost work), but lower implementation risk (no collision).
- **Verdict:** FALLBACK ONLY if Option A is rejected. Wastes 4 hours of prior work.

---

## 6. Dependency / import consequences of each viable option

### Option A (RECOMMENDED) — split into `runtime/` (orchestration) and `sandbox/` (capability)

**5 importers need a one-line import-path update:**

```python
# Before (canonical)
from ..runtime.session_manager import SandboxSession

# After (Option A)
from ..sandbox.session_manager import SandboxSession
```

Affected files (all in `src/orchestrator/`):
- `postex/pipeline.py:5`
- `exploit/pipeline.py:5`
- `scanners/pipeline.py:4`
- `exfil/pipeline.py:5`
- `phishing/pipeline.py:4`

**The orphan's Runtime imports are unaffected** (orphan stays in `runtime/`).

**Tests:** the 2 orphan tests (`test_runtime_phase1.py`, `test_broker_mandatory_phase2.py`) only import from `orchestrator.runtime`; no change. None of the canonical 239 tests touch the runtime package or the 5 pipelines at all.

**Blast radius:** 5 files, each a single-line change. Mechanical. No behavior change in P1 (the change is path-only, P1 is allowed to do this as part of the path decision).

### Option B — Runtime at `cognition/`, sandbox stays

**Orphan files renamed:** `loop.py` → `cognition/runtime.py`; `types.py` → `cognition/types.py`.

**Orphan's `__init__.py` updated:** `from .cognition.runtime import RaphaelRuntime` → wait, that's wrong. The orphan's `__init__.py` is `from .loop import ...`. Renamed to `from .cognition.runtime import ...` (relative) or `from orchestrator.cognition.runtime import ...` (absolute).

**Orphan's `loop.py` `__init__.py` import:** `from .types import ComponentBundle` → `from .types` (unchanged, still sibling).

**2 consumers (`arena/ablation_runner.py`, `raphael/main.py`) updated:** `from orchestrator.runtime import ...` → `from orchestrator.cognition import ...`.

**Tests updated:** the 2 orphan tests.

**Sandbox path unchanged:** 5 importers of `SandboxSession` stay as-is.

**Blast radius:** 4 orphan files renamed + 4 consumers updated. Slightly more files than Option A but fewer behavioral concerns.

### Option C — Runtime at top-level `src/runtime/`

**Layout:**

```
src/
├── runtime/                    ← NEW (orphan moves here)
│   ├── __init__.py
│   ├── loop.py
│   └── types.py
├── orchestrator/
│   ├── runtime/                ← existing (canonical, sandbox)
│   │   ├── __init__.py
│   │   ├── caido_bootstrap.py
│   │   ├── docker_client.py
│   │   └── session_manager.py
│   ├── arena/
│   ├── brain/
│   ├── ...
```

**Concerns:**
- `src/runtime/` collides with Python's stdlib `runtime` references in some test frameworks.
- `src.runtime` is not a recognized sub-package by the existing `pyproject.toml` package discovery (`[tool.setuptools.packages.find] where=["src"], include=[..., "benchmarks*"]`). P1 must update `pyproject.toml`.
- Test discovery (`pytest` collect) walks `src/` — a top-level `src/runtime/` adds one more package to walk.

**Blast radius:** pyproject.toml update + 4 consumers + 2 tests = 7 files, plus infrastructure (setuptools config).

### Option D (REJECTED) — collides with L4

Skipped: violates locked decisions.

### Option E (FALLBACK) — discard orphan work, build Runtime elsewhere

Orphan work (~1000 lines) is discarded. P1 rebuilds `RaphaelRuntime` from scratch at a new path. Highest wasted-work cost. Acceptable only if the orphan's design is fundamentally wrong (it is not — the orphan follows v4.1 exactly).

---

## 7. Recommended layout (Option A)

```
src/orchestrator/
├── runtime/                          ← CANONICAL ORCHESTRATION LAYER (v4.1 RaphaelRuntime)
│   ├── __init__.py                   (orphan: 63 lines, exports)
│   ├── loop.py                       (orphan: 773 lines, RaphaelRuntime)
│   └── types.py                      (orphan: 57 lines, ComponentBundle)
│
├── sandbox/                          ← CANONICAL CAPABILITY/SANDBOX LAYER (below broker)
│   ├── __init__.py                   (NEW, empty, marks package boundary)
│   ├── caido_bootstrap.py            (canonical: 130 lines, from src/orchestrator/runtime/)
│   ├── docker_client.py              (canonical: 132 lines, from src/orchestrator/runtime/)
│   └── session_manager.py            (canonical: 116 lines, from src/orchestrator/runtime/)
│
├── brain/                            ← CANONICAL COGNITION (Planner, Broker, WorldModel, ...)
├── arena/                            ← evaluation harness (drives Runtime after P2)
├── student/                          ← S-Series (per v4.1, activated in P7)
├── modes/                            ← CLI mode handlers
├── capabilities/                     ← E-Series (SSH, reverse shell, filters)
├── api/                              ← FastAPI service (out-of-band, not canonical)
├── ...
```

**Path semantics:**

- `orchestrator.runtime` = orchestration (the brain loop composer)
- `orchestrator.sandbox` = capability/sandbox infra (below broker, per L7)
- `orchestrator.brain` = cognition (Planner, Broker, WorldModel, ...) — unchanged

**Why this is consistent with v4.1:**

- **L1 (one unified cognitive core):** Runtime is the single orchestrator. ✓
- **L4 (Head 2 canonical):** Brain unchanged. Runtime composes from it. ✓
- **L7 (capability/sandbox below broker):** Sandbox layer is below the broker. ✓
- **L8 (single canonical execution boundary):** Runtime's `_authorize` is broker-only; sandbox is reached through broker-gated capabilities. ✓
- **L12 (seam must be welded, not permanent):** Runtime is the destination, not the seam itself. The seam is the bridge from Arena's inlined loop to the Runtime (P3 closes it). ✓

---

## 8. Proposed migration sequence for recovering the orphan Runtime work

The sequence below is **a proposed plan**, not yet executed. Each step is independently auditable; a failure at any step halts the sequence and the previous canonical state is recovered.

### Step 0 — Pre-migration snapshot (REQUIRED before any code movement)

```
git tag -a raphael-p1-pre-migration-7272880f 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0 \
    -m "RAPHAEL P1.0 pre-migration snapshot — v4.1 P0 baseline, no changes applied"
```

If migration goes wrong, recovery is `git reset --hard raphael-p1-pre-migration-7272880f`.

### Step 1 — Migrate the 3 canonical sandbox files to a new path (BEFORE introducing the orphan)

```
mkdir -p src/orchestrator/sandbox
git mv src/orchestrator/runtime/caido_bootstrap.py src/orchestrator/sandbox/
git mv src/orchestrator/runtime/docker_client.py   src/orchestrator/sandbox/
git mv src/orchestrator/runtime/session_manager.py src/orchestrator/sandbox/
touch src/orchestrator/sandbox/__init__.py
```

**Verify after:** `src/orchestrator/runtime/` now contains only `__init__.py` (empty). The 5 importers of `SandboxSession` are now BROKEN (the path is wrong). This is acceptable for this transient step because:

- All 5 importers are inside pipelines that are themselves only consumed by services behind broken symlinks.
- No canonical entry point (Arena, CLI, modes) loads any of these 5 files.
- The 239-test baseline does not import them.
- The 5 files are momentarily dead — we restore them in step 3.

```
# Verify baseline still green
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: 239 passed (5 imports broken, but no test loads them)
```

If baseline FAILS: STOP. Investigate which canonical test path loads the sandbox pipeline. Document and escalate.

### Step 2 — Update the 5 importers' import paths

For each of these 5 files, change `from ..runtime.session_manager import SandboxSession` to `from ..sandbox.session_manager import SandboxSession`:

```
src/orchestrator/postex/pipeline.py:5
src/orchestrator/exploit/pipeline.py:5
src/orchestrator/scanners/pipeline.py:4
src/orchestrator/exfil/pipeline.py:5
src/orchestrator/phishing/pipeline.py:4
```

```
# Verify baseline still green after the 5 edits
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: 239 passed (5 importers fixed, no test path loads them, but
# the path is now correct for any future caller)
```

### Step 3 — Recover the orphan Runtime work

Two viable sub-options:

**3a. Apply the orphan to the now-empty `src/orchestrator/runtime/`:**

The orphan's `__init__.py`, `loop.py`, `types.py` are designed to live in this path. With the 3 sandbox files now at `sandbox/`, the path is no longer conflicting. Apply the orphan by:

```
# Cherry-pick only the runtime/ subtree from the orphan stash
git checkout stash@{2}^3 -- src/orchestrator/runtime/loop.py \
                              src/orchestrator/runtime/types.py
git checkout 4b96049661f5a1f9f1adf1e7e0b5ad1e811577a9 -- \
    src/orchestrator/runtime/__init__.py
```

**3b. (Safer) Do not pop the stash at all.** Leave the orphan work in `stash@{2}` and let P1 work directly with the orphan files as a reference. P1 then writes the Runtime from scratch, mirroring the orphan's design, into `src/orchestrator/runtime/{__init__.py, loop.py, types.py}`. This loses nothing (P1 still produces the same code) but avoids any git-stash pop risk.

**Recommendation:** Step 3b is safer. The orphan is already audited (its code was reviewed in the prior P1 work); the design is known-good. P1 produces the same files from scratch in the now-empty path. This is a 2-hour cost to gain the safety of "no git-stash pop, ever."

### Step 4 — Recover the orphan's quarantine markers (independent of Runtime)

The orphan's quarantine work is on 4 files:

- `src/arena/ablation_runner.py` (seam, depends on Runtime) — apply ONLY after Step 3
- `src/orchestrator/brain/action.py` (Planner documented as non-authoritative) — independent of Runtime
- `src/orchestrator/capabilities/interactive_shell/capability.py` (shell bypass) — independent
- `src/orchestrator/kali_tools_client.py` (kali local bypass) — independent
- `src/raphael/executor/executor.py` (Head-1 subprocess bypass) — independent
- `src/raphael/main.py` (CLI seam) — depends on Runtime
- `tests/e1_interactive_shell_test.py` (test update for shell bypass opt-in) — independent

**Apply non-Runtime quarantine changes first (Step 4a), then Runtime-dependent changes (Step 4b).**

**4a. Independent quarantine changes** — these can be applied immediately. They:
- Add `BypassNotAuthorized` exception class
- Add `_bypass_authorized = False` flag
- Add `authorize_bypass(reason=...)` opt-in method
- Add quarantine gate at the bypass site
- Document intent in docstrings
- Do NOT change behavior of the canonical execution path; tests without opt-in will now raise `BypassNotAuthorized` instead of executing

```
# After Step 4a, the existing 239 tests must STILL pass (tests don't
# invoke the bypasses, so the new gate has no effect on them)
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: 239 passed
```

The 1 test that does invoke the bypass (`tests/e1_interactive_shell_test.py:test_adversarial_unauthorized_callback`) needs the orphan's opt-in call. Apply the test update as part of Step 4a.

**4b. Runtime-dependent quarantine changes** — `src/arena/ablation_runner.py` and `src/raphael/main.py` depend on `from orchestrator.runtime import ...`. Apply AFTER Step 3.

### Step 5 — Verification

```
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: ≥239 passed (the orphan's 2 new test files bring the total to 253)
```

If baseline FAILURES appear: STOP. Diff against the snapshot. Identify which step introduced the regression. Revert that step only. Document and escalate.

### Step 6 — Tag the post-migration state

```
git tag -a raphael-p1-post-migration-7272880f HEAD \
    -m "RAPHAEL P1.0 post-migration — Runtime recovered at canonical path, sandbox migrated to orchestrator/sandbox/"
```

---

## 9. Decision (P1.0)

**Chosen option: Option A — split into `runtime/` (orchestration) and `sandbox/` (capability).**

**Migration path: Step 3b (P1 reproduces orphan files from scratch in the now-empty `runtime/` path; no `git stash pop`).**

**Rationale:**

1. **Architectural correctness:** the two layers serve different purposes; their current path collision is a packaging mistake. Splitting makes the architecture self-documenting at the directory level.
2. **Zero behavior change in the live runtime:** the migration is path-only. P1 starts with the same 239-test green baseline, the same 17-bypass inventory, the same Arena-only broker mediation.
3. **Zero risk to existing tests:** none of the 239 canonical tests import from `orchestrator.runtime` as a package. None of the 5 pipelines that import `SandboxSession` are exercised by tests. The migration is invisible to the test suite.
4. **Minimum blast radius:** 5 one-line import-path edits + 3 file moves. Mechanical. Auditable per-step. Rollback is `git reset --hard` to a pre-migration tag.
5. **Honors the orphan's design without the stash pop risk:** the orphan's Runtime code is reproduced verbatim in P1 (P1 reads the stash as reference). The orphan's quarantine code is also reproduced. P1 never runs `git stash pop`.
6. **Caido/Docker/session are not "displaced without an explicit architectural decision"** — they are migrated to a new path with full content preservation. Per v4.1, this is the explicit architectural decision being recorded in this evidence package.

---

## 10. Affected paths summary

| Path | Before migration | After migration | Action class |
|---|---|---|---|
| `src/orchestrator/runtime/__init__.py` | empty (0 bytes) | populated (P1 writes) | REPRODUCE (orphan as reference) |
| `src/orchestrator/runtime/loop.py` | absent | P1 writes | REPRODUCE |
| `src/orchestrator/runtime/types.py` | absent | P1 writes | REPRODUCE |
| `src/orchestrator/sandbox/__init__.py` | (path does not exist) | empty (P1 writes) | NEW |
| `src/orchestrator/sandbox/caido_bootstrap.py` | `src/orchestrator/runtime/caido_bootstrap.py` | moved | MIGRATE (content unchanged) |
| `src/orchestrator/sandbox/docker_client.py` | `src/orchestrator/runtime/docker_client.py` | moved | MIGRATE (content unchanged) |
| `src/orchestrator/sandbox/session_manager.py` | `src/orchestrator/runtime/session_manager.py` | moved | MIGRATE (content unchanged) |
| `src/orchestrator/postex/pipeline.py:5` | `from ..runtime.session_manager import ...` | `from ..sandbox.session_manager import ...` | EDIT (1 line) |
| `src/orchestrator/exploit/pipeline.py:5` | same | same | EDIT (1 line) |
| `src/orchestrator/scanners/pipeline.py:4` | same | same | EDIT (1 line) |
| `src/orchestrator/exfil/pipeline.py:5` | same | same | EDIT (1 line) |
| `src/orchestrator/phishing/pipeline.py:4` | same | same | EDIT (1 line) |
| `src/orchestrator/brain/action.py` | canonical | quarantine comment added | EDIT (Phase 4a, after P1 produces Runtime) |
| `src/orchestrator/capabilities/interactive_shell/capability.py` | canonical | quarantine markers added | EDIT (Phase 4a) |
| `src/orchestrator/kali_tools_client.py` | canonical | quarantine markers added | EDIT (Phase 4a) |
| `src/raphael/executor/executor.py` | canonical | quarantine markers added | EDIT (Phase 4a) |
| `src/raphael/main.py` | canonical | CLI seam added | EDIT (Phase 4b, depends on Runtime) |
| `src/arena/ablation_runner.py` | canonical | runtime-via-runtime seam added | EDIT (Phase 4b, depends on Runtime) |
| `tests/e1_interactive_shell_test.py` | canonical | test opt-in updated | EDIT (Phase 4a) |
| `tests/test_runtime_phase1.py` | absent (orphan) | P1 writes | NEW |
| `tests/test_broker_mandatory_phase2.py` | absent (orphan) | P1 writes | NEW |

**Net effect:**

- 3 file moves (sandbox infra → new path)
- 5 one-line import edits
- 4 quarantine-only source edits (Phase 4a)
- 2 runtime-seam source edits (Phase 4b)
- 1 test opt-in edit
- 2 new test files
- 2 new sandbox `__init__.py` and runtime `__init__.py`

**Total: 7 source edits + 5 import edits + 3 moves + 3 new files = 18 file operations across 4 phases (Steps 0–6).** Each operation is independently auditable and rollback-safe.

---

## 11. What P1.0 explicitly does NOT do

- Does NOT pop the orphan stash (`git stash pop`).
- Does NOT modify the orphan files in place.
- Does NOT introduce new behavior.
- Does NOT write any Runtime or quarantine code (that is P1.1+, not P1.0).
- Does NOT close any bypass (that is P3).
- Does NOT activate the migration seam (that is P2).
- Does NOT retire `AdaptiveBrain` (that is P2).
- Does NOT begin Head 1 migration (that is P9).
- Does NOT proceed to P2.

P1.0's deliverable is **this evidence artifact and the recorded path/layout decision**, with an explicit migration sequence that P1 may follow.

---

## 12. Open questions for P1 implementation

These do not block P1.0 (which is the path decision) but should be resolved during P1.1+:

1. **`_bypass_authorized` state model:** the orphan's quarantine uses a per-instance flag set by `authorize_bypass(reason=...)`. Should this be a class-level flag, a per-process flag, or a context-manager? The orphan's class-level approach is the simplest. Keep it.
2. **Sandbox `__init__.py` content:** empty vs. exports the public surface (`DockerSandbox`, `CaidoProxy`, `SandboxSession`)? v4.1's P3 work on capability broker-gating will need to import from this module. Recommend: empty initially; exports added by P3 when the broker-gated sandbox capability lands.
3. **`ArenaRunner._run_raphael_via_runtime()` lifecycle:** the orphan's seam is opt-in via env var. P2 must make it the default (per v4.1's "ONE RUNTIME" architecture). The seam must be removed in P3, not later.
4. **`src/raphael/main.py` CLI seam:** the orphan's `_run_via_canonical_runtime()` only works if Head 1's `RaphaelOrganism` exposes a `state` attribute (it does). The seam is a thin adapter. P1.1+ should confirm the seam semantics before promoting it from opt-in to default.

---

## 13. Reproduction commands

```bash
# Verify canonical checkout
cd /home/yaser/external-audits/raphael-2
git rev-parse HEAD
# Expected: 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0

# Verify baseline
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: 239 passed

# Verify baseline tag
git tag --list 'raphael-p0-*'
# Expected: raphael-p0-baseline-7272880f

# Inspect orphan stash contents
git ls-tree -r 'stash@{2}^3' -- src/orchestrator/runtime/ tests/
# Expected: 5 files (loop.py, types.py, hippocampus_episodes.json, test_runtime_phase1.py, test_broker_mandatory_phase2.py)

# Inspect orphan-modified files (use 4b960496... as the working-tree commit)
git show 4b96049661f5a1f9f1adf1e7e0b5ad1e811577a9 -- src/orchestrator/runtime/__init__.py | head -50

# Confirm no canonical import of orchestrator.runtime
grep -rEn "import orchestrator\.runtime|from orchestrator\.runtime" src/ tests/ --include="*.py" | grep -v __pycache__
# Expected: empty (canonical has zero such imports)

# Confirm the 5 sandbox consumers
grep -rEn "from \.\.runtime\.session_manager import SandboxSession" src/ --include="*.py" | grep -v __pycache__
# Expected: 5 lines (postex, exploit, scanners, exfil, phishing)
```
