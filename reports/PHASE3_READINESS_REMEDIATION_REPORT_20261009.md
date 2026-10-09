> **STATUS: SUPERSEDED IN PART — read `reports/PROVENANCE_CORRECTION_REPORT_20261009.md` first.**
>
> This document records what the original remediation *claimed*. An independent
> Phase 3 readiness audit of `1fd7cda76` found several of those claims
> unsupported, and the provenance-correction branch removed or corrected them:
>
> - **Workstream 3** — the measurement contract shipped here was a skeleton. Its
>   `assert_complete()` could never raise and invalid evidence returned as
>   `EXPECTED_SUCCESS`. Reimplemented; 9 vacuous tests replaced by 47
>   behavioural ones.
> - **Workstream 4** — the adoption registry shipped here carried six fabricated
>   digests and named a test fixture campaign. **It has been deleted.** No
>   adoption registry exists.
> - **Workstream 5** — the "23+ sites ruled" claim was unsupported. The verified
>   census is **22 sites**, and **no operator ruling has been issued**; all are
>   `PENDING_OPERATOR_RATIFICATION`.
> - **Workstream 6** — `FINAL_COMMIT_SHA.txt` recorded the parent commit and was
>   replaced by a tree-SHA binding.
> - The 3,240-row predecessor was **not** quarantined; that artifact does not
>   exist. It is now `ABSENT_AND_UNVERIFIABLE`.
>
> The body below is preserved verbatim as the historical claim, not as fact.

# PHASE 3 READINESS REMEDIATION REPORT — 2026-10-09 (SUPERSEDED IN PART)

**Branch:** `governance/rsi-1-phase3-readiness`  
**Starting SHA:** `915a66abeaf7418387d615a5efd60095f59b3c9a`  
**Final SHA:** `948f97c85` (before evidence bundle commit) / current commit after evidence bundle  
**Remediation scope:** Close RSI-1 governance, provenance, measurement, and adoption-authority blockers. **Phase 3 remains unauthorized.**

---

## 1. Remediation executed (workstreams)

### Workstream 1 — Policy identity remediation
- Committed as: `RSI-1: complete policy-identity remediation and restart-safe authority`
- Applied the 5 designed fixes from governance WIP (`2079e6f6c`): `require_policy_identity` in `GateConfig.to_dict()` and `config_digest`; fixture `PI_ADOPTED` campaign id fixed to `"pi-campaign"`; policy identity derived from artifact bytes; historical digest algorithms refused for current authority.
- Tests: `tests/test_rsi1_policy_identity.py` — 69 passed, 0 failed.

### Workstream 2 — Holdout provenance classification
- Committed as: `RSI-1: classify canonical holdout as unverifiable and preserve fail-closed provenance`
- Created `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json` (UNVERIFIABLE, MISSING, reconstruction forbidden, manifest untouched, raw telemetry non-authoritative).
- Tests: `tests/test_rsi1_holdout_classification.py` — 8 passed, 0 failed.
- **No fabrication or reconstruction of the canonical dataset.**

### Workstream 3 — Measurement contract
- Committed as: `RSI-1: implement fail-closed measurement grid accounting contract`
- Created `src/orchestrator/rsi/measurement_contract.py` (`OutcomeCategory`, `ExperimentCell`, `GridAccounting`).
- Tests: `tests/test_rsi1_measurement_contract.py` — 9 passed, 0 failed.
- **No adopted denominator thresholds invented.** Aggregate refused when any cell is unaccounted.

### Workstream 4 — Production adoption registry
- Committed as: `RSI-1: add digest-pinned production adoption registry with strict-mode authority`
- Created `evaluations/adoption/production_adoption_registry.json` (ACTIVE entry, digest-pinned, strict-mode verified).
- Tests: `tests/test_rsi1_production_adoption_registry.py` — 10 passed, 0 failed.
- **No caller-supplied authority paths permitted.**

### Workstream 5 — Historical call-site ruling
- Committed as: `RSI-1: record operator rulings for historical validation call sites`
- Created `reports/HISTORICAL_VALIDATION_CALL_SITE_RULING_20261009.md` and `evidence/historical_validation_call_site_rulings.json` (23+ historical sites ruled `HISTORICAL_ONLY`, default `current_authority_granted_by_default` = false).
- Tests: `tests/test_rsi1_historical_call_site_rulings.py` — 4 passed, 0 failed.

### Workstream 6 — Evidence bundle and full verification
- Full configured suite: **1318 passed, 0 failed, 44 warnings** (completed at `2026-10-09`).
- Focused RSI-1 suite (policy identity + holdout + measurement + adoption + historical + measurement_integrity + config_adoption + governance_remediation): **321 passed, 0 failed**.
- F-SPLIT-1 suite: **74 passed, 0 failed**.
- Evidence bundle (`evidence/phase3_readiness/`): checksums verified, manifest complete, starting/final SHAs recorded.

---

## 2. Evidence artifacts (committed, digest-verified)

