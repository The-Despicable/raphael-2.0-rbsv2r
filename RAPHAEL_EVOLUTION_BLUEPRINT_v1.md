# RAPHAEL EVOLUTION BLUEPRINT v1 — From Restoration to Self-Evolving Weapon

> **SUPERSEDED 2026-09-30** by `RAPHAEL_ARCHITECTURE_ROADMAP_v2.md` (operator
> directive: singular architecture/roadmap absorbing research rounds 1-17).
> This file is retained as an archive. Live content: loops → v2 §7, capability
> ladder → v2 §5, execution table → v2 §8, metrics → v2 §9, backlog → v2 §10,
> four-loop diagram → v2 §3, status → v2 §0, technique patterns → v2 §4.

Status: ARCHIVED (superseded by v2)

Companion to `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md` (also archived). The roadmap restores
capability; this blueprint layers the **evolution loops** that compound it —
every engagement, every feed, every self-test makes Raphael sharper. Built on
verified status as of 2026-09-30.

---

## 0. STATUS SNAPSHOT (verified)

| Fact | Evidence |
|---|---|
| Branch `offensive-restore`, HEAD == baseline `e6a8c707e`, zero commits since | `git log --oneline -3` |
| P1 edits present in worktree, content PASS | P1-VERIFY-01 (5 paths + untracked `policies/engagement-open-v0.json`) |
| `interactive_shell/reverse_shell.py` **still deleted** (only stale .pyc remains) | directory glob 2026-09-30 |
| Dead `to_open_broker_policy` alias still present (`runtime/policy.py:157-168`) | P1-VERIFY-01 |
| Verification probes written, **never run** | `/mnt/c/.../Temp/opencode/p1_verify.py`, `weld_probe.py` |
| Full suite not run since P1 edits; last green = 621 at P0.1 | session log |
| P1.5 pending: ~40 `pytest.raises(WeldNotAuthorized)` sites + 2 guardrail tests | `test_am4_weld_gates.py`, `sub10/sub13` |
| **Environment degraded**: `wsl.exe -- <cmd>` fails 0x8007274c while `\\wsl.localhost` FS works, distro shows Running | live commands this session |
| Research rounds 1-8 compiled | `references/offensive_powerups_v1.md`; rounds 9-10 deferred |
| **Receipt audit (2026-09-29, hypothesis rejected)**: deny/success/timeout share identical 20-field hash-bound records, integrity passes all three — no thin-success gap. Real gap = no outcome vocabulary: `result` free-text, `impact_estimate` str, TIMEOUT-vs-FAILED only via `status`. E1 cache key unrecoverable until fixed. | scratch probe (deleted); `ActionReceipt` dataclass, `verify_integrity()` on 3 paths |
| WSL breakage is Windows-host side only; distro runs commands natively (uname 6.6.87.2-microsoft-standard-WSL2) — S0 not blocking in-distro work | live, 2026-09-29 |

---

## 1. END-STATE DEFINITION ("ever evolving weapon")

Raphael is done when **all six** hold simultaneously:

1. **Armed**: all 10 execution bodies restored, full arsenal wired (recon →
   n-day → executor loops, cloak/redirector infra), autonomy unbound per
   engagement config — with broker mediation intact.
2. **Continuous**: multi-hour autonomous runs without operator prompts
   (P6), engaging rotating operator-supplied target sets.
3. **Absorbing**: threat feeds (KEV/EPSS/VulnCheck/LOLDrivers) enter the
   capability catalog automatically as *queued tasks with provenance receipts* —
   never auto-executed.
4. **Self-validating**: every technique claim passes a lab-range reproduction
   before promotion from `unverified` → `verified` → `wired` in the catalog.
5. **Self-red-teaming**: scheduled jobs attack its own gates (restrictive
   control, weld probes, blindspot scenarios); any regression is auto-filed
   and fixed before it can hide.
6. **Improving**: a candidate strategy is retained only when it
   demonstrably outperforms the incumbent on held-out scenarios, with the
   acceptance verdict from **protected external evaluation** — never from
   Raphael judging itself.

