# RAPHAEL ARCHITECTURE & ROADMAP v2 — Singular Master Document

Status: ACTIVE (2026-09-30, **v2.1 target-agnostic extension adopted** same day —
operator directive redefining north-star from "every exploit" to "generalization
across authorized target complexity"; see §1 north-star, §3 abstraction layer,
§6 phases F4/F5.) — **supersedes both** `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md`
and `RAPHAEL_EVOLUTION_BLUEPRINT_v1.md` (retained as archives with pointer banners).

Merged by operator directive: the build plan (P-phases), the evolution machinery
(S/E loops), and the **technique-pattern layer distilled from research rounds 1-17**
now live in one document, so no technique pattern is homeless between plans.

Sources: end-to-end audit (2026-09-30); P1-VERIFY-01; architecture review
(2026-09-29, adopted); `references/offensive_powerups_v1.md` (rounds 1-9);
`references/famous_group_ttps_v1.md` (rounds 10-17); `references/papers/AutoPen_2025_CSAE.pdf`;
CloakBrowser engine validation (2026-09-30).

---

## 0. VERIFIED STATUS (as of 2026-09-30)

| Fact | Evidence |
|---|---|
| Branch `offensive-restore`, HEAD == baseline `e6a8c707e`, zero commits since | `git log --oneline -3` |
| P1 edits present in worktree, content PASS; merge blocked (alias + `reverse_shell.py`) | P1-VERIFY-01 |
| `interactive_shell/reverse_shell.py` still deleted | directory glob |
| Verification probes written, never run (`p1_verify.py`, `weld_probe.py`) | temp dir |
| Suite floor 621 (last green at P0.1; not run since P1 edits) | session log |
| **WSL exec RESTORED** (0x8007274c self-healed) | live commands 2026-09-30 |
| **Research rounds 1-17 compiled** (capability 1-9, adversary 10-17) | both `references/*.md` |
| CloakBrowser installed + validated (headed+humanize passes CF; host-guard rule) | `/home/yaser/.venvs/cloak` |
| Toolchain still absent (no nuclei/subfinder/msf/sqlmap/ffuf); receipts ephemeral | recon run |
| Dispatched in-distro diffs: 0/2 landed | worktree grep |

---

## 1. OBJECTIVE & DEFINITION OF DONE

**North-star (v2.1, operator directive 2026-09-30):**

> Raphael should be able to reason about, assess, and operate across targets of
> arbitrary scale and technical complexity, provided the engagement is authorized
> and the available capabilities support the required actions.

This replaces "give Raphael every possible exploit." The system is **target-agnostic,
not technique-agnostic**: generalization across *authorized target complexity*, not
unlimited offensive capability. Capabilities support required actions; they do not
define what Raphael can handle.

**Dimensions Raphael must hold** (each maps to mechanisms in §3/§6):

| Dimension | Raphael should handle | Mechanism |
|---|---|---|
| Size | single VM → thousands of hosts → large enterprise | hierarchical engagement tree (§3.3) |
| Architecture | web, API, cloud, SaaS, AD, hybrid, network/edge | attack-surface graph; capability families (§5) |
| Difficulty | known vuln → novel/ambiguous surface | hypothesis engine (§3.2), difficulty ladder TP-19 |
| State | stateless scan → multi-day/multi-stage | environment-state graph; mission loop |
| Information | sparse start → continuously expanding evidence | evidence graph growth; info-gain actions |
| Failure | dead ends, false positives, unavailable tools, changing state | status vocabulary (§3.2), E1 rectifier |
| Scale | one target → many authorized target sets | scope.covers + target groups; scale ladder (§6 F8) |
| Planning | single action → long-horizon dependency graph | hierarchical DAG planner (F6) |
| Learning | failure → diagnosis → strategy adjustment | E1 → E1.5 loops |
| Evidence | every claim tied to reproducible evidence | receipts; TP-16 validation-first |
| Recovery | crash/interruption → resume from durable state | I1 durable store + resume checkpoint |
| Evaluation | simple lab → held-out difficult scenarios | E1.5a external verdict |

**Objective**: restore every welded/deleted offensive capability, then compound it
through evolution loops, making Raphael a continuously operating autonomous
offensive agent whose *decision quality* — not damage output — measurably improves
across engagements against operator-supplied target sets.

**End-state (all six hold simultaneously)**:
1. **Armed** — 10 execution bodies restored, full arsenal wired (recon → n-day →
   executor → C2 → post-ex), autonomy unbound per engagement config, broker intact.
2. **Continuous** — multi-hour autonomous runs, rotating operator target sets,
   zero approvals in-loop (receipts for every action).
3. **Absorbing** — feeds (KEV/EPSS/VulnCheck/LOLDrivers/MSF) enter the catalog as
   *queued tasks with provenance*, never auto-executed.
4. **Self-validating** — every technique claim reproduces on the lab range before
   `unverified → verified → wired`.
5. **Self-red-teaming** — scheduled jobs attack its own gates; regressions auto-file.
6. **Improving** — candidate strategies retained only on a measured positive delta
   on held-out scenarios, verdict from **protected external evaluation** (E1.5a).

**Definition of Done** (roadmap §0, unchanged): all 15 welds AUTHORIZED under open
policy; 10 bodies restored + live probes; suite green with INV-1/guardrails untouched;
cold-start E2E autonomous run with zero approvals; continuous episode loop.

