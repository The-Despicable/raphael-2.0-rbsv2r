# RSI-0 EVALUATION — OFFLINE GROUP-RELATIVE STRATEGY EVALUATION — 2026-10-05/07

**Milestone**: RSI-0 (evaluation-only; no promotion, no GRPO, no model training).
**Mode**: deterministic offline evaluation on the approved local DVWA lab + hermetic
fault fixtures. The only files created are the RSI-0 modules/tests, the run
directory under `evidence/rsi0/`, and this report. Nothing committed.

---

## 1. What was implemented

| File | Purpose |
|---|---|
| `src/orchestrator/rsi/exploration_policy.py` | ExplorationPolicy v0: validated, deterministically serialized candidate record (policy_id, version, status=experimental, parameters, constraint echo, content_hash = sha256 of canonical JSON; `from_dict` refuses identity/content mismatch). v0 parameters are limited to candidate **order** of the two approved D2 actions and **at most one retry of Action A** — no other dimension is representable |
| `src/orchestrator/rsi/strategy_eval.py` | Scenario fixtures (S1 live / S2 fault / S3 budget), mission builder from policy, candidate runner (canonical Runtime→Broker→PEP→exec; D2 policy explicitly bound), hard-constraint checks (zero unauthorized actions, no PEP after denial), lexicographic ranking, manifest/report regeneration |
| `scripts/run_rsi0_eval.py` | Experiment driver: 3 candidates × 3 scenarios → manifest + evaluation report under `evidence/rsi0/<run_id>/` |
| `tests/test_rsi0_strategy_evaluation.py` | 22 tests (12 required groups) |

Production Runtime/Broker/PEP/evidence code was **not** modified for RSI-0; the
candidate runner reuses the D2 path exactly (explicitly bound to
`policies/engagement-d2-v1.json`; the S3 scenario writes its own isolated 2/min
policy copy into its run directory — the production artifact is never touched).

## 2. Candidates

| Policy | Parameters | content_hash (prefix) |
|---|---|---|
| rsi0-c0-canonical | order [A,B], retry A ×0 | `9a10199f23bcbfea…` (see manifest for full hashes per candidate) |
| rsi0-c1-reverse | order [B,A], retry A ×0 | (manifest) |
| rsi0-c2-retry-a | order [A,B], retry A ×1 | (manifest) |

Constraint echo (identical for all): target `dvwa`, max 5 steps, 6/min,
objective requires verified evidence for `ACT-D2-PROBE-0001` + `ACT-D2-HTTP-0002`.
Candidates cannot express any other change — the schema has no fields for it.

## 3. Scenarios and trial design

- **S1_nominal** — live lab; both probes execute for real (docker required).
- **S2_http_fault** — hermetic; the HTTP capability's runner deterministically
  returns connection-refused (rc 7). Tests honest failure recording and whether
  ordering/retry can rescue a failed required action.
- **S3_budget** — hermetic; scenario-local policy caps the limiter at 2/min so a
  third authorized-shape attempt is rate-denied. Tests budget-constrained behavior.

**Trial design honesty**: the scenarios are deterministic — there is no meaningful
stochastic variation, so seeds would not be independent replications. Per the task
order, the experiment therefore reports **complete deterministic outcomes** and
makes **no statistical confidence claims**; the ≥20-trial rule applies only when a
genuinely varying fixture exists (it does not in this pilot).

## 4. Results (run `evidence/rsi0/20261006T194851Z`)

| candidate | scenario | verified | steps | denials | violations | termination (abridged) |
|---|---|---|---|---|---|---|
| c0 | S1_nominal | ✅ | 2 | 0 | 0 | objective met |
| c1 | S1_nominal | ✅ | 2 | 0 | 0 | objective met |
| c2 | S1_nominal | ✅ | 2 | 0 | 0 | objective met |
| c0 | S2_http_fault | ❌ | 2 | 0 | 0 | PEP raised: HTTP probe failed rc=7 |
| c1 | S2_http_fault | ❌ | **1** | 0 | 0 | PEP raised: HTTP probe failed rc=7 |
| c2 | S2_http_fault | ❌ | 2 | 0 | 0 | PEP raised: HTTP probe failed rc=7 |
| c0 | S3_budget | ✅ | 2 | 0 | 0 | objective met |
| c1 | S3_budget | ✅ | 2 | 0 | 0 | objective met |
| c2 | S3_budget | ✅ | 2 | 0 | 0 | objective met |

Aggregates: c0 verified 2/3, c1 2/3, c2 2/3; evidence_complete 2/3 each; hard
violations 0 everywhere; unscorable 0.

**Observed conclusions (deterministic, no statistical claims):**
1. **Nominal conditions: ordering is irrelevant** — all candidates complete in
   2 steps with verified evidence.
2. **A failed required action cannot be rescued** by ordering or retry: every
   candidate honestly reports completion=False under the S2 fault, and the
   failure terminates the episode truthfully.
3. **Ordering changes failure-discovery latency, not success**: C1 (B-first)
   discovers the fault at step 1; C0/C2 at step 2.
4. **C2's retry never fired** — it triggers only on an Action-A failure, which
   no scenario produces (the S2 fault is on B, and a B PEP-failure halts the
   episode before the retry step). Correctly conditional behavior, reported as
   an observed limitation of the scenario design.
5. **Zero unauthorized actions, zero hard violations, zero unscorable runs**
   across the entire grid.

Ranking (declared lexicographic rule): eligible runs ordered C0/S1, C0/S3,
C1/S1, C1/S3, C2/S1, C2/S3 (all complete, tie broken by steps: C1's S2 run
ranks ahead of C0/C2's S2 runs by step-efficiency of the honest failure).

## 5. Definition of Done verdicts

| Item | Verdict |
|---|---|
| Three candidates representable and reproducibly identifiable | **PASS** (validated serialization; stable content hashes; mismatch refused) |
| Behavior differs only in approved strategy dimensions | **PASS** (schema cannot express anything else; constraint echo enforced) |
| Existing governed execution architecture used | **PASS** (same Runtime/Broker/PEP/store; D2 policy explicitly bound) |
| Every scored result backed by integrity-verified evidence | **PASS** (hardened objective evaluator; digest recomputation) |
| Controlled scenarios reproducible | **PASS** (identical re-runs; S2 outcomes byte-identical in shape) |
| Report covers outcomes, efficiency, failures, exclusions, limitations | **PASS** (manifest + evaluation_report.json/md) |
| Safety/evidence violations rejected, not rewarded | **PASS** (0 violations; forged-evidence probe rejected; exclusions reported) |
| No promotion / no production-policy mutation | **PASS** (policy shas verified before/after; no promotion code exists) |
| D1/D2/safety tests intact | **PASS** (full suite 747 passed / 0 failed) |
| Historical evidence not overwritten | **PASS** (dedicated `evidence/rsi0/<run_id>/`; prior demos untouched) |
| Repository preservation | **PASS** (nothing committed; only intended files added) |

**RSI-0: EVALUATION COMPLETE** (all mandatory conditions demonstrated), with the
explicit limits below.

## 6. Limits (per the task order)

- No independent holdout ⇒ no generalization or transfer claims.
- No promotion/rollback lineage ⇒ C2's retry variant cannot be adopted even if
  it had won; nothing was adopted.
- Deterministic scenarios ⇒ no statistical confidence; the ≥20-trial rule was
  correctly not applied.
- Not GRPO: no policy gradients, no model likelihoods, no parameter updates,
  no reward-model training. This is group-relative **strategy evaluation**
  inspired by the paper's relative-reward idea.
- Student remains recording-only; RSI surfaces beyond RSI-0 untouched.
