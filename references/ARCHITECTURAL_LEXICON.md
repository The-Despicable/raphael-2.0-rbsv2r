# Architectural Lexicon — Salvage from `src/raphael/`

**Status:** in progress. Grounded by direct source reading; every entry carries `path:line`.
**Purpose:** capture designs worth reimplementing from the welded-off parallel architecture
`src/raphael/` (86 files, 12,662 lines) before building the brain roadmap on top of them.

> **Scope.** Control plane only — state models, contracts, candidate selection, negative
> caching, persistence, event plumbing. Offensive payload content is deliberately excluded;
> where a registry declares such things we record the *schema* and counts, never the content.

---

## 0. Why this document exists

`src/raphael/` was welded off from the canonical runtime and the weld is **test-enforced**:

- `src/raphael/main.py:387` — legacy organism loop deleted
- `tests/test_am4_weld_gates.py:84` — `assert "RaphaelOrganism(config)" not in text`
- `tests/test_p21_walking_skeleton.py:106` — `assert "RaphaelOrganism" not in source`

The weld covers **`RaphaelOrganism` only**. The subsystems it called were never welded; they
were orphaned. Four of them have **zero behavioural tests** — the five test files that mention
`raphael.` are the guardrail locks above, not coverage:

| Module | Test files exercising behaviour |
|---|---|
| `src/raphael/cortex/planner.py` | 0 |
| `src/raphael/hippocampus/episode_store.py` | 0 |
| `src/raphael/cerebellum/error_diagnoser.py` | 0 |
| `src/raphael/cerebellum/technique_validator.py` | 0 |

The package is nonetheless live in packaging terms: `pyproject.toml:31` includes `raphael*`,
and `REVIEWER_GUIDE.md` / `RAPHAEL_STATE.md` never mention it at all.

**The risk this document manages:** a builder rediscovers this tree mid-build and writes a
third planner. Every salvage below is annotated with *what it replaces* so that does not happen.

---

## 1. The finding that constrains everything else

**`src/raphael/` has no planner.** Verified, not inferred:

- No `solve` / `reachable` / `achievable` / `backward` / `chain_plan` / `can_reach` / `find_path`
  function anywhere in `src/raphael/`.
- No BFS / DFS / topological / backtracking over techniques. The only `visited` set is
  `src/raphael/cognitive/network_graph.py:93`, unrelated to planning.
- No field named `requires` exists. The fields are `prerequisites`, `blockers`,
  `required_capabilities` (`src/raphael/techniques/__init__.py:15,16,23`).

What exists instead is a **flat registry plus a greedy candidate filter**.
`select_next_step` (`src/raphael/cortex/planner.py:94`) iterates every registered technique and
keeps those passing four independent gates:

```python
prereqs_met    = all(p in available_affordances for p in technique.prerequisites)   # :108-110
blockers_clear = not any(b in available_constraints or b in available_affordances
                         for b in technique.blockers)                               # :112-115
not_dead       = not target.is_technique_dead(...)                                 # :118-121
not_exhausted  = not self._is_exhausted(technique.name, set())                     # :123
```

It answers *"what can I do right now that I have not already done uselessly."*
It does **not** answer *"what sequence reaches the goal."* There is no goal representation,
no sequence construction, and no backward chaining.

**Consequence for the roadmap:** stages 0–1 are substantially salvageable; **stage 2 (goal-directed
planning) is genuine new design and must be built against the canonical runtime.**

---

## 2. SALVAGE — state substrate

### 2.1 `TargetModel` — affordance/constraint vector

`src/raphael/models/target_model.py:10-11`

```python
constraints: set[str] = field(default_factory=set)
affordances: set[str] = field(default_factory=set)
```

With `has_affordance` / `has_constraint` (`:14`, `:17`), a `to_dict` / `from_dict` round-trip
(`:22`, `:30`), and a delta type carrying `new_constraints` / `new_affordances` (`:40-41`) plus
`is_empty()` (`:47`).

**Replaces:** my claim that the canonical world model has no usable state vector.
`orchestrator/brain/world.py` has entities and relationships but no such substrate.

