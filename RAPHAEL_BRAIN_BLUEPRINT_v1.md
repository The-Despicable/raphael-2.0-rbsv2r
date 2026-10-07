# RAPHAEL BRAIN BLUEPRINT v1

Synthesis of a three-way architecture session (repo owner + two external models),
reconciled against the live source tree at branch `offensive-restore`.

Scope note: this document is control-plane architecture only — perception,
evidence, identity, outcomes, goals, plans. It makes no assessment of offensive
capability and proposes restoring none. Every claim about existing code carries a
`path:line` citation verifiable by opening that file at that line.

---

## 1. Verdict

Raphael is not primarily missing offensive capability. It is missing a **trustworthy
closed-loop decision substrate** — a substrate whose feedback edges actually reach
the belief state, so that what the agent observes changes what it plans.

The loop that substrate would sit on **already exists and is already declared
canonical**: `RaphaelRuntime.run_episode` (`src/orchestrator/runtime/loop.py:126`)
drives `STAGE_ORDER` (`src/orchestrator/runtime/stages.py:831`), which is
observe → world-read → candidates → plan → broker → exec → receipt →
integrate → contradiction → replan. `REVIEWER_GUIDE.md:5-6` names both as the
canonical runtime and states "10 stages, no more". Both external models independently
specified exactly this cycle.

But the loop is **inert**. All three feedback edges are stubs (§3): integration writes
a receipt-id string into the evidence graph instead of an observation; the
contradiction stage reads a dict whose only writer is unreachable from production; and
the replan stage triggers only on a signal the roadmap deletes (§4). The declared
ten-stage architecture is real; its feedback semantics are absent.

---

## 2. The loop that already exists

`RaphaelRuntime.run_episode` (`src/orchestrator/runtime/loop.py:126`) accepts
`max_iterations`, `action_cap`, `require_scope`, `episode_outputs`. Its docstring
(`loop.py:131-152`) documents §14.6 scope fail-closed, P3.11 §14.10 per-iteration
candidate sets and denial-driven replanning, and P4.1 §15.1 halt conditions.

Defaults are one iteration, one action
(`loop.py:159` — `max_iterations = halt.get("max_iterations", 1)`,
`action_cap = halt.get("action_cap", 1)`, `require_scope` default `False`).

`STAGE_ORDER` (`stages.py:831-841`) is exactly ten stages, ending at `STAGE_REPLAN`.
`STAGE_HANDLERS` (`stages.py:844`) maps each to its stage function. This is the
canonical control plane per `REVIEWER_GUIDE.md:5-6`.

Mapped to the classic cycle:

| Cycle phase | Stage |
|---|---|
| observe | `STAGE_OBSERVE` (`stages.py:831`) |
| reduce into belief | `STAGE_WORLDMODEL_READ`, `STAGE_WORLDMODEL_INTEGRATE` |
| plan | `STAGE_STUDENT_CANDIDATE`, `STAGE_PLANNER_REQUEST` |
| authorize | `STAGE_BROKER` |
| dispatch / execute | `STAGE_PEP` |
| observe again | `STAGE_RECEIPT` |
| integrate | `STAGE_WORLDMODEL_INTEGRATE` (`stages.py:712`) |
| detect | `STAGE_CONTRADICTION` (`stages.py:728`) |
| replan | `STAGE_REPLAN` (`stages.py:779`) |

The architecture is right. What is missing is the wiring that makes the last three
stages mean anything.

---

## 3. The three inert feedback edges

### 3.1 Integration writes a receipt id, not an observation

`stage_worldmodel_integrate` (`stages.py:712-726`) extracts the receipt and calls
`organs.record_integration(receipt.receipt_id)` (`stages.py:718`).

`record_integration` (`src/orchestrator/runtime/organs.py:103-113`) constructs an
`Evidence` with `trust_level=TrustLevel.TOOL_OBSERVATION`,
`source_detail="runtime.receipt"`, and — critically —
`raw_content=f"receipt:{receipt_id}"` (`organs.py:110`). The receipt's content
never reaches the evidence graph.

`WorldModel` exists on the organ bundle (`organs.py:57`) and is wired into the
Planner (`organs.py:80-88`). `record_integration` never touches it. The belief state
is therefore unchanged by any execution result; a string standing in for an
observation is what enters the graph.

Note also that `ActionReceipt` itself (`src/orchestrator/hardening/action_receipt.py:66`)
carries `result` as a free-text field (`action_receipt.py:103`) and
`impact_estimate` as an unconstrained string (`action_receipt.py:82`) — the
defect that makes the integration contract impossible to enforce today. See §8
Stage 1.

### 3.2 The contradiction stage reads a dict nobody fills in production

`stage_contradiction` (`stages.py:728-775`) reads
`organs.contradiction_manager.contradictions.values()` directly
(`stages.py:744`) rather than calling `detect_contradictions()`.

The only writer of that dict is `self.contradictions[con.contradiction_id] = con`
inside `ContradictionManager.detect_contradictions()`
(`src/orchestrator/brain/contradiction.py:196`, method defined at
`contradiction.py:161`).

Repo-wide callers of `detect_contradictions()` are:
`src/arena/ablation_runner.py:281`, `src/arena/runner.py:382`, and
`src/orchestrator/brain/contradiction.py:630` (a self-check that returns
`passed: False` when nothing is detected) — plus test files
(`tests/e2_shell_candidate_generation_test.py:566`, `tests/test_noop_contract.py:87`).
All are harnesses or self-verification. **Correction to an earlier draft of this
finding:** `src/arena/environment.py` does not call it; `environment.py:686-700`
is the T10 decoy handler, which fabricates contradicting evidence for the ablation
harness rather than invoking the detector.

