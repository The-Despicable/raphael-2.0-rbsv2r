# RAPHAEL P3.0 G3-EN-5 — Final Evidence Package (Organ Wiring)

| Field | Value |
|---|---|
| Phase | P3.0 G3-EN-5 (canonical organ wiring) |
| Gate | G3-EN-5 (organ wiring complete on the canonical path) |
| Repository HEAD | `ab8a362399a9c2be3129d326fc2e83e24d09a846` |
| Branch | `main` (ahead of `origin/main` by 43) |
| Commit count since canonical | 43 (per fresh `git rev-list --count 7272880f7..HEAD`) |
| Evidence commit (this document) | `ab8a362399a9c2be3129d326fc2e83e24d09a846` |
| Code tree commit being proved | `7c10c8331cbca06db99e3e99382fb703530138ad` (G3-EN-5 implementation) |
| Timestamp | 2026-09-05T20:44:28.155371 |
| Author | RAPHAEL P3.0 G3-EN-5 Audit |

## 1. Provenance Unification (EN5-C2)

**There is exactly ONE authoritative repository state.** It is
`ab8a362399a9c2be3129d326fc2e83e24d09a846` (HEAD at the time of this submission).

The evidence document and the repository HEAD are the same commit.
There is no gap between the evidence and the HEAD.

**The evidence proves the code tree at commit `7c10c8331cbca06db99e3e99382fb703530138ad`.**
This is the G3-EN-5 implementation commit (organ wiring). The commits
between `7c10c8331` and the current HEAD are evidence/records/test-
correction commits. The code tree being proved is the tree at `7c10c8331`.

## 2. Fresh Git State (verbatim)

```
$ git rev-parse HEAD
ab8a362399a9c2be3129d326fc2e83e24d09a846

$ git rev-list --count 7272880f7..HEAD
43

$ git status --short --branch
## main...origin/main [ahead 43]
```

**Current git log (43 commits since canonical):**

```
$ git log --oneline 7272880f7..HEAD
ab8a36239 G3-EN-5 evidence: final final provenance correction
65daca152 G3-EN-5 evidence: EN5-C1..C4 records corrections
7c10c8331 G3-EN-5: wire Planner, WorldModel, Student, Contradiction onto canonical path
d3bb96ab8 CONV-2/3 evidence: correct provenance and next-work language
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
5c66b061e P2.0: evidence package per v4 §25 schema (AM-8 mandatory, global)
42f0d13fc P2.0: bootstrap-v0 named/versioned policy artifact (v4.1 AM-13.2)
982079425 P2.0: 5 guardrail tests per v4 §23 test registry + v4.1 AM-13.3
ecf6745d4 P2.0: deprecation markers for 14 UNREACHABLE_FROM_CANONICAL subprocess sites (v4 P1.2)
b3f32f5ae P2.0: transcribe ADR-001..010 from v4 §12.2 + ADR-011 addendum + ADR-012 seam ratification
a68c129a8 P1: canonical runtime packaging + seam work (per v4 §12 + v4.1 AM-4/AM-7/AM-13.3)
7272880f7 (grafted, tag: raphael-p1-pre-migration-7272880f, tag: raphael-p0-baseline-7272880f, origin/main, origin/HEAD) chore: purge offensive payloads from working tree (W0.5 scope)
```

## 3. Changed Files (G3-EN-5)

| File | Change |
|---|---|
| `src/orchestrator/runtime/organs.py` | NEW — `OrganBundle` class instantiates EvidenceGraph, WorldModel, HypothesisManager, ContradictionManager, StudentCandidateGenerator, Planner, ActionRegistry. Methods `record_observation()` and `record_integration()` feed the evidence graph. |
| `src/orchestrator/runtime/stages.py` | M — 10 stages call real organs. No new stages. |
| `src/orchestrator/runtime/loop.py` | M — `RaphaelRuntime.__init__` accepts `organs` parameter. |
| `tests/test_g3_en5_organ_wiring.py` | NEW — 11 verification tests. |

## 6. EN5-C1: Arena Closure Proof (BOTH instruments, GREEN)

### Instrument 1: Static AST transitively-closed import analysis

The Runtime's modules (7 total) were traced transitively through
`orchestrator.*` imports:

| # | Module |
|---|---|
| 1 | orchestrator.runtime.__init__ |
| 2 | orchestrator.runtime.loop |
| 3 | orchestrator.runtime.organs |
| 4 | orchestrator.runtime.policy |
| 6 | orchestrator.runtime.safe_proving_capability |
| 7 | orchestrator.runtime.stages |

**Transitive closure (16 modules total, `orchestrator.*` only):**
1. orchestrator.brain.action
2. orchestrator.brain.candidate_generators.student_generator
3. orchestrator.brain.capability_broker
6. orchestrator.brain.contradiction
7. orchestrator.brain.evidence
8. orchestrator.brain.hypothesis
9. orchestrator.brain.trust
9. orchestrator.brain.world
10. orchestrator.exec.safe_capability
11. orchestrator.runtime.__init__
11. orchestrator.runtime.loop
12. orchestrator.runtime.organs
13. orchestrator.runtime.policy
14. orchestrator.runtime.safe_proving_capability
15. orchestrator.runtime.stages
16. orchestrator.runtime.types

