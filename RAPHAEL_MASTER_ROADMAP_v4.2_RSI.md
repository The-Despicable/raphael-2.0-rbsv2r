# RAPHAEL MASTER ROADMAP v4.2 — DUAL-LANE EXECUTION + RSI AMENDMENT

**Purpose:** Canonical, implementation-grade roadmap for completing Raphael as one coherent system and, only after the secure core is proven, establishing a governed recursive-improvement substrate.

**Primary implementation agents:**
- **Minimax / OMP / HackerAI-class execution agent:** repository inspection, code changes, test execution, debugging, migration, evidence production.
- **GLM:** architecture authority, contract author, adversarial reviewer, gatekeeper.

**Status:** Planning / execution contract, **v4.2**. This document supersedes prior phase wording where it explicitly adds or revises the RSI-related P4–P10 requirements below. It does not authorize work outside the current phase/task packet.

**Source basis:**
- RAPHAEL MASTER ROADMAP v4 — DUAL-LANE EXECUTION.
- RAPHAEL MASTER ROADMAP v4.1 — ARBITRATION & FINAL AMENDMENT SET (AM-1…AM-14).
- *The Last AI Built by Humans — Toward Genuine Recursive Self-Improvement*, arXiv:2609.11873v2.
- *Dream-RSI — Recursive Self-Improvement through Evolving Worlds*, arXiv:2609.14858v1.
- RAPHAEL-RSI-002 forensic repository audit by DeepSeek V4.1, 2026-09-19.

**Version precedence:** v4.2 preserves v4/v4.1 locked architecture and governance unless this document explicitly changes a phase requirement. The v4.1 amendments remain normative. RSI additions are an extension of P4–P10, not a renumbering or replacement of the phase spine.

**Current execution state (2026-09-19):**
- Repository audited: `/home/yaser/external-audits/raphael-2`.
- Audit HEAD: `3b2e22db3d952622150d271c12c41d9ed21e81fd`.
- Branch: `weld-sub10-evidence`.
- Working tree was dirty at audit time.
- **AM-4-R3: NOT EXECUTED.**
- **G3: BLOCKED / NOT PASSED.**
- **RSI implementation: NOT STARTED.**
- **Next engineering action: execute AM-4-R3; do not begin RSI implementation before G3 passes.**

**Baseline:** Historical audit baseline was `The-Despicable/raphael-2.0-rbsv2r` at `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`. This is **not** assumed to be the current baseline. P0 establishes the true baseline.

**Source synthesis:** This roadmap combines the architecture decisions from the GLM review with the repository-grounded execution detail from the HackerAI review. The resulting rules supersede earlier roadmap wording when this document is more specific.

---

## 0. EXECUTIVE SUMMARY

Raphael currently contains two internally divergent architectural realities: a live/minimal Head 1 under `src/raphael/` and a deeper cognitive system under `src/orchestrator/` that is heavily tied to the arena. The project direction is to produce **one Raphael** rather than a federation of systems. The canonical cognitive machinery comes from Head 2; the useful operator-facing shell and selected live Head-1 organics are absorbed into a new production runtime.

The final architecture is:

```text
                         OPERATOR
                            |
                            v
                    +----------------+
                    |   CLI / Face   |
                    +-------+--------+
                            |
                            v
                 +---------------------+
                 |  RaphaelRuntime     |
                 |  thin sequencer     |
                 |  ordering + halt    |
                 +----+-----------+----+
                      |           |
          stage calls |           | stage calls
                      v           v
                  COGNITION     BROKER (PDP)
                      |             |
          +-----------+             v
          |                     EXEC/PEP
          |                        |
          v                    Sandbox
      WorldModel                  |
      Student                     v
      Planner                 Capability
      Falsification                |
                                   v
                              EvidenceReceipt
                                   |
                                   v
                              WorldModel
                                   |
                                   v
                              Replan / Learn
```

The canonical loop is:

```text
observe
  -> understand
  -> generate candidates
  -> plan
  -> authorize
  -> execute
  -> collect evidence
  -> update WorldModel
  -> falsify / check contradictions
  -> replan
  -> learn (post-MVP)
  -> repeat / terminate
```

The execution program is split into two lanes:

```text
GLM architecture contract
        |
        v
HackerAI / Minimax / OMP implementation
        |
        v
automated tests + runtime proof
        |
        v
GLM adversarial review
        |
   +----+----+
   |         |
 PASS       FAIL
   |         |
 next      remediation
 phase
```

The most important sequencing rule is **born-gated execution**: the new Runtime must use `Broker.authorize -> PEP` from its first usable execution path. A temporary compatibility seam may exist only around legacy paths; it is never part of the canonical Runtime.

The MVP is a **walking skeleton at G3**. It proves the architecture with minimal depth. It does not require Decepticon, full Student learning, full arena parity, full evaluation, or broad capability expansion.

## 0.1 v4.2 RSI amendment — executive position

The RSI research does **not** justify calling current Raphael recursively self-improving. The repository audit found a governed execution skeleton plus partial learning-related fragments, but no canonical experience → diagnosis → candidate → evaluation → acceptance → persistence → successor loop.

The updated roadmap therefore adopts a staged target:

```text
P3 / G3
  |
  v
P4  durable improvement substrate
  |
  v
P5  diagnosis + exploration policy
  |
  v
P6  learner-conditioned acquisition + bounded learning
  |
  v
P7  governed deployment + rollback
  |
  v
P8  replay + protected holdout + recursive evaluation
  |
  v
P9  lifecycle / consolidation
  |
  v
P10 L5 admission / recursive improvement mechanism
```

**Critical architectural rule:** this does not create a second production Runtime or a second autonomous cognitive loop. The secure task loop remains the sole canonical Runtime loop. The improvement workflow is a governed meta-level process that proposes, evaluates, accepts/rejects, and versions improvements to an explicitly bounded evolvable surface.


---


## 0.2 v4.1 governance inheritance — mandatory

The v4.1 arbitration layer remains incorporated. Its amendments are summarized here so the consolidated v4.2 roadmap does not depend on an external mental merge.

| Amendment | Normative effect in v4.2 |
|---|---|
| AM-1 | Halt-and-re-derive whenever an audit reference shifts; P3.0 re-inventory is mandatory before relying on stale bypass maps. |
| AM-2 | Contradiction predicate and epistemic cleanup are explicit prerequisites to P5. |
| AM-3 | P7a arena divergence tracking is continuous from G2 onward; it is not a late one-time adapter task. |
| AM-4 | Migration seam has a positive interface, closed legacy sites require genuine Broker/PEP routing plus deletion of the legacy branch, and G3 requires the full P3-confirmed weld set. |
| AM-5 | T3MP3ST-derived concepts require a pattern-provenance ledger; P4 types are not complete until relevant ledger entries exist. |
| AM-6 | Test floor is monotonic for retained behaviour; weakening/skipping/xfailing kept-code tests outside P9 atomic deletion is evidence tampering and an automatic gate failure. |
| AM-7 | Every invariant has an activation phase and explicit advisory/build-breaking state; static/dynamic/data controls cannot remain "eventual" requirements. |
| AM-8 | Every phase, including P0, requires the global Evidence Package schema with an explicit scope-deviations field. |
| AM-9 | Risk Register is a standing governance artifact and gains phase-specific risks as evidence reveals them. |
| AM-10 | Final-decision / do-not-implement-yet material remains authoritative; navigation improvements do not alter authority. |
| AM-11 | One implementation phase at a time; permitted parallel tracks are constrained and baseline drift triggers re-verification. |
| AM-12 | Neither lane may silently amend the other's authority; conflicts stop the task and escalate. |
| AM-13 | Editorial fixes are adopted, including file-access boundary wording, bootstrap-v0 for P2, P1 seam restoration, paired-run wording, G7/G8 evaluation wording, epistemic permission wording, and P0 environment-vs-code-edit boundary. |
| AM-14 | P5 receives a P3-grade pre-execution task matrix and its contradiction predicate / coupling contract before implementation starts. |

The consolidated roadmap is the actionable document. This table records the v4.1 inheritance; it does not reopen those decisions.

# 1. OPERATING DOCTRINE

## 1.1 One roadmap, two lanes

There is one source of truth. GLM and the implementation agent do not maintain competing roadmaps.

### GLM owns

- final architecture
- invariants
- interface contracts
- security model
- phase acceptance criteria
- test intent
- proof standards
- scope control
- gate decisions
- adversarial review
- escalation decisions when implementation reality conflicts with architecture

### HackerAI / Minimax / OMP owns

- repository discovery
- file-level mapping
- implementation mechanics
- migrations
- refactors within the architecture contract
- test implementation
- tool execution
- debugging
- runtime probes
- evidence collection
- git commits
- reporting scope deviations

### Mutual-constraint rule

Neither lane may unilaterally amend the other's authority. The implementation agent may not amend architecture invariants, interface contracts, or phase acceptance criteria; on conflict it halts the affected task and escalates rather than silently reinterpreting the contract. GLM may not dictate file-level mechanics when the existing implementation satisfies the architectural contract. Silent amendment by either lane invalidates the affected gate and requires revert-and-redo.

### Automated infrastructure owns

- mechanical invariants
- regression execution
- import-graph checks
- static execution-path checks
- receipt/linkage checks
- deterministic runtime proofs where feasible

GLM is the final gate authority, but **passing tests alone never constitutes a gate pass**.

---

## 1.2 Task taxonomy

Every task in every phase is one of three types.

### A — Architecture task

Written and owned by GLM.

Examples:
- define the Runtime stage contract
- define what an EvidenceReceipt must contain
- define the Broker/PEP boundary
- define an allowed/denied action matrix

### B — Implementation task

Owned by the implementation agent.

Examples:
- modify `action.py`
- introduce `RaphaelRuntime`
- wire a capability through Broker
- add a test
- migrate an arena driver

### C — Proof / Disproof task

Shared between automation, implementation agent, and GLM.

Examples:
- demonstrate direct subprocess execution is blocked
- demonstrate an unprovenanced WorldModel claim is rejected
- demonstrate Runtime and arena use the same Runtime object
- demonstrate Student cannot mutate WorldModel

---

## 1.3 Universal phase lifecycle

Every phase follows this lifecycle.

```text
READY
  |
  v
GLM CONTRACT
  |
  v
IMPLEMENTATION
  |
  v
AUTOMATED PROOF
  |
  v
EVIDENCE PACKAGE
  |
  v
GLM ADVERSARIAL REVIEW
  |
  +----> PASS -> next phase
  |
  +----> FAIL -> remediation -> proof -> review
```

No phase is complete merely because its code exists.

---

# 2. LOCKED ARCHITECTURAL DECISIONS

These are closed unless an explicit superseding ADR is created.

| ID | Decision |
|---|---|
| L1 | One Raphael, one repository identity, one canonical Runtime, one canonical cognitive loop. |
| L2 | Head 2 (`src/orchestrator/brain/`) is canonical for cognition; Head 1 is not retained as a sibling cognitive architecture. |
| L3 | Head 1's useful operator-facing and runtime-supporting organics may be absorbed into the canonical Runtime; its old internal loop is superseded. |
| L4 | `RaphaelRuntime` is a thin sequencer. It owns stage order, termination, and stage contracts, not domain logic. |
| L5 | Broker is the Policy Decision Point (PDP). It decides allow/deny and constraints. |
| L6 | `exec/` is the Policy Enforcement Point (PEP). It is the only package permitted to hold process/network/file primitives. |
| L7 | Sandbox is a PEP enforcement mechanism. Capabilities execute under it and cannot self-authorize. |
| L8 | Runtime execution is Broker-mediated from the first usable Runtime commit. No Runtime-wide OFF mode exists. |
| L9 | Legacy behavior-parity seam exists only as migration scaffolding around pre-existing legacy paths and is removed after migration. |
| L10 | T3MP3ST is a pattern source only. No AGPL source is incorporated without a new explicit legal ADR. |
| L11 | Decepticon is selectively absorbed only for execution/sandbox/capability infrastructure, post-MVP and off the critical path. |
| L12 | Student may generate candidates and later update its own bounded strategy state; Student never writes WorldModel beliefs. |
| L13 | Assertions are not Findings. Evidence must be provenance-linked. |
| L14 | Falsification is the only subsystem permitted to promote/demote epistemic classes. |
| L15 | Arena is a driver/scorer/environment layer, not a second brain. |
| L16 | Repository cleanup follows replacement proof. Delete late, atomically, and only after zero-reference proof. |
| L17 | `NOT_IMPLEMENTED` capabilities are not implemented merely because they exist. They require evaluation-backed justification. |
| L18 | No new cognitive loop stages without a superseding ADR. |
| L19 | The baseline test floor is whatever P0 actually records, not a historical test count. |
| L20 | Every phase produces an Evidence Package; no package means no gate review. |
| L21 | RSI is a governed improvement workflow around the canonical Runtime, not a second Runtime, second brain, or second production loop. |
| L22 | The improvement control surface is split into **protected** and **evolvable** classes; protected surfaces are never self-modifiable. |
| L23 | Structured improvement experience is distinct from EvidenceRecord provenance and from mission-scoped WorldModel belief state. |
| L24 | A replay simulator must replay recorded history/state and outcomes; deterministic scenario regeneration is not sufficient, and textual history injection is not replay. |
| L25 | Replay-selected candidates are not deployable from replay evidence alone; protected unseen/holdout evaluation is required before promotion. |
| L26 | Every accepted improvement has immutable identity, content hash, parent/supersedes lineage, evidence, evaluation, acceptance, deployment, and rollback metadata. |
| L27 | Cross-mission durable state is limited to explicitly governed improvement/experience state; WorldModel belief persistence is not assumed merely because storage exists. |
| L28 | Structural recursion and effective recursion are separate claims and require separate evidence. |
| L29 | RAPHAEL does not claim L2/L3/L4/L5 until the corresponding admission tests pass under matched-resource, independently evaluated conditions. |

---

# 3. CURRENT-STATE MODEL TO PRESERVE AND CORRECT

The following facts are treated as **audit-derived hypotheses until P0 re-verifies them against the chosen checkout**.

## 3.1 Architectural split

### Head 1 — `src/raphael/`

Known historical characteristics:

- live CLI/operator-facing surface
- `RaphaelOrganism`-style shell/runtime behavior
- simple Planner → Executor → State flow
- EventBus / Blackboard / related organics
- `techniques/`
- `models/`
- `limbic/parallel_recon`
- duplicate/dormant cognitive planner code
- execution paths that historically bypassed Broker

Disposition:

- CLI face: keep
- useful organics: selectively absorb
- old loop: deprecate and later remove
- duplicate cognitive machinery: deprecate/remove after reference proof

### Head 2 — `src/orchestrator/`

Known historical characteristics:

- deeper Planner
- WorldModel
- hypothesis/contradiction/falsification machinery
- CapabilityBroker
- Student
- evidence machinery
- mode-specific orchestration
- arena-heavy integration

Disposition:

- cognitive machinery: canonical
- arena coupling: remove
- mode-local execution: fold into Runtime contracts or deprecate
- Broker: keep and universalize

## 3.2 Arena

Historical arena code contains substantial cognitive behavior and evidence logic, including `ablation_runner` and `defeater`-style components.

Final disposition:

- scenario/environment infrastructure: keep
- scoring/metrics: keep
- cognitive orchestration: remove from arena ownership
- Runtime: becomes the subject under test and the common driver

## 3.3 Known historical security gaps to re-verify at P0

Examples from the audit map include:

- Planner self-authorization such as an `allowed=True` shortcut in `orchestrator/brain/action.py`
- commented/unused broker binding in `capability_broker.py`
- Head-1 `_subprocess_fallback` in `raphael/executor/executor.py`
- direct local execution in `kali_tools_client.py`
- direct reverse/SSH capability construction
- divergent phase routing through `modes/autonomous.py`
- hard-coded bridge/path assumptions

These paths are **not to be trusted as exact line references until P0 confirms them**.

---

# 4. TARGET ARCHITECTURE CONTRACT

## 4.1 Runtime responsibility

`RaphaelRuntime` must:

- accept a mission/context input
- own the normative stage order
- invoke stage handlers through explicit contracts
- carry loop state
- enforce termination conditions
- produce/forward runtime trace events
- ensure the execution stage enters Broker/PEP
- coordinate stage outputs

`RaphaelRuntime` must not:

- implement Planner heuristics
- implement policy logic
- import the migration seam
- hold process/network/file primitives
- become a god-object that owns WorldModel internals
- contain arena scoring logic
- embed Student learning algorithms directly

## 4.2 Canonical stage contract

The Runtime implements one canonical loop.

| # | Stage | Required responsibility | MVP depth |
|---|---|---|---|
| 1 | Observe | collect allowed observations through Broker/PEP | minimal |
| 2 | Understand | read WorldModel and contextual state | minimal |
| 3 | Candidate generation | combine Student proposals, heuristics, operator directives | proposal/recording |
| 4 | Plan | Planner transforms candidates into action requests | request-only |
| 5 | Authorize | Broker PDP evaluates mission/scope/action | Scope v0 |
| 6 | Execute | PEP invokes sandbox/capability after approval | one safe capability |
| 7 | Evidence | PEP mints receipt/artifact/provenance data | v1 |
| 8 | Integrate | WorldModel consumes receipt-backed results | minimal |
| 9 | Falsify | detect contradiction / verification requirement | minimal trigger |
| 10 | Replan | adjust next decision when blocked/contradicted/failed | one demonstrated trigger |
| 11 | Learn | Student consumes verified outcomes and later updates strategy | post-MVP |
| 12 | Repeat/terminate | mission completion, budget, scope exhaustion, operator halt | minimal |

The order is normative. Any change requires an ADR.

---

# 5. SECURITY MODEL

## 5.1 PDP / PEP separation

```text
Mission + Scope + ActionSpec
             |
             v
       BROKER / PDP
       allow / deny
       constraints
       decision_id
             |
             v
          EXEC / PEP
       enforcement only
             |
             v
          SANDBOX
             |
             v
        CAPABILITY
             |
             v
       RESULT + ARTIFACT
             |
             v
      PEP-MINTED RECEIPT
```

## 5.2 Universal Broker rule

Everything that touches the environment is in scope for Broker mediation:

- process execution
- shell-like operations
- file access where treated as an environment interaction
- network access
- tool execution
- sandbox invocation
- observation probes
- verification probes used by falsification

There are no "trusted internal stage" exceptions.

Tests may use named policies such as `test-local-v1`, but those are policy artifacts rather than alternate code paths.

## 5.3 Static enforcement

CI must eventually enforce:

- process/network/file primitives only importable from the execution boundary
- no canonical Runtime import of arena
- no canonical Runtime import of migration seam
- no deprecated module imports from canonical modules
- no absolute hard-coded user paths in new runtime code
- Decepticon imports confined to its fenced execution subtree

## 5.4 Dynamic enforcement

Runtime must enforce:

- every ExecutionEvent references a Broker decision id
- missing decision linkage is a failure
- denied actions do not execute
- authorization context is derived from current mission/scope
- direct capability construction cannot create an executable privileged object outside the Broker contract

## 5.5 Data enforcement

The model must enforce:

- execution-derived WorldModel claims require evidence linkage
- receipts are immutable
- artifacts are content-addressed or otherwise integrity-linked
- ledger is append-only
- secret-bearing content is redacted before operator-visible persistence

---

# 6. EPISTEMIC MODEL

Raphael distinguishes five classes.

| Class | Meaning | Can authorize action? |
|---|---|---:|
| Assertion | Model-generated claim/hypothesis | No |
| Observation | Non-mutating observed result | Not directly; may support verification |
| ExecutionResult | Result of an approved action | Evidence candidate |
| Artifact | Stored execution/observation output | Evidence support |
| Finding | Admitted WorldModel state | Yes, subject to mission/scope/policy |

Core rule:

> **Cognition proposes; evidence disposes.**

Student and Planner produce assertions/action proposals. They cannot simply declare a finding. The falsification/verification mechanism controls promotion and refutation.

---

# 7. STUDENT MODEL

Student evolves through five governed levels.

```text
Level 0 — proposal_only
       |
       v
Level 1 — proposals + outcome recording
       |
       v
Level 2 — outcomes linked to receipts / falsification
       |
       v
Level 3 — shadow learning
       |
       v
Level 4 — flagged bounded learning
       |
       v
Level 5 — learner-conditioned experience acquisition
```

Constraints:

1. Student never writes WorldModel beliefs directly.
2. Trusted feedback comes only from evidence-backed receipts and verified/falsified outcomes.
3. Updates are bounded, deterministic, versioned, and resettable.
4. Learning state is externally visible and lineage-linked.
5. Operator can freeze learning and reset learned state.
6. A regression guard protects retained baseline behaviour.
7. Learner-conditioned acquisition can select only admissible experience/tasks within mission, scope, resource, and operator constraints.
8. Student cannot deploy policy versions; promotion remains a separate governed function.

Student is a candidate/learning component, not a second orchestrator and not a belief authority.

# 8. T3MP3ST PATTERN BOUNDARY

No T3MP3ST source is copied by default.

| T3MP3ST concept | Native Raphael concept | Intent |
|---|---|---|
| Mission | `MissionSpec` | operator intent and task envelope |
| Scope | `Scope` | target/resource/action constraints |
| Authorization Context | derived `AuthorizationContext` | why/how/for-whom an action is permitted |
| Evidence receipt | `EvidenceReceipt` | execution-attributable result |
| Artifact reference | `ArtifactRef` | link to stored output |
| Provenance | `ProvenanceRecord` | mission → authorization → execution → artifact → claim |
| Finding verification | falsification / promotion engine | move claims into trusted state |
| Operator visibility | `MissionLedger` / `DecisionTrace` | auditable operator surface |

These are Raphael-owned types, names, tests, and documentation.

---

# 9. DECEPTICON BOUNDARY

Decepticon is not a second agent architecture.

## Allowed post-MVP absorption

- sandbox/process isolation core
- capability/tool registry patterns
- output capture
- execution result normalization
- selected task-oriented execution infrastructure
- optional skill-source patterns if evaluated later

## Rejected

- orchestration
- agent loop
- LLM prompting architecture
- mission/planning ownership
- system identity
- multi-agent peer structure
- provider fallback as a required core path

The integration boundary is:

```text
Raphael Broker
      |
      v
Raphael exec/PEP
      |
      v
Decepticon-derived execution component
```

Decepticon never controls the Runtime, Planner, Student, WorldModel, or mission policy.

---

# 10. PHASE SPINE

```text
P0  Re-anchor baseline                         G0
 |
v
P1  Architecture + migration scaffolding      G1
 |
v
P2  Born-gated Runtime walking skeleton       G2
 |
v
P3  Universal Broker closure + MVP             G3 / MVP
 |
v
P4  Mission / Scope / Evidence + RSI substrate G4
 |
v
P5  WorldModel / Falsification / Replan +      G5
|   diagnosis / exploration policy
v
P6  Student shadow -> bounded learning +       G6
|   learner-conditioned acquisition
v
P7  Arena / RedTeam parity + governed           G7
|   deployment adaptation / rollback
v
P8  Evaluation + replay / holdout / recursive   G8
|   improvement assessment
v
P9  Consolidation / deletion + learned-state    G9
|   lifecycle
v
P10 Advanced capabilities + L5 recursive         G10
    improvement admission
```

Parallel tracks:

- P7a arena adapter preparation may begin after G2, provided it does not become a second cognitive loop and does not weaken the frozen arena measurement boundary.
- Decepticon investigation/license/dependency work may begin as a planning track early, but integration remains post-MVP and execution-only below the Broker.
- Evaluation-protocol design may begin during P5, but measured candidate-promotion claims belong to P8 after G7 conditions are satisfied.
- No RSI implementation work begins before G3.

# 11. PHASE P0 — RE-ANCHOR / BASELINE / REPRODUCIBILITY

**Gate:** G0

**Primary objective:** establish the actual repository state before any behavior-changing work.

## 11.1 Why P0 exists

The historical audit and the live repository had drifted. Historical test counts such as 239 cannot be treated as today's floor without reproducing them. File/line references from the audit may have moved. P0 therefore converts historical facts into verified facts or marks them stale.

## 11.2 GLM Contract

GLM must define:

- the rule for selecting the canonical checkout
- what evidence is required to call the baseline reproducible
- what constitutes a baseline regression
- the inventory schema for execution paths
- the classification of each audit claim as CONFIRMED / SHIFTED / ABSENT / UNKNOWN

Canonical checkout rule:

1. Prefer current `main` if it is runnable and reproducible under a documented environment.
2. Use the audit baseline only if current `main` cannot be made runnable without behavior-changing fixes that would invalidate the baseline decision.
3. Never mix files from different commits when establishing P0.

## 11.3 HackerAI / Minimax / OMP Tasks

### P0.1 — Repository identity

- fetch relevant refs
- record current HEAD
- record audit HEAD
- produce commit graph delta
- identify whether the working tree is clean
- create a dedicated baseline branch/tag

Expected artifact:

`docs/BASELINE.md`

### P0.2 — Environment inventory

Record:

- OS
- Python version
- declared Python constraint
- package manager state
- lockfile state
- required/missing dependencies
- environment variables needed to run tests
- symlink assumptions
- hard-coded path assumptions

Do not repair code in this task.

### P0.3 — Test floor

Run the complete available test suite from a clean environment if possible.

Record:

- total tests
- passed
- failed
- skipped
- warnings
- duration
- exact command
- environment fingerprint

The result becomes:

`FLOOR(P0)`

### P0.4 — Runtime probes

Re-run historically reported probes only to determine whether those claims still hold.

Examples:

- Student proposal-only behavior
- autonomous/recon path behavior
- existing arena entry behavior

Record actual outputs. Do not infer them from source.

### P0.5 — Execution-path inventory

Discover all reachable environment-touching paths from:

- CLI
- Runtime candidates
- arena
- autonomous/modes
- capability constructors
- local subprocess helpers
- network helpers
- sandbox calls

For each path record:

| Field | Required |
|---|---|
| Path ID | yes |
| File/function | yes |
| Entry caller | yes |
| Primitive touched | yes |
| Broker involvement | yes/no |
| Reachability | live/dead/unknown |
| Planned disposition | close/retain/deprecate |

### P0.6 — Audit-reference verification

Re-check historically cited locations, including known candidates such as:

- Planner self-authorization
- CapabilityBroker binding
- Head-1 subprocess fallback
- Kali local subprocess path
- reverse/SSH constructors
- autonomous phase routing
- bridge hard-coded paths

Every citation becomes one of:

`CONFIRMED`, `SHIFTED`, `ABSENT`, `UNKNOWN`.

### P0.7 — Deletion inventory seed

Inventory:

- duplicate planners
- dormant brain modules
- alternate entry points
- bridge
- legacy CLI
- old arena orchestration
- `NOT_IMPLEMENTED` executors
- stale documentation
- historical reports/artifacts

Do not delete.

## 11.4 Automated Proof

P0 is proof-only. No new behavior.

Required evidence:

- chosen HEAD
- reason for choice
- exact `FLOOR(P0)`
- exact environment manifest
- runtime probe transcripts
- execution-path inventory
- stale-reference status table
- deletion inventory

## 11.5 G0 Gate

PASS only when:

- canonical checkout is selected and immutable
- actual test floor is recorded
- no historical count is presented as current truth without reproduction
- execution paths are inventoried
- file/line references have been re-verified
- no code behavior was changed
- Evidence Package exists

**Failure:** return to P0. Do not start P1 while the baseline is ambiguous.

## 11.6 Rollback

None required beyond branch/tag reset because P0 is non-behavioral.

---

# 12. PHASE P1 — ARCHITECTURE FREEZE + MIGRATION SCAFFOLDING

**Gate:** G1

**Objective:** make the new architecture explicit before behavior changes begin, and provide a temporary migration seam only around legacy paths.

## 12.1 GLM Contract

Define and approve:

- canonical head decision
- Runtime stage contracts
- PDP/PEP split
- born-gated rule
- migration seam rules
- epistemic taxonomy
- no-second-entry-point policy
- T3MP3ST pattern-only rule
- Decepticon post-MVP boundary
- deprecation policy

## 12.2 ADR set

Recommended ADRs:

- ADR-001 Canonical architecture
- ADR-002 RaphaelRuntime
- ADR-003 Broker PDP / PEP separation
- ADR-004 Born-gated Runtime
- ADR-005 Legacy migration seam
- ADR-006 No second cognitive entry point
- ADR-007 T3MP3ST pattern-only posture
- ADR-008 Decepticon fenced post-MVP integration
- ADR-009 Epistemic taxonomy
- ADR-010 Falsification as claim promotion engine

## 12.3 HackerAI / Minimax / OMP Tasks

### P1.1 — Add architecture documentation

Create/update canonical architecture docs.

The docs must clearly identify:

- canonical Runtime
- canonical brain components
- deprecated components
- execution boundary
- arena role

### P1.2 — Deprecation markers

Mark, where P0 verifies them:

- legacy Head-1 internal loop
- AdaptiveBrain
- duplicate planner
- dormant cognitive stubs
- alternate orchestration entry points
- `NOT_IMPLEMENTED` executors

Do not remove them.

### P1.3 — Migration seam

Implement a seam that can wrap **only existing legacy call sites**.

Rules:

- OFF = legacy delegation
- ON = Broker/policy-mediated behavior
- seam can never be imported by canonical Runtime
- seam has owner + removal ticket
- seam is temporary

A candidate implementation name such as `BehaviorAlterableGate` is acceptable; the final location is an implementation decision constrained by the architecture contract.

### P1.4 — Reference inventory

Create a living inventory for:

- `api/`
- `modes/`
- `agent/`
- duplicate CLI
- bridge
- old arena loop
- dormant Student modules

### P1.5 — CI architecture guardrails

Introduce initial checks for:

- imports from deprecated modules
- Runtime → arena dependency
- Runtime → seam dependency
- execution primitive imports outside intended boundary
- absolute paths in new Runtime code

## 12.4 Tests

Minimum test set:

- `test_behavior_neutral_gate_off`
- `test_import_graph_single_runtime`
- deprecated-import check
- seam cannot be imported by Runtime
- gate ON denies unapproved operation

## 12.5 Runtime proof

Run an existing legacy path with seam OFF and demonstrate behavior parity.

Run seam ON with a named test policy and demonstrate a policy decision is observable.

No new Runtime yet.