Consequence: in production, `contradictions_found` is always `0` and `triggered` is
always `False`. Note also that the stage returns `success=True` unconditionally
(`stages.py:772`), regardless of what it found.

### 3.3 Replan fires only on a policy denial the open policy eliminates

`stage_replan` (`stages.py:779-800+`) reports `replanned=True` only when a
`DenialRecord` with `denial_class == DenialClass.PERSISTENT` exists whose
`(action_type, target, capability)` triple differs from the current receipt's triple
(`stages.py:800-806`, comparison at `stages.py:808-810`).

`DenialClass` (`src/orchestrator/brain/action.py:538-548`) defines `PERSISTENT` as
"based on policy/scope/capability and will not change within the episode";
`TEMPORARY` covers rate limits, budget, transient conditions.

So the self-correction branch is conditioned on **exactly** the class of signal the
open policy is designed to eliminate. That is the roadmap contradiction, §4.

---

## 4. The contradiction with the roadmap

> **Falsifiable claim.** Under the open policy proposed by
> `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md` — "gates stay real, policy goes open",
> every ticket returns broker `AUTHORIZED` (roadmap line 22, Phase 1 at line 68) —
> `DenialClass.PERSISTENT` records are not produced. `stage_replan`'s only trigger
> therefore never fires. `replanned` is permanently `False`. Raising
> `max_iterations` from 1 yields N iterations of the same ten inert stages.

Roadmap Phase 1 confirms the direction: broker denials of `tool_execute`/`agent_engage`
are removed, impact budget opens, rate limiter and engagement window become no-ops
(lines 78-91).

**Verification in under a minute:** grep the replan handler for `DenialClass`
(`stages.py:800`) and grep the roadmap for "AUTHORIZED" (line 22). The replan stage
has no other trigger.

This is not a nit about one stage. It is the architectural statement: *the repo's
only implemented self-correction path is conditioned on the denial signal that the
restoration roadmap deletes.* Under the current restrictive policy the loop is inert
too — one iteration by default, and the three feedback edges of §3 do not carry
information. Under the proposed open policy it is inert **by construction**.

The roadmap's Phase 3 multi-iteration wiring (line 166:
`RaphaelRuntime.run_episode(..., max_iterations=<open>, action_cap=<open>)`) therefore
multiplies zero signal N times.

---

## 5. Confirmed dead code and stubs

| Module / file | Line | What it claims | What it does | Evidence |
|---|---|---|---|---|
| `brain/strategy.py` | 12 | `build_strategy()` produces a phase list | Zero callers repo-wide | grep `build_strategy` → 1 hit, the definition |
| `brain/strategy_learner.py` | 16 | `get_best_strategy()` selects a learned plan | Sole caller `modes/autonomous.py:93` passes literal `"none"`, hitting `if mode == "none": return None` (`strategy_learner.py:17`) | Always `None` |
| `brain/strategy_learner.py` | 48 | `record_outcome()` learns | Zero callers; `q_table` (`strategy_learner.py:10`) is process-global and never persisted | Nothing ever writes it |
| `brain/reasoning.py` | 6 | `reasoning_chain()` reasons | 0 importers; returns a hardcoded 6-line template (`reasoning.py:8-15`) | No branching on `success` |
| `brain/reflection.py` | 7 | `reflect_outcome()` reflects | 0 importers; an f-string with two branches (`reflection.py:8-11`) | — |
| `brain/skill_indexer.py` | 8-14 | `SkillIndexer` indexes and searches skills | Consumer `agents/skill_agent.py:23` calls `build_index()`, `:27` calls `search(query, top_k=...)`; the class only defines `index` and `search(self, query)` | `AttributeError` at runtime |
| `brain/adaptive_brain.py` | 2 | — | Self-declared "AdaptiveBrain (31-line counter stub)" and a deprecation target in its own header | Header comment |
| `brain/plan_decision.py` | 19 | `PlanDecision` is "the causal intermediate" | 67-line frozen dataclass — an output record with no planning logic. The real Planner is `brain/action.py:649` | — |
| `Planner.decide()` | 839 | Ranks candidates by utility | Utility is a fixed sum of literal constants: base `0.5` (`action.py:921`), known entity `+0.3` (`:930`), relationships `+0.2` (`:935`), falsification `+0.4`/`+0.6` (`:942`, `:960`), version scan `+0.35` (`:975`), concrete action `+0.2` (`:983`), `shell_connect` `+0.3` (`:986`), `shell_command` `+0.4` (`:988`) | No learned or evidence-derived weight |
| `world.py` | 960, 973 | `_ingest_command_executed` / `_ingest_command_output` ingest command records | Both bodies are `return []` (`world.py:970`, `world.py:982`), yet both are registered in `handler_map` (`world.py:664-665`) | Registered no-ops |
| `world.py` | 124 | `Entity.add_identifier()` adds an alternative identifier | Writes `self.identifiers` only; `_by_identifier` is populated solely in `add_entity` (`world.py:275-279`). Post-hoc identifier writes are unsearchable | — |
| `world.py` | 1271 | `create_process()` builds a process entity | Uses `primary_identifier=f"pid:{pid}"` — not host-scoped; `_by_identifier` is last-write-wins (`world.py:278`) | PID collisions across hosts silently overwrite |
| `world.py` | 389 | `confirm_same_as()` confirms a resolution | Zero callers repo-wide (definition plus `evidence.py:374` variant; no call sites) | `ResolutionState.CONFIRMED_SAME_AS` (`world.py:87`) is unreachable |
| `world.py` | 850 / `tty_normalizer.py` 547 | `_ingest_user_accounts()` consumes parsed user lists | `_parse_user_list` emits `{"raw": line}` for `id`-style output (`tty_normalizer.py:567`), but `_ingest_user_accounts` requires `structured["accounts"][*]["username"]` (`world.py:861-863`) and skips entries without it | Silent end-to-end perception loss |
| — | — | World/hypothesis state is durable | **v1.2 correction:** no `from_dict`/loader in `brain/world.py` or `brain/hypothesis.py` (grep: zero) — but the claim was scoped to `brain/` and stated as repo-wide, which was **wrong**. Working loaders exist in the welded-off tree: `src/raphael/models/target_model.py:28-34` (round-trip verified faithful) and `src/raphael/hippocampus/episode_store.py:61-78`. Canonical state is lost on restart; a proven model of how to fix it is available | See lexicon §5 |

