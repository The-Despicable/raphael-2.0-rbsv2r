# RC-B: Option Analysis — three permitted mechanisms for severing brain → arena

## Context

The remaining brain → arena runtime import is at
`src/orchestrator/brain/hypothesis.py:536`:
```python
from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
```

This is the D-5 V2 falsification policy machinery (per v4 §16).
The function `apply_belief_transition` + its transition tables
encode the frozen V2 belief-update policy (POLICY_VERSION =
"D5_V2_2026-07-26").

GLM has determined that the brain → arena dependency must be
severed before Runtime birth, but allows escalation if P5-scale
work is required.

---

## Option A — Re-home

**Description:** Move `apply_belief_transition`, `DefeaterOutcome`,
`BeliefTransition`, and the transition tables from
`src/arena/defeater.py` to a brain-owned module (or to the existing
`src/orchestrator/brain/defeater_types.py`).

**Affected files:**
- `src/orchestrator/brain/defeater_types.py` (extend the existing stub to match the V2 policy exactly)
- `src/orchestrator/brain/hypothesis.py:536` (update import)
- `src/arena/defeater.py` (deprecate or leave as backward-compat shim)
- `src/arena/ablation_runner.py` and other arena callers (if they use the same symbols)

**Architectural direction:** Brain becomes the canonical owner of the
D-5 V2 falsification policy. Arena becomes a consumer (via brain →
arena direction reversal). This is the correct direction per v4 §3.1
("cognitive machinery: canonical") and v4 INV-5.

**Behavioral risk: HIGH.** The existing brain-owned stub at
`defeater_types.py:96` returns WRONG state names ("WEAKENED",
"REINFORCED", "UNCHANGED") instead of the V2 policy's correct state
names ("POSTULATED", "DOUBTFUL", "ABANDONED"). A naive re-home would
silently break the hypothesis state machine (the state_map at
hypothesis.py:559-566 expects the V2 state names). Reproducing the
EXACT V2 policy requires:
- TRIGGERED_TRANSITIONS table with 4 entries (state-specific lambdas)
- NOT_TRIGGERED_TRANSITIONS table with 4 entries
- INCONCLUSIVE_TRANSITION fallback
- State-dependent dispatch logic (~60 lines)
- The HYPOTHESIS_STATES list and POLICY_VERSION constant

**Migration complexity: HIGH.** The re-home itself is mechanical
(cut from arena, paste into brain, update imports). But preserving
the EXACT semantics requires reproducing the V2 policy tables, which
is the core of P5 work.

**P2-legal: NO.** The V2 policy is the D-5 falsification machinery,
which is P5 per v4 §16. Moving it without the P5 contradiction
predicate contract (v4.1 AM-2) and the P5 task matrix (v4.1 AM-14)
would be pulling P5 semantics into P2.