**Corrections adopted from architecture review (2026-09-29):**
- *Continuous autonomy ≠ self-improvement.* S6 delivers persistent
  operation; getting better is a separate problem, owned by E1.5. A system
  can run 20 hours and learn nothing.
- *A growing catalogue ≠ a better decision process.* E2/E3/E4 grow
  knowledge and capability (the action space); only E1.5 changes how
  strategies are selected (the decision process).
- *The system cannot certify its own improvement.* E5's gate tests are
  mechanical (objective pass/fail) and may self-run; any "evolved and now
  better" claim is not machine-checkable from inside and routes to
  external evaluation — otherwise `Raphael changes itself → Raphael
  evaluates itself → Raphael declares itself improved`.
- *Offensive power ≠ autonomy value.* Blast radius ranks tools;
  autonomy value = action diversity × observability × feedback quality ×
  reproducibility × strategic depth. Progress = how intelligently the
  action space is used, never how much damage the toolset can cause
  (§7C tier ladder).

---

## 1A. FOUR-LOOP AUTONOMY ARCHITECTURE

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

Coverage today: mission loop = S6; experience loop = E1; self-assurance =
E5; capability growth (E2/E3/E4) is **orthogonal** — it expands the action
space, not the decision process. The **strategy loop (E1.5) is the gap**
between "Raphael remembers" and "Raphael becomes better."

## 2. PHASE LADDER (actionable, ordered)

Each phase: tasks → exit gate → commit. No phase starts before its gate.

### S0 — Re-arm environment (blocker, ~15 min)
1. Restore WSL exec: try `wsl.exe -d Ubuntu -- echo ok`; if persists,
   `wsl --shutdown` then start distro — **operator confirmation required**
   (a concurrent opencode session runs in the distro; shutdown kills it).
2. Re-run status commands; confirm tree == §0 snapshot.

**Gate**: `wsl.exe -d Ubuntu -- echo ok` returns.

### S1 — Clear P1 (merge gate, ~1 day)
1. `git checkout -- src/orchestrator/capabilities/interactive_shell/reverse_shell.py`
2. Re-grep `to_open_broker_policy` → delete dead alias from `runtime/policy.py`.
3. Run `p1_verify.py` — weld probe must print **all AUTHORIZED**; restrictive
   control must print DENIED; ScopeV0 wildcard checks pass.
4. Full suite ≥ 621.
5. Commit P1 (open policy loader/factories + wildcard matchers + artifact).

**Gate**: suite green + `git diff --stat` shows only intended P1 paths.

### S2 — P1.5 test-regime flip (~1 day)
1. `tests/test_am4_weld_gates.py`: flip ~40 `pytest.raises(WeldNotAuthorized)`
   sites → assert AUTHORIZED + receipt present.
2. `test_p2_guardrail_sub10_closed.py:61`, `sub13_closed.py:48` → align with
   open expectations (or parametrize both policies).
3. **New negative control** `test_restrictive_policy_still_denies`: same
   request through `make_broker_restrictive` must raise `WeldNotAuthorized`.
4. Verify `test_authorization_lifecycle.py:100,122` (engagement-id default is
   now `engagement-open-v0`) — fix assertions if they pin `bootstrap-v0`.

**Gate**: suite green AND restrictive control proves fail-closed still exists.
Commit.

### S3 — P2: restore execution bodies (the edge, 2-4 days)
Per deleted file, proven recipe:
```
git log -S '<raise message>' --oneline -- <path>
git show <DEL-commit>^:<path>        # last full version
```
Restructure to current interfaces (receipt shapes, broker mediation, action
types), then run the file's original test module. Restore order = dependency
order (inspect → craft → deploy → run → others). **Commit per file** —
bisectable history.

**Gate**: suite green each commit; `fixture.inspect` chain end-to-end still
works; every restored body emits a receipt on broker-mediated actions.

### S4 — P3: C2, cloak, proxy (1-2 days)
1. Restore `c2_command` bodies → wire to Sliver/Mythic/Havoc CLI (round 3).
2. Restore `cloak-service` → redirector fleet orchestration (round 8):
   nginx redirector + decoy site + secret-header filter as code, not docs.