**DoD-7 (v2.1) — Target Complexity Invariance**: increasing target size,
heterogeneity, uncertainty, or engagement duration must degrade Raphael's
performance *gracefully* rather than fundamentally breaking its planning model.
Verified via the horizontal/vertical scale ladders in §6 F8; measured by the
invariance metric in §9.

**Corrections adopted from architecture review**: continuous autonomy ≠
self-improvement; catalog growth ≠ better decisions; the system cannot certify its
own improvement; offensive power ≠ autonomy value (§4 ladder, §8 metrics).

---

## 2. RESTRICTION MODEL & NON-NEGOTIABLES

### 2.1 Five blocking layers (restoration opens in order)

| Layer | What it blocks | Where |
|---|---|---|
| L1 Policy | broker denies tool/agent actions; impact > budget; exact-match checks | `policies/bootstrap-v0.json`, `capability_broker.py:220-236` |
| L2 Weld gates | 43 files raise `WeldNotAuthorized` unless broker AUTHORIZED | `orchestrator/auth.py` + W-01…W-15 |
| L3 Deleted bodies | 10 files: gate passed then unconditional raise | §5 F2 table |
| L4 Dormant wiring | arsenal never proposed by Student/Planner; services unrouted | `runtime/loop.py`, `chains/` |
| L5 Autonomy bounds | max_iterations=1, approvals, command filter, falsification blocks, rate limits | `loop.py`, `api/types.py`, `command_filter.py` |

Plus environment: `reverse_shell.py` deleted, Python drift, no live LLM endpoint.

### 2.2 Non-negotiables / kill switch (standing, all phases)

- Broker mediation never bypassed — loops add receipts, not side doors (INV-1 preserved).
- Kill switch = swap decision source to `bootstrap-v0` → **one-file revert to deny-all**;
  tested once at end of F4.
- Rate ceilings and `scope.covers` never raised by any evolution loop.
- §11 non-goals stand (no ransomware/extortion playbooks, cash-out/laundering,
  victim-selection, uninvited targets).

---

## 3. ARCHITECTURE — FOUR-LOOP AUTONOMY

```text
┌─────────────────────────────────────────────┐
│ MISSION LOOP                               │  ← S6: watchdog, engagement
│ achieve objective → reassess → continue    │     rotation, receipts
│  ┌───────────────────────────────────────┐  │
│  │ EXPERIENCE LOOP                       │  │ ← E1 rectifier
│  │ act → observe → reflect → remember    │  │    (failure_class pre-task)
│  │  ┌─────────────────────────────────┐  │  │
│  │  │ STRATEGY LOOP                   │  │  │ ← E1.5 (the missing layer)
│  │  │ generate → evaluate → select    │  │  │
│  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │ SELF-ASSURANCE LOOP       │  │  │  │ ← E5 self-red-team
│  │  │  │ test → detect → repair    │  │  │  │
│  │  │  └───────────────────────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

Substrate (under all loops): broker + 20-field hash-bound `ActionReceipt`,
`scope.covers` + rate ceilings + kill switch. Capability growth (E2/E3/E4) is
orthogonal — it expands the **action space**; only E1.5 changes the **decision
process**.

### 3.1 Target Complexity Abstraction Layer (v2.1)

Sits above the capability ladder, below the mission loop — **extends** the four
loops rather than replacing them: Mission manages the global objective, Strategy
picks which branch deserves attention, Experience learns, Self-Assurance checks
reasoning integrity and invariants.

```text
                         RAPHAEL
                            │
                 ┌──────────▼──────────┐
                 │ Mission Controller  │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │ Target Understanding│
                 │ + Complexity Model  │
                 └──────────┬──────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Attack Surface      Environment          Objective
     Graph             State Graph          Graph
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                  Strategy Generation → Evaluation → Action Selection
                            │
                     Broker / Scope
                            │
                   Capability Layer
                            │
                  Evidence / Receipts
                            │
                  Observe ──┴── Reflect
                            │
                       Experience → Replanning
```

**Key change: Raphael never decides strategy solely from available tools.** It first
constructs a model answering nine questions, then chooses the next action:

1. What exists? 2. What is known? 3. What is uncertain? 4. What has been tested?
5. What failed? 6. What relationships exist between discovered assets?
7. What objectives remain? 8. What actions are actually authorized?
9. What evidence would prove or disprove a hypothesis?

### 3.2 Target Model, Hypothesis Model & uncertainty management

**Hypothesis records are first-class** — "I don't know" is a state, not a failure:

```text
Hypothesis H17
────────────────────────────────
Claim:      Asset X is related to service Y
Evidence:   + fingerprint match
            + certificate relationship
            - ownership unconfirmed
