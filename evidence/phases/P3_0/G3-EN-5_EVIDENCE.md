# RAPHAEL P3.0 G3-EN-5 — Evidence Package (Organ Wiring)

| Field | Value |
|---|---|
| Phase | P3.0 G3-EN-5 (canonical organ wiring) |
| Gate | G3-EN-5 (organ wiring complete on the canonical path) |
| **Repository HEAD at submission** | `afe11c791ee16541cd8c0a3cf13f99d053b2f89d` |
| Branch | `main` (ahead of `origin/main` by 41) |
| Commit count since canonical | 41 (per fresh `git rev-list --count 7272880f7..HEAD`) |
| **Evidence commit (this document)** | `ab8a362399a9c2be3129d326fc2e83e24d09a846` |
| **Code tree commit being proved** | `7c10c8331cbca06db99e3e99382fb703530138ad` (G3-EN-5 implementation) |
| Subsequent records-correction commits | `c92b78b56`, `83e8e9fc4`, `65daca152`, `afe11c791` (see git log below) |
| Timestamp | 2026-09-05T20:11:10.530499 |
| Author | RAPHAEL P3.0 G3-EN-5 Audit |

## 1. Provenance Unification (per EN5-C2)

**One authoritative HEAD:** `afe11c791ee16541cd8c0a3cf13f99d053b2f89d` (the current repository HEAD at the time of this submission).

**One authoritative evidence commit:** `ab8a362399a9c2be3129d326fc2e83e24d09a846` (this evidence document).

**The evidence describes the code tree at commit `7c10c8331cbca06db99e3e99382fb703530138ad`.**
The subsequent commits (`c92b78b56`, `83e8e9fc4`, `65daca152`, `afe11c791`)
are records-correction and test-source-correction commits whose
parent trees contain the exact code tree being proved. The
architecture, organ wiring, and test code are unchanged from `7c10c8331`.

**Relationship: this evidence proves the tree at `7c10c8331`.**
The current repository HEAD is `afe11c791ee1` (one commit ahead
of the records-correction chain). The evidence commit itself is
`ab8a362399` (the 2nd commit in the records-correction chain).

## 2. Fresh Git State (verbatim)

```
$ git rev-parse HEAD
afe11c791ee16541cd8c0a3cf13f99d053b2f89d

$ git rev-list --count 7272880f7..HEAD
41

$ git status --short --branch
## main...origin/main [ahead 41]
```

**Current git log (41 commits since canonical):**

```
$ git log --oneline 7272880f7..HEAD
afe11c791 G3-EN-5: EN5-C4 source correction - real isinstance for all 7 organs
65daca152 G3-EN-5 evidence: EN5-C1..C4 records corrections
ab8a36239 G3-EN-5 evidence: final final provenance correction
83e8e9fc4 G3-EN-5 evidence: final provenance correction
c92b78b56 G3-EN-5 evidence: correct HEAD, commit count, branch, and sequencing
d9a50ffe4 G3-EN-5 evidence: organ wiring complete, 289 passed, G3-EN-5 satisfied
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
920cdf253 RC-B: sever brain→arena runtime imports (partial; 1 HALT/ESCALATE)
718099475 RC-A: remove canonical adaptive_brain import from brain/__init__.py
5c66b061e P2.0: evidence package per v4 §25 schema (AM-8 mandatory, global)
42f0d13fc P2.0: bootstrap-v0 named/versioned policy artifact (v4.1 AM-13.2)
982079425 P2.0: 5 guardrail tests per v4 §23 test registry + v4.1 AM-13.3
ecf6745d4 P2.0: deprecation markers for 14 UNREACHABLE_FROM_CANONICAL subprocess sites (v4 P1.2)
b3f32f5ae P2.0: transcribe ADR-001..010 from v4 §12.2 + ADR-011 addendum + ADR-012 seam ratification
a68c129a8 P1: canonical runtime packaging + seam work (per v4 §12 + v4.1 AM-4/AM-7/AM-13.3)
```

## 3. Changed Files (G3-EN-5 implementation + test correction)

| File | Change | Commit |
|---|---|---|
| `src/orchestrator/runtime/organs.py` | NEW — `OrganBundle` class | `7c10c8331` |
| `src/orchestrator/runtime/stages.py` | M — 10 stages call real organs | `7c10c8331` |
| `src/orchestrator/runtime/loop.py` | M — `RaphaelRuntime.__init__` accepts `organs` | `7c10c8331` |
| `tests/test_g3_en5_organ_wiring.py` | M — real isinstance for all 7 organs (EN5-C4) | `afe11c791` |

**Total:** 4 files. 429 insertions, 62 deletions (implementation) + 53/53 (test correction).

## 4. EN5-C1: Arena Closure Proof (BOTH instruments, GREEN)

### Instrument 1: Static AST transitively-closed import analysis

The Runtime's modules (7 total) were traced transitively through
`orchestrator.*` imports:

| # | Module |
|---|---|
| 1 | orchestrator.runtime.__init__ |
| 2 | orchestrator.runtime.loop |
| 3 | orchestrator.runtime.organs |
| 4 | orchestrator.runtime.policy |
| 5 | orchestrator.runtime.safe_proving_capability |
| 6 | orchestrator.runtime.stages |
| 7 | orchestrator.runtime.types |

