# §14.6 Scope v0 — Implementation Evidence (EVIDENCE READY, NOT ACCEPTED)

## Baseline (immutable accepted SHELL state)

- HEAD: `485aacdc02c011dad91ae887ad33b709c7b584c2`, branch `weld-sub10-evidence`
- Verified pre-flight: `git rev-parse HEAD` → `485aacdc0…`, `git status -sb` clean
- Baseline floor (actual run, pre-change): **297 passed / 0 failed / 0 skipped / 0 xfail**
- Guardrails collected (`guardrail` match): 30
- Accepted seams untouched: SUB-14, SUB-13, SUB-10, SHELL (no SHELL file modified)

## Pre-flight findings

Existing scope-related structures found:

1. `BrokerPolicy` (`src/orchestrator/brain/capability_broker.py`): allowed/prohibited
   targets, action types, capabilities + fail-closed `is_*_allowed`. This is the
   PDP's authorization input, NOT a mission boundary — no mission identity, no
   declared-boundary semantics, not derived from MissionContext.
2. `ScopeParser` (`src/orchestrator/brain/scope_parser.py`): HackerOne scope-text
   parser, optional legacy P1 broker input. Not in the canonical Runtime closure;
   not used by any runtime stage. Left untouched.
3. `MissionContext.constraints` (dict): unstructured, never read by any stage.
4. Planner stage builds a hardcoded `ActionRequest(safe_proving_capability,
   <view target>, fixture.inspect)`; broker stage calls
   `propose_action(..., capability="fixture.inspect", method="inspect",
   impact_estimate=0.0)`; PEP stage gates + invokes the exec/ capability.

Proposed canonical location: `src/orchestrator/runtime/scope.py` (pure contract,
stdlib-only, no brain/exec/arena imports).
Integration point: broker stage (`stage_broker`) as a post-allow conjunction +
`run_episode(require_scope=...)` pre-stage gate; scope threaded via
`MissionContext.scope` → `RuntimeContext.scope` → `stage_ctx["scope"]`.
No new Runtime stage required: STAGE_ORDER unchanged (single-cognitive-loop
guardrail preserved); the scope check is an additional conjunct inside the
existing broker stage, not a decision source.

## Scope v0 contract (`ScopeV0`, frozen dataclass)

Fields: `mission_id` (required non-empty), `targets` (required non-empty tuple),
`allowed_action_types` / `prohibited_action_types`,
`allowed_capabilities` / `prohibited_capabilities`, `max_impact >= 0` (default 0.0).

Validation (deterministic, fail-closed, at construction):
missing/blank mission_id → ScopeError; empty targets → ScopeError; malformed
CIDR / non-string / blank entries → ScopeError; allowed∩prohibited overlap →
ScopeError; negative/non-numeric max_impact → ScopeError; `from_dict` unknown
keys / wrong version / missing required → ScopeError.

`covers(target, action_type, capability, impact_estimate=0.0)` → (bool, reason):
target by omission-deny (exact/CIDR/wildcard match); prohibited action/capability
deny; empty allow-list denies; impact above max denies. Pure function.
Stable serialization: `to_dict` (fixed key order) / strict `from_dict` /
`scope_hash` (sha256 of canonical JSON).

## Implementation commit

- Commit: `85c3bc90856e601130e4f75b1547cebc40f457b1`
  "§14.6 Scope v0: immutable mission-boundary contract + broker-stage
  conjunction + 16 tests"
- Files: `src/orchestrator/runtime/scope.py` (new),
  `src/orchestrator/runtime/types.py` (+scope on MissionContext/RuntimeContext),
  `src/orchestrator/runtime/loop.py` (thread scope; require_scope pre-stage gate),
  `src/orchestrator/runtime/stages.py` (broker-stage scope conjunction),
  `src/orchestrator/runtime/__init__.py` (export ScopeV0, ScopeError),
  `tests/test_scope_v0.py` (new, 16 tests)
- No existing test edited → R-W2: none required. No SHELL file touched.

## Integration path

MissionContext(scope=ScopeV0(...)) → run_episode validates type (non-ScopeV0 →
fail-closed `final_stage="scope"`, zero iterations) → RuntimeContext.scope →
stage_ctx["scope"] → stage_broker: broker allow AND scope.covers(...) else
fail-closed `Stage 'broker' failed: §14.6 Scope v0 fail-closed: ...`.
Legacy path (scope=None, require_scope=False) byte-identical behavior.

## Test results

- New: `tests/test_scope_v0.py` → **16 passed** (8 fail-closed/malformed/out-of-scope
  negatives incl. missing-scope-required, impostor-scope, empty targets, bad CIDR,
  overlap, negative impact, strict from_dict; out-of-scope target + unlisted
  capability at runtime; prohibited action/capability; in-scope success with PEP
  reached; scope-does-not-bypass-broker-denial; determinism; serialization
  stability; frozen immutability + defensive copy; stdlib-only AST purity;
  no-WorldModel/Broker surface).
- SHELL/institutional regression: shell_closed (4) + g3_en5_organ_wiring (11) +
  inv1 (5) → 20 passed.
- Full floor (actual, post-change): **313 passed / 0 failed / 0 skipped / 0 xfail**
  (297 + 16, monotonic, no deletions/weakenings).
- Guardrails collected: 30 (unchanged; scope tests are additive, not guardrail-named).

## Anti-bypass results

- scope.py AST import surface: {fnmatch, hashlib, ipaddress, json, dataclasses,
  typing, __future__} — stdlib only (test-enforced).
- No `execute/inspect/authorize/approve/emit/run/record_authorization/propose_action`
  definitions in ScopeV0 (test-enforced).
- No subprocess/network/file primitives; no authorization issuance; no Broker/PEP
  replacement; no WorldModel writes; no second loop/stage/path (STAGE_ORDER
  unchanged, verified by existing single-loop guardrail).
- `kali_tools_client` occurrences in B-1a closure listing: 0.

## Closure results (B-1a probe, post-change)

- STATIC: 32 orchestrator / 0 arena (31 + new scope.py, delta exactly the weld file)
- LOADED (post-episode walk): 51 / 0 arena (50 + scope.py)
- VERDICTS: STATIC_ARENA_FREE=True, EPISODE_ARENA_FREE=True

## Remaining limitations (§14.7+ explicitly not started)

- Scope derivation is manual (caller constructs ScopeV0); no mission-spec parser.
- Planner still emits the hardcoded walking-skeleton request; scope constrains it
  but does not yet steer candidate generation (Student filtering is legacy D8 path).
- No target-declaration discovery; `run_episode` view target still hardcoded
  `system_info.name` (scope covers it when declared).
- max_impact enforcement consumes the broker call's 0.0 estimate; per-capability
  impact budgets are §14.7 WorldModel work.