Confidence: 0.63
Next information-gain action: [candidate action]
Status:     UNCONFIRMED
```

**Status vocabulary (never collapse these into "EXPLOIT FAILED"):**

`UNKNOWN` · `UNREACHABLE` · `UNAUTHORIZED` · `UNSUPPORTED` · `UNVERIFIED` ·
`FAILED` · `BLOCKED` · `LOW CONFIDENCE` · `PROVEN`

- Connects directly to TP-16 validation-first: an LLM-generated claim is never an
  observed fact; `PROVEN` requires a receipt-backed observation.
- **Raphael must be able to say "I can't."** Honest `REFUSE`/`UNAUTHORIZED`/
  `UNSUPPORTED` outcomes (the Meow precedent: reached an honest REFUSE rather than
  fabricating success when governed capability did not match the target's service)
  are correct behavior, centrally preserved. Maturity = distinguishing these nine
  states, not maximizing `PROVEN`.
- `UNAUTHORIZED`/`UNREACHABLE` feed E1 as non-retryable `failure_class` entries;
  `LOW CONFIDENCE` drives info-gain action selection (reduce uncertainty before
  acting).

### 3.3 Hierarchical reasoning (the scaling fix)

A huge target cannot be handled by a larger context window. Raphael reasons
hierarchically; the same architecture serves every level:

```text
Engagement
├── Business / environment
├── Target groups: internet perimeter · identity · cloud · SaaS · internal net · endpoints
├── Asset clusters: web-01 · api-* · AD · cloud accounts · edge devices
└── Local hypotheses: H1 · H2 · H3
```

Mission Loop = global objective. Strategy Loop = which branch deserves attention.
Experience Loop = what happened. Self-Assurance Loop = reasoning integrity +
invariants. Result: an **autonomous research-and-decision system**, not an enormous
collection of attack scripts. Each node carries its own nine-question model (§3.1)
and hypothesis set (§3.2); evidence propagates up the tree via receipts.

---

## 4. TECHNIQUE PATTERN LAYER (research rounds 1-17 → architecture)

The single biggest gap this v2 closes: 17 research rounds ended in ad-hoc
"integration" paragraphs with no authoritative home per pattern. This section is
that authority. Each pattern (TP-xx) has exactly one architecture home, a tier,
and a build phase; §7 tracks acceptance.

### 4.1 Distilled convergence findings

1. **Trust & identity beat perimeter** — across hacktivist, nation-state, and
   cybercrime classes alike, the dominant entries are trust-chain and identity
   abuse; a 2026 lens adds SaaS/OAuth consent and misconfigured guest profiles
   over CVEs (R13, R16, R17).
2. **Trust chains escalate**: registrar/CMS/ad-widget (2014) → npm packages, OAuth
   apps, SaaS admin APIs, MDM (Intune-as-wiper), captive portals (2025-26).
3. **Validation is the bottleneck** — GTG-1002's AI attacker hallucinated results
   and needed constant human verification (R17). Receipt-backed verification of
   every claimed finding is therefore core, not a nicety.
4. **Enforcement breaks on identity + money** (R10-17 OPSEC tables) — Raphael
   structurally holds neither: declared scope, receipts, no identities/funds.
5. **Impact phase is out** (§11): ransomware, cash-out, wipers, extortion, DDoS
   vs uninvited targets are *recognition/defense content only*.

### 4.2 Pattern inventory (the mapping table)

| ID | Pattern | Source rounds | Architecture home | Tier | Build phase |
|---|---|---|---|---|---|
| TP-01 | Passive-first discovery chain + pivots (subfinder→puredns→alterx; favicon/JARM) | R2 | `chains/tool_registry` recon chain | A | F3 |
| TP-02 | Web-app vuln detection with evidence receipts (SQLi error/blind class, headers, TLS) | R10, osmania exercise | whatweb/nuclei/sqlmap executors → receipts | B | F3 |
| TP-03 | n-day prioritized exploit loop (KEV/EPSS/VulnCheck → `check()` → execute) | R7 | E2 queue → W-01 executor | B/C | F3 |
| TP-04 | Allowlist-shaped execution (signed-binary proxying, RMM/LOTL, LOLBAS catalog) | R4, R12, R16 | capability catalog entries w/ machine preconditions | C | F3 |
| TP-05 | BYOVD data-only defense evasion | R5, R16 | catalog Tier-E entries (precondition: HVCI off) | E | F3-last |
| TP-06 | Anti-analysis implant profiles (time-gate, env-check, dormancy receipts) | R6, R11 | `sandbox.py` staging gates + build profiles | E | F3 |
| TP-07 | C2 cloaking: redirector fleet, malleable profiles, per-phase channels | R8, R11 | `cloak-service`, `proxy_guard` | D | F3 (S4 slot) |
| TP-08 | Edge-device exposure inventory (VNC, SOHO routers, captive portals, MDM) | R11, R14, R15 | new Tier-A recon section → report findings | A | F3 |
| TP-09 | Third-party trust-chain inventory (DNS/registrar, CMS, widgets, OAuth consent, SaaS integrations, npm/CI-CD, GitHub secrets) | R9, R10, R15, R16 | new Tier-A recon section + `A03` checklist rows | A | F3 |
| TP-10 | Identity-surface defense checks (push-bombing, SIM-swap, session/token binding, helpdesk verification, OAuth consent governance) | R12, R16 | `A07` checklist + report remediation items | — | E4 |
| TP-11 | Supply-chain build/package recognition (build injection, package poisoning, stale test credentials) | R11, R15, R16 | `A03` checklist + E2 feed awareness | — | E2/E3 |
| TP-12 | Detection fixtures: DGA/encoding C2, fake-SSO domains, push-fatigue traffic | R11, R12 | E3 blue fixtures | — | E3 |
| TP-13 | Dormancy / victim-conditional logic recognition | R11 | planner knowledge (S7) + report items | — | E4 |
| TP-14 | DoS/DDoS + gamified hacktivism recognition; opportunistic VNC/OT intrusion checks | R10, R14 | report items + OT exposure checks in Tier A | A | F3 |
| TP-15 | Remote-admin/MDM-as-wiper recognition (Intune class) | R14, R15 | defense checklist | — | E4 |
| TP-16 | Validation-first discipline: every claimed finding verified against a receipt | R17 | receipt model promoted to core planner requirement | substrate | standing / F6 |
| TP-17 | Structural OPSEC (no identities/funds, declared scope, rate ceilings) | R10-17 OPSEC tables | §2.2 non-negotiables (already structural) | substrate | standing |
| TP-18 | Cross-group strategy feature space (entry × persistence × evasion taxonomy) | R13, R17 | E1.5 candidate-strategy features | — | E1.5a |
| TP-19 | Difficulty-ladder scenario archetypes (hacktivist → cybercrime → APT grade) | R10-17 | S7 planner ladder → **F6** + E1.5 held-out suite | — | F6 / E1.5a |
| TP-20 | Entry-vector coverage histogram (TA0001–TA0011, difficulty-weighted) | R13, R17 | metrics §8 row | — | H |

### 4.3 Where patterns land (six destinations)

| Destination | Patterns | Mechanism |
|---|---|---|
| Wired capabilities (execute) | TP-01…TP-07 | F3 capability layer + tool registry (broker-mediated) |
| Recon sections (observe, report) | TP-08, TP-09, TP-14 | Tier-A chain additions; findings → report |
| Knowledge/checklists (defensive report content) | TP-10, TP-11, TP-13, TP-15 | `references/` rows; E4 promotion |
| E3 blue fixtures (detection exercises) | TP-12 | lab range scenarios |
| Substrate/decision process | TP-16, TP-17, TP-18, TP-19 | receipts, §2.2, E1.5a, F6 planner |
| Metrics | TP-20 | §9 dashboard |

### 4.4 Excluded by §11 (recognition only, never operationalized)

Ransomware/extortion playbooks and leak-site ops; cash-out/laundering; wiper
weaponization; DDoS tooling against uninvited targets; victim selection. All
ransomware/hacktivism data in the research files exists solely so reports can
*recognize* these patterns on operator-declared targets.

### 4.5 Pattern acceptance criteria (TP-acc, #28 — testable exit conditions)

Every TP is done only when its criterion passes in the lab range (E3-Range) with
receipts archived. These fold the research into testable F3/F5/F6/E1.5a
requirements rather than decorative table rows.

| ID | Acceptance criterion |
|---|---|
| TP-01 | lab chain run emits host-list receipt; every expansion re-checked by `scope.covers`; zero target creep |
| TP-02 | SQLi-class detection on DVWA produces a finding carrying request/response evidence receipt (osmania methodology, lab targets only) |
| TP-03 | one end-to-end loop: KEV queue entry → `check()` → execute → receipt → next action |
| TP-04 | every catalog execution action carries machine-readable preconditions; broker **denies** when unmet |
| TP-05 | BYOVD entry denied unless HVCI-off precondition proven; reachable only after Tier-E gate |
| TP-06 | dormancy decision (execute vs skip) emits a receipt; silent non-execution ≠ failure |
| TP-07 | redirector config issued + per-phase channel separation observable in receipts |
| TP-08 | recon section reports VNC/SOHO-router/captive-portal/MDM exposure as findings on lab |
| TP-09 | third-party trust inventory runs on lab (OAuth consent, SaaS integrations, CI/CD secrets); new `A03` rows added |
| TP-10 | generated report includes identity-defense items with 2025-26 case citations (§ R16 sources) |
| TP-11 | `A03` build/package rows exist; E2 queue flags the stale-test-credential pattern (Klue class) |
| TP-12 | three E3 fixtures (DGA-encoded C2, fake-SSO domain, push-fatigue traffic) each detected |
| TP-13 | planner classifies a dormancy/victim-conditional pattern in ≥1 scenario; report item generated |
| TP-14 | report includes DoS-recognition + VNC/OT exposure findings |
| TP-15 | defense checklist contains the remote-admin/MDM-as-wiper item |
| TP-16 | planner **refuses** any finding not backed by a receipt: injected fabricated claim → refused, not promoted |
| TP-17 | §2.2 invariant tests green: no ceiling raise anywhere, kill-switch reverts to deny-all, INV-1 violations = 0 |
| TP-18 | E1.5a candidate feature vectors drawn from the entry×persistence×evasion taxonomy; suite scores expose those axes |
| TP-19 | held-out suite contains ≥1 scenario per archetype tier (hacktivist / cybercrime / APT grade) |
| TP-20 | engagement report emits the TA0001–TA0011 entry-vector histogram with difficulty weights |
| TP-16 ext. | *(F5 gate)* nine-state status vocabulary exercised: a run produces ≥3 distinct honest states (`UNAUTHORIZED`, `UNSUPPORTED`, `LOW CONFIDENCE`) without collapsing to `FAILED` |

---

## 5. CAPABILITY LADDER (dual-axis, annotated with patterns)

Offensive power = blast radius × reliability. Autonomy value = action diversity ×
observability × feedback quality × reproducibility × strategic depth.
**Progress = how intelligently the action space is used, never damage potential.**

| Tier | Class | Members | Autonomy value | Patterns | Role in evaluation |
|---|---|---|---|---|---|
| A | Discovery | subfinder, puredns, alterx, nuclei | **Very high** | TP-01, TP-08, TP-09, TP-14 | First autonomy substrate |
| A+ | Knowledge/research | `browser_research` (CloakBrowser, S5r) | **Very high** | feeds all TPs | Intelligence feed; `research_scope` receipts |
| B | Validation | whatweb, MSF `check()`, controlled verification | High | TP-02, TP-03 | Hypothesis → test → consequence |
| C | Multi-step strategy | MSF exploits, Certipy, autobloody | High | TP-04, TP-03 | Strategy-loop substrate |
| D | Long-horizon state | Sliver C2, cloak/proxy, mission state | Medium-high | TP-07 | Mission continuity |
| E | High-consequence | BYOVD, anti-analysis, destructive classes | Medium | TP-05, TP-06 | Wired last; strongest isolation (E3 + §2.2) |

Progression rule: demonstrate autonomous competence at tier *k* (E1.5 external
verdict) before wiring tier *k+1*.

### 5.1 Capability abstraction — verbs, not tools (v2.1)

The planner reasons over **abstraction verbs**:

`DISCOVER` · `ENUMERATE` · `IDENTIFY` · `VALIDATE` · `CORRELATE` ·
`FORM_HYPOTHESIS` · `TEST_HYPOTHESIS` · `REASSESS` · `DOCUMENT`

Tiers describe capability *families*; **tools are implementations of
capabilities** — each registered in the catalog as a broker-mediated action with
prerequisites, receipts, scope, and impact/rate checks. New capability families
plug in **without rewriting the planner**. This is how the anti-goal is enforced:

> "Raphael knows tool X, therefore Raphael can handle target X" — rejected.

Tools change; the verb vocabulary and the target model (§3) do not. This is also
the mechanism behind Target Complexity Invariance (DoD-7): complexity growth
changes the *graph*, not the action vocabulary.

---

## 6. UNIFIED BUILD SEQUENCE (P-phases ∧ S-phases merged)

Old numbering reconciled: P0→F0, P1+P1.5→F1 (=S1+S2), P2→F2 (=S3),
P3→F3 (=S4+S5+S5r), **P4→F7, P5→F8, P6→F9** — with **two new phases F4/F5**
inserted (v2.1): the roadmap's old spine "restore → wire → unbind → continuous"
becomes:

```text
F0–F2 Foundation → F3 Capability → F4 Target Understanding → F5 Hypothesis Engine
      → F6 Strategy/Planning → F7 Controlled Action + Autonomy
      → Evidence + Verification → Experience/Memory → External Evaluation
      ───────────────────────────────────────────► Strategy Improvement