## 12.6 G1 Gate

PASS requires:

- ADRs merged
- seam parity proven
- canonical Runtime contract approved
- import rules active
- no behavior regression relative to `FLOOR(P0)`
- deletion inventory live

## 12.7 Must not happen

- Runtime implementation
- arena rewiring
- capability expansion
- physical deletion
- Student learning
- Decepticon vendoring

---

# 13. PHASE P2 — BORN-GATED RAPHAEL RUNTIME WALKING SKELETON

**Gate:** G2

**Objective:** build the smallest real Runtime with a canonical loop and Broker-mediated execution from its first usable commit.

## 13.1 GLM Contract

`RaphaelRuntime` must:

- own sequence and termination
- call stage handlers
- have no domain logic
- have no policy logic
- have no migration-seam dependency
- enter Broker/PEP for EXECUTE
- expose a stable trace interface

The Runtime uses Head 2 organs as handlers rather than rewriting their internal logic.

## 13.2 Runtime interface

At minimum, define conceptual contracts for:

```text
RuntimeContext
MissionContext
StageResult
ActionRequest
PolicyDecision
ExecutionEvent
EvidenceReceipt
LoopTermination
```

Exact Python class names may change during implementation, but behavior and ownership must remain consistent.

## 13.3 HackerAI / Minimax / OMP Tasks

### P2.1 — Runtime skeleton

Create a new Runtime layer, preferably under an architecture-consistent namespace such as `orchestrator/runtime/`.

Runtime responsibilities:

- initialize context
- execute stage sequence
- capture stage outputs
- terminate cleanly
- emit trace

Do not place Planner/WorldModel implementation code into Runtime.

### P2.2 — Wire stage handlers

Wire minimal handlers for:

- observation
- WorldModel read
- Student candidate generation in recording mode
- Planner request generation
- Broker call
- PEP invocation
- receipt emission
- minimal WorldModel integration
- minimal contradiction/failure trigger
- replan

### P2.3 — Broker-mediated mock path

The first Runtime execution path must be:

```text
Runtime
 -> Broker.authorize
 -> PEP
 -> mock capability
 -> ExecutionEvent
 -> EvidenceReceipt
```

### P2.4 — Safe proving capability

Add exactly one low-risk, deterministic, Raphael-native capability.

Prefer a capability that:

- has deterministic output
- has no external network requirement
- can be run inside a local fixture
- clearly demonstrates receipt generation

A read-only fixture inspection or equivalent is acceptable.

### P2.5 — CLI entry

Wire the operator-facing CLI to invoke Runtime for a one-iteration run.

The legacy Head-1 loop may remain available only through a separately documented migration path; the canonical Runtime must not invoke it.

### P2.6 — Trace

Produce a minimal `DecisionTrace` that shows:

- stage
- candidate/request
- policy decision
- execution linkage
- receipt id
- next-stage outcome

### P2.7 — Arena oracle

Record the historical arena stage sequence as a behavioral oracle.

Do not copy arena orchestration into Runtime.

## 13.4 Tests

Minimum:

- `test_import_graph_single_runtime`
- `test_runtime_executes_via_broker`
- `test_receipt_minted_by_pep`
- `test_runtime_has_no_seam_dependency`
- `test_runtime_stage_order`
- `test_head1_loop_not_used_by_runtime`

## 13.5 Runtime proof

One command should demonstrate:

```text
CLI
 -> Runtime
 -> observe
 -> candidates
 -> plan
 -> Broker
 -> PEP
 -> safe capability
 -> receipt
 -> WorldModel integration
 -> trace
```

Use a deterministic fixture.

## 13.6 G2 Gate

PASS only if:

- Runtime is demonstrably a sequencer
- execution is broker-mediated from first Runtime execution
- no Runtime seam import exists
- one safe capability completes successfully
- trace is emitted
- architecture import graph is correct
- `FLOOR(P0)` remains intact
- Evidence Package exists

## 13.7 Must not happen

- direct Runtime subprocess
- Runtime OFF mode
- arena rewiring into Runtime
- Decepticon
- full Student learning
- repo cleanup
- new capabilities

---

# 14. PHASE P3 — UNIVERSAL BROKER CLOSURE + MVP

**Gate:** G3

**Milestone:** **MVP**

This phase closes the legacy bypasses and turns the walking skeleton into a provable minimal Raphael.

## 14.1 GLM Contract

The final production rule is:

```text
Planner proposes
Broker decides
PEP enforces
Capability executes
PEP mints evidence
```

No production execution can bypass the Broker.

## 14.2 Bypass closure task matrix

All paths below are `[REVERIFY]` until P0 confirms them.

| Task | Historical candidate | Required outcome |
|---|---|---|
| P3.1 | Planner authorization shortcut | Planner becomes request-only |
| P3.2 | Head-1 subprocess fallback | Broker/PEP mediated or removed |
| P3.3 | Kali local subprocess path | Broker/PEP mediated |
| P3.4 | Reverse/SSH constructors | require Broker-issued execution context |
| P3.5 | ExecutionEngine binding | execution requires explicit Broker decision |
| P3.6 | Autonomous phase routing | no mode-local execution outside Broker |
| P3.7 | Observation/probe paths | Broker mediated |
| P3.8 | Static execution invariant | CI blocks new bypasses |
| P3.9 | Dynamic bypass suite | deliberate bypass attempts fail |

## 14.3 Scope v0

Implement the minimum mission/scope model required to prove authorization.

At minimum:

- mission identifier
- authorized targets/resources
- allowed action class
- halt condition
- denial reason
- policy version

Do not build the full long-term mission schema yet.

## 14.4 Native minimal sandbox

The sandbox is Raphael-native for MVP.

Minimum properties:

- controlled working directory
- deterministic resource limits where possible
- timeout
- output limit
- no unintended network access
- explicit artifact collection

The sandbox does not need Decepticon at MVP.

## 14.5 Evidence v1

Receipt must minimally link:

```text
mission
 -> decision
 -> execution
 -> capability
 -> artifact
 -> result
```

Suggested conceptual fields:

- receipt id
- mission id
- action id
- decision id
- capability id
- target/scope reference
- execution status
- timing
- artifact refs
- integrity/hash information
- provenance metadata

## 14.6 WorldModel minimum enforcement

For MVP:

- model assertions remain quarantined
- execution-derived claims require receipt linkage
- unprovenanced execution claims are rejected

Full promotion/demotion semantics remain P5 depth, but the minimum invariant is already enforced.

## 14.7 Minimal replan trigger

MVP needs one real demonstration that evidence can alter the next decision.

The simplest acceptable implementation is a deterministic contradiction/failure trigger where:

```text
Run A: evidence integrated -> next decision changes
Run B: falsification/replan path disabled -> next decision differs
```

The exact cognitive depth is deliberately small.

## 14.8 HackerAI / Minimax / OMP Tasks

### P3.1 — Re-verify all bypasses

Refresh P0 inventory after P2 changes.

### P3.2 — Planner request-only

Remove self-authorization semantics.

Planner returns an action proposal/request. It does not grant permission.

### P3.3 — Close Head-1 subprocess paths

Route reachable execution through Broker/PEP.

Delete the legacy execution branch only once parity/proof exists.

### P3.4 — Close direct tool path

Wrap local execution/tool clients behind the canonical PEP route.

### P3.5 — Gate capability constructors

Ensure privileged capability objects cannot be directly constructed into an executable state without Broker authorization.

### P3.6 — Fix ExecutionEngine ownership

There must be one canonical execution-engine path.

Remove unused duplicate paths only when proven safe.

### P3.7 — Fold/deprecate mode-local execution

Mode-specific orchestration must no longer be able to circumvent the Runtime/Broker contract.

### P3.8 — Static guardrail

Create an AST/import-graph based test such as:

`test_no_unbrokered_execution`

It must search for:

- process primitives
- network primitives
- file/process launches
- known direct execution helpers

outside allowed packages.

### P3.9 — Dynamic bypass tests

Attempt, in tests, to trigger:

- Planner self-authorization
- direct subprocess
- direct capability constructor
- mode-local execution
- observation/probe bypass
- migration seam misuse
- invalid test policy use

Expected behavior: denied/blocked and traceable.

### P3.10 — Native sandbox + safe capability

Implement the minimal local capability and sandbox contract.

### P3.11 — MVP demonstration

Assemble the deterministic one-command proof.

## 14.9 Required tests

- `test_planner_requires_broker`
- `test_no_unbrokered_execution`
- `test_broker_required_error_on_direct_ctor`
- `test_evidence_receipt_linked_artifact`
- `test_runtime_execution_decision_linkage`
- `test_scope_denies_out_of_scope_action`
- `test_replan_changes_next_decision`
- full `FLOOR(P0)` regression

## 14.10 MVP demonstration

A deterministic local mission:

```text
mission file
  -> scope declared
  -> Student + Planner produce candidate/request
  -> Broker authorizes valid action
  -> Broker denies injected out-of-scope action
  -> PEP runs safe capability
  -> receipt + artifact + provenance created
  -> WorldModel accepts evidence-backed state
  -> contradiction/failure triggers replan
  -> Student outcome is recorded
  -> DecisionTrace emitted
```

## 14.11 MVP failure criteria

Any of the following fails MVP:

1. Any Runtime execution event lacks a Broker decision id.
2. Direct execution can bypass Broker.
3. WorldModel accepts an execution-derived claim without evidence linkage.
4. Replan cannot change the next decision.
5. The demonstration cannot reproduce from a clean checkout.
6. A second canonical loop is reachable.
7. A migration seam can ungate the canonical Runtime.
8. The safe capability cannot produce evidence through PEP.

## 14.12 G3 adversarial review

GLM must actively attempt to break the system through:

- Planner self-auth path
- direct capability construction
- direct process execution
- direct probe path
- mode-local execution
- migration seam
- test policy abuse
- missing decision linkage
- fake receipt creation
- WorldModel claim forgery

G3 passes only when these attempts fail according to policy and leave traceable evidence.

---

# 15. PHASE P4 — MISSION / SCOPE / EVIDENCE / PROVENANCE + IMPROVEMENT SUBSTRATE

**Gate:** G4

**Objective:** turn MVP-level mission/scope/evidence scaffolding into a coherent first-class model and establish the durable structures required for later governed improvement. P4 does **not** deploy self-improvement.

## 15.1 GLM Contract

The native model must provide the existing P4 contract plus a separate improvement substrate:

- `MissionSpec`
- `Scope`
- `AuthorizationContext`
- `EvidenceReceipt`
- `ArtifactRef`
- `ProvenanceRecord`
- `MissionLedger`
- `DecisionTrace`
- structured improvement `ExperienceNode`
- versioned `ExplorationPolicy` representation
- successor/lineage metadata

Authorization context is derived per decision and is not a stale cached object.

### Improvement-state separation

```text
MISSION-SCOPED EPISTEMIC STATE
    WorldModel
    Hypotheses
    Contradictions

CROSS-MISSION GOVERNED IMPROVEMENT STATE
    Experience history
    ExplorationPolicy versions
    Candidate metadata
    Evaluation history
    Promotion / rollback history
```

Do not make the WorldModel globally persistent merely because durable storage exists.

## 15.2 Experience model

`ExperienceNode` records the structure required for later replay and improvement diagnosis.

Minimum fields:

```text
node_id
parent_id / branch_id
mission_id
policy_version
pre-decision state reference
candidate/action reference
observation/effect reference
artifact references
evaluator result reference
resource cost
provenance
created_at / ordering metadata
```

`ExperienceNode` is not a replacement for `EvidenceRecord`.

- EvidenceRecord answers provenance/authority questions.
- ExperienceNode answers decision-history/search-tree questions.

The later replay system must be able to reconstruct which action/branch occurred, from which state, with which outcome, under which policy version.

## 15.3 ExplorationPolicy contract

`ExplorationPolicy` is a first-class serialized object, not an implicit code path.

Minimum fields:

```text
policy_id
version
parent_version / supersedes
content_hash
parameters
constraints
motivation
evidence_refs
evaluation_refs
status
created_by
```

Initial scope is limited to bounded exploration behaviour, such as:

- candidate ordering
- breadth/depth preference
- revisit policy
- probe allocation
- bounded parallel-group size
- stopping criteria
- compute allocation

It does not control authorization semantics or protected evaluator logic.

## 15.4 Successor / versioning contract

Every candidate policy version must support:

```text
vN
 |
 +--> candidate vN+1
        |
        +--> evaluation
        |
        +--> acceptance / rejection
        |
        +--> deployment record
        |
        +--> rollback target
```

A version is not accepted merely because it has a higher score in one run.

The successor record must include:

- parent/supersedes
- content hash
- motivation
- supporting experience/evidence
- evaluation references
- acceptance decision
- deployment state
- rollback target/status

## 15.5 P4 Tasks

### P4.1 — Mission model

Implement mission identity, objectives, target envelope, constraints, halt conditions.

### P4.2 — Scope model

Represent allowed targets/resources/action classes declaratively and validate containment.

### P4.3 — Authorization context

Derive context from current Mission + Scope + ActionSpec.

### P4.4 — Receipt persistence

Move ephemeral/in-memory receipts into durable storage.

Requirements:

- survives restart
- integrity-checkable
- traceable to mission/action
- deterministic serialization

### P4.5 — Artifact store

Use minimal content-addressed or hash-linked artifact storage.

### P4.6 — Provenance chain

Implement:

```text
Mission
 -> Authorization
 -> Execution
 -> Artifact
 -> Claim/Finding
```

### P4.7 — Epistemic schema enforcement

Encode Assertion / Observation / ExecutionResult / Artifact / Finding distinctions.

### P4.8 — Ledger

Append-only operator ledger.

### P4.9 — Redaction

Ensure secrets/sensitive outputs are not written directly into operator-visible ledger content.

### P4.10 — CLI visibility

Render mission, scope, authorization, denials, executions, evidence, provenance, contradictions, and replans.

### P4.11 — ExperienceNode store

Add the minimal durable representation for structured decision history. Do not implement policy optimization yet.

### P4.12 — ExplorationPolicy store

Add serialization, validation, content hashing, and parent/supersedes lineage. The loader must not silently ignore declared lineage metadata.

### P4.13 — Protected/evolvable surface registry

Publish a machine-readable registry of what improvement mechanisms may and may not modify.

## 15.6 Protected vs evolvable surface

### PROTECTED — never self-modifiable

```text
CapabilityBroker / PDP
authorization semantics
exec/ PEP
process/network/file authority
Evidence identity + provenance authority
single Runtime
single production loop
WorldModel belief authority
protected evaluator / holdout rules
promotion gate
human release authority
```

### EVOLVABLE — only through the governed improvement workflow

```text
ExplorationPolicy
candidate-generation policy
bounded strategy parameters
prompt/context assembly
knowledge weighting
experience-selection policy
```

The registry itself is protected. Evolving a policy cannot rewrite the registry.

## 15.7 Tests

Existing P4 tests plus:

- `test_experience_node_persists`
- `test_experience_parent_child_lineage`
- `test_policy_successor_lineage`
- `test_policy_content_hash`
- `test_protected_surface_rejected`
- `test_evolvable_surface_registry`
- `test_persistence_across_restart`
- `test_evidence_receipt_linked_artifact`
- `test_claim_verified_vs_model_asserted`
- `test_redaction_no_secrets_in_ledger`
- `test_authorization_context_derived_per_decision`

