# P4.2 §15.2 Scope Model — Evidence Package

**Starting HEAD:** `a3107c1167c13634ff7cae86a90e620af6b85c5b` (P4.1-accepted)
**Final HEAD:** `89bf876f7a6c51ad1494cfa94af2dbb35dcb87bf`
**Branch:** `weld-sub10-evidence`
**Working tree at capture:** clean except this evidence directory (committed below)

## 1. §15.2 requirement mapping

Roadmap P4.2 (one sentence): *"Represent allowed targets/resources/action classes declaratively and validate containment."*

| Requirement | Existing | Missing | Change | Evidence |
|---|---|---|---|---|
| Allowed targets declarative | `targets` tuple + `_target_matches` | Rules-as-data + deciding-rule introspection | `ScopeRule` + `ScopeV0.rules()` | `test_rules_expose_declared_containment` |
| Allowed resources declarative | Target envelope (hostnames/IPs/CIDRs/fixture keys) | Explicit envelope mapping | Documented: targets ARE the resource envelope; no parallel dimension (second-evaluator risk refused) | mapping test via rules() origins |
| Allowed action classes declarative | `allowed_*`/`prohibited_*` tuples | Same introspection gap | Same `rules()` surface (deny rules carry effect=deny) | prohibited-wins test naming the rule |
| Validate containment | `covers()` → (bool, str) | Machine-readable verdict (deciding dimension + rule) | `ScopeContainment` + `ScopeV0.check()`; `covers()` delegates identically | 11-case equivalence test + per-dimension tests |

## 2. Scope model design

- `ScopeRule{dimension, pattern, effect, origin, index}` — frozen data, no evaluation, no authority.
- `ScopeContainment{allowed, dimension, matched_rule, reason}` — frozen verdict; `reason` strings byte-identical to proven covers().
- `ScopeV0.rules()` — declaration order: targets(allow) → prohibited actions(deny) → allowed actions → prohibited caps(deny) → allowed caps → impact cap.
- `ScopeV0.check()` — THE single canonical evaluator (exact/CIDR/wildcard; prohibited-wins; empty-allowlist-deny; numeric cap; first-failure-decides). `covers()` is a thin view over it.
- Containment answers (§8): target=exact/CIDR/wildcard allowlist, missing→deny; action/capability=prohibited-wins then allowlist, empty→deny; impact=strict-greater denies, malformed→deny; conflicts rejected at construction; evaluation order target→action→capability→impact.

## 3. Changed files (exact)

- `src/orchestrator/runtime/scope.py` (+164/−22: types + rules/check + delegation only)
- `tests/test_p42_scope_containment.py` (NEW, 14 tests)
- `evidence/p42_scope/` (this package)

## 4. Verification

- P4.2 targeted (14 new + 19 scope): 33 passed — `p42_targeted_transcript.txt`
- guardrails: 30 passed — `p42_guardrails_transcript.txt`
- full floor: **417 passed / 0 failed / 0 skipped / 0 xfail / 33 warnings** — `p42_floor_transcript.txt` (403 + 14; warnings unchanged)
- static closure: 35/0; loaded: 54/0 (unchanged — no new module)
- architecture: 1 Runtime / 1 PDP / 1 PEP / 10 stages (probe green); STAGE_ORDER untouched
- security review: Broker sole PDP (unchanged code path); Scope constraint-only (no allow/authorize/decide methods on Scope/Rule/Containment — asserted); fail-closed preserved (19/19 + malformed/empty/boundary tests); F1 binding untouched; evaluated scope is the mission-bound scope threaded by run_episode (unchanged threading); no substitution path added (frozen dataclass, no setters); no bypass (broker-stage conjunction unchanged); G3/P4.1 guarantees intact (95-suite + 18 P4.1 tests green within floor)

## 5. Status classification

- P4.2: PROVEN (NOT ACCEPTED — governance adjudication pending)
- G4: NOT YET ACCEPTED
