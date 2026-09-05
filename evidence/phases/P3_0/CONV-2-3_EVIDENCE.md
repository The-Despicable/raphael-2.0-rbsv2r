# RAPHAEL P3.0 CONV-2 / CONV-3 — Evidence Package

| Field | Value |
|---|---|
| Phase | P3.0 CONV-2 + CONV-3 (exec/ PEP, capability gating, INV-1 live) |
| Gate | (precedes G3-EN-5 organ wiring) |
| Repository HEAD | `22eff1774402c712ff6efaea8d18cabda2240966` |
| Branch | `main` (ahead of `origin/main` by 31) |
| Implementation commit | `22eff1774` (7 files, 531 insertions, 105 deletions) |
| Timestamp | 2026-09-05 |
| Author | RAPHAEL P3.0 CONV-2/3 Audit |

## 1. CONV-2: PEP in exec/ (v4 L6)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

### Created

- `src/orchestrator/exec/__init__.py` — PEP package marker, exports
  `SafeProvingCapability`, `CapabilityResult`, `verify_inv1_primitive_confinement`,
  `INV1_VIOLATION`
- `src/orchestrator/exec/safe_capability.py` — the safe proving capability
  (relocated from `src/orchestrator/runtime/safe_proving_capability.py`)
- `src/orchestrator/exec/inv1_guard.py` — INV-1 static check utility
  (scans `src/orchestrator/` for forbidden primitive imports outside
  `exec/`)

### Runtime integration

- `src/orchestrator/runtime/loop.py` — `RaphaelRuntime.__init__`
  constructs `SafeProvingCapability(broker=self._broker)`. The
  capability is imported from `orchestrator.exec.safe_capability`.
- `src/orchestrator/runtime/stages.py` — `stage_pep` calls
  `capability.inspect(request.target)` on the exec/-owned capability.

## 2. CONV-3: SafeProvingCapability relocated + constructor gating

### Relocation

- `SafeProvingCapability` moved from
  `src/orchestrator/runtime/safe_proving_capability.py` to
  `src/orchestrator/exec/safe_capability.py`
- `src/orchestrator/runtime/safe_proving_capability.py` retained as
  a re-export shim (per GLM pattern: BootstrapPolicy retained as
  loader; physical deletion is P9)

### Constructor gating

`SafeProvingCapability(broker: Optional[CapabilityBroker] = None)`:
- If a broker is bound, `inspect(target)` requires
  `record_authorization(target)` to have been called for that target.
  Otherwise raises `CapabilityNotGatedError`.
- The `stage_pep` calls `capability.record_authorization(request.target)`
  after the broker stage succeeds, before invoking
  `capability.inspect(request.target)`.
- INV-2 decision linkage preserved: the receipt from
  `broker.propose_action()` carries the `action_id` that
  `stage_pep` uses as the `decision_id` on the `ExecutionEvent`.

## 3. INV-1 goes live

INV-1: process/network/file primitives are confined to `exec/`.

### Broadened primitive lexicon (per the standing note)

Forbidden outside `exec/`:
- `subprocess` (any form)
- `os.system`, `os.popen`, `os.exec*`, `os.spawn*`
- `socket.*`
- `urllib.*`, `http.client`, `http.server`
- `requests`
- `open(..., 'w')`, `open(..., 'a')`, `open(..., 'x')` (write modes)
- `os.remove`, `os.unlink`, `os.rmdir`, `shutil.rmtree`

### Static check

`verify_inv1_primitive_confinement()` in `orchestrator.exec.inv1_guard`
scans `src/orchestrator/` for forbidden primitive imports outside
`exec/`. Returns a list of violations (empty = INV-1 satisfied).

The broader orchestrator/ tree has pre-existing primitive usage
(70 violations across legacy code paths like `weaponizer/`,
`c2/`, `exfil/`, `tactics/`, etc.). These are pre-existing and are
P3+ migration work. The Runtime's own files (`orchestrator/runtime/`)
are clean.

### Runtime verification

`test_inv1_runtime_clean` (new guardrail): scans
`src/orchestrator/runtime/` for forbidden primitives. **PASS** —
the Runtime's own files use no forbidden primitives.

## 4. Test Results

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 280 passed, 0 failed, 32 warnings, ~8s

| Metric | Pre-CONV-2/3 | Post-CONV-2/3 |
|---|---|---|
| Passed | 275 | **280** |
| Failed | 0 | **0** |
| Warnings | 31 | **32** |
| Guardrails (P2 + new) | 19 | **24** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton (real Broker +
exec/ capability) + 9 G2-C2 fail-closed (real Broker) + 19 P2
guardrails + 5 new INV-1/CONV-2/CONV-3 guardrail tests = **280**.

### New guardrail tests (CONV-2/3)

| Test | Status |
|---|---|
| `test_inv1_runtime_clean` | PASS — Runtime files use no forbidden primitives |
| `test_inv1_exec_package_may_use_primitives` | PASS — exec/ guard callable |
| `test_inv1_stage_pep_delegates_to_exec` | PASS — stage_pep delegates to exec/ |
| `test_inv3_capability_gated_by_broker` | PASS — unauthorized target raises |
| `test_inv3_capability_works_after_authorization` | PASS — post-auth inspect succeeds |

## 5. Changed Files (CONV-2/3)

```
src/orchestrator/exec/__init__.py                    (NEW)
src/orchestrator/exec/safe_capability.py             (NEW)
src/orchestrator/exec/inv1_guard.py                  (NEW)
src/orchestrator/runtime/loop.py                      (M)
src/orchestrator/runtime/safe_proving_capability.py  (M, now re-export shim)
src/orchestrator/runtime/stages.py                   (M, stage_pep records auth)
tests/test_p2_guardrail_inv1.py                      (NEW, 5 tests)
```

**Total changes:** 7 files (3 new source, 2 modified source, 1
new test). 531 insertions, 105 deletions.

## 6. Constraints Honored (from GLM §5)

1. ✅ **FLOOR = 280** (>= 275), monotonic; zero skips, zero xfails, zero weakening
2. ✅ **All 24 P2 guardrails green continuously** (19 original + 5 new)
3. ✅ **Arena-free closure** (verified by `test_import_graph_single_runtime`)
4. ✅ **INV-2 decision linkage** unbroken
5. ✅ **Fail-closed preserved** (G2-C2 tests pass against real Broker)
6. ✅ **Exactly one PDP** on the canonical path (CapabilityBroker)
7. ✅ **INV-1 live** — `verify_inv1_primitive_confinement` scans Runtime
8. ✅ `RAPHAEL_USE_LEGACY=1` remains the sole legacy reach
9. ✅ One cognitive loop; no new stages
10. ✅ No roadmap modification

## 7. Prohibited Work NOT Performed

- ❌ Organ wiring (Planner, WorldModel, Student) — not yet (GLM §4.3, G3-EN-5)
- ❌ Welds (SUB14, SUB10, SHELL) — not yet (GLM §4.5, G3-EN-4)
- ❌ MVP demonstration — not yet (GLM §4.6)
- ❌ Scope v0, native sandbox, evidence v1, WorldModel enforcement, replan trigger — not yet
- ❌ P4 depth, Decepticon, Student learning, Teacher, P5-BIND-1 — prohibited

**STOP after CONV-2/3.** Awaiting G3-EN-5 confirmation before organ wiring.