## 15.8 Runtime proof

Run a mission, terminate the process, restart, load receipts and experience records, and demonstrate:

- evidence survives
- provenance resolves
- experience ordering/parentage resolves
- policy identity and lineage resolve
- mission-scoped WorldModel can be reconstructed from authoritative evidence
- protected/evolvable surface is machine-visible
- ledger remains internally consistent

## 15.9 G4 Gate

PASS requires:

- mission/scope actually enforced
- receipts persist
- provenance machine-verifiable
- assertions cannot silently become findings
- ledger complete and redacted
- ExperienceNode durable and lineage-valid
- ExplorationPolicy object exists with stable identity/hash/lineage
- protected/evolvable boundary is explicit and enforced
- no candidate improvement is deployed yet
- no AGPL source incorporated

---

# 16. PHASE P5 — WORLDMODEL / FALSIFICATION / REPLANNING + DIAGNOSIS / EXPLORATION

**Gate:** G5

**Objective:** make Raphael's cognitive machinery materially influence future decisions and establish the diagnostic machinery that can later propose improvements without modifying protected surfaces.

This remains the core cognition phase. It now also establishes the meta-level diagnosis boundary required by RSI.

## 16.1 Architectural principle

Use existing substantial machinery wherever possible. The default is:

```text
promote + decouple + rewire
```

not:

```text
rewrite everything
```

## 16.2 GLM Contract

Falsification is the only component allowed to move claims between epistemic classes.

At minimum:

```text
Assertion --verification--> Finding
Finding --contradiction--> Refuted/invalidated
```

A contradiction must have decision consequences.

### Meta-level diagnosis rule

Task diagnosis and improvement diagnosis are different:

```text
TASK DIAGNOSIS
Why did this mission decision fail?

IMPROVEMENT DIAGNOSIS
Which bounded, evolvable mechanism appears responsible for the repeated limitation?
```

The second output is an `ImprovementHypothesis`, never an automatic code change.

## 16.3 HackerAI / Minimax / OMP Tasks

### P5.1 — P5 re-inventory

Before implementation, re-inventory historical defeater/arena coupling and verify which modules are truly reachable from canonical Runtime after P4.

### P5.2 — Promote defeater logic

Historical `arena/defeater.py`-type logic may be decoupled from arena ownership.

Do not copy scenario/scoring machinery with it.

### P5.3 — WorldModel claim matching

Implement comparison between existing Findings and new receipt-backed observations/results.

### P5.4 — Contradiction detector

Create deterministic contradiction conditions suitable for testing.

### P5.5 — Falsification stage

Make falsification an explicit Runtime stage handler.

### P5.6 — Replan hook

Planner receives a clear reason for replanning:

- contradiction
- verification failure
- execution failure
- denial that changes feasible options

### P5.7 — Paired-run harness

Run identical seeded scenarios with falsification/replanning ON vs OFF and compare the next decision trace.

### P5.8 — Promotion/demotion schema

Only the verification/falsification authority may change epistemic class.

### P5.9 — Cross-component diagnosis

Create a bounded diagnoser that can consume evidence, execution outcomes, WorldModel contradictions, and planner behaviour to emit an `ImprovementHypothesis` referencing evidence rather than making a change directly.

Minimum hypothesis fields:

```text
hypothesis_id
observed_limitation
affected_surface
supporting_experience_refs
expected_effect
risk/constraints
candidate_policy_delta
status
```

### P5.10 — ExplorationPolicy decision interface

Expose a deterministic, serializable policy interface that decides only among bounded exploration parameters. It must not perform environment execution or authorization.

### P5.11 — Exploration traceability

Every policy decision records which policy version produced it and what bounded parameters were active.

### P5.12 — Advisory rollback mode

If needed during development, permit advisory-only falsification rollback behaviour, but it must be feature-flagged, owner-assigned, and removed or made unnecessary after validation.

## 16.4 ChainSynthesizer decision

Audit indicated a historical path where `runner.chain_synthesizer` was referenced but not populated. Decide honestly:

- fix it as a real Runtime dependency, or
- prove it unused and remove/deprecate later.

Do not leave silent dead references in the canonical path.

## 16.5 Tests

- contradiction unit tests
- promotion/demotion unit tests
- no-receipt claim rejection
- `test_contradiction_changes_next_decision`
- paired-run deterministic divergence
- claim-forgery adversarial test
- `test_improvement_hypothesis_is_evidence_linked`
- `test_policy_decision_is_versioned`
- `test_protected_surface_not_targetable_by_diagnoser`

## 16.6 Runtime proof

Task cognition proof remains:

```text
Initial assumption / Finding
        |
        v
new verified observation contradicts it
        |
        v
falsification
        |
        v
planner receives changed state
        |
        v
next decision differs
```

Meta-level proof remains non-deployment-only:

```text
repeated limitation
      |
      v
cross-component diagnosis
      |
      v
ImprovementHypothesis
      |
      v
bounded policy delta proposal
```

The hypothesis must not directly mutate Runtime, Broker, PEP, or evaluator code.

## 16.7 G5 Gate

PASS requires:

- full falsification logic reachable from Runtime
- no arena-only cognitive dependency for this path
- only falsification can promote/demote claim classes
- paired-run divergence proven
- GLM claim-forgery attack fails
- cross-component diagnosis emits evidence-linked hypotheses
- ExplorationPolicy is a first-class bounded decision object
- diagnosis cannot target protected control surfaces
- no autonomous improvement deployment occurs in P5

---

# 17. PHASE P6 — STUDENT SHADOW → BOUNDED LEARNING + LEARNER-CONDITIONED ACQUISITION

**Gate:** G6

**Objective:** activate Student as a controlled learner only after verified outcomes exist and make experience acquisition itself a bounded, inspectable policy rather than an ungoverned side effect.

## 17.1 GLM Contract

Learning must be evidence-driven, bounded, resettable, optional, and versioned.

### Learning ladder

```text
Recording
   |
   v
Outcome-linked
   |
   v
Shadow learning
   |
   v
Flagged bounded learning
   |
   v
Learner-conditioned acquisition
```

The final step means the learner can choose which admissible experience/tasks to acquire next within explicit mission/resource constraints. It does not mean arbitrary environment access.

Learning is not ON by default merely because code exists.

## 17.2 HackerAI / Minimax / OMP Tasks

### P6.1 — Student path activation

Remove historical forced `proposal_only` behaviour only where the Runtime path genuinely exists.

Do not activate disconnected Student subsystems wholesale.

### P6.2 — Feedback bus

Connect:

```text
EvidenceReceipt
   +
FalsificationResult
   +
EvaluationResult
   |
   v
Student feedback input
```

### P6.3 — Strategy delta journal

Record proposed changes before applying them.

### P6.4 — Shadow mode

Compute learning updates but do not apply them.

Demonstrate that the system can calculate a change without altering behaviour.

### P6.5 — Bounded learning

Implement deterministic update functions with:

- per-episode caps
- explicit allowed parameter set
- explicit maximum delta
- no uncontrolled recursive self-modification

### P6.6 — State persistence

Learned state must be:

- versioned
- inspectable
- resettable
- wipeable
- lineage-linked

### P6.7 — Freeze/reset

Provide an operator-visible control to freeze learning and reset to `proposal_only`.

### P6.8 — Experience-selection policy

Allow Student to recommend which admissible experience/task should be acquired next, subject to:

- Mission/Scope bounds
- resource budget
- operator halt
- protected evaluation constraints
- no direct privileged execution

### P6.9 — Learning provenance

Every learned delta links to the exact verified outcomes and experience nodes that produced it.

### P6.10 — Candidate staging

All learned candidates enter a staging state before any promotion mechanism can consume them.

## 17.3 Student invariants

Student cannot:

- write WorldModel Findings directly
- alter Broker policy
- change Runtime stage order
- create privileged capabilities
- use model self-assessment as trusted outcome
- bypass mission/scope to acquire experience
- deploy an unevaluated policy version

## 17.4 Tests

- `test_student_candidate_reaches_planner_broker`
- `test_student_receives_outcome`
- `test_student_changes_next_proposal_bounded`
- Student cannot write WorldModel
- freeze/reset test
- learned-state rollback test
- regression-bound test
- `test_learning_delta_links_verified_experience`
- `test_experience_selection_respects_scope_and_budget`
- `test_staged_candidate_not_deployed`

## 17.5 Runtime proof

At least two deterministic episodes:

```text
Episode 1
 -> verified outcome
 -> feedback
 -> strategy delta

Episode 2
 -> proposal set differs
 -> difference is bounded
 -> trace identifies why
```

A later acquisition demonstration must show:

```text
eligible tasks/experiences
        |
        v
selection policy
        |
        v
admissible next task
```

with no scope/authorization bypass.

## 17.6 G6 Gate

PASS requires:

- shadow learning works
- flagged bounded learning works
- reset/freeze works
- Student never writes WorldModel
- updates are bounded and versioned
- trace contains learning diffs
- baseline performance guard is active
- learner-conditioned acquisition is scope/resource constrained
- no candidate is considered deployable solely because Student generated it

---

# 18. PHASE P7 — ARENA / REDTEAM PARITY + GOVERNED DEPLOYMENT ADAPTATION

**Gate:** G7

**Objective:** prove that the same Runtime is the brain in production and validation, then establish controlled candidate deployment with explicit promotion and rollback.

## 18.1 Two sub-stages

### P7a — early adapter track

May start after G2.

Goal: prepare arena to consume Runtime without changing the old arena loop's measurement semantics.

### P7b — full parity

Starts after G6.

Goal: arena and local validation use the same canonical Runtime.

### P7c — governed deployment

Starts only after parity is proven and G6 has passed.

Goal: deploy an **accepted policy successor** under explicit promotion and rollback controls.

## 18.2 GLM Contract

Arena is:

- environment provider
- scenario loader
- scorer
- measurement harness

Arena is not:

- second Planner
- second Runtime
- second Student
- source of policy truth
- promotion authority

### Promotion contract

```text
Candidate Policy
      |
      v
Replay Evaluation
      |
      v
Protected Unseen/Holdout Evaluation
      |
      v
Promotion Gate
   +------+------+
   |             |
 reject        accept
   |             |
   v             v
archive       successor
                  |
                  v
             deployment
                  |
                  v
             rollback
```

Replay results alone never authorize deployment.

## 18.3 HackerAI / Minimax / OMP Tasks

### P7.1 — parity harness

Create a diff tool for:

- stage sequence
- action request
- Broker decision
- evidence ids
- WorldModel state deltas
- final result

### P7.2 — Runtime backend switch

Make Runtime the canonical backend while preserving the old loop only as temporary migration scaffolding.

### P7.3 — Same Runtime object proof

Arena and CLI resolve to the same Runtime class/implementation.

### P7.4 — Local protected environment

Create/use a deterministic local fixture for real sandboxed execution.

### P7.5 — RedTeam environment adapter

Keep targets isolated from core. All access remains mission/scope/Broker constrained.

### P7.6 — Scenario audit

Classify old arena scenarios as compatible / needs adapter / needs redesign / obsolete.

### P7.7 — PromotionDecision schema

Implement immutable acceptance/rejection records containing:

- candidate policy id/version
- evidence refs
- replay evaluation refs
- holdout evaluation refs
- resource budget
- decision
- reviewer/authority
- timestamp
- rollback target

### P7.8 — Deployment record

Record which policy version was deployed, where, under which environment and constraint set.

### P7.9 — Rollback mechanism

Rollback must restore the last accepted policy version without rewriting or deleting evaluation evidence.

### P7.10 — Promotion lock

Reject deployment when:

- candidate has no parent lineage
- content hash is invalid
- replay evidence is incomplete
- holdout evidence is missing
- safety criteria fail
- rollback target is absent

## 18.4 Tests

- `test_same_runtime_both_envs`
- `test_local_episode_matches_mission_scope`
- import-graph parity check
- arena measurement isolation test
- fixed-seed scenario test
- `test_candidate_cannot_deploy_without_holdout`
- `test_promotion_decision_has_lineage`
- `test_deployment_is_rollbackable`
- `test_replay_score_alone_cannot_promote`

## 18.5 Runtime proof

First prove parity:

```text
CLI -> Runtime
Arena -> Runtime
```

Then prove governed deployment:

```text
policy vN
   |
   v
candidate vN+1
   |
   +--> replay
   +--> holdout
   |
   v
promotion decision
   |
   +--> reject
   |
   +--> accept -> deploy -> rollback target retained
```

## 18.6 G7 Gate

PASS requires:

- no cognitive subsystem is arena-only
- arena and CLI use same Runtime
- RedTeam/local environment is Broker-gated
- scoring does not feed Runtime decisions directly
- parity evidence archived
- promotion requires replay + protected holdout evidence
- accepted versions have complete lineage
- deployment is rollbackable
- human/authorized release remains outside the self-modifiable surface

---

# 19. PHASE P8 — EVALUATION PROGRAM + REPLAY / RECURSIVE EVALUATION

**Gate:** G8

**Objective:** measure Raphael's architecture and recursive improvement claims without contaminating the test subject and without confusing deterministic regeneration with replay.

## 19.1 Evaluation model

Do not create separate agent implementations as evaluation arms.

Use one canonical Runtime and controlled configuration/policy ablations.

Primary task-performance arms remain:

```text
FULL
-LEARN
-WM
-FALSIFY
SINGLE-SHOT
```

Recursive-improvement evaluation additionally compares **policy versions under matched conditions**.

## 19.2 Replay model

### Discovery / experience history

The recorded history is a structured decision tree/graph, not a flat log only.

Minimum replay requirements:

```text
root
  |
  +-- branch A -- outcome
  |
  +-- branch B -- outcome
  |
  +-- branch C
         |
         +-- child
```

Each replayable node must retain the state/action/outcome references needed to determine which historical child would have been observed from that prefix.

### Replay simulator

Replay:

- loads recorded history/state
- presents only observations available at that prefix
- returns recorded outcomes where the historical branch exists
- does not re-run the production agent/evaluator
- does not perform real environment execution
- scores candidate policies against the fixed history

A deterministic scenario rerun from the same seed is **not** accepted as a replay simulator.

Historical text/context injection is also not equivalent to replay.

## 19.3 Dream-RSI boundary adopted by Raphael

The inspiration from Dream-RSI is deliberately narrow:

- improve the **exploration policy**, not the protected agent/evaluator
- reuse completed history as a replay world
- evaluate many candidate policies cheaply offline
- retain the accepted policy for a later round

Raphael does **not** copy the paper's code or assume the same task/evaluator.

The replay selector must preserve the distinction:

```text
history as replay simulator
        !=
history as semantic prompt guidance
```

## 19.4 Evaluation axes

### A — Architecture

Does the canonical loop improve task performance vs. single-shot behaviour?

### B — Student

Does bounded learning improve subsequent proposal quality?

### C — WorldModel

Does evidence-backed state improve multi-step behaviour?

### D — Safety

Can scope violations and bypass attempts be reliably blocked?

### E — Evidence

Can claims be traced to execution/artifacts?

### F — Replanning

Does contradiction/failure change future decisions appropriately?

### G — Adaptivity

Does the improvement mechanism change behaviour in response to measured experience rather than a fixed script?

### H — Retention