---

## 6. What is genuinely good and must be preserved

- **Confidence core** — `brain/hypothesis.py`: `compute_source_reliability`
  (`:174`), `compute_independence` (`:189`), `compute_freshness` (`:214`, 168.0h
  default half-life, decay `0.5 ** (age/half_life)` at `:231`), feeding
  `compute_confidence` (`:281`) which composes supporting/contradicting evidence,
  assumptions and falsification.
  **v1.2 correction:** an earlier draft called this "a real epistemic model, not a heuristic".
  That was **too generous** and is withdrawn. The code establishes that a confidence value is
  *computed* from factorised evidence inputs with a history. It does not establish that the
  value approximates `P(H true | available evidence)`, nor that higher confidence tracks higher
  empirical correctness. Either claim needs calibration, discrimination, update-validity,
  temporal-behaviour, adversarial-robustness and held-out measurements — none of which exist.
  Defensible claim: **a substantive confidence-scoring mechanism with factorised inputs and
  history; epistemic semantics partially specified; calibration unestablished.** Preserve the
  mechanism; do not cite it as validated.
- **Full `ConfidenceSnapshot` history** (`hypothesis.py:65`) — confidence is a
  record over time, not a scalar. Preserve.
- **`HypothesisManager` lifecycle** (`hypothesis.py:354`) — create/retire with
  evidence linkage. Preserve.
- **`DefeaterOutcome.NOT_TESTABLE`** (`brain/defeater_types.py:40`) — "No authorized
  discriminating action exists." A correct epistemic primitive that keeps unresolved
  state unresolved instead of collapsing it to a guess. Preserve and use (§10).
- **The ontology** — 15 `EntityType` members (`world.py:45-62`) and 17
  `RelationshipType` members (`world.py:65-84`), including the E1 shell-derived set
  (`PROCESS`, `FILE`, `NETWORK_CONNECTION`, `SHELL_SESSION`, `VULNERABILITY`).
  Sufficient for the control plane; do not grow it.
- **ScopeV0 CIDR matching** — `runtime/scope.py:143` dataclass; target matching via
  `ipaddress.ip_address(target) in ipaddress.ip_network(...)` (`scope.py:70`), network
  construction `strict=False` (`scope.py:165`), `covers()` at `scope.py:315`.
- **The one-way authorization chain** — PDP (`brain/capability_broker.py`) → PEP
  (`stages.py:stage_pep` → `exec/`), per `REVIEWER_GUIDE.md:7-8`. Never invert it.
- **The execution/evidence split** — `ActionReceipt` hash-bound lifecycle with
  `ActionProposalStatus` states (`action_receipt.py:28-56`, class `ActionReceipt` at `action_receipt.py:66`) is sound; its
  `result`/`impact_estimate` typing is not (§5, §8 Stage 1).

---

## 7. The minimum architecture

Five layers, with persistence cutting vertically. `src/orchestrator/brain/contracts/`
now exists as an unwired specification layer (its own `__init__.py:1-4` states
"a specification layer, not a wired implementation"); §7.1 records what it covers
and §7.2 what remains to be defined.

```
GOAL LEDGER          ── goals, subgoals, verified predicates, DefeaterOutcome
        │
BELIEF / WORLD STATE ── Evidence, Hypothesis, WorldModel, ResolutionState
        │
PLAN FRONTIER        ── candidate actions, preconditions, expected info gain
        │
ACTION / GOVERNOR    ── ActionSpec → Proposal → Scope → Broker (PDP) → Receipt
        │
EXECUTION / OBSERV.  ── PEP → exec/ primitives → Observation → Outcome
        │
PERSISTENCE (vertical, cuts all five; owns no semantics)
```

**§7.1 What `src/orchestrator/brain/contracts/` already provides** (reference
layer, imported by nothing in `stages.py` or `loop.py`):

- `outcomes.py:78` `ExecutionStatus` — DENIED / NOT_STARTED / FINISHED / TIMEOUT /
  TRANSPORT_ERROR / UNKNOWN_EXECUTION. `UNKNOWN_EXECUTION` is the required
  "cannot classify" state.
- `outcomes.py:94` `PredicateAssessment` — ESTABLISHED / REFUTED / UNKNOWN /
  DISPUTED, with `outcomes.py:117` `PredicateResult` requiring non-empty
  `evidence_ids` for ESTABLISHED/REFUTED.
- `outcomes.py:129` `ActionOutcome` — three-layer result carrying the invariant
  that "a finished command is not semantic success", and the `llm_transport.py:56-68`
  precedent applied to `failure_class`.
- `outcomes.py:107` `GoalProgress` and `goal.py:42` `GoalStatus` — evidence-gated
  completion; `goal.py:89` `GoalEvaluation.all_established` is the only input to
  SATISFIED.
- `action_spec.py:75` `ActionSpec` — immutable declared context projection
  (`declared_dependencies`), causal preconditions, `required_scope_predicates`,
  `impact_class`, retry policy.
- `identity.py:56` `make_process_identifier(host, pid)` — the host-scoped
  identifier `world.py:1271` lacks; `identity.py:126` `ExecutionIdentity` and
  `identity.py:148` `failure_key` distinguish a retry from a new operation.