**Would it pre-empt P5 work: YES.** Reproducing the V2 policy tables
would constitute implementing P5 falsification machinery before P5
is authorized. This violates v4.1 AM-14 ("P5 task granularity elevated
to P3-grade detail") and the gated phase ordering.

**Verdict:** NOT RECOMMENDED in P2. Possible in P5.1+ under the
proper P5 contracts.

---

## Option B — TYPE_CHECKING

**Description:** Move the import to `TYPE_CHECKING` guard so it
becomes type-only (no runtime import).

**Affected files:**
- `src/orchestrator/brain/hypothesis.py:536` (wrap in TYPE_CHECKING)

**Architectural direction:** Removes the runtime import edge.
TYPE_CHECKING imports are contract-compliant per v4.1 AM-13.3 (type-
only uses are fine).

**Behavioral risk: HIGH — WOULD BREAK FUNCTIONALITY.** The symbols
are used at runtime:
- `apply_belief_transition` — called at line 550 (runtime)
- `DefeaterOutcome.INCONCLUSIVE/NOT_TESTABLE` — checked at line 546 (runtime)
- `BeliefTransition` — constructed at line 573 (runtime)

Moving these to TYPE_CHECKING would cause NameError at runtime when
`apply_defeater_result()` is called. The function would not work.

**Migration complexity: LOW (if it worked)**, but the option is NOT
APPLICABLE because the symbols are genuinely runtime, not type-only.

**P2-legal: NO** (not applicable; the symbols are runtime).

**Would it pre-empt P5 work: NO** (but it would break functionality).

**Verdict:** NOT APPLICABLE. The symbols are runtime, not type-only.

---

## Option C — Dependency inversion

**Description:** Define a brain-owned protocol/port (e.g.,
`BeliefTransitionPolicy` with a `apply_belief_transition(prior_state,
prior_confidence, outcome) -> tuple[float, str]` method). Arena
implements the protocol. Brain depends only on the protocol, not on
the Arena implementation.

**Affected files:**
- New: `src/orchestrator/brain/belief_transition_policy.py` (protocol definition)
- New: `src/arena/belief_transition_policy_impl.py` (Arena implementation)
- `src/orchestrator/brain/hypothesis.py` (depends on protocol, not Arena)
- Arena: register the implementation at composition root
- The composition root would inject the implementation into
  `HypothesisManager.__init__` or a module-level factory

**Architectural direction:** Brain defines the policy CONTRACT. Arena
provides the IMPLEMENTATION. The dependency direction is brain →
protocol (in brain) and arena → brain (to register the impl). This is
the textbook dependency inversion pattern (DIP).

**Behavioral risk: MEDIUM.** The interface is simple (one method
with 3 args, returns a tuple). The behavior is entirely in the
implementation. If the implementation is injected correctly, the
behavior is preserved. The composition root must be modified to
register the Arena implementation.

**Migration complexity: MEDIUM.** Requires:
1. Define the protocol (small, ~10 lines)
2. Move the V2 policy implementation to an Arena module that
   implements the protocol (~100 lines, including the transition tables)
3. Modify `HypothesisManager.__init__` to accept a policy parameter
   (or use a module-level factory)
4. Wire the composition root to inject the Arena implementation
5. Update hypothesis.py to use the injected policy

**P2-legal: MARGINAL.** Dependency inversion is a standard pattern and
is not inherently P5 work. HOWEVER, the V2 policy content (the
transition tables) IS P5 work. The protocol can be defined in P2,
but the implementation should be a V2-compliant implementation, which
requires P5 contract work.

If the P2 protocol is defined with a clear interface and a documented
contract that the Arena implementation must satisfy, and the Arena
implementation is the existing V2 policy (preserved as-is), then this
is P2-legal. The P5 work is the CONTRADICTION PREDICATE (v4.1 AM-2),
not the V2 policy per se.

**Would it pre-empt P5 work: PARTIALLY.** Defining the protocol in P2
is fine. The V2 policy implementation is already in Arena. The P5
contradiction predicate (v4.1 AM-2) is a different artifact — it
specifies when a Finding is contradicted by a new Observation. The
`apply_belief_transition` function is the BELIEF-UPDATE POLICY (what
happens to a hypothesis's confidence and state when a defeater result
arrives), which is related but distinct from the contradiction
predicate.

**Verdict:** MARGINALLY VIABLE in P2. Requires careful scoping to
avoid pre-empting P5. The protocol can be defined, but the
implementation contract must defer the V2 policy details to P5.

---

## Summary

| Option | P2-legal? | Behavioral risk | Pre-empts P5? | Verdict |
|---|---|---|---|---|
| A — Re-home | NO | HIGH (silent semantic drift) | YES | NOT RECOMMENDED in P2 |
| B — TYPE_CHECKING | NO (not applicable) | HIGH (would break functionality) | NO | NOT APPLICABLE |
| C — Dependency inversion | MARGINAL | MEDIUM | PARTIALLY | VIABLE with careful scoping |

## Recommended disposition

**Classify as P5-SCALE.** The brain → arena edge at `hypothesis.py:536`
requires reproducing the D-5 V2 falsification policy, which is P5
semantic work. None of the three permitted mechanisms is cleanly
P2-legal without either:
- Silent semantic drift (Option A)
- Breaking functionality (Option B)
- Pre-empting P5 contract work (Option C without careful scoping)

**Recommended action:** HALT and defer to P5.1+ when the P5
contradiction predicate contract (v4.1 AM-2) and P5 task matrix
(v4.1 AM-14) exist. At that point, either Option A (with the
authoritative P5 policy tables) or Option C (with the P5 protocol) can
be implemented under the proper P5 contracts.

**No source edits performed.** The lazy runtime import at
`hypothesis.py:536` remains, with the documented HALT/ESCALATE
comment. The guardrail test (`test_no_arena_runtime_import_from_orchestrator_brain`)
correctly identifies this as a known P5-scale violation via
`pytest.skip`.