Do accepted improvements persist and remain active across later rounds/restarts?

### I — Transfer

Do improvements hold on tasks/seeds/distributions not used to select the candidate?

### J — Efficiency

Does the improvement achieve comparable or better outcomes under controlled resource budgets/costs?

### K — Stability

Does the accepted mechanism avoid regressions on protected baseline tasks?

### L — Meta-recursion

Does the mechanism responsible for future improvement itself persist/change across rounds? This axis is P10 admission-level evidence, not a blanket P8 claim.

### M — Capability effectiveness

Do capabilities produce expected known-answer results under policy constraints?

## 19.5 GLM Contract

Before any evaluation run:

- protocol is pre-registered
- metrics are frozen
- instrumentation validated per arm
- seed strategy fixed
- safety and efficacy are separate metrics
- defective arms quarantined
- resource budget fixed for matched comparisons
- evaluator independence boundary documented

For recursive-improvement claims, report at minimum:

```text
baseline policy
candidate policy
parent lineage
selection-history results
protected holdout results
budget/resource accounting
retention result
transfer result
stability result
rollback availability
```

## 19.6 HackerAI / Minimax / OMP Tasks

### P8.1 — Harness

Implement evaluation runner around the canonical Runtime.

### P8.2 — Instrumentation pre-flight

For every arm prove intended configuration, no silent exceptions, consistent logging, sane counters, and matched environment/seed policy.

### P8.3 — Seeded runs

Run deterministic seeds including protected holdout sets.

### P8.4 — Ablation runs

Measure each architectural axis independently.

### P8.5 — Safety injections

Run controlled denial/bypass/escape scenarios.

### P8.6 — Report generation

Produce machine-readable and human-readable results.

### P8.7 — Experience-tree builder

Build the replayable decision-history representation from canonical execution records without weakening provenance.

### P8.8 — Replay engine

Given fixed historical experience, evaluate candidate `ExplorationPolicy` versions without invoking real execution.

### P8.9 — Protected holdout evaluator

Evaluate candidates on tasks/seeds that were not used for replay selection. The evaluator must be protected from candidate policy modification.

### P8.10 — Promotion-comparison protocol

Compare policy vN against candidate vN+1 under matched resource budgets, same environment distribution, and independent evaluation.

### P8.11 — Long-horizon metrics

Implement reporting for Adaptivity, Retention, Transfer, Efficiency, Stability, and Meta-recursion.

## 19.7 Tests

- evaluation protocol validation
- per-arm instrumentation self-check
- seed reproducibility
- no post-hoc configuration drift
- safety metric separation
- `test_replay_does_not_execute`
- `test_replay_returns_recorded_branch`
- `test_replay_prefix_observability`
- `test_holdout_is_not_selection_history`
- `test_candidate_evaluator_is_protected`
- `test_policy_versions_compared_under_matched_budget`
- `test_retention_across_rounds`
- `test_transfer_to_unseen_tasks`
- `test_stability_against_baseline`

## 19.8 Runtime / evaluation proof

The minimum recursive-evaluation demonstration is:

```text
Round N
  |
  +--> collect experience
  |
  +--> build replay history
  |
  +--> evaluate candidate policies on history
  |
  +--> select candidate for holdout
  |
  +--> protected holdout evaluation
  |
  +--> accept/reject
  |
  +--> retain parent/child lineage
  |
  v
Round N+1
```

Replay selection may prove only a historical property. Holdout evaluation is required to establish any transfer/stability claim.

## 19.9 G8 Gate

PASS only when:

- all reported arms pass instrumentation pre-flight
- results are reproducible under fixed seeds
- safety and efficacy separated
- no defective arm presented as evidence
- methodology archived
- replay is actual recorded-history replay rather than regeneration
- candidate evaluator is protected
- holdout is independent of replay selection
- policy versions have complete lineage
- resource budgets are comparable
- retention/transfer/stability measurements are reproducible
- no structural/effective RSI claim exceeds the evidence actually produced

---

# 20. PHASE P9 — REPOSITORY CONSOLIDATION / DELETION + LEARNED-STATE LIFECYCLE

**Gate:** G9

**Objective:** remove obsolete architecture and migration scaffolding only after replacements are proven, while giving accepted learning/policy state an explicit lifecycle.

## 20.1 Deletion rule

```text
deprecate
   -> verify zero canonical references
   -> delete atomically
   -> run tests
   -> run architecture checks
   -> record commit
   -> continue
```

## 20.2 Candidate cleanup set

Subject to P0/P1 inventory and actual zero-reference proof:

- legacy Head-1 internal loop
- legacy CLI flag
- migration seam
- AdaptiveBrain
- duplicate planner
- dormant brain stubs
- unused bridge
- legacy `agent/`
- unused `api/`
- duplicate CLI surfaces
- broken symlinks
- stale hard-coded launch scripts
- obsolete arena orchestration
- unused `NOT_IMPLEMENTED` stubs
- superseded policy versions where the retention policy explicitly permits archival/retirement
- obsolete learned-state records after retention/rollback requirements are satisfied

Historical reports and benchmark artifacts should be archived rather than casually deleted where they are provenance for earlier claims.

## 20.3 Learned-state lifecycle

For each accepted policy/learning artifact define:

```text
ACTIVE
  |
  +--> SUPERSEDED
  |
  +--> ROLLBACK TARGET
  |
  +--> RETIRED / ARCHIVED
```

No retirement may destroy evidence required to explain why a version was accepted or deployed.

## 20.4 HackerAI / Minimax / OMP Tasks

### P9.1 — Final reference scan

Before every deletion inspect imports, dynamic imports, entry points, tests, docs, scripts, and packaging metadata.

### P9.2 — Atomic deletion units

Never perform a giant cleanup commit.

### P9.3 — Documentation reconciliation

Update README, architecture docs, deployment/run docs, test commands, module references, and policy/version lifecycle docs.

### P9.4 — Final architecture test suite

Include:

- `test_import_graph_single_runtime`
- `test_no_duplicate_planner_import`
- `test_no_orchestrator_import_of_legacy`
- no-seam import test
- no-absolute-path invariant
- learned-state lifecycle consistency test
- policy lineage integrity test

### P9.5 — Clean clone

Reproduce the canonical local demo after cleanup.

### P9.6 — Learned-state archival

Archive superseded policy/learning state according to declared retention and rollback requirements.

## 20.5 G9 Gate

PASS requires:

- no unexplained dead canonical architecture
- seam removed
- legacy flag removed
- target tree coherent
- documentation matches implementation
- learned-state lifecycle is coherent
- clean clone works
- regression floor preserved

---

# 21. PHASE P10 — ADVANCED CAPABILITIES / OPTIMIZATION + RECURSIVE IMPROVEMENT ADMISSION

**Gate:** G10

**Objective:** expand Raphael only where evaluation demonstrates value, and admit L5 recursive improvement only when the evidence demonstrates the required mechanism rather than merely a learning effect.

## 21.1 Candidate areas

- selected `NOT_IMPLEMENTED` capabilities
- broader reconnaissance capability support
- specialized domain lanes
- multi-episode mission memory
- mature Student strategies
- provider resilience/fallback
- knowledge-graph-backed skills
- performance/context optimization
- stronger sandboxing
- selected Decepticon-derived components
- bounded meta-level exploration mechanisms

## 21.2 Required admission test for every advanced capability

A proposed capability must answer:

1. What mission class requires it?
2. Why can't an existing capability satisfy the need?
3. How does it remain Broker-gated?
4. What evidence does it emit?
5. What evaluation slot measures it?
6. What security test exercises failure/abuse?
7. What is the rollback strategy?

If these questions cannot be answered, the capability does not enter P10.

## 21.3 L2 / L3 / L4 / L5 admission ladder

### L2 — improvement-strategy autonomy

Required evidence:

- `ExplorationPolicy` is a first-class persistent object
- system can generate/select bounded policy candidates without external per-round editing of the policy mechanism
- candidates are evaluated independently
- accepted policy persists and governs a later round

### L3 — learner-conditioned experience acquisition

Required evidence:

- learner selects admissible future experience/tasks
- selection is bounded by mission/scope/resource constraints
- chosen experience changes later learning opportunities
- selection is reproducible and traceable

### L4 — environment/deployment adaptation

Required evidence:

- accepted improvement is deployed into a later production/validation round
- deployment is governed, reversible, and lineage-linked
- operator/human release authority remains protected
- adaptation does not weaken Broker/PEP/evidence authority

### L5 structural recursion

Required evidence:

```text
policy vN
   |
   v
changes the mechanism used to produce future improvement
   |
   v
policy vN+1
   |
   v
vN+1 itself governs the next improvement round
```

The improved mechanism must persist and be reused.

### L5 effective recursion

Structural persistence is not enough.

Required evidence must show stronger successors under comparable resource budgets using protected independent evaluation. Report at least:

- Adaptivity
- Retention
- Transfer
- Efficiency
- Stability
- Meta-recursion

A replay-only improvement is not sufficient to establish effective recursion because replay covers only the realized search space.

## 21.4 Hard L5 exclusions

Do **not** count these as L5 by themselves:

- changing prompts manually
- editing source code once
- accumulating logs
- persisting a memory database
- increasing a score on the training/replay history only
- changing Student weights without successor evaluation
- deterministic scenario regeneration
- textual history injection
- a single successful candidate deployment

## 21.5 Protected control surface — permanent

The following remain outside recursive modification even at P10:

```text
CapabilityBroker / PDP
exec / PEP
authorization semantics
evidence authority / provenance invariants
single Runtime rule
single loop rule
protected evaluator / holdout protocol
promotion authority
human release authority
```

Any proposal to make these self-modifiable requires a new explicit ADR and is outside this roadmap by default.

## 21.6 Decepticon track

Decepticon-derived components may be integrated after G4 and preferably after MVP proof is stable.

Requirements:

- attribution / license compliance
- fenced subtree
- dependency audit
- no cognitive imports upward
- Broker route
- PEP receipt
- sandbox containment test
- evaluation delta

## 21.7 G10 Gate

PASS requires either:

1. justified advanced-capability admission with security/evaluation/rollback evidence, **or**
2. an explicit RSI admission package demonstrating the claimed level without overstating evidence.

No L2/L3/L4/L5 claim is accepted merely because the code contains learning, versioning, or self-modification.

---

# 22. DECEPTICON PARALLEL TRACK — PD

This track does not block the MVP.

## PD.1 Investigation

- identify exact modules of interest
- inspect coupling
- inspect license headers
- inspect transitive dependencies
- classify ADAPT / REIMPLEMENT / REJECT

## PD.2 Integration matrix

| Component | Action | Target | Constraint |
|---|---|---|---|
| sandbox/process isolation | ADAPT + WRAP | `exec/` | Broker-configured |
| capability registry patterns | ADAPT | Raphael capability registry | no duplicate registry |
| result normalization | REIMPLEMENT | Evidence model | native Receipt mapping |
| artifact capture | ADAPT if clean | ArtifactStore | hash-linked |
| tool protocol | evaluate later | adapter layer | only if needed |
| specialist agents | REJECT | — | no peer architecture |
| orchestration | REJECT | — | Runtime ownership |
| mission/planning | REJECT | — | Raphael native |
| provider fallback | optional P10 | provider adapter | eval-gated |

## PD.3 Gate

`G-D` requires:

- at least one derived execution component working through Broker/PEP
- evidence receipt exists
- sandbox containment proof
- no cognitive inversion
- license/dependency audit passes

---

# 23. TEST REGISTRY

This is the initial canonical registry. Tests may be renamed, but their proof obligations cannot disappear without an ADR.

| Test | Phase | Purpose |
|---|---:|---|
| `test_behavior_neutral_gate_off` | P1 | legacy seam parity |
| `test_import_graph_single_runtime` | P2-P9 | one canonical loop |
| `test_runtime_executes_via_broker` | P2 | born-gated Runtime |
| `test_receipt_minted_by_pep` | P2 | evidence boundary |
| `test_planner_requires_broker` | P3 | no Planner self-auth |
| `test_no_unbrokered_execution` | P3 | no direct environment path |
| `test_broker_required_error_on_direct_ctor` | P3 | capability construction boundary |
| `test_scope_rejects_out_of_mission` | P3-P4 | policy enforcement |
| `test_evidence_receipt_linked_artifact` | P3-P4 | evidence integrity |
| `test_persistence_across_restart` | P4 | durable evidence |
| `test_redaction_no_secrets_in_ledger` | P4 | operator ledger hygiene |
| `test_claim_verified_vs_model_asserted` | P4 | epistemic separation |
| `test_contradiction_changes_next_decision` | P5 | load-bearing falsification |
| `test_student_candidate_reaches_planner_broker` | P6 | Student path |
| `test_student_receives_outcome` | P6 | feedback path |
| `test_student_changes_next_proposal_bounded` | P6 | bounded learning |
| `test_same_runtime_both_envs` | P7 | arena/CLI parity |
| `test_local_episode_matches_mission_scope` | P7 | environment scope proof |
| `test_no_cognitive_inversion` | PD | Decepticon fence |
| `test_no_duplicate_planner_import` | P9 | cleanup |
| `test_no_orchestrator_import_of_legacy` | P9 | cleanup |

---

# 24. INVARIANT REGISTRY

| ID | Invariant | Activation | Enforcement state |
|---|---|---:|---|
| INV-1 | process/network/file primitives confined to `exec/` | P2 | build-breaking from P2 |
| INV-2 | every execution event has Broker `decision_id` | P2/P3 | build-breaking from P3 |
| INV-3 | execution-derived claims require receipts | P3 | build-breaking from P3 |
| INV-4 | assertions quarantined; falsification controls promotion | P3/P5 | build-breaking from P5 |
| INV-5 | CLI → Runtime; Runtime does not import arena | P2 | build-breaking from P2 |
| INV-6 | Runtime cannot import migration seam | P2 | build-breaking from P2 |
| INV-7 | no absolute hard-coded user paths in new Runtime code | P2 | build-breaking from P2 |
| INV-8 | Student never writes WorldModel | P6 | build-breaking from P6 |
| INV-9 | Decepticon imports confined to `exec/` | PD | build-breaking when integration begins |
| INV-10 | no AGPL source without explicit legal ADR | P1 onward | build-breaking |
| INV-11 | deprecated modules not imported by canonical code | P1 advisory; P2+ enforced | advisory P1 / build-breaking P2+ |
| INV-12 | ledger append-only and redacted | P4 | build-breaking from P4 |
| INV-13 | arena scoring does not affect Runtime decisions | P7/P8 | build-breaking from P7 |
| INV-14 | test floor for retained behaviour is monotonic; no weakening outside P9 atomic deletion | all | build-breaking |
| INV-15 | `NOT_IMPLEMENTED` stubs remain unrouted unless explicitly admitted | P1-P10 | build-breaking for canonical reachability |
| INV-16 | T3MP3ST-influenced native types are recorded in `docs/PATTERN_PROVENANCE.md` with concept/influence/non-copied-source note | P1 onward | build-breaking at affected gate |
| INV-17 | `ExperienceNode` is immutable for a replay evaluation round and remains provenance-linked | P4 | build-breaking from P4 |
| INV-18 | `ExplorationPolicy` has stable identity, hash, parent lineage, and bounded target surface | P4 | build-breaking from P4 |
| INV-19 | replay does not execute real environment actions | P8 | build-breaking from P8 |
| INV-20 | replay-selected candidates require protected holdout evaluation before deployment | P7/P8 | build-breaking from P7 |
| INV-21 | accepted policy successor is rollbackable and lineage-complete | P7 | build-breaking from P7 |
| INV-22 | protected control surface cannot be targeted by the improvement mechanism | P4 onward | build-breaking |
| INV-23 | structural and effective RSI claims are admitted separately | P10 | build-breaking for RSI claim package |