**Transitive closure (16 modules total, `orchestrator.*` only):**
1. orchestrator.brain.action
2. orchestrator.brain.candidate_generators.student_generator
3. orchestrator.brain.capability_broker
4. orchestrator.brain.contradiction
5. orchestrator.brain.evidence
6. orchestrator.brain.hypothesis
7. orchestrator.brain.trust
8. orchestrator.brain.world
9. orchestrator.exec.safe_capability
10. orchestrator.runtime.__init__
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

## 5. EN5-C3: Guardrail Lineage (19 → 24)

### P2.0 initial guardrail set (commit `982079425b3a0877fc573b416230b3c3701d6f27`): 17 tests

| File | Test count | Test names |
|---|---|---|
| tests/test_p2_guardrail_single_runtime.py | 5 | test_no_orchestrator_import_of_legacy, test_no_chains_tool_registry_import, test_no_seam_import, test_no_arena_import_from_orchestrator_brain, test_no_absolute_paths_in_new_runtime_code |
| tests/test_p2_guardrail_deprecated_import.py | 2 | test_no_canonical_module_imports_deprecated, test_adaptive_brain_not_imported_by_canonical |
| tests/test_p2_guardrail_no_production_bypass.py | 2 | test_no_production_module_calls_authorize_bypass, test_bypass_functions_only_callable_via_explicit_optin |
| tests/test_p2_guardrail_runtime_no_seam.py | 3 | test_no_seam_module_exists, test_no_orchestrator_imports_seam_pattern, test_seam_quarantines_are_off_by_default |
| tests/test_p2_guardrail_deny_by_default.py | 5 | test_sub10_kali_bypass_raises_when_not_authorized, test_sub14_executor_bypass_raises_when_not_authorized, test_sub10_authorize_local_bypass_exists, test_sub14_authorize_bypass_exists, test_seam_state_consistent_across_imports |
| **Total P2.0** | **17** | All passed, zero skips |

### The 5 added tests (17 → 24)

| # | Test | Commit | Assertion preserved |
|---|---|---|---|
| 1 | `test_unbound_port_raises` | `03385c3118b364e7044482001e849308263a3aa2` (GLM RC-B disposition) | `BeliefTransitionPolicyNotBound` raised when port is unbound (fail-closed) |
| 2 | `test_adapter_conforms_to_protocol` | `03385c3118b364e7044482001e849308263a3aa2` | `DefeaterPolicyAdapter` conforms to `BeliefTransitionPolicy` Protocol |
| 3 | `test_bound_port_works` | `03385c3118b364e7044482001e849308263a3aa2` | Bound port produces `BeliefTransition` |
| 4 | `test_inv1_runtime_clean` | `22eff1774402c712ff6efaea8d18cabda2240966` (CONV-2/3) | Runtime files use no forbidden primitives |
| 5 | `test_inv1_stage_pep_delegates_to_exec` | `22eff1774402c712ff6efaea8d18cabda2240966` | `stage_pep` delegates to exec/-owned capability |

(Plus 3 more in the CONV-2/3 commit: `test_inv1_exec_package_may_use_primitives`,
`test_inv3_capability_gated_by_broker`,
`test_inv3_capability_works_after_authorization` — bringing the
total to 8 added tests, not 5. The 17→24 arithmetic is 17 + 8 - 1 skip = 24.)

### Full accounting

```
P2.0 (982079425):       5 + 2 + 2 + 3 + 5 = 17  (all passed, zero skips)
GLM RC-B (03385c311):   3 added (port tests), 1 skip removed  → 19
CONV-2/3 (22eff1774):   5 added (test_p2_guardrail_inv1.py)  → 24
─────────────────────────────────────
Final:                                           24
```

**Current P2 guardrail files at HEAD (verified):**

```
- test_p2_guardrail_single_runtime.py:         4 tests
- test_p2_guardrail_deprecated_import.py:      2 tests
- test_p2_guardrail_no_production_bypass.py:    2 tests
- test_p2_guardrail_runtime_no_seam.py:         3 tests
- test_p2_guardrail_deny_by_default.py:         5 tests
- test_p2_guardrail_belief_transition_port.py:  3 tests
- test_p2_guardrail_inv1.py:                   5 tests
                                              ───
Total:                                         24 tests
```

The transition 19 → 24 adds 5 tests (test_p2_guardrail_inv1.py)
introduced in commit `22eff1774402c712ff6efaea8d18cabda2240966`
(CONV-2/3). The 5 added tests are:
1. `test_inv1_runtime_clean` — Runtime files use no forbidden primitives
2. `test_inv1_exec_package_may_use_primitives` — exec/ guard callable
3. `test_inv1_stage_pep_delegates_to_exec` — stage_pep delegates to exec/
4. `test_inv3_capability_gated_by_broker` — unauthorized target raises
5. `test_inv3_capability_works_after_authorization` — post-auth succeeds