**§7.2 Still missing and required by this design:**

- `Observation` — `observation_id`, `source`, `target`, `schema_version`,
  `payload: dict`, `received_at`. The *content* of an execution result. This is
  what `record_integration` (`organs.py:103`) should have been storing; no
  equivalent type exists in `contracts/` today.
- `BeliefDelta` — what changed in belief state after an observation, as entity/
  relation/resolution/confidence deltas, so the integrate stage becomes checkable
  instead of a `True` literal.
- `PlanStep` — `precondition_ids`, `action_spec`, `expected_information_gain`,
  `defeater`.
- `PlanFrontier` / `EpisodeController` services themselves — no type yet.

Layer rules:
- **GOAL LEDGER** may only read from BELIEF; it never authorizes.
- **BELIEF** never authorizes and never dispatches.
- **PLAN FRONTIER** proposes only; every step must carry its preconditions.
- **GOVERNOR** is the only layer that decides admissibility.
- **EXECUTION** returns `Observation` + `ActionOutcome`, never a verdict.

---

## 8. Build order

### 8.0 Authoritative order (v1.1 — this list governs)

v1.0 carried two conflicting build orders: this section began at Stage 0 while
§14 began at Stage −1. §14's ordering is adopted; this list is now canonical and
the per-stage detail below describes each entry in it.

```
Stage −1  Baseline / integrity
Stage  0  Perception + identity + provenance + persistence
Stage  1  Observation / outcome contracts
Stage  2  Goal ledger + predicate evaluation
Stage  3  PlanFrontier
Stage  4  EpisodeController + level reconciliation
Stage  5  Contextual-action memory / failure intelligence
Stage  6  Adversarial evaluation + mutation testing
```

Contradiction detection is **not** a separate late stage; it folds into Stage 1
(observation and assessment) per §16.5.

### 8.1 Stage detail

**Stage 0 — perception, identity, persistence boundary.** Do this first because
everything else reasons over it and today it silently loses data.

**v1.2 correction — persistence already exists and the state substrate is salvageable.**
This stage previously said "add `from_dict`/loaders for world + hypothesis state", implying
no loader exists. That was scoped to `orchestrator/brain/` and stated as a global fact; it was
wrong. Working loaders exist in the welded-off tree:

- `src/raphael/models/target_model.py:28-34` — `DomainState.from_dict`, round-trip verified
  faithful (`from_dict(to_dict(x)) == x` → `True`).
- `src/raphael/hippocampus/episode_store.py:61-78` — `_load` / `_save` / `store`.

`DomainState` (`target_model.py:8-34`) also carries a **third set, `unknowns`**, which is the
explicit-unknown primitive this stage was trying to design. See
`references/ARCHITECTURAL_LEXICON.md` §5.

So Stage 0 becomes: **port `DomainState` and `TargetModel.absorb()` rather than inventing
them**, then fix the canonical defects — `_ingest_user_accounts` accepting the `{"raw": line}`
shape, `add_identifier` updating `_by_identifier` (`world.py:124` vs `world.py:278`), host-scoped
process identity (`world.py:1271`), and the two no-op command handlers (`world.py:960`, `:973`).

`absorb()` (`target_model.py:86-121`) is the piece to take verbatim: it is set algebra, and its
`resolved_unknowns & domain.unknowns` makes a stale resolve structurally unable to *create* an
unknown. Two defects to fix while porting: `ConstraintDelta.to_dict()` truncates evidence to
500 chars (`:58`), and there is no `from_dict` (verified `hasattr(...) == False`), so deltas
cannot be replayed.

Acceptance: a restart preserves resolution state and confidence snapshots; a `getent`/`id`
output line produces an entity; `absorb` is idempotent under re-application of the same delta.

**Stage 2 — `GoalLedger` with verified predicates.** `contracts/goal.py:64` `Goal`
and `goal.py:89` `GoalEvaluation` already gate satisfaction on evidence; build the
ledger service on top of them. Use `DefeaterOutcome.NOT_TESTABLE`
(`defeater_types.py:40`) for predicates no authorized action can currently test.
Acceptance: a goal cannot be marked achieved by planner assertion.

**v1.2 correction — this is genuine new design, and it is the only stage that is.**
The salvage audit found **no planner anywhere in the legacy tree**: no solver, no goal
representation, no sequence construction, no backward chaining. `select_next_step`
(`src/raphael/cortex/planner.py:94`) is a flat candidate *filter* — four independent gates
applied to a registry, answering "what can I do now that I have not already done uselessly",
not "what sequence reaches the goal". Additionally its only execution path raises
`RuntimeError: Executor._subprocess_fallback() is removed in WELD-SUB14`
(`src/raphael/executor/kali_bridge.py:82-86`), so it has never run a technique to completion.

Therefore Stage 2 must be built fresh against the canonical runtime, on top of Stage 0's
affordance vector. Two live design questions are unresolved and belong here:

1. **Affordances or predicates?** They are the same abstraction under different names. Using
   both guarantees a third planner. The affordance vector is further along and is the
   persistence substrate; the recommendation is to re-specify the goal layer *over* it — a goal
   becomes "drive the affordance set from A to B" — rather than alongside it.
2. **Which state schema wins.** `src/raphael/models/` (live) and
   `src/raphael/cognitive/models.py` (orphaned, 14 files / 2,659 LOC, zero behavioural tests)
   define the same names incompatibly. The `cognitive/` records are richer — `Affordance`,
   `Constraint` and `Unknown` as objects rather than bare strings — but adopting them is a
   decision, not a rename over a live path.

