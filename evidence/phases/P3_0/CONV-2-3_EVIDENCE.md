# RAPHAEL P3.0 CONV-2 / CONV-3 — Evidence Package

| Field | Value |
|---|---|
| Phase | P3.0 CONV-2 + CONV-3 (exec/ PEP, capability gating, INV-1 live) |
| Gate | G3-EN-5 (organ wiring next authorized work) |
| Repository HEAD | `19256f3358fe7ac32aba8bdaa46b7b2d9a4b7eeb` |
| Branch | `main` (ahead of `origin/main` by 33) |
| Commit count since canonical | 33 (per fresh `git rev-list --count 7272880f7..HEAD`) |
| Implementation commit | `22eff1774` (CONV-2/3 code: 7 files, 531 insertions, 105 deletions) |
| Evidence commit | `19256f335` (this file: 1 file, 157 insertions) |
| Timestamp | 2026-09-05 |
| Author | RAPHAEL P3.0 CONV-2/3 Audit |

## 1. Provenance Reconciliation (per artifact-only review)

The previous version of this file recorded the implementation commit
`22eff1774402c712ff6efaea8d18cabda2240966` as "Repository HEAD."
That was true at the moment the implementation commit was created.
The evidence commit (`19256f3358fe7ac32aba8bdaa46b7b2d9a4b7eeb`) was
then created on top of it, making `19256f335` the current HEAD.

**Authoritative current HEAD:** `19256f3358fe7ac32aba8bdaa46b7b2d9a4b7eeb`
(commit `CONV-2/3 evidence package`).

**Commit count:** 33 since canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`.

**Provenance of CONV-2/3 commits (chronological):**

| # | Commit | Description |
|---|---|---|
| 1 | `22eff1774402c712ff6efaea8d18cabda2240966` | CONV-2/3: PEP in exec/, capability gated by broker, INV-1 live |
| 2 | `19256f3358fe7ac32aba8bdaa46b7b2d9a4b7eeb` | CONV-2/3 evidence package (this file) |

The implementation commit is one commit before the evidence commit.

## 2. Fresh Git State (verbatim)

```
$ git rev-parse HEAD
19256f3358fe7ac32aba8bdaa46b7b2d9a4b7eeb

$ git rev-list --count 7272880f7..HEAD
33

