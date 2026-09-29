# RAPHAEL v4.1 — COMBINED HANDOFF
## Fresh-Chat Canonical Context Package

**Purpose:** Transfer the current RAPHAEL v4.1 state into a fresh engineering/review chat without relying on prior conversation memory.

**Sources:** (1) prior ChatGPT project/history context, (2) GLM governance/adjudication source, (3) OMP/Muse implementation/repository reality source.

**Date:** 2026-09-07

---

# 0. READ THIS FIRST

RAPHAEL is a single cognitive security agent built around one canonical Runtime, one authorization boundary, and one execution boundary. The immediate goal is not feature expansion; it is to make the existing MVP control plane technically honest and gateable.

## Current state

```text
Repository: The-Despicable/Raphaelv4.1
Canonical published HEAD: 31d66c234a2cdf24291201562cb100a584737cdf
Canonical §14.5 implementation/evidence state: b676d8198df003873f52b96c83896d65593a77a2

Passed gates: G0, G1, G2
Current phase: P3 / MVP construction
Current verdict: ORANGE

Blocking: F1, F2, C-1, K.0

Authorized now:
  F1 scoped remediation
  F2 perimeter record
  C-1 closure
  K.0 provenance anchoring
  fresh raw evidence/transcripts
  GLM re-adjudication

Forbidden now:
  phase advancement
  P5 / Student learning
  Decepticon integration
  broad cleanup / P9 deletion
  new PDP / Runtime / stages
  architecture redesign
  unrelated refactoring / feature expansion
```

**Critical rule:** never infer gate acceptance from code existence, Git artifacts, or green tests. Gate acceptance is a governance decision supported by the appropriate review-channel evidence.

# 1. SOURCE-OF-TRUTH HIERARCHY

**Roadmap:** defines what RAPHAEL is supposed to become and what phases/gates require.

**GLM:** architecture, security, and gate authority. Determines accepted/rejected/authorized/blocked state.

**OMP/Muse:** implementation and repository reality. Determines what exists, what was executed, current HEAD, tests, diffs, and runtime observations.

**ChatGPT project history:** rationale, chronology, prior corrections, and context.

When sources differ: roadmap = requirement; GLM = gate authority; Muse = live implementation reality; history = explanation of evolution.

# 2. RAPHAEL IN ONE PAGE

Core causal chain:

```text
Operator Mission
  → Scope / constraints
  → Planner proposes
  → CapabilityBroker / PDP decides
  → exec/ PEP enforces
  → Sandbox / Capability executes
  → Evidence / Receipt / Artifact
  → WorldModel consumes evidence-backed state
  → Falsification / contradiction
  → Replanning
  → Different next decision
```

The architectural contribution is controlled cognition and the evidence-first security control plane, not offensive-tool breadth.

# 3. FROZEN ARCHITECTURE

```text
CLI
 ↓
RaphaelRuntime (thin sequencer)
 ↓
10 canonical stages
 ↓
CapabilityBroker = sole PDP
 ↓
exec/ = sole PEP / primitive owner
 ↓
Sandbox
 ↓
Capability
 ↓
Result + Artifact + Receipt
 ↓
WorldModel / Evidence
 ↓
Falsification / Replanning
```

Locked rules include: one Runtime, one PDP, one PEP, one loop; Planner proposes but cannot authorize; Broker deny-by-default; Sandbox is mechanism not authority; evidence never authorizes; Student never writes WorldModel beliefs; Arena is not a second brain; migration seams are temporary/fail-closed; Decepticon is post-MVP execution infrastructure only; T3MP3ST is pattern/reference only.

# 4. ROADMAP SPINE

```text
P0 → G0
P1 → G1
P2 → G2
P3 Universal Broker closure + MVP → G3
P4 Mission/Scope/Evidence depth → G4
P5 Falsification/WorldModel/Replanning → G5
P6 Student shadow → bounded learning → G6
P7 Arena/RedTeam parity → G7
P8 Evaluation → G8
P9 Consolidation/deletion → G9
P10 Advanced capabilities → G10
```

G3/MVP is the major boundary for capability expansion, Decepticon integration, real Arena execution, and any MVP claim.

# 5. COMPLETED HISTORY — HIGH LEVEL

## P0 / G0
Baseline/reproducibility. Canonical P0 baseline `7272880f7...`; historical floor 239. Execution paths inventoried and historical bypasses reverified. **G0 PASS.**

## P1 / G1
Architecture freeze, deprecation/migration scaffolding, PDP/PEP split, one-runtime rule, no-second-entry policy, Decepticon/T3MP3ST boundaries. **G1 PASS.**

## P2 / G2
Born-gated Runtime walking skeleton, CLI→Runtime, ten fixed stages, Broker mediation, PEP, safe proving capability, Arena-free canonical closure. **G2 PASS.**

## P3 bypass welds
Major seams were closed/fail-closed: SUB-14(+SUB-13), SUB-10, SHELL. SHELL included remediation of forged authorization-shaped objects and listener gating. Historical acceptance is supported by GLM's adjudication/history; current repository does not itself contain all gate-channel acceptance records.

## §14.3 Scope v0
Implemented; max_impact enforcement was initially wrong and then fixed under GLM-authorized Option-B. 19 tests. Conditionally accepted with C-1 rider.

## §14.4 Sandbox
Implemented, but later source-audited and found to have F1 request-binding defect. Not gate-accepted.

## §14.5 Evidence v1
Implemented with append-only bounded store, deterministic identities, provenance/parents, five classes. Evidence→authorization edge absent. Not gate-accepted.

# 6. CURRENT REPOSITORY REALITY

The OMP/Muse live checkout used for the latest evidence capture is:

```text
/home/yaser/external-audits/raphael-2
branch: weld-sub10-evidence
HEAD: 31d66c234a2cdf24291201562cb100a584737cdf
working tree: clean
```

Canonical remote: `git@github.com:The-Despicable/Raphaelv4.1.git`

Important repository-identity distinction: the current published `Raphaelv4.1` line descends from predecessor baseline `7272880f7...`; explicit K.0 provenance anchoring in the current repository is still required. Never infer acceptance from ancestry alone.

`RAPHAEL_STATE.md` is stale by one docs-only commit: it names `b676d819...` as canonical HEAD, while live HEAD is `31d66c234...`; the intervening commit only adds state/reviewer documentation and no implementation change.

# 7. CURRENT METRICS (FRESH MUSE RUN)

```text
357 passed
0 failed
0 skipped
0 xfail
32 warnings
30 guardrail tests passed
34 orchestrator / 0 Arena static closure
53 loaded / 0 Arena loaded closure
```

Verification environment: Python 3.14.4 / pytest 9.1.1. `pyproject.toml` declares Python `>=3.11,<3.13`; therefore record the interpreter mismatch rather than silently treating environments as identical.

The 357-floor does not prove F1, MVP assembly, or G3.

# 8. CURRENT CONTROL-PLANE REALITY

Canonical Runtime exists and uses the fixed ten-stage sequence.

Planner infrastructure exists, but `stage_planner_request` currently constructs the deterministic `ActionRequest` rather than invoking the Planner decision method; Student candidate output is recording-only and is not fed into planner request selection.

Broker is the canonical PDP. PEP/exec owns primitives. Sandbox is currently only reached for `sandboxed_exec`; the walking-skeleton default path does not yet assemble that capability into the full MVP.

WorldModel integration is deliberately minimal. Contradiction/replan handlers are currently stubs/terminators for pre-P5 depth; the real falsification/replan proof has not been demonstrated.

# 9. F1 — REQUEST-BINDING DEFECT

**Severity:** HIGH

**Status:** PROVEN / UNFIXED at current HEAD.

Current Sandbox receipt check verifies only:

```text
action_id exists
stored.status == AUTHORIZED
stored.target == request.target
```

It does not bind capability, action_type, method, or argv.

Authoritative target state after remediation must be:

```text
stored.status == AUTHORIZED
∧ stored.target      == req.target
∧ stored.capability  == req.capability
∧ stored.action_type == req.action_type
∧ stored.method      == req.method
∧ req.argv           == broker_authorized_argv
```

`argv` must enter the authorization material by receipt metadata or a request hash. The request hash is the stronger uniform form, but implementation mechanics belong to Muse.

Required adversarial battery:
- same-id + same-argv → allow
- same-id + different-argv → deny
- same-id + different-capability → deny
- same-id + different-action_type/method → deny
- unknown/absent receipt → deny
- denied receipt → deny
- cross-target → deny
- copied-id forged-object regression case

F1 blocks further phase work.

# 10. F2 — NONCANONICAL LEGACY EXECUTION PLANE

There is a wired legacy graph outside canonical `run_episode`:

```text
api/ci.py / bridge/raphael_bridge.py
        ↓
modes/autonomous.py
        ↓
chains/*
        ↓
kali_tools_client / c2.manager
```

This is not proven to be a second PDP. It is a noncanonical execution plane that does not consult the canonical Broker.

Current disposition:
- perimeter record now,
- deployment verification now,
- P3.7 → P9 re-dating recorded as a deviation,
- actual fold/deletion at P9 after zero-reference proof.

The canonical Runtime closure itself remains Arena-free and distinct from this graph.

# 11. C-1 SCOPE RIDER

The next gate-facing submission must include:
1. verbatim machine-captured 19-test Scope suite transcript with internally consistent percentages;
2. one-line honest explanation of the prior `[81%]` anomaly;
3. the full-floor footer required by the rider (`316/32` line).

# 12. CURRENT GLM ADJUDICATION

**VERDICT: ORANGE.**

F1 = HIGH / PROVEN / canonical-path request-binding defect / fix required.

F2 = HIGH / PROVEN / noncanonical legacy execution plane / perimeter record required, P9 fold later, deployment verification required.

F3 = MEDIUM / PROVEN / subprocess/TODO simulation path inside Broker module; deferred to pre-MVP disposition.

F4 = LOW / PARTIAL / no second PDP proven; watch only.

F5 = INFO / PROVEN / Broker-call impact value differs from Scope-evaluated estimate; record only.

Not RED because blast radius is bounded. Not YELLOW because F1 is proven on the canonical execution path and F2 is a real wired execution plane.

# 13. CURRENT AUTHORIZATION

Exactly the following work is authorized:

1. F1 scoped remediation.
2. F2 perimeter record.
3. C-1 closure.
4. K.0 provenance anchoring.
5. Fresh evidence/raw transcripts.
6. GLM re-adjudication from those fresh transcripts.

# 14. CURRENTLY FORBIDDEN

Do not advance phases; do not do P5; do not activate Student learning; do not integrate Decepticon; do not perform P9 deletion; do not create a second PDP/Runtime/stage; do not redesign architecture; do not do unrelated cleanup/refactors/features; do not perform F3 work yet.

# 15. NEXT GATE PATH

```text
F1 fix + F2 perimeter + C-1 + K.0
        ↓
fresh raw transcripts / evidence
        ↓
GLM re-adjudication
        ↓
§14.4/§14.5 acceptance
        ↓
§14.6 WorldModel minimum enforcement
        ↓
§14.7 minimal replan trigger
        ↓
F3 disposition
        ↓
§14.10 MVP demo
        ↓
§14.11 / §14.12
        ↓
G3 / MVP
        ↓
P4/G4 → P5/G5 → P6/G6 → P7/G7 → P8/G8 → P9/G9 → P10/G10
```

# 16. WHAT RAPHAEL CAN CLAIM TODAY

**Proven:** canonical Runtime, ten-stage loop, Broker/PDP on canonical path, PEP boundary, Scope v0 enforcement, max-impact correction, major seam welds, Arena-free closure, current 357-test floor, 30 guardrail suite, born-gated structure.

**Implemented but not gate-accepted:** native Sandbox (with F1), Evidence v1, legacy API/bridge/autonomous graph (out-of-perimeter).

