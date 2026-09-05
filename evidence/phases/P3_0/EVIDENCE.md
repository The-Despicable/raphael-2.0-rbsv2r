# RAPHAEL P3.0 — Records Baseline (G3 Entry)

| Field | Value |
|---|---|
| Phase | P3.0 (records baseline before first implementation commit) |
| Gate | G3 entry (AUTHORIZED WITH CONDITIONS) |
| Repository HEAD | `9028c57829c140d41705665a8e60f96230ea4133` |
| Branch | `main` (ahead of `origin/main` by 28) |
| Commits since canonical | 28 (per fresh `git rev-list --count 7272880f7..HEAD`) |
| Implementation commits in P3.0 | 0 (records-only) |
| Timestamp | 2026-09-05 |
| Author | RAPHAEL P3.0 Audit <p3.0-audit@raphael.local> |

## 1. G2 Closure Ruling

Per the GLM G3 entry adjudication: **G2 PASS. P2 complete.** Two records defects were rejected (truncation narrative; four inconsistent commit counts) and carried forward into G3-EN-1, not accepted into the record. The code, tests, and architecture of P2 are fully trusted.

## 2. Fresh Git State (G3-EN-1)

Per G3-EN-1: "replace all four commit counts with one number derived from a fresh `git rev-list --count 7272880f7..HEAD` transcript; regenerate the stale git-log transcript and branch line."

```
$ git rev-parse HEAD
9028c57829c140d41705665a8e60f96230ea4133

$ git rev-list --count 7272880f7..HEAD
28

$ git status --short --branch
## main...origin/main [ahead 28]
```

**Authoritative commit count: 28.**

**Anomaly retraction (per GLM §1.1):** The previously offered explanation that the prior string `445f21a87cc2ce14e9e6c80e0fd7d77c4d7e9c5e1` was "a truncated representation of the REAL commit `445f21a878d490804930f4287d6d07f672d469bd`" is **rejected**. The real commit begins `445f21a878…`; the prior string begins `445f21a87c…`. The strings diverge at position 10. The prior string is not a truncation of the real commit — it shares only a nine-character prefix. Additionally, the two previously conflicting HEAD claims (`445f21a87cc2ce…` and `2c81c58bcc2ce14…`) share a ~30-character common tail (`c2ce14e9e6c80e0fd7d77c4d7e9c5e1`) that appears in **neither** real commit. The truthful reconciliation is that at least one previously reported HEAD string corresponded to no real commit. Whether the cause was transmission garbling or construction error is not adjudicated; what is adjudicated is that the "truncation" explanation cannot be true as transmitted and does not enter the accepted record.

**Current git log (28 commits since canonical `7272880f7`):**

```
$ git log --oneline 7272880f7..HEAD
9028c5782 G2 final HEAD reconciliation: f8abe9fa is authoritative CURRENT HEAD
f8abe9fa9 G2 provenance cleanup: correct commit count 23->24 and stale current-tip wording
ba0f965cb G2 FR-4 final: correct authoritative HEAD to b48e8ef59
b48e8ef59 G2-FR final records correction: G2-FR-2, G2-FR-3, G2-FR-4, G2-FR-5
85ee1f873 G2-FR-1..FR-5: records-only corrections (no code/test/architecture changes)
445f21a87 G2-C4 + G2-C5: corrected evidence package (full-G2 deliverable)
2c81c58bc G2-C3: convergence tickets for P2->P3 (no migration performed)
c7ab7eada G2-C1 + G2-C2: canonical CLI wiring + fail-closed proof
4c5a55fe0 P2.1: evidence package per v4 §25 schema (full-G2 deliverable)
b8a581ad6 P2.1: RaphaelRuntime walking skeleton (born-gated, v4 §13.3)
d2674ace5 G2 RC: final evidence index — RC-A..F complete, GLM RC-B applied
4b5c17354 RC-B GLM: evidence for GLM section 4 disposition implementation
03385c311 RC-B GLM disposition: dependency inversion via brain-owned port
5c90cdbfb RC-B escalation: analysis of apply_belief_transition dependency
deed0383c RC-F: untrack 14 episodes.jsonl test artifacts (keep on disk)
fa25ad715 G2 RC: evidence package index — RC-A..F remediation complete
f1756eb3c RC-F: bookkeeping/provenance cleanup
b63f0bde5 RC-E: evidence for bootstrap-v0 + ADR-012 (documentation only)
02c3b9c01 RC-D: correct guardrail scope to P2 jurisdiction (P9 retains full sweep)
0743d0a7e RC-C: complete deprecation marker coverage + authoritative registry
920cdf253 RC-B: sever brain→arena runtime imports (partial; 1 HALT/ESCALATE)
718099475 RC-A: remove canonical adaptive_brain import from brain/__init__.py
5c66b061e P2.0: evidence package per v4 §25 schema (AM-8 mandatory, global)
42f0d13fc P2.0: bootstrap-v0 named/versioned policy artifact (v4.1 AM-13.2)
982079425 P2.0: 5 guardrail tests per v4 §23 test registry + v4.1 AM-13.3
ecf6745d4 P2.0: deprecation markers for 14 UNREACHABLE_FROM_CANONICAL subprocess sites (v4 P1.2)
b3f32f5ae P2.0: transcribe ADR-001..010 from v4 §12.2 + ADR-011 addendum + ADR-012 seam ratification
a68c129a8 P1: canonical runtime packaging + seam work (per v4 §12 + v4.1 AM-4/AM-7/AM-13.3)
```

