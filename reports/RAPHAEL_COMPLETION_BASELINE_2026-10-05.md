# RAPHAEL COMPLETION BASELINE (Phase C0) — 2026-10-05

**Task**: RAPHAEL-M-C0 — baseline reconciliation & milestone gate. Read-only audit
and planning; the only file created by this task is this report. The prior audit
report and JSON inventory are superseded **in specific claims only** (§3 below)
and remain intact on disk. No production source, policy, test, Docker config, or
historical evidence was modified; nothing committed.

---

## 1. Current state (re-verified today)

| Item | Observed |
|---|---|
| Branch / HEAD | `offensive-restore` / `e6a8c707e` (matches all prior reports) |
| Worktree | 70 modified/untracked entries (M0→M2.1 + 4 reports + inventory JSON); preserved |
| Python | `.venv` 3.12.15 (pin satisfied) |
| Lab | dvwa / kali-tools / dvwa-db running, loopback-only (M2.1) |
| Active policy | `engagement-d1-v1.json` sha `777999a3c8d5b817…` (unchanged since M2); `bootstrap-v0` kill switch; `engagement-open-v0.json` unwired; **no D2 artifact** |
| D1 tests | 23/23 pass (re-run today) |

## 2. Documents inspected and authority

`RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` (canonical architecture/governance — highest
authority), `RAPHAEL_ARCHITECTURE_ROADMAP_v2.md` (phase structure F0–F9),
`RAPHAEL_HANDOFF_v4.1.md`, the four `evidence/` milestone packages (M0, M0-review,
M1, M2/D1, M2.1), `evidence/DEFECT_REGISTER.md` (DR-001), `reports/M3_ENTRY_GATE_2026-10-04.md`,
`reports/M3_D2_DESIGN_FREEZE_2026-10-04.md`, `reports/TOOL_INTEGRATION_AUDIT_2026-10-05.md`
+ `reports/tool_integration_inventory_2026-10-05.json`, suite/guardrail/weld tests.
Authority rule applied: source code > reports; master roadmap > research
blueprints; nothing in this report relies on an older report where current
evidence was checkable.

## 3. Reconciled integration audit (corrections)

All counts recomputed from the JSON. **Confirmed totals (unchanged):** 103
entries = TOOL 48 + TOOL_FAMILY 1 + WORKFLOW 8 + INFRASTRUCTURE 8 + CAPABILITY 38;
status A5 / B6 / C23 / D62 / F7 / E0 / G0; governance VERIFIED 6 / PARTIAL 5 /
N-A 92. **Corrections to the audit report's prose (superseded claims):**

1. **A-set membership (§3 prose was wrong).** The 5 INTEGRATED-AND-VERIFIED
   entries are **W-08 (D1 episode), I-01 (kali container), I-02 (dvwa/db), K-01
   (world model), K-02 (hypothesis engine)** — all substrates of the D1 path.
   The audit's §3 sentence listed "the nmap probe tool" among them; the JSON
   row T-01 is and remains **B (integrated, partially verified)**: nmap has
   exactly one verified bounded invocation route; its general executor
   (`tool_registry.py:101`) is gated and unexercised.
