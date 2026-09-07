# P4.4 §15 Receipt Persistence — Evidence Package

**Starting HEAD:** `e667a207673c47db1bf2406eb82c3828cfc8d0e7` (P4.3-accepted)
**Final HEAD:** `5ba213ac0529aea8caad13a5f078b4d9c035a848`
**Branch:** `weld-sub10-evidence`
**Working tree at capture:** clean except this evidence directory (committed below)

## 1. §15 P4.4 requirement mapping

Roadmap P4.4: *"Move from ephemeral/in-memory receipts to durable storage appropriate for local operation"* + survives restart, integrity-checkable, traceable to mission/action, deterministic serialization.

| Requirement | Existing substrate | Missing | Change | Evidence |
|---|---|---|---|---|
| Durable local storage | `EvidenceStore` (EvidenceRecord-only) + ephemeral broker `_receipt_store` | Receipt-durable store | NEW `exec/receipt_store.py` `ReceiptStore` (JSONL, §14.5 fail-closed conventions) | 24 new tests |
| Survives restart | In-memory only | Cross-process proof | `tests/_p44_restart_helper.py` write/read in separate OS processes | `test_receipts_survive_process_restart` (real subprocess boundary) |
| Integrity-checkable | `verify_integrity()` in-memory | Load-time verification + mission binding | Receipt-hash check + `record_hash` envelope binding on append/load | 6-dim + id + hash + binding tamper refusals |
| Traceable mission/action | P4.3 context (in-memory) | Persisted binding | Envelope `{receipt, mission_id, mission_digest, scope_hash}` | traceability + masquerade tests |
| Deterministic serialization | Insertion-ordered to_dict | Canonical bytes | sort_keys/compact/ensure_ascii; tuple→list normalization; verbatim values (hash is type-sensitive — a coercion bug was found and fixed during development) | byte-identity + round-trip tests |

## 2. Mechanism

- `ReceiptStore(path, max_records=10000)`: `append(receipt, mission_id, mission_digest, scope_hash)`, `get(action_id)`, `__len__`.
- Envelope v1: `{schema_version, action_id, mission_id, mission_digest, scope_hash, receipt, record_hash}`.
- Fail-closed: missing file = empty store; malformed/truncated/hash/binding/schema failures refuse whole load; dup-same idempotent; dup-conflict/oversize/over-cap rejected; fsync on write.
- Authority: durable REPRESENTATION only. `_check_receipt` consults only the live Broker store — proven by `test_persisted_receipt_cannot_authorize` (fresh broker + disk-loaded receipt → SandboxNotAuthorized).

## 3. Changed files (exact)

- `src/orchestrator/exec/receipt_store.py` (NEW)
- `tests/_p44_restart_helper.py` (NEW, subprocess-only, never imported)
- `tests/test_p44_receipt_persistence.py` (NEW, 24 tests)
- `evidence/p44_persistence/` (this package)

Zero modifications to existing source files.

## 4. Verification

- P4.4 targeted: 24 passed — `p44_targeted_transcript.txt`
- Regression (P4.1 18 + P4.2 14 + P4.3 12 + scope 19 + guardrails 30 + sandbox 30 + demo 3 + probes 13): 139 passed — `p44_regression_transcript.txt`
- Full floor: **453 passed / 0 failed / 0 skipped / 0 xfail / 33 warnings** — `p44_floor_transcript.txt` (429 + 24; warnings unchanged)
- Static closure: 35/0; loaded: 54/0 (unchanged — store not in runtime closure by design)
- Architecture: 1 Runtime / 1 PDP / 1 PEP / 10 stages (probe green); STAGE_ORDER untouched

## 5. Status classification

- P4.4: PROVEN (NOT ACCEPTED — governance adjudication pending)
- G4: NOT YET ACCEPTED
