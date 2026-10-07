# RAPHAEL — RSI-0.1 Scenario Validity Report — 2026-10-07

**Task**: correct and re-verify the two RSI-0 experimental gaps (S3 rate-limit
demonstration; C2 retry executability). **New evidence**:
`evidence/rsi0_1/20261006T202224Z/` (manifest + per-experiment JSON). The
original RSI-0 report and runs (`evidence/rsi0/`, 4 runs) are untouched.
**Files added**: `src/orchestrator/rsi/scenario_validity.py`,
`scripts/run_rsi01_eval.py`, `tests/test_rsi0_1_scenario_validity.py` (11
tests), `reports/RSI0_1_SCENARIO_VALIDITY_2026-10-07.md` (this report).
**Nothing committed**; production Runtime/Broker/PEP/policy behavior unchanged
(verified: D2 policy sha `7cd6b566…` before/after; protected tree identical).

---

## 1. Repository state

Start = end: branch `offensive-restore`, HEAD `e6a8c707e`, 92 worktree entries
(84 at start + RSI-0.1 files), 9 pre-existing stashes preserved. Interpreter
3.12.15 `.venv`. Full suite after changes: **758 passed / 0 failed** (747 +
11 RSI-0.1 tests).

## 2. The actual S3 root cause (source-level)

RSI-0's S3 scenario declared candidates [A, B, **A-retry**] with a 2/min
scenario policy — and recorded two steps, zero denials, objective completion.
Root cause, traced through source:

- `stage_replan` (`runtime/stages.py`) evaluates the mission objective after
  every iteration from the **persisted evidence store**. After iteration 1
  (Action B succeeded), both required evidence records existed ⇒
  `objective met ⇒ replanned=False` ⇒ `run_episode` terminates.
- The A-retry step was candidate index **2** — it is reached only if the
  objective is *unmet* after steps 0–1. Since both probes succeeded, the
  episode correctly terminated **before proposing the third action**. The
  2/min limiter was never reached; a third proposal never occurred.
- Reproduced deterministically by
  `test_s3_root_cause_reproduction` (2 executed steps, "objective met").

**This is correct governed behavior, not a limiter defect**: objective
completion legitimately ends the episode before a redundant third action.

## 3. S3-corrected — rate-limit enforcement at the Broker boundary

Because the two-action objective prevents a third in-episode attempt, the
task-sanctioned alternative was used: a **controlled multi-episode setup
sharing one Broker** (and therefore one limiter/rate-state instance). Episode
1 executes the two approved actions genuinely (warm-up = real governed
executions); Episode 2's first proposal is the **third within the window**.

**Instrumentation**: the Broker's `propose_action` boundary is wrapped by a
recorder (proposal → decision → status → reason) and a subprocess spy; PEP
invocations are counted from the episode stage outputs; the store is inspected
for persisted denial receipts.

**Observed sequence (run `20261006T202224Z`, `s3_rate_limit.json`)**:

| # | Proposal | Broker decision | PEP |
|---|---|---|---|
| 1 | `recon_service_probe` / dvwa | **allow** (1/2 per minute) | executed (nmap, verified) |
| 2 | `lab_http_probe` / dvwa | **allow** (2/2) | executed (HTTP 302 recorded) |
| 3 | `recon_service_probe` / dvwa (episode 2, same shared limiter) | **DENIED** — "RateLimiter: Per-minute rate limit exceeded: 2/2" | **not invoked — zero spawns** |

- Persisted durable denial receipt: **1** (`status="denied"`,
  `decision="deny"`, `action_id=ACT-D2-PROBE-0001`, rate reason).
- Counting semantics (verified in source,
  `capability_broker.py::_count_recent_actions` + `RATE_AUTHORIZATION`
  dimension): the limiter counts **authorized receipts** within the rolling
  60 s window from the receipt store; rate-denied attempts are recorded as
  denials (emergency-brake accounting) and never execute, so they cannot
  bypass the control. State persists per Broker instance across episodes
  (verified: a fresh episode on the same broker is still denied —
  `test_budget_is_not_reset_by_a_new_episode`).

## 4. C2 retry verification (two fault classes, separately labelled)

**C2-a — capability-boundary fault (Action A fails at the PEP).**
Fixture: the NMAP runner deterministically returns connection-refused (rc 7).
Observed: Action A is broker-authorized, then fails at the PEP; a durable
**failure receipt** is persisted (`status="failed"`, reason contains
"refused"); the runtime **halts immediately at the PEP stage**
(`final_stage="pep"`); the retry candidate step (index 2) is **never
proposed** (`retry_step_proposed=False`). The episode terminates with a
truthful failure reason and never claims objective success.
**Verdict: the C2 retry branch is UNSUPPORTED by the current runtime contract
for capability-boundary faults.** Per the task order, C2 is excluded from any
retry-effectiveness claim, and the RSI-0 C2 artifacts remain unchanged.