**Reimplements:** my `Observation` contract's `validity_interval` and provenance channels —
neither exists in `TargetModel`, and the canonical tree needs both.

### 2.2 Negative cache with resurrection — the best design in the tree

`src/raphael/models/target_model.py:129-148`, docstring *"Negative cache with resurrection"*

```python
def is_technique_dead(self, technique_name, current_cycle, technique_prereqs, technique_blockers):
    if technique_name not in self.failed_techniques: return False
    record = self.failed_techniques[technique_name]
    if record.is_permanent: return True
    for prereq in technique_prereqs:
        if prereq in state.affordances: return False      # resurrected: new prereq met
    for blocker in technique_blockers:
        if blocker not in state.constraints: return False  # blocker removed
    return True
```

This is the correct answer to the question I spent Round 4 and Round 5 specifying: a failure
record is **context-bound and revalidates when the relevant state changes**, rather than a
permanent blacklist. My `FailureRecord` + `ContextSignature` in `contracts/identity.py` is a more
elaborate re-derivation of something already written more simply.

**Replaces:** the design intent behind `contracts/identity.py`. **Salvage the idea, not the class.**

### 2.3 Exhaustion / `produced_new_info` — PARTIALLY LIVE

`src/raphael/cortex/planner.py:79-87` increments a counter when a technique produced no new
information and resets it when it did. This is the `NO_BELIEF_UPDATE` distinction, already
written. **The counter path is live:** `_is_exhausted` reads the same `_exhaustion_count` dict
at `:70-72` against `_exhaustion_threshold = 2`.

**Two verified defects degrade it:**

1. **The affordance-repetition check is dead.** `_is_exhausted` has a second branch (`:74-77`)
   meant to detect "producing the exact same affordances repeatedly". Its sole call site
   passes an **empty set** — `not self._is_exhausted(technique.name, set())` at `:123`. The
   branch requires `new_affordances` to be truthy, so it can never fire. Repetition detection
   does not exist; only count-based exhaustion does.
2. **A dead duplicate counter.** `self._exhaustion_counts` (plural) is declared at `:50` and
   never touched again. The live one is `_exhaustion_count` (singular) at `:53`.

**Verdict:** salvage the counter concept; discard the repetition branch. This is *weaker* than
what the v1.1 `StageReport` vocabulary already expresses, so the canonical contracts stay.

### 2.4 Ranking weights are a no-op — DO NOT SALVAGE

`planner.py:44` declares `ranking_weights = {"recon": 1.0, "exploit": 1.0}`. It is read at
`:170` as a multiplier, but **both values are 1.0**, so the weight vector has no effect. The
effective ranking is `expected_value(name, category)` alone. This is the same defect class as
`orchestrator/brain/action.py:921`'s literal constants — a scoring apparatus that looks
tunable and is not. Rebuild ranking as a declared, unit-tested function.

---

## 3. DO NOT SALVAGE — the registry and its effects

`src/raphael/techniques/__init__.py:12-28` defines a 16-field `Technique` dataclass. The
**declaration schema is worth keeping**. The **effect semantics are unsound**:

**Defect 1 — the effect relation is unconditional.** `src/raphael/executor/executor.py:114-115`
adds `provides_affordances` to the target model after every run **regardless of outcome**. The
affordance set therefore grows on a *failed* execution, unblocking downstream techniques that
declare those affordances as prerequisites. This is the inverse of a sound effect relation and
would silently corrupt any plan built on it.

**Defect 2 — two divergent effect fields.** `provides` and `provides_affordances` express the
same idea and **disagree in 5 of 24 declarations** (`:50`, `:69`, `:170`, `:331`, `:432`).
Worse, the three consumers read different ones: `planner.py:135` filters on `provides`,
`executor.py:114-115` mutates with `provides_affordances`, `cognitive/planner.py:266` estimates
with `provides_affordances`. Relevance-filtering and state-mutation read different sets.

**Defect 3 — three divergent filter implementations.** `cortex/planner.py:108-115`,
`cognitive/planner.py:219-221`, and a hard-coded LLM/heuristic fallback at
`cortex/hypothesizer.py:40-110` all evaluate the same fields with different semantics.

