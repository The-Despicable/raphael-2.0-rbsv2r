# P4.1 §15.1 Entry — Evidence Package

**Starting HEAD:** `19121d7da7fa2b81b222400c0f889ab52ac26741` (G3-accepted)
**Final HEAD:** `9527ed033cdb482f0692d56572947602fa9384bb`
**Branch:** `weld-sub10-evidence`
**Working tree at capture:** clean except this evidence directory (committed below)

## 1. P4 requirement mapping

| P4 requirement | Existing implementation | Missing | Change | Verification |
|---|---|---|---|---|
| MissionSpec (identity/objectives/target envelope/constraints/halt) | `MissionContext` (unvalidated) | Validated first-class spec | NEW `mission_spec.py`: `MissionSpec` + `HaltConditions` frozen, strict from_dict | 18 new tests |
| Scope (P4 canonical) | `ScopeV0` (proven) | Canonical P4 name | `Scope = ScopeV0` alias; enforcement untouched | 19 scope tests green |
| AuthorizationContext (derived per decision) | Inline receipt→decision mapping | First-class frozen context | NEW `AuthorizationContext`; broker stage attaches per decision; no authority | freshness + non-authorizing tests |
| EvidenceReceipt (§15.1) | Runtime `EvidenceReceipt` (minimal) | Provenance linkage | Defaulted fields; stage_receipt populates from stored truth | linkage + F1 + non-authorizing tests |

Out of scope for P4.1 (later P4 tasks): ArtifactRef (P4.5), ProvenanceRecord chain (P4.6), MissionLedger (P4.8), receipt persistence (P4.4), redaction (P4.9), CLI visibility (P4.10).

## 2. Changed files (exact)

- `src/orchestrator/runtime/mission_spec.py` (NEW, dataclasses-only)
- `src/orchestrator/runtime/types.py` (EvidenceReceipt +9 fields defaulted; `MissionContext.from_spec`)
- `src/orchestrator/runtime/stages.py` (`_derive_auth_context`; 4 context attachments; receipt provenance)
- `src/orchestrator/runtime/loop.py` (halt resolution; mission_id in views; termination-block dedent fix)
- `tests/test_p41_mission_models.py` (NEW, 18 tests)
- `evidence/p41_entry/` (this package)

## 3. Model evidence

- MissionSpec: valid/invalid construction, strict round-trip, scope mapping, from_spec, halt consumption — `p41_targeted_transcript.txt` (18 passed)
- Scope: `Scope is ScopeV0`; enforcement identical (19 scope tests green)
- AuthorizationContext: binds inputs; frozen (FrozenInstanceError on mutation); no PDP reference in source; fresh object per decision on allow AND deny paths
- EvidenceReceipt: legacy defaults preserved; provenance copied from stored authorization truth (broker_receipt_id/action triple/argv match); no authorize/allow/decide methods; no executor/store references

## 4. Regression verification

- G3 suites (guardrails 30 + sandbox 30 + scope 19 + demo 3 + probes 13): 95 passed — `p41_g3_regression_transcript.txt`
- Full floor: **403 passed / 0 failed / 0 skipped / 0 xfail / 33 warnings** — `p41_floor_transcript.txt` (385 baseline + 18 new; warnings unchanged)
- Static closure: 35 orchestrator / 0 arena (Δ+1 = mission_spec.py, expected)
- Loaded closure: 54 / 0 arena (Δ+1, expected)
- Architecture: 1 Runtime / 1 PDP / 1 PEP / 10 stages (probe green); STAGE_ORDER untouched; no new files outside runtime/ + 1 test

## 5. Status classification

- MissionSpec: PROVEN (NOT ACCEPTED — G4 adjudication pending)
- Scope: PROVEN (canonical name; enforcement HISTORICAL/ACCEPTED from G3)
- AuthorizationContext: PROVEN (NOT ACCEPTED)
- EvidenceReceipt: PROVEN (NOT ACCEPTED)
- Provenance: IMPLEMENTED (per-decision derivation + receipt linkage; full chain is P4.6 work — DEFERRED)
- G4: NOT YET ACCEPTED
