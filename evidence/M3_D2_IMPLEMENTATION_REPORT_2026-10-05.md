# M3/D2 BOUNDED EXECUTION — IMPLEMENTATION REPORT — 2026-10-05

**Task**: D2 Bounded Execution Implementation (operator-approved two-action scope).
Branch `offensive-restore`, HEAD `e6a8c707e` (unchanged). **Nothing committed.**
Deterministic only: zero LLM/provider calls; the 660-test baseline grew to 685 with
the new D2 tests; protected historical evidence byte-identical throughout.

---

## 1. Starting state and worktree constraints

Branch/HEAD as above; 70 preserved worktree entries at start (M0→M2.1 + reports);
9 pre-existing stashes untouched. Lab healthy loopback-only (smoke PASS).

## 2. Files added

| File | Purpose |
|---|---|
| `policies/engagement-d2-v1.json` | Operator-approved two-action bounded policy: {`recon_service_probe`} ∪ {`lab_http_probe`} × {`exec.d1_lab_probe`} ∪ {`exec.http_probe`} × {`dvwa`}; fixed HTTP contract (GET, `http://dvwa/`, `max_redirects 0`, 60 s, 64 KiB, in-container); rate limits 6/min, 60/hr, 1 concurrent; impact caps; fail-closed flags; kill switch = bootstrap-v0 swap |
| `src/orchestrator/exec/capabilities/http_probe.py` | Action-B capability: fixed argv `docker exec kali-tools curl --max-redirs 0 --max-time 60 --max-filesize 65536 -s -S -o - -w <metadata> http://dvwa/`; live identity verification (running + image prefix + shared network); CONV-3 gating; no `-L` (redirects recorded via `%{redirect_url}`, never followed); `--max-filesize` bounds collection (exit 63 → honest bounded-abort failure); body artifact with sha256; transport failures raise (truthful FAILED) |
| `scripts/run_demo_d2.py`, `scripts/run_demo_d2.sh` | D2 launcher: smoke + identity checks, positive two-step episode, kill-switch control, wrong-target control, subprocess-spy proofs, timestamped evidence |
| `tests/test_m3_d2_bounded_execution.py` | 25 tests covering all 16 required groups |
| `evidence/M3_D2_IMPLEMENTATION_REPORT_2026-10-05.md` | this report |

## 3. Files modified (all minimal, backward-compatible)

| File | Change |
|---|---|
| `src/orchestrator/runtime/policy.py` | `D2_POLICY_PATH`; strict optional HTTP-contract validation (GET-only, 0 redirects, bounded time/size, in-container context declared — malformed ⇒ `PolicyLoadError`); `make_broker_from_policy` now **binds the existing `RateLimiter`** to the returned broker (deterministic: jitter 0/0; the per-minute cap and denial accounting stay active) |
| `src/orchestrator/runtime/stages.py` | `_persist_denial_record` — durable denial receipts at the broker stage (authorization, scope/target, and rate-limit denials); `_persist_failure_record` — durable failure receipts after a started execution fails; PEP **capability registry** routing (same PEP stage; registry miss = exact legacy behavior); `stage_replan` **evidence-based objective evaluation** (objective contract lists required action_ids; met ⇔ persisted `execution_result` records with `decision=allow`, `status ok/succeeded` exist) |
| `src/orchestrator/runtime/loop.py` | `capability_registry` constructor param threaded to the PEP stage; objective contract threaded into the view; **replan continuation** (replan-stage `replanned=True` + remaining budget ⇒ next iteration) mirroring the existing broker-denial continuation; honest terminal reason from the evaluated objective |
| `src/orchestrator/brain/capability_broker.py` | **Bug fix (enforcement order)**: the rate check ran *after* `authorize()`, and `deny()` refuses an AUTHORIZED receipt (invalid transition) — a rate-denied attempt returned `None`. The limiter now runs **before** authorization, so a rate-denied attempt produces a proper DENIED receipt while still PROPOSED |
| `src/orchestrator/exec/evidence_store.py` | additive `records()` read API (objective evaluation + verification) |

Untouched: `exec/capabilities/d1_lab_probe.py` (reused unmodified per scope), all
weld gates, all deleted bodies, `bootstrap-v0.json`, `engagement-d1-v1.json`,
`engagement-open-v0.json` (still unwired), protected evidence trees.

## 4. Already present vs implemented/repaired

Already present: single Runtime/loop, Broker PDP, PEP boundary, ScopeV0
conjunction, receipt lifecycle, evidence store, deterministic candidate
episodes, D1 capability, policy loader, kill switch (decision-source swap).
Implemented: D2 policy, HTTP capability, PEP registry routing, rate-limiter
wiring, denial/failure persistence, objective evaluation + replan
continuation, D2 demo + tests. Repaired: the rate-deny ordering bug above.

## 5. Final D2 execution and policy flow

```text
mission (objective: {A_ID, B_ID}; candidates per step; ScopeV0 d2 scope)
 → stage_broker: CapabilityBroker.propose_action
     dimensions (exact) + rate limiter (BOUND, pre-authorization)
     ALLOW  → receipt AUTHORIZED → scope.covers() conjunction
     DENY   → DENIED receipt → PERSISTED denial record → halt/continue per budget
 → stage_pep: AUTHORIZED→STARTED→ registry[capability].inspect → SUCCEEDED/FAILED
 → stage_receipt: EvidenceReceipt (event, decision, broker receipt, scope hash, artifacts)
 → evidence store: ExecutionResult (+ Artifact via driver, digest-verified)
 → stage_replan: objective met ⇔ required evidence in store → terminate or continue
```

