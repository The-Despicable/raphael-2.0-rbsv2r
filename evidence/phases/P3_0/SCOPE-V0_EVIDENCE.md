# §14.3 Scope v0 — Implementation Evidence (EVIDENCE READY, NOT ACCEPTED)

Canonical numbering note: the Scope v0 section is §14.3. In-tree source
comments and runtime reason/error strings still carry the working label
"§14.6" (predates the canonical correction); executable behavior does not
depend on the label (no code parses it; tests assert only the "scope"
substring). Renumbering those strings is deferred to a future authorized
pass. Commit messages `85c3bc90`/`0f060369` are historical.

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

## Remaining limitations (§14.4+ explicitly not started)

- Scope derivation is manual (caller constructs ScopeV0); no mission-spec parser.
- Planner still emits the hardcoded walking-skeleton request; scope constrains it
  but does not yet steer candidate generation (Student filtering is legacy D8 path).
- No target-declaration discovery; `run_episode` view target still hardcoded
- max_impact enforcement consumes the broker call's 0.0 estimate; per-capability
  impact budgets are §14.7 WorldModel work.
  (SUPERSEDED by the Option-B remediation record below: covers() now enforces
  the cap against the broker-decided estimate; per-capability/cumulative
  budgets remain §14.6 WorldModel work per canonical numbering.)

## Option-B remediation record (max_impact enforcement correction)

Baseline for this correction: `0f060369` (floor 313 / 0 / 0 / 0, guardrails 30).

### False-claim correction (not hidden)

- The original evidence (line "impact above max denies") claimed `covers()`
  enforced the impact cap.
- Pre-conversion source audit showed the comparison was absent: `covers()`
  parsed `impact_estimate` to float, rejected only malformed input, then
  unconditionally returned True. No `impact > max_impact` check existed
  anywhere on the Scope path.
- GLM authorized minimal Option-B correction. The comparison now exists.

### Exact covers() comparison (commit `c4ff633`)

```python
        if impact > self.max_impact:
            return False, "Scope v0: impact exceeds declared max"
```

Semantics: strictly greater denies; exactly equal allows; malformed input
preserves the pre-existing fail-closed "malformed impact estimate" denial.
No other `covers()` ordering/semantics altered.

### Stage-level estimate handling

Preflight finding: no genuine per-request impact estimate exists anywhere in
the canonical path (planner `ActionRequest` carries none; the broker call
hardcoded `impact_estimate=0.0`). Selecting a conservative default from
existing information was mechanical, not architectural — no escalation needed.

Resolution (no new estimator, no broker modification, no new architecture):
`stage_broker` threads the exact estimate the Broker decided on —
`receipt.metadata["impact_estimate"]`, written by `propose_action` itself —
into `covers()`. Absent estimate fails closed
(`"Scope v0: no impact estimate available"`) rather than silently passing 0.0.
Existing behavior preserved: decided 0.0 vs default max 0.0 allows by equality.
No per-capability or cumulative impact system introduced.

### Tests added (existing tests untouched)

- `test_over_max_impact_denied`: estimate 0.5 vs max 0.0 → `(False, "Scope v0:
  impact exceeds declared max")`.
- `test_exact_max_impact_allowed`: 0.0 vs 0.0 and 1.0 vs 1.0 allow; 1.5 vs 1.0
  denies (locks strict-greater semantics).
- `test_stage_fails_closed_without_impact_estimate`: stub-broker receipt with
  empty metadata → stage fails closed with "no impact estimate available"
  (strictly necessary to verify the stage-level resolution).

### Verification

- `tests/test_scope_v0.py`: 19 passed.
- Full floor (actual): **316 passed / 0 failed / 0 skipped / 0 xfail**.
- Guardrails collected: 30 (unchanged).
- Closure (B-1a): static 32 orchestrator / 0 arena; loaded 51 / 0 arena;
  STATIC_ARENA_FREE=True, EPISODE_ARENA_FREE=True. SHELL tests green.
- R-W2: no existing test edited or removed (3 tests appended only).

### Bootstrap-v0 reconciliation (adjudicated wording)

"Roadmap declares bootstrap-v0 superseded-by Scope v0 at P3; as-implemented,
Scope v0 constrains post-decision but bootstrap-v0 still feeds PDP inputs —
retirement per CONV-1/G3 criterion (policy.py decision-source removal) remains
open and is re-dated to P4."

Re-dating does not weaken current enforcement: both bootstrap-v0's allowlist
(empty-list-deny in `BrokerPolicy.is_*_allowed`) and the Scope conjunction
deny by default. The open issue is the PDP decision-source artifact, not
whether anything is enforced.

### §14.10 MVP denial set (records only; §14.10 not started)

Future demonstration denial set: out-of-scope target; unlisted capability;
prohibited action; over-cap impact.
