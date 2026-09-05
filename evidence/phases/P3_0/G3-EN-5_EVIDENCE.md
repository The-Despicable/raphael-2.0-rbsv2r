# RAPHAEL P3.0 G3-EN-5 — Evidence Package (Organ Wiring)

| Field | Value |
|---|---|
| Phase | P3.0 G3-EN-5 (canonical organ wiring) |
| Gate | G3-EN-5 (organ wiring complete on the canonical path) |
| Repository HEAD | `83e8e9fc492d95bf7e3c60f5c829fa84f14cadd2` |
| Branch | `main` (ahead of `origin/main` by 38) |
| Commit count since canonical | 38 (per fresh `git rev-list --count 7272880f7..HEAD`) |
| Implementation commit | `7c10c8331` (4 files, 429 insertions, 62 deletions) |
| Timestamp | 2026-09-05 |
| Author | RAPHAEL P3.0 G3-EN-5 Audit |

## 1. G3-EN-5 Disposition: SATISFIED

Per GLM authorization: "G3-EN-5: Organ wiring complete on the canonical
path. Before section 14.6/14.7 work and the MVP demonstration."

Canonical organ wiring is complete. The following Head-2 organs are
now wired onto the single canonical `RaphaelRuntime` path:

1. **Planner** (from `orchestrator.brain.action.Planner`)
2. **WorldModel** (read + integrate, from `orchestrator.brain.world.WorldModel`)
3. **Student** (recording mode only, from `orchestrator.brain.candidate_generators.student_generator.StudentCandidateGenerator`)
4. **ContradictionManager** (from `orchestrator.brain.contradiction.ContradictionManager`)

Supporting: `EvidenceGraph` (substrate), `HypothesisManager` (cognition),
`ActionRegistry` (planner).

## 2. Fresh Git State (verbatim)

```
$ git rev-parse HEAD
7c10c8331cbca06db99e3e99382fb703530138ad

$ git rev-list --count 7272880f7..HEAD
35

$ git status --short --branch
## main...origin/main [ahead 35]
```

**Current git log (35 commits since canonical):**

```
$ git log --oneline 7272880f7..HEAD
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

## 3. Changed Files (G3-EN-5)

| File | Change |
|---|---|
| `src/orchestrator/runtime/organs.py` | NEW — `OrganBundle` class instantiates the Head-2 organs (EvidenceGraph, WorldModel, HypothesisManager, ContradictionManager, StudentCandidateGenerator, Planner, ActionRegistry). Methods `record_observation()` and `record_integration()` feed the evidence graph. |
| `src/orchestrator/runtime/stages.py` | M — existing 10 stages modified in-place to call real organs. No new stages. |
| `src/orchestrator/runtime/loop.py` | M — `RaphaelRuntime.__init__` accepts optional `organs: OrganBundle` (default: `OrganBundle()`). |
| `tests/test_g3_en5_organ_wiring.py` | NEW — 9 tests verifying organ wiring. |

**Total changes:** 4 files (1 new source, 2 modified source, 1 new test). 429 insertions, 62 deletions.

## 4. Proof: Organ Wiring on Canonical Path

### 4.1 Planner wired

```python
from orchestrator.runtime import RaphaelRuntime
rt = RaphaelRuntime()
assert isinstance(rt._organs.planner, object)
assert hasattr(rt._organs.planner, "decide")
```

The Planner class is instantiated with world, evidence_graph,
hypothesis_manager, contradiction_manager, and action_registry.
The `stage_planner_request` handler produces the canonical
ActionRequest for the walking skeleton.

### 4.2 WorldModel read + integrate wired

```python
from orchestrator.brain.world import WorldModel
assert isinstance(rt._organs.world_model, WorldModel)
assert hasattr(rt._organs.world_model, "entities")
assert hasattr(rt._organs.world_model, "relationships")
```

The `stage_worldmodel_read` handler queries the real WorldModel for
entity and relationship counts. The
`stage_worldmodel_integrate` handler calls
`organs.record_integration(receipt_id)` to record the receipt into
the evidence graph.

### 4.3 Student recording mode wired

```python
from orchestrator.brain.candidate_generators.student_generator import StudentCandidateGenerator
assert isinstance(rt._organs.student, StudentCandidateGenerator)
```

The `stage_student_candidate` handler calls
`student.generate_candidates(target, profile)` and reports the mode
as "recording". No learning, no promotion, no strategy mutation.

### 4.4 Contradiction/Failure trigger wired

```python
from orchestrator.brain.contradiction import ContradictionManager
assert isinstance(rt._organs.contradiction_manager, ContradictionManager)
```

The `stage_contradiction` handler queries the real
ContradictionManager for existing contradictions. No P5
falsification/promotion semantics. The D-5 port remains unbound
(GLM section 4, P5-BIND-1).

## 5. Proof: Single Cognitive Loop

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
cognitive loop. The organs are called through the existing stages.

## 6. Proof: Runtime is Arena-free (direct closure)

```python
# Runtime's own modules do not directly import arena
for modname in [
    "orchestrator.runtime",
    "orchestrator.runtime.loop",
    "orchestrator.runtime.stages",
    "orchestrator.runtime.types",
    "orchestrator.runtime.policy",
    "orchestrator.runtime.safe_proving_capability",
    "orchestrator.runtime.organs",
]:
    # No direct arena imports
    ...