# 25. EVIDENCE PACKAGE STANDARD

Every phase must end with one structured Evidence Package.

Recommended file:

`evidence/phases/PX_<slug>/EVIDENCE.md`

This schema is mandatory for every phase from P0 through P10, including the explicit **scope deviations** field under §25.2. `none` is an acceptable value; an omitted field is not. No gate review may begin against a package missing any required section.

## Required contents

### 25.1 Identity

- phase
- gate
- repository HEAD
- implementation commit
- timestamp

### 25.2 Scope

- tasks completed
- tasks not completed
- scope deviations

### 25.3 Changed files

Table:

| File | Change | Reason |
|---|---|---|

### 25.4 Tests

- exact test command
- full output
- pass/fail/skip counts
- comparison with `FLOOR(P0)`

### 25.5 Runtime proof

- exact command
- expected behavior
- actual transcript
- generated trace/artifacts

### 25.6 Security proof

Where applicable:

- bypass attempted
- expected denial
- actual denial
- trace/receipt evidence

### 25.7 Review notes

- known issues
- unresolved questions
- rollback point
- next-phase prerequisites

No gate review begins without this package.

# 26. GATE REVIEW PROTOCOL FOR GLM

At each gate GLM must review four dimensions.

## 26.1 Contract compliance

Does the implementation satisfy the phase's architectural contract?

## 26.2 Scope compliance

Did the implementation agent modify anything outside the approved scope?

## 26.3 Proof adequacy

Does the evidence demonstrate behavior rather than merely show test counts? The reviewer must first verify Evidence Package schema completeness, including explicit scope-deviation status, before evaluating substantive proof.

## 26.4 Adversarial integrity

Can GLM intentionally violate the invariant?

### Example G3 adversarial checklist

```text
[ ] Planner self-auth
[ ] Direct subprocess
[ ] Direct capability construction
[ ] Direct probe
[ ] Mode-local execution
[ ] Seam abuse
[ ] Test policy abuse
[ ] Missing decision_id
[ ] Fake receipt
[ ] Unprovenanced WorldModel claim
[ ] Alternate Runtime entry point
```

A single successful invariant violation is a gate failure.

### RSI adversarial checklist (G7/G8/G10)

```text
[ ] Replay invokes real execution
[ ] Replay exposes evaluator truth unavailable at the prefix
[ ] Candidate modifies protected evaluator
[ ] Candidate targets Broker/PEP/authorization semantics
[ ] Candidate has no parent lineage
[ ] Replay win deploys without holdout
[ ] Rollback target is missing
[ ] Learning delta lacks verified evidence
[ ] Learner selects out-of-scope experience
[ ] Structural recursion is claimed without persistent successor reuse
[ ] Effective recursion is claimed from replay-only gains
```

---

# 27. IMPLEMENTATION AGENT OPERATING PROMPT

The following block is intended to be used as the standing instruction for Minimax / OMP / HackerAI-style execution agents.

```text
You are Raphael's implementation engineer.

You are operating under RAPHAEL MASTER ROADMAP v4 — DUAL-LANE EXECUTION.

Your authority is limited to the current phase/task packet.

RULES:
1. Inspect the repository before editing.
2. Treat all audit file/line references as hypotheses until verified against the current checkout.
3. Never fix forward against a stale reference.
4. Preserve the canonical architecture: one Raphael, one Runtime, one loop.
5. Do not create a second orchestration system.
6. The Runtime is born-gated. Never add an ungated Runtime execution path.
7. Planner proposes; Broker authorizes; PEP executes.
8. Do not add process/network/file execution primitives outside the allowed execution boundary.
9. Do not bypass Broker to make tests or development easier.
10. Do not implement deferred capabilities merely because they exist.
11. Do not perform broad cleanup outside the phase scope.
12. Reuse substantial working machinery unless the phase explicitly requires redesign.
13. Add/update tests with every behavioral change.
14. Run targeted tests first, then the relevant regression suite, then the full suite when required.
15. Produce runtime proof, not just a claim that code works.
16. Preserve the P0 test floor.
17. Record every scope deviation explicitly.
18. If repository reality conflicts with an architecture contract, stop the conflicting task and report the conflict rather than silently changing architecture.
19. Use atomic commits for logically separate migration/deletion operations.
20. End every phase with an Evidence Package.

IMPLEMENTATION STYLE:
- Prefer small, reviewable changes.
- Prefer adapters and seams over large rewrites.
- Prefer deterministic tests.
- Prefer explicit interfaces over hidden coupling.
- Keep Runtime thin.
- Keep security enforcement below cognition.
- Keep evidence attribution at the execution boundary.

FINAL RESPONSE FOR EACH TASK:
- What changed
- Why it changed
- Files changed
- Tests run
- Runtime proof
- Result
- Known issues
- Remaining work
- Scope deviations
- Commit hash
```

---

# 28. GLM ARCHITECTURE REVIEW PROMPT

The following is the standing review instruction for GLM.

```text
You are Raphael's architecture lead and adversarial gate reviewer.

Review the implementation only against the current phase contract in RAPHAEL MASTER ROADMAP v4.

You do not rewrite file-level implementation mechanics unless required to enforce an architectural invariant.

For each phase:
1. verify the implementation satisfies the architecture contract
2. inspect the Evidence Package
3. compare claimed proof with actual proof
4. test the critical invariant mentally and, where possible, adversarially
5. identify scope deviations
6. identify hidden second-loop or bypass risk
7. verify the test floor was preserved
8. verify no deferred feature escaped into the phase
9. return PASS or FAIL

A PASS requires:
- contract satisfied
- required tests present
- runtime proof present
- no critical invariant violation
- scope deviations explained
- rollback available

A FAIL must name:
- exact invariant/acceptance criterion violated
- evidence showing violation
- minimal remediation needed
- what must be re-run

Special focus:
- pre-G3 Broker bypasses
- Runtime/seam separation
- PDP/PEP separation
- epistemic integrity
- Student/WorldModel separation
- arena/runtime duplication
- Decepticon cognitive inversion
- deletion safety
```

---

# 29. REMEDIATION PROTOCOL

A failed gate does not cause the roadmap to restart.

```text
GATE FAIL
   |
   v
Create remediation task
   |
   v
HackerAI implementation
   |
   v
Targeted proof
   |
   v
Regression
   |
   v
GLM re-review
```

Remediation must be narrowly scoped to the failed criterion.

Do not use a failure as justification for unrelated cleanup or architecture expansion.

---

# 30. ROLLBACK POLICY

## Runtime rollback

Prefer reverting individual implementation commits rather than resetting the entire branch.

## Seam rollback

Legacy migration seam may temporarily restore a legacy path during migration debugging, but:

- it must not ungate canonical Runtime
- it must be documented
- it must have an owner
- it must have an expiry/removal phase

## Student rollback

Disable learning and return to proposal-only behavior. Learned state can be wiped.

## Falsification rollback

Temporary advisory-only mode is allowed during remediation if contract permits it. It must not silently remain the default after the gate.

## Deletion rollback

Each deletion is atomic and independently revertible.

---

# 31. SCOPE-CONTROL RULES

| Rule | Requirement |
|---|---|
| R1 | MVP is frozen once G3 is reached. |
| R2 | No new Runtime stage without ADR. |
| R3 | No direct execution outside PEP. |
| R4 | No Planner authorization. |
| R5 | No Student → WorldModel writes. |
| R6 | No Decepticon cognitive imports. |
| R7 | No AGPL source incorporation by default. |
| R8 | No physical deletion before P9. |
| R9 | No implementation of stubs without evaluation-backed admission. |
| R10 | No weakening green tests of kept code to pass a gate. |
| R11 | Every feature flag has an owner and removal phase. |
| R12 | Every phase has an Evidence Package. |
| R13 | HackerAI may not amend architecture invariants without escalation. |
| R14 | GLM may not micromanage file-level mechanics when the implementation satisfies the contract. |
| R15 | Arena loop is frozen during the migration window unless a gate-approved weld requires a change. |
| R16 | Any audit reference that shifts at P0 must be re-derived before editing. |

---

# 32. DEPENDENCY GRAPH

```text
                         +------------------+
                         |       P0         |
                         | baseline/reality |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P1         |
                         | architecture     |
                         | + seam + guards  |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P2         |
                         | born-gated       |
                         | Runtime skeleton |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P3         |
                         | Broker closure   |
                         | + MVP            |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P4         |
                         | Mission/Evidence |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P5         |
                         | WM/Falsification |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P6         |
                         | Student learning |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P7         |
                         | Arena parity     |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P8         |
                         | Evaluation       |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |       P9         |
                         | Consolidation    |
                         +---------+--------+
                                   |
                                   v
                         +------------------+
                         |      P10         |
                         | Advanced work   |
                         +------------------+

Parallel:

P1 -----> Decepticon analysis only
P2 -----> P7a arena adapter preparation
P5 -----> P8 evaluation protocol design
P1 -----> P9 deletion inventory maintenance
P4 -----> Decepticon integration readiness

RSI dependency chain (after G3):

P4 -----> ExperienceNode + PolicyVersion + protected/evolvable registry
P5 -----> diagnosis + ExplorationPolicy decision interface
P6 -----> bounded learning + learner-conditioned acquisition
P7 -----> promotion + deployment + rollback
P8 -----> replay + protected holdout + long-horizon recursive evaluation
P9 -----> policy/learning lifecycle
P10 ----> structural/effective RSI admission
```

---

# 33. PHASE STATUS FORMAT

Use this exact compact record in the master roadmap as execution progresses.

```text
PHASE: P3
STATUS: IN_PROGRESS
OWNER: HackerAI
ARCHITECTURE: GLM
GATE: G3

TASKS:
[x] P3.1
[x] P3.2
[ ] P3.3
...

TEST FLOOR:
FLOOR(P0) = <actual>
CURRENT = <actual>

EVIDENCE PACKAGE:
<path>

LAST PROOF:
<command / result>

BLOCKERS:
<none / details>

SCOPE DEVIATIONS:
<none / details>

INVARIANT ENFORCEMENT:
<advisory/build-breaking summary for active invariants>

NEXT ACTION:
<task id>
```

This makes the roadmap machine-readable enough for a model to resume work without reconstructing the entire history.

---

# 34. DEFINITION OF DONE

Raphael is considered architecturally complete when all of the following are demonstrated.

## Architecture

- one Runtime
- one cognitive loop
- no parallel brain
- CLI and arena drive the same Runtime

## Security

- no known Broker bypass
- static import invariant active
- dynamic bypass attempts blocked
- every execution decision-linked

## Evidence

- receipts are PEP-minted
- artifacts are integrity-linked
- provenance is reconstructible
- WorldModel claims are evidence-constrained

## Cognition

- WorldModel influences planning
- contradiction/falsification changes future decisions
- replan is demonstrably load-bearing

## Student

- receives verified outcomes
- changes future proposals in bounded mode
- reset/freeze works
- cannot mutate WorldModel beliefs

## Validation

- arena parity proven
- controlled local mission proven
- evaluation protocol validated
- safety and efficacy measured separately

## Repository

- deprecated architecture removed or explicitly justified
- migration seam deleted
- documentation matches implementation
- clean clone reproduces the core demonstration

---

# 35. FINAL AUTHORITATIVE DECISIONS

### Canonical head

Head 2 cognition is canonical. Head 1 survives only as the operator-facing shell plus explicitly selected organics that fill real gaps.

### Canonical orchestrator

`RaphaelRuntime` is the only production cognitive-loop owner.

### Broker

Broker is the deny-by-default PDP. It is mandatory for environment interaction.

### PEP

The execution package is the only holder of environment-execution primitives and is responsible for enforcing Broker decisions and minting evidence.

### Seam

Temporary migration scaffolding only. It never enters the canonical Runtime. It is welded closed during P3 and deleted in P9.

### WorldModel

Canonical state store. Execution-derived state must be evidence-linked. Assertions remain quarantined until verification.

### Falsification

The only component authorized to move claims between epistemic classes.

### Student

Candidate generator first; bounded learner later. Never a second orchestrator and never a direct WorldModel writer.

### Arena

Driver/scorer/environment layer. It is not a second brain.

### Decepticon

Post-MVP, execution-only, fenced below the Broker.

### T3MP3ST

Conceptual pattern source only, native Raphael implementation, no AGPL source by default.

### MVP

G3 walking skeleton: gated, evidenced, minimally replanning, deterministic, reproducible.

### Baseline

`FLOOR(P0)` is the only authoritative regression floor.

---

### RSI improvement workflow

The improvement workflow is a governed meta-level process around the canonical Runtime. It is not a second Runtime, second cognitive loop, or alternate production orchestrator.

### Improvement experience

Structured `ExperienceNode` history is distinct from `EvidenceRecord` provenance and from mission-scoped WorldModel belief state. Evidence remains the authority; experience organizes reusable decision history.

### ExplorationPolicy

Exploration behaviour becomes a first-class, versioned, bounded evolvable object. It cannot authorize execution and cannot modify the protected control surface.

### Replay

Replay means evaluation against recorded history/state/outcomes without real environment execution. Scenario regeneration and historical prompt injection are not substitutes.

### Promotion

Replay selection never alone authorizes deployment. Candidates require protected unseen/holdout evaluation plus lineage, resource accounting, safety checks, and rollback.

### RSI claims

L2, L3, L4, structural L5, and effective L5 are separate admissions. Raphael must not claim a higher level merely because a lower-level mechanism exists.

### Permanent control line

Broker/PDP, PEP, authorization semantics, evidence authority/provenance invariants, single Runtime/loop rules, protected evaluator/holdout rules, promotion authority, and human release authority remain protected from recursive modification.

# 36. IMMEDIATE EXECUTION QUEUE

## Current hard gate

```text
AM-4-R3
   ↓
G3
   ↓
P4 / RSI substrate
```

AM-4-R3 has **not** been executed. G3 has **not** passed. No RSI implementation is authorized yet.

## HackerAI / Minimax / OMP / GLM execution sequence

1. Execute AM-4-R3 exactly as governed by the v4.1 arbitration and current task packet.
2. Independently audit AM-4-R3.
3. Re-derive/reconcile CENSUS, WELD_SET, and related evidence after genuine deletion/re-homing.
4. Pass G3.
5. Start P4 with a new phase contract derived from this roadmap.
6. Do not skip gates because RSI work is conceptually attractive or because supporting code already exists.

## RSI stop rule

Until G3 passes, do **not**:

- add ExperienceNode infrastructure to production
- activate Student learning
- implement a replay simulator
- add policy promotion/deployment
- modify the Runtime for RSI purposes
- introduce a second loop

# 37. MASTER RULE