**Defect 4 — prefix matching is undeclared.** Every consumer honours `p + ":"` or `p + "_"`
prefixes on affordance strings (`cortex/planner.py:58-66`) rather than exact membership, and the
registry never declares which convention a given token uses.

**Defect 5 — declared-but-dead and silent-fallback fields.** `stealth_score` is read by no code.
`parser` resolves via `PARSER_REGISTRY.get` with silent fallback to `parse_raw`
(`executor.py:110`). A malformed argument template raises an uncaught `KeyError`
(`executor.py:100`) with no pre-flight check.

> **Rule for the rebuild:** take the *field schema*. Do not take the effect semantics. Effects
> must be asserted by a verifier against evidence — never granted because a run completed.

---

## 4. Runtime plumbing — eventbus is the largest component and unreachable

`src/raphael/eventbus/core.py` is **827 lines and the most complete component in the legacy
tree**: a Redis Streams bus with per-event-type streams (`raphael:events:{event_type}` @296),
consumer groups with XREADGROUP, XPENDING_RANGE/XCLAIM stale-message reclaim (:444-466),
exponential backoff (:532-535), a dead-letter stream, 11 metrics counters, and a
contextvars-based trace/span propagation layer.

**It is reachable from nothing in production.** The canonical runtime uses a linear
`STAGE_ORDER`, not pub/sub.

### 4.1 Authorization: trust-the-planner

Across the whole 4,175-line runtime slice, `enforce_broker_mediation()` (the fail-closed
`WeldNotAuthorized` check) is called from exactly **two** places, both in files that are
themselves dead or entry-point-only: `executor/kali_bridge.py:53` and `verifier/__main__.py:36`.

Everything else — eventbus, circulatory, blackboard, `executor.py`, `verifier/core.py`,
`integration/` — performs **zero** authorization, scope, or budget checks. `Executor.execute`
trusts the planner's technique name, checks only a pause flag and registry membership, and the
only mediation happens one layer down inside `KaliBridge.run`.

**Consequence: none of this can be lifted into a broker-mediated runtime without reworking
every dispatch path.** The canonical `CapabilityBroker` seam must stay authoritative.

### 4.2 Event bus defects — the declared contract exceeds the behaviour

| Claim | Reality |
|---|---|
| `subscribe()` registers a handler | Local registration only; it does **not** touch Redis, create a group, or start a consumer. `Blackboard.subscribe` (`blackboard/contracts.py:116`) only ever calls this — so it wires a handler that is **inert** unless someone separately calls `start_consumer` (:364). An undeclared two-phase contract. |
| `EventPriority` LOW/NORMAL/HIGH/CRITICAL | **Stored but never used for scheduling** (:66, :302-307). XADD is FIFO. The enum implies prioritization that does not exist — the same defect class as `ranking_weights`. |
| At-least-once delivery | Correct, but the retry path **ACKs the original then re-publishes a NEW event** (:537-550). A handler that partially applied its effect and then raised gets a **second full application**. No idempotency key is propagated. |
| Every event is handled | With no subscriber, the event is **ACKed and discarded** (:478-482) — a silent black hole. |
| Handlers are independent | They run **sequentially in a for-loop** (:491-495). The first raising handler skips all later handlers for that event. |

**Salvage verdict:** the *trace propagation* and *metrics* designs are worth reimplementing.
The delivery semantics are not — a pub/sub bus with double-application on retry and silent
black-holing is worse than the canonical linear stage order, which is at least deterministic.


---

## 5. State substrate — two conflicting schemas, one live

`src/raphael/models/` (3 files, 321 LOC) and `src/raphael/cognitive/models.py` define the
**same four names incompatibly**:

| Name | `models/` (LIVE) | `cognitive/models.py` (ORPHANED) |
|---|---|---|
| `TargetModel` | `target_id`, `domains: dict[str,DomainState]`, `failed_techniques` (`target_model.py:74-84`) | `id`, `identifier`, `type`, `affordances: Dict[str,Affordance]`, `constraints`, `unknowns`, `risk_score` (`cognitive/models.py:144-156`) |
| `Capability` | 6 fields, `status: str` (`capability_model.py:8-14`) | 14 fields, `state: CapabilityState`, `reliability`, `success/failure_count` (`cognitive/models.py:72-85`) |

