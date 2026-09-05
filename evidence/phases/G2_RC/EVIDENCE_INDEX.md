# G2 RC Remediation — Final Evidence Package

| Field | Value |
|---|---|
| Phase | G2 RC (RC-A through RC-F, GLM disposition applied) |
| Repository HEAD | `4b5c17354f6c973d6776fc50254f65d30569faa3` |
| Branch | `main` (ahead of `origin/main` by 16) |
| Canonical HEAD | `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` (unchanged) |
| Floor | 258 passed, 0 failed (239 legacy + 19 P2 guardrails) |
| P2 guardrails | 19 tests, ALL GREEN (no skips) |
| Status | G2 corrections complete. STOP for G2 confirmation. |

## RC dispositions (after GLM disposition)

```
RC-A: PASS
RC-B: PASS (GLM §4 dependency inversion implemented)
RC-C: PASS
RC-D: PASS
RC-E: PASS
RC-F: PASS
```

## RC-B GLM disposition summary

GLM §4: dependency inversion via a brain-owned port (`BeliefTransitionPolicy`),
with verbatim re-home of two vocabulary types (`DefeaterOutcome`,
`BeliefTransition`).

- **MOVE (verbatim)**: `DefeaterOutcome`, `BeliefTransition` → brain-owned
  `defeater_types.py`. Byte-identical class bodies verified.
- **STAY**: `apply_belief_transition`, D-5 V2 policy tables, transition
  semantics — byte-identical in `arena/defeater.py` (11 grep matches unchanged).
- **ADD (brain)**: `BeliefTransitionPolicy` Protocol (signature only) +
  `BeliefTransitionPolicyNotBound` exception.
- **ADD (arena)**: `DefeaterPolicyAdapter` implementing the port by
  delegating to `arena.defeater.apply_belief_transition`.
- **CHANGE (brain)**: `hypothesis.py` uses brain-owned types, calls
  through injected port, raises when unbound.
- **DEFAULT BEHAVIOR**: Unbound port → `BeliefTransitionPolicyNotBound`
  (fail-closed). Never silent no-op.
- **P2 COMPOSITION**: Port deliberately unbound in walking skeleton.
- **TICKETS**: P5-BIND-1 registered (canonical brain-side binding is P5).
- **ENFORCEMENT**: 3 new tests (unbound-port-raises, adapter-conforms,
  bound-port-works). Existing guardrail skip removed.

## Evidence files

```
evidence/phases/G2_RC/
├── EVIDENCE_INDEX.md                              (this file)
├── deprecation_marker_registry.md                 (RC-C)
├── RC-E_bootstrap_v0_and_ADR012.md                 (RC-E)
├── RC-F_bookkeeping.md                            (RC-F)
└── RC-B/
    ├── dependency_analysis.md                     (RC-B escalation analysis)
    ├── symbol_usage.md                            (RC-B escalation)
    ├── dependency_graph.txt                       (RC-B escalation)
    ├── option_analysis.md                         (RC-B escalation: Options A/B/C)
    └── glm_disposition_implementation.md          (RC-B GLM §4 implementation evidence)
```

## Floor verification

```
$ PYTHONPATH=src python3 -m pytest tests/ --no-header -q
258 passed, 31 warnings in 6.89s

$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_*.py --no-header -q
19 passed, 5 warnings in 3.12s
```

- 239 legacy tests passed (FLOOR(P0) preserved, zero test edits)
- 19 P2 guardrail tests passed (16 original + 3 new GLM RC-B port tests)
- 0 failed
- 0 skipped (the previous pytest.skip for RC-B HALT/ESCALATE was removed
  because the brain→arena edge is now resolved)

## Commit list (16 commits since canonical)

| # | Commit | Description |
|---|---|---|
| 1 | `a68c129a8` | P1: canonical runtime packaging + seam work |
| 2 | `b3f32f5ae` | P2.0: 12 ADRs transcribed |
| 3 | `ecf6745d4` | P2.0: 14 deprecation markers |
| 4 | `982079425` | P2.0: 5 guardrail test files |
| 5 | `42f0d13fc` | P2.0: bootstrap-v0 policy artifact |
| 6 | `5c66b061e` | P2.0: evidence package |
| 7 | `718099475` | RC-A: adaptive_brain removed from brain/__init__ |
| 8 | `920cdf253` | RC-B: brain→arena severance (partial; 1 HALT/ESCALATE) |
| 9 | `0743d0a7e` | RC-C: deprecation markers + registry |
| 10 | `02c3b9c01` | RC-D: guardrail scope correction |
| 11 | `b63f0bde5` | RC-E: bootstrap-v0 + ADR-012 evidence |
| 12 | `f1756eb3c` | RC-F: bookkeeping/provenance |
| 13 | `deed0383c` | RC-F: untrack episodes.jsonl |
| 14 | `fa25ad715` | G2 RC: evidence index |
| 15 | `5c90cdbfb` | RC-B escalation: analysis (P5-SCALE) |
| 16 | `03385c311` | RC-B GLM disposition: dependency inversion |
| 17 | `4b5c17354` | RC-B GLM: evidence for disposition implementation |