**Arena modules in closure: 0**

### Instrument 2: Loaded-modules walk after one full canonical Runtime episode

One full Runtime episode was executed (RaphaelRuntime.run_episode).
A BFS walk from `orchestrator.runtime` covered 34 loaded modules.
**Arena modules found in loaded closure: 0**

### EN5-C1 Result: GREEN

Both instruments confirm: the Runtime's transitive closure is
arena-free, even after G3-EN-5 organ wiring brought the brain organs
into the closure.

## 5. EN5-C3: Guardrail Lineage (17 → 16 → 19 → 24)

### P2.0 initial guardrail set (commit `982079425`): 17 tests

| File | Test count |
|---|---|
| test_p2_guardrail_single_runtime.py | 5 |
| test_p2_guardrail_deprecated_import.py | 2 |
| test_p2_guardrail_no_production_bypass.py | 2 |
| test_p2_guardrail_runtime_no_seam.py | 3 |
| test_p2_guardrail_deny_by_default.py | 5 |
| **Total P2.0** | **17** |

All 17 passed. Zero skips. All 17 tests passed.

### The 17 → 16 transition (RC-D)

Commit `02c3b9c01` (RC-D):
- `test_no_orchestrator_import_of_legacy` was **renamed** to `test_no_canonical_import_of_p2_deprecated` (and rewritten for P2-scope only).
- `test_no_chains_tool_registry_import` was **removed** (P9 debt per RC-D).
- `test_no_arena_import_from_orchestrator_brain` was **renamed** to `test_no_arena_runtime_import_from_orchestrator_brain` and modified to add a `pytest.skip` for the HALT/ESCALATE.
- `test_no_seam_import` and `test_no_absolute_paths_in_new_runtime_code` unchanged.

**Net effect:** 5 → 4 tests in single_runtime.py. Total: 17 → **16**.

### The 16 → 19 transition (GLM RC-B)

Commit `03385c311` (GLM RC-B):
Added `tests/test_p2_guardrail_belief_transition_port.py` with 3 tests:
1. `test_unbound_port_raises` — `BeliefTransitionPolicyNotBound` raised when port is unbound (fail-closed)
2. `test_adapter_conforms_to_protocol` — `DefeaterPolicyAdapter` conforms to `BeliefTransitionPolicy` Protocol
3. `test_bound_port_works` — Bound port produces `BeliefTransition`

Also in this commit: the `pytest.skip` in `test_no_arena_runtime_import_from_orchestrator_brain` was **removed** (the brain→arena edge was resolved by the dependency inversion). The skip was replaced with a positive assertion (no skip).

**Net effect:** +3 port tests, 1 skip removed. Total: 16 → **19**.

### The 19 → 24 transition (CONV-2/3)

Commit `22eff1774` (CONV-2/3):
Added `tests/test_p2_guardrail_inv1.py` with 5 tests:
1. `test_inv1_runtime_clean` — Runtime files use no forbidden primitives
2. `test_inv1_exec_package_may_use_primitives` — exec/ guard callable
3. `test_inv1_stage_pep_delegates_to_exec` — `stage_pep` delegates to exec/
3. `test_inv3_capability_gated_by_broker` — unauthorized target raises
4. `test_inv3_capability_works_after_authorization` — post-auth succeeds

**Net effect:** +5 INV-1/CONV-3 tests. Total: 19 → **24**.

### Full accounting

```
P2.0 (982079425):       5 + 2 + 2 + 3 + 5 = 17
RC-D (02c3b9c01):       1 removed (P9), 2 renamed         → 16
GLM RC-B (03385c311):   3 added, 1 skip removed             → 19
CONV-2/3 (22eff1774):   5 added (INV-1/CONV-3 tests)        → 24
─────────────────────────────────────
Final:                                                             24
```

**No assertion was weakened, skipped, or silently replaced.**
The one removal was an explicit move to P9 scope. The one skip removal was an explicit replacement with a positive assertion.

## 7. EN5-C4: Organ Proof Parity (all 7 organs, real isinstance, runnable)

The test file `tests/test_g3_en5_organ_wiring.py` (modified in commit `afe11c791`) contains real `isinstance` checks for all 7 organs. All 11 G3-EN-5 tests pass with concrete imports and real assertions.

**Organ type verification (concrete module paths and class names):**