`models/` is live — `main.py:265`, `executor.py:130,139` and `planner.py:240` all use it, and
the persisted snapshot `data/hippocampus_episodes.json` carries its `"domains"` key.
`cognitive/models.py` has no live consumer; only `integration/harness.py:32` imports the package.
`cognitive/` is 14 files / 2,659 LOC with **zero behavioural tests**.

**Any salvage must pick one schema.** The `cognitive/` records are richer (`Affordance`,
`Constraint`, `Unknown` as objects rather than bare strings) and are the better model — but
porting them means choosing deliberately, not renaming over a live path.

### 5.1 `DomainState` — three sets, not two

`target_model.py:8-34`: `constraints`, `affordances`, **and `unknowns`**. The third set is the
explicit-unknown primitive the canonical world model lacks entirely. `to_dict`/`from_dict`
round-trip is **faithful** — verified `DomainState.from_dict(ds.to_dict()) == ds` → `True`,
including duplicate collapse. Only set *ordering* is nondeterministic, which is irrelevant.

**SALVAGE.** This is the state substrate the canonical runtime needs.

### 5.2 `TargetModel.absorb()` — the best algorithm in the legacy tree

`target_model.py:86-121`. Encoded as **set algebra rather than asserts**, which is why it is
correct despite having no tests:

```python
new_constraints   = delta.new_constraints - domain.constraints   # idempotent re-add rejected
resolved_unknowns = delta.resolved_unknowns & domain.unknowns    # resolving can never ADD an unknown
changed = <set only on genuine change>
```

The `&` on `resolved_unknowns` is deliberate and correct: a resolve event can only ever remove
an unknown. An implementation using `|` or assignment would let a stale resolve *create* an
unknown. This is the belief-update function the canonical tree does not have.

**SALVAGE VERBATIM AS THE MODEL**, with the truncation defect below fixed.

### 5.3 Defects in the state substrate

- **`ConstraintDelta.to_dict()` is LOSSY** — `evidence` is truncated to 500 chars (`:58`).
  Verified: 900-char evidence serialises to 500. Raw tool output is the primary evidence
  carrier; silently truncating it is the same defect class as `ActionReceipt.result: str`.
- **`ConstraintDelta` has NO `from_dict`** (verified `hasattr(...) == False`). Deltas are
  write-only, so they cannot be persisted or replayed.
- **`FailureRecord.reason_class` is comment-only** (`:66-70`). The comment declares
  `"permission"|"timeout"|"unavailable"|"server_error"` but there is **no enum and no
  validation** — the failure taxonomy specified in Round 5 exists here as a comment.
- `data/` contains **zero Python modules** — only `hippocampus_episodes.json` and a SQLite
  blackboard. Nothing imports `raphael.data`.

---

## 6. Orchestration — the legacy loop is structurally real but cannot execute

### 6.1 The organism loop would fail on every technique

`RaphaelOrganism` is structurally complete, but its only execution path is severed:
`Executor.execute()` → `KaliBridge.run()` raises

```
RuntimeError: Executor._subprocess_fallback() is removed in WELD-SUB14
```

at `src/raphael/executor/kali_bridge.py:82-86`. **Every technique dispatched from the loop
fails.** The planner, affordance filter and exhaustion logic above it are therefore never
exercised end to end. This is why "salvage the planner" must mean "reimplement the ideas",
not "call the code": the code has never run to completion.

### 6.2 The pause/thermoregulator circuit is unreachable

`Thermoregulator._current_risk` is initialised to `0.0` and only ever *decayed*
(`src/raphael/main.py:96,99`). **No writer raises it.** Verified: after 5 ticks the risk stays
`0.0`, `inhibit()` never fires, and since `SpinalReflex.inhibit` is the sole caller of
`Executor.pause`, the `paused` guard at `main.py:205` can never trigger.

