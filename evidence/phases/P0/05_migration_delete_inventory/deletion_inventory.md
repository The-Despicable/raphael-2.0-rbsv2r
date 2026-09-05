## P0 — Initial Deletion / Migration Inventory (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Inventory items (no deletions performed in P0)

| Item | Current state | References | Intended disposition | Earliest action phase | Deletion phase | Proof required |
|---|---|---|---|---|---|---|
| `src/orchestrator/runtime/caido_bootstrap.py` | Canonical file (5303 bytes) | Imported in v3+ docs as "Caido integration"; actual callers TBD | **MIGRATE / RENAME** — orphan stash uses the same path with different contents (`loop.py`, `types.py`); reconciliation needed before P1 | P1 start | P9 (verify zero references) | Reconciliation plan + decision |
| `src/orchestrator/runtime/docker_client.py` | Canonical file | Same conflict as above | MIGRATE / RENAME | P1 start | P9 | Same |
| `src/orchestrator/runtime/session_manager.py` | Canonical file | Same conflict | MIGRATE / RENAME | P1 start | P9 | Same |
| `src/agent/` (legacy agent module) | Untouched at canonical; not wired into Arena or CLI | 11 files in `src/agent/modules/` | DELETE LATER (P9) | P9 | P9 | Confirm zero reachable callers |
| `src/cli/` (Node.js scaffolding) | Untouched at canonical | `package.json`, `.bun-version`, etc. | DELETE LATER (P9) — wrong language for Python repo | P9 | P9 | Confirm no Python import of Node CLI |
| `src/raphael/cognitive/` (duplicate planners, dormant) | Untouched at canonical | `planner.py` (`GreedyPlanner`), `hypothesizer.py`, etc. | DELETE LATER (P9) | P9 | P9 | Confirm Head-1 doesn't reach dormant modules |
| `src/orchestrator/brain/adaptive_brain.py` (31-line counter stub) | Untouched at canonical | Not an orchestrator; only analytics | DELETE LATER (P9) — replace with real orchestrator in P2 | P2 (decision) | P9 | Replace in P2; delete in P9 |
| `src/orchestrator/brain/{reasoning,reflection,skill_indexer,strategy}.py` | Untouched at canonical; small stubs | Various imports | DELETE LATER (P9) | P9 | P9 | Confirm zero callers |
| `src/orchestrator/brain/neural_memory.py` | Untouched at canonical; 79 lines | Bridge only (broken) | DELETE LATER (P9) | P9 | P9 | Confirm no live caller |
| `src/bridge/raphael_bridge.py` | Untouched at canonical; hard-coded broken path | Self-only (broken import) | DELETE LATER (P9) — or fix | P9 (or P3 if Student re-anchored) | P9 | Decide: bridge is needed vs. dead |
| 47 empty `__init__.py` files in `orchestrator/` subpackages | Untouched at canonical | Various | DELETE LATER (P9) | P9 | P9 | Confirm no namespace-package side effects |
| 4 broken symlinks: `cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service` → `/home/yaser/raphael-2.0/<service>` | Untouched; target absent | None | DELETE / REPAIR (P9) | P9 | P9 | Decide: remove or relocate targets |
| `launch_pilot.sh` | Untouched at canonical; broken paths | Self-only | DELETE LATER (P9) | P9 | P9 | Confirm no caller |
| 9 `NOT_IMPLEMENTED` phase executor stubs (harvest, recon, scan, exploit, postex, lateral, credential, exfil, phish) | Untouched at canonical | `src/orchestrator/brain/phases/models.py` | IMPLEMENT or DELETE — decide in P5 (P5 has the second-highest risk per v4.1 AM-14) | P5 | P5 (decision) | Per-phase disposition |
| 4 real phase executors (cicd, ml_attack, cloud_abuse, container_escape) | Real, 1851 LOC total | Same | KEEP (Broker-gate in P3) | P3 | — | Broker gating verified |
| `Report_Raphael/`, `STUDENT_REPORT_TO_SENTINEL_*.md`, `RESEARCH_ASSIGNMENT_001_REPORT.md`, `d6b_failed.jsonl`, `SESSION_REPORT_FULL.md` | Prior audit artifacts | None | ARCHIVE (P9) — not production code | P9 | P9 | Confirm none read by tests |
| `forge/`, `baseline/`, `templates/`, `docker/`, `ci-templates/`, `kali-tools/`, `sliver/` | Untouched; UNKNOWN consumers | Various | TRIAGE in P5/P8 | P5 (decision) | P9 | Confirm reachability |

### Items NOT in scope of this P0 inventory

- 9 NOT_IMPLEMENTED phase executors: tracked in v4.1 AM-14 for P5 task granularity; their implementation/disposition is a P5 deliverable, not P0.
- 47 empty `__init__.py` files: bulk-tracked under "deletion later"; per-file disposition deferred.
- Decepticon and T3MP3ST integration: explicitly out of scope (PD track and v4.1 AM-5 pattern ledger).

### Critical observation: P1 name collision

The orphan stash (Phase 1+2 work) and the canonical `src/orchestrator/runtime/` directory both target the same path with disjoint contents:

| File | Canonical | Orphan stash |
|---|---|---|
| `__init__.py` | empty | exports `RaphaelRuntime`, `EnvironmentAdapter`, etc. |
| `loop.py` | absent | the canonical runtime loop |
| `types.py` | absent | `ComponentBundle` |
| `caido_bootstrap.py` | 5303 bytes Caido integration | absent |
| `docker_client.py` | Docker session client | absent |
| `session_manager.py` | session manager | absent |

If P1 begins by popping the stash, the canonical Caido/Docker/session files will be silently overwritten. P1 must:
1. Decide which surface owns `src/orchestrator/runtime/`.
2. If the new Runtime wins: explicitly delete `caido_bootstrap.py`, `docker_client.py`, `session_manager.py` from canonical before popping the stash.
3. If the Caido/Docker/session surface wins: re-architect Phase 1+2 to use a different package name (e.g., `orchestrator.cognition.runtime` or `src/runtime/`).

This decision is the first thing P1 must make. **P0 defers the decision; P1 must record it.**