> **The repository is the implementation substrate, GLM is the architecture authority, automated tests are mechanical witnesses, and runtime evidence is the final proof.**
>
> Raphael is not complete because the code is large. Raphael is complete when one Runtime can safely observe, plan, obtain authorization, execute, capture evidence, update state, falsify assumptions, replan, and eventually learn — with every critical boundary demonstrably enforced. Recursive-improvement claims require an additional chain of evidence: experience → diagnosis → bounded candidate → protected evaluation → acceptance/rejection → persistent successor → governed reuse.

---

# 38. CHANGE CONTROL

Any change to a locked decision must use an ADR containing:

- current decision
- observed contradiction/problem
- proposed replacement
- impact on existing phases
- migration implications
- test changes
- rollback
- gate affected

No silent roadmap edits.

When a roadmap change is approved, the corresponding phase/task IDs must be updated before implementation resumes.

---

# 39. END STATE

The secure task loop remains singular. The improvement workflow sits around it rather than replacing it.

```text
                         ONE RAPHAEL
                              |
                      RaphaelRuntime
                              |
          +-------------------+-------------------+
          |                   |                   |
       Student             Planner            WorldModel
          |                   |                   |
          +-------------------+-------------------+
                              |
                           Broker
                              |
                            PEP
                              |
                          Sandbox
                              |
                        Capability
                              |
                     EvidenceReceipt
                              |
                         Provenance
                              |
                      Falsify / Replan
                              |
                         Student
                              |
                       TASK LOOP
                              |
                              v
                    structured Experience
                              |
                              v
                         Diagnosis
                              |
                              v
                      ImprovementHypothesis
                              |
                              v
                     ExplorationPolicy
                              |
                              v
                        Replay / Holdout
                              |
                              v
                    Promotion / Rollback
                              |
                              v
                    next accepted version
                              |
                              +---------> TASK LOOP
```

The final architecture has one identity, one Runtime, one task loop, one execution boundary, and a governed improvement workflow that can only influence explicitly evolvable surfaces through evidence, protected evaluation, promotion, and rollback.

# 40. READY-TO-SEND PHASE PROMPTS

The sections below are deliberately written so the roadmap can be used as the basis of a direct task prompt for Minimax/OMP/HackerAI and a corresponding review prompt for GLM. The implementation agent should receive only the current task packet plus the standing implementation-agent operating prompt from §27; it does not need to infer the overall project strategy. Later RSI prompts are subordinate to the same sequential engineering loop and may not self-advance phases.

## 40.0.1 AM-4-R3 handoff — current next task

Before P0/P4-style future work in this consolidated roadmap, the actual current repository task remains the already-issued **AM-4-R3** implementation packet governed by the v4.1 arbitration.

Current state:

```text
AM-4-R3 prompt: EXISTS / NOT YET EXECUTED
AM-4-R3 implementation: NOT EXECUTED
G3: BLOCKED
RSI implementation: NOT STARTED
```

The model receiving the current AM-4-R3 packet must execute **only AM-4-R3**, report, and stop. The resulting report becomes the input to the next independent audit/adjudication step. It must not jump to P4 or RSI work.

## 40.1 P0 prompt — implementation agent

```text
You are executing RAPHAEL MASTER ROADMAP v4, Phase P0.

ROLE: repository implementation/reproducibility engineer.

MISSION:
Establish the true repository baseline before any behavior-changing work.

DO NOT:
- modify application behavior
- refactor modules
- fix architecture problems
- change pyproject constraints
- delete files
- update code merely to make tests pass

YOU MUST:
1. Inspect git state and compare the historical audit baseline with the current repository.
2. Choose exactly one canonical checkout using the roadmap decision rule.
3. Record the exact HEAD and working-tree state.
4. Establish the actual test floor by running the available complete suite.
5. Record the exact environment required to reproduce the suite.
6. Re-run the historical runtime probes where they are still meaningful.
7. Re-verify every known execution-bypass reference against the chosen checkout.
8. Inventory alternate entry points, dormant modules, bridge/path hazards, and deletion candidates.
9. Create/update docs/BASELINE.md.
10. Produce the P0 Evidence Package.

REQUIRED OUTPUTS:
- chosen canonical checkout
- justification
- FLOOR(P0)
- environment manifest
- runtime probe transcripts
- bypass inventory with CONFIRMED/SHIFTED/ABSENT/UNKNOWN status
- deletion inventory
- list of repo facts that differ from the historical audit

STOP CONDITIONS:
- repository cannot be reproduced and the barrier is undocumented
- a cited path no longer exists and you cannot safely identify its replacement
- test execution would require behavior changes

In a stop condition, document the barrier and do not fix forward.

SUCCESS = G0 evidence package is complete and no application behavior changed.
```

## 40.2 P0 prompt — GLM review

```text
Review P0 of RAPHAEL MASTER ROADMAP v4.

Verify:
1. exactly one checkout was selected
2. the checkout choice follows the decision rule
3. FLOOR(P0) is an observed result, not a historical assumption
4. audit references were re-verified
5. every known bypass has a current status
6. runtime probes are evidenced
7. no behavior-changing edits occurred
8. no hidden baseline repair was performed

Return PASS or FAIL.
If FAIL, name the exact missing evidence and the minimum remediation task.
```

---

## 40.3 P1 prompt — implementation agent

```text
Execute Phase P1.

GOAL:
Freeze the architecture and create migration scaffolding without changing canonical behavior.

REQUIRED:
- create/merge the architecture ADRs defined by the roadmap
- mark deprecated architecture
- establish import-graph guardrails
- create the migration seam ONLY for P0-confirmed legacy paths
- prove seam-OFF behavior parity
- create the living deletion inventory
- create the Runtime stage contract that P2 will implement

The seam is scaffolding, not architecture.
The seam may not be imported or invoked by RaphaelRuntime.
Do not implement RaphaelRuntime in P1.

Required tests:
- seam OFF behavior parity
- seam ON denial
- deprecated import detection
- Runtime cannot import the seam
- baseline regression

Required evidence:
- ADR list
- seam file and call sites
- parity transcript
- import-graph output
- unchanged FLOOR(P0)

Do not delete anything.
Do not rewire arena.
Do not add capabilities.
```

## 40.4 P1 prompt — GLM review

```text
Review P1.

Focus on:
- architecture contract completeness
- seam confinement
- absence of Runtime implementation
- absence of behavior drift
- whether the CI invariants are enforceable rather than advisory
- whether deprecation markers identify the actual legacy graph

Attack the seam conceptually:
- Can canonical Runtime import it?
- Can a flag silently ungate Runtime?
- Can the seam become a second execution path?

PASS only if these failure modes are structurally blocked or explicitly fenced.
```

---

## 40.5 P2 prompt — implementation agent

```text
Execute Phase P2: Born-Gated RaphaelRuntime Walking Skeleton.

GOAL:
Create one thin Runtime sequencer without rewriting Head 2 cognitive organs.

RUNTIME MUST OWN:
- stage ordering
- loop state
- termination
- stage contracts
- trace orchestration

RUNTIME MUST NOT OWN:
- Planner heuristics
- policy logic
- WorldModel internals
- Student learning algorithms
- arena scoring
- migration seam
- direct process/network/file primitives

IMPLEMENT THE LOOP:
observe
-> understand
-> generate candidates
-> plan
-> authorize
-> execute
-> evidence
-> integrate WorldModel
-> minimal contradiction/failure check
-> replan
-> terminate

FOR EXECUTION:
Runtime EXECUTE must call Broker -> PEP on its first usable path.
There is no Runtime OFF mode.

USE:
- Head 2 cognitive organs as handlers
- existing Head 1 CLI as operator surface
- arena only as behavioral oracle

ADD:
- one deterministic safe Raphael-native capability
- minimal receipt v0
- DecisionTrace v0

DO NOT:
- change the old arena loop
- add Decepticon
- activate Student learning
- implement new loop stages
- perform cleanup

PROVE:
CLI -> Runtime -> Broker -> PEP -> safe capability -> receipt -> trace.
```

## 40.6 P2 prompt — GLM review

```text
Review P2 as architecture gate G2.

Inspect:
- Runtime source and dependency graph
- stage ownership
- execution call chain
- seam references
- process primitive imports
- arena dependency direction

Reject if:
- Runtime contains domain logic
- Runtime has an ungated mode
- Runtime uses the seam
- Runtime imports arena for cognition
- a capability can execute without Broker/PEP
- an old Head-1 loop remains a canonical entry

Required proof:
- one CLI Runtime iteration
- decision_id present
- receipt minted by PEP
- import graph proves a single canonical Runtime
```

---

## 40.7 P3 prompt — implementation agent

```text
Execute Phase P3: Universal Broker Closure + MVP.

THIS IS A SECURITY-CRITICAL PHASE.

GOAL:
Close every P0/P2-confirmed production execution bypass and deliver the walking-skeleton MVP.

FIRST:
Refresh the bypass inventory. Do not trust line numbers from the historical audit.

CLOSE:
- Planner self-authorization
- direct subprocess fallback
- direct local tool execution
- direct privileged capability constructors
- duplicate/unused execution engine routes
- mode-local execution routes
- observation/probe bypasses

RULE:
Planner proposes.
Broker decides.
PEP enforces.
Capability executes.
PEP mints evidence.

IMPLEMENT:
- Scope v0
- deny-by-default policy
- derived AuthorizationContext
- native minimal sandbox
- one safe capability
- EvidenceReceipt v1
- ArtifactRef
- ProvenanceRecord
- minimal contradiction/failure -> replan trigger

MIGRATION SEAM:
- only legacy paths may use it
- weld closed sites ON
- delete the legacy branch at the site
- never allow Runtime to use seam

DO NOT:
- vendor Decepticon
- import T3MP3ST source
- activate Student learning
- add unrelated capabilities
- perform broad cleanup

SECURITY TESTS MUST INCLUDE:
- Planner self-auth attempt
- direct subprocess attempt
- direct capability construction attempt
- mode-local execution attempt
- probe bypass attempt
- seam abuse attempt
- invalid policy/test-policy attempt

MVP DEMO:
mission + scope -> candidate -> plan -> Broker allow -> PEP -> safe capability -> receipt -> WorldModel -> contradiction -> changed next decision -> Student outcome recording -> trace.

The demonstration must be deterministic and one-command reproducible.
```

## 40.8 P3 prompt — GLM review

```text
Act as an adversarial security reviewer for G3.

Do not accept test counts as sufficient proof.

Attempt to bypass:
1. Planner authorization
2. direct subprocess
3. direct capability construction
4. mode-local execution
5. observation probes
6. migration seam
7. test policy
8. missing decision_id
9. fake receipt
10. unprovenanced WorldModel claim

For each attempt record:
- attack path
- expected outcome
- actual outcome
- evidence

PASS requires every deliberate bypass to fail and the failure to be observable.

Also verify the MVP is actually small. Reject scope creep.
```

---

## 40.9 P4 prompt — implementation agent

```text
Execute Phase P4: Mission / Scope / Evidence / Provenance Depth.

GOAL:
Turn MVP scaffolding into a coherent native evidence/authorization model.

IMPLEMENT:
1. MissionSpec
2. Scope
3. AuthorizationContext derived per decision
4. persistent EvidenceReceipt
5. content-addressed or integrity-linked ArtifactRef
6. ProvenanceRecord
7. epistemic classes
8. append-only MissionLedger
9. DecisionTrace rendering
10. redaction before operator-visible persistence

EPISTEMIC CLASSES:
Assertion
Observation
ExecutionResult
Artifact
Finding

ENFORCE:
- Assertion cannot directly become Finding
- execution-derived claims require receipt
- receipt links to artifacts
- provenance chain is reconstructible
- AuthorizationContext is not stale or forgeable

TEST:
- out-of-scope denial
- no-scope denial
- restart persistence
- receipt/artifact linkage
- assertion quarantine
- redaction
- derived authorization context

DO NOT:
- introduce AGPL source
- create new capabilities
- rewrite WorldModel internals unnecessarily
- change Runtime stage order
```

## 40.10 P4 prompt — GLM review

```text
Review G4.

Attempt:
- forged AuthorizationContext
- stale AuthorizationContext reuse
- assertion-to-finding promotion without proof
- receipt/artifact mismatch
- ledger mutation
- secret leakage
- out-of-scope action

Verify that the model is typed/enforced rather than documented by convention.
```

---

## 40.11 P5 prompt — implementation agent

```text
Execute Phase P5: WorldModel / Falsification / Replanning.

GOAL:
Make the existing cognitive machinery materially alter future Runtime decisions.

DEFAULT STRATEGY:
Promote, decouple, rewire. Do not rewrite substantial working machinery.

SOURCE OF TRUTH:
The real falsification/defeater logic identified in the audit must be re-verified at P0 and then promoted out of arena-only ownership.

IMPLEMENT:
- Falsification Runtime stage handler
- contradiction detection
- claim promotion/demotion rules
- WorldModel evidence integration
- Planner replan hook
- deterministic paired-run harness

NORMATIVE PROOF:
Same scenario + same seed:
A = falsification enabled
B = falsification disabled

The next planner decision must differ in a measurable trace field.

ONLY FALSIFICATION MAY MOVE EPISTEMIC CLASSES.

DO NOT:
- introduce a second loop
- rewrite WorldModel architecture
- activate Student learning
- add capabilities
- delete old arena code

Resolve the ChainSynthesizer reference honestly:
fix it if required by the canonical path, otherwise record it for retirement.
```

## 40.12 P5 prompt — GLM review

```text
Review G5.

Verify:
- falsification is on the canonical Runtime path
- no arena-only dependency remains for the behavior under test
- claim-promotion authority is unique
- contradiction genuinely changes the next decision

Attempt to inject:
- fake finding
- unprovenanced observation
- contradiction that should not trigger replan
- evidence that should trigger replan but does not

PASS only when falsification is demonstrably load-bearing.
```

---

## 40.13 P6 prompt — implementation agent

```text
Execute Phase P6: Student Shadow -> Bounded Learning.

GOAL:
Turn Student into a controlled learner using verified outcomes only.

ORDER:
recording -> receipt-linked outcomes -> shadow learning -> flagged bounded learning

IMPLEMENT:
- feedback input from EvidenceReceipt + falsification result
- strategy delta journal
- shadow mode
- bounded deterministic update function
- persistent versioned learning state
- freeze/reset
- regression guard

INVARIANTS:
- Student never writes WorldModel
- Student never changes Broker policy
- Student never changes Runtime stage order
- Student never creates privileged capabilities
- learning is not default-on without explicit policy

REQUIRED DEMO:
Episode 1 -> verified outcome -> strategy delta
Episode 2 -> proposal set changes within bounds

REQUIRED ADVERSARIAL TEST:
Attempt Student->WorldModel direct write. It must fail structurally or by enforced contract.
```

## 40.14 P6 prompt — GLM review

```text
Review G6.

Test whether Student can:
- alter WorldModel beliefs directly
- exceed update bounds
- learn from assertions instead of receipts
- survive a freeze command
- evade reset
- degrade behavior beyond the declared regression bound

Verify the before/after proposal difference is real and attributable to verified feedback.
```

---

## 40.15 P7 prompt — implementation agent