**Stage 1 — outcome contracts + `ActionSpec`.** `src/orchestrator/brain/contracts/`
already exists (§7.1); extend it with `Observation` and `BeliefDelta` (§7.2), then
wire `record_integration` (`organs.py:103`) to store an `Observation` rather than
`f"receipt:{receipt_id}"` (`organs.py:110`).
Do **not** modify `ActionReceipt` (`hardening/action_receipt.py:66`); the new types
reference receipts by `receipt_id` alongside it. Acceptance: an execution result
round-trips as structured content, and an unclassifiable result is representable
as unclassifiable.

**Stage 2 — `GoalLedger` with verified predicates.** `contracts/goal.py:64` `Goal`
and `goal.py:89` `GoalEvaluation` already gate satisfaction on evidence; build the
ledger service on top of them. Use `DefeaterOutcome.NOT_TESTABLE`
(`defeater_types.py:40`) for predicates no authorized action can currently test.
Acceptance: a goal cannot be marked achieved by planner assertion.

**Stage 3 — `PlanFrontier`.** Bounded backward chaining from unmet predicates to
`PlanStep`s, replacing the constant-sum utility in `Planner.decide()`
(`action.py:839-990`). Candidate ordering becomes a *derived* consequence of
precondition closure and expected information gain, not a literal table.
Acceptance: removing a literal from `action.py:921-988` changes no ranking for a
scenario whose evidence supports the ranking.

**Stage 4 — `EpisodeController` above `BaseAgent.run()`.**
`BaseAgent.run` (`src/orchestrator/agents/base.py:123`) already iterates
(`base.py:131`) and terminates on `should_terminate` (`base.py:119`). The controller
owns iteration budget, replan triggers, and goal-state evaluation. This is where
`stage_replan`'s trigger set becomes a real decision (§12 Q2). Acceptance: an
episode terminates on goal achievement, goal impossibility, or budget — not only
on iteration count.

**Stage 5 — failure intelligence.** Make `detect_contradictions()`
(`contradiction.py:161`) reachable from production by having the integrate stage
call it on the `CONTRADICTS` relations it creates. Then `stage_contradiction`
(`stages.py:744`) can report a real number. Acceptance: injecting two contradictory
`TOOL_OBSERVATION` records into an episode yields
`contradictions_found > 0` from the stage.

**Stage 6 — evaluation.** The falsification suite of §11, with an
evaluator-controlled oracle.

---

## 9. What NOT to build

- No RL, no Q-learning. `strategy_learner.py` has a `q_table` with no writer
  (`strategy_learner.py:10`, `record_outcome` at `:48` uncalled). Do not revive it
  yet. If learning is later wanted, the correct substrate is outcome-labelled
  evidence in the belief state — not a parallel table in a process global.
- No learned action weights. The literal constants at `action.py:921-988` should be
  *deleted*, not trained.
- No multi-agent supervisor hierarchy.
- No MCTS, no HTN/PDDL planning formalism.
- No giant semantic memory. `EvidenceGraph` (`brain/evidence.py`) plus hypotheses
  is sufficient and is already the canonical evidence substrate
  (`REVIEWER_GUIDE.md:13`).
- No recursive self-improvement.
- No autonomous capability invention. Capability registration is an operator act
  (see roadmap line 148: register each with capability names + action classes).

The general rule: every one of these is a *learning or search* mechanism proposed to
compensate for a substrate that does not exist yet. Fix the substrate first.

---

## 10. Governance

**Scope is an admissibility predicate AND is enforced independently at dispatch.**
Every action must satisfy:

```
dispatchable(a, s) = causal_preconditions
                  AND scope_allowed
                  AND budget_available
                  AND broker_authorized
```

- `causal_preconditions` are checked in PLAN FRONTIER; the other three are checked
  in ACTION / GOVERNOR. Precondition satisfaction is never authorization.
- **Unknown scope-relevant parameters mean NOT DISPATCHABLE, never
  probably-permitted.** `ScopeV0` (`scope.py:143`) matching is CIDR-based with
  `strict=False` (`scope.py:165`); an unparseable or unresolvable target must
  fail the predicate, not fall through to an allow.
- `NOT_TESTABLE` (`defeater_types.py:40`) preserves unresolved epistemic state and
  **never relaxes authorization**. A goal whose discriminator is not authorized
  stays open; it is not converted into permission.