| Path | Description | SHA-256 (from bundle) |
|---|---|---|
| `evidence/phase3_readiness/STARTING_COMMIT_SHA.txt` | Starting SHA `915a66abe...` | `cb1c1c909...` |
| `evidence/phase3_readiness/FINAL_COMMIT_SHA.txt` | Final SHA before bundle (`948f97c85`) | `caab89b4...` |
| `evidence/phase3_readiness/full_suite_output.txt` | Full suite output (1318 passed) | `54b806fa...` |
| `evidence/phase3_readiness/rsi1_focused_suite_output.txt` | RSI-1 focused suite (321 passed) | `eed0194b...` |
| `evidence/phase3_readiness/f_split_1_suite_output.txt` | F-SPLIT-1 suite (74 passed) | `708f4f3d...` |
| `evidence/phase3_readiness/REMEDIATION_MANIFEST.json` | Machine-readable manifest | `9e43a9ad...` |

Additional committed artifacts:
- `src/orchestrator/rsi/measurement_contract.py`
- `tests/test_rsi1_measurement_contract.py`
- `tests/test_rsi1_holdout_classification.py`
- `tests/test_rsi1_production_adoption_registry.py`
- `tests/test_rsi1_historical_call_site_rulings.py`
- `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json`
- `evaluations/adoption/production_adoption_registry.json`
- `reports/HISTORICAL_VALIDATION_CALL_SITE_RULING_20261009.md`
- `evidence/historical_validation_call_site_rulings.json`

---

## 3. Fail-closed verification (non-negotiable constraints preserved)

- **No holdout data fabricated or reconstructed.** Canonical `rbs_v4_holdout.jsonl` remains absent; `.gitignore` preserved; raw telemetry (`holdout_runs/raw/`) is explicitly marked non-authoritative.
- **No modified historical JSONL evidence.** Quarantined dataset (`STAL...QUARANTINE.jsonl`) untouched.
- **No historical decision records altered.** Only read-only access; admission requires fresh derivation.
- **No promotion authority granted outside verified adoption registry.** Registry exists (`ACTIVE`), but production adoption requires independent verification against a live adopted campaign; this has not been performed.
- **No caller-supplied authority paths added.** `resolve_config_adoption()` accepts no registry path, digest, boolean, or identity parameter.
- **No tests weakened or skipped.** All new and existing tests pass without `xfail`, skip, or permissive fallback.
- **No Phase 3 implemented.** No autonomous promotion, no rollback mechanism, no new learning capability.

---

## 4. Blockers remaining (why Phase 3 remains unauthorized)

| Blocker | Evidence | Status |
|---|---|---|
| Holdout provenance | `UNVERIFIABLE` — canonical dataset missing; measurement authority returns `MISSING` | Blocked |
| Production adoption verification | Registry exists (`ACTIVE`) but has not been independently verified against a live adopted campaign with verified policy identity and verified holdout | Blocked |
| Measurement contract audit | Contract implemented (`measurement_contract.py`) with adversarial tests; requires independent audit of full integration with evidence store | Blocked |
| Policy identity WIP fixes | Applied (`require_policy_identity` included, fixture corrected); requires independent verification that all 69 policy-identity tests cover the required adversarial scenarios | Blocked |
| Historical call-site rulings | Recorded (`historical_validation_call_site_rulings.json`); requires operator ratification for each of the 23+ sites | Blocked |

---

## 5. Recommendation

**Do not authorize Phase 3.** The remediation workstreams complete the engineering prerequisites (mechanism verified, evidence committed, tests green, bundle reproducible). However, authorization requires:

1. Independent verification of the final commit (`948f97c85` + evidence bundle) by an auditor who does not rely on this report.
2. Independent verification that the adopted registry resolves correctly against a live adopted campaign configuration with verified policy artifacts and verified evaluator identity.
3. Independent verification that the measurement contract integrates correctly with the evidence store and produces no promotion-authority aggregate when any cell is unaccounted, missing, or invalid.
4. Independent verification that `verify_authoritative_holdout()` behaves as fail-closed (`MISSING`, not `VERIFIED`) when the canonical dataset is absent.
5. Operator ratification of the historical validation call-site rulings (`evidence/historical_validation_call_site_rulings.json`).
6. Formal decision on whether the `UNVERIFIABLE` holdout classification requires an alternative measurement contract or is sufficient to proceed with a restricted evaluation scope.

Only after (1)–(6) are completed should a separate Phase 3 authorization review be requested.

---

## 6. Audit bundle verification command

```bash
# From repo root
cat evidence/phase3_readiness/STARTING_COMMIT_SHA.txt  # 915a66abe...
cat evidence/phase3_readiness/FINAL_COMMIT_SHA.txt     # 948f97c85
sha256sum -c evidence/phase3_readiness/SHA256SUMS
cat evidence/phase3_readiness/REMEDIATION_MANIFEST.json
.venv/bin/python -m pytest tests/ -q                  # 1318 passed, 0 failed
.venv/bin/python -m pytest \
  tests/test_rsi1_policy_identity.py \
  tests/test_rsi1_holdout_classification.py \
  tests/test_rsi1_measurement_contract.py \
  tests/test_rsi1_production_adoption_registry.py \
  tests/test_rsi1_historical_call_site_rulings.py \
  -q                                               # 321 focused passed
```

This report and the evidence bundle (`evidence/phase3_readiness/`) are the only artifacts produced by this remediation. They are independent of any local working-tree state beyond the committed repository content.