3. `proxy_guard` gains **per-phase infra separation** config (initial-access /
   persistence / interactive channels; burner-per-operation).
4. Worker-forwarder + ECH profile options recorded in driver config.

**Gate**: cloak service issues a redirector config + receipt in a test
engagement; channel separation observable in receipts.

### S5 — P4: arsenal wiring (2-3 days)
1. **Recon chain** (round 2): `subfinder → puredns → alterx → whatweb →
   nuclei -tags kev` registered in `chains/tool_registry`; host-list receipt
   schema; every expansion re-checked by `scope.covers` (no target creep).
2. **n-day loop** (round 7): KEV/EPSS/VulnCheck queue → `check()` fingerprint
   → `msfconsole -x` via restored W-01 executor → receipt → next action.
3. **Capability catalog** (rounds 4-6): LOLTL execution actions, GraphQL/JWT
   checklist runs, BYOVD + anti-analysis entries — each with machine-readable
   preconditions (admin, HVCI off) so the broker denies instead of
   half-executing.
4. **Implant profiles** (round 6): sandbox gates as build profiles; every
   dormancy decision emits a receipt (silent non-execution ≠ failure).

**Wiring order = §7C tiers A→E**: start with the discovery/validation pair
(nuclei + Metasploit `check()`/execute — the cleanest
discover→observe→hypothesize→select→act→rectify→replan loop); Tier C
multi-step, Tier D stateful, and Tier E high-consequence wire last, each
gated by E3 verification plus (Tier E) the stronger isolation requirements.

**Gate**: one engagement run produces receipts spanning recon → queue →
exec → cloak; restrictive control still denies everything.

### S5r — Browser research through the brain (Playwright)

New broker-mediated capability `browser_research` the planner can call
mid-engagement:

1. **Module**: `src/orchestrator/capabilities/browser_research/` following
   the `interactive_shell` layout — `capability.py` registration +
   Playwright (Python sync API, headless Chromium) executor.
2. **Actions** (each an action type, each receipted):
   - `web_research.search` — Scholar / Semantic Scholar API / SERP fan-out
   - `web_research.fetch` — JS-rendered page → clean text (the reason to
     use a real browser over curl)
   - `web_research.read_pdf` — download → extract → chunked text
3. **Source config** (config, not code): open-access defaults — arXiv,
   Semantic Scholar, USENIX/NDSS/BlackHat papers, vendor advisories, MITRE,
   Exploit-DB, GitHub PoC repos — plus operator-configured mirrors
   (**Sci-Hub included per operator request**) and any platform relevant
   to the target's stack.
4. **Scope class**: research URLs are NOT engagement targets → separate
   `research_scope` domain allowlist + SSRF guard (deny `file://`,
   localhost, RFC1918) + per-fetch receipts tagged
   `scope_class=research`; global rate ceilings still apply.