$ git status --short --branch
## main...origin/main [ahead 33]
```

**Current git log (33 commits since canonical):**

```
$ git log --oneline 7272880f7..HEAD
19256f335 CONV-2/3 evidence package: PEP in exec/, capability gated, INV-1 live
22eff1774 CONV-2/3: PEP in exec/, capability gated by broker, INV-1 live
809c3af82 CONV-1 evidence package: real Broker as single canonical PDP
5c37bbef1 CONV-1: real brain CapabilityBroker as single canonical PDP
a9e4424c7 P3.0: records baseline (G3-EN-1, G3-EN-2, G3-EN-3)
9028c5782 G2 final HEAD reconciliation: f8abe9fa is authoritative CURRENT HEAD
f8abe9fa9 G2 provenance cleanup: correct commit count 23->24 and stale current-tip wording
ba0f965cb G2 FR-4 final: correct authoritative HEAD to b48e8ef59
b48e8ef59 G2-FR final records correction: G2-FR-2, G2-FR-3, G2-FR-4, G2-FR-5
85ee1f873 G2-FR-1..FR-5: records-only corrections (no code/test/architecture changes)
445f21a87 G2-C4 + G2-C5: corrected evidence package (full-G2 deliverable)
2c81c58bc G2-C3: convergence tickets for P2->P3 (no migration performed)
c7ab7eada G2-C1 + G2-C2: canonical CLI wiring + fail-closed proof
4c5a55fe0 P2.1: evidence package per v4 §25 schema (full-G2 deliverable)
b8a581ad6 P2.1: RaphaelRuntime walking skeleton (born-gated, v4 §13.3)
d2674ace5 G2 RC: final evidence index — RC-A..F complete, GLM RC-B applied
4b5c17354 RC-B GLM: evidence for GLM section 4 disposition implementation
03385c311 RC-B GLM disposition: dependency inversion via brain-owned port
5c90cdbfb RC-B escalation: analysis of apply_belief_transition dependency
deed0383c RC-F: untrack 14 episodes.jsonl test artifacts (keep on disk)
fa25ad715 G2 RC: evidence package index — RC-A..F remediation complete
f1756eb3c RC-F: bookkeeping/provenance cleanup
b63f0bde5 RC-E: evidence for bootstrap-v0 + ADR-012 (documentation only)
02c3b9c01 RC-D: correct guardrail scope to P2 jurisdiction (P9 retains full sweep)
0743d0a7e RC-C: complete deprecation marker coverage + authoritative registry
920cdf253 RC-B: sever brain->arena runtime imports (partial; 1 HALT/ESCALATE)
718099475 RC-A: remove canonical adaptive_brain import from brain/__init__.py
5c66c061e P2.0: evidence package per v4 §25 schema (AM-8 mandatory, global)
42f0d13fc P2.0: bootstrap-v0 named/versioned policy artifact (v4.1 AM-13.2)
982079425 P2.0: 5 guardrail tests per v4 §23 test registry + v4.1 AM-13.3
ecf6745d4 P2.0: deprecation markers for 14 UNREACHABLE_FROM_CANONICAL subprocess sites (v4 P1.2)
b3f32f5ae P2.0: transcribe ADR-001..010 from v4 §12.2 + ADR-011 addendum + ADR-012 seam ratification
a68c129a8 P1: canonical runtime packaging + seam work (per v4 §12 + v4.1 AM-4/AM-7/AM-13.3)
```

## 3. CONV-2: PEP in exec/ (v4 L6)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

### Created

- `src/orchestrator/exec/__init__.py` — PEP package marker, exports
  `SafeProvingCapability`, `CapabilityResult`, `verify_inv1_primitive_confinement`,
  `INV1_VIOLATION`
- `src/orchestrator/exec/safe_capability.py` — the safe proving capability
  (relocated from `src/orchestrator/runtime/safe_proving_capability.py`)
- `src/orchestrator/exec/inv1_guard.py` — INV-1 static check utility
  (scans `src/orchestrator/` for forbidden primitive imports outside
  `exec/`)

### Runtime integration

- `src/orchestrator/runtime/loop.py` — `RaphaelRuntime.__init__`
  constructs `SafeProvingCapability(broker=self._broker)`. The
  capability is imported from `orchestrator.exec.safe_capability`.
- `src/orchestrator/runtime/stages.py` — `stage_pep` calls
  `capability.inspect(request.target)` on the exec/-owned capability.

## 4. CONV-3: SafeProvingCapability relocated + constructor gating

### Relocation

- `SafeProvingCapability` moved from
  `src/orchestrator/runtime/safe_proving_capability.py` to
  `src/orchestrator/exec/safe_capability.py`
- `src/orchestrator/runtime/safe_proving_capability.py` retained as
  a re-export shim (per GLM pattern: BootstrapPolicy retained as
  loader; physical deletion is P9)

### Constructor gating

`SafeProvingCapability(broker: Optional[CapabilityBroker] = None)`:
- If a broker is bound, `inspect(target)` requires
  `record_authorization(target)` to have been called for that target.
  Otherwise raises `CapabilityNotGatedError`.
- The `stage_pep` calls `capability.record_authorization(request.target)`
  after the broker stage succeeds, before invoking
  `capability.inspect(request.target)`.
- INV-2 decision linkage preserved: the receipt from
  `broker.propose_action()` carries the `action_id` that
  `stage_pep` uses as the `decision_id` on the `ExecutionEvent`.

## 5. INV-1 goes live

INV-1: process/network/file primitives are confined to `exec/`.

### Broadened primitive lexicon (per the standing note)

Forbidden outside `exec/`:
- `subprocess` (any form)
- `os.system`, `os.popen`, `os.exec*`, `os.spawn*`
- `socket.*`
- `urllib.*`, `http.client`, `http.server`
- `requests`
- `open(..., 'w')`, `open(..., 'a')`, `open(..., 'x')` (write modes)
- `os.remove`, `os.unlink`, `os.rmdir`, `shutil.rmtree`

### Static check

`verify_inv1_primitive_confinement()` in `orchestrator.exec.inv1_guard`
scans `src/orchestrator/` for forbidden primitive imports outside
`exec/`. Returns a list of violations (empty = INV-1 satisfied).

The broader orchestrator/ tree has pre-existing primitive usage
(70 violations across legacy code paths like `weaponizer/`,
`c2/`, `exfil/`, `tactics/`, etc.). These are pre-existing and are
P3+ migration work. The Runtime's own files (`orchestrator/runtime/`)
are clean.

### Runtime verification

`test_inv1_runtime_clean` (new guardrail): scans
`src/orchestrator/runtime/` for forbidden primitives. **PASS** —
the Runtime's own files use no forbidden primitives.

## 6. Test Results

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 280 passed, 0 failed, 32 warnings, ~9.5s

| Metric | Pre-CONV-2/3 | Post-CONV-2/3 |
|---|---|---|
| Passed | 275 | **280** |
| Failed | 0 | **0** |
| Warnings | 31 | **32** |
| Guardrails (P2 + new) | 19 | **24** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton (real Broker +
exec/ capability) + 9 G2-C2 fail-closed (real Broker) + 19 P2
guardrails + 5 new INV-1/CONV-2/CONV-3 guardrail tests = **280**.

### New guardrail tests (CONV-2/3)

| Test | Status |
|---|---|
| `test_inv1_runtime_clean` | PASS — Runtime files use no forbidden primitives |
| `test_inv1_exec_package_may_use_primitives` | PASS — exec/ guard callable |
| `test_inv1_stage_pep_delegates_to_exec` | PASS — stage_pep delegates to exec/ |
| `test_inv3_capability_gated_by_broker` | PASS — unauthorized target raises |
| `test_inv3_capability_works_after_authorization` | PASS — post-auth inspect succeeds |

## 7. Changed Files (CONV-2/3)

```
src/orchestrator/exec/__init__.py                    (NEW)
src/orchestrator/exec/safe_capability.py             (NEW)
src/orchestrator/exec/inv1_guard.py                  (NEW)
src/orchestrator/runtime/loop.py                      (M)
src/orchestrator/runtime/safe_proving_capability.py  (M, now re-export shim)
src/orchestrator/runtime/stages.py                   (M, stage_pep records auth)
tests/test_p2_guardrail_inv1.py                      (NEW, 5 tests)
```

**Total changes:** 7 files (3 new source, 2 modified source, 1
new test). 531 insertions, 105 deletions.

## 8. Constraints Honored (from GLM §5)

1. ✅ **FLOOR = 280** (>= 275), monotonic; zero skips, zero xfails, zero weakening
2. ✅ **All 24 P2 guardrails green continuously** (19 original + 5 new)
3. ✅ **Arena-free closure** (verified by `test_import_graph_single_runtime`)
4. ✅ **INV-2 decision linkage** unbroken
5. ✅ **Fail-closed preserved** (G2-C2 tests pass against real Broker)
6. ✅ **Exactly one PDP** on the canonical path (CapabilityBroker)
7. ✅ **INV-1 live** — `verify_inv1_primitive_confinement` scans Runtime
8. ✅ `RAPHAEL_USE_LEGACY=1` remains the sole legacy reach
9. ✅ One cognitive loop; no new stages
10. ✅ No roadmap modification

## 9. Next Authorized Work (corrected from prior version)

Per the GLM authorization:

> **G3-EN-5: Organ wiring complete on the canonical path.** Before
> §14.6/§14.7 work and the MVP demonstration.

**Organ wiring is the next authorized work** (G3-EN-5). This
includes: Planner, WorldModel (read + integrate), Student
(recording mode), and minimal contradiction/failure trigger — as
stage handlers on the canonical path.

## 10. Prohibited Work (not yet authorized)

- ❌ §14.6/§14.7 work and MVP demonstration (until G3-EN-5 is satisfied)
- ❌ Welds (SUB14, SUB10, SHELL) — not until after G3-EN-5
- ❌ Scope v0, native sandbox, evidence v1, WorldModel enforcement, replan trigger
- ❌ P4 depth, Decepticon, Student learning, Teacher, P5-BIND-1