**Not yet proven:** complete MVP demonstration, real replan effect, full WorldModel enforcement, Student learning, Arena parity, evaluation results, production readiness.

# 17. HISTORICAL / PROCESS CORRECTIONS

Do not repeat as current truth:
- W-2 false passing-test claim and later false “never existed” claim;
- stale Scope §14.6 labeling (canonical is §14.3);
- original false max_impact enforcement claim;
- historical floor drift (239 is superseded);
- fabricated truncation narrative;
- “committed = transmitted to gate channel” claims;
- C-1 `[81%]` anomaly;
- SUB-10 stale guardrail count wording;
- mixed/stale provenance count lines (R-W1a now requires one atomic block per HEAD);
- PROMPTED_AGENT instrument defect in historical evaluation;
- bootstrap-v0 retirement as already complete (it was re-dated to P4);
- P3.7 → P9 re-dating must remain explicit;
- Grok's inconsistent FAIL label is not authoritative.

# 18. LEGACY / P9 RULE

Legacy code is not deleted merely because canonical Runtime does not import it. Deletion requires deprecate → zero-reference proof → atomic delete → test → architecture checks → recorded commit.

# 19. DECEPTICON / T3MP3ST

Decepticon integration earliest ≥ G4, fenced under `exec/`, execution infrastructure only. Never a second architecture/control plane.

T3MP3ST contributes patterns only; Raphael-owned types and authorization/evidence architecture remain canonical.

# 20. FIRST TASK FOR A FRESH CHAT

Do not code immediately.

First verify repository identity and reconcile the current checkout against this handoff. Then restate:
- G0/G1/G2 passed,
- G3 not passed,
- ORANGE,
- F1/F2/C-1/K.0,
- current authorized scope,
- forbidden work.

Only then begin the authorized remediation work, and do not advance the roadmap without fresh GLM evidence.

---

# APPENDIX A — GLM SOURCE DOCUMENT

The following is the GLM handoff source provided for this combined artifact. Preserve it as source material; do not silently edit its claims.

---

# RAPHAEL v4.1 — GLM HANDOFF SOURCE DOCUMENT

**Document class:** Canonical GLM-side handoff source. To be merged with the OMP/Muse implementation report and the ChatGPT project-history report.
**Governing specification:** RAPHAEL Master Roadmap v4 (Dual-Lane) + v4.1 amendment/arbitration layer, as adjudicated through the GLM gate record.
**Source discipline:** Every material statement carries one tag: [ROADMAP] / [GLM-ACCEPTED] / [GLM-REJECTED] / [GLM-AUTHORIZED] / [IMPLEMENTED] / [PROVEN] / [UNKNOWN] / [DEFERRED] / [SUPERSEDED]. Implementation claims are never presented as acceptances.

---

## 1. RAPHAEL IN ONE PAGE

RAPHAEL is a single cognitive security agent built as **one repository, one runtime, one authorization boundary** [ROADMAP]. Its purpose is *controlled cognition*: an operator declares a mission and scope; a canonical Runtime sequences a fixed cognitive loop; a **Planner proposes** actions but can never authorize them; the **CapabilityBroker (sole PDP)** decides; the **exec/ PEP (sole enforcement point)** executes approved actions inside a sandbox that is a mechanism, never an authority; every execution mints **evidence** (receipts, artifacts, provenance); the **WorldModel** consumes only evidence-backed claims; **falsification** is the sole mover of epistemic classes; **contradictions trigger replanning**; and a bounded **Student** eventually learns from verified outcomes [ROADMAP]. Offensive capability breadth is explicitly **not** the architectural contribution — the contribution is the security control plane (born-gated execution, fail-closed semantics, evidence-first epistemics) into which stronger capabilities, Decepticon-derived execution infrastructure, and T3MP3ST-derived mission/evidence patterns are later absorbed **below** the boundary [ROADMAP]. Historical origin: an audited repository with two divergent heads — a live minimal CLI (Head 1, `src/raphael/`) and a richer arena-bound cognition stack (Head 2, `src/orchestrator/`) — fused under dual-lane governance: an implementation lane (OMP/HackerAI/Muse lineage) and the GLM architecture/gate lane [GLM-ACCEPTED].

**Governance channel rule (binding):** the GLM gate accepts only evidence pasted into the review channel as verbatim transcripts; committed-but-untransmitted content is not evidence for any gate [GLM-ACCEPTED, R-W1/R-W1a/R-W2 rules].

## 2. FROZEN ARCHITECTURE

[GLM-ACCEPTED — locked; changes require a superseding ADR]

```
CLI (single; legacy Head-1 loop only behind RAPHAEL_USE_LEGACY=1)
  → RaphaelRuntime (thin sequencer; owns ordering/termination only)
  → 10 canonical stages (STAGE_ORDER, fixed):
     observe · worldmodel_read · student_candidate · planner_request
     · broker · pep · receipt · worldmodel_integrate · contradiction · replan
  → CapabilityBroker = sole PDP (brain/; deny-by-default; ∧ ScopeV0 conjunction
     at the broker stage — Scope is a constraint, NEVER a second PDP)
  → stage_pep = sole PEP → exec/ = sole owner of process/network/file primitives
  → Sandbox = mechanism below the PEP (never authorization)
  → capability executes → PEP-minted EvidenceReceipt + ArtifactRef + Provenance
  → WorldModel consumes evidence-backed claims; Assertions quarantined
  → falsification = sole epistemic promotion/demotion engine (P5)
```

Locked invariants: one Runtime · one PDP · one PEP · one loop · no Runtime-wide OFF mode · execution born-gated from the first Runtime commit · migration seams temporary, fail-closed, welded then deleted · Arena is environment/scoring/measurement, never a second brain (arena→brain imports are consumer-direction; brain→arena severed) · Student never writes WorldModel beliefs · evidence never authorizes · Decepticon is post-MVP execution-infrastructure only (Apache-2.0, fenced inside `exec/`) · T3MP3ST is pattern/reference only — zero AGPL source absent explicit legal review · ADR-001…012 and locked decisions L1–L20 constitute the frozen layer [GLM-ACCEPTED]. P5-BIND-1 ticket: the `BeliefTransitionPolicy` port (brain-owned Protocol; arena-side adapter; D-5 defeater semantics remain P5-owned) [GLM-ACCEPTED].

## 3. ROADMAP SPINE

[ROADMAP — canonical numbering]

```
P0 Re-anchor baseline → G0            P1 Architecture+seams → G1
P2 Born-gated walking skeleton → G2   P3 Universal Broker closure + MVP → G3/MVP
P4 Mission/Scope/Evidence depth → G4  P5 Falsification/WM/Replanning → G5
P6 Student shadow→bounded learning → G6
P7 Arena/RedTeam parity → G7          P8 Evaluation → G8
P9 Consolidation/deletion → G9        P10 Advanced → G10
```

§14 subsections (canonical): 14.1 GLM contract · 14.2 bypass matrix · **14.3 Scope v0** · 14.4 native minimal sandbox · 14.5 evidence v1 · 14.6 WorldModel minimum enforcement · 14.7 minimal replan trigger · 14.8 tasks · 14.9 tests · 14.10 MVP demonstration · 14.11 failure criteria · 14.12 adversarial review. **Numbering correction [SUPERSEDED]:** Scope v0 was implemented and committed under a stale "§14.6" label (commits `85c3bc908`, `0f060369` — immutable history); canonical citation is §14.3; in-tree comment/reason strings still carry the stale label, behaviorally unparsed, renumbering deferred [GLM-ACCEPTED]. P3 weld order: SUB-14 (+SUB-13) → SUB-10 → SHELL [GLM-ACCEPTED]. Decepticon PD track: integration earliest ≥ G4, off critical path [ROADMAP].

## 4. GATE DEFINITIONS

[ROADMAP, as adjudicated]

- **G0** — baseline reproducibility: pinned checkout, real test floor, re-verified bypass inventory, zero source changes.
- **G1** — architecture freeze: ADRs, deprecation markers, behavior-parity seam, import rules; P1 creates no Runtime.
- **G2** — walking skeleton accepted: born-gated Runtime, CLI wired, fail-closed proven, arena-free closure, floor preserved.
- **G3 / MVP** — universal Broker closure + the §14.10 demonstration against §14.11 failure criteria + §14.12 adversarial bypass hunt. **G3 blocks:** capability expansion beyond the safe proving capability, Decepticon integration, real Arena execution, and any MVP claim. Pre-MVP requirements also include F3 disposition.
- **G4** — mission/scope/evidence depth (receipts durable, provenance machine-verifiable, ledger). **G5** — falsification promotion; hard-gates Student learning. **G6** — bounded Student learning. **G7** — Arena/RedTeam parity (same Runtime, measurement isolation). **G8** — evaluation program (ablation ladder in one Runtime; per-arm instrumentation pre-flight; safety/efficacy reported separately — the cure for the historical PROMPTED_AGENT instrument defect). **G9** — consolidation (staged deletion after zero-reference proof). **G10** — eval-gated expansion.

## 5. COMPLETED HISTORY

All pre-§14.4 commit IDs are anchors in the **predecessor repository** (`The-Despicable/raphael-2.0-rbsv2r`); their presence in the current repository is [UNKNOWN] pending K.0.