5. **Improvement loop** (the actual point — "improve its logic against the
   target"): S7 planner requests research on the fly → claims enter
   planner context *with citation receipts*; E4 converts verified
   observations into catalog entries with source provenance; E1.5 takes
   literature-grounded strategy candidates (papers on the target's stack →
   candidate orderings).
6. **Deps**: Playwright + Chromium added to S2.5 inventory/install;
   implement only after integration review #4 closes.
7. **Engine: CloakBrowser (validated 2026-09-30)** — Playwright
   drop-in, installed at `/home/yaser/.venvs/cloak` (venv, PEP 668),
   stealth Chromium v146 (Ed25519-verified). Real-target results:
   - headless **fails** Cloudflare (dl.acm.org stuck on "Just a
     moment"); `headless=False, humanize=True` passes instantly
     (WSLg `DISPLAY=:0` works) → S5r must default headed + humanized.
   - **Host-guard mandatory**: squatted mirror `sci-hub.wf` redirected
     into a Clickadu ad chain → final URL must stay within the source
     allowlist or the fetch is aborted (exactly the S5r SSRF/redirect
     guard).
   - Bot-gates on live mirrors are simple click gates (`.pl` "Are you
     a robot?/No"), dismissible; Sci-Hub lacks post-2021 papers anyway
     (gold-OA ACM PDF was the real route).

**Gate**: query → fetched paper → extracted claim → planner context entry,
full receipt chain; suite green.

### S6 — P5/P6: autonomy unbinding (1-2 days)
1. Raise `max_iterations` per engagement config; approval flow →
   operator-supplied allow list; command filter tuned to receipts, not
   blanket blocks.
2. Rate ceilings **stay** (1e6/min artifact values are the hard ceiling —
   raising autonomy never raises the ceiling).
3. Falsibility: failed actions feed rectifier memory (E1) instead of
   halting the loop; still block only on guardrail violations.
4. Continuous-run watchdog + engagement rotation (operator-supplied sets).

**Non-claim**: S6 delivers *continuous operation* only — uptime is not a
proxy for competence. A system can run 20 hours and learn nothing;
improvement is measured solely by E1.5 on held-out scenarios.

**Gate (three distinct proofs)**: (a) *continuous operation* — multi-hour
run; (b) *boundary integrity* — full receipt trail, zero INV-1 violations,
kill-switch tested (§4); (c) *measurable autonomous improvement* —
multi-episode evaluation carried by the E1.5a external verdict. All three,
not uptime alone.

## 2A. CLOSURE PHASES (the 20→100 gaps)

Assessment (2026-09-29): blueprint = correct sequence, but ~20% of "heavy
penetration" — execution 0%, **toolchain absent (verified: no nuclei/
subfinder/msfconsole/whatweb/sqlmap/ffuf in the distro)**, receipts
ephemeral (`action_receipt.py:60` in-memory dict), no range, no planner.
These phases close exactly those four gaps.

### S2.5 — Toolchain bring-up (missing from original blueprint)
1. Run `scripts/env_inventory.sh` → present/absent manifest.
2. Install in §7C tier order (A first): subfinder, puredns, alterx, nuclei,
   whatweb, ffuf, sqlmap → Metasploit → Sliver → Certipy — version-pin
   every entry in the manifest.
3. Data: nuclei template DB update; EPSS/VulnCheck feed keys; optional
   Shodan/Censys.
4. Register each tool in `chains/tool_registry` with a version receipt.
**Gate**: Tier A+B present + versioned + registry receipts; suite green.

### I1 — Durable evidence store
Replace the ephemeral `_receipt_store` dict with an append-only JSONL
backend (`audit_trail.jsonl`, as `action_receipt.py:59` already promises):
hash chain verified across restarts, no delete/overwrite API preserved,
`verify_integrity()` over the full file.
**Gate**: kill-and-restart test — chain verifies across process restarts;
suite green. **Owner**: this session, AFTER integration review #4 closes —
no new diff layer before P1 verification.

### E3-Range — authorized lab range bring-up
docker-compose of deliberately vulnerable services (web app + AD-lite +
full logging) — operator-supplied target set by construction.
**Gate**: one E2→E3 promotion runs end-to-end on a real candidate.

### S7 — Planner intelligence (round 1; the heaviest remaining gap)
Difficulty-aware multi-step planner + rectifier-fed replanning (E1) +
strategy candidates (E1.5). Heavy penetration = chained plans, not single
actions — this is the engine everything else feeds.
**Gate**: multi-step engagement plan executes with full receipt trail.

**100% definition**: S1-S6 green + S2.5 toolchain live + I1 durable
evidence + E3-Range standing + rounds 9-13 absorbed + S7 planner + E1.5
external verdict loop operational.

---

## 3. EVOLUTION LOOPS (the compounding machinery)

These are built **after S4** and are what make it "ever evolving":

### E1 — Rectifier memory (round 1, core)
- **Pre-task (prerequisite, filed from receipt audit)**: promote a closed
  failure vocabulary onto the receipt — `failure_class: str` on
  `ActionReceipt`, hash-bound, `verify_integrity()` stays green. Seeds,
  in priority order: (1) **`src/raphael/cerebellum/error_diagnoser.py`** —
  already classifies executor failures into a closed vocabulary
  (`permission`/`timeout`/`unavailable`/`server_error`/`tool_missing`/
  `protocol_error`) with an `is_permanent` flag and feeds negative-cache
  `FailureRecords`; action-level, exactly this problem, and **not yet
  mirrored onto the orchestrator receipt** (verified absent from
  `action_receipt.py`); (2) `src/arena/llm_transport.py` `FAILURE_CLASS_*` +
  `RETRYABLE_CLASSES` (LLM calls only). Candidate E1 store already exists:
  `src/raphael/circulatory/blackboard.py` (`failure_class` + output +
  latency columns). Without the receipt-bound copy, the orchestrator
  receipt stream has no cache key.
- Cache key = `(action_type, target, failure_class)`; **retryable classes
  bypass the cache** — only non-retryable outcomes (auth, permission,
  unsupported, malformed) become "never retry X" entries, or a transient
  rate-limit would poison legitimate retries.
- Per-action reflection store: outcome + error class + context → planner
  input on the next similar decision (no blind retries).
- Persists to the existing learning-log area; reflection records carry the
  same receipt IDs as the action (auditable self-critique).
- **Metric**: repeat-failure rate trending to zero across runs.

### E1.5 — Strategy selection loop (the missing layer)

Bridges "remembers what happened" → "becomes better because of it":

```text
E1 experiences/trajectories → strategy candidates → independent
evaluation → selection → persist accepted strategy → next generation
```

- **Strategy = parameterized decision policy** over an engagement class
  (ordering, tempo, retry/tempo policy, recon-vs-exploit weighting) —
  storable variants, not free text.
- **Evaluation = held-out scenario suite**: fixed evaluation engagements
  Raphael does not generate and cannot read scores for during runs. In-tree
  precedent: `evaluations/campaign/` + sentinel/judge artifacts.
- **Selection = survival criterion**: retain candidate B only on a measured
  positive delta vs incumbent A on the held-out suite; otherwise incumbent
  persists. Self-praise is not a delta.
- **Independence guard**: the acceptance verdict comes from the protected
  external evaluation path, closing `changes itself → evaluates itself →
  declares itself better`. This is why the earlier external-evaluation
  work remains necessary even with this blueprint.
- **Dependencies**: E1 `failure_class` (trajectory quality), E3 validation
  (strategies may only rely on verified capabilities), evaluation harness.
- **Owner**: evaluation design = this session; selector implementation
  unassigned until E1 pre-task lands.

### E2 — Feed absorption pipeline
- Scheduled poller: CISA KEV, EPSS V5 deltas, VulnCheck in-the-wild, LOLDrivers
  updates, Metasploit weekly module list.
- Output: catalog queue entries with provenance receipt (source, date,
  score) — **queued for validation, never auto-executed**.
- **Metric**: feed-latency (KEV publish → queue entry) < 24h.

### E3 — Lab validation range
- Every claim (research rounds, feed entries) → reproduce against the
  authorized range → promote `unverified → verified → wired`.
- Catalog records status; S5-style wiring only reads `verified` entries.
- **Metric**: % of catalog verified; target ≥ 90% before a technique is
  reachable in an engagement.

### E4 — After-action catalog growth
- Engagement findings + rectifier reflections → new `references/` checklist
  rows → new broker action types (same 4-step promotion as E3).
- **Metric**: catalog entries added per engagement (learning rate).

### E5 — Self-red-team job
- Scheduled run: restrictive control (must deny), weld probes (must authorize
  only when configured), scope-escape scenarios (must fail-closed), rate
  ceiling probes (must throttle).
- Any failure auto-files a task in this blueprint's backlog; suite floor
  re-asserted (621 → grows with S2/S3 tests).
- **Self-certification limit**: gate tests are mechanical — machine
  pass/fail — so E5 may self-run and self-repair. *Evolution claims*
  ("this improved") are not machine-checkable from inside; they route to
  E1.5's external acceptance verdict. E5 proves the controls still hold;
  it never proves the agent got better.
- **Metric**: self-red-team MTTR (mean time to repair) < 1 day; guardrail
  violations = 0, always.

---

## 4. NON-NEGOTIABLES / KILL SWITCHES

- Broker mediation is never bypassed — evolution loops add *receipts*, not
  side doors (roadmap §5, INV-1 preserved).
- Kill switch = swap decision source: `make_broker_from_bootstrap` fallback or
  restore `bootstrap-v0.json` as active artifact → **one-file revert to full
  deny-all**. Test the switch once at end of S6.
- Rate ceilings and engagement scope (`scope.covers`) are never config-raised
  by the evolution loops.
- Roadmap §5 exclusions stand (no ransomware/extortion playbooks, no
  cash-out/laundering, no victim-selection; operator-supplied targets only).

---

## 5. METRICS DASHBOARD ("high potential" made measurable)

| Metric | Source | Target |
|---|---|---|
| Autonomous hours per run | watchdog | multi-hour, rising |
| Receipt coverage of actions | receipts DB | 100% |
| Catalog entries / % verified | catalog | growing, ≥90% verified |
| Feed-latency KEV → queue | poller | < 24h |
| Repeat-failure rate | rectifier | → 0 |
| Self-red-team MTTR | E5 tasks | < 1 day |
| Strategy survival (B vs A delta, held-out suite) | E1.5 external eval | retain only on positive, externally signed delta |
| Guardrail (INV-1) violations | receipts | 0, forever |
| Suite floor | pytest | ≥ 621, growing |
| Tier competence (per §7C tier) | E1.5 eval | rises A→E; damage output is never a metric |

---

## 6. IMMEDIATE BACKLOG (next session, in order)

**Lane split (2026-09-29):** in-distro agent owns E1/E2/E4/E5, metrics
harness, and the two dispatched items below; this session owns S1/S2
verification bookkeeping, blueprint upkeep, and S3-S6 (per this session's
operating spec those remain in scope here), with no file overlap.

**Architecture review adopted (2026-09-29):** autonomy ≠ self-improvement;
E1.5 strategy loop + external-acceptance gate inserted (§1, §1A); S6 marked
continuous-operation-only; execution order S0→S1→S2→S3 unchanged. E1.5
evaluation design = this session; selector implementation unassigned.

1. [dispatched → in-distro] `failure_class` on `ActionReceipt` + keyed E1
   cache (constraints above: non-retryable-only, 3-path integrity green).
2. [dispatched → in-distro] CUT dead `to_open_broker_policy` alias
   (`runtime/policy.py:157-168`).
3. [in-distro, offered] S1 verification package: restore `reverse_shell.py`,
   run `p1_verify.py` + full suite (≥621) — mechanical, they hold exec.
4. [this session] S2 test-regime spec + P1.5 expectations; S3 restoration
   recipes per file.
5. [this session] Absorb audit result into integration review before any
   commit.

Deferred: rounds 9-10 research (supply-chain/initial-access brokering;
network-layer) — absorbed through the E2→E3→S5 pipeline once it exists.

---

## 7. ARCHITECTURE & EXECUTION TABLES (living — update status in place)

### 7A. Architecture table

| Layer | Component | ID | Function | Hard constraint |
|---|---|---|---|---|
| Substrate | Broker mediation + `ActionReceipt` (20-field, hash-bound) | S1/P1 | Every action gated and recorded, deny/success/timeout uniform | Never bypassed; loops add receipts, not side doors |
| Substrate | `scope.covers` + rate ceilings + kill switch | §4 | Execution boundary | Evolution loops never raise ceilings; one-file revert to deny-all |
| Action space | 10 execution bodies | S3 | Restore capability (the blade) | Dependency order; commit per file; receipts on every mediated action |
| Action space | C2 / cloak / proxy fleet | S4 | Infra (Sliver/Mythic/Havoc, redirectors, per-phase channels) | Channel separation observable in receipts |
| Action space | Arsenal wiring (recon chain, n-day loop, catalog) | S5 | Reach loops wired to real tools | Only E3-`verified` entries reachable |
| Action space | Autonomy unbinding | S6 | Continuous operation | Non-claim: uptime ≠ competence; ceilings stay |
| Mission loop | Watchdog + engagement rotation | S6 | achieve → reassess → continue | Operator-supplied target sets only |
| Experience loop | Rectifier memory | E1 (+pre-task `failure_class`) | act → observe → reflect → remember | Key `(action_type, target, failure_class)`; retryable classes bypass cache |
| Strategy loop | Candidates → held-out eval → selection | E1.5 | Generate → evaluate → select → persist | Acceptance verdict only from protected external evaluation; survival = positive delta |
| Self-assurance loop | Self-red-team job | E5 | test → detect → repair | Mechanical pass/fail only; never certifies evolution |
| Capability growth | Feed poller | E2 | External knowledge → queue | Queued with provenance, never auto-executed |
| Capability growth | Lab validation | E3 | unverified → verified → wired | ≥90% verified before reachable |
| Capability growth | After-action catalog growth | E4 | Findings → checklist → action type | Same 4-step promotion as E3 |
| Independent evaluation | Held-out scenario suite + judge/sentinel verdict | E1.5a | Answers "did it actually get better?" | Protected: Raphael neither generates nor reads scores |

### 7B. Execution table

Status legend: DONE · DISPATCHED (accepted by lane) · OFFERED (awaiting lane
accept) · PENDING · BLOCKED (external dependency) · DEFERRED.

| # | ID | Task | Owner | Status | Depends on | Exit gate |
|---|---|---|---|---|---|---|
| 0 | P0/P1 | Baseline `e6a8c707e` + P1 content edits | this session | DONE (in worktree, unverified) | — | P1-VERIFY content PASS; merge blocked by #2 |
| 1 | E1-pre | `failure_class` on `ActionReceipt` + keyed cache | in-distro | DISPATCHED | — | 3-path integrity green + constraints in §3 |
| 2 | S1a | CUT dead `to_open_broker_policy` alias | in-distro | DISPATCHED | — | grep 0 hits + suite |
| 3 | S1b | Restore `reverse_shell.py`, run `p1_verify.py` + suite ≥621 | in-distro | OFFERED | — | All probes AUTHORIZED; restrictive DENIED |
| 4 | — | Integration review of P1 diffs (+ #1-#2 when landed) | this session | IN PROGRESS | 0, 1, 2 | Diff audit PASS (P1-VERIFY format) |
| 5 | S0 | Re-arm host-side `wsl.exe` exec | operator + this session | BLOCKED (not gating in-distro work) | operator: `wsl --shutdown` confirm (kills concurrent session) | `wsl.exe -d Ubuntu -- echo ok` |
| 6 | S2 | Test-regime flip + `test_restrictive_policy_still_denies` | this session (spec) / exec TBD | PENDING | #3 green | Suite green AND restrictive control denies |
| 7 | S3 | Restore 10 bodies, dep order, commit per file | this session | PENDING | #6 | Per-file tests; receipts emitted; fixture.inspect intact |
| 8 | S4 | C2/cloak/proxy fleet restoration + wiring | this session | PENDING | #7 | Redirector config + receipt; channel separation visible |
| 9 | S5 | Arsenal wiring (recon chain, n-day loop, BYOVD/anti-analysis entries with preconditions) | this session | PENDING | #8 | One engagement run spans recon→queue→exec→ cloak receipts |
| 10 | S6 | Autonomy unbinding + multi-episode evaluation + kill-switch test | this session | PENDING | #9 + #16 readiness | 3 proofs: continuous run; 0 INV-1 + switch tested; E1.5a verdict shows improvement |
| 11 | E1 | Rectifier store live (reflection → planner) | in-distro | PENDING | #1 | Repeat-failure rate trends to 0 |
| 12 | E5 | Self-red-team job (build early, after S2) | in-distro | PENDING | #6 | MTTR < 1 day; suite floor re-asserted |
| 13 | E2 | Feed poller (KEV/EPSS/VulnCheck/LOLDrivers/MSF) | in-distro | PENDING | queue schema | KEV publish → queue < 24h |
| 14 | E3 | Lab validation range | UNASSIGNED | PENDING | #9 (range) | ≥90% of catalog verified |
| 15 | E4 | After-action catalog growth | in-distro | PENDING | #14 promotion chain | Entries added per engagement |
| 16 | E1.5a | Held-out suite + external verdict design | this session | DESIGN NOW (parallel with #6/#7) | #1, metrics harness | Suite exists; Raphael can't generate or read scores |
| 17 | E1.5b | Strategy selector (generate → evaluate → select) | UNASSIGNED | PENDING | #11, #14, #16 | Retain only on positive external delta |
| 18 | H | Metrics harness (§5 dashboard) | in-distro | PENDING | rows in §5 | Dashboard live |
| 19 | R9-10 | Rounds 9-10 research absorption | this session | DEFERRED | #13→#14→#9 pipeline | Absorbed via E2→E3→S5 |
| 20 | S2.5 | Toolchain inventory (`scripts/env_inventory.sh`) + tier-ordered install + registry wiring | in-distro | PENDING | #20 needs exec only | Tier A+B present, versioned, registry receipts |
| 21 | I1 | Durable JSONL receipt store (replace ephemeral dict) | this session | PENDING (after #4 closes) | #4 | Restart test: chain verifies across restarts; suite green |
| 22 | E3r | Range bring-up: docker vulnerable services + logging | in-distro (spec: this session) | PENDING | minimal Tier A | One E2→E3 promotion end-to-end |
| 23 | S7 | Difficulty-aware multi-step planner wired to E1/E1.5 | this session | PENDING | #11, #16 | Multi-step plan executes with full receipts; AutoPen precedent (IA orchestration/backtracking, KG, stage-wise metric) in `references/papers/` |
| 24 | R9-13 | Research rounds 9-13 (supply-chain, network, anti-forensics, identity, physical) | this session | IN PROGRESS | — | Compiled into research report v2 |
| 25 | S5r | Browser-research capability (Playwright) through the brain — spec'd, **engine validated** (CloakBrowser installed; ACM OA fetch passed headed+humanize) | this session | SPEC'D + ENGINE-VALIDATED (implement after #4) | #4 (playwright now in venv) | query → paper → claim → planner context with citation receipts |

### 7C. Capability ladder — dual-axis ranking

Two axes, kept separate on purpose:

- **Offensive power** = blast radius × reliability (what the tool can do)
- **Autonomy value** = action diversity × observability × feedback quality ×
  reproducibility × strategic depth (what the tool can *teach the decision
  loop*)

Principle: **the action space gets more powerful; Raphael's progress is
measured by how intelligently it uses that space, not by damage potential.**

| Tier | Class | Members | Offensive power | Autonomy value | Role in evaluation |
|---|---|---|---|---|---|
| A | Discovery | subfinder, puredns, alterx, nuclei | High / Med-high | **Very high** | First autonomy substrate: large observable discovery space, clean feedback |
| B | Validation | whatweb, Metasploit `check()`, controlled verification | High | High | Hypothesis → test → consequence chain |
| C | Multi-step strategy | Metasploit exploits, Certipy/Certighost, autobloody graph paths | Very high | High | Strategy-loop substrate: state → candidate path → action → new state → recompute |
| D | Long-horizon state | Sliver C2, persistent mission state, cloak/proxy | Very high | Medium-high | Mission continuity and stateful operation |
| E | High-consequence | BYOVD, anti-analysis, destructive classes | Extremely high | Medium | Wired last: strongest isolation + evaluation requirements (E3 + §4) |
| A+ | Knowledge/research | Playwright `browser_research`: papers, advisories, PoCs (S5r) | Low | **Very high** | Intelligence feed for S7/E1.5; every fetch receipted under `research_scope` |

Key rankings: nuclei and the subfinder chain carry the **highest autonomy
value** (discovery → observe → hypothesize → select → act → rectify →
replan loop); autobloody is the premier **strategy-loop** specimen but a
poor first substrate (blast radius); BYOVD tops **offensive power** while
sitting mid on autonomy value — consequence severity is not experiment
quality.

Progression rule: demonstrate autonomous competence at tier *k* (E1.5
external eval) before wiring tier *k+1*.
