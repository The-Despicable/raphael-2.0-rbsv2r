# RAPHAEL P0 — Evidence Package

Phase: P0 (re-anchor baseline / reproducibility)
Roadmap: RAPHAEL MASTER ROADMAP v4.1
Lane: MiniMax implementation / GLM review

## 5.1 Identity

- **Repository root:** `/home/yaser/external-audits/raphael-2`
- **Canonical checkout (HEAD):** `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
- **Branch:** `main` (matches `origin/main`; HEAD is grafted)
- **P0 baseline tag:** `raphael-p0-baseline-7272880f` (tag-object hash `72f33ee5623c656071a3a5a687712decd3c80b40`) → points at commit `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
- **Working tree:** clean (post-stash of pre-P0 orphan modifications from prior audit + Phase 1 + Phase 2 work)
- **Submodules:** none
- **Timestamp:** P0 evidence package authored 2026-09-04 from a single agent session

## 5.2 Scope

### IN SCOPE

- Repository identity (HEAD, branch, baseline tag)
- Reproducible environment manifest
- Test floor (FLOOR(P0))
- Live execution-path inventory (process creation, network primitives, file primitives, executor constructors, PHASE_EXECUTORS, Arena entry points)
- Historical bypass candidate re-verification against the canonical tree
- Canonical Runtime and Arena entry-point reality
- Initial deletion / migration inventory
- P0 risk delta
- Observational runtime probes

### OUT OF SCOPE

- Application-source behavior changes
- Implementation of any phase beyond P0 (no P1/P2/P3 behavior, no seam welding, no Broker hardening, no Head-1 migration, no Student learning activation, no Decepticon/T3MP3ST integration, no scope implementation, no policy artifact `bootstrap-v0`)
- Deletion of any tracked file
- "Just make it run" source patches
- Test gaming (weakening / skipping / xfail / narrowing / pruning retained tests)

### SCOPE DEVIATIONS

- **none.** P0-R1 satisfied: zero application-source edits in the working tree against the canonical commit. All modified files from prior work have been stashed under `RAPHAEL-P0-pre-baseline-stash-orphans-from-prior-audit-and-phases` and are NOT part of the canonical P0 artifact.

## 5.3 Changed files

- **Application source changed:** **NO**
- **Environment / provisioning changes:** none beyond what's needed to make the canonical commit runnable on this host (symlink `/home/yaser/raphael-2.0-rbsv2r -> /home/yaser/external-audits/raphael-2` was present before P0 started; pip-installed deps `httpx`, `aiohttp`, `paramiko` were installed in prior session for the prior audit's runtime probes; `pytest`/`pytest-asyncio` likewise). No new application-source changes; no new commits; no new files outside `evidence/phases/P0/`.
- **Evidence files added:** `evidence/phases/P0/` (this directory and its subdirectories).
- **Tags created:** `raphael-p0-baseline-7272880f` (immutable rollback marker; recorded in §5.1 and §5.7).
- **Stashes created:** `RAPHAEL-P0-pre-baseline-stash-orphans-from-prior-audit-and-phases` (pre-baseline orphan modifications stashed, recorded in §5.7).

## 5.4 Tests

