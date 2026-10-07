# RAPHAEL MASTER ROADMAP v1

**Derived from:** `RAPHAEL_BRAIN_BLUEPRINT_v1.md` (architecture) +
`references/ARCHITECTURAL_LEXICON.md` (salvage audit of `src/raphael/`).
**Date:** 2026-10-01. Every structural claim carries a `path:line` citation.

---

## 0. What changed after grounding

The blueprint was written before the salvage audit. Two of its load-bearing premises did not
survive contact with `src/raphael/`:

| Blueprint said | Grounding found |
|---|---|
| "Stage 2 goal/plan graph must be built from scratch" | **Correct** — but Stage 0/1 are *not* from scratch; the state substrate and negative-cache design already exist. |
| "No persistence exists anywhere" | **False.** `src/raphael/hippocampus/episode_store.py:61-78` and `src/raphael/models/target_model.py:20-34` both persist with faithful round-trips. My claim was scoped to `orchestrator/brain/` and stated as a global fact. |

And one premise the blueprint never made at all: **`src/raphael/` is an 86-file, 12,662-line
parallel agent architecture**, packaged (`pyproject.toml:31`), that the governance docs never
mention (`REVIEWER_GUIDE.md` / `RAPHAEL_STATE.md` contain zero references to it).

---

## 1. Repository shape — what exists

Surveyed by file/line count:

| Package | Files | Lines | Disposition |
|---|---|---|---|
| `orchestrator/` | 263 | 57,818 | **Canonical.** `REVIEWER_GUIDE.md` names `runtime/loop.py` the control plane. |
| `arena/` | 39 | 22,194 | Evaluation/ablation harness. Test scaffolding, not runtime. |
| `raphael/` | 86 | 12,662 | **Welded-off legacy architecture.** Salvage source — see lexicon. |
| `agent/` | 17 | 6,699 | Capability modules. Outside this roadmap's scope. |
| `mcp-hub/` | 33 | 1,414 | MCP server surface. |
| `sword/` | 10 | 1,294 | `SwordPipeline` phase-0→5 runner. A third pipeline family; capability-oriented. |
| 9 thin services | 15 | 2,295 | Service wrappers. |

**Scope of this roadmap:** the control plane only. `agent/`, `sword/` and the service wrappers
are recorded for completeness and are not analysed further.

---

## 2. The problem, restated after grounding

`RaphaelRuntime.run_episode` (`loop.py:126`) executes a 10-stage `STAGE_ORDER`
(`stages.py:831`) and **terminates after one iteration by default** (`loop.py:159`) — confirmed
by execution, not by reading:

```
Runtime trace: 10 stages
Termination: G3-EN-5 organ-wired walking skeleton: one iteration complete
```

All three feedback edges are dead:

1. `stage_worldmodel_integrate` (`stages.py:712`) calls `organs.record_integration`
   (`organs.py:103`), which stores the string `f"receipt:{receipt_id}"` as evidence content
   (`organs.py:110`). The live `world_model` at `organs.py:57` is never touched.
2. `stage_contradiction` (`stages.py:728`) reads `contradiction_manager.contradictions`
   directly (`stages.py:744`); the only writer is `contradiction.py:196`, reachable only from
   test/ablation harnesses.
3. `stage_replan` (`stages.py:779`) fires only on `DenialClass.PERSISTENT` (`action.py:538`).

**And the roadmap that proposes to fix this makes it worse:** opening the policy removes
policy/scope/capability denials, so `stage_replan`'s only trigger becomes unreachable. Raising
`max_iterations` then yields N iterations of the same inert stages.

---

## 3. The systemic defect: declared ≠ implemented

Six configuration values across both architectures have types, defaults, docstrings or enums
implying behaviour that does not exist:

| Knob | Appears to | Actually |
|---|---|---|
| `action_cap` | cap actions per episode | parsed `loop.py:160-161`, never referenced in the loop body |
| `EventPriority` | prioritise by urgency | stored; XADD is FIFO (`eventbus/core.py:66,302-307`) |
| `ranking_weights` | tunable ranking | both values are 1.0 (`cortex/planner.py:44`, used `:170`) |
| `stealth_score` | stealth tuning | read by no code |
| `Thermoregulator._current_risk` | back-pressure | initialised 0.0, only decayed, no writer (`main.py:96,99`) |
| `_exhaustion_counts` | exhaustion tracking | declared `cortex/planner.py:50`, live var is the singular `:53` |

Plus two more of the same shape in the canonical tree: `Planner.decide()`'s literal constants
(`action.py:921`) and `stage_contradiction` returning `success=True` unconditionally.

**This is why the build order starts with measurement, not construction.** No review of
docstrings will catch this class; only a machine check will.

---

## 4. Salvage decision

| Component | Verdict | Basis |
|---|---|---|
| `TargetModel` / `DomainState` (affordances, constraints, **unknowns**) | **SALVAGE** | Faithful round-trip verified; `unknowns` is the primitive the canonical world model lacks |
| `TargetModel.absorb()` (`:86-121`) | **SALVAGE VERBATIM** | Set algebra; `resolved_unknowns & unknown` makes a stale resolve unable to *create* an unknown |
| Negative cache with resurrection (`:129-148`) | **SALVAGE THE IDEA** | Context-bound failure record that revalidates — better than the `contracts/identity.py` re-derivation |
| `Technique` declaration schema (16 fields) | **SALVAGE THE SCHEMA** | Effect *semantics* are unsound — see below |
| Exhaustion counter | **PARTIAL** | Count path live; repetition branch dead (empty set at call site `:123`) |
| Event bus (827 lines) | **REIMPLEMENT trace/metrics only** | Double-application on retry; silent black-holing; unreachable |
| Executor / verifier / blackboard plumbing | **DO NOT LIFT** | Trust-the-planner: `enforce_broker_mediation()` called from 2 dead files only |
| `KaliBridge` execution path | **DEAD** | Raises `RuntimeError: ... removed in WELD-SUB14` (`kali_bridge.py:82-86`) |

