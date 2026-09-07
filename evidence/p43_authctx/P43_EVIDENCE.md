# P4.3 §15 Authorization Context — Evidence Package

**Starting HEAD:** `6f49483a73e62f542b88a016a32ea501f079b0bb` (P4.2-accepted)
**Final HEAD:** `6f4bd5207740849d475d25d772dadb484ae1755c`
**Branch:** `weld-sub10-evidence`
**Working tree at capture:** clean except this evidence directory (committed below)

## 1. §15 P4.3 requirement mapping

Roadmap P4.3: *"Derive context from current Mission + Scope + ActionSpec."*
(No `ActionSpec` class exists; the canonical action model is `ActionRequest` — no parallel model invented, per §11.)

| Requirement | P4.1 state | P4.3 gap closed | Evidence |
|---|---|---|---|
| Derive from current Mission | mission_id from view string (spoofable) | Actual `MissionSpec` object threaded via `MissionContext.spec` → view; spec wins authoritatively | `test_derivation_uses_actual_spec_not_view_string` |
| Mission binding | No digest; reuse undetectable | `MissionSpec.digest()` (sha256 over identity/objectives/targets/scope_hash); context carries it | digest determinism + cross-mission mismatch tests |
| Scope binding | scope_hash only | Unchanged carrier (hash IS the binding) + proof of no duplicate evaluation in derivation source | `test_context_carries_bound_scope`, `test_scope_evaluation_unchanged_single_evaluator` |
| ActionSpec binding | Request fields, but method fell back empty vs stored "inspect" | Stored-receipt-first binding (capability/method/action_type as authorized, request fallback) | `test_context_matches_stored_broker_truth` (failed pre-fix, green post-fix) |
| Broker decision binding | decision_id only | `receipt_id` links stored authorization truth | stored-truth equality test |
| Allow + deny | Both derived | Preserved + denied-context non-approval proven behaviorally | deny test incl. PEP-gate refusal probe |
| Immutability | Frozen | Preserved + determinism proven (equal bindings modulo fresh ids) | FrozenInstanceError + re-derivation tests |
| Non-authorizing | Source scan | Preserved + tightened (definition-statement checks; docstring prose distinguished from authority) | source + behavioral tests |

## 2. Changed files (exact)

- `src/orchestrator/runtime/mission_spec.py` (digest + 2 fields + to_dict)
- `src/orchestrator/runtime/types.py` (spec field + from_spec binding)
- `src/orchestrator/runtime/loop.py` (view spec threading)
- `src/orchestrator/runtime/stages.py` (precedence + stored-first binding)
- `tests/test_p43_auth_context.py` (NEW, 12 tests)
- `evidence/p43_authctx/` (this package)

Diff: +75/−9 across 4 runtime files. No other source touched.

## 3. Verification

- P4.3 targeted: 12 passed — `p43_targeted_transcript.txt`
- Regression (P4.1 18 + P4.2 14 + scope 19 + guardrails 30 + sandbox 30 + demo 3 + probes 13): 127 passed — `p43_regression_transcript.txt`
- Full floor: **429 passed / 0 failed / 0 skipped / 0 xfail / 33 warnings** — `p43_floor_transcript.txt` (417 + 12; warnings unchanged)
- Static closure: 35/0; loaded: 54/0 (unchanged)
- Architecture: 1 Runtime / 1 PDP / 1 PEP / 10 stages (probe green); STAGE_ORDER untouched
- Repairs honestly recorded: (1) test initially contradicted the fail-closed reserved-key design (test fixed, design kept); (2) stored-vs-request method gap found by new test (implementation fixed to stored-first); (3) two edit-tool duplications repaired with git-original text (to_dict restored, except-clause restored)

## 4. Status classification

- P4.3: PROVEN (NOT ACCEPTED — governance adjudication pending)
- G4: NOT YET ACCEPTED