**Branch line (regenerated):** `## main...origin/main [ahead 28]`

## 3. CONV Tickets Exhibition (G3-EN-2)

Per G3-EN-2: "exhibit CONVERGENCE_TICKETS.md with per-ticket owner, target phase, and G3 verification criterion; name CONV-4's subject."

### CONV-1: BootstrapPolicy → single canonical PDP at P3

- **Ticket subject:** Retire `BootstrapPolicy` (P2 placeholder PDP in `src/orchestrator/runtime/policy.py`) and route the Runtime's `stage_broker` through the brain's `CapabilityBroker` (`src/orchestrator/brain/capability_broker.py`) as the single canonical Policy Decision Point (PDP).
- **Owner:** GLM (gate reviewer) + implementation lane
- **Target phase:** P3 (when Scope v0 lands per v4 §14.3)
- **G3 verification criterion:** At G3 review, the gate reviewer must confirm: (1) `src/orchestrator/runtime/policy.py` no longer exists as the decision source (file deleted or reduced to a re-export shim with no policy logic); (2) `stage_broker` in `src/orchestrator/runtime/stages.py` invokes `CapabilityBroker.propose_action()` (or equivalent brain-owned PDP method) — not a local policy; (3) `CapabilityBroker` is the sole PDP reachable from the Runtime's transitive closure. No second PDP exists; (4) Scope v0 is committed and applied. `bootstrap-v0.json` is retired.

### CONV-2: Runtime PEP stage → exec/ at P3

- **Ticket subject:** Move the Runtime's PEP enforcement (`stage_pep` in `src/orchestrator/runtime/stages.py`) into the brain-owned `src/orchestrator/exec/` package, so that process/network/file primitives are confined to `exec/` per v4 L6.
- **Owner:** GLM (gate reviewer) + implementation lane
- **Target phase:** P3
- **G3 verification criterion:** At G3 review, the gate reviewer must confirm: (1) `src/orchestrator/exec/` directory exists and is the sole package permitted to hold process/network/file primitives; (2) `stage_pep` in the Runtime delegates to an exec/-owned capability — not to a `Runtime/safe_proving_capability.py` module; (3) the Runtime's transitive import closure does not include any `orchestrator/runtime/safe_proving_capability` module (it has been relocated); (4) No `subprocess`, `os.system`, `socket.*`, or `urllib.*` import exists outside `src/orchestrator/exec/`. INV-1 goes live.

### CONV-3: safe_proving_capability.py → capabilities namespace / approved ADR-011 exception, with P3 convergence

- **Ticket subject:** Move `SafeProvingCapability` from `src/orchestrator/runtime/safe_proving_capability.py` to `src/orchestrator/capabilities/` (or a new approved namespace) per ADR-011 arena-clause addendum.
- **Owner:** GLM (gate reviewer) + implementation lane
- **Target phase:** P3 (= P3.5)
- **G3 verification criterion:** At G3 review, the gate reviewer must confirm: (1) `src/orchestrator/runtime/safe_proving_capability.py` no longer exists (file deleted or reduced to a re-export shim); (2) `SafeProvingCapability` lives under `src/orchestrator/capabilities/` (or an ADR-approved location); (3) An ADR exists that approves the move (per v4.1 amendment discipline); (4) The Runtime's `stage_pep` imports `SafeProvingCapability` from its new location. Constructor gating active.

### CONV-4: no second PDP or orphaned scaffolding survives to G3 (NAMED per G3-EN-2)

- **Ticket subject:** At G3 (MVP gate), verify that there is exactly one PDP, exactly one PEP, and no orphaned P2 scaffolding.
- **Owner:** GLM (gate reviewer)
- **Target phase:** G3
- **G3 verification criterion:** At G3 review, the gate reviewer must confirm: (1) Exactly one PDP exists: `CapabilityBroker` in `src/orchestrator/brain/capability_broker.py`. No `BootstrapPolicy`, no other policy module reachable from Runtime; (2) Exactly one PEP exists: `src/orchestrator/exec/`. No `Runtime/safe_proving_capability.py` PEP emulation; (3) The `src/orchestrator/runtime/` directory contains only: `__init__.py`, `loop.py` (thin sequencer), `types.py` (contracts), `stages.py` (stage handlers). No policy module, no capability module; (4) No P2 walking-skeleton scaffolding survives (no `BootstrapPolicy` as decision source, no in-process dict fixtures, no `PYTHONPATH=src` test-only paths). The P9 sweep ticket (G3-EN-3) documents the legacy-repository sweep that re-establishes the P9-scope tests removed during RC-D (chains.tool_registry, sword.phase_0_recon, orchestrator.api.*).