**Three unsound effects to carry as prohibitions:**

- `executor.py:114-115` grants `provides_affordances` after **every** run regardless of outcome,
  so a failed execution grows the affordance set and unblocks downstream techniques.
- `provides` and `provides_affordances` disagree in 5 of 24 declarations, and three consumers
  read different ones — relevance-filtering and state-mutation disagree.
- `ConstraintDelta.to_dict()` truncates evidence to 500 chars (`:58`); no `from_dict` exists.

---

## 5. Build order

```
Stage −1  Repository truth          resolve the import break; machine-record the true floor
Stage  0  State substrate           affordance/constraint/unknown model + absorb() + persistence
Stage  1  Outcome contracts        four-layer semantics + verifier-gated effects
Stage  2  Goal-directed planning    ← GENUINE NEW DESIGN, no salvage exists
Stage  3  Plan frontier             bounded backward chaining over ActionSpec
Stage  4  Reconciliation           level-based ControlDecision above BaseAgent.run()
Stage  5  Failure memory            contextual action keys, informed by the resurrection cache
Stage  6  Adversarial evaluation   mutation tests on every causal edge
```

### Stage −1 — repository truth (blocking)

`src/orchestrator/capabilities/interactive_shell/reverse_shell.py` is deleted in the worktree
but present at HEAD `e6a8c707`. `interactive_shell/__init__.py:23` still imports it, so
`orchestrator.runtime` is unimportable and **30 test modules fail to collect**. Measured:
121 failed / 122 passed / 30 errors, single root cause, 436 references.

**Owner decision required** — restore via authorized remediation, remove imports and dependent
assumptions, or implement an explicit unavailable state. Suppressing the import to obtain green
is not an option.

Deliverable: a machine-written `ClaimRecord` (§6) recording commit, command, environment, and
collected/passed/failed/skipped/xfailed/collection_errors.

### Stage 0 — state substrate (substantially salvageable)

Port `DomainState` and `absorb()`. Add what the salvage lacks: provenance channels typed as
`TrustLevel` (`trust.py:43`, already defined and never read), and validity intervals.

### Stage 1 — outcome contracts (four layers)

`StageExecution` / `InputDisposition` / `IntegrationEffect` / `PredicateAssessment` — already
specified in `brain/contracts/outcomes.py`. **Effects must be verifier-gated against evidence,
never granted because a run completed** — the explicit prohibition from the salvage audit.

### Stage 2 — goal-directed planning (new design)

**Nothing to salvage.** The legacy tree has a candidate *filter*, not a planner: no solver, no
goal, no sequence construction, no backward chaining. This stage must be built fresh against
the canonical runtime, using the Stage 0 affordance vector as its state substrate.

> **Contested, unresolved:** whether `STAGE_CONTRADICTION` (`stages.py:728`) is retired as a
> stage with contradiction folded into assessment, or kept with a changed contract
> (*derive contradiction from qualified persisted assessments*). ChatGPT argued a property can
> still have an independent processing stage; Perplexity argued it is semantically an assessment
> property. **Undecided — see lexicon §7.**

### Stage 6 — adversarial evaluation

Mandatory mutants, each of which must fail a behavioural test:

```
integration becomes no-op          reconciliation requires denial again
contradiction producer no-op       postcondition assessment always establishes
state reload drops execution       breadth-deleting weights replaced with 1.0
```

The last is new and comes from §3: a test that passes with `ranking_weights` set to no-ops is a
test that certifies nothing.

---

## 6. Governance invariants

```
No generated claim may outrun its evidence.
documentation_claim.value == authoritative_artifact.value
```

Dispatch admissibility, adopted from the three-way session:

```
dispatchable(a,s) = causal_preconditions(a,s) AND scope_allowed(a,s)
                  AND budget_available(a,s) AND broker_authorized(a,s)
```

Unknown scope-relevant parameters mean **NOT DISPATCHABLE**, never probably-permitted.
`NOT_TESTABLE` preserves unresolved epistemic state and never relaxes authorization.
**The broker authorizes the concrete resolved action and target, never the planner's label** —
the salvage audit is why this matters, since the legacy executor trusts the planner entirely.

Kill-switch guarantee (true and testable): activating deny-all establishes a new policy epoch;
after acknowledgment, every new execution admission — including queued, retried and resumed
operations — is denied. Prior authorization cannot authorize admission under the new epoch.
Operations admitted before activation are reported as in flight; cancellation is not implied.

---

## 7. Open decisions requiring the owner

1. **The `reverse_shell.py` import boundary.** Blocks Stage −1. Not resolvable by analysis.
2. **The replan trigger set.** §17's mechanism (level-based reconciliation) is settled; the
   concrete signal set is not.
3. **Whether to keep the roadmap's open-policy change**, given it deletes the only implemented
   self-correction trigger.
4. **`STAGE_CONTRADICTION`: retire or retain-with-changed-contract.**
5. **Which schema wins** if the richer `cognitive/models.py` records are adopted over the live
   `models/` shape.

---

## 8. Honest status

The **contract layer is executable and falsifiable in isolation** (`brain/contracts/`, 6 files).
The **integrated brain is not**, and cannot be until Stage −1 clears. No claim of autonomous
behaviour is supported by the current tree, and the six dead knobs in §3 mean several existing
configurations appear to do things they do not.

Next milestone — much smaller than "autonomous Raphael":

> Raphael executes one authorized action, accurately determines what happened, persists that
> determination, and demonstrably alters a future decision because of it.