- **Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`
- **Environment:** Python 3.14.4, x86_64, WSL2 Linux, pytest via pip
- **Result:**
  - passed: **239**
  - failed: 0
  - skipped: 0
  - xfailed: 0
  - xpassed: 0
  - warnings: 27
  - duration: 5.14s
  - exit code: 0

- **FLOOR(P0) = 239 passed at canonical commit `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` against the canonical Python 3.14.4 environment on this host.**

- **Warning summary:** 27 warnings, all in pre-existing test files. 26 of these are the well-documented `PytestReturnNotNoneWarning` in `tests/test_cli_smoke.py` (tests returning a list instead of asserting). The +1 (vs. the 26 seen in the prior audit/Phase-1/Phase-2 runs) is in `tests/test_cli_smoke.py::test_project_structure`, same warning category.

- **Floor-monotonicity (P0-R5 / AM-6):** satisfied. The canonical commit ran green without weakening, skipping, xfail-ing, narrowing, deleting, or otherwise modifying any test. No retained tests were touched in P0.

- **Pre-existing failures:** none. The canonical baseline is green.

## 5.5 Runtime proof

### Probe A — CLI entry reachability

- **Canonical CLI entry:** `src/raphael/main.py:312` `async def main()` → `RaphaelOrganism.run()` at `src/raphael/main.py:160`.
- **Direct Runtime routing:** none at canonical. The CLI does **not** call any `RaphaelRuntime`. Phase 1 / Phase 2 work added this routing but is in the stashed orphan state, NOT part of the canonical P0 artifact.

### Probe B — Runtime construction

- **Result:** `from orchestrator.runtime import RaphaelRuntime` fails with `ImportError: cannot import name 'RaphaelRuntime' from 'orchestrator.runtime'`.
- The `orchestrator.runtime` package exists at canonical commit but contains different contents (`caido_bootstrap.py`, `docker_client.py`, `session_manager.py`, empty `__init__.py`). No `RaphaelRuntime` class anywhere in the canonical tree.

### Probe C — Arena entry-point classification

- **Default Arena entry:** `AblationRunner._run_raphael()` at `src/arena/ablation_runner.py:880` (980-line inlined cognitive loop).
- **Runtime-mode Arena entry:** none at canonical. Phase 1 added `_run_raphael_via_runtime()` but it lives in the stashed orphan state.
- **LLM-only entry:** `AblationRunner._run_llm_only()` at `src/arena/ablation_runner.py:2684`.
- **Scripted entry:** `AblationRunner._run_scripted()` at `src/arena/ablation_runner.py:2945`.

### Probe D — Execution primitive reachability

- **Subprocess sites in canonical tree:** 17 sites across 13 files. Full inventory in `02_execution_inventory/subprocess_sites.md`.
- **Reachable from canonical Arena `_run_raphael()`:** 0 subprocess sites. The arena's `env.handle_action()` is a simulated environment (returns fake observations), no real subprocess.
- **Reachable from canonical CLI `RaphaelOrganism.run()`:** depends on which `TECHNIQUE_REGISTRY` entries fire; `TECHNIQUE_REGISTRY` has 24 entries; techniques that reach `Executor.execute()` ultimately hit `_subprocess_fallback` for tool execution. The CLI requires a live target and the Kali tools service; without it, the loop exits stuck without calling `_subprocess_fallback`.
- **Reachable from canonical CLI `RAPHAEL_USE_RUNTIME=1` path:** none — no Runtime exists at canonical.

### Probe E — Broker presence on canonical route

- **Arena canonical route (`_run_raphael`):** YES. Calls `runner.propose_action(...)` at `src/arena/ablation_runner.py:1504` (via `runner.propose_action` from `src/arena/runner.py:285`, which delegates to `CapabilityBroker.propose_action`).
- **CLI canonical route (`RaphaelOrganism.run`):** NO. The CLI does not construct or call `CapabilityBroker`. Only `Planner(cortex)` and `Executor(executor)`.
- **Planner decision bypass on Arena route:** YES. `Planner.decide()` at `src/orchestrator/brain/action.py:1109` hardcodes `allowed = True  # Assume allowed for planning purposes`. Planner is selection-only, Broker is the authorization authority — but Planner does not call Broker; the Arena's `_run_raphael` calls `runner.propose_action` AFTER `Planner.decide` already selected. The "bypass" is Planner's local hardcoded allow, but actual execution authorization still goes through `runner.propose_action`.
- **CLI route's `_subprocess_fallback`:** exists, no Broker gate. Called from `Executor.execute()` → `Executor._subprocess_fallback()`. Quarantine state: **not quarantined** at canonical (Phase 2 quarantine lives in stashed orphan state).