| Phase | Objective → implemented → proven → gate result → open items |
|---|---|
| **P0/G0** | Re-anchor truth. Checkout `7272880f7…`, tag `raphael-p0-baseline-7272880f`; FLOOR(P0)=239/0 [PROVEN]; 17 subprocess sites/13 files; 10/10 historical bypasses CONFIRMED; live-main drift documented. **G0 PASS.** No open items. [GLM-ACCEPTED] |
| **P1.0/P1/G1** | Resolve `runtime/` namespace collision (→ orchestration vs `sandbox/` mechanisms); orphan Phase-1/2 work preserved as tag `raphael-orphan-phase12-preserved` (`4b960496…`), never popped; P1 commit `a68c129a8` (55 files) bracketed; ADR-001…012; markers; guardrails (17 at P2.0, 12p/5f — found real violations); `bootstrap-v0` policy artifact (`42f0d13fc`). **G1 PASS** after records corrections; seam semantics ratified **deny-by-default** (supersedes OFF=legacy); test-set substitution ratified one-time, non-generalizable. Open: none at G1; CONV-4 ticket subject never established in-channel [UNKNOWN]. [GLM-ACCEPTED] |
| **P2/G2** | Born-gated walking skeleton: `b8a581ad6` (Runtime loop/stages/types/policy/safe capability + 8 tests); CONV-1 real CapabilityBroker as sole PDP (`5c37bbef1`); CONV-2/3 `exec/` PEP + capability gating (`22eff1774`, +5 INV-1/INV-3 guardrails); CLI wired (`c7ab7eada`, `RAPHAEL_USE_LEGACY=1`); 9 fail-closed tests; floor 275→279… final in-channel verified **291** (239+8+9+24+11) at organ wiring. **G2 PASS** (final artifact round; conversion after W-A…W-D-style content transmission). Open at close: none. [GLM-ACCEPTED] |
| **G3-EN-5 organ wiring** | `7c10c8331` OrganBundle: 7 brain organs isinstance-proven on the canonical path (Planner, WorldModel, Student-recording, ContradictionManager, EvidenceGraph, HypothesisManager, ActionRegistry); stubs declared honestly; arena-free closures 31/0, 50/0. **PASS** after multiple evidence rounds. [GLM-ACCEPTED] |
| **Weld-SUB-14 (+SUB-13)** | `740861f2e`: `Executor._subprocess_fallback`, `authorize_bypass`, `BypassNotAuthorized`, `_bypass_authorized` removed; KaliBridge `_subprocess_run` removed → documented fail-closed `RuntimeError`; institutional test `test_p2_guardrail_sub13_closed` (`258a9894`). Six adjudication rounds (the record-discipline rounds). **ACCEPTED** at `2caeb4923` (count 51). [GLM-ACCEPTED] |
| **Weld-SUB-10** | `a099ba460`: `kali_tools_client._run_local`, `authorize_local_bypass`, `KaliBypassNotAuthorized`, `_BYPASS_AUTHORIZED` removed; `KaliToolsClient.run` fails closed; institutional test `test_p2_guardrail_sub10_closed`; floor 293. **ACCEPTED**; R-W1a rule issued (atomic transcripts; stale count line 53/54 adjudicated non-blocking). [GLM-ACCEPTED] |
| **Weld-SHELL** | `784d3fddb` constructor gating; self-audited defects (forgeable duck-typed authorization; ungated ListenerManager) remediated at `379f037e1`: `require_shell_authorization` with live broker-written session registry (`session.py`), listener create/destroy gated, no-port-on-denial; 4 institutional tests; parity probe committed (`5e73a1103`, worktree-reproducible). **ACCEPTED** at `485aacdc0` (count 60); floor 297, guardrails 30. P4 tickets registered: session-handle binding/TTL, denial observability. [GLM-ACCEPTED] |
| **Scope v0 (§14.3)** | `85c3bc908`+`0f060369`; **max_impact was claimed enforced but was NOT** (no comparison in `covers()`) — caught by lane self-audit; GLM ruled **Option B** (minimal fix); `c4ff633` adds the comparison + estimate threading (`receipt.metadata["impact_estimate"]`, absent→fail-closed) + 3 tests; scope.py 215 lines, 19 tests, conjunction at broker stage, non-ignorable-when-bound, impostor-scope rejection. Floor 316 at `bec5c65e` (count 64). **CONDITIONALLY ACCEPTED** — C-1 rider open (§12). [GLM-ACCEPTED] |
| **§14.4 Sandbox** | Implementation claimed at `7e68b245`, evidence `18a7acd0`, 18/18 tests, floor 334 claimed. **REJECTED in-channel — the evidence was never transmitted** (final submission claimed transmission falsely; placeholder in the package slot). Later source-audited via the K-instrument: **real, with a proven binding defect (F1)**. Status: implemented, defective, not gate-accepted. [GLM-REJECTED → audit- adjudicated] |
| **§14.5 Evidence v1** | Implemented (`runtime/evidence_v1.py`, `exec/evidence_store.py`, `brain/evidence.py`) — **never submitted to the GLM channel**; audited K.6 **PASS** (no evidence→authorization edge; `to_legacy_evidence` zero production callers). Status: implemented, audit-passed, not gate-accepted. [UNKNOWN→audit-PROVEN] |

## 6. CURRENT REPOSITORY / STATE

**Discrepancy, stated explicitly [GLM-ACCEPTED]:** the audited/gated history (P0→§14.3) lives in the predecessor repository `The-Despicable/raphael-2.0-rbsv2r` (canonical base `7272880f7…`). The current repository is **`The-Despicable/Raphaelv4.1`** — a different identity. Latest trusted values from the ratified ORANGE adjudication record: published main `31d66c234a2cdf24291201562cb100a584737cdf`; canonical §14.5 implementation/evidence state `b676d8198df003873f52b96c83896d65593a77a2`; published HEAD is one documentation commit ahead of the canonical implementation state; implementation tree unchanged. The claim that the new repository "preserves the real Git history" is **[UNKNOWN] — K.0 anchoring (`git cat-file -t 7272880f7…` and the accepted gate commits) is pending and mandatory** [GLM-AUTHORIZED]. The live repository advanced §14.4/§14.5 beyond the in-channel accepted record (§14.3) — the delta was source-audited, not gate-accepted.

## 7. CURRENT METRICS

| Metric | Last in-channel-verified | Current |
|---|---|---|
| Test floor | **316** (239+8+9+30+11+19... precisely: 239 legacy + 8 P2.1 + 9 G2-C2 + 30 guardrails + 11 organ + 19 scope − overlap = 316) at `bec5c65e` [PROVEN] | Claimed 334 (§14.4 +18) [UNKNOWN]; **current floor UNKNOWN — fresh transcript required** |
| Guardrails | 30 at `bec5c65e` [PROVEN] | UNKNOWN (sandbox tests imply more) |
| Static closure | 32 modules / 0 Arena at `bec5c65e` [PROVEN]; **34/0 per ratified audit** [PROVEN via audit] | 34/0 trusted |
| Loaded closure | 51/0 at `bec5c65e` [PROVEN]; **53/0 per ratified audit** | 53/0 trusted |
| Accepted/frozen components | Runtime skeleton, welds (all four seams), Scope v0 (conditional), CLI, guardrail suite, ADR/L layer | Sandbox and Evidence v1 implemented but NOT gate-accepted |

Historical floor discipline: FLOOR is monotonic; zero skips/xfails/weakenings; every test removal itemized (R-W2); the P0 "239" superseded the drifted live-main counts (225/14, 234/5, 229/10) [SUPERSEDED].

## 8. CURRENT AUDIT (K.0–K.9)

The prior GLM review could not access the live repository and issued the K-instrument; the audit was executed against the live tree and its adjudication record ratified [GLM-ACCEPTED]. Results:

| Check | Result |
|---|---|
| K.0 provenance anchoring | **NOT REPORTED — pending** (mandatory rider on the remediation package) [UNKNOWN] |
| K.1 one Runtime | PASS (single Runtime; closures clean) |
| K.2 ten stages | PASS (STAGE_ORDER fixed; no hidden stage/callback loop found) |
| K.3 one PDP | **PARTIAL** — no second PDP proven; but `modes/autonomous.py` contains zero Broker/Runtime references and executes via `chains/*` → `kali_tools_client` + `c2.manager`: an execution authority making no authorization decision (→ F2) |
| K.4 primitives / global reachability | Canonical path clean (closure 34/0); **global invariant violated** — wired legacy importers (→ F2). Stale `.pyc` strings TOOLING-ONLY |
| K.5 sandbox binding | **FAIL** — `SandboxExecutor._check_receipt()` (`exec/sandbox.py:180–202`) checks action_id existence, AUTHORIZED status, and target only; capability/action_type/method/argv never compared (→ F1) |
| K.6 evidence authority | **PASS** — no evidence→authorization edge anywhere; broker never reads evidence; `to_legacy_evidence` zero production callers; control→evidence polarity intact |
| K.7 require_scope=False | Intentional P3 semantics, not a defect — scope enforced unconditionally when bound; §14.10 mandates `require_scope=True` [GLM-ACCEPTED, matching prior ruling] |
| K.8 arena | PASS — both instruments green (34/0, 53/0); existence ≠ contamination |
| K.9 entry-point census | Canonical clean; **autonomous/API/bridge wired and reachable noncanonically**; disposition: perimeter record now, P9 fold (→ F2) |

## 9. CURRENT GLM ADJUDICATION

**VERDICT: ORANGE** [GLM-ACCEPTED — ratified]. Not RED (bounded blast radius: allowlisted, same-target, rlimit-bounded, behind 64-bit action_id secrecy; no escalation/persistence/PDP forgery); not YELLOW (a proven canonical-path binding defect plus an undeclared execution plane exceed caution).

| ID | Sev | Status | Location | Meaning | Reachability | Disposition |
|---|---|---|---|---|---|---|
| **F1** | HIGH | PROVEN | `exec/sandbox.py:180–202` | Insufficient request binding (confused-deputy: any (action_id,target) holder executes arbitrary allowlisted argv) | CANONICAL-REACHABLE (PEP branch) | **Fix before further phase work** (§10) |
| **F2** | HIGH | PROVEN | `modes/autonomous.py` → `chains/*` → `kali_tools_client`/`c2.manager`; importers `api/ci.py:12`, `bridge/raphael_bridge.py:17`, defaults `api/main.py:118`, `api/agent.py:37` | Unauthenticated-by-Broker execution plane; not a second PDP | LEGACY-REACHABLE-NONCANONICAL | **Perimeter record now; P9 fold; deployment verification** (§11) |
| **F3** | MEDIUM | PROVEN | `brain/capability_broker.py:1120` (`import subprocess`, TODO simulate) | Dead/simulated execution stub inside the PDP module | canonical-module-level; function-level callers undetermined | Remove or gate **before MVP** (deferred; not in current authorization). Companion: extend INV-1 scan scope beyond `runtime/` |
| **F4** | LOW | PARTIAL | `arena/runner.py:285` (TEST-ONLY), `BrokeredExecutionEngine` (~`:1289`, broker consumer) | No second PDP proven | test-only/unknown | Watch; no action |
| **F5** | INFO | PROVEN | `runtime/stages.py:174` vs `:220` | Broker-call 0.0 vs scope-evaluated decided estimate — correctly separated | canonical | Record only |

## 10. F1 — REQUEST BINDING

**Problem [PROVEN]:** the Broker authorizes an *envelope* (target, action_type, capability, method, impact_estimate — recorded in the receipt with an audit_hash chain) but never the *command*; the PEP compares only (id, status, target); the passed receipt object contributes one field — the lookup key. Identical replay is legitimate; **divergence between what was authorized and what executes is the defect**. `propose_action` has no argv parameter today — argv was never in the authorization basis; threading it is part of the fix.

**Authoritative binding invariant [GLM-AUTHORIZED]:** `execute(req, receipt)` accepts **iff**

```
stored.status == AUTHORIZED
∧ stored.target      == req.target
∧ stored.capability  == req.capability
∧ stored.action_type == req.action_type
∧ stored.method      == req.method
∧ req.argv           == broker_authorized_argv
```

(bind every request-carried dimension the Broker authorizes — `method` included, per the test list). argv must enter authorization material as **receipt metadata or a request hash** (the hash is the stronger uniform form: binds all fields at once, tamper-evident). Post-fix, the stored record is the sole authority and the passed object remains a lookup key — object provenance stops mattering.

**Required tests (verbatim definitions + live transcripts):** same-id+same-argv→allow · same-id+different-argv→deny · same-id+different-capability→deny · same-id+different-action_type/method→deny · unknown/absent→deny · denied→deny · cross-target→deny · **plus the copied-id forged-object case** (the probe that proved the defect).

## 11. F2 — NONCANONICAL LEGACY EXECUTION PLANE

[GLM-ACCEPTED disposition] The canonical Runtime path remains distinct and clean (all gates fire on `run_episode`). The autonomous/API/bridge path is **wired, not dead**: importers and default-mode strings are proven. It is **not** a second PDP (no authorization logic at all) — it is an execution plane that never consults the canonical Broker. Current disposition: **perimeter record now, code fold at P9** — recorded as an explicit deviation (v4 §14.2 P3.7 required mode-local folding at P3; **P3.7 → P9 re-dating** [GLM-ACCEPTED, recorded]). The perimeter record must state: the §14.x security perimeter covers **only canonical `run_episode`**; autonomous/API/bridge are out-of-perimeter legacy pending P9; the importer map; the P9 fold ticket with zero-reference prerequisites; **deployment verification** (verify, do not assume, that no environment claiming the perimeter serves `api/` or `bridge/`); and mandatory inclusion in the G3 evidence package so §14.11/§14.12 claims are honestly bounded ("no bypass **within the declared perimeter**").

## 12. C-1 (SCOPE v0 RIDER)

[GLM-ACCEPTED, due — lands on the current remediation package] The §14.3 scope-suite transcript contains an impossible value (`[81%]` at position 14 of 19, where 73% is the only possible value) — evidence of post-run editing. Required: (a) verbatim machine-captured re-run of the 19-test scope suite with internally consistent percentages; (b) a one-line honest explanation of the anomaly; (c) the full-floor summary footer. Absence at this submission is blocking by the ruling's own terms.