2. **Tool-class denominator (§7 arithmetic was wrong).** Tool-class entries =
   48 tools + 1 family = **49**, summing **B1 + C14 + D32 + F2** (the audit's
   tool line summed to 48 by omitting the family's D). Overall totals were and
   remain correct (D62 includes the family).
3. **Confidence coverage (§10 was wrong).** Actual: **95 high / 8 medium = 103**
   (medium: T-13, T-29, T-30, T-31, T-32, T-37, T-43, T-47). The audit's "48
   high, 5 medium" covered only 53 entries and understated both numbers.
4. **"One authorization decision away" (finding #9 was overstated).** Of the 23
   C entries, authorization alone is **insufficient for at least 12**:
   - T-02 sqlmap, T-03 metasploit: executor body (`_run_command`) is **deleted**
     (W-01) — an authorizing policy still hits the fail-closed raise.
   - T-04/T-07/T-09/T-10/T-11/T-12/T-13/T-14 scanner wrappers: **no weld gate of
     their own**; they route through `kali_tools_client.run()` — whose W-07 body
     is deleted. Needs body restoration + dispatch, not just a policy.
   - T-08 nuclei: templates absent. T-18 bloodhound: neo4j not running.
     T-19 netexec, T-20 chisel: binaries absent from the container.
   - The 9 C capability families (F-04/06/07/09/12/14/15/18/22) similarly sit
     behind deleted/gated dispatch chains.
   Additionally, **no C entry has an `exec/`-class capability or canonical PEP
   dispatch today** — each needs a D1-style governed wrapper + policy entry +
   tests. Corrected statement: *authorization is a necessary but never
   sufficient condition for any C entry; the C shelf is a restoration backlog,
   not a switch.*
5. **Category scan (beyond the four named):** workflow, infrastructure, and
   cognitive counts all reconcile; governance mapping (VERIFIED 6 = T-01, W-08,
   I-01, I-02, K-01, K-02) is consistent. **D-vs-E rule made explicit:** every
   "NONE FOUND" entry is *documented in the sources*, so D (documented/planned)
   is the correct class; E (absent) would require an implementation expectation
   from the roadmap that is missing entirely — none found. No G (undetermined)
   entries; none forced.

**No single completion percentage is offered** — tool availability (14/24
container binaries) is a dependency statistic, not capability coverage.

## 4. Evidence-backed completion baseline

### A. Governed execution — **strong, narrow**
Single Runtime/loop (`runtime/loop.py`), single Broker PDP
(`brain/capability_broker.py::propose_action`), single PEP (`exec/`, CONV-3
gating) — verified live four times on the D1 path: authorization+scope before
dispatch, deny-by-default (wrong target/capability/action, malformed policy all
fail closed), kill switch (bootstrap-v0 swap → denied, zero spawns), zero
capability invocations and zero subprocess spawns after denial (spy-proven,
per-test), receipts bound to decision_id + broker receipt + artifact digest.
**Scope of proof: one exact request against one target.** No other path is
exercised; generalization is unproven (correct per plan).

### B. Cognitive loop — **stages real and tested; multi-step causality unproven**
All 10 canonical stages exist and run in order (walking-skeleton test
`test_p21_walking_skeleton.py`; lifecycle `test_authorization_lifecycle.py`;
receipt persistence `test_p44_receipt_persistence.py`; conclusion infra
`test_conclusion_infra.py`). Causally verified **within one iteration**:
observation→candidates→planner→broker→PEP→receipt→world-model
integration→contradiction check→replan probe. **Unproven end-to-end:**
evidence→*next-iteration* candidate change (replan across steps),
hypothesis-verification against live multi-step evidence, objective-met
termination. Termination today is budget/exhaustion or failure only —
`stage_replan` literally terminates "after one iteration" (stages.py:825); no
objective-met evaluation exists.

### C. Failure handling & learning — **denial-class real; broader taxonomy thin**
Failure classification: PERSISTENT vs TEMPORARY denial classes with planner
suppression — implemented, tested, exercised in D1 denial-feedback episodes.
Retained negative knowledge: hypothesis history + contradiction records exist
and are suite-tested. **Not demonstrated:** retries vs abandonment policy
beyond denial suppression, failure-driven strategy change across steps, and
any learning (Student is recording-only by design; no promotion path exists —
an authorization-respecting boundary). Failed actions cannot become findings
(Finding requires evidenced parents; FAILED receipts are terminal) — enforced
by construction, tested at object level.

### D. Runtime & reproducibility — **green with standing defects**
Pinned 3.12.15 venv; lab loopback-only (re-verified rendered compose this
session: zero non-loopback published ports); suite 660/660/0/0 (re-verified
this session; last full run 2026-10-05); protected `arena/results/raw`
byte-identical (7th+ consecutive check); defect register: DR-001 (sword drift)
+ 18 structural import failures unchanged; **rate limiter exists but is
unbound by default** (`CapabilityBroker.__init__(..., rate_limiter=None)`,
applied only `if self.rate_limiter:` — capability_broker.py:281/362) — the D2
6/min limit is declared, not enforced, until wired; holdout dataset absent
(`unverifiable-in-repo`); credential rotation **operator-blocked**; D1 denial
receipts live in the broker receipt store but are **not persisted to the
evidence store** (episode fails before stage_receipt) — attempt-level denial
evidence is transcript-only today.

## 5. Definition of Done — bounded deterministic multi-step local-lab agent (D2 target)

Statuses are the baseline; D2 is **not implemented** and **not authorized**.

| # | Criterion (behavior proved) | Authority | Path | Required test/demo | Evidence artifact | Status |
|---|---|---|---|---|---|---|
| 1 | Multi-step scoped mission (2 actions × ≤5 steps) | v4.2 single-loop; entry-gate §7 | `run_episode(max_iterations=N)` + deterministic candidates | D2 episode demo | transcript + per-step receipts | **NOT STARTED** |
| 2 | Every action through Broker+PEP | INV-2; v4.2 | canonical stages (unchanged) | step-by-step decision ids in transcript | receipts w/ decision_id | **PASS** (architecture; D1-proven) |
| 3 | Receipt for every attempt **incl. denials** | v4.2 receipts; entry-gate §5.5 | broker receipts; denial persistence | denial during episode → persisted record | evidence-store denial record | **PARTIAL** (denials not persisted to store) |
| 4 | Evidence-grounded replanning | v4.2; blueprint §23.2 | denial feedback (exists) + evidence-keyed replan | step-2 candidate differs due to step-1 record | stage outputs + store lineage | **PARTIAL** (denial path only) |
| 5 | Truthful failure/contradiction/missing-evidence handling | v4.2; D2 freeze §3 halt rules | FAILED terminals; contradiction stage; Finding parents | fault-injection run | receipts + contradiction record | **PARTIAL** (single-step proven; halt rules untested) |
| 6 | Termination: objective-met / denial / safety / budget | v4.2; D2 freeze §3 | budget exists; objective-met NOT implemented | 4 termination scenarios | LoopTermination records | **PARTIAL** (budget+failure only; no objective-met) |
| 7 | Limits enforced, not declared | D2 freeze §3; entry-gate | rate-limiter wiring + capability constants | 7th action/min breach → denied with receipt | denial receipt w/ rate reason | **BLOCKED** (limiter unbound) |
| 8 | Kill switch + zero-spawn across whole episode | M2/D1 pattern | bootstrap-v0 swap per run | kill-switch phase inside D2 demo | 0-spawn spy proof | **PARTIAL** (single-step proven) |
| 9 | Reproducible demo | M2 pattern | `run_demo_d2.sh` (future) | cold-start ×2 identical outcomes | timestamped transcripts | **NOT STARTED** |
| 10 | D1, invariants, protected evidence intact | every milestone gate | regression + hash checks | full suite + tree hash | suite output + hash compare | **PASS** (re-verified today) |

## 6. Outstanding gates and defects (unchanged unless noted)

1. **Credential rotation — operator** (BLOCKED since M0; M0 security gate open).
2. **D2 scope authorization — operator** (design freeze contract NOT AUTHORIZED).
3. **Rate-limiter wiring — engineer, C1 scope** (BLOCKED item above; code exists).
4. **Denial-receipt persistence — engineer, C1 scope** (newly explicit in §4.D).
5. **Objective-met termination — engineer, C1 scope** (no implementation exists).
6. **Holdout dataset — operator** (recover or amend manifest).
7. **Commit authorization — operator** (70-entry worktree uncommitted).
8. DR-001 + 18 structural import failures — deferred (defect register).

## 7. Stage mapping to canonical roadmap (no silent renames)

| Program stage | Roadmap mapping | Conflict note |
|---|---|---|
| C0 baseline | (this task; supports all) | none |
| C1 authorized D2 implementation | F7 subset (autonomy, bounded; D2 contract) + F1-style bounded policy (d2-v1 artifact, exact-match) | none — F1's *open-policy* scope is intentionally NOT part of C1; the d2 policy stays bounded per entry-gate |
| C2 episode verification | F7 gate ("3-iteration episode, zero approvals, zero WeldNotAuthorized; kill-switch tested; ≥1 replan proven") | aligned |
| C3 completion/release gate | F8 lab-scenario subset + F9 (README/state sync, evidence integrity) | F8's scale ladders and C2/phish scenarios deferred to C4+ |
| C4 selective capability integration | F2 (bodies) + F3 (arsenal wiring) | **explicit re-ordering**: canonical roadmap ran F2/F3 before F7; the completion program completes the bounded core first — consistent with v2.1 north-star ("decision quality, not damage output") but a real sequence change, flagged for operator acceptance |

## 8. Completion backlog (dependency-ordered; nothing started)

| # | Item | Depends on | Files/components | Acceptance test | Evidence | Pri | Operator gate | Completion condition |
|---|---|---|---|---|---|---|---|---|
| C1-1 | Wire rate limiter onto D2 broker | D2 scope approval | `runtime/policy.py` factory; `brain/rate_limiter.py` | 7 actions/min → 7th denied w/ receipt | denial receipt (rate reason) | P0 | D2 scope | limit enforced + tested |
| C1-2 | Persist denial receipts to evidence store | — | `stages.py` broker-denial path or driver | denial → store record | evidence_store denial record | P0 | D2 scope | every attempt persisted |
| C1-3 | Objective-met termination | — | `runtime/loop.py`/stages (evidence-checked, never model-asserted) | objective satisfied → truthful termination | LoopTermination record | P0 | D2 scope | 4 termination modes work |
| C1-4 | `engagement-d2-v1.json` + loader strictness | scope approval | `policies/`, `runtime/policy.py` | exact-match deny tests | loader tests | P0 | **D2 scope authorization** | policy active, bounded |
| C1-5 | Action-B HTTP probe (in-container `http://dvwa/`) | C1-4; impl-time endpoint verification | `exec/capabilities/` | metadata+digest; redirects never followed | artifact + digest | P0 | D2 scope + endpoint gate | T2/T10–T13 matrix rows |
| C1-6 | `run_demo_d2.sh` + evidence dir | C1-1..5 | `scripts/` | cold-start ×2 | transcripts | P0 | D2 scope | DoD 1–9 PASS |
| C2-1 | Fault-injection (timeout, oversized, contradiction) episode | C1 | demo driver | defined halt per fault | receipts | P1 | — | DoD 5 PASS |
| C2-2 | Replan-from-evidence proof (≥1 non-denial trigger) | C1 | loop | step-2 changes on step-1 record | stage lineage | P1 | — | DoD 4 PASS; F7 replan gate |
| C3-1 | Release gate: full regression, hash integrity, doc sync, limitations | C2 | docs, README | suite + hash + review | release report | P1 | — | DoD 10 PASS |
| C4-x | Selective capability integration (per-audit backlog B-4..B-14) | C3 release gate | per-entry (exec/ wrappers; W-body decisions per roadmap F2) | per-entry D1-style probes | receipts | P2+ | per-capability authorization | roadmap F2/F3 gates |

**Deferred tool integration (explicit):** all 23 C-entries and 62 D-entries of the
reconciled inventory remain out of scope until C3 passes; blueprint fixture/
simulation/research-only classifications (§15) are retained — C4 items must
re-apply them per entry.

## 9. Checks executed (this task)

`git branch/rev-parse/status`; `sha256sum policies/engagement-d1-v1.json`;
`pytest tests/test_m2_d1_governed_action.py -q` (23 passed); JSON recount
(103; A5/B6/C23/D62/F7; confidence 95/8; governance 6/5/92); C-entry blocker
re-derivation from implementation text; rate-limiter constructor/invocation
inspection (`capability_broker.py:281,362`); scanner-wrapper dispatch
inspection (`gobuster_wrapper.py` → `kali.run`, W-07); termination-logic
inspection (`stages.py:825`); stage-test inventory; rendered-compose loopback
re-check (from today's session); full-suite + protected-tree hash (last
executed earlier today in this workspace: 660/660/0/0, identical — not re-run
in the final hour; D1 file re-run above is current).

## 10. Unverified claims (and why)

- Multi-step causality (replan-from-evidence, hypothesis verification across
  steps): no multi-step episode has ever run — D1 is single-step by design.
- Rate-limit denial behavior end-to-end: limiter unbound; never observed.
- Denial-receipt persistence: not implemented; transcripts only.
- Objective-met termination: implementation absent.
- Holdout reproducibility, provider rotation: externally blocked; unverifiable
  from the repository.
- Live-container tool inventory: relied on the M1/M2.1 inventory (image
  unchanged since; flagged, not re-probed).

## 11. Final status

**`BASELINE READY FOR OPERATOR REVIEW`.** The governed-execution core and
reasoning substrate are real and verified; the completion gap is a bounded,
well-specified implementation step (C1) whose every blocker is either an
operator gate (rotation, D2 scope, holdout, commit) or a named engineering
item (rate-limiter wiring, denial persistence, objective-met termination).
D2 remains **not implemented and not authorized**; nothing in this report
changes any authorization.
