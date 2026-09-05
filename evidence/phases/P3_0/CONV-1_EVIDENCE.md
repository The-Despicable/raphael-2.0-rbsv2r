# RAPHAEL P3.0 CONV-1 — Evidence Package

| Field | Value |
|---|---|
| Phase | P3.0 CONV-1 (real brain CapabilityBroker as single canonical PDP) |
| Gate | G3-EN-4 (CONV-1 complete and fail-closed re-proven) |
| Repository HEAD | `5c37bbef1fafd040696e6df881fc309c6cd38fd2` |
| Branch | `main` (ahead of `origin/main` by 30) |
| Implementation commit | `5c37bbef1` (6 files, 304 insertions, 354 deletions) |
| Timestamp | 2026-09-05 |
| Author | RAPHAEL P3.0 CONV-1 Audit <p3.0-conv-1-audit@raphael.local> |

## 1. CONV-1 Objective (GLM §4.2)

> Replace the Runtime's P2 placeholder PDP (`BootstrapPolicy`) decision role with the real brain `CapabilityBroker`. Then re-prove the G2-C2 fail-closed suite against the real Broker with assertions preserved. Exactly one PDP on the canonical path.

## 2. Changes Made

### 2.1 Source Changes (4 files)

| File | Change |
|---|---|
| `src/orchestrator/runtime/policy.py` | `BootstrapPolicy` retained as loader/policy-input helper (per GLM: "loader/policy-input mechanics are the lane's; physical deletion is P9"). Added `to_broker_policy()` factory and `make_broker_from_bootstrap()` to construct a `CapabilityBroker` from bootstrap-v0 rules. The `BootstrapPolicy` class no longer has an `authorize()` method — it is now a loader, not a decision source. |
| `src/orchestrator/runtime/stages.py` | `stage_broker` now calls `broker.propose_action()` on the real `CapabilityBroker`. Maps `ActionReceipt` → `PolicyDecision` (`decision_id = receipt.action_id` for INV-2 linkage). G2-C2 fail-closed hardening preserved and re-proven against the real Broker. |
| `src/orchestrator/runtime/loop.py` | `RaphaelRuntime.__init__` now accepts `broker: Optional[CapabilityBroker]` instead of `policy: Optional[BootstrapPolicy]`. Default broker is `make_broker_from_bootstrap(capability_name="fixture.inspect")`. Exactly one PDP on the canonical path. |
| `src/orchestrator/runtime/__init__.py` | Exports updated: `make_broker_from_bootstrap` added, `BootstrapPolicy` retained (loader), `RaphaelRuntime` now takes a `CapabilityBroker`. |

### 2.2 Test Changes (2 files)

| File | Change |
|---|---|
| `tests/test_g2_c2_fail_closed.py` | All 9 tests re-proven against the real `CapabilityBroker` (not the `BootstrapPolicy` placeholder). Same 9 test functions, same assertions, real Broker as the policy source. The `_make_broker()` helper creates a real `CapabilityBroker` with configurable `BrokerPolicy`. |
| `tests/test_p21_walking_skeleton.py` | `ctx` dict updated to use `"broker"` instead of `"policy"`. All 8 tests pass against the real Broker. |

## 3. Invariant Verification

### 3.1 Single-PDP Invariant (GLM §5.6)

**Command:**
```python
from orchestrator.runtime import RaphaelRuntime
rt = RaphaelRuntime()
print('Runtime broker attribute:', type(rt._broker).__name__)
```

**Result:** `Runtime broker attribute: CapabilityBroker`

**Verification:** Exactly one PDP on the canonical path. The `BootstrapPolicy` is retained as a loader (not a decision source). The Runtime's `_broker` attribute is a `CapabilityBroker` instance. No second PDP exists.

### 3.2 INV-2 Decision Linkage (GLM §5.4)

**Command:**
```python
from orchestrator.runtime import RaphaelRuntime, MissionContext
rt = RaphaelRuntime()
mission = MissionContext(mission_id='inv2-verify', name='inv2', objectives=['inspect'])
traces, term = rt.run_episode(mission)
# ... (full stage execution)
event = ctx['pep']['event']
receipt = ctx['receipt']['receipt']
decision = ctx['broker']['decision']
assert event.decision_id == receipt.decision_id == decision.decision_id
```

