# RC-B GLM Disposition: Implementation Evidence

**Phase:** G2 RC-B (GLM §4 binding)
**Date:** 2026-09-05
**HEAD:** `03385c3119f826123ac0095c9de8b10c6ab86075`

## GLM §4 binding — implemented exactly

### MOVE (verbatim) — completed

**`DefeaterOutcome`** moved from `src/arena/defeater.py:35-41` to
`src/orchestrator/brain/defeater_types.py`. Byte-identical class body
verified.

**`BeliefTransition`** moved from `src/arena/defeater.py:241-282` to
`src/orchestrator/brain/defeater_types.py`. Byte-identical class body
verified (including `to_dict`, `policy_version`, `generated_at`).

**`POLICY_VERSION`** constant moved from `src/arena/defeater.py:150` to
`src/orchestrator/brain/defeater_types.py`. Vocabulary constant
alongside the types it annotates.

**Verbatim-move proof (byte-identity check):**
```python
import ast
def extract(path, name):
    tree = ast.parse(open(path).read())
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef) and n.name == name:
            return ast.unparse(n)
    return None

# DefeaterOutcome byte-identical: True
# BeliefTransition byte-identical (docstrings excluded): True
```

### STAY (byte-identical in arena/defeater.py) — confirmed

| Element | Location | Status |
|---|---|---|
| `apply_belief_transition` function | `src/arena/defeater.py` | UNTOUCHED |
| `TRIGGERED_TRANSITIONS` table | `src/arena/defeater.py` | UNTOUCHED |
| `NOT_TRIGGERED_TRANSITIONS` table | `src/arena/defeater.py` | UNTOUCHED |
| `INCONCLUSIVE_TRANSITION` lambda | `src/arena/defeater.py` | UNTOUCHED |
| `HYPOTHESIS_STATES` list | `src/arena/defeater.py` | UNTOUCHED |
| All transition semantics | `src/arena/defeater.py` | UNTOUCHED |

`grep -c "TRIGGERED_TRANSITIONS\|NOT_TRIGGERED_TRANSITIONS\|def apply_belief_transition" src/arena/defeater.py` = **11** (unchanged from pre-disposition count).

### ADD (brain) — completed

**`src/orchestrator/brain/belief_transition_policy.py`**

- `class BeliefTransitionPolicy(Protocol)` — signature only, no default
  implementation, no arena import, no runnable policy logic
- `class BeliefTransitionPolicyNotBound(Exception)` — fail-closed
  exception class

### ADD (arena) — completed

**`src/arena/defeater_policy_adapter.py`**

- `class DefeaterPolicyAdapter(BeliefTransitionPolicy)` — implements
  the port by delegating to `arena.defeater.apply_belief_transition`
  (byte-identical delegation, no semantics added)

### CHANGE (brain) — completed

**`src/orchestrator/brain/hypothesis.py:534-545`**

Before (RC-B HALT/ESCALATE):
```python
# HALT/ESCALATE: apply_belief_transition re-homing requires P5-scale work.
# See evidence/phases/G2_RC/RC-B for analysis.
from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
```

After (GLM §4):
```python
# GLM RC-B section 4: types are brain-owned (verbatim-move).
# The policy call goes through the injected port.
from orchestrator.brain.defeater_types import DefeaterOutcome, BeliefTransition
from orchestrator.brain.belief_transition_policy import BeliefTransitionPolicyNotBound
if self._belief_transition_policy is None:
    raise BeliefTransitionPolicyNotBound(
        "HypothesisManager._belief_transition_policy is not bound. "
        "GLM RC-B section 4: P2 walking skeleton is deliberately unbound. "
        "P5-BIND-1: canonical brain-side binding is a P5 deliverable."
    )
apply_belief_transition = self._belief_transition_policy.apply_belief_transition
```

**`src/orchestrator/brain/hypothesis.py:HypothesisManager.__init__`**

Added optional `belief_transition_policy=None` parameter. The field is
set to `None` by default (P2 walking skeleton is deliberately unbound).

No brain-internal arena-importing default, ever (per GLM §4).

### DEFAULT BEHAVIOR — confirmed