### Probe F — hard-coded environment paths

- `grep -rEn "/home/yaser/"|/Users/" src/ 2>/dev/null` → 14 files match. Notable:
  - `src/orchestrator/config/paths.py:2` — `sys.path.insert(0, "/home/yaser/raphael-2.0")` (target absent)
  - `src/orchestrator/config/target.py:2` — same
  - `src/orchestrator/student/research_scheduler.py` (multiple)
  - `src/arena/d6_manifest.py`, `d7_r1_mechanism_test.py`, etc. — 9 arena test files `open("/home/yaser/raphael-2.0-rbsv2r/...")` for source-text assertions
  - `launch_pilot.sh:2-3` — broken path
- The `/home/yaser/raphael-2.0-rbsv2r` symlink target IS present on this host (pointing at `/home/yaser/external-audits/raphael-2`), so the 9 arena test files can read their targets.
- The `/home/yaser/raphael-2.0` symlink target is **absent**. This breaks `src/orchestrator/config/paths.py` and `target.py` if they are loaded by any code path during the canonical baseline. They are imported by `student/research_scheduler.py` (deferred import) and by the broken `bridge.raphael_bridge` — neither is exercised by the canonical 239-test suite.

## 5.6 Security proof

### Execution-path inventory (canonical)

- **Total subprocess sites:** 17 (13 files). Full inventory in `02_execution_inventory/subprocess_sites.md`.
- **`subprocess` import sites:** 40 files.
- **Canonical reachability classification** (full table in `02_execution_inventory/execution_paths.md`):

| Class | Count | Examples |
|---|---|---|
| CANONICAL_REACHABLE | 0 | — |
| LEGACY_REACHABLE | 17 (via CLI/arena fallback) | raphael/executor/executor.py:72, kali_tools_client.py:41, etc. |
| UNREACHABLE_FROM_CANONICAL | 17 | weaponizer, chains/tool_registry, c2/sliver, c2/implant_builder, recon-pipeline, agent/modules/executor, sword/phase_0_recon, etc. (NOT invoked by canonical Arena or CLI) |

### Historical bypass re-verification (canonical)

- `raphael/executor/executor.py:_subprocess_fallback` — **CONFIRMED** (line 67). Quarantine state: NOT QUARANTINED.
- `orchestrator/kali_tools_client.py:_run_local` — **CONFIRMED** (line 20). Quarantine state: NOT QUARANTINED.
- `orchestrator/capabilities/interactive_shell/{ssh_shell,reverse_shell}` constructors — **CONFIRMED** (no broker enforcement in `__init__`). Quarantine state: NOT QUARANTINED.
- `orchestrator/brain/action.py:1109 allowed=True` — **CONFIRMED**. Planner is selection-only, not authorization; but the comment "would check against broker policy" is misleading.
- `capability_broker.py:1223 broker commented` (ExecutionEngine) — **CONFIRMED**.
- `BrokeredExecutionEngine` (`capability_broker.py:1277`) — **CONFIRMED** defined; **NOT REACHABLE** from any canonical caller (only constructed by `capability_broker.create_brokered_engine()` at line 1370, which is itself unreferenced outside its own file).
- `modes/autonomous.py` PHASE_EXECUTORS — **CONFIRMED**. 9 of 13 phase executors are `NOT_IMPLEMENTED` stubs (return `success=False, status="not_implemented"`). 4 are real: `cicd`, `ml_attack`, `cloud_abuse`, `container_escape`.

### Authorization classification

| Site | Authorization |
|---|---|
| `arena._run_raphael` → `runner.propose_action` → `broker.propose_action` | BROKER_MEDIATED |
| `Planner.decide` `allowed = True` line 1109 | LOCAL_AUTHORIZATION (selection only, NOT execution authorization) |
| `raphael.executor._subprocess_fallback` | DIRECT (no broker gate) |
| `kali_tools_client._run_local` | DIRECT (no broker gate) |
| `ReverseShellCapability`/`SSHShellCapability` constructors | DIRECT (no broker gate at construction) |
| 17 other subprocess sites | DIRECT (or unreferenced) |