**Result:**
```
event.decision_id: 7ae1ab8399323e1f
receipt.decision_id: 7ae1ab8399323e1f
decision.decision_id: 7ae1ab8399323e1f
INV-2: OK (all three match)
```

**Verification:** Every `ExecutionEvent` carries a `decision_id` from the real Broker. Every `EvidenceReceipt` has both `event_id` and `decision_id`. The linkage is unbroken.

## 4. G2-C2 Fail-Closed Suite (Re-Proven Against Real Broker)

All 9 G2-C2 tests re-proven against the real `CapabilityBroker`:

| Test | Status |
|---|---|
| `test_c2_1_non_allowlisted_action_class_denied` | PASSED — real Broker denies unknown action_class |
| `test_c2_2_denied_produces_no_execution_event` | PASSED — denied action does not reach PEP |
| `test_c2_3_denied_produces_no_receipt` | PASSED — denied action does not mint receipt |
| `test_c2_4_denial_appears_in_decision_trace` | PASSED — denial recorded in trace |
| `test_c2_5_denied_episode_terminates_deterministically` | PASSED — 5 stages, broker failure |
| `test_c2_6a_missing_broker_fails_closed` | PASSED — broker=None → fail with explicit error |
| `test_c2_6b_failing_broker_fails_closed` | PASSED — broker.propose_action() exception → fail |
| `test_c2_7_default_deny_dynamically_exercised` | PASSED — deny path is dynamic, not configured |
| `test_c2_8_full_fail_closed_episode` | PASSED — end-to-end fail-closed with real Broker |

**Assertion preservation:** All assertions from the original G2-C2 tests are preserved. The only change is the policy source: from `BootstrapPolicy` (placeholder) to `CapabilityBroker` (real Broker). No assertion was weakened, skipped, or narrowed.

## 5. Floor Verification

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 275 passed, 0 failed, 31 warnings, ~7s

| Metric | FLOOR(P0) | Post-G2-FR | Post-CONV-1 |
|---|---|---|---|
| Passed | 239 | 275 | **275** |
| Failed | 0 | 0 | **0** |
| Warnings | 26-27 | 31 | **31** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton (real Broker) + 9 G2-C2 fail-closed (real Broker) + 19 P2 guardrails = **275**.

**FLOOR = 275. Zero skips. Zero xfails. Zero weakening. 19 P2 guardrails green.**

## 6. Changed Files (CONV-1)

```
src/orchestrator/runtime/__init__.py                    (M)
src/orchestrator/runtime/loop.py                        (M)
src/orchestrator/runtime/policy.py                      (M)
src/orchestrator/runtime/stages.py                      (M)
tests/test_g2_c2_fail_closed.py                         (M)
tests/test_p21_walking_skeleton.py                     (M)
```

**Total changes:** 6 files (4 source, 2 tests). 304 insertions, 354 deletions.

## 7. Constraints Honored (from GLM §5)

1. ✅ **FLOOR = 275**, monotonic; zero skips, zero xfails, zero weakening
2. ✅ **All 19 P2 guardrails green continuously**
3. ✅ **Arena-free closure** (verified by `test_import_graph_single_runtime`)
4. ✅ **INV-2 decision linkage** unbroken (verified above)
5. ✅ **Fail-closed preserved and re-proven** against the real Broker (9 tests)
6. ✅ **Exactly one PDP** on the canonical path (CapabilityBroker)
7. ✅ **INV-1 live** — INV-1 not yet triggered (exec/ not yet created; CONV-2)
8. ✅ `RAPHAEL_USE_LEGACY=1` remains the sole legacy reach
9. ✅ One cognitive loop; no new stages
10. ✅ No roadmap modification

## 8. Prohibited Work NOT Performed

- ❌ CONV-2 (exec/ creation, INV-1 activation) — not yet
- ❌ CONV-3 (SafeProvingCapability relocation) — not yet
- ❌ Organ wiring (Planner, WorldModel, Student) — not yet (GLM §4.3)
- ❌ Welds (SUB14, SUB10, SHELL) — not yet (GLM §4.5)
- ❌ MVP demonstration — not yet (GLM §4.6)
- ❌ Scope v0, native sandbox, evidence v1, WorldModel enforcement, replan trigger — not yet

**STOP after CONV-1.** Awaiting G3-EN-4 confirmation before CONV-2/CONV-3.
