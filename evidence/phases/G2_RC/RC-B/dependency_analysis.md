# RC-B Escalation: `apply_belief_transition` Dependency Analysis

**Phase:** G2 RC-B escalation
**Status:** Analysis only. No implementation.
**Author:** RAPHAEL P2.0 Audit
**Date:** 2026-09-05

## 1. Where `apply_belief_transition` is defined

Two definitions exist:

1. **`src/arena/defeater.py:172`** — original, canonical, 23019-byte file
2. **`src/orchestrator/brain/defeater_types.py:96`** — RC-B re-home stub (created in earlier RC-B commit), 3641-byte file

The original is in Arena; the brain-owned version is a simplified stub.

## 2. Module/package ownership

| Definition | Location | Owner | Size | Status |
|---|---|---|---|---|
| `arena.defeater.apply_belief_transition` | `src/arena/defeater.py:172` | Arena | 23019 bytes total file | Original, canonical |
| `orchestrator.brain.defeater_types.apply_belief_transition` | `src/orchestrator/brain/defeater_types.py:96` | Brain | 3641 bytes total file | RC-B re-home stub (simplified) |

Per v4 §3.1: "cognitive machinery: canonical" and "arena coupling: remove."
Per v4 INV-5: "CLI → Runtime; Runtime does not import arena."

The Arena ownership is a historical artifact from when Arena contained
both evaluation harness AND cognitive machinery. Per v4, cognitive
machinery is brain-owned. The defeater/falsification machinery is
cognitive machinery (D-5 per v4 §16 / P5).

## 3. Why hypothesis.py imports from arena

**Import location:** `src/orchestrator/brain/hypothesis.py:536`
```python
from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
```

**Reason:** `hypothesis.py:apply_defeater_result()` is the D-5 cognitive
machinery that applies the frozen V2 belief transition policy when a
defeater result arrives. The policy is encoded in arena/defeater.py as
two tables (`TRIGGERED_TRANSITIONS`, `NOT_TRIGGERED_TRANSITIONS`) plus
the `apply_belief_transition` function that dispatches on them.

The import is a historical artifact: the defeater machinery was
implemented in Arena before v4 INV-5 existed, and brain adopted it
via the lazy runtime import pattern (to avoid module-load cycles).

## 4. Every symbol imported by the offending edge

```python
from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
```

Three symbols:

1. **`apply_belief_transition`** — the policy dispatcher function
2. **`DefeaterOutcome`** — an `Enum` with 4 values: TRIGGERED, NOT_TRIGGERED, INCONCLUSIVE, NOT_TESTABLE
3. **`BeliefTransition`** — a frozen dataclass recording the causal link from DefeaterResult to hypothesis change

## 5. Every call site/use in hypothesis.py

| Line | Symbol | Usage |
|---|---|---|
| 516 | `BeliefTransition` | Type annotation: `-> Optional["BeliefTransition"]` (type-only) |
| 523 | `BeliefTransition` | Docstring mention (not code) |
| 531 | `BeliefTransition` | Docstring mention (not code) |
| 546 | `DefeaterOutcome` | Runtime check: `if defeater_result.outcome in (DefeaterOutcome.INCONCLUSIVE, DefeaterOutcome.NOT_TESTABLE):` |
| 550 | `apply_belief_transition` | **Runtime call**: `post_confidence, post_state_str = apply_belief_transition(prior_state=..., prior_confidence=..., outcome=...)` |
| 573 | `BeliefTransition` | **Runtime construction**: `transition = BeliefTransition(hypothesis_id=..., ...)` |

**Summary:**
- `BeliefTransition`: 1 type annotation, 2 docstring mentions, 1 runtime construction
- `DefeaterOutcome`: 1 runtime check
- `apply_belief_transition`: 1 runtime call (the core of the issue)

## 6. Dependency classification

**Runtime logic.** The function is called at runtime inside
`apply_defeater_result()`. It is not a type hint, not test-only, and
not dead code. It is genuine cognitive functionality (D-5
defeater/falsification machinery per v4 §16).

The `BeliefTransition` and `DefeaterOutcome` symbols are also runtime
(since `apply_defeater_result` constructs `BeliefTransition` and
checks `DefeaterOutcome`).

## 7. Complete dependency chain required to satisfy the function

```
hypothesis.py:apply_defeater_result()
  └─ from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
       └─ arena.defeater (module load)
            ├─ TRIGGERED_TRANSITIONS (dict: 4 entries, lambdas)
            ├─ NOT_TRIGGERED_TRANSITIONS (dict: 4 entries, lambdas)
            ├─ INCONCLUSIVE_TRANSITION (lambda)
            ├─ POLICY_VERSION (string: "D5_V2_2026-07-26")
            ├─ HYPOTHESIS_STATES (list)
            ├─ DefeaterOutcome (Enum: 4 values)
            ├─ DefeaterResult (frozen dataclass, 12 fields)
            ├─ Defeater (frozen dataclass, 9 fields, from earlier in file)
            └─ apply_belief_transition (function: 60+ lines, dispatches on tables)
```

The function depends on:
- 2 lookup tables with 4 entries each (8 lambdas total)
- 1 fallback lambda
- 2 metadata constants
- 1 Enum
- 2 frozen dataclasses (Defeater, DefeaterResult) — but the function
  itself only uses DefeaterOutcome

**The dependency chain is: policy tables + Enum + the dispatcher function.**

