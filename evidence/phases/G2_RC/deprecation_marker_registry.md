# RC-C: Authoritative Deprecation Marker Registry

**Phase:** G2 RC-C
**Status:** Accepted (per v4 §12.2 P1.2)
**Source:** v4 master roadmap §12.2 P1.2 + v4.1 AM-5 (pattern-provenance)

## Single authoritative list

This registry is the **single source of truth** for deprecated modules in the
RAPHAEL codebase. It is shared by:
- P2 guardrail tests (`tests/test_p2_guardrail_*.py`)
- P9 cleanup inventory (deferred to P9)
- Architecture documentation

### Markers added in P1 (commit ecf6745d4, 14 sites)

| Path ID | File | Path | Status | Disposition |
|---|---|---|---|---|
| SUB-01 | weaponizer_engine.py | `src/orchestrator/weaponizer/weaponizer_engine.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-02 | weaponizer_engine.py | `src/orchestrator/weaponizer/weaponizer_engine.py:9-16` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-03 | weaponizer_engine.py | `src/orchestrator/weaponizer/weaponizer_engine.py:17-24` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-04 | chains/tool_registry.py | `src/orchestrator/chains/tool_registry.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-05 | c2/sliver_backend.py | `src/orchestrator/c2/sliver_backend.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-06 | c2/sliver_backend.py | `src/orchestrator/c2/sliver_backend.py:9-16` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-07 | c2/implant_builder.py | `src/orchestrator/c2/implant_builder.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-08 | c2/implant_builder.py | `src/orchestrator/c2/implant_builder.py:9-16` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-09 | c2/implant_builder.py | `src/orchestrator/c2/implant_builder.py:17-24` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-11 | recon-pipeline/main.py | `src/recon-pipeline/main.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-12 | agent/modules/executor.py | `src/agent/modules/executor.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-15 | sword/phase_0_recon.py | `src/sword/phase_0_recon.py:1-8` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-16 | sword/phase_0_recon.py | `src/sword/phase_0_recon.py:9-16` | UNREACHABLE_FROM_CANONICAL | P9.1 |
| SUB-17 | sword/phase_0_recon.py | `src/sword/phase_0_recon.py:17-24` | UNREACHABLE_FROM_CANONICAL | P9.1 |

### Markers added in RC-A (commit 718099475)

| Item | File | Path | Status | Disposition |
|---|---|---|---|---|
| AdaptiveBrain | `src/orchestrator/brain/adaptive_brain.py:1-10` | DEPRECATED (removed from brain/__init__.py closure) | P9.1 |

### Markers added in RC-C (this commit)

| Item | File | Path | Status | Disposition |
|---|---|---|---|---|
| NOT_IMPLEMENTED executors (9) | `src/orchestrator/brain/phases/models.py:1-12` | DORMANT COGNITIVE STUBS (v4 INV-15, v4 L17) | P9.1 |
| RaphaelOrganism (Head-1 loop) | `src/raphael/main.py:1-13` | DEPRECATED (v4 L3, v4 P1.2, v4 L1) | P9.1 |

## Marker format (canonical)

Per v4 §12.2 P1.2 and the existing P1 convention:

```python
# --- P1 DEPRECATION MARKER (per v4 section 12.2 P1.2) ---
# <item>: <status> (v4 <reference>).
# <description>.
# <invariants>.
# <disposition>.
# P9 owns deletion. See evidence/phases/G2_RC/RC-C.
# -------------------------------------------------------
```

## Items NOT marked (out of scope)

| Item | Reason |
|---|---|
| `sword/pipeline.py → sword.phase_0_recon` | P9 debt per RC-D (sword/phase_0_recon is marked, but pipeline.py still imports it) |
| `orchestrator/api/* → orchestrator.chains.tool_registry` | P9 debt per RC-D (chains/tool_registry is marked, but api/ still imports it) |
| `adaptive_brain` (module itself) | Marked in RC-A; physical deletion is P9 work |
| 9 NOT_IMPLEMENTED executors in phases/models.py | Marked in RC-C; physical deletion is P9 work |

## Coverage summary

| v4 P1.2 category | Marked | Notes |
|---|---|---|
| legacy Head-1 internal loop | ✅ RaphaelOrganism (raphael/main.py) | |
| AdaptiveBrain | ✅ adaptive_brain.py | Removed from brain/__init__.py closure (RC-A) |
| duplicate planner | N/A | No duplicate planner found in current tree |
| dormant cognitive stubs | ✅ 9 NOT_IMPLEMENTED executors (phases/models.py) | v4 INV-15 |
| alternate entry points | N/A | No alternate entry points found (Arena is a driver, not an entry) |
| NOT_IMPLEMENTED executors | ✅ 9 stubs (phases/models.py) | Same as dormant cognitive stubs |
| 14 UNREACHABLE subprocess sites | ✅ All marked in P1 | P0-verified legacy inventory |

## Guardrail test source-of-truth alignment

The P2 guardrail tests reference this registry:

- `tests/test_p2_guardrail_deprecated_import.py` — `DEPRECATED_MODULES` set
  must be kept in sync with this registry.
- `tests/test_p2_guardrail_single_runtime.py` — legacy module detection
  must be kept in sync with this registry.

Any future deprecation must be added to BOTH this registry AND the
guardrail test sets to maintain single source of truth.

## References

- v4 master roadmap §12.2 P1.2 (deprecation markers)
- v4 master roadmap §24 INV-15 (NOT_IMPLEMENTED stubs)
- v4.1 AM-5 (pattern-provenance ledger, for T3MP3ST)
- evidence/phases/P0/02_execution_inventory/subprocess_sites.md (P0-verified legacy)
- evidence/phases/P1/03_seam_work/SEAM_SITES.md (P1 seam work)