```

The tail (evidence → experience → evaluation → improvement) is the loop machinery
of §7; **F4 and F5 are the genuinely new phases** — the missing Target Model +
Hypothesis Model connecting the four loops to arbitrary-scale environments.
Closure phases (S2.5, I1, E3-Range) interleave as shown.
**No phase starts before its gate.**

```text
F0 → F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 → F9
      │    │     │    │     │           │     │
      │    │     │    │     │           │     └─ scale ladders + DoD-7 invariance
      │    │     │    │     │           └─ I1 durable receipts before continuous runs
      │    │     │    │     └─ needs S2.5 toolchain (graphs built from recon output)
      │    │     │    └─ F8 needs E3-Range standing
      │    │     └─ E1/E2/E5 build in parallel (in-distro lane)
      │    └─ test flip + restrictive control (hard gate)
      └─ F6 planner ← E1 receipts + E1.5a suite (parallel from F4 on)
```

| Phase | Contents | Gate | Size |
|---|---|---|---|
| **F0 Stabilize** | restore `reverse_shell.py`; commit baseline (P0.2); venv 3.12; LLM endpoint config | suite = 621 green | S |
| **F1 Open policy** | `engagement-open-v0.json`; wildcard matchers; open loader/ScopeV0; **test-regime flip** (~40 sites) + `test_restrictive_policy_still_denies` | weld probe all-AUTHORIZED **and** restrictive DENIED; suite green | S–M |
| **F2 Restore bodies** | 10 deleted bodies, dependency order (inspect→craft→deploy→run), **commit per file** | per-file probe: harmless exec through restored sink → receipt; `fixture.inspect` intact | M |
| **F3 Arsenal + patterns** | capability layer (ToolExec/KaliTool/Shell/CodeExec/C2/Phish/Harvest); **TP-01…TP-09 wiring**; S4 slot = TP-07 cloak; S5r browser_research; S2.5 toolchain prerequisite | one run spans recon→queue→exec→cloak receipts; restrictive control still denies | L |
| **F4 Target Understanding** *(new v2.1)* | Target Model + Complexity Model; three graphs (attack-surface, environment-state, objective); hierarchical engagement tree (§3.3); nine-question model (§3.1) evaluated per node | lab arena fully modeled: every target group answers all nine questions; every graph mutation emits a receipt | L |
| **F5 Hypothesis Engine** *(new v2.1)* | hypothesis records (claim/evidence±/confidence/next-info-gain/status); nine-state vocabulary; honest REFUSE path; info-gain action selection (§3.2) | full lifecycle on lab: `FORM_HYPOTHESIS → TEST_HYPOTHESIS → PROVEN` **and** an honest `REFUSE`/`UNAUTHORIZED`/`UNSUPPORTED` outcome, both receipted; fabricated claim refused (TP-16) | M |
| **F6 Strategy/Planning** *(absorbs old S7)* | hierarchical difficulty-aware DAG planner over §3 graphs; resource/uncertainty management; TP-19 ladder; TP-16 validation-first; verb vocabulary (§5.1) | multi-step plan executes with full receipts; planner picks branch from model, not from tool list | L |
| **F7 Autonomy** *(was F4)* | driver script; approvals→open; command filter short-circuit; falsification→advisory; providers live; **replan trigger re-based**: `stage_replan` fires only on `DenialClass.PERSISTENT` (verified `stages.py:756/796`, `brain/action.py:538`) — open policy deletes exactly those denials, so the trigger must move to reconciliation-invalid / evidence-divergence (brain report 2026-09-30) | 3-iteration episode, zero approvals, zero `WeldNotAuthorized`; **kill-switch tested**; **≥1 replan proven from a non-denial trigger** | M |
| **F8 E2E + scale ladders** *(was F5 + v2.1 acceptance)* | compose arena → full chain + C2 + phish + failure-injection scenarios; then **horizontal ladder** (1 → 10 → 100 targets → enterprise → multi-environment) and **vertical ladder** (simple → complex → multi-stage → long-horizon → high-uncertainty) | DoD 4/5 proven + **DoD-7 invariance**: performance degrades gracefully across both ladders — no planning-model break | M–L |
| **F9 Ops** *(was F6)* | crash-restart, evidence rotation, telemetry, README truth sync, resume-from-checkpoint (recovery metric) | continuous supervised run incl. interruption-resume | S |

**Scaling doctrine (v2.1)**: the system must not require a different architecture
at each level — horizontal growth adds nodes to the engagement tree (§3.3);
vertical growth deepens hypotheses/uncertainty per node; both are *model* growth,
never planner rewrites.

**Interleaved closure phases** (own gates, from v2 §2A of the old blueprint):

| ID | Task | Gate | Owner |
|---|---|---|---|
| S2.5 | Toolchain bring-up (env_inventory → tier-ordered install → registry version receipts) | Tier A+B present, versioned | in-distro |
| I1 | Durable JSONL receipt store (replace ephemeral dict at `action_receipt.py:60`) + resume checkpoint | kill-restart: hash chain verifies; engagement resumes | this session, after integration review closes |
| E3-Range | docker vulnerable services + full logging (operator target set by construction) | one E2→E3 promotion end-to-end | in-distro (spec: this session) |
| S7 | *absorbed into F6* (hierarchical planner + TP-19 ladder; AutoPen precedent) | see F6 gate | this session |
| S5r | `browser_research` capability — CloakBrowser engine validated; **host-guard + headed+humanize mandatory** | query→paper→claim→planner context with citation receipts | this session, after integration review |

---

## 7. EVOLUTION LOOPS (built after F3 — what makes it compound)

**E1 rectifier memory** — pre-task: `failure_class: str` on `ActionReceipt`
(seed from `cerebellum/error_diagnoser.py` vocabulary + `llm_transport`
`FAILURE_CLASS_*`), hash-bound, integrity green. Cache key
`(action_type, target, failure_class)`; retryable classes bypass cache.
Metric: repeat-failure rate → 0.

**E1.5 strategy selection (the missing layer)** — E1 trajectories → parameterized
strategy candidates → **held-out suite** (Raphael neither generates nor reads
scores) → retain only on positive externally-signed delta. Candidate feature
space = **TP-18**. Dependencies: E1 failure_class, E3 verification, evaluation
harness. Owner: design = this session; selector unassigned.

**E2 feed absorption** — KEV/EPSS/VulnCheck/LOLDrivers/MSF poller → catalog queue
with provenance receipt, never auto-executed; absorbs **TP-11** awareness. Metric:
KEV publish → queue < 24h.

**E3 lab validation** — every claim reproduces on range → `unverified → verified →
wired`; hosts **TP-12** fixtures. Metric: ≥90% of catalog verified before reachable.

**E4 after-action growth** — engagement findings → `references/` rows (where
**TP-10/11/13/15** land) → new action types via the same 4-step promotion.

**E5 self-red-team** — restrictive control must deny, weld probes must gate,
scope-escape must fail-closed, ceilings must throttle; mechanical pass/fail only —
never certifies "got better" (that is E1.5a). Metric: MTTR < 1 day; guardrail
violations = 0, always.

**E1.5a external evaluation** — held-out scenario suite + protected verdict;
the structural countermeasure to the GTG-1002 failure mode (**TP-16/17**).

---

## 8. EXECUTION TABLE (living — update status in place)

Status legend: DONE · DISPATCHED · OFFERED · IN PROGRESS · PENDING · BLOCKED · DEFERRED.

| # | ID | Task | Owner | Status | Depends on | Exit gate |
|---|---|---|---|---|---|---|
| 0 | P0/P1 | Baseline `e6a8c707e` + P1 content edits | this session | DONE (in worktree, unverified) | — | content PASS; merge blocked by #2 |
| 1 | E1-pre | `failure_class` on `ActionReceipt` + keyed cache | in-distro | DISPATCHED (0/2 landed) | — | 3-path integrity green |
| 2 | S1a | CUT dead `to_open_broker_policy` alias | in-distro | DISPATCHED (0/2 landed) | — | grep 0 hits + suite |
| 3 | S1b | Restore `reverse_shell.py`, run `p1_verify.py` + suite ≥621 | in-distro | OFFERED | — | probes AUTHORIZED; restrictive DENIED |
| 4 | — | Integration review of P1 diffs (+ #1-#2 when landed) | this session | IN PROGRESS | 0, 1, 2 | diff audit PASS |
| 5 | S0 | Re-arm host-side `wsl.exe` exec | — | **DONE** (self-healed 2026-09-30) | — | `wsl.exe -d Ubuntu -- echo ok` |
| 6 | F1/S2 | Test-regime flip + restrictive negative control | this session (spec) / exec TBD | PENDING | #3 green | suite green AND restrictive denies |
| 7 | F2/S3 | Restore 10 bodies, dep order, commit per file | this session | PENDING | #6 | per-file receipts; fixture.inspect intact |
| 8 | F3/S4 | C2/cloak/proxy restoration (TP-07) | this session | PENDING | #7 | redirector config + channel separation in receipts |
| 9 | F3/S5 | Arsenal wiring + **TP-01…TP-09, TP-14** pattern wiring | this session | PENDING | #8, #20 | engagement run spans recon→queue→exec→cloak |
| 10 | F7/S6 | Autonomy unbinding + kill-switch test (operates *through* F4-F6) | this session | PENDING | #9, #16, #29, #30 | 3 proofs: continuous, 0 INV-1 + switch, E1.5a verdict; replan fires without denial (open-policy invariant) |
| 11 | E1 | Rectifier store live | in-distro | PENDING | #1 | repeat-failure → 0 |
| 12 | E5 | Self-red-team job | in-distro | PENDING | #6 | MTTR < 1 day; floor re-asserted |
| 13 | E2 | Feed poller (absorbs TP-11) | in-distro | PENDING | queue schema | KEV → queue < 24h |
| 14 | E3 | Lab range + **TP-12 fixtures** | UNASSIGNED | PENDING | minimal Tier A | ≥90% catalog verified |
| 15 | E4 | After-action growth (**TP-10/11/13/15 landing**) | in-distro | PENDING | #14 promotion chain | entries added per engagement |
| 16 | E1.5a | Held-out suite + external verdict design (**TP-18/19 features**) | this session | DESIGN NOW (parallel #6/#7) | #1, metrics harness | Raphael can't generate/read scores |
| 17 | E1.5b | Strategy selector | UNASSIGNED | PENDING | #11, #14, #16 | retain only on positive external delta |
| 18 | H | Metrics harness (§9 dashboard + **TP-20**) | in-distro | PENDING | §9 rows | dashboard live |
| 19 | — | Research rounds absorption | this session | **DONE** — rounds 1-17 compiled | — | both research files + this §4 |
| 20 | S2.5 | Toolchain inventory + tier-ordered install + registry | in-distro | PENDING | exec only | Tier A+B versioned + receipts |
| 21 | I1 | Durable JSONL receipt store | this session | PENDING (after #4) | #4 | restart: chain verifies |
| 22 | E3r | Range bring-up docker services | in-distro (spec: this session) | PENDING | Tier A | one E2→E3 promotion |
| 23 | F6/S7 | Hierarchical planner (**TP-16 validation-first, TP-19 ladder, §3 graphs, §5.1 verbs**) | this session | PENDING | #11, #16, #29, #30 | multi-step plan + full receipts; planner branches from model, not tool list; AutoPen in `references/papers/` |
| 24 | — | Rounds 9-13 research (supply-chain … synthesis) | this session | **DONE** | — | `famous_group_ttps_v1.md` R10-13 + `offensive_powerups_v1.md` R9 |
| 25 | S5r | Browser-research capability — spec'd + engine validated | this session | SPEC'D + ENGINE-VALIDATED (implement after #4) | #4 | query→paper→claim→planner context w/ receipts |
| 26 | — | Rounds 14-17 recency addendum (2025-26 campaigns) | this session | **DONE** (2026-09-30) | — | `famous_group_ttps_v1.md` §Addendum |
| 27 | — | **Technique pattern layer (this §4)** | this session | **DONE** (2026-09-30) | #19, #24, #26 | TP-01…TP-20 mapped to homes |
| 28 | TP-acc | Per-pattern acceptance criteria (§4.5) | this session | **DONE** (2026-09-30) | #27 | every TP has a testable exit condition |
| 29 | TU-1 | **Target Model + Complexity Model schema** (§3.1/§3.3: three graphs, nine questions, hierarchical tree, receipted graph mutations) | this session | PENDING | #27 | lab arena fully modeled per F4 gate |
| 30 | HE-1 | **Hypothesis Engine** (§3.2: records, nine-state vocabulary, info-gain selection, honest-REFUSE path) | this session | PENDING | #29 | F5 gate: PROVEN + honest REFUSE lifecycle receipted; fabricated claim refused |
| 31 | TCL-1 | **Target Complexity Invariance acceptance** (§6 F8 horizontal/vertical ladders + §9 invariance metric) | UNASSIGNED | PENDING | #10, #23 | DoD-7: graceful degradation measured at every ladder rung |

---

## 9. METRICS DASHBOARD

| Metric | Source | Target |
|---|---|---|
| Autonomous hours per run | watchdog | multi-hour, rising |
| Receipt coverage of actions | receipts DB | 100% |
| Catalog entries / % verified | catalog | growing, ≥90% verified |
| Feed-latency KEV → queue | poller | < 24h |
| Repeat-failure rate | rectifier | → 0 |
| Self-red-team MTTR | E5 tasks | < 1 day |
| Strategy survival (B vs A delta) | E1.5a external eval | positive signed delta only |
| Guardrail (INV-1) violations | receipts | 0, forever |
| Suite floor | pytest | ≥ 621, growing |
| Tier competence A→E | E1.5a eval | rises; damage is never a metric |
| **Pattern coverage** | §4 / §4.5 | all TP criteria defined (done 2026-09-30); then wired+passing |
| **Entry-vector histogram** (TP-20) | engagement reports | coverage vs TA0001–11, difficulty-weighted |
| **Target Complexity Invariance** (DoD-7) | §6 F8 scale ladders | performance slope vs size/heterogeneity/uncertainty is graceful, never a planning-model cliff |
| **Hypothesis accuracy** | F5/E3 range | proven/refuted vs range ground truth; rising |
| **Evidence quality** | receipts | receipt-backed claim ratio = 100%; fabricated-claim refusals logged (TP-16) |
| **Honest-state discipline** | status vocabulary | ≥3 distinct non-`FAILED` negative states used per run; zero collapses |
| **Planning depth** | planner telemetry | median DAG depth per engagement; grows with tier, not with target size alone |
| **Replanning quality** | E1.5a | share of replans that beat the prior strategy on held-out scenarios |
| **Recovery after interruption** | I1 + F9 | resume from durable state with zero evidence loss |
| **Resource efficiency** | receipts | actions + tool-time per verified finding; trending down |

---

## 10. IMMEDIATE BACKLOG (next session, in order)

**Lane split (standing):** in-distro owns E1/E2/E4/E5, metrics harness, dispatched
items; this session owns F1/F2 verification bookkeeping, doc upkeep, F3+ design,
E1.5a evaluation design. No file overlap.

1. [dispatched → in-distro] `failure_class` on `ActionReceipt` + keyed E1 cache.
2. [dispatched → in-distro] CUT dead `to_open_broker_policy` alias.
3. [in-distro, offered] S1 verification package (`reverse_shell.py`, `p1_verify.py`, suite ≥621).
4. ~~[this session] TP-acc (#28)~~ **DONE** — criteria live in §4.5.
5. [this session] **TU-1/HE-1 (#29/#30)**: design the Target Model + Hypothesis
   Model schemas (three graphs, nine questions, hypothesis record, nine-state
   vocabulary) — the v2.1 missing piece; inputs to F4/F5/F6.
6. [this session] F1 test-regime spec; F2 restoration recipes per file.
7. [this session] Integration review when #1/#2 land.

Deferred/withdrawn: osmania follow-ups (operator: forget it); 13-OA-paper bulk
fetch offer (still open, non-blocking).

---

## 11. NON-GOALS (unchanged from roadmap §5)

- No Section-5-adjacent content anywhere in scope; engagements run against
  operator-supplied target sets only.
- No deletion of INV-1/guardrail machinery — restoration is *through* the gates.
- No ransomware/extortion playbooks, cash-out/laundering, victim-selection,
  uninvited targets — ever, as capability.
- README/evidence truthfulness fixes tracked separately (audit H-1/H-2).

---

## APPENDIX A — Risk register (merged)

| Risk | Mitigation |
|---|---|
| Bodies unrecoverable from git history | per-item probe first; rewrite from raise-message comments |
| Denial-test rework slips → suite red | F1 is a hard gate before F2 merges |
| LLM endpoint unavailable → Student inert | deterministic candidate generator fallback |
| Docker/kali arena unavailable | degrade to local-toolchain scenario |
| INV-1 guard fights new code | primitives under `exec/` (guard's CANONICAL_TREES) |
| 621 floor drifts as bodies return | record suite at every gate; floor only ratchets up |
| Pattern sprawl (TP list grows unbounded) | §4 is the only home; additions require source-round citation + home + tier + phase |
| Research/code divergence | TP-acc (#28) makes patterns testable, not decorative |

## APPENDIX B — Supersession notes

- `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md` → archive: build phases now §6,
  restriction model §2, DoD §1, non-goals §11, risks App. A.
- `RAPHAEL_EVOLUTION_BLUEPRINT_v1.md` → archive: loops §7, ladder §5, execution
  table §8, metrics §9, backlog §10, four-loop diagram §3, status §0.
- Research files remain canonical source material:
  `references/offensive_powerups_v1.md` (rounds 1-9),
  `references/famous_group_ttps_v1.md` (rounds 10-17);
  patterns extracted into §4 above.