### Unknown routes

- **0 unknown routes** at canonical. Every historical bypass site is either CONFIRMED or ABSENT from the canonical tree.

### Security claims

This evidence package does NOT claim:
- Bypass closure (none closed — that is P3 work)
- Broker enforcement on the canonical Runtime path (no Runtime exists at canonical)
- Head 1 migration (not performed — Phase 9 work)
- P3 MVP conditions (P3 not yet executed)

This evidence package DOES establish:
- The exact set of execution paths reachable from the canonical Arena and CLI
- The exact set of unbrokered execution paths at canonical
- The fact that no Runtime exists at canonical, so any claim of "Runtime-mediated Broker enforcement" against the canonical artifact is unsupported

## 5.7 Review notes

### Known issues / unresolved references

- **`src/orchestrator/runtime/` name collision with Phase 1 work.** Phase 1 created a `RaphaelRuntime` class in `src/orchestrator/runtime/loop.py` and overwrote `__init__.py` with new exports. The canonical commit has a different package at the same path (`caido_bootstrap.py`, `docker_client.py`, `session_manager.py`, empty `__init__.py`). This is the same path with disjoint contents. If Phase 1's stashed work were re-applied, the canonical package contents would be silently overwritten (the stash is named "prior-audit-and-phases" — it is the Phase 1 + Phase 2 working tree). The stash must be either dropped or carefully merged before P1 begins, NOT simply popped.
- **No Runtime exists at canonical.** All claims of "Runtime-mediated execution" against the canonical artifact are unsupported. The audit's "Phase 1 SEAM" is **stashed orphan state**, not part of the canonical P0 baseline.
- **9 of 13 phase executors are `NOT_IMPLEMENTED` stubs** at canonical (`harvest, recon, scan, exploit, postex, lateral, credential, exfil, phish`). Only `cicd, ml_attack, cloud_abuse, container_escape` are real. This is documented honestly in source comments.
- **4 broken symlinks** (target `/home/yaser/raphael-2.0` absent): `cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service`. These are not part of the canonical reachable execution path under P0 tests; they were flagged by the prior audit and remain unchanged at canonical.

### Risk delta (vs. v4.1 reference baseline)

- **R-1 (stale-map execution):** AM-1's halt-and-re-derive rule applied throughout P0 — every historical reference reverified against canonical before use. No forward-fixing against stale data.
- **R-2 (seam becomes permanent):** N/A at canonical — no seam exists. Will become applicable after Phase 1 reintroduces the seam.
- **R-3 (floor-monotonicity gaming):** P0-R5 satisfied. FLOOR(P0) = 239 reflects the canonical tree's actual green state; no tests weakened to achieve it.
- **R-4 (dual-loop coexistence):** APPLIES. Canonical has only one cognitive loop (`arena._run_raphael`); the Phase-1-introduced Runtime loop is in stashed orphan state. After P1 lands, both would coexist temporarily; AM-3's P7a tracking would catch drift.
- **R-5 (weld breaks arena parity):** N/A at canonical — no weld attempted.
- **R-6 (escalation deadlock):** N/A — no architecture conflict encountered.

### Unresolved questions for P1

- **Phase 1 seam's destination path:** Phase 1 wrote to `src/orchestrator/runtime/`, but canonical has different files at the same path. P1 must reconcile (drop the conflicting canonical files, or pick a different path) — and document the decision. Without reconciliation, popping the P0 stash will silently overwrite canonical contents.
- **`adaptive_brain.py`:** unchanged at canonical (31-line counter stub). AM-1 specifies this should be retired or repurposed in P2; P1 may want to begin that work.

### Evidence gaps

- None. The canonical checkout ran the 239-test suite green without any application-source modification. The execution-path inventory is complete for canonical. The historical bypass re-verification is complete for canonical.

