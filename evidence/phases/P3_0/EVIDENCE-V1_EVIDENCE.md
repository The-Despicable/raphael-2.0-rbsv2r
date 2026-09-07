# §14.5 Evidence v1 — Implementation Evidence (EVIDENCE READY, NOT ACCEPTED)

## 1. Baseline (pre-change, actual)

- HEAD: `18a7acd091ea17615c290feeed9ca865111f1650`, branch `weld-sub10-evidence`, clean
- Floor: 334 passed / 0 failed / 0 skipped / 0 xfail; guardrails 30
- Closure: static 33 orchestrator / 0 arena; loaded 51 / 0 arena
- §14.3 CLOSED/FROZEN; §14.4 implemented; SHELL/SUB10/SUB14 ACCEPTED

## 2. Existing evidence architecture (audit)

- `brain/evidence.py`: `Evidence` (frozen, sha256 content_hash — but random
  `evidence_id` and wall-clock `collected_at` inside the hash, so identity is
  nondeterministic); `EvidenceRelation` (typed, incl. derived_from);
  `EvidenceGraph` (canonical in-memory graph shared by WorldModel/organs via
  `runtime/organs.py`; NO persistence, NO mission linkage, NO strict ingest).
- `hardening/action_receipt.py`: ephemeral receipt chain (no durable backing).
- `audit_trail.py`: legacy operator JSONL log (not evidence-typed).
- `runtime/types.py:EvidenceReceipt`: in-trace PEP→decision link only.
- No evidence tests, no durable store, no deterministic identity, no five-class
  substrate anywhere in the repo.

## 3. Design

- NEW `runtime/evidence_v1.py` (pure, stdlib-only at top level): five frozen
  dataclasses sharing one `EvidenceRecord` envelope — Assertion, Observation,
  ExecutionResult, Artifact, Finding. Frozen + validated + bounded.
- Identity: `ev1_` + sha256 over canonical body (version, kind, mission_id,
  producer, parents, payload). `observed_at` is provenance, NOT identity:
  equivalent content observed at different times shares identity (idempotent
  ingest). Payload restricted to JSON scalars + one tuple level, bounded
  strings, ≤24 fields, ≤8 parents, ≤16 artifact refs.
- Serialization: fixed key order, explicit version 1, strict `from_dict`
  (unknown fields / wrong version / missing required / identity mismatch all
  raise `EvidenceError`), round-trip preserves identity.
- NEW `exec/evidence_store.py` (file writes permitted ONLY in exec/ per INV-1):
  append-only bounded JSONL (`evidence_v1.jsonl`), fsync per append, index by
  identity, parent-existence check, identical-reingest idempotent, identity
  conflict rejected, oversize rejected (>128KiB serialized), cap 10000 records
  (StoreFull fail-closed), corrupt-line fail-closed load. No overwrite/delete API.
- Graph: NO new graph. `to_legacy_evidence()` exports into the canonical
  `EvidenceGraph` via existing `add_evidence` (student producers map to
  MODEL_INFERENCE — no trust elevation; producer labels preserved verbatim).
- Integration: downstream adapters (`execution_result_from_sandbox`,
  `artifact_records_from_sandbox`) consume existing `SandboxResult`/receipt
  objects structurally. NO runtime/ change, NO new stage, STAGE_ORDER untouched.
- Artifacts are references (relpath + size + sha256); evidence never reads host
  files (bytes passed in, never opened by path).

## 4. Implementation commit

- Commit: `8cd3a956149a4eb5c814532385ccfa819067ffda`
  "§14.5 Evidence v1: five typed classes + deterministic identity + bounded JSONL store + 23 tests"
- Files: `src/orchestrator/runtime/evidence_v1.py` (new),
  `src/orchestrator/exec/evidence_store.py` (new),
  `src/orchestrator/runtime/__init__.py` (+exports),
  `src/orchestrator/exec/__init__.py` (+export),
  `tests/test_evidence_v1.py` (new, 23 tests)
- R-W2: no existing test edited or removed.

## 5. Test results

- `tests/test_evidence_v1.py`: 23 passed — five classes, malformed/version/
  determinism/round-trip/unknown/missing/provenance/live-sandbox linkage/
  artifact refs/bounds/idempotent-duplicate/conflict/invalid-ref/cycle-bound/
  persistence/corrupt/no-authorization/scope-sandbox-unchanged/no-stage/no-arena/
  worldmodel-untouched/graph-integration/artifact-ref-bound.
- Full floor (actual): **357 passed / 0 failed / 0 skipped / 0 xfail** (334 + 23).
- Guardrails collected: 30 (unchanged).
- SHELL + Scope + Sandbox subsets green within the floor.

## 6. Closure (B-1a, actual)

- Static: 34 orchestrator / 0 arena (33 + `runtime.evidence_v1` via runtime init).
- Loaded: 53 / 0 arena (+`evidence_v1` via runtime init, +`evidence_store` via
  exec init — neither on the episode execution path).
- VERDICTS: STATIC_ARENA_FREE=True, EPISODE_ARENA_FREE=True.

## 7. Invariants confirmed

- One PDP (no broker change); one Runtime; one loop; STAGE_ORDER 10/10 pinned;
  PEP sole enforcement; exec/ file-primitive ownership (store lives there;
  records module has zero file/network/subprocess imports); no Arena Runtime
  dependency; no second evidence/receipt authority (store adjudicates nothing);
  SHELL/Scope/Sandbox untouched.

## 8. Later-phase boundary (NOT implemented)

No belief writes, no Assertion→Observation→Finding promotion, no Refuted
status, no trust recalculation, no contradiction resolution, no replan
triggering, no Student learning, no Teacher, no Arena/Decepticon/Docker,
no graph reasoning, no falsification traversal, no schema registry, no DB.

## 9. C-1 rider (carried forward)

### Fresh machine-captured Scope 19-test transcript (this session)

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

============================== 19 passed in 0.28s ==============================
```

One-line honest explanation of the previous [81%] anomaly: the earlier
transmitted Scope transcript was hand-reassembled with non-monotonic progress
percentages (a packet transcription error, not a test-result issue); the
machine-captured rerun above at the same HEAD shows monotonic percentages
and 19/19 pass.

Full-floor summary carried forward: 316 passed, 32 warnings (at §14.3 close).

## 10. Remaining non-blocking items

- Store cap 10000 with fail-closed StoreFull (no rotation yet — explicit).
- Artifact bytes referenced, never embedded (large-content retrieval is later).
- `to_legacy_evidence` maps v1 kinds into legacy `evidence_type` strings;
  legacy `collected_by` carries the v1 action ref (provenance, not authority).
- Per-record wall-clock `observed_at` defaults to `time.time()` (provenance
  only; excluded from identity by design).