- **The broker authorizes the concrete resolved action and target, never the
  planner's label.** Today `stage_replan` compares `(action_type, target,
  capability)` strings off the receipt (`stages.py:802-805`). Under Stage 1 the
  broker's decision attaches to an `ActionSpec` whose parameters are resolved
  before authorization, so a proposal cannot be authorized as a label and executed
  as different parameters.
- The one-way chain of §6 is preserved: PDP decides, PEP enforces, `exec/` is the
  sole owner of primitives (`REVIEWER_GUIDE.md:7-9`).

---

## 11. The honesty problem

The repo's stated failure mode is **docstrings asserting behaviour the code does not
have.** Confirmed instances:

1. `world.py:24` — "Each resolution step requires evidence." `confirm_same_as`
   (`world.py:389-393`) defaults `additional_evidence` to `None`, and has zero
   callers.
2. `world.py:175` — "States: SEPARATE → POSSIBLY_SAME_AS → CONFIRMED_SAME_AS."
   `SEPARATE` is assigned nowhere; `CONFIRMED_SAME_AS` is unreachable.
3. `stage_contradiction` returns `success=True` unconditionally
   (`stages.py:772`) — a stage that measured nothing reports success.
4. `stage_worldmodel_integrate` returns `{"integrated": True}` unconditionally
   (`stages.py:724`) after writing a string.

**Proposal: executable invariants over prose.**

- **Declared-handler reachability check.** For every symbol registered in a
  dispatch table or handler map — `STAGE_HANDLERS` (`stages.py:844`),
  `handler_map` (`world.py:657-666`) — assert the symbol has at least one call
  site reachable from a production entry point, and assert its return is consumed.
  This check alone would have caught `world.py:960`/`:973` and
  `confirm_same_as`.
- **Docstring-claim audit.** Extract checkable claims from docstrings ("requires",
  "each", "every", "returns", state-transition enumerations) and assert each has a
  corresponding code path or a marked `TODO(claim)`. An unenforced claim becomes
  a typed comment, not a sentence.
- **Falsification suite**, measured by an evaluator-controlled oracle — never by
  agent self-report:
  1. **Outcome perturbation** — flip an execution result; belief state must change.
     Today it cannot (`organs.py:110`).
  2. **Evidence perturbation** — remove one supporting evidence id; confidence must
     fall (`hypothesis.py:281`).
  3. **Scope narrowing mid-episode** — narrow `ScopeV0` between iterations
     (`scope.py:143`); subsequent dispatches must fail the predicate.
  4. **Crash/restart** — kill after integrate; restart must recover resolution and
     confidence state (currently impossible: no loader).
  5. **Held-out novel compositions** — entity/relationship pairs not present in the
     ontology's training examples; the controller must not hallucinate a relation.

  Pass criteria are oracle-side (state deltas, gate decisions), not stage return
  values. `{"integrated": True}` is not evidence of integration.

---

## 12. Owner decisions

### 12.0 Decided in this session (removed from the open list — v1.1)

v1.0 carried these as open questions after they had in fact been settled by
three-way agreement. They are decisions, not questions:

| Formerly "open" | Resolution | Where |
|---|---|---|
| Replace stage bodies or the loop? | **Keep the skeleton, replace the inert handler semantics.** Preserve `STAGE_ORDER`, the one-way authorization ordering, and the runtime entry point. | Round 3, both models independently |
| Replan trigger set? | **Level-based reconciliation**, not an event disjunction. Every pass compares state against commitments; events only accelerate it. | §17 |
| Single enum or split outcomes? | **Split.** Execution status / predicate assessment / goal progress are three layers. | §16.2 |
| Plan graph before perception? | **Perception first.** Outcome contracts, then goals, then plan frontier. | §8.0 |
| Is scope a precondition evaluator? | **Yes — and enforced independently at dispatch.** Unknown scope-relevant parameters are not dispatchable. | §10 |

### 12.1 Still genuinely open

1. **The `reverse_shell.py` import-boundary decision.** Blocks Stage −1.
   Restore through authorized remediation, remove imports and dependent
   assumptions, or implement an explicit unavailable state. Measured impact:
   121 failed, 122 passed, 30 collection errors, all from this one module
   (§13). Not resolvable by this document.
2. **The replan trigger set, concretely.** §17 settles the *mechanism*
   (level-based); it does not enumerate which signals should force a repair.
   Candidates: goal-achieved, goal-impossible, precondition invalidation,
   budget exhaustion, `NOT_TESTABLE` with no remaining discriminator.
3. **Whether to keep the roadmap's open-policy change.** §4 shows it deletes the
   only implemented self-correction trigger. Either replace the trigger set
   before shipping multi-iteration wiring, or defer the open policy until
   Stages 3–5 land. Doing it without the replacement ships an N-iteration no-op.
4. **Migration cost for retiring `STAGE_CONTRADICTION`** per §16.5, since it is
   a registered stage and the reviewer's position changes the stage graph.

---

*Every `path:line` above was verified against the working tree at branch
`offensive-restore`. Where an earlier draft's citation was wrong — `environment.py:692`
as a caller of `detect_contradictions()` — the correction is stated inline in §3.2.*

---

## 13. Baseline reality (measured, not documented)

Round 4 measured the test tree for the first time since the P1 edits.

```
121 failed, 122 passed, 30 collection errors
```

**Root cause, verified:** `src/orchestrator/capabilities/interactive_shell/__init__.py:23`
imports `.reverse_shell`, and `reverse_shell.py` is deleted in the worktree. The
deletion predates this session (`git status` reported `D` at its start) and is
roadmap P1 step 1, not damage.

**Fan-out, verified:** all 121 failures and all 30 collection errors carry the
identical `ModuleNotFoundError` (436 references across one run). One missing
module accounts for the entire red tree. There is no second cause.

Two documentation claims are therefore false against the current tree:

| Source | Claim | Actual |
|---|---|---|
| `RAPHAEL_STATE.md:11` | `357 passed / 0 failed / 0 skipped` | not the current tree |
| `RAPHAEL_EVOLUTION_BLUEPRINT_v1.md` §0 | `last green = 621 at P0.1` | stale |

**Precision about what 122 means.** 122 is an *observed partial result*, not a
test floor. With 30 collection errors the suite was never fully evaluated, so
pytest's success condition is not met. A subset passing is not a floor. The
correct statement is: "121 failed, 122 passed, 30 collection errors, single root
cause `reverse_shell` absent."

This is §11's failure mode in its purest form: a documented claim with no
falsifiable behavioral witness, wrong by roughly 3x.

## 14. Stage -1: baseline integrity precedes perception integrity

Round 4 converged that Stage 0 needs a prerequisite stage.

> The authoritative stage ordering is **§8.0**. It is not restated here: v1.1
> removed this duplicate because two build orders in one document is exactly
> the kind of undocumented divergence §11 describes. §14 covers Stage −1 only.


**Stage -1 requires an authorized decision on the missing module.** Three
options, and none of them is "suppress the import error to get green":

| Decision | Correct repair |
|---|---|
| Capability remains required | Restore through the authorized remediation process |
| Capability intentionally removed | Remove its imports, registration, dependent assumptions |
| Capability is optional | Implement an explicit unavailable state, and test that state |

**Honest parallel-work rule:** contract development may continue under a named,
reproducible subset. Runtime integration acceptance stays blocked until the
baseline is restored or explicitly redefined with reviewed exclusions. A red tree
does not prevent engineering; it prevents honest system-level evaluation.

**The two floors** that replace prose assertions:

- *Import/collection floor*: `collection_errors == 0` for the supported surface.
- *Behavioural floor*: a machine-recorded manifest of `commit`, `test_command`,
  `environment`, `collected`, `passed`, `failed`, `skipped`, `xfailed`,
  `collection_errors` — so every later run reports `current - baseline`.

## 15. Claim records (documentation as a view, never a source)

Replace handwritten test-count and capability claims with machine-asserted records.
The governing invariant:

```
No generated claim may outrun its evidence.
documentation_claim.value == authoritative_artifact.value
```

On mismatch: fail the build, or mark the artifact `STALE / UNVERIFIED`.

```python
@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    subject: str
    metric: str
    value: str
    unit: str
    source_artifact: str      # e.g. pytest-report.json
    source_revision: str      # commit or worktree digest
    measured_at: float
    verification_command: str
    status: str               # VERIFIED | STALE | UNVERIFIED
