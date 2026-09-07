# §14.4 Native Minimal Sandbox — Implementation Evidence (EVIDENCE READY, NOT ACCEPTED)

## 1. Baseline (pre-change, actual)

- HEAD: `bec5c65ed32834a7e19f35ff85809ae881a18e54`, branch `weld-sub10-evidence`, clean
- Floor: 316 passed / 0 failed / 0 skipped / 0 xfail; guardrails 30
- Closure: static 32 orchestrator / 0 arena; loaded 51 / 0 arena
- §14.3 Scope v0 CLOSED/FROZEN; SHELL/SUB10/SUB14 ACCEPTED/FROZEN

## 2. Preflight findings

- exec/ held zero subprocess primitives (fixture-only PEP). INV-1 guardrail
  scans only `orchestrator/runtime/*.py` file text; `test_inv1_stage_pep_delegates_to_exec`
  requires stage_pep success via exec/ capability.
- Narrowest extension point: new `exec/sandbox.py` mechanism + dispatch branch
  inside existing `stage_pep` for `action_type == "sandboxed_exec"` (unreachable
  via the hardcoded planner until MVP). Lazy import keeps `runtime/*.py` free of
  primitive imports. No new stage, no new PDP, no broker/scope/shell changes.
- Receipt verification reuses the broker's own `receipt_store`: stored fields
  only (action_id lookup, status AUTHORIZED, target match). No new registry.

## 3. Implementation commit

- Commit: `7e68b245202b11dcf11ef9c113cb40ff4ab1dbb5`
  "§14.4 Native minimal sandbox: exec-owned bounded executor + PEP dispatch + 18 tests"
- Files: `src/orchestrator/exec/sandbox.py` (new, ~400 lines),
  `src/orchestrator/exec/__init__.py` (exports, additive),
  `src/orchestrator/runtime/stages.py` (+dispatch branch + `_stage_pep_sandboxed`
  helper; no primitive imports added to runtime/),
  `tests/test_exec_sandbox.py` (new, 18 tests)
- R-W2: no existing test edited or removed.

## 4. Authorization path

Broker `propose_action` (allow) → `stage_broker` (broker + scope conjunct) →
`stage_pep` allow-gate → `sandboxed_exec` branch → `SandboxedExecutor.execute`
re-verifies receipt against `broker.receipt_store` → bounded execution →
`SandboxResult` → `ExecutionEvent(capability="sandbox.exec")` → existing receipt
stage. Absent/forged/denied/cross-target receipts raise `SandboxNotAuthorized`
(CONV-3 convention). No bypass flag, no unsafe mode, no `authorized=True`
convention (verified by source search: only docstring mentions).

## 5. Enforcement matrix (brutally honest)

| Requirement | Mechanism | Actually Enforced? | Test |
|---|---|---|---|
| Controlled cwd | mkdtemp under policy root; Popen(cwd=workdir); always removed | YES | test_controlled_cwd_enforced |
| Cwd escape | absolute artifacts rejected at construction; traversal rejected at collection (realpath containment) | YES | test_artifact_escape_rejected |
| Timeout | deadline + setsid/killpg + bounded reap | YES | test_timeout_enforced |
| Output limit | combined-size poll (50ms) + kill + truncate; RLIMIT_FSIZE kernel backstop | YES (poll granularity) | test_output_limit_enforced |
| Resource limit | RLIMIT_CPU (+SIGXFSZ mapping); RLIMIT_AS/memory NOT claimed | YES (CPU/file-size only) | test_resource_limit_cpu_busy_loop |
| Network restriction | NO kernel isolation in v0; allow_network=True → UNSUPPORTED fail-closed; local-only posture via no-shell + resolved allowlist + DEVNULL stdin + scrubbed env (mitigation, not guarantee) | NO → fail-closed | test_network_unsupported_fails_closed |
| Artifact collection | declared relative paths, realpath containment, per-file cap, missing → ARTIFACT_FAILURE | YES | test_artifact_collection_bounded |

Result statuses: success/timeout/output_limit/resource_limit/setup_failure/
exec_failure/artifact_failure/unsupported — all exercised by tests.

## 6. Test results

- `tests/test_exec_sandbox.py`: 18 passed (repeat runs stable, incl. 3x race check
  on output/resource tests).
- Full floor (actual): **334 passed / 0 failed / 0 skipped / 0 xfail** (316 + 18).
- Guardrails collected: 30 (unchanged; no new guardrail-named tests).
- SHELL + G3-EN-5 + INV-1 subsets green within the floor.