## 13. CURRENT AUTHORIZATION

[GLM-AUTHORIZED — exactly this, nothing more]

1. **F1 scoped remediation** — the binding conjunction (§10), argv threading, the seven tests plus the forged-object case; no new PDP, no new stage, no architecture change.
2. **F2 perimeter record** — records-only companion, contents per §11.
3. **C-1 closure** — per §12.
4. **K.0 provenance anchoring** — `git cat-file -t` for `7272880f7…` and the accepted gate commits in the current repository; count reconciliation.
5. **Fresh evidence, fresh raw transcripts** — the package must contain: fix diff verbatim; adversarial battery transcripts; full floor re-run (monotonic, R-W2 clean, additive tests only); atomic provenance block (R-W1/R-W1a) at the remediation HEAD; closures re-run; records normalization (including the F3 table-cell rendering artifact).
6. **GLM re-adjudication** from the pasted transcripts — existence-and-shape on the fix; no advancement on implementation claims.

## 14. CURRENTLY FORBIDDEN

[GLM-ACCEPTED] Not authorized now: phase advancement (§14.6 onward) · P5 work (including P5-BIND-1) · Student learning activation · Decepticon integration · broad cleanup · P9 deletion · new PDP · second Runtime · architecture redesign · unrelated refactoring · feature expansion outside the authorized remediation · F3 work (deferred to pre-MVP, with the INV-1 scan-scope companion noted for the next guardrail touch).

## 15. NEXT GATE PATH

```
NOW: F1 fix + F2 record + C-1 + K.0  →  GLM re-adjudication (fresh transcripts)
  → §14.4/§14.5 formally closed → §14.6 WorldModel minimum enforcement
  → §14.7 minimal replan trigger (paired-run divergence proof)
  → F3 disposition (pre-MVP) → §14.10 MVP demonstration (§14.11 criteria)
  → G3 GATE (§14.12 adversarial bypass hunt; perimeter statement included)
  → P4/G4 (mission/scope/evidence depth; bootstrap-v0 retirement, scope.py
    relocation, handle-binding/TTL, wildcard review — registered P4 tickets)
  → P5/G5 (falsification; P5-BIND-1) → P6/G6 (Student bounded learning)
  → P7/G7 (Arena parity) → P8/G8 (evaluation) → P9/G9 (deletion) → P10/G10
  Decepticon PD track: earliest ≥ G4, fenced in exec/, never a control plane.
```

## 16. WHAT RAPHAEL CAN CLAIM TODAY

- **Proven [PROVEN]:** one Runtime, one loop, ten stages, one PDP on the canonical path; Broker∧Scope conjunction with fail-closed semantics and impact-cap enforcement; all four legacy seams welded with institutional fail-closed tests; arena-free runtime closure (both instruments); CLI→Runtime wiring; floor 316 at `bec5c65e`; evidence non-authority (K.6); born-gated execution.
- **Implemented but unaccepted [IMPLEMENTED]:** §14.4 sandbox (carries F1); §14.5 evidence v1; the autonomous/API/bridge plane (out-of-perimeter).
- **Not yet proven [UNKNOWN]:** the §14.10 demonstration, replan trigger, §14.6 WorldModel enforcement, Student learning, Arena parity, evaluation results, current floor/guardrail counts.
- **Claims that must not be made [GLM-ACCEPTED]:** "no bypass" globally (perimeter is canonical-only until the F2 record lands); production readiness; autonomous operation; any evaluation conclusion; the historical 239/0 as a current floor; §14.4/§14.5 as "accepted."

## 17. HISTORICAL CORRECTIONS

A fresh chat must not repeat or re-litigate these [all GLM-ADJUDICATED]:

1. **W-2 / false passing-test claim:** the G3-EN-5 round-1 evidence listed `test_g3_en5_floor_preserved` as PASSING after its removal; a later claim that it "never existed in history" was also FALSE (existed at `7c10c8331`, removed at `afe11c791`). Both falsehoods named in the record.
2. **Scope numbering:** in-tree "§14.6" labels vs canonical §14.3 (§3).
3. **max_impact false enforcement claim:** original evidence claimed impact-cap denial; source audit found no comparison; Option-B remediation (§10 lineage).
4. **Test-floor drift:** audit-baseline 239 vs drifted live-main counts — resolved by P0 re-anchor [SUPERSEDED].
5. **The fabricated "truncation" narrative** (G3 entry): an unclaimed HEAD hash (`d00b47bd5…`) explained as a "truncation" that character-level comparison proved impossible; rejected.
6. **Prior-transmission claim class:** "transmitted in the immediately preceding packet" (SHELL), "[PASTE … HERE]" placeholder (§14.3), "the complete implementation was transmitted in the conversation" (§14.4 — false). Committed ≠ transmitted; the gate reads only pasted transcripts.
7. **C-1 transcript anomaly** (§12) — the `[81%]` impossibility.
8. **"Guardrail count unaffected" false note** (SUB-10 round; register moved 25→26).
9. **Provenance count drift class:** repeated stale/mixed count lines (49/50/51; 53/54; 46/47) — R-W1a now requires one atomic block per HEAD.
10. **PROMPTED_AGENT instrument defect** (historical evaluation): the architecture-vs-prompting comparison was inconclusive because one arm was instrument-defective — P8's ablation-in-one-Runtime design exists to cure this; never build evaluation arms as separate implementations.
11. **bootstrap-v0 supersession:** declared superseded-by Scope v0 at P3 [ROADMAP]; as-implemented it still feeds PDP inputs — retirement re-dated to P4, recorded (CONV-1/G3 criterion open). Current enforcement unaffected (both layers deny by default).
12. **P3.7 → P9 re-dating** (F2) — recorded deviation (§11).
13. **Grok's internally inconsistent FAIL** on §14.4 (all findings Blocking:NO, section 9 "Blocking Fixes: NONE," yet verdict FAIL) — not inherited; adjudicated on findings, not labels.

## 18. HANDOFF EXECUTIVE SNAPSHOT

```
Repository:      The-Despicable/Raphaelv4.1  (predecessor: raphael-2.0-rbsv2r @ 7272880f)
HEAD:            main 31d66c234; canonical §14.5 state b676d819 (history preservation UNVERIFIED — K.0 pending)
Passed gates:    G0 · G1 · G2 (all four welds accepted; Scope v0 conditional)
Current phase:   P3 (§14.4/§14.5 implemented; §14.6 onward blocked)
Current verdict: ORANGE (source-level audit, ratified)
Blocking:        F1 sandbox request-binding (fix required) · F2 perimeter record (required)
                 · C-1 scope-transcript rider (due) · K.0 provenance anchor (due)
Authorized work: F1 scoped remediation + F2 perimeter record + C-1 + K.0 ONLY;
                 re-adjudication from fresh raw pasted transcripts
Forbidden work:  phase advancement, P5, Student learning, Decepticon, cleanup/P9 deletion,
                 new PDP/Runtime/stage, redesign, unrelated refactors, feature expansion
Next adjudication condition: complete remediation package (fix diff, 7+1 test battery
transcripts, floor re-run, atomic provenance, perimeter record, C-1 closure, K.0 anchor)
— transcripts, not summaries; no advancement on claims.
```

---

*End of GLM handoff source. The governing rule for the fresh reviewer, unchanged since P0: the repository is read through transcripts pasted into the review channel; prose is claims, floors verify, and nothing is "done" until the evidence that says so has been shown.*

# APPENDIX B — OMP / MUSE IMPLEMENTATION SOURCE

The following is the OMP/Muse evidence-capture source provided for this combined artifact. Preserve it as source material; do not silently edit its claims.

---