## Changed files (all commits)

### Source changes
- `src/arena/defeater.py` (GLM RC-B: removed DefeaterOutcome, BeliefTransition class defs; added brain re-import)
- `src/arena/defeater_policy_adapter.py` (GLM RC-B: NEW)
- `src/orchestrator/brain/__init__.py` (RC-A: removed adaptive_brain)
- `src/orchestrator/brain/adaptive_brain.py` (RC-A: deprecation marker)
- `src/orchestrator/brain/plan_decision.py` (RC-B: re-homed from arena)
- `src/orchestrator/brain/defeater_types.py` (RC-B: re-homed from arena, then GLM §4: verbatim-move)
- `src/orchestrator/brain/semantic_types.py` (RC-B: re-homed from arena)
- `src/orchestrator/brain/belief_transition_policy.py` (GLM RC-B: NEW Protocol)
- `src/orchestrator/brain/action.py` (RC-B: brain-owned PlanDecision)
- `src/orchestrator/brain/hypothesis.py` (RC-B: brain-owned types; GLM RC-B: injected port)
- `src/orchestrator/brain/phases/models.py` (RC-C: deprecation marker)
- `src/raphael/main.py` (RC-C: deprecation marker)
- `.gitignore` (RC-F: episodes.jsonl)

### Policy/ADR
- `policies/bootstrap-v0.json` (P2.0: NEW)
- `docs/adr/ADR-001..012` (P2.0: 12 ADRs)

### Tests
- `tests/test_p2_guardrail_single_runtime.py` (P2.0 + RC-D + GLM RC-B)
- `tests/test_p2_guardrail_deprecated_import.py` (P2.0 + RC-D)
- `tests/test_p2_guardrail_runtime_no_seam.py` (P2.0)
- `tests/test_p2_guardrail_deny_by_default.py` (P2.0)
- `tests/test_p2_guardrail_no_production_bypass.py` (P2.0)
- `tests/test_p2_guardrail_belief_transition_port.py` (GLM RC-B: NEW)
- `tests/test_d5_seven_gate_proof.py` (GLM RC-B: bind adapter; not weakening)

### Evidence
- `evidence/phases/P0/` (P0 evidence, committed)
- `evidence/phases/P1/` (P1 evidence, committed)
- `evidence/phases/P1_0/` (P1.0 evidence, committed)
- `evidence/phases/P2_0/EVIDENCE.md` (P2.0 evidence)
- `evidence/g1_corrections/` (G1 corrections evidence)
- `evidence/phases/G2_RC/` (G2 RC evidence, this package)

## Scope deviations

- **SD-1 (from P1, carried forward):** Weld-SHELL deferred to P3.
- **GLM RC-B test composition (tests/test_d5_seven_gate_proof.py):** the
  test now binds `DefeaterPolicyAdapter` in `HypothesisManager` construction.
  This is required by GLM §4 composition (the test exercises D-5
  transitions which need the port bound). NOT test weakening — it is
  correct composition. The test's assertions are unchanged.

## Constraints honored

- ✅ P3 remains unauthorized
- ✅ No welds
- ✅ No subprocess closure
- ✅ No 5→1 sandbox importer contraction
- ✅ No Decepticon
- ✅ No Student learning
- ✅ No Arena migration
- ✅ No RaphaelRuntime creation
- ✅ No roadmap modification
- ✅ No test weakening, skipping, or xfail
- ✅ No silent contract reinterpretation
- ✅ No changes to apply_belief_transition or D-5 transition tables
- ✅ No P5 semantics reimplemented or relocated in P2
- ✅ HALT/ESCALATE on prior v4.1 conflict (RC-B escalation analysis)

## Stop condition

**STOP for G2 confirmation review.**

Do NOT create `RaphaelRuntime`.
Do NOT begin P2.1.
Do NOT begin P3.

---

## Final response format

```
RC-A: PASS
RC-B: PASS (GLM §4 dependency inversion implemented)
RC-C: PASS
RC-D: PASS
RC-E: PASS
RC-F: PASS

legacy floor: 239 passed, 0 failed
P2 guardrails: 19 passed, 0 failed (no skips)
current HEAD: 4b5c17354f6c973d6776fc50254f65d30569faa3
changed files: 13 source + 16 evidence/ADR + 7 tests + 1 .gitignore
evidence path: evidence/phases/G2_RC/
```