```text
Execute Phase P7: Arena / RedTeam Parity.

GOAL:
Make arena and local validation consumers of the same RaphaelRuntime.

ARENA ROLE:
scenario/environment/scoring only.

REMOVE FROM ARENA OWNERSHIP:
- cognitive loop
- alternate Planner
- alternate Student
- alternate Runtime

IMPLEMENT:
- parity harness
- same Runtime assertion
- scenario/seed normalization
- local protected environment
- RedTeam environment adapter through Broker
- audit of old-loop assumptions

PARITY:
Same scenario + same seed.
Compare:
- stage sequence
- requests
- policy decisions
- evidence links
- WorldModel deltas
- final result

Document accepted nondeterminism explicitly.

DO NOT allow scoring feedback to affect Runtime decisions.
```

## 40.16 P7 prompt — GLM review

```text
Review G7.

Verify import graph:
CLI -> Runtime
Arena -> Runtime
and never:
Runtime -> Arena brain

Verify scoring is measurement-only.
Verify RedTeam/local targets remain Broker-gated.
Verify parity evidence is reproducible.
```

---

## 40.17 P8 prompt — implementation agent

```text
Execute Phase P8: Evaluation Program.

GOAL:
Measure architecture/component value without creating separate agent implementations.

USE ONE Runtime.

PRIMARY ARMS:
FULL
-LEARN
-WM
-FALSIFY
SINGLE-SHOT

ADDITIONAL ARMS require explicit justification.

IMPLEMENT:
- evaluation harness
- protocol validation
- seeded scenarios
- holdout scenarios
- per-arm instrumentation self-check
- safety tests
- evidence-integrity tests
- capability known-answer tasks
- separate safety and efficacy reports

DO NOT:
- modify Runtime logic to fit evaluation results
- change metrics after seeing results
- report an arm that fails instrumentation pre-flight
- combine safety and completion into one score without explicit rationale

PRE-RUN REQUIREMENT:
Protocol and metrics committed before measured runs.
```

## 40.18 P8 prompt — GLM review

```text
Review G8.

Check:
- pre-registration
- arm configuration integrity
- instrumentation parity
- seed reproducibility
- no silent exceptions
- no post-hoc metric changes
- safety separated from efficacy

Reject any conclusion based on a defective arm.
```

---

## 40.19 P9 prompt — implementation agent

```text
Execute Phase P9: Repository Consolidation.

GOAL:
Remove obsolete architecture only after all replacements are proven.

FOR EACH DELETE:
1. identify exact item
2. prove zero canonical references
3. inspect tests/docs/scripts/packaging references
4. delete atomically
5. run targeted tests
6. run architecture checks
7. run full relevant regression
8. commit
9. record deletion in Evidence Package

CANDIDATES:
- legacy Head-1 loop
- migration seam
- legacy CLI flag
- AdaptiveBrain
- duplicate planner
- dormant modules
- bridge if unused
- duplicate CLI/API/agent surfaces if unused
- broken symlinks/scripts
- obsolete arena orchestration
- unselected stubs

DO NOT:
- delete based on intuition
- weaken tests
- rewrite history
- delete historical evaluation evidence that is needed as provenance
```

## 40.20 P9 prompt — GLM review

```text
Review every deletion batch.

For each deleted item verify:
- zero-reference proof
- replacement is live
- test coverage still exists for retained behavior
- no second entry point was accidentally left alive
- docs no longer reference deleted architecture

Reject batch deletions when the evidence is insufficient.
```

---

## 40.21 P10 prompt — implementation agent

```text
Execute P10 only for an explicitly admitted advanced capability.

Before implementation, produce an admission note:
- capability name
- mission class requiring it
- existing capability insufficiency
- security boundary
- evidence output
- evaluation slot
- rollback
- dependencies

Do not implement because a stub exists.
Do not implement because the capability is interesting.
Do not add capability breadth without measurable justification.

Every admitted capability must:
- use Broker/PEP
- produce evidence
- pass its security contract
- receive an evaluation delta
- preserve the one-loop architecture
```

## 40.22 P10 prompt — GLM review

```text
Review the admission note before allowing implementation.

Ask:
- Is this needed?
- Is there evidence of demand?
- Can an existing capability satisfy the need?
- Does it preserve one-loop ownership?
- Does it add a new bypass vector?
- Is there a measurable evaluation slot?
- Is rollback defined?

Without affirmative answers, reject the capability.
```

---

# 41. QUICK-REFERENCE PHASE TABLE

| Phase | Main outcome | HackerAI/Minimax/OMP owns | GLM owns | Gate |
|---|---|---|---|---|
| P0 | true baseline | repo reality, tests, inventory | baseline validity | G0 |
| P1 | architecture frozen | ADR/scaffolding/seam | architecture contract | G1 |
| P2 | born-gated Runtime | Runtime implementation | Runtime contract | G2 |
| P3 | bypasses closed + MVP | security closure + MVP | adversarial security review | G3 |
| P4 | mission/evidence depth + RSI substrate | persistence, experience, policy lineage | epistemic + improvement-state contract | G4 |
| P5 | cognition + diagnosis + exploration policy | falsification, replan, diagnoser | cognitive + meta-level boundary | G5 |
| P6 | bounded learning + acquisition | Student feedback, learning, acquisition policy | learning safety | G6 |
| P7 | one Runtime + governed deployment | arena/RedTeam parity, promotion, rollback | parity + release governance | G7 |
| P8 | valid evaluation + replay + recursive metrics | harness, replay, holdout, reports | methodology + evaluator independence | G8 |
| P9 | clean architecture + lifecycle | deletion, archival, learned-state lifecycle | deletion proof | G9 |
| P10 | advanced work + L5 admission | selected capabilities / recursive mechanism experiments | admission/evaluation | G10 |

# 42. WHAT THE IMPLEMENTATION AGENT SHOULD NEVER HAVE TO DECIDE

The implementation agent should never have to independently decide:

- whether Head 1 or Head 2 is canonical
- whether a second Runtime is acceptable
- whether the Broker can be bypassed
- whether Student can write beliefs
- whether Decepticon can own orchestration
- whether T3MP3ST source can be imported
- whether a new loop stage is justified
- whether MVP scope has expanded
- whether a failed gate can be ignored

Those are roadmap/architecture decisions.

The implementation agent **does** decide:

- exact file placement within the architecture contract
- migration mechanics
- adapter details
- how to structure tests
- how to debug repository-specific failures
- exact commands/tooling
- implementation-level refactor sequence

---

# 43. WHAT GLM SHOULD NEVER HAVE TO REDISCOVER

GLM's review input should always include:

- current phase
- contract
- exact task IDs
- changed-file list
- tests run
- runtime proof
- git commit
- scope deviations
- known issues

GLM should not need to rediscover the entire repository for every phase.

---

# 44. WHAT MUST BE PRESERVED ACROSS ALL PHASES

## One identity

Never create peer systems inside Raphael.

## One loop

Never create a second cognitive traversal.

## One security boundary

Never create a privileged execution shortcut.

## Evidence integrity

Never treat an assertion as a verified finding.

## Regression floor

Never weaken retained tests to manufacture a green phase.

## Controlled scope

Never expand the MVP because a convenient capability or module exists.

---

# 45. FINAL EXECUTION COMMANDMENT

```text
DO NOT ASK:
"What else can we add?"

ASK:
"What is the smallest change required to satisfy the current phase contract,
and what evidence will prove that it works?"
```

That is the governing rule for the entire Raphael program.


---

# 46. RISK REGISTER

This section incorporates the v4.1 risk-register requirement and adds RSI-specific triggers.

| Risk | Trigger | Detection / Control | Owner |
|---|---|---|---|
| Stale-map execution | implementation references shifted/absent audit path | halt-and-re-derive | implementation lane → GLM |
| Permanent migration seam | seam remains active while legacy branch exists past welding deadline | AM-4 weld inventory + G3 exit + import invariant | GLM |
| Floor-monotonicity gaming | tests weakened/skipped outside allowed deletion commit | diff review at every gate | GLM |
| Dual-loop coexistence | second cognitive entry point remains reachable | import-graph + single-runtime checks | GLM |
| Arena parity drift | P3/P4 weld changes arena behaviour | P7a divergence tracking | implementation + GLM |
| Escalation deadlock | repo reality conflicts with architecture contract | stop, document, escalate | both lanes |
| False RSI claim | persistence/learning/replay mistaken for recursion | P8/P10 admission tests | GLM |
| Replay/regeneration confusion | candidate evaluated on regenerated scenarios and called replay | replay-specific tests | implementation + GLM |
| Protected evaluator contamination | candidate changes evaluator/holdout logic | protected-surface registry + evaluator isolation | GLM |
| Policy lineage loss | successor lacks parent/hash/evaluation/rollback record | lineage validation | implementation |
| Unbounded learning | Student changes protected or unbounded state | delta caps + protected-surface tests | implementation |
| Deployment without independent evidence | replay win directly causes deployment | P7 promotion lock | GLM |

Each phase Evidence Package may append phase-specific risks.

---

# 47. CONCURRENCY AND CADENCE

1. Only one phase may be in `IN_PROGRESS` implementation status at a time.
2. P7a arena adapter preparation, Decepticon analysis, and pre-P8 evaluation-protocol design are the permitted planning tracks that may overlap with the active phase when they do not modify the active phase's canonical behaviour.
3. No maximum staleness window is imposed between implementation and review, but meaningful baseline drift triggers a lightweight re-verification pass using the same halt-and-re-derive rule as AM-1.
4. RSI candidate evaluation rounds are serial with respect to promotion. Candidate experimentation may be parallel offline, but only one authoritative promotion decision may advance the active policy lineage at a time.

---

# APPENDIX A — v4.2 RSI MECHANISM CONTRACT

## A.1 Canonical improvement loop

```text
EXPERIENCE
   ↓
DIAGNOSIS
   ↓
IMPROVEMENT HYPOTHESIS
   ↓
CANDIDATE POLICY / BOUNDED DELTA
   ↓
REPLAY EVALUATION
   ↓
PROTECTED HOLDOUT EVALUATION
   ↓
ACCEPT / REJECT
   ↓
PERSIST SUCCESSOR
   ↓
GOVERNED DEPLOYMENT
   ↓
NEW EXPERIENCE
   ↺
```

Every arrow must be evidenced before the corresponding RSI level is claimed.

## A.2 Replay contract

A compliant replay system must satisfy all of the following:

- recorded nodes are immutable for the evaluated replay round
- candidate policy reads only prefix-observable information
- branch/outcome responses come from recorded history
- replay never invokes real environment execution
- replay never changes protected evaluator logic
- replay selection is separate from holdout selection
- candidate and parent policies are evaluated under the same declared resource conditions

## A.3 Protected control line

```text
                 PROTECTED
────────────────────────────────────────
CapabilityBroker / PDP
PEP / exec authority
authorization semantics
Evidence authority
Provenance invariants
Single Runtime rule
Single loop rule
WorldModel belief authority
Protected evaluator / holdout
Promotion authority
Human release authority
────────────────────────────────────────
                 EVOLVABLE
ExplorationPolicy
candidate-generation policy
bounded strategy parameters
prompt/context assembly
knowledge weighting
experience-selection policy
```

The bottom region may evolve only through the governed improvement workflow. The top region is not an optimization target.

## A.4 Evidence required for claims

| Claim | Minimum evidence |
|---|---|
| Learning | verified outcome causes bounded state/proposal change |
| L2 | persistent exploration policy controls later exploration strategy |
| L3 | learner chooses admissible future experience under constraints |
| L4 | accepted successor is governed, deployed, retained, and rollbackable |
| L5 structural | improved improvement mechanism persists and governs a later improvement round |
| L5 effective | stronger successors under comparable budgets + independent unseen evaluation |

## A.5 Negative-result discipline

A failed improvement is still an improvement-system datum if the candidate, reason, evaluation, and rejection decision are preserved. Do not delete failed candidates merely because they are unsuccessful; they may be required to explain the search trajectory and prevent repeated waste.

## A.6 No prompt-guidance shortcut

Historical experience may be made available to replay as data/state. It must not be treated as equivalent to injecting hand-written semantic guidance into the next prompt and calling the result a replay-based improvement mechanism.

---

# APPENDIX B — RSI SOURCE SYNTHESIS ADOPTED BY RAPHAEL

## B.1 The Last AI Built by Humans

Adopted concepts:

- five-level progression from improvement-execution autonomy through improvement-strategy autonomy, experience-acquisition autonomy, environment-adaptation autonomy, and recursive meta-improvement
- structural recursion vs effective recursion distinction
- long-horizon evaluation dimensions: Adaptivity, Retention, Transfer, Efficiency, Stability, Meta-recursion
- importance of cross-component diagnosis, reliable learning signals, persistent state, governed adaptation, long-horizon evaluation, resource-aware improvement, and reproducible cross-round inheritance

Not adopted as a Raphael metric:

- HCI is not a Raphael gate score
- external ordering/ranking is not imported into RAPHAEL acceptance criteria

## B.2 Dream-RSI

Adopted concepts:

- exploration policy as an explicit meta-level improvement target
- completed discovery history as a replay simulator/world
- online exploration → history construction → offline dreaming → policy improvement → redeployment
- fixed agent/evaluator during policy improvement
- replay selection does not imply online generalization
- history-as-replay is distinct from semantic prompt guidance

Not adopted blindly:

- no copied code
- no assumption that Raphael's Arena already constitutes replay
- no assumption that replay alone proves future improvement
- no assumption that Raphael should make the full agent or evaluator self-modifiable

---

# APPENDIX C — RAPHAEL-RSI-002 AUDIT ADJUDICATION

**Audit status:** ACCEPTED.

**Mechanism-level current position:** governed execution substrate with a partial/unproven L1 execution slice; B0 for the improvement mechanism; L2–L5 absent until admission tests pass.

**Critical repository gaps validated by the audit:**

- canonical evidence/receipt/artifact stores are mostly write-only for learning purposes
- WorldModel/contradiction/Student stages contain disconnected or recording-only paths
- no first-class persistent ExplorationPolicy
- no candidate improvement evaluator
- no successor/promotion/rollback chain
- no true replay world
- no structural/effective recursion evidence
- PEP gate self-satisfaction requires remediation

**Roadmap consequence:** these are phase-gated engineering requirements, not reasons to skip G3 or to introduce an uncontrolled self-modification subsystem early.

---

# APPENDIX D — CURRENT OPERATING STATE

```text
VERSION:                v4.2
CURRENT REPO HEAD:      3b2e22db3d952622150d271c12c41d9ed21e81fd
CURRENT BRANCH:         weld-sub10-evidence
AM-4-R3:                NOT EXECUTED
G3:                     BLOCKED
RSI IMPLEMENTATION:     NOT STARTED
NEXT ENGINEERING STEP:  AM-4-R3
```

No later roadmap phase is authorized merely because its design is complete. Implementation remains sequential: **task → evidence → independent audit → gate → next task**.


# APPENDIX E — CONSOLIDATED ROADMAP PRECEDENCE

When documents or reports appear to conflict, use this order:

```text
1. Explicit superseding ADR / governance ruling
2. RAPHAEL MASTER ROADMAP v4.2 — this document
3. v4.1 AM-1…AM-14 inheritance summarized in §0.2
4. Earlier v4 roadmap wording
5. Historical audit reports / repository comments
6. Individual model suggestions
```

A model report can provide evidence that the roadmap is wrong, incomplete, or impossible in the current repository. It cannot silently rewrite the roadmap. The discrepancy becomes a governance question and is adjudicated before implementation continues.
