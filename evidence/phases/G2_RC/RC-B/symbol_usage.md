# RC-B: Symbol Usage Analysis — `apply_belief_transition`, `DefeaterOutcome`, `BeliefTransition`

## Symbols imported by the offending edge

`src/orchestrator/brain/hypothesis.py:536`:
```python
from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition
```

## Per-symbol usage in `hypothesis.py`

### `apply_belief_transition` (function)

| Line | Context | Type |
|---|---|---|
| 536 | `from arena.defeater import apply_belief_transition, DefeaterOutcome, BeliefTransition` | Import |
| 550 | `post_confidence, post_state_str = apply_belief_transition(prior_state=prior_state, prior_confidence=prior_confidence, outcome=defeater_result.outcome)` | **Runtime call** |

**Call signature:**
```python
apply_belief_transition(
    prior_state: str,        # "POSTULATED" | "DOUBTFUL" | "ABANDONED" (uppercased)
    prior_confidence: float, # [0.0, 1.0]
    outcome: DefeaterOutcome, # Enum: TRIGGERED | NOT_TRIGGERED | INCONCLUSIVE | NOT_TESTABLE
) -> tuple[float, str]       # (posterior_confidence, posterior_state_string)
```

**Call count:** 1 runtime call site.

### `DefeaterOutcome` (Enum)

| Line | Context | Type |
|---|---|---|
| 536 | `from arena.defeater import ... DefeaterOutcome ...` | Import |
| 546 | `if defeater_result.outcome in (DefeaterOutcome.INCONCLUSIVE, DefeaterOutcome.NOT_TESTABLE):` | **Runtime check** |

**Values used:**
- `DefeaterOutcome.INCONCLUSIVE` (line 546)
- `DefeaterOutcome.NOT_TESTABLE` (line 546)

**Call count:** 1 runtime check site, 2 enum values referenced.

### `BeliefTransition` (frozen dataclass)

| Line | Context | Type |
|---|---|---|
| 516 | `) -> Optional["BeliefTransition"]:` | Type annotation |
| 523 | `Returns a BeliefTransition artifact proving the causal link from` | Docstring |
| 531 | `BeliefTransition if the hypothesis was found and outcome` | Docstring |
| 536 | `from arena.defeater import ... BeliefTransition` | Import |
| 573 | `transition = BeliefTransition(hypothesis_id=hypothesis_id, defeater_result_id=defeater_result.result_id, outcome=defeater_result.outcome, prior_confidence=prior_confidence, posterior_confidence=post_confidence, prior_state=prior_state, posterior_state=post_state_str,)` | **Runtime construction** |

**Fields used in construction:**
- `hypothesis_id`
- `defeater_result_id`
- `outcome`
- `prior_confidence`
- `posterior_confidence`
- `prior_state`
- `posterior_state`

**Call count:** 1 type annotation, 2 docstring mentions, 1 runtime construction.

## Summary

| Symbol | Runtime uses | Type-only uses | Docstring uses | Total |
|---|---|---|---|---|
| `apply_belief_transition` | 1 (line 550) | 0 | 0 | 1 |
| `DefeaterOutcome` | 1 (line 546) | 0 | 0 | 1 |
| `BeliefTransition` | 1 (line 573) | 1 (line 516) | 2 | 4 |

All three symbols are used in RUNTIME contexts (not purely type-only).
The import cannot be moved to `TYPE_CHECKING` without breaking
functionality.

## What would need to be re-homed

To fully sever the brain → arena edge at `hypothesis.py:536`, the
following would need to be moved to brain-owned modules:

1. **`apply_belief_transition` function** (~60 lines) + its dependencies:
   - `TRIGGERED_TRANSITIONS` table (4 entries with lambdas)
   - `NOT_TRIGGERED_TRANSITIONS` table (4 entries with lambdas)
   - `INCONCLUSIVE_TRANSITION` lambda
   - `POLICY_VERSION` string constant
   - `HYPOTHESIS_STATES` list

2. **`DefeaterOutcome` Enum** (5 lines)

3. **`BeliefTransition` dataclass** (frozen, ~30 lines with to_dict)

The function + tables are the D-5 V2 falsification policy. The tables
encode the semantic policy. Moving them is P5 work per v4 §16 and
v4.1 AM-2/AM-14.

## Commands used

```bash
# Find the import and all usages
grep -n "apply_belief_transition\|DefeaterOutcome\|BeliefTransition" \
    src/orchestrator/brain/hypothesis.py

# Check the original definition and its dependencies
grep -n "def apply_belief_transition" src/arena/defeater.py
grep -n "TRIGGERED_TRANSITIONS\|NOT_TRIGGERED_TRANSITIONS\|POLICY_VERSION\|HYPOTHESIS_STATES" \
    src/arena/defeater.py

# Check for the same dependency in action.py
grep -n "apply_belief_transition\|BeliefTransition\|DefeaterOutcome" \
    src/orchestrator/brain/action.py
```