## 7. Primitive confinement

- New primitives (`subprocess`, `os.killpg`, `shutil.rmtree`, `resource`) exist
  ONLY in `src/orchestrator/exec/sandbox.py` (INV-1-permitted package).
- `src/orchestrator/runtime/*.py` gains no forbidden-primitive import
  (INV-1 file-scan test green; dedicated `test_no_primitive_imports_in_runtime`).
- Legacy-tree primitives (agents/, c2/, exploit/, …) pre-date §14.4, outside the
  canonical Runtime closure (B-1a lists 33 modules, none legacy).

## 8. Invariants confirmed

- One PDP (`broker.propose_action` single runtime call site); one Runtime
  (`class RaphaelRuntime` once); one loop (single `step()` sequencer);
  STAGE_ORDER unchanged (test-pinned, 10 stages); PEP sole execution
  enforcement; no Arena in closure (static 33/0, loaded 51/0, both verdicts
  True); no second control plane; SHELL untouched.

## 9. Closure deltas (honest)

- Static 32 → 33: exactly `orchestrator.exec.sandbox` (lazy import in stages.py).
- Loaded 51 → 51: sandbox not imported by the default episode path.

## 10. Carried-forward records (GLM riders)

### C-1 rider — Scope suite verbatim transcript (machine-captured this session)

```
============================= test session starts ==============================
collecting ... collected 19 items

tests/test_scope_v0.py::test_missing_scope_required_fails_closed_before_any_stage PASSED [  5%]
tests/test_scope_v0.py::test_non_scopev0_scope_object_fails_closed PASSED [ 10%]
tests/test_scope_v0.py::test_missing_mission_id_rejected PASSED          [ 15%]
tests/test_scope_v0.py::test_empty_targets_rejected PASSED               [ 21%]
tests/test_scope_v0.py::test_malformed_entries_rejected PASSED           [ 26%]
tests/test_scope_v0.py::test_out_of_scope_target_rejected_after_broker_allow PASSED [ 31%]
tests/test_scope_v0.py::test_prohibited_capability_rejected PASSED       [ 36%]
tests/test_scope_v0.py::test_unlisted_capability_rejected_at_runtime PASSED [ 42%]
tests/test_scope_v0.py::test_prohibited_action_type_rejected PASSED      [ 47%]
tests/test_scope_v0.py::test_valid_in_scope_declaration_succeeds PASSED  [ 52%]
tests/test_scope_v0.py::test_valid_scope_does_not_bypass_broker_denial PASSED [ 57%]
tests/test_scope_v0.py::test_scope_covers_is_deterministic_and_bounded PASSED [ 63%]
tests/test_scope_v0.py::test_serialization_roundtrip_stable PASSED       [ 68%]
tests/test_scope_v0.py::test_scope_immutable_after_validation PASSED     [ 73%]
tests/test_scope_v0.py::test_scope_module_is_pure_contract PASSED        [ 78%]
tests/test_scope_v0.py::test_scope_does_not_touch_worldmodel_or_broker PASSED [ 84%]
tests/test_scope_v0.py::test_over_max_impact_denied PASSED               [ 89%]
tests/test_scope_v0.py::test_exact_max_impact_allowed PASSED             [ 94%]
tests/test_scope_v0.py::test_stage_fails_closed_without_impact_estimate PASSED [100%]

============================== 19 passed in 0.35s ==============================
```

One-line honest explanation of the previous percentage anomaly: the earlier
transmitted Scope transcript was hand-reassembled with non-monotonic progress
percentages (a packet transcription error, not a test-result issue); the
machine-captured rerun above at the same HEAD shows monotonic percentages
and 19/19 pass.

Full-floor summary carried forward: 316 passed, 32 warnings (at §14.3 close).

### §14.10 design ruling carried forward

Future over-cap-impact demonstration must exercise the REAL chain using a
Broker-recorded estimate exceeding mission max_impact. The impact value must
not be manufactured inside Scope. §14.10 not implemented here.

## 11. Remaining non-blocking items

- RLIMIT_AS/memory caps unclaimed (no reliable sizing in v0).
- Kernel network isolation unavailable (fail-closed UNSUPPORTED recorded).
- `sandboxed_exec` unreachable via the hardcoded planner until MVP assembly.
- Executable allowlist is a static mechanism bound (coreutils set); widening is
  a future explicit decision, not runtime behavior.
- preexec_fn assumes the single-threaded sequencer (documented in module).