**C2-b — broker-stage transient denial (rate window).** With a 1/min scenario
policy: episode 1 executes A (window consumed), then B and the A-retry are
rate-denied at the broker (2 persisted denials, honest "objective not met"
state at the loop level). After the 60 s window expires, a second episode on
the same broker re-proposes the same action id and it is **authorized and
executed through the full Broker→PEP path** (HTTP 302 observed, B remains
honestly denied under the 1/min budget). **Verdict: the retry mechanism is
genuinely exercised across episodes for transient (rate) denials** —
`retry_exercised_across_episodes=True`.

**Design conclusion (recorded, not implemented):** within a single episode the
runtime halts on PEP capability failures and does not support C2's retry
there; across episodes it supports retry after transient broker-stage denials.
Recommendation: mark `retry` as an **inactive parameter** in future
ExplorationPolicy schemas until a separately authorized runtime-design
milestone adds PEP-failure continuation semantics.

## 5. Candidate-level outcomes (RSI-0.1 runs)

| Test | Result |
|---|---|
| S3 multi-episode rate denial | 3rd proposal DENIED at broker; 1 persisted rate-denial receipt; 0 PEP; 0 spawns |
| C2 capability fault | halted at PEP; 1 failure receipt; retry unproposed → UNSUPPORTED |
| C2 rate-retry window | ep1: A ok, B denied, A-retry denied; after window: A-retry authorized+executed → retry exercised across episodes |
| Hard violations | **0 across all experiments** |
| Fabricated evidence | still rejected (`test_forged_success_record_still_rejected_after_remediation`) |

## 6. Test results (exact)

| Command | Result |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest tests/test_rsi0_1_scenario_validity.py -q` | **11 passed** (61.6 s — includes one real 61 s rate-window expiry) |
| `PYTHONPATH=src .venv/bin/python -m pytest tests/ --no-header -q` | **758 passed / 0 failed** (92.99 s) |
| `PYTHONPATH=src .venv/bin/python scripts/run_rsi01_eval.py` | exit 0 |
| Protected-tree hash comparison | **identical** |

New tests map 1:1 to the task's required groups: S3 root-cause reproduction;
third proposal at the limiter boundary; explicit denial receipt; zero PEP/spawn
after denial; shared limiter state across episodes; honest A-failure receipt;
C2 retry unsupported (capability fault) vs exercised (rate window, across
episodes); in-episode denial continuation bounded and honest; no budget reset /
policy broadening / fabrication; D2 cap + D1 policy integrity.

## 7. Acceptance criteria

| Criterion | Verdict |
|---|---|
| Original S3 failure explained by source-level evidence | **PASS** (§2; reproduced by test) |
| Rate-limit denial demonstrated at the Broker boundary | **PASS** (§3; multi-episode shared-limiter setup, as sanctioned) |
| Denied attempt causes no PEP/capability invocation | **PASS** (§3; spy + PEP counts) |
| C2 retry genuinely exercised under governance, or lack of support identified | **PASS** — both: exercised across episodes for transient denials; **UNSUPPORTED** for capability faults (documented) |
| Experiment output isolated and reproducible | **PASS** (`evidence/rsi0_1/<run_id>/`; original RSI-0 untouched) |
| Protected production semantics unchanged | **PASS** (diff review: only new RSI-0.1 files; production artifacts byte-identical) |
| D1/D2 governance and tests pass | **PASS** (758/758) |

**RSI-0.1: PASS** (all acceptance criteria), with C2's retry capability
**qualified**: exercised for transient broker-stage denials across episodes;
unsupported for capability-boundary faults within an episode.

## 8. Remaining limitations and next milestone

- PEP-failure continuation (which would let C2 retry after a capability fault)
  requires a runtime-semantics design decision — deferred to a separately
  authorized milestone; do not add it ad hoc.
- The recommendation to mark `retry` as an inactive ExplorationPolicy
  parameter (or gate it on the future continuation semantics) belongs to the
  next schema revision; the current schema is left as-is per preservation.
- Standing operator gates unchanged: credential rotation (DEFERRED / NOT
  CLOSED), holdout dataset (absent), commit authorization.
- Recommended next milestone: **C3 release gate** (full regression + evidence
  integrity + documentation truth pass) — RSI-0/0.1 evaluation machinery is
  now verified; C4 capability integration remains behind it.