### Scope deviations (explicit)

- **none.** (See §5.2.)

### Rollback point

- **P0 baseline tag:** `raphael-p0-baseline-7272880f`
- **P0 baseline target commit:** `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
- **Verified by:** `git rev-parse raphael-p0-baseline-7272880f` → `72f33ee5623c656071a3a5a687712decd3c80b40` (tag-object hash, distinct from commit hash); the tag points at the canonical commit.
- **Orphan-stash reference:** `RAPHAEL-P0-pre-baseline-stash-orphans-from-prior-audit-and-phases` (contains Phase 1 + Phase 2 working-tree modifications; NOT part of canonical, but may be needed to reconstruct Phase 1/2 if P1 begins from the orphan state).

### P0 handoff to P1

- CANONICAL_CHECKOUT = `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
- FLOOR(P0) = 239 passed (canonical baseline)
- RUNTIME_ENTRY = NONE (no Runtime exists at canonical)
- ARENA_RUNTIME_ENTRY = NONE (no `_run_raphael_via_runtime` at canonical)
- ARENA_LEGACY_ENTRY = `AblationRunner._run_raphael` at `src/arena/ablation_runner.py:880`
- BROKER_ON_CANONICAL_PATH = YES (Arena calls `runner.propose_action` → `CapabilityBroker.propose_action`)
- PEP_ON_CANONICAL_PATH = NO (no PEP layer exists; canonical routes have direct subprocess calls)
- LEGACY_EXECUTION_SITES = 17 (canonical)
- CANONICAL_EXECUTION_SITES = 0 (canonical — Runtime doesn't exist)
- QUARANTINED_SITES = 0 (canonical — no quarantine logic exists)
- UNKNOWN_SITES = 0 (canonical)
- NEW_EXECUTION_SITES_FOUND = 0 (canonical — all 17 historical sites verified, none new)
- P0_SCOPE_DEVIATIONS = none
- P0_BLOCKERS = none (canonical baseline is reproducible; FLOOR(P0) is derivable; all historical references verified)

---

## P0 Exit Statement (per packet §12 template)

```
P0 VERDICT: PASS

Canonical checkout: 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
P0 baseline tag:    raphael-p0-baseline-7272880f
Rollback point:     raphael-p0-baseline-7272880f -> 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0
FLOOR(P0):          239 passed, 0 failed, 27 warnings, 5.14s
Application source changed: NO
Environment-only provisioning: symlink /home/yaser/raphael-2.0-rbsv2r (pre-existing, P0-R2 legal)
Execution sites inventoried: 17 subprocess sites across 13 files
Historical bypass candidates reverified: 7 (all CONFIRMED)
Unknown execution sites: 0
Runtime entry point: NONE (no Runtime exists at canonical)
Arena canonical route: AblationRunner._run_raphael (src/arena/ablation_runner.py:880)
Arena legacy route: same (canonical has only one cognitive loop)
P0 scope deviations: none
P0 blockers: none

G0 recommendation: BEGIN P1
  (with the noted reconciliation step: P1 must drop or merge the
  stashed Phase 1+2 orphan state before starting implementation, since
  the stash uses src/orchestrator/runtime/ which already contains
  disjoint canonical files.)

Primary unresolved risks:
- Phase 1+2 orphan stash collides on src/orchestrator/runtime/ contents
  with canonical caido_bootstrap.py / docker_client.py / session_manager.py.
  Resolution: drop canonical caido_bootstrap, docker_client, session_manager
  (or merge into the new Runtime package) before popping the stash.
- No Runtime exists at canonical: P1 must build the Runtime from scratch
  per v4.1, not as a re-application of Phase 1 (which lives in orphan state).

What P0 explicitly did NOT do:
- Broker closure (P3 work)
- Head 1 migration (Phase 9 work)
- seam welding (P3 work, gated by AM-4)
- P3 MVP implementation (P3 work)
- Any application-source behavior changes
```