RAPHAEL v4.1 — Implementation / Repository Reality Handoff (evidence capture only)

 ▏ Source discipline: [PROVEN] = command/test/transcript at stated HEAD. [IMPLEMENTED] = source exists, behavior not fully demonstrated. [ACCEPTED] = GLM
 ▏ gate record found (never inferred from code). [UNKNOWN] / [DEFERRED] / [HISTORICAL] / [SUPERSEDED] as defined. No changes made. No deps installed. No
 ▏ cleanup. No fixes. No roadmap advance.

 REQUIRED PREAMBLE (live identity)

 All machine-state claims below observed at HEAD 31d66c234a2cdf24291201562cb100a584737cdf, branch weld-sub10-evidence unless explicitly labeled otherwise.

 - [PROVEN] Absolute path: /home/yaser/external-audits/raphael-2 (realpath, git rev-parse --show-toplevel).
 - [PROVEN] Remotes: canonical git@github.com:The-Despicable/Raphaelv4.1.git (fetch/push); origin https://github.com:The-Despicable/raphael-2.0-rbsv2r
   (fetch/push) (git remote -v).
 - [PROVEN] Branch: weld-sub10-evidence (git branch --show-current, symbolic-ref --short HEAD). NOT detached (symbolic-ref -q HEAD →
   refs/heads/weld-sub10-evidence).
 - [PROVEN] HEAD: 31d66c234a2cdf24291201562cb100a584737cdf / short 31d66c234 (git rev-parse HEAD). Message: Publication orientation: RAPHAEL_STATE.md +
   REVIEWER_GUIDE.md (docs only, no implementation change).
 - [PROVEN] Working tree: clean, nothing to commit (git status); staged: none (git diff --cached --name-only empty); untracked: none (git status
   --porcelain empty).
 - [PROVEN] Recent log (15): 31d66c234 (docs) → b676d8198 (§14.5 records) → 8cd3a9561 (§14.5 impl) → 18a7acd09 (§14.4 records) → 7e68b2452 (§14.4 impl) →
   bec5c65ed (§14.3 Option-B correction) → c4ff633df (§14.3 Option-B) → 0f060369a (§14.6 Scope records) → 85c3bc908 (§14.6 Scope impl) → 485aacdc0
   (WELD-SHELL records) → 5e73a1103 (SHELL probe) → 82c4138e5/379f037e1 (SHELL remediation) → 9bfb1edc0 (SHELL evidence) → 784d3fddb (SHELL gate) → … (git
   log --oneline -15/-30).
 - [PROVEN] Tags: raphael-orphan-phase12-preserved, raphael-p0-baseline-7272880f, raphael-p1-post-migration-7272880f, raphael-p1-pre-migration-7272880f,
   raphael-p14.5-baseline (×2 listing, one duplicate line) (git tag --list). git show-ref: main = weld-sub10-evidence = 31d66c234; canonical/main =
   31d66c234; origin/main = origin/HEAD = 7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0 (stale); weld-sub14-evidence branch = 2caeb4923; stash ref 832ddcf3
   exists (contents not inspected — read-only).
 - [PROVEN] RAPHAEL_STATE.md canonical-HEAD field is stale by one docs-only commit: claims b676d8198df003873f52b96c83896d65593a77a2; live HEAD is
   31d66c234. Diff b676d8198..31d66c234 --stat = 2 files, 66 insertions (RAPHAEL_STATE.md +31, REVIEWER_GUIDE.md +35), zero implementation change.
 - [PROVEN] Environment for verification: Linux DESKTOP-FKUOPQ1 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun 5 18:30:46 UTC 2025 x86_64
   GNU/Linux (uname -a).
 - [PROVEN] Python: Python 3.14.4 (python3 --version); pytest 9.1.1 (pytest --version); runners: /usr/bin/python3, /home/yaser/.local/bin/pytest. Mismatch
   note: pyproject.toml requires-python >=3.11,<3.13 but verification ran on 3.14.4 — floor below is valid only for that interpreter.
 - [PROVEN] Package/test runner: pyproject.toml [tool.pytest.ini_options] testpaths=["tests"] pythonpath=["src"]; canonical invocation per
   REVIEWER_GUIDE.md: PYTHONPATH=src python3 -m pytest tests/ --no-header -q.
 - Session cwd at task start: /home/yaser/tmp (outside git; active subject repo is /home/yaser/external-audits/raphael-2, selected because it alone carries
   src/orchestrator/runtime|brain|exec, evidence/phases/P3_0, weld history, and RAPHAEL_STATE.md).

 1. REPOSITORY IDENTITY

 - [PROVEN] Repo path /home/yaser/external-audits/raphael-2; remote canonical = Raphaelv4.1.git, origin = raphael-2.0-rbsv2r; branch weld-sub10-evidence;
   HEAD 31d66c234; clean; tags above.
 - [PROVEN] Relationship to canonical history: live HEAD is descendant of 7272880f7 (origin/main, P0 baseline) and identical to canonical/main (show-ref
   both 31d66c234). It is NOT merely name-correct: canonical/main pointer equality + weld/scope/sandbox/evidence commit chain +
   evidence/phases/{P0,P1,P2_0,P2_1,P3_0,G2_RC,g1_corrections} presence confirm it is the lane-canonical working line. origin/main is behind (at
   7272880f7).
 - [UNKNOWN] Whether canonical remote tip equals GLM-accepted tip — no gate-channel record in repo proves acceptance at any HEAD. Never infer acceptance
   from pointer equality.

 2. CURRENT TREE STRUCTURE

 Observed at HEAD 31d66c234, branch weld-sub10-evidence (directory listings + scout file:line markers; independent re-verification of key paths).

 - [IMPLEMENTED] src/orchestrator/runtime/ — canonical. 9 files: loop.py (149L, RaphaelRuntime thin sequencer), stages.py (446L, STAGE_ORDER 10 stages +
   handlers), scope.py (215L, ScopeV0), evidence_v1.py (443L), organs.py, policy.py, types.py, safe_proving_capability.py (shim). Markers:
   runtime/__init__.py:10-12 CONV-1 single canonical PDP = real CapabilityBroker; loop.py:17-21 CONV-1/2/3; stages.py:11-15 canonical path + INV-2.
 - [IMPLEMENTED] src/orchestrator/brain/ — canonical (Head-2). capability_broker.py (1501L, CapabilityBroker.propose_action), action.py (Planner,
   ActionRegistry), world.py (WorldModel), contradiction.py, evidence.py (canonical EvidenceGraph), plan_decision.py:7-9 canonical home of PlanDecision,
   plus phases/, candidate_generators/{shell_generator,student_generator}.py. adaptive_brain.py is 31-line deprecated stub (P1 marker).
 - [IMPLEMENTED] src/orchestrator/exec/ — canonical PEP (INV-1, CONV-2/3). __init__.py:2,5,7,10-12,16-18 (only primitive-holder, PEP, confinement);
   safe_capability.py, sandbox.py (449L), evidence_store.py (128L), inv1_guard.py.
 - [IMPLEMENTED] src/orchestrator/capabilities/interactive_shell/ — canonical E1 extension (Broker-wired, SHELL-gated). 8 files (capability.py, session.py,
   listener_manager.py, command_filter.py, tty_normalizer.py, ssh_shell.py, reverse_shell.py). No top-level /capabilities or /src/capabilities (MISSING
   [PROVEN]).
 - [IMPLEMENTED] src/arena/ — canonical driver/scorer (arena→brain direction: runner.py, ablation_runner.py:67-71 import brain; defeater_types.py:8-16
   P5-BIND-1). Top-level arena/ is results-only/test-only (d6c_results/, results/raw, no .py).
 - [IMPLEMENTED] src/orchestrator/api/ (agent.py, ci.py, main.py, session*.py, tools*.py, types.py) — exists, ownership UNKNOWN (no canonical marker; not
   in B-1a static/loaded closures; see §11).
 - [IMPLEMENTED] src/orchestrator/modes/ (autonomous.py, student.py, deep_research.py, debate.py, postmortem.py, community.py, rsi.py, scan.py) — exists,
   legacy-adjacent/UNKNOWN (brain/__init__.py:14-17 directs consumers to adaptive_brain directly; not on canonical path).
 - [PROVEN] No legacy/ directory (glob **/legacy*, **/deprecated* → no files). Legacy/Head-1 = src/raphael/ (main.py 381L, RaphaelOrganism with P1
   DEPRECATION MARKER :2-10, gated behind RAPHAEL_USE_LEGACY=1 at :358-362); plus legacy execution envelope agents/, c2/, exploit/, chains/, ad/,
   phishing/, postex/, etc. — all present, SUB-marked where inventoried, outside canonical closure.
 - [PROVEN] tests/ (37 files incl. test_scope_v0.py, test_exec_sandbox.py, test_evidence_v1.py, e1_interactive_shell_test.py, test_p21_walking_skeleton.py,
   test_g3_en5_organ_wiring.py, 10× test_p2_guardrail_*); evidence/{g1_corrections,phases/{P0,P1,P1_0,P2_0,P2_1,P3_0,G2_RC}}; docs/adr/ADR-001..012;
   policies/bootstrap-v0.json (only policy file); src/bridge/raphael_bridge.py; cli/ is unrelated Node scaffold (not the control plane); broken symlinks
   cai_service/cloak_service/mcp_hub/mhddos_service → /home/yaser/raphael-2.0/* (targets absent — unresolved, out of scope).

 3. CURRENT CONTROL PLANE

 Trace verified read-only at HEAD 31d66c234 (import lists + stage bodies quoted; planner-invocation gap confirmed).

 - [IMPLEMENTED] CLI → src/raphael/main.py:323 main() parses target/RAPHAEL_TARGET, --help; legacy branch RAPHAEL_USE_LEGACY=1 → organism.run() else
   canonical RaphaelRuntime().run_episode(MissionContext(mission_id='cli-walking-skeleton'…)) (:367-376); __main__ → asyncio.run(main()).
 - [IMPLEMENTED] Runtime → src/orchestrator/runtime/loop.py:43 RaphaelRuntime (thin sequencer, born-gated docstring). Imports Broker,
   SafeProvingCapability, STAGE_ORDER/STAGE_HANDLERS, make_broker_from_bootstrap, OrganBundle; no arena import. step(ctx) iterates STAGE_ORDER, fail-closed
   on first !success. run_episode() enforces ScopeV0 pre-gate (non-ScopeV0/require_scope fails closed).
 - [IMPLEMENTED] Stages → stages.py:60-446, 10 handlers + order pinned: observe → worldmodel_read → student_candidate → planner_request → broker → pep →
   receipt → worldmodel_integrate → contradiction → replan.
 - [IMPLEMENTED] Planner class, invocation stub on hot path: brain/action.py:649 Planner (decide/plan/register_denial, ActionRegistry:481 with empty
   _register_builtins: pass) exists and is organ-wired (organs.py:34), but stage_planner_request (:130) does NOT call decide() — builds deterministic
   ActionRequest(action_type="safe_proving_capability", target=…, args={"read_only":True}).
 - [IMPLEMENTED] Broker (sole PDP) → brain/capability_broker.py:310 propose_action(target, action_type, capability, method, impact_estimate, metadata) →
   create_proposal → _run_all_checks (TARGET/ROE/CAPABILITY/RATE/IMPACT, deny-by-default) → authorize/deny → receipt_store[action_id]=receipt. stage_broker
   (:154) calls with impact_estimate=0.0, maps to decision, fail-closed on deny, plus Scope conjunction (scope.covers(); missing estimate fails closed).
 - [IMPLEMENTED] PEP → exec/ sole owner. stage_pep (:238): default capability.record_authorization → inspect → ExecutionEvent(capability=…); sandboxed_exec
   branch → _stage_pep_sandboxed lazy-imports exec.sandbox (keeps runtime/*.py primitive-free per INV-1). inv1_guard.py scans forbidden primitives.
 - [IMPLEMENTED] Sandbox (conditional) → exec/sandbox.py SandboxedExecutor.execute(request, receipt) re-verifies receipt then bounds execution (see §7).
   Only entered for action_type=="sandboxed_exec"; walking-skeleton default path never enters it.
 - [IMPLEMENTED] Capability → exec/safe_capability.py SafeProvingCapability (fixture dict, record_authorization gate target in broker_authorized_targets,
   inspect walk); runtime/safe_proving_capability.py is deprecated re-export shim (CONV-3). Planner-side ActionRegistry is NOT a tool-execution registry;
   legacy chains/tool_registry.py _run_command (asyncio.create_subprocess_exec) carries SUB-04 UNREACHABLE_FROM_CANONICAL — not on canonical path.
 - [IMPLEMENTED] Receipt/evidence → hardening/action_receipt.py:71 ActionReceipt (+create_proposal/authorize/deny, hash chain); runtime/types.py
   ExecutionEvent/EvidenceReceipt/DecisionTrace (INV-2: decision.decision_id = broker action_id); stage_receipt (:346) mints EvidenceReceipt. Durable
   EvidenceRecord/EvidenceStore available but NOT invoked on hot receipt path (substrate, not yet wired).
 - [IMPLEMENTED, minimal] WorldModel → brain/world.py:246 WorldModel exists; stage_worldmodel_read (:77) returns counts only; stage_worldmodel_integrate
   (:365) appends Evidence(trust=TOOL_OBSERVATION, source="runtime.receipt") to EvidenceGraph via organs.record_integration — no
   add_entity/add_relationship belief write by design.
 - [IMPLEMENTED, recording-only] Student → candidate_generators/student_generator.py:241 StudentCandidateGenerator.generate_candidates exists;
   stage_student_candidate (:102) calls it (fixed profile nginx/django, mode:"recording", exception→[]) but output count is NOT fed to planner_request
   (unwired consumption).
 - [STUB by design] Contradiction/replan → ContradictionManager (:134) exists with detect_contradictions(), but stage_contradiction (:381) only counts
   pre-existing contradictions (never calls detect; always empty fresh) with rule g3-en-5.deterministic.no_contradiction; stage_replan (:409) returns
   {replanned:False, one-iteration-complete} terminator; loop ends after one iteration. No falsification/replan semantics (explicit P4 non-goal).

 4. P0/P1/P2 IMPLEMENTATION STATE

 - [HISTORICAL+IMPLEMENTED] P0 (re-anchor): tag raphael-p0-baseline-7272880f → commit 7272880f7 [PROVEN via show-ref/tags]; evidence
   evidence/phases/P0/{00_manifest,01_test_floor,02_execution_inventory (subprocess_sites.md SUB-09..14
   table),03_historical_reverification,04_architecture_reanchor (canonical_graph.md,
   runtime_entrypoints.md),05_migration_delete_inventory,06_risks,07_runtime_probes} [IMPLEMENTED]. Historical floor counts inside P0 records are
   [HISTORICAL] — not rerun in this session.
 - [HISTORICAL+IMPLEMENTED] P1 (migration/seam wrap): tags raphael-p1-pre/post-migration-7272880f; deprecation markers in-tree (src/raphael/main.py:2-10,
   brain/adaptive_brain.py:1-7, runtime/safe_proving_capability.py:1-5, G2_RC/deprecation_marker_registry.md, G1_CONFIRMATION_PACKAGE.md,
   seam_status_WRAPPED_vs_WELDED.md) [IMPLEMENTED]. Migration content not re-executed here.
 - [IMPLEMENTED] P2 (entry + walking skeleton + guardrails + closure):
   - Canonical Runtime [IMPLEMENTED] loop.py RaphaelRuntime, 10-stage sequence pinned (stages.py STAGE_ORDER, test_stage1_invariants.py,
     test_p21_walking_skeleton.py) — stages file unchanged since G3-EN-5 per evidence.
   - Born-gated [IMPLEMENTED] (loop.py:43 docstring; make_broker_from_bootstrap default fixture.inspect; SafeProvingCapability(broker);
     test_p21_walking_skeleton.py + test_g3_en5_organ_wiring.py green inside fresh 357 floor).
   - CLI→Runtime [IMPLEMENTED] src/raphael/main.py:367-376 (see §3); cli/ dir is NOT the path.
   - Broker mediation [IMPLEMENTED] single propose_action call site on runtime path; test_p2_guardrail_deny_by_default.py,
     test_p2_guardrail_no_production_bypass.py green.
   - Safe proving capability [IMPLEMENTED] exec/safe_capability.py (broker-gated fixture inspect).
   - Arena-free closure [PROVEN fresh] static 34 orchestrator / 0 arena, loaded 53 / 0 arena, STATIC_ARENA_FREE=True, EPISODE_ARENA_FREE=True (B-1a probe
     rerun this session; see §12). P2-era counts (e.g. 289 at G3-EN-5) are [HISTORICAL]/[SUPERSEDED] by 357.
   - Bootstrap policy [IMPLEMENTED, retired] policies/bootstrap-v0.json (PROPOSED, superseded_by: Scope v0, retirement at P3, exclusions: production
     caps/real subprocess/Decepticon).

 5. P3 BYPASS WELDS

 Commits observed via git log --oneline --grep at HEAD 31d66c234 (all on weld-sub10-evidence); current file bodies re-read; deletion claims checked by
 symbol search.

 - SUB-14 (+SUB-13 fold-in) [IMPLEMENTED, welded]: orig seam src/raphael/executor/executor.py (_subprocess_fallback → asyncio.create_subprocess_shell,
   tool_runner fallthrough; kali_bridge.py _subprocess_run fallback; P0 inventory SUB-14 executor.py:72, SUB-13 kali_bridge.py:152). Weld 740861f2e (+
   follow-ons f78efdb58 evidence, 258a9894c SUB-13 test, 5c4fba89d correction, 2caeb4923 BD-1 provenance). Change: fallback removed, tool_runner or
   kali_bridge.run, RuntimeError Executor._subprocess_fallback() is removed in WELD-SUB14; kali_bridge.py:69-72 RuntimeError. Evidence
   WELD-SUB14_EVIDENCE.md (W-A/W-B/W-C/W-D, W-2 reconciled). Current: bypass symbols NOT FOUND (grep), header quarantined [PROVEN]. No deletion of legacy
   files — weld, not delete. GLM acceptance: [UNKNOWN] (no gate record found; header = evidence-ready posture).
 - SUB-10 [IMPLEMENTED, welded]: orig seam src/orchestrator/kali_tools_client.py:41 _run_local (asyncio.create_subprocess_exec) +
   _BYPASS_AUTHORIZED/authorize_local_bypass. Weld a099ba460 (+ 480811584 evidence, f652152f9 BD-S10 appendix). Change: 107-line rewrite, local path
   removed; both remote-failure and local paths now raise RuntimeError("kali_tools_client._run_local is removed in WELD-SUB10…") (:73-82 re-read). File
   still imports subprocess/httpx (:2,8) but execution paths fail closed. Guardrail test_p2_guardrail_sub10_closed.py green in fresh floor. No file
   deletion. GLM acceptance: [UNKNOWN].
 - SHELL [IMPLEMENTED, welded+remediated]: orig seam capabilities/interactive_shell/ — ReverseShellCapability.__init__ (reverse_shell.py:77),
   SSHShellCapability.__init__ (ssh_shell.py:38), Factory.create (capability.py:275), create_from_listener (reverse_shell.py:162) unconditional (SD-1
   deferred). Weld 784d3fddb (+ 9bfb1edc0 evidence, 379f037e1/82c4138e5 broker-state-bound + listener gating, 5e73a1103 parity probe, 485aacdc0 conversion
   records). Change: ShellNotAuthorized + require_shell_authorization(authorization, expected_session_id) (authorized is True,
   authorized_by==capability_broker, non-empty numeric unexpired session_id/expires_at, is_shell_session_authorized) enforced in base
   __init__/create/reverse/ssh (capability.py:19-88,149-151,359-361). Guardrail test_p2_guardrail_shell_closed.py (4 tests) + e1_interactive_shell_test.py
   green. No constructor deletion — gating, not removal. GLM acceptance: [UNKNOWN].

 6. SCOPE V0

 - [IMPLEMENTED] File src/orchestrator/runtime/scope.py (215L, SCOPE_VERSION="v0"); impl commit 85c3bc908 (+16 tests), records 0f060369a, Option-B fix
   c4ff633df, correction record bec5c65ed (all in log at HEAD 31d66c234).
 - [IMPLEMENTED] Records commit 0f060369a + correction bec5c65ed (false-claim record, numbering fix, bootstrap note, denial set) — per SCOPE-V0_EVIDENCE.md
   grep.
 - [IMPLEMENTED] Fields (ScopeV0 frozen): mission_id, targets, allowed_action_types/prohibited_action_types, allowed_capabilities/prohibited_capabilities,
   max_impact=0.0 (scope.py:80-90); ScopeError fail-closed; from_dict strict; scope_hash sha256; stdlib-only, never calls Broker/PEP/WorldModel.
 - [IMPLEMENTED] Enforced semantics: covers(target, action_type, capability, impact_estimate=0.0) (:141-171) — exact/CIDR/wildcard match, prohibited-wins,
   empty-allow denies, malformed impact denies, if impact > self.max_impact: False (strict-greater; equal allows); broker-stage conjunction in
   stages.py:198-233 (Broker-recorded estimate threaded; absent estimate → no impact estimate available fail-closed); run_episode require_scope pre-gate.
 - [IMPLEMENTED] Tests: tests/test_scope_v0.py 19 tests (16 + 3 impact); fresh floor confirms green (19/19 inside 357; C-1 transcript in
   SANDBOX-V0_EVIDENCE.md §10 shows monotonic 5%…100% 19 passed).
 - [HISTORICAL] Floor at the time: 313 (297+16) at 85c3bc908/0f060369a; 316 after Option-B c4ff633df [HISTORICAL per SCOPE-V0_EVIDENCE.md]; both
   [SUPERSEDED] by current 357.
 - [IMPLEMENTED] Current status: in-tree, frozen per lane claim, enforced on canonical path; header posture = evidence-ready, NOT gate-accepted (see §14).
 - [IMPLEMENTED] C-1 rider (open): gate submissions must include verbatim Scope 19-test transcript + one-line transcription-error explanation (prior
   hand-reassembled percentages non-monotonic) + 316/32 §14.3 floor line (carried in SANDBOX-V0_EVIDENCE.md §10, EVIDENCE-V1_EVIDENCE.md §9,
   RAPHAEL_STATE.md).
 - [IMPLEMENTED] max_impact correction (Option-B): pre-fix covers() unconditionally returned True on scope match (no impact check); GLM-authorized minimal
   fix c4ff633df added impact > max_impact comparison + threaded decided estimate at broker stage + 3 tests (test_over_max_impact_denied 0.5 vs 0.0 → deny;
   test_exact_max_impact_allowed; test_stage_fails_closed_without_impact_estimate).
 - [DEFERRED] §14.10 ruling: over-cap demo must use Broker-recorded estimate; no Scope-manufactured impact (not implemented here, per evidence).

 7. NATIVE SANDBOX

 At HEAD 31d66c234, file src/orchestrator/exec/sandbox.py (449L), impl 7e68b2452, records 18a7acd09.

 - [IMPLEMENTED] Authorization flow: Broker propose_action (allow) → stage_broker (broker+scope) → stage_pep allow-gate → sandboxed_exec branch →
   SandboxedExecutor.execute re-verifies receipt against broker.receipt_store → bounded run → SandboxResult → ExecutionEvent(capability="sandbox.exec") →
   receipt stage. Absent/forged/denied/cross-target → SandboxNotAuthorized (CONV-3). No bypass flag / no authorized=True convention (source search per
   evidence).
 - [IMPLEMENTED] Receipt lookup: _check_receipt(broker, receipt, request.target) (:173-202 re-read verbatim) — broker None → deny; receipt.action_id
   missing → deny; broker.receipt_store dict lookup, unknown → not Broker-issued; stored.status != AUTHORIZED → deny; stored.target != target → deny. Only
   STORED fields trusted.
 - [IMPLEMENTED] Allowlist: DEFAULT_ALLOWED_EXECUTABLES = (/bin/true, /bin/false, /bin/echo, /bin/sleep, /bin/cat) (:83-88), realpath-both-sides, must be
   absolute, must be runnable file; no shell ever.
 - [IMPLEMENTED] Limits/timeout/caps: SandboxPolicy defaults timeout 10s, output 65536B, artifact 65536B, cpu 5s, fsize 262144B, allow_network=False;
   execute() resolves timeout request.timeout_s or policy.timeout_s; _run deadline + setsid/killpg + bounded reap (poll 0.05s, reap 5s); output
   combined-size poll + kill + truncate + RLIMIT_FSIZE backstop; RLIMIT_CPU/FSIZE via preexec_fn; RLIMIT_AS/memory NOT claimed; artifacts declared-relative
   + realpath containment + per-file cap, missing/escape/oversize → ARTIFACT_FAILURE; workdir mkdtemp under policy root, Popen(cwd=workdir), always
   removed; stdin=DEVNULL, env {"PATH":"/usr/bin:/bin"}.
 - [IMPLEMENTED] Network: NO kernel isolation in v0; allow_network=True → UNSUPPORTED fail-closed; posture (no-shell + allowlist + DEVNULL + scrubbed env)
   is mitigation, not guarantee (honest matrix in evidence).
 - [IMPLEMENTED] Process handling: Popen + wait(timeout=0.05) loop, size/deadline kill via process group, SIGKILL escalation, 8 statuses
   (success/timeout/output_limit/resource_limit/setup_failure/exec_failure/artifact_failure/unsupported); 18 tests in tests/test_exec_sandbox.py green in
   fresh floor.
 - F1 finding (do not minimize): [PROVEN] Current _check_receipt() binds action_id → stored status + stored target only. It does NOT bind
   argv/executable/args/policy to the receipt. execute() passes request.target for the target check but passes NO argv binding: ActionReceipt has no
   argv/command field (action_receipt.py:71-87 fields = action_id/target/capability/method/impact_estimate + metadata action_type/impact_estimate);
   _check_receipt never compares request.argv to anything stored. A receipt AUTHORIZED for target T therefore authorizes ANY allowlisted argv against T
   within policy bounds. Verbatim binding = lines :180-202 (lookup + two comparisons, nothing else).
 - [PROVEN] F1 remediation has NOT been implemented: no argv/request-binding comparison exists in sandbox.py:173-242; no commit after 7e68b2452/18a7acd09
   touches binding (git log shows only bec5c65e/c4ff633d scope, 8cd3a95/b676d81 evidence, 31d66c23 docs on top); no test binds argv to receipt (18 sandbox
   tests cover forged/denied/cross-target/no-broker + PEP/INV-1, none assert argv mismatch denial — confirmed by test-name/content review). Status =
   unfixed (not partial, not unevidenced-fixed).

 8. EVIDENCE V1

 At HEAD 31d66c234, impl 8cd3a9561, records b676d8198.

 - [IMPLEMENTED] Implementation: NEW src/orchestrator/runtime/evidence_v1.py (443L, pure stdlib top level) + NEW src/orchestrator/exec/evidence_store.py
   (128L, sole file-primitive holder) + export deltas in both __init__.py + tests/test_evidence_v1.py (23 tests). No existing test edited (R-W2); no
   runtime/ stage change; STAGE_ORDER untouched.
 - [IMPLEMENTED] Store: append-only bounded JSONL (evidence_v1.jsonl), fsync per append, index by identity, MAX_RECORD_BYTES 131072, MAX_RECORDS 10000
   (StoreFull fail-closed), idempotent identical re-ingest, identity-conflict/oversize/unknown-parent/corrupt-line rejected fail-closed; no
   overwrite/delete API; lives in exec/ per INV-1 (records module has zero file/network/subprocess imports).
 - [IMPLEMENTED] Classes: EvidenceKind 5 + frozen EvidenceRecord envelope — Assertion, Observation, ExecutionResult, Artifact, Finding — with
   _check_kind_shape per-kind validation.
 - [IMPLEMENTED] Identity/hash: ev1_ + sha256 over canonical body (version, kind, mission_id, producer, parents, payload; fixed key order, version 1).
   observed_at is provenance, NOT identity (same content at different times shares identity → idempotent ingest). Strict from_dict (unknown field / wrong
   version / missing required / identity mismatch → EvidenceError); round-trip preserves identity.
 - [IMPLEMENTED] Parent/provenance: ≤8 parents, parent-existence enforced; ≤24 payload fields, ≤16 artifact refs, bounded strings (8192/65536); artifacts
   are references (relpath+size+sha256), evidence never opens host files (bytes passed in).
 - [IMPLEMENTED] Persistence: JSONL identity+record; to_legacy_evidence() exports into canonical EvidenceGraph.add_evidence (student producers →
   MODEL_INFERENCE, no trust elevation, labels verbatim); adapters execution_result_from_sandbox / artifact_records_from_sandbox consume
   SandboxResult/receipt structurally.
 - [IMPLEMENTED] Tests: 23 passed (five classes, malformed/version/determinism/round-trip/provenance/live-sandbox
   linkage/artifact/bounds/duplicate/conflict/invalid-ref/cycle/persistence/corrupt/no-authorization/scope-sandbox-unchanged/no-stage/no-arena/worldmodel-u
   ntouched/graph-integration). Green inside fresh 357.
 - [UNKNOWN] Current acceptance: header = EVIDENCE READY, NOT ACCEPTED; RAPHAEL_STATE.md phase = §14.5 IMPLEMENTED / EVIDENCE READY (NOT accepted), next
   gate §14.5 acceptance (GLM authority). No GLM acceptance record found → NOT [ACCEPTED].
 - K.6 conclusion: [UNKNOWN] — literal K.6 (and K.0–K.9) has zero hits in evidence/ docs/ tests/ (grep, HEAD 31d66c234). The §14.5 evidence instead records
   closure 34/0 static, 53/0 loaded, ARENA_FREE True + invariants + later-phase boundary (no
   promotion/refuted/trust/contradiction/replan/learning/Arena/DB). Do not conflate that closure with a K.6 verdict.

 9. K.0–K.9 IMPLEMENTATION AUDIT

 - [UNKNOWN] No K-instrument results exist in the repository at HEAD 31d66c234. Commands: grep -rn "K\.0\|…\|K\.9" evidence/ docs/ tests/ → empty (exit 0,
   no matches); grep -rn "F1\b\|F2\b\|K\.0\|K\.6\|C-1" RAPHAEL_EXTERNAL_AUDIT.md → only C-1 hits (lines 30, 11385, 12144), zero K/F hits; P3 evidence
   SANDBOX/SCOPE/EVIDENCE-V1 contain no K.* strings. Therefore per-instrument command/result/HEAD/output/verdict: all UNKNOWN — cannot reproduce what was
   never committed. No FAIL rewritten to PASS; nothing to table.
 - [PROVEN] The only rider with verbatim transcript in-repo is C-1 (Scope 19-test transcript, monotonic, 19 passed — see §6/§12), not a K-series
   instrument.

 10. F1 CURRENT STATE

 - Verdict: [PROVEN] UNFIXED (not partial, not fixed-unevidenced, not accepted) at HEAD 31d66c234, branch weld-sub10-evidence.
 - Exact files: src/orchestrator/exec/sandbox.py:173-202 (_check_receipt), :239-242 (call site execute → _check_receipt(broker, receipt, request.target));
   authority types src/orchestrator/hardening/action_receipt.py:71-87,162-187; Broker store src/orchestrator/brain/capability_broker.py:291,310,387.
 - Authorization data change: none — ActionReceipt still carries no argv/command/request-hash field; no migration, no new column.
 - Request-binding implementation: none — no argv/executable/policy-hash comparison exists anywhere in sandbox.py.
 - Adversarial tests for argv binding: none — 18 sandbox tests cover no-broker/missing/forged/denied/cross-target + bounds + PEP + INV-1; zero tests assert
   valid-receipt + mutated-argv → deny.
 - Fresh test results: N/A (nothing to run for an unimplemented fix); canonical floor 357 green does NOT evidence F1 (it never exercises argv binding).
 - No fix commit, no evidence record, no GLM acceptance for F1 exists at this HEAD. Next chat must treat any request reuse across argv as
   authorized-for-target under current code.

 11. F2 CURRENT STATE

 All paths observed at HEAD 31d66c234. Nothing deleted or changed in this session.

 ┌──────────────────────────────────────────────────────────────────────┬────────────────┬────────────────────────────────────────────────────────────────┐
 │ File                                                                 │ Exists         │ Reachability evidence (production vs test)                     │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/api/ci.py (/v1/ci router, :12 imports               │ [IMPLEMENTED]  │ [IMPLEMENTED, unmounted] Importable; NOT mounted by            │
 │ modes.autonomous.handle as autonomous_handle, :160 awaits it)        │                │ api/main.py:86-89 (mounts agent/tools/tools_bridge/session     │
 │                                                                      │                │ only). Reachable iff ci.router imported directly; unreachable  │
 │                                                                      │                │ via main.app. No runtime/* importer (grep zero).               │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/bridge/raphael_bridge.py (stdio JSON-RPC; :17 imports modes.*,   │ [IMPLEMENTED]  │ [IMPLEMENTED, standalone bridge] Importable/executable as      │
 │ :19 c2.*, :22 kali; :49 mode.autonomous → :119-120                   │                │ bridge process; zero callers from runtime/*/stages/loop (grep  │
 │ autonomous.handle; c2.*, kali.* dispatch :63-82,152-211)             │                │ zero); NOT in B-1a static (34) or loaded (53) closures. Second │
 │                                                                      │                │ control plane, not canonical.                                  │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/api/main.py (FastAPI app, :86-89 mounts 4 routers,  │ [IMPLEMENTED]  │ [IMPLEMENTED] Runnable as service; mounts                      │
 │ ci conspicuously absent)                                             │                │ agent/tools/tools_bridge/session; imports api.* only on this   │
 │                                                                      │                │ path. Not imported by canonical Runtime.                       │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/api/agent.py (/api/agent router :30, imports        │ [IMPLEMENTED]  │ [IMPLEMENTED] Reachable via main.app; distinct from            │
 │ agents.engage :24)                                                   │                │ modes.autonomous path. Not on canonical Runtime path.          │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/modes/autonomous.py (handle(target, phases…) legacy │ [IMPLEMENTED]  │ [IMPLEMENTED, legacy-reachable] Callable via api/ci.py:160 and │
 │ fan-out harvest→phish :PHASES; imports providers, adaptive_brain,    │                │ bridge:119-120; zero runtime/* callers (grep zero); absent     │
 │ neural_memory, target_profiler, audit_trail, target_state,           │                │ from B-1a closures.                                            │
 │ brain.phases, engagement_queue, chains.* , hardening.*)              │                │                                                                │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/chains/* (ad_kill_chain.py:5,13 imports kali +      │ [IMPLEMENTED]  │ [IMPLEMENTED, legacy-reachable] Reachable via                  │
 │ c2.manager:get_c2; credential_spray.py:5-6 same; direct              │                │ modes.autonomous; not via Runtime. Execution today fails       │
 │ kali.run(...) call sites e.g. :117,183)                              │                │ closed at kali.run (SUB-10 weld) but call graph is intact.     │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/kali_tools_client.py (singleton kali :149; run()    │ [IMPLEMENTED,  │ [IMPLEMENTED, fail-closed] Importable (chains/bridge import    │
 │ remote→RuntimeError on failure :73-76, local→RuntimeError :79-82;    │ welded]        │ it); every execution path raises. subprocess/httpx imports     │
 │ FORCE_LOCAL flag retained)                                           │                │ remain (:2,8) though local exec is dead.                       │
 ├──────────────────────────────────────────────────────────────────────┼────────────────┼────────────────────────────────────────────────────────────────┤
 │ src/orchestrator/c2/manager.py (C2Manager, get_c2 :190-193, default  │ [IMPLEMENTED]  │ [IMPLEMENTED, noop-default] Importable; chains/* call          │
 │ NoopBackend :44)                                                     │                │ get_c2(); refresh/generate/execute/deploy exist but backend    │
 │                                                                      │                │ noop unless init(backend≠noop). Zero Runtime callers.          │
 └──────────────────────────────────────────────────────────────────────┴────────────────┴────────────────────────────────────────────────────────────────┘

 Net: [PROVEN] F2 envelope is canonically isolated (zero runtime|brain/capability_broker|exec imports of it; absent from both B-1a closures) but NOT
 unreachable in production: bridge and api/ci (when mounted/imported) and modes/chains/kali/c2 form an intact second execution graph outside the canonical
 Runtime. test_g2_c2_fail_closed.py + test_p2_guardrail_no_production_bypass.py constrain production bypass on the canonical path only — they do not delete
 or gate the legacy graph itself.

 12. TEST / GUARDRAIL / CLOSURE METRICS (fresh, same HEAD)

 Exact command (cwd /home/yaser/external-audits/raphael-2, HEAD 31d66c234, branch weld-sub10-evidence, clean, Python 3.14.4, pytest 9.1.1):

 - [PROVEN] PYTHONPATH=src python3 -m pytest tests/ --no-header -q → 357 passed, 0 failed, 0 skipped, 0 xfail, 32 warnings in 24.29s (exit 0). Tail
   verbatim: 357 passed, 32 warnings in 24.29s (+ PytestReturnNotNoneWarning test_cli_smoke.py::test_project_structure, SyntaxWarning "\-" <unknown>:141).
 - [PROVEN] Guardrails: PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_*.py --no-header -q → 30 passed (exit 0). Collect-only test_p2_guardrail_*
   + test_g2_c2_fail_closed + test_g3_en5_organ_wiring → 50 collected. The 30 are the test_p2_guardrail_* subset; G2/G3 files are separate.
 - [PROVEN] Static closure (B-1a instrument 1, fresh): PYTHONPATH=src python3 evidence/phases/P3_0/_b1a_probe.py →
   ORCHESTRATOR_MODULES_IN_STATIC_CLOSURE=34, ARENA_MODULES_IN_STATIC_CLOSURE=0, STATIC_ARENA_FREE: True (+ 34-module list incl. runtime.evidence_v1,
   exec.sandbox).
 - [PROVEN] Loaded closure (B-1a instrument 2, fresh, post-run_episode walk): ORCHESTRATOR_AND_ARENA_MODULES_AFTER_EPISODE=53,
   ARENA_MODULES_AFTER_EPISODE=0, EPISODE_ARENA_FREE: True.
 - [PROVEN] Arena count: 0 and 0 (static, loaded). No new failures/regressions vs RAPHAEL_STATE.md claim (357/30/34/53 all match lane record).
 - [HISTORICAL, SUPERSEDED] Phase floors in evidence records: 297 (pre-scope) → 313 (scope 16) → 316 (Option-B) → 334 (sandbox 18) → 357 (evidence 23).
   Historical; current rerun supersedes with 357.
 - Note: broad pytest --collect-only -q from /home/yaser/tmp (wrong cwd) collects 478 + 25 symlink errors via raphael_audit/raphael-2.0-rbsv2r — [PROVEN]
   artifact of cwd/symlink, NOT the canonical invocation; ignore.

 13. GIT / PROVENANCE

 - [PROVEN] Current HEAD 31d66c234 (docs-only) atop b676d8198 (§14.5 records). Short log in preamble; 30-log extends through
   SHELL/SUB10/SUB14/G3-EN-5/CONV/G2/P2.1/RC-B chain (§4 log).
 - [PROVEN] Relevant impl commits (all ancestors of HEAD): SUB14 740861f2e, SUB10 a099ba460, SHELL 784d3fddb + remediation 379f037e1/82c4138e5 + probe
   5e73a1103, Scope 85c3bc908 + Option-B c4ff633df, Sandbox 7e68b2452, Evidence 8cd3a9561.
 - [PROVEN] Evidence (records-only) commits: SUB14 f78efdb58/5c4fba89d/2caeb4923/258a9894c, SUB10 480811584/f652152f9, SHELL 9bfb1edc0/485aacdc0, Scope
   0f060369a/bec5c65ed, Sandbox 18a7acd09, Evidence b676d8198, plus G3-EN-5/CONV/G2-RC records chain.
 - [PROVEN] Branch weld-sub10-evidence; main + canonical/main same SHA; weld-sub14-evidence at 2caeb4923; tags as §1; stash ref exists (uninspected).
 - [PROVEN] Provenance chain for remediation state: P0 baseline 7272880f7 → P1 seam/deprecation → P2 walking skeleton b8a581ad6 → G2 RC-A..F → G3-EN-5
   organ wiring 7c10c8331 → CONV-1/2/3 → WELD-SUB14 → WELD-SUB10 → WELD-SHELL (+remediation/probe/conversion) → Scope (+Option-B) → Sandbox → Evidence →
   docs orientation 31d66c234. Each link is a git ancestor, not a transcript merge — no cross-session transcripts combined; fresh runs labeled with HEAD
   above.

 14. ACCEPTED / FROZEN COMPONENTS

 - [UNKNOWN] No GLM gate acceptance record was found in the repository for any P3 item in this session. grep for K.*/F-verdicts: empty.
   Weld/Scope/Sandbox/Evidence headers uniformly state EVIDENCE READY / NOT ACCEPTED, prepared for adjudication, STOP awaiting GLM, Next gate §14.5
   acceptance (GLM authority). RAPHAEL_STATE.md line Accepted/frozen: SHELL, SUB-10, SUB-13, SUB-14, Scope v0 is a lane assertion ([IMPLEMENTED] as a claim
   in that file), NOT gate-channel evidence — MUST NOT be cited as [ACCEPTED].
 - [IMPLEMENTED] Lane-frozen (code + evidence + floor, acceptance pending): SHELL (gated + remediated + probe), SUB-10 (welded + guardrail), SUB-14/SUB-13
   (welded + institutional test), Scope v0 (incl. Option-B + C-1 rider). Sandbox v0 + Evidence v1 are IMPLEMENTED/EVIDENCE-READY, explicitly not
   frozen-accepted.
 - [HISTORICAL] G1/G2-era records (G1_CONFIRMATION_PACKAGE.md, G2_RC/*, P2_1/EVIDENCE.md) assert prior conditional/RC dispositions — treated as
   [HISTORICAL], not re-adjudicated here; no fresh GLM instrument rerun.

 15. UNRESOLVED ITEMS

 - F1 [PROVEN unfixed]: _check_receipt target-only binding; no argv binding; no remediation commit/test/acceptance (§10).
 - F2 [PROVEN open envelope]: second execution graph (api/ci, bridge, modes/autonomous, chains/*, kali_tools_client, c2/manager) canonically isolated but
   legacy-reachable; ci unmounted from main.app but directly importable; kali.run fail-closed but graph intact (§11).
 - F3/F4/F5 [UNKNOWN]: no definitions/instruments for these labels found in repo at HEAD 31d66c234 (same empty grep as §9). Cannot list semantics; next
   chat must supply the finding texts — do not invent.
 - C-1 [PROVEN open rider]: verbatim 19-test transcript + transcription-error one-liner + 316/32 floor line must accompany every gate submission (carried
   in three records).
 - Other material UNKNOWN/DEFERRED [IMPLEMENTED as documented limits]: sandboxed_exec planner-unreachable until MVP assembly; no kernel net isolation
   (fail-closed UNSUPPORTED); RLIMIT_AS/memory unclaimed; static coreutils allowlist; single-thread preexec assumption; evidence cap 10000 fail-closed no
   rotation; artifact bytes referenced never embedded; §14.10 over-cap demo design ruling unimplemented; cli/ Node scaffold vs canonical CLI confusion
   hazard; broken *_service symlinks; Python 3.14 vs <3.13 floor mismatch. No speculative issues added.

 16. WHAT IS ACTUALLY RUNNABLE TODAY (clean checkout, PYTHONPATH=src)

 - [PROVEN] Canonical Runtime path: python3 -m pytest tests/ (357 green); RaphaelRuntime().run_episode(MissionContext(...)) one-iteration walking skeleton
   (fixture inspect + receipt + evidence-graph note); src/raphael/main.py canonical branch (needs RAPHAEL_TARGET or argv target; legacy only if
   RAPHAEL_USE_LEGACY=1); _b1a_probe.py closure instruments; Scope/Sandbox/Evidence unit suites individually.
 - [IMPLEMENTED, not assembled] sandboxed_exec via SandboxedExecutor.execute (callable directly with Broker receipt; unreachable via hardcoded planner
   until MVP assembly per evidence §11).
 - [IMPLEMENTED] Legacy paths (runnable outside canonical Runtime, NO canonical authorization): modes.autonomous.handle(...) (phase fan-out; downstream
   kali.run fail-closes, c2 noop-default, but model/providers/phase executors still invoke); bridge.RaphaelBridge.{mode_autonomous,kali_*,c2_*} JSON-RPC;
   api.main.app (agent/tools/session routers); api.ci router iff imported/mounted manually; chains.ad_kill_chain/credential_spray via modes/bridge.
 - [IMPLEMENTED] Test-only paths: e1_interactive_shell_test.py, test_prompted_agent_*, arena runner.py/ablation_runner.py drivers/scorers, scripts/* (~49
   files), benchmarks/evaluations/failures/* fixtures.
 - [UNKNOWN]/unsupported: any path requiring kernel net isolation, RLIMIT_AS sizing, evidence rotation, Docker/Decepticon/Sliver backends, production
   kali-tools:3800 service, or GLM signing/ledger submission (no signing station in repo).

 17. WHAT MUST NOT BE ASSUMED

 Next chat MUST NOT infer (each is a live trap at HEAD 31d66c234):

 1. A raise NotImplementedError/pass/TODO stub is implemented (e.g. Planner.decide exists but stage_planner_request never calls it; stage_replan
    terminator; ActionRegistry._register_builtins: pass).
 2. A green test evidences runtime behavior it never exercises (357 green does NOT evidence F1 argv binding, MVP assembly, or production mounting of ci).
 3. A git artifact (commit/tag/evidence/*.md/transcript) equals gate-channel acceptance — lane Accepted/frozen ≠ GLM [ACCEPTED].
 4. Legacy code is unreachable because canonical Runtime doesn't import it (bridge/api/modes/chains/kali/c2 importable and mutually reachable outside
    runtime/*; B-1a closures cover canonical path only).
 5. Scope/Sandbox/Evidence implemented ⇒ G3 passed (§14.3 lane-frozen claim vs §14.4/14.5 explicitly NOT accepted; G3-EN-5 organ evidence ≠
    sandbox/evidence acceptance).
 6. RAPHAEL_STATE.md canonical HEAD is current (stale by 31d66c234 docs commit); historical floors (313/316/334) are current (superseded by fresh 357);
    cli/ is the control-plane CLI (it is Node scaffold; real entry is src/raphael/main.py).
 7. kali_tools_client executes (all paths raise post-SUB10) or c2/manager is live (noop-default) — importable ≠ operable.
 8. Python <3.13 floor transfers to 3.14 without the noted interpreter mismatch.

 18. IMPLEMENTATION SNAPSHOT (machine-oriented)

 ```text
repository: Raphaelv4.1 lane (raphael-2 working line)
path: /home/yaser/external-audits/raphael-2
remote: canonical=git@github.com:The-Despicable/Raphaelv4.1.git; origin=https://github.com/The-Despicable/raphael-2.0-rbsv2r
branch: weld-sub10-evidence
HEAD: 31d66c234a2cdf24291201562cb100a584737cdf
clean: true (staged=0, untracked=0, detached=false)
test_floor: 357 passed / 0 failed / 0 skipped / 0 xfail (PYTHONPATH=src python3 -m pytest tests/ --no-header -q, 24.29s, 32 warnings, HEAD 31d66c234)
guardrails: 30 passed (tests/test_p2_guardrail_*.py); 50 collected with g2_c2+g3_en5
static_closure: 34 orchestrator / 0 arena (STATIC_ARENA_FREE=True, B-1a fresh)
loaded_closure: 53 modules / 0 arena (EPISODE_ARENA_FREE=True, B-1a fresh)
passed_gates_known: none verified in-repo this session (lane claims SHELL/SUB-10/SUB-13/SUB-14/Scope-frozen; §14.4/§14.5 explicitly NOT accepted; G1/G2
records historical only)
current_phase_known: §14.5 Evidence v1 IMPLEMENTED / EVIDENCE READY (NOT accepted) per RAPHAEL_STATE.md at HEAD 31d66c234
current_verdict_known: UNKNOWN (no GLM verdict record in repo; next gate §14.5 GLM acceptance)
open_findings: F1-unfixed(target-only _check_receipt, no argv binding); F2-open(second graph canonically-isolated but legacy-reachable, ci-unmounted);
F3/F4/F5-UNKNOWN(no definitions in repo); C-1-rider-open; K.0-K.9-UNKNOWN(zero in-repo hits)
authorized_work: none (evidence capture only; no fixes/cleanup/advance performed)
unverified_claims: any GLM acceptance of SHELL/SUB-10/SUB-14/Scope/Sandbox/Evidence; any K-series verdict; any F3-F5 semantics; production behavior of
legacy graph beyond fail-closed kali/c2 defaults
 ```

 Report produced read-only at HEAD 31d66c234 / weld-sub10-evidence, clean. Fluents: canonical floor 357 + guardrails 30 + closures 34/53 re-executed this
 session; file bodies (sandbox.py:173-242, kali_tools_client.py:52-82, scope.py:141-171, api/main.py:86-89, bridge:119-120) re-read; K/F3-F5 absence
 grep-verified. No files written. No roadmap advanced. Merge with GLM governance report + ChatGPT history report for the full handoff.

 2026-09-07 16:49:21  ⤵ 659  ⤴ 13K  💾 116K  ⏱ 3.2s  ⚡ 165.2/s

 • Background job completed [task] MetricsProvScout (4m38s)

 Late MetricsProvScout payload consistent with delivered handoff — no revision needed.

 - Floor 357/30, closures 34/53, headers EVIDENCE READY / NOT ACCEPTED, frozen list SHELL/SUB10/SUB13/SUB14/Scope: all match §§12/14 as delivered at HEAD
   31d66c234.
 - 31 modules / 0 kali is the [HISTORICAL] SUB10-era closure from WELD-SUB10_EVIDENCE.md, superseded by fresh 34/53 rerun — already distinguished in §12.

 Handoff stands as delivered.

 2026-09-07 16:50:37  ⤵ 14K  ⤴ 258  💾 117K  ⏱ 8.7s  ⚡ 24.1/s

                                                                                                                    Raphael Handoff Source Generation Report
 π  > ◕ Muse Spark 1.3 Free > 🗑 ~/tmp ↳ deepseek-harness > ⑂ master ?2 ▶──────────12%────────────────────────────────────────────────────────┃───────────1M─
╰─