```

Minimum gate scope: current baseline status; "implemented"/"complete"/"verified"
milestones in the state document; authorization and semantic-success guarantees.
Everything else stays design intent, explicitly labelled as such.

**Mandatory mutant:** replace a required behavioural witness with a no-op while
keeping the documentation claim. The acceptance check must fail.

## 16. Four-layer outcome semantics (v1.1 — corrected)

**v1.1 correction.** The v1 contract in this section collapsed three distinct
notions into one `effect_status`, and asserted an invariant that is false. Both
are fixed below. The v1 text is retained in §16.1 so the retraction is auditable.

### 16.1 What was wrong

The v1 vocabulary was:

```
execution_status   FINISHED
input_disposition  ACCEPTED | UNPARSEABLE
effect_status      ESTABLISHED | NO_EFFECT | UNKNOWN
```

Two defects:

1. **`ESTABLISHED` conflated predicate assessment with integration effect.** A
   supported observation can confirm an *already-known* fact without mutating
   belief state. That is an assessment, not a state change. Separately, a belief
   can be updated without being relevant to the current goal. One field cannot
   carry both.
2. **The v1 invariant was too strong and has been retracted.** v1 asserted:

   ```
   effect_status == ESTABLISHED  ⇒  produced_artifact_refs ≠ ∅
                                ⇒  state_delta_refs ≠ ∅
   ```

   This is false: confirming an already-known fact produces qualifying evidence
   with an *empty* state delta. The second conjunct was wrong and is withdrawn.
   The retraction preserves epistemic evidence independently of state mutation.

`NO_EFFECT` is also withdrawn as a term — "no effect" is vague about *what*.
`NO_BELIEF_UPDATE` says precisely what did not change.

### 16.1a The missing `Observation` contract (v1.1)

Gap confirmed against the repo: `grep "class Observation"` over
`src/orchestrator/brain/contracts/` returns **nothing**. The four-layer model
above is unimplementable without it, because an assessment needs a provenance
and a validity window to qualify as evidence. Must be added to
`contracts/` before Stage 1:

```python
@dataclass(frozen=True)
class Observation:
    """A typed, provenance-bearing reading. Not yet a belief."""
    observation_id: str
    execution_id: str            # ties to ExecutionIdentity, not a raw receipt
    subject_ref: str             # canonical, namespace-qualified (see identity.py)
    predicate: str
    value: str
    provenance_channel: str      # TrustLevel member (trust.py:43)
    observed_at: float
    validity_interval: tuple     # (not_before, not_after); absence ⇒ not expired
    extractor_version: str
    source_artifact_ref: str     # the raw output, never inlined
    coverage_contract_ref: str   # required before any negative conclusion (§16.4)
```

Two properties this must carry, both drawn from defects in §3 and §5:

- `provenance_channel` is `TrustLevel`, not a free string. `trust.py:43` already
  defines the seven channels including `TARGET_CONTROLLED` and `MODEL_INFERENCE`;
  the world model imports `TrustLevel` and never reads it. An observation whose
  channel is `MODEL_INFERENCE` is a proposal, not evidence.
- `validity_interval` is required because the world model has `first_seen` /
  `last_seen` and `Relationship.expires_at` with no decay and no
  contradiction-driven invalidation. Without an interval, a stale reading can
  never stop being load-bearing.

`coverage_contract_ref` is what stops an absence from becoming a refutation. It
is null when no coverage claim is being made, and required before any
`REFUTED` assessment.

### 16.2 The corrected four layers

```python
class StageExecution(str, Enum):
    COMPLETED = "completed"     # the stage's protocol ran to completion
    FAILED    = "failed"        # exception, or durable write failed

class InputDisposition(str, Enum):
    SUPPORTED_PARSED      = "supported_parsed"
    SUPPORTED_PARSE_FAILED= "supported_parse_failed"
    UNSUPPORTED           = "unsupported"   # no adapter for this output shape
    ABSENT                = "absent"        # nothing to interpret

class IntegrationEffect(str, Enum):
    BELIEFS_UPDATED   = "beliefs_updated"
    NO_BELIEF_UPDATE  = "no_belief_update"
    INTEGRATION_FAILED= "integration_failed"

class PredicateAssessment(str, Enum):
    ESTABLISHED = "established"
    REFUTED     = "refuted"
    UNKNOWN     = "unknown"
    DISPUTED    = "disputed"