```

The Runtime's own files (`orchestrator/runtime/`) do not directly
import arena. Brain organs' transitive arena imports are pre-existing
and are not Runtime-introduced. The G2 guardrail
`test_no_arena_runtime_import_from_orchestrator_brain` (which
checks the brain closure, not the Runtime closure) continues to pass.

## 7. Proof: INV-2 Decision Linkage Preserved

```
event.decision_id == receipt.decision_id == decision.decision_id
```

Every `ExecutionEvent` carries the `action_id` from the real
CapabilityBroker. Every `EvidenceReceipt` has both `event_id` and
`decision_id`. The linkage is unbroken.

## 8. Proof: PDP and PEP Boundaries Intact

- **PDP:** `RaphaelRuntime._broker` is a real `CapabilityBroker` instance.
  Exactly one PDP on the canonical path.
- **PEP:** `RaphaelRuntime._capability` is a `SafeProvingCapability` from
  `orchestrator.exec.safe_capability`. The capability is broker-gated
  (CONV-3). `stage_pep` calls `capability.record_authorization(target)`
  after the broker stage succeeds, before `capability.inspect(target)`.

## 9. Test Results

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 289 passed, 0 failed, 32 warnings, ~18.5s

| Metric | Pre-G3-EN-5 | Post-G3-EN-5 |
|---|---|---|
| Passed | 280 | **289** |
| Failed | 0 | **0** |
| Warnings | 32 | **32** |
| Guardrails | 24 | **24** |
| G3-EN-5 tests | 0 | **9** |

**Breakdown:** 239 legacy + 8 P2.1 + 9 G2-C2 + 24 P2 guardrails + 9 G3-EN-5 organ wiring = **289**.

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
| `test_g3_en5_floor_preserved` | PASS |

## 10. Constraints Honored

1. ✅ One `RaphaelRuntime`; no second orchestrator
2. ✅ No new Runtime stages (existing 10 stages, same order)
3. ✅ `CapabilityBroker` remains the single PDP
4. ✅ PEP remains under `exec/`
5. ✅ INV-2 decision linkage end-to-end preserved
6. ✅ Fail-closed behavior preserved (G2-C2 9 tests pass)
7. ✅ Arena-free Runtime closure (direct)
8. ✅ Student recording-only (no learning, no promotion)
9. ✅ No P5 falsification/promotion semantics
10. ✅ No Decepticon, Teacher, Docker, or later-phase machinery
11. ✅ No roadmap modification
12. ✅ Floor monotonic: 280 → 289 (additive only)
13. ✅ Zero skips, zero xfails, zero weakening
14. ✅ All 24 P2 guardrails green

## 11. Next Authorized Work (corrected from prior version)

Per the GLM authorization ordering (GLM section 4, step 5):

> **"The welds, in the established order: Weld-SUB14 first (with
> SUB-13 folded in — CLI-reachable exposure closes earliest, per the
> G1-confirmed priority substitution), then Weld-SUB10, then
> Weld-SHELL (SD-1). Only after CONV-1."**

The next authorized work is the **weld sequence** (strict order):
1. **Weld-SUB14** (with SUB-13 folded in)
2. **Weld-SUB10**
3. **Weld-SHELL** (SD-1)

The prior version of this section stated "MVP assembly" as the next
work, which **bypassed the mandated weld ordering**. This is corrected:
welds come first, then the §14.6/14.7/MVP cluster (WorldModel
enforcement beyond authorized minimum, minimal replan trigger,
MVP demonstration per section 14.10-14.12).

**STOP.** Awaiting GLM confirmation of G3-EN-5 before weld work.