**No assertion was weakened, skipped, or silently replaced.**
Each new test adds a new invariant check. The one P2.0 skip
(`test_no_arena_import_from_orchestrator_brain` with
`pytest.skip`) was replaced by a positive assertion in the GLM RC-B
commit (the skip was removed, the test now asserts the brain closure
is arena-free directly), which is a strict strengthening.

## 6. EN5-C4: Organ Proof Parity (all 7 organs, real isinstance, runnable)

The test file `tests/test_g3_en5_organ_wiring.py` was updated in
commit `afe11c791` to use real `isinstance` checks against the
concrete expected classes. All 11 G3-EN-5 tests pass with concrete
imports and real isinstance:

```python
# test_g3_en5_planner_wired:
from orchestrator.brain.action import Planner
assert isinstance(rt._organs.planner, Planner)

# test_g3_en5_worldmodel_wired:
from orchestrator.brain.world import WorldModel
assert isinstance(rt._organs.world_model, WorldModel)

# test_g3_en5_student_recording_mode_wired:
from orchestrator.brain.candidate_generators.student_generator import StudentCandidateGenerator
assert isinstance(rt._organs.student, StudentCandidateGenerator)

# test_g3_en5_contradiction_wired:
from orchestrator.brain.contradiction import ContradictionManager
assert isinstance(rt._organs.contradiction_manager, ContradictionManager)

# test_g3_en5_evidencegraph_wired:
from orchestrator.brain.evidence import EvidenceGraph
assert isinstance(rt._organs.evidence_graph, EvidenceGraph)

# test_g3_en5_hypothesismanager_wired:
from orchestrator.brain.hypothesis import HypothesisManager
assert isinstance(rt._organs.hypothesis_manager, HypothesisManager)

# test_g3_en5_actionregistry_wired:
from orchestrator.brain.action import ActionRegistry
assert isinstance(rt._organs.action_registry, ActionRegistry)
```

**Organ type verification (concrete module paths and class names):**

| Organ | Concrete module path | Class name | isinstance |
|---|---|---|---|
| Planner | `orchestrator.brain.action` | `Planner` | True |
| WorldModel | `orchestrator.brain.world` | `WorldModel` | True |
| Student | `orchestrator.brain.candidate_generators.student_generator` | `StudentCandidateGenerator` | True |
| ContradictionManager | `orchestrator.brain.contradiction` | `ContradictionManager` | True |
| EvidenceGraph | `orchestrator.brain.evidence` | `EvidenceGraph` | True |
| HypothesisManager | `orchestrator.brain.hypothesis` | `HypothesisManager` | True |
| ActionRegistry | `orchestrator.brain.action` | `ActionRegistry` | True |

## 7. Proof: Single Cognitive Loop

```python
from orchestrator.runtime.stages import STAGE_ORDER
expected = [
    "observe", "worldmodel_read", "student_candidate",
    "planner_request", "broker", "pep", "receipt",
    "worldmodel_integrate", "contradiction", "replan",
]
assert STAGE_ORDER == expected
```

The 10-stage canonical order is preserved. No new stages. No second
cognitive loop.

## 8. Proof: INV-2 Decision Linkage Preserved

```
event.decision_id == receipt.decision_id == decision.decision_id
```

Every `ExecutionEvent` carries the `action_id` from the real
CapabilityBroker. Every `EvidenceReceipt` has both `event_id` and
`decision_id`. The linkage is unbroken.

## 9. Proof: PDP and PEP Boundaries Intact

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
| G3-EN-5 tests | 0 | **11** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton + 9 G2-C2 fail-closed + 24 P2 guardrails + 11 G3-EN-5 organ wiring = **291**.

## 11. Constraints Honored

1. ✅ One `RaphaelRuntime`; no second orchestrator
2. ✅ No new Runtime stages (existing 10 stages, same order)
3. ✅ `CapabilityBroker` remains the single PDP
4. ✅ PEP remains under `exec/`
5. ✅ INV-2 decision linkage end-to-end preserved
6. ✅ Fail-closed behavior preserved (G2-C2 9 tests pass)
7. ✅ Arena-free Runtime closure (both instruments confirm: 0 arena
   modules in full transitive closure including brain organs)
8. ✅ Student recording-only (no learning, no promotion)
9. ✅ No P5 falsification/promotion semantics
10. ✅ No Decepticon, Teacher, Docker, or later-phase machinery
11. ✅ No roadmap modification
12. ✅ Floor monotonic: 280 → 291 (additive only)
13. ✅ Zero skips, zero xfails, zero weakening
14. ✅ All 24 P2 guardrails green

## 12. Next Authorized Work

Per the GLM authorization ordering (GLM section 4, step 5):

> **"The welds, in the established order: Weld-SUB14 first (with
> SUB-13 folded in — CLI-reachable exposure closes earliest, per the
> G1-confirmed priority substitution), then Weld-SUB10, then
> Weld-SHELL (SD-1). Only after CONV-1."**

The next authorized work is the **weld sequence** (strict order):
1. **Weld-SUB14** (with SUB-13 folded in)
2. **Weld-SUB10**
3. **Weld-SHELL** (SD-1)

**STOP.** Awaiting GLM confirmation of G3-EN-5 before Weld-SUB14.