A back-pressure mechanism with no producer is the same defect class as `EventPriority` and
`ranking_weights`: the knob exists, the docstring implies the behaviour, the behaviour is absent.

### 6.3 The weld covers a branch, not the module

`Thermoregulator` and `ParallelRecon` remain defined and imported. The CLI help text still
advertises `RAPHAEL_MAX_CYCLES`, which now controls nothing. The enforcing test is a
**3-substring grep over the file text** (`tests/test_am4_weld_gates.py`) — it proves a name is
absent, not that behaviour is unreachable.

### 6.4 The canonical path runs exactly one iteration — confirmed by execution

`main.py:406` calls `rt.run_episode(mission, require_scope=True)` with **no `max_iterations`**,
and `_canonical_mission` sets no `halt` key, so `run_episode` falls back to its documented
`max_iterations=1` default (`loop.py:159`). Running it with the missing module stubbed
produces:

```
Runtime trace: 10 stages
Termination: G3-EN-5 organ-wired walking skeleton: one iteration complete
```

This confirms the blueprint's central claim by execution rather than by reading. **Additionally:
`action_cap` is parsed at `loop.py:160-161` and then never referenced in the loop body** — a
third dead configuration value alongside `ranking_weights` and `EventPriority`.


---

## 7. Open — awaiting remaining slices

- `cortex/` hypothesizer, model_refiner
- `cerebellum/` error_diagnoser, technique_validator
- `hippocampus/` episode_store persistence + similarity replay
- `main.py` canonical path + `_canonical_mission` config
- Other 14 top-level packages
---

## 8. Cross-check against OpenCode (independent analysis)

OpenCode — a separate agent session — was given these findings and asked to **verify them
independently rather than accept them**. It ran its own verification passes.

**Independently confirmed:** the three inert edges; one-iteration termination; the `KaliBridge`
`RuntimeError` severance; the weld being test-enforced; the unconditional affordance grant at
`executor.py:114-115`; and the 121/122/30 baseline.

**Agreement on the load-bearing risk, reached from a different direction.** Its risk ranking for
an end product: (1) *no goal-directed planner anywhere — the product cannot decide sequences;
everything else is plumbing around an empty core*, (2) execution plane broken at both ends. This
document reached the empty-core conclusion from the planner code; OpenCode reached it from the
import graph.

**One framing disagreement — salvage vs rewrite.** This document's position: *reimplement the
ideas, do not port the code*, because the legacy execution path has never completed a technique
and the effect semantics are unsound. OpenCode's position: the decision is about **substrate**,
and substrate choice should minimise time-to-planner, so salvage wins *if* the seams do not
block. Both reduce to the same build order; they differ on whether the legacy bodies are worth
reading as reference. **Reconciliation:** read them as reference, write fresh, and treat
`target_model.py` and `episode_store.py` as the thing actually being ported.

**Where OpenCode is wrong.** It reported `src/agent/` as TypeScript-only. Verified: **17 Python
files, 0 TypeScript**. `src/cli` is the TypeScript package (2,413 `.ts`, 0 `.py`).

**A finding its hunch produced, which I had missed.** It noticed `arena/` keeps tests *inside*
`src/`. Verified and quantified: `pyproject.toml:37` sets `testpaths = ["tests"]`, so bare
`pytest` collects **only** `tests/`. **Seven test files under `src/**/tests/` are never
collected** — `test_baseline_equivalence`, `test_evaluator_robustness`,
`test_generator_invariant`, `test_runconclusion`, `test_safety_regression`, `test_server`,
`test_state_isolation`.

That is a **seventh instance of the declared-vs-implemented class in §3**: a suite that exists,
is named as though it runs, and does not. It is also evidence about the 621 figure — whatever
that number counted, it cannot have included these seven.

**Unresolved.** OpenCode's import-cycle claim (7 short cycles; `brain` importing
`cicd`/`cloud_abuse`/`container_escape`/`ml_attack` rather than registering into it) came from a
regex probe it itself flagged as possibly over-matching. It declined to defend the claim without
reading the real import lines. Still open.