## 6. Test results (exact)

| Command | Result |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest tests/test_m3_d2_bounded_execution.py -q` | **25 passed** |
| `PYTHONPATH=src .venv/bin/python -m pytest tests/ --no-header -q` | **685 collected — 685 passed / 0 failed / 0 skipped — 25.34 s** (660 baseline + 25 D2) |
| Interpreter | Python 3.12.15 (repository `.venv`) |

## 7. Demo runs (both independently timestamped, both exit 0)

- `evidence/demo/d2/20261005T063806Z/` — positive 2-step episode
  (A: decision `d720ad0ad2acc433`, SUCCEEDED, nmap `80/tcp open`;
   B: decision `34579c4ca166dc38`, SUCCEEDED, HTTP 302, redirect_url
   `http://dvwa/login.php`, redirect_followed=False; artifacts digest-verified;
   termination "objective met: required evidence present for
   ACT-D2-PROBE-0001, ACT-D2-HTTP-0002"); kill-switch: 2 steps denied,
   0 spawns; wrong-target: denied at broker, 0 spawns.
- `evidence/demo/d2/20261005T063845Z/` — independent second run, same verdicts.
- Store contents (final run): 5 execution_result records — 2 `ok/allow`
  (A, B) + 3 `denied/deny` (2 kill-switch steps, 1 wrong-target), each with
  reasons. Earlier failing debug runs (`063455Z`–`063649Z`) are retained as the
  audit trail of three driver/candidate bugs found and fixed by their own
  negative assertions.

## 8. Negative-test proof summary

- Kill switch: bootstrap-v0 swap → every step denied at the broker stage;
  subprocess-spy delta 0; capability invocation counters 0; denial records persisted.
- Wrong target: `example.invalid` → denied at the broker (target dimension);
  0 spawns. (First control run accidentally probed dvwa — the control's own
  zero-spawn assertion caught the driver bug; fixed, re-run clean.)
- Rate limit: 7 authorized-shape attempts within a minute → 7th DENIED at the
  enforcement boundary (inside `propose_action`, pre-authorization) with a
  persisted denial receipt and zero spawns.
- Malformed/broadened policies: missing file, malformed JSON, POST/https/
  nonzero-redirects/bad-path HTTP contracts, relaxed fail-closed flags ⇒
  `PolicyLoadError` (no broker produced).

## 9. Rate-limiter counting semantics (documented per task order)

The limiter counts **authorized proposals** — actions that passed every other
authorization dimension (`_record_action` on allow). Rate-denied proposals are
recorded as **denials** (emergency-brake accounting) and never execute, so they
cannot bypass the control. Dimension-denied attempts never reach the limiter at
all (they are denied before it). Jitter is deliberately disabled in the bounded-
lab factory for deterministic episodes; the caps and denial accounting remain
active. Concurrency 1 is enforced by the policy dimension plus the inherently
sequential single-loop Runtime.

## 10. Definition of Done verdicts

| # | Item | Verdict |
|---|---|---|
| 1 | Policy strictly represents the two-action scope | **PASS** (exact-match; broadened/malformed artifacts fail closed) |
| 2 | Both actions through the existing Broker and PEP | **PASS** (live demo, 2 steps, linked decisions) |
| 3 | HTTP originates in kali; redirects never followed | **PASS** (fixed argv, no `-L`, `--max-redirs 0`, recorded `redirect_followed=False`) |
| 4 | All limits enforced at runtime | **PASS** (limiter bound; 7th attempt denied; timeout/cap enforced during collection; concurrency structural) |
| 5 | Durable receipt for every attempt incl. denials | **PASS** (store: 2 succeeded + 3 denied in the final run) |
| 6 | Bounded, persisted, provenance-linked evidence | **PASS** (artifacts + sha256 + decision/event linkage) |
| 7 | Evidence-grounded replanning, admissible actions only | **PASS** (objective evaluated from store records; candidates predeclared) |
| 8 | Truthful evidence-based termination | **PASS** ("objective met…" / "objective not met…"; never success without evidence) |
| 9 | Reproducible demo, negatives prove non-execution | **PASS** (two exit-0 runs; spy-proven denials) |
| 10 | D1 behavior + governance regressions intact | **PASS** (D1 demo re-run PASS; suite 685/685; weld/guardrail tests unmodified) |
| 11 | Recorded results for all checks | **PASS** (this report) |
| 12 | No unrelated changes discarded or committed | **PASS** (nothing committed; pre-existing work preserved) |

**D2: PASS (all 12 DoD items demonstrated).**

## 11. Remaining limitations / deferred

- Action B's evidence for `GET http://dvwa/` is a 302 with a **zero-byte body**
  (the truthful response) — metadata + digest constitute the artifact; body
  content evidence would require a different endpoint (out of approved scope).
- The D2 policy is step-bounded at 5 by the episode driver (`max_iterations`);
  a mis-declared candidate tail falls back to the legacy safe-proving proposal,
  which the D2 broker denies (observed honestly in failure-path tests).
- DR-001 and the 18 structural import failures remain deferred (defect register).
- Credential rotation remains **operator-blocked**; the M0 security gate is NOT
  closed (D2 required no provider and no credentials).
- Holdout dataset remains `unverifiable-in-repo`.
- Nothing committed; the entire M0→D2 worktree awaits commit authorization.
