# RAPHAEL P0 — Final Report (v4.1)

## P0 VERDICT: PASS

```
Canonical checkout:    7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
P0 baseline tag:       raphael-p0-baseline-7272880f
                       (tag-object hash 72f33ee5623c656071a3a5a687712decd3c80b40
                        points at commit 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0)
Rollback point:        raphael-p0-baseline-7272880f -> 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
FLOOR(P0):             239 passed, 0 failed, 27 warnings, 5.14s
                       (Python 3.14.4, WSL2 Linux, canonical commit)
Application source changed:    NO
Environment-only provisioning: symlink /home/yaser/raphael-2.0-rbsv2r (pre-existing,
                                P0-R2 legal). No new dependencies installed.
Execution sites inventoried:  17 subprocess sites across 13 files
Historical bypass candidates reverified: 10 (10 CONFIRMED, 0 SHIFTED, 0 ABSENT,
                                            0 RESOLVED, 0 NEW, 0 UNKNOWN)
Unknown execution sites:       0
Runtime entry point:           NONE (no RaphaelRuntime at canonical)
Arena canonical route:         AblationRunner._run_raphael (src/arena/ablation_runner.py:880)
Arena legacy route:            same (canonical has only one cognitive loop)
P0 scope deviations:           none
P0 blockers:                   none
```

## G0 recommendation: **BEGIN P1** (with one prerequisite decision)

P1 may begin once the following prerequisite decision is documented and resolved (the decision itself is a P1 deliverable, not a P0 action):

> **P1 prerequisite:** Reconcile the **name collision** between canonical `src/orchestrator/runtime/{caido_bootstrap.py, docker_client.py, session_manager.py, empty __init__.py}` and the orphan-stash `src/orchestrator/runtime/{loop.py, types.py, populated __init__.py}`. P1 must record the chosen path layout before popping the orphan stash; otherwise canonical Caido/Docker/session code is silently overwritten. (See `05_migration_delete_inventory/deletion_inventory.md` for the full collision matrix.)

## Primary unresolved risks

- **R-8 (HIGH, P1 prerequisite):** `src/orchestrator/runtime/` name collision between canonical and orphan-stash contents. See above.
- **R-10 (HIGH, G3 blocker):** Canonical CLI runs through `Executor._subprocess_fallback` without `CapabilityBroker` mediation. Phase 3 MVP must close this.
- **R-4 (HIGH, G2 blocker):** Dual-loop coexistence risk post-P1 if Runtime lands without reconciliation. v4.1 AM-3's P7a tracking catches drift.
- **R-7 (MEDIUM, deferred):** Python 3.14.4 vs pyproject's `<3.13` constraint. Tests run green; production runtime untested (no Runtime exists at canonical).

Full risk register: `06_risks/risk_delta.md`.

## What P0 explicitly did NOT do

- Broker closure (P3 work)
- Head 1 migration (Phase 9 work)
- Seam welding (P3 work, gated by v4.1 AM-4)
- P3 MVP implementation
- Any application-source behavior changes
- Runtime construction (Phase 1 work is in orphan stash, not at canonical)
- `bootstrap-v0` policy artifact (P2.0 work per v4.1 AM-13.2)
- Decepticon or T3MP3ST integration (PD track / AM-5)
- Student learning activation (P7 work)
- Deletion of any tracked file
- "Just make it run" source patches

## Files / evidence created

12 files under `evidence/phases/P0/`:

```
EVIDENCE_PACKAGE.md                          (top-level summary, conforms to AM-8 schema)
00_manifest/checkout.txt                     (HEAD, branch, baseline tag, status)
00_manifest/environment.md                   (Python 3.14.4, WSL2, deps, env vars)
01_test_floor/baseline.txt                   (FLOOR(P0) = 239 passed)
01_test_floor/test_inventory.md              (22 test files, 239 tests, what they prove/don't prove)
02_execution_inventory/execution_paths.md    (canonical Runtime/CLI/Arena entry chains)
02_execution_inventory/subprocess_sites.md   (17 sites with reachability classification)
03_historical_reverification/bypass_reverification.md  (10 historical bypasses, all CONFIRMED)
04_architecture_reanchor/runtime_entrypoints.md        (no Runtime at canonical)
04_architecture_reanchor/canonical_graph.md  (operator/CLI → ... → canonical graph)
05_migration_delete_inventory/deletion_inventory.md   (initial deletion inventory + name-collision matrix)
06_risks/risk_delta.md                        (17 risks, AM-9 baseline + P0 discoveries)
07_runtime_probes/probe_results.md           (9 probes, all observational, results)
```

Plus 1 tag:

```
raphael-p0-baseline-7272880f -> 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
```

And 2 stashes (pre-P0 orphan noise + post-baseline test-artifact noise):

```
RAPHAEL-P0-pre-baseline-stash-orphans-from-prior-audit-and-phases
RAPHAEL-P0-post-baseline-test-artifact-noise
RAPHAEL-P0-final-test-artifact-cleanup
```

## Reproducibility commands

```
# 1. Verify canonical checkout
git rev-parse HEAD
# Expected: 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0

# 2. Verify baseline tag exists
git tag --list 'raphael-p0-*'
# Expected: raphael-p0-baseline-7272880f

# 3. Verify clean working tree
git status --short --branch
# Expected: ## main...origin/main (with only `?? evidence/` untracked)

# 4. Re-derive FLOOR(P0)
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
# Expected: 239 passed, 26-27 warnings, ~5s
```

## Handoff to P1

```
CANONICAL_CHECKOUT      = 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
FLOOR(P0)               = 239 passed (canonical baseline)
RUNTIME_ENTRY           = NONE (Phase 1 work in orphan stash, not at canonical)
ARENA_RUNTIME_ENTRY     = NONE (no _run_raphael_via_runtime at canonical)
ARENA_LEGACY_ENTRY      = AblationRunner._run_raphael (src/arena/ablation_runner.py:880)
BROKER_ON_CANONICAL_PATH = YES (Arena calls runner.propose_action → CapabilityBroker.propose_action)
PEP_ON_CANONICAL_PATH   = NO (no PEP layer at canonical)
LEGACY_EXECUTION_SITES  = 2 reachable (SUB-13 KaliBridge._subprocess_run, SUB-14 Executor._subprocess_fallback)
                           + 15 unreachable from canonical entry points
CANONICAL_EXECUTION_SITES = 0
QUARANTINED_SITES        = 0 (canonical — Phase 2 quarantine is in orphan stash)
UNKNOWN_SITES            = 0
NEW_EXECUTION_SITES_FOUND = 0
P0_SCOPE_DEVIATIONS      = none
P0_BLOCKERS              = none

P1 PREREQUISITE:
  Resolve src/orchestrator/runtime/ name collision BEFORE popping the
  orphan stash. Document the chosen path layout in P1 evidence package.
```

## P0 success condition (per packet §13)

The next agent can start P1 without having to guess:
- which repository state is authoritative → **7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0** (tagged `raphael-p0-baseline-7272880f`)
- what the actual baseline is → **239 passed, 0 failed**
- which execution routes exist → **17 subprocess sites, 2 LEGACY_REACHABLE from CLI, 15 UNREACHABLE**
- which historical findings are still true → **all 10 CONFIRMED, none SHIFTED/ABSENT/RESOLVED**
- which paths are canonical vs legacy → **Arena (broker-mediated) is canonical; CLI is legacy (unbrokered); no Runtime exists**
- what remains unknown → **0 unknowns at P0**
- what must not be touched yet → **see R-8 (name-collision reconciliation) and R-10 (canonical CLI unbrokered — Phase 3 work)**

P0 achieves its goal: the truth about RAPHAEL is now precise enough that every later security and architecture claim can be tested against the same baseline.

---

**End of P0.**