## 4. P9 Legacy-Sweep Ticket (G3-EN-3)

Per G3-EN-3: "register now the P9 re-establishment of the full-repository legacy sweep (the removed chains assertion's contractual home per v4 §23)."

**Ticket ID:** P9-SWEEP-1
**Subject:** At P9, re-establish the full-repository legacy-sweep test that was removed during RC-D (commit `02c3b9c01`). The removed test `test_no_chains_tool_registry_import` checked P9-scope items: `orchestrator/api/main.py` and `orchestrator/api/tools.py` importing `orchestrator.chains.tool_registry`, and `sword/pipeline.py` importing `sword.phase_0_recon`. The deprecation markers for these sites were added in P1 (commit `ecf6745d4`). The markers are in the authoritative registry at `evidence/phases/G2_RC/deprecation_marker_registry.md` and are verified by the current P2 deprecated-import guardrail.
**Owner:** GLM (gate reviewer) + implementation lane
**Target phase:** P9
**Verification criterion:** At P9 review, the gate reviewer must confirm: (1) The full-repository legacy sweep test is re-added; (2) The test checks `orchestrator/api/* → chains.tool_registry` and `sword/pipeline.py → sword.phase_0_recon` imports; (3) All deprecation markers in the authoritative registry are present; (4) P2-DEPRECATED-MODULES includes `orchestrator.brain.adaptive_brain` (already verified at P3.0). Verified at P3.0: `adaptive_brain` is in the authoritative registry (line 38 of `evidence/phases/G2_RC/deprecation_marker_registry.md`) and in `P2_DEPRECATED_MODULES` set in `tests/test_p2_guardrail_deprecated_import.py`. The original standalone `test_adaptive_brain_not_imported_by_canonical` was folded into the registry-consistency test `test_p2_registry_matches_guardrail`; this consolidation is acceptable per the G3-EN-1 note: "the adaptive_brain-specific test folded into the registry test — acceptable only if the registry includes `adaptive_brain`, verified here."

## 5. Invariants Continuously Enforced (from GLM §5)

1. **FLOOR = 275**, monotonic; zero skips, zero xfails, zero weakening
2. **All 19 P2 guardrails green continuously**
3. **Arena-free closure**, both instruments (static transitive + runtime loaded-module)
4. **INV-2 decision linkage** unbroken through the CONV-1 swap
5. **Fail-closed preserved and re-proven** against the real Broker
6. **Exactly one PDP** on the canonical path after CONV-1
7. **INV-1 live** from `exec/` creation
8. `RAPHAEL_USE_LEGACY=1` remains the sole legacy reach; one cognitive loop; no new stages; no roadmap modification

## 6. Floor Verification (P3.0, no implementation work)

**Command:** `PYTHONPATH=src python3 -m pytest tests/ --no-header -q`

**Result:** 275 passed, 0 failed, 31 warnings, ~7s

| Metric | FLOOR(P0) | Post-P2.0 | Post-G2-RC | Post-P2.1 | Post-G2-C1+C2 | Post-G2-FR | Post-P3.0 |
|---|---|---|---|---|---|---|---|
| Passed | 239 | 239 | 258 | 266 | 275 | 275 | **275** |
| Failed | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| Warnings | 26-27 | 26 | 31 | 31 | 31 | 31 | **31** |

**Breakdown:** 239 legacy + 8 P2.1 walking-skeleton + 9 G2-C2 fail-closed + 19 P2 guardrails = **275**.

**Guardrail status (P3.0):**

```
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_*.py --no-header -q
19 passed, 0 failed, 0 skipped
```

**deprecated-import guardrail (includes adaptive_brain):**

```
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_deprecated_import.py -v
tests/test_p2_guardrail_deprecated_import.py::test_no_canonical_module_imports_p2_deprecated PASSED
tests/test_p2_guardrail_deprecated_import.py::test_p2_registry_matches_guardrail PASSED
2 passed
```

**FLOOR = 275. Zero skips. Zero xfails. Zero weakening. 19 P2 guardrails green.**

## 7. Scope Statement (P3.0)

**P3.0 scope: records baseline only.** No source code modified. No tests modified. No architecture amendments. No P3 implementation work. No welds. No organ wiring. No CONV-1. No Runtime redesign. No P5 work.

**Next allowed work (per GLM authorization):** CONV-1 (canonical PDP swap: `stage_broker` calls real brain `CapabilityBroker`; `BootstrapPolicy` retired from decision role; exactly one PDP). CONV-1 is the first implementation work item. No weld may be performed before G3-EN-4 (CONV-1 complete and fail-closed re-proven).

## 8. Changed Files (P3.0)

- `evidence/phases/P3_0/EVIDENCE.md` (NEW: this document)

**Total changes:** 1 new file (records only). Zero source/test/architecture changes.

## 9. Commits

P3.0 is records-only. The next commits will be the CONV-1 implementation, which requires the records baseline to be in place.

**STOP.** Awaiting G3-EN-1/2/3 confirmation before CONV-1.