```

Four distinct semantics, four distinct owners:

| Layer | Writer | Establishes |
|---|---|---|
| Stage execution | stage handler | the protocol ran |
| Input disposition | reducer/adapter | whether the output was interpretable |
| Integration effect | world-model writer | whether belief state changed |
| Predicate assessment | registered verifier | what is true, with evidence |

### 16.3 The pipeline these types describe

```
Action → Execution → Observation → Observation validation/parsing
       → Predicate assessment → Belief update → Goal evaluation
       → Plan reconciliation → Next commitment
```

Not `Action → Receipt → Integration → Goal progress`. The four-step collapse was
the defect.

Worked example. Same target, two executions, both successful:

```
Action            inspect X
Observation       service X:22 is reachable
Assessment        reachable(X,22) = ESTABLISHED
Belief update     reachable(X,22): UNKNOWN → TRUE      # mutates
Goal evaluation   no goal predicate changed
Reconciliation    existing plan remains valid

Action            inspect X again
Observation       service X:22 is reachable
Assessment        reachable(X,22) = ESTABLISHED          # same verdict
Belief update     NO_BELIEF_UPDATE                      # does not mutate
Goal evaluation   unchanged
Reconciliation    repeated action yields no new information
```

Both are successful executions. Only one mutates belief state. The v1 contract
could not express this pair.

### 16.4 Corrected invariants

```
BELIEFS_UPDATED            ⇒  state_delta_refs ≠ ∅
ESTABLISHED | REFUTED      ⇒  qualifying_evidence_refs ≠ ∅
                           ∧  verifier_contract ≠ ∅
STAGE_COMPLETED            ⇏  predicate_established
INTEGRATION_FAILED         ⇒  predicate assessment for the affected subject is UNKNOWN
ABSENT | UNSUPPORTED       ⇒  no predicate assessment may be produced
```

`ABSENT` and `UNSUPPORTED` producing no assessment is what prevents an
uninterpretable receipt from becoming a refutation, and therefore from
retiring a plan node.

### 16.5 Where contradiction detection belongs

**Correction to the stage model.** Contradiction is not a late feedback stage.
It is a property of assessments: two assessments about the same resolved
subject, property, and overlapping validity window that cannot both hold. It
must therefore live in the observation/assessment path where supported evidence
can actually produce or revise it — not in a `CONTRADICTION` stage that runs
after the fact against a dict with no producer (§3.2).

`STAGE_CONTRADICTION` (`stages.py:728`) should be retired as a stage and its
function folded into assessment. A stage that only summarises assessments
adds a second place for the semantics to drift.

### 16.6 Why the current implementation still fails

`stage_worldmodel_integrate` (`stages.py:712`) writes
`Evidence("receipt:<id>")` (`organs.py:110`) and returns `success=True`. Under
the corrected contract that is:

```
StageExecution.COMPLETED
InputDisposition.ABSENT          # a receipt id is not interpretable output
IntegrationEffect.NO_BELIEF_UPDATE
PredicateAssessment: none produced
```

It is not uncertifiable on the state-delta ground (retracted). It fails on the
input-disposition ground: `ABSENT` was reported as if input had been
`SUPPORTED_PARSED` and had produced no effect, when in fact nothing was
interpreted at all.

## 17. Reconciliation invariant (adopted from Round 3)

Event-triggered correctness is insufficient; edges can be lost or duplicated.
Reconciliation is **level-based**: every pass compares current authoritative
state against outstanding commitments. Events accelerate or explain it.

> Before each dispatch, the selected commitment is valid against the current
> relevant state, authorization, and budget — **even if no change event was
> delivered.**

This removes denial as the architectural hinge without removing denial as an
input. `ReconciliationRecord` must record `NO_CHANGE` explicitly; inventing a
repair to demonstrate activity is the same failure mode as a handler reporting
success while doing nothing.

## 18. Kill-switch guarantee, stated so it is true and testable

The roadmap's "one-file revert to full deny-all" does not hold as written,
because a queued proposal can still reach dispatch. State it against **execution
admission**, not proposal creation:

> Activating deny-all establishes a new policy epoch. After activation
> acknowledgment, every new execution admission — including queued proposals,
> retries, and resumed operations — is denied while deny-all remains active.
> Prior authorization cannot authorize admission under the new epoch. Operations
> admitted before activation are reported separately as in flight; cancellation is
> not implied.

A remote invocation admitted before activation may still finish afterward.
Claiming otherwise requires fencing or cancelling pending handoffs; do not claim
it without implementing and testing it.

The policy transition and the admission check require a defined ordering (shared
lock or atomic fencing). Checking the policy and then invoking later is a
check/use race (CWE-367).

**Invariant:** for every execution admission ordered after deny-all activation,
while deny-all remains active — `admission.decision == DENY`, no executor
invocation is issued, and `admission.policy_epoch >= activation.policy_epoch`.

**Mandatory mutant:** use the proposal's cached epoch-7 authorization instead of
checking the current admission policy. It must invoke the executor and fail the
test. A second race mutant releases the admission fence between authorization and
handoff.

Corrected wording: *one configuration change selects deny-all at the
authoritative admission boundary; unchanged broker and PEP enforcement prevents
stale proposals from bypassing it.* One-file configuration is not one-file
enforcement.

## 19. Next milestone

Not "contracts exist", and not "autonomous Raphael":

> Raphael executes one authorized action, accurately determines what happened,
> persists that determination, and demonstrably alters a future decision because
> of it.

Smaller, and much harder to fake. Once that single causal edge is truthful, the
plan graph has a real substrate rather than a notation.

**Trust axiom (adopted):** Raphael is not trusted because its modules exist, its
tests are green, or its documentation says they work. It is trusted only to the
extent its claimed causal pathways are demonstrably reachable, observable,
persistent, and capable of changing future behaviour under controlled
interventions.