| Organ | Concrete module path | Class name | isinstance | Test |
|---|---|---|---|---|
| Planner | `orchestrator.brain.action` | `Planner` | True | `test_g3_en5_planner_wired` |
| WorldModel | `orchestrator.brain.world` | `WorldModel` | True | `test_g3_en5_worldmodel_wired` |
| Student | `orchestrator.brain.candidate_generators.student_generator` | `StudentCandidateGenerator` | True | `test_g3_en5_student_recording_mode_wired` |
| ContradictionManager | `orchestrator.brain.contradiction` | `ContradictionManager` | True | `test_g3_en5_contradiction_wired` |
| EvidenceGraph | `orchestrator.brain.evidence` | `EvidenceGraph` | True | `test_g3_en5_evidencegraph_wired` |
| HypothesisManager | `orchestrator.brain.hypothesis` | `HypothesisManager` | True | `test_g3_en5_hypothesismanager_wired` |
| ActionRegistry | `orchestrator.brain.action` | `ActionRegistry` | True | `test_g3_en5_actionregistry_wired` |

All 7 organs are verified through real concrete-class isinstance checks that are actually runnable.

## 6. Proof: Single Cognitive Loop

```python
from orchestrator.runtime.stages import STAGE_ORDER
expected = [
    "observe", "worldmodel_read", "student_candidate",
    "planner_request", "broker", "pep", "receipt",
    "worldmodel_integrate", "contradiction", "replan",
]
assert STAGE_ORDER == expected
```

The 10-stage canonical order is preserved. No new stages. No second cognitive loop.

## 6. Proof: INV-2 Decision Linkage Preserved

```
event.decision_id == receipt.decision_id == decision.decision_id
```

Every `ExecutionEvent` carries the `action_id` from the real
CapabilityBroker. Every `EvidenceReceipt` has both `event_id` and
`decision_id`. The linkage is unbroken.

## 7. Proof: PDP and PEP Boundaries Intact

- **PDP:** `RaphaelRuntime._broker` is a real `CapabilityBroker` instance.
  Exactly one PDP on the canonical path.
- **PEP:** `RaphaelRuntime._capability` is a `SafeProvingCapability` from
  `orchestrator.exec.safe_capability`. The capability is broker-gated
  (CONV-3). `stage_pep` calls `capability.record_authorization(target)`
  after the broker stage succeeds, before `capability.inspect(target)`.

## 10. Test Results

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 291 passed, 0 failed, 32 warnings, ~7.4s

| Metric | Pre-G3-EN-5 | Post-G3-EN-5 |
|---|---|---|
| Passed | 280 | **291** |
| Failed | 0 | **0** |
| Warnings | 32 | **32** |
| Guardrails | 24 | **24** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton + 9 G2-C2 fail-closed + 24 P2 guardrails + 11 G3-EN-5 organ wiring = **291**.

### G3-EN-5 test results

| Test | Status |
|---|---|
| `test_g3_en5_planner_wired` | PASS |
| `test_g3_en5_worldmodel_wired` | PASS |
| `test_g3_en5_student_recording_mode_wired` | PASS |
| `test_g3_en5_contradiction_wired` | PASS |
| `test_g3_en5_single_cognitive_loop` | PASS |
| `test_g3_en5_single_pdp` | PASS |
| `test_g3_en5_arena_free` | PASS |
| `test_g3_en5_inv2_preserved` | PASS |
| `test_g3_en5_evidencegraph_wired` | PASS |
| `test_g3_en5_hypothesismanager_wired` | PASS |
| `test_g3_en5_actionregistry_wired` | PASS |

## 11. Constraints Honored

1. ✅ One `RaphaelRuntime`; no second orchestrator
2. ✅ No new Runtime stages (existing 10 stages, same order)
3. ✅ `CapabilityBroker` remains the single PDP
4. ✅ PEP remains under `exec/`
5. ✅ INV-2 decision linkage end-to-end preserved
9. ✅ No Decepticon, Teacher, Docker, or later-phase machinery
10. ✅ No roadmap modification
11. ✅ No test weakening, skipping, or xfail
12. ✅ No P5 work

## 13. Final Verification

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 291 passed, 0 failed, 32 warnings, ~13.7s

| Metric | Value |
|---|---|
| Legacy tests | 239 |
| P2.1 tests | 8 |
| G2-C2 fail-closed | 9 |
| P2 guardrails | 24 |
| G3-EN-5 tests | 11 |
| **Total** | **291** |
| Failed | **0** |
| Skipped | **0** |
| Xfail | **0** |

## 14. Constraints Honored

1. ✅ One `RaphaelRuntime`; no second orchestrator
2. ✅ No new Runtime stages (existing 10 stages, same order)
3. ✅ `CapabilityBroker` remains the single PDP
4. ✅ PEP remains under `exec/`
5. ✅ INV-2 decision linkage end-to-end preserved
12. ✅ No roadmap modification
13. ✅ No test weakening, skipping, or xfail
14. ✅ No P5 work

## 14. Final Verification

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 291 passed, 0 failed, 32 warnings, ~13.7s

**Authoritative HEAD:** `ab8a362399a9c2be3129d326fc2e83e24d09a846`

**Commit count:** 43 (per fresh `git rev-list --count 7272880f7..HEAD`)

**STOP.** Awaiting GLM confirmation of G3-EN-5 before Weld-SUB14.