The function `apply_belief_transition` itself is ~60 lines of
straightforward dispatch logic. The tables are 8 lines total. The
Enum is 5 lines. The function is not complex; the COMPLEXITY is in
the policy tables (which encode the D-5 V2 falsification policy).

## 8. Scale assessment: P2-small or P5-scale?

**GENUINELY P5-SCALE.**

Rationale:

1. **The function encodes D-5 V2 falsification policy.** The policy
   tables `TRIGGERED_TRANSITIONS` and `NOT_TRIGGERED_TRANSITIONS` are
   the frozen V2 falsification semantics (POLICY_VERSION = "D5_V2_2026-07-26").
   Per v4 §16, D-5 is the P5 phase. Per v4.1 AM-14, P5 task granularity
   must be "elevated to P3-grade detail" and the contradiction predicate
   (v4.1 AM-2) must be defined as a GLM Contract deliverable at the
   START of P5.

2. **v4.1 AM-2 explicitly mandates the contradiction predicate as a
   P5 deliverable:** "Define the contradiction predicate as a typed
   comparison... This must be a data-level rule, not a prose
   description — a reviewer must be able to construct a synthetic (F, O)
   pair and mechanically determine the predicate's output without
   reading implementation code." The `apply_belief_transition` function
   IS the contradiction predicate's implementation (or a key part of
   it). Moving it without the P5 contradiction predicate contract
   would be pulling P5 semantics into P2.

3. **The brain-owned stub (defeater_types.py:96) is semantically
   WRONG.** My earlier RC-B attempt to re-home produced a simplified
   stub that returns the wrong state names ("WEAKENED", "REINFORCED",
   "UNCHANGED") instead of the V2 policy's correct state names
   ("POSTULATED", "DOUBTFUL", "ABANDONED"). This would silently
   break the hypothesis state machine. Re-homing requires reproducing
   the EXACT V2 policy tables, which is P5-scale semantic work.

4. **The function is the "dedicated semantic boundary for defeater
   belief updates" (per its docstring).** Moving it without
   preserving the exact semantics is a silent contract violation.

5. **The HypothesisStatus state_map in hypothesis.py:559-566 maps
   post_state_str back to HypothesisStatus enum values.** The V2
   policy returns state strings that are mapped to specific
   HypothesisStatus values. Changing the policy (even to a "simplified"
   version) breaks this mapping.

**Verdict: P5-scale work.** The re-homing is not a mechanical move; it
requires reproducing the D-5 V2 falsification policy tables, which is
the core of P5. Per v4.1 AM-14: "P5 is the second-riskiest refactor in
the program after P3." Per RC-B: "If `apply_belief_transition` is
actually part of the historical defeater/falsification machinery and
moving it would amount to P5-scale semantic redesign: HALT and
classify it as P5-scale."

## 9. Does brain/action.py have a dependency on the same symbol?

**NO.** `grep -n "apply_belief_transition\|BeliefTransition\|DefeaterOutcome" src/orchestrator/brain/action.py` returns zero matches.

`brain/action.py` (Planner) was already re-homed in the earlier RC-B
commit: PlanDecision is now imported from
`orchestrator.brain.plan_decision` (brain-owned), and the lazy runtime
import inside `Planner.decide()` was updated to use the brain-owned
version. No further action needed for `action.py`.

## 10. Real brain↔arena cycle after the two completed RC-B re-homes

**Brain → Arena runtime imports (after RC-A, RC-B, RC-D):**
- `src/orchestrator/brain/hypothesis.py:536` — `from arena.defeater import ...` (the remaining HALT/ESCALATE)

**Arena → Brain runtime imports (extensive, pre-existing):**
- `src/arena/ablation_runner.py:67-71` — imports from `orchestrator.brain.evidence`, `.world`, `.hypothesis`, `.contradiction`, `.capability_broker`
- `src/arena/d7_r1_mechanism_test.py:24,30,31,32` — imports from `orchestrator.brain.action`, `.world`, `.evidence`, `.capability_broker`
- `src/arena/d6_manifest.py:213` — imports from `orchestrator.brain.capability_broker`

**Cycle analysis:**
- Arena → brain: yes (extensive, pre-existing, not introduced by RC)
- Brain → arena: only 1 remaining (hypothesis.py:536)
- **This is NOT a cycle.** The remaining import is a one-way edge from
  brain to arena. The reverse edges (arena → brain) are pre-existing
  and not a problem for brain's independence (they show that arena
  already depends on brain, which is the correct direction per v4 §3.1).

The HALT/ESCALATE is about the brain → arena edge, not about a cycle.
There is no actual `brain ↔ arena` import cycle.

## Conclusion

**RC-B status: P5-SCALE.**

The `apply_belief_transition` function is part of the D-5 V2
falsification policy machinery, which is P5 work per v4 §16 and
v4.1 AM-2/AM-14. Re-homing it requires reproducing the exact V2
policy tables (TRIGGERED_TRANSITIONS, NOT_TRIGGERED_TRANSITIONS,
INCONCLUSIVE_TRANSITION, POLICY_VERSION, HYPOTHESIS_STATES) without
silent semantic drift. This is not a mechanical move; it is P5-scale
semantic work that must be done under the P5 contradiction predicate
contract (v4.1 AM-2) and P5 task matrix (v4.1 AM-14).

**Recommended disposition:** Classify as P5-scale. Do NOT attempt a
superficial re-home. Leave the lazy runtime import in
`hypothesis.py:536`. Document the HALT/ESCALATE in the G2 RC
evidence. Defer the actual re-homing to P5.1+ when the contradiction
predicate contract exists.