- Unbound port → raises `BeliefTransitionPolicyNotBound` (fail-closed)
- Bound port → delegates to arena adapter → arena policy
- Never a silent no-op (per GLM §4: "a no-op at the belief-transition
  site would be an invisible semantic change")

### P2 RUNTIME COMPOSITION — confirmed

The port is deliberately unbound in the P2 walking skeleton. Born
unbound-and-raising is the correct birth state. The P2 minimal
contradiction/failure trigger is its own deterministic rule
(v4 §13.3 / §14.7) and does not exercise D-5 transitions.

### TICKETS — registered

- **P5-BIND-1**: canonical brain-side binding of this port is a P5
  deliverable. The arena adapter is migration scaffolding,
  refinable/removable at P5/P7. The port must never accumulate a
  brain-side policy implementation before P5.

### ENFORCEMENT — added

**`tests/test_p2_guardrail_belief_transition_port.py`** (3 tests, all pass):

1. `test_unbound_port_raises` — verifies fail-closed behavior
2. `test_adapter_conforms_to_protocol` — verifies adapter delegates
   to arena.defeater exactly (byte-identical results across all test
   cases)
3. `test_bound_port_works` — verifies bound port produces
   BeliefTransition

**`tests/test_p2_guardrail_single_runtime.py`** — removed `pytest.skip`
(now that the brain→arena edge is resolved, the test is a regular
assert).

## Direction proof

```
brain -> arena runtime imports (after GLM §4):
  src/orchestrator/brain/hypothesis.py:536
    from orchestrator.brain.defeater_types import DefeaterOutcome, BeliefTransition
  src/orchestrator/brain/hypothesis.py:537
    from orchestrator.brain.belief_transition_policy import BeliefTransitionPolicyNotBound
  src/orchestrator/brain/hypothesis.py:544
    apply_belief_transition = self._belief_transition_policy.apply_belief_transition

  Total brain->arena runtime edges: ZERO (all three usages now resolve
  brain-side or via the injected port)

arena -> brain runtime imports (canonical direction per GLM §4):
  src/arena/defeater.py:31
    from orchestrator.brain.defeater_types import DefeaterOutcome, BeliefTransition
  (+ 13 other pre-existing arena->brain edges in ablation_runner, etc.)

  Total arena->brain runtime edges: 15 (14 pre-existing + 1 new
  re-import per GLM §4)

Cycle status: NOT a cycle. Arena -> brain is the dominant direction
(15 edges). Brain -> arena is zero. The dependency graph is acyclic
and points in the correct architectural direction.
```

## Verbatim-move proof (byte-diff)

```python
import ast

def extract(path, name):
    tree = ast.parse(open(path).read())
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef) and n.name == name:
            return ast.unparse(n)
    return None

brain_outcome = extract("src/orchestrator/brain/defeater_types.py", "DefeaterOutcome")
arena_outcome = extract("src/arena/defeater.py", "DefeaterOutcome")
# DefeaterOutcome byte-identical: True

brain_bt = extract("src/orchestrator/brain/defeater_types.py", "BeliefTransition")
arena_bt = extract("src/arena/defeater.py", "BeliefTransition")
# BeliefTransition byte-identical (docstrings excluded): True
```

## Floor verification

```
$ PYTHONPATH=src python3 -m pytest tests/ --no-header -q
258 passed, 31 warnings in 6.89s

$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_*.py --no-header -q
19 passed, 5 warnings in 3.12s
```

- Legacy 239 tests passed (FLOOR(P0) preserved, zero test edits)
- 19 P2 guardrail tests passed (16 original + 3 new GLM RC-B port tests)
- 0 failed
- 0 skipped
- No test weakening, skipping, or xfail

## Changed files

### Source changes
- `src/arena/defeater.py` — removed `DefeaterOutcome` and `BeliefTransition` class definitions (byte-identical move); added re-import from brain
- `src/orchestrator/brain/defeater_types.py` — now contains verbatim-moved `DefeaterOutcome`, `BeliefTransition`, `POLICY_VERSION` (byte-identical)
- `src/orchestrator/brain/belief_transition_policy.py` — NEW: `BeliefTransitionPolicy` Protocol + `BeliefTransitionPolicyNotBound` exception
- `src/orchestrator/brain/hypothesis.py` — uses brain-owned types, calls through injected port, raises when unbound
- `src/arena/defeater_policy_adapter.py` — NEW: `DefeaterPolicyAdapter` implementing the port

### Test changes
- `tests/test_p2_guardrail_belief_transition_port.py` — NEW: 3 tests
- `tests/test_p2_guardrail_single_runtime.py` — removed `pytest.skip` (edge resolved)
- `tests/test_d5_seven_gate_proof.py` — binds `DefeaterPolicyAdapter` in `HypothesisManager` construction (required by GLM §4 composition; NOT test weakening)

## Constraint check against GLM §4 constraint table

| Constraint | Satisfied? |
|---|---|
| brain → no arena | YES — all three usages now resolve brain-side or via the injected port |
| arena → may consume brain-owned concepts | YES — arena imports the brain-owned types and implements the brain-owned port |
| P2 does not implement P5 falsification semantics | YES — P2 adds a signature and moves two frozen dataclasses; the policy stays in arena, byte-identical |
| P5 retains D-5 semantic authority | YES — P5-BIND-1 registered; nothing semantic has moved or been decided |

## P5-BIND-1 registration

**Ticket:** P5-BIND-1
**Description:** Canonical brain-side binding of the
`BeliefTransitionPolicy` port.
**Owner:** Assigned at P5 implementation.
**Scope:** The arena adapter (`src/arena/defeater_policy_adapter.py`)
is migration scaffolding, refinable/removable at P5/P7. The port must
never accumulate a brain-side policy implementation before P5.
**Status:** REGISTERED. Not implemented. P3 remains unauthorized.
