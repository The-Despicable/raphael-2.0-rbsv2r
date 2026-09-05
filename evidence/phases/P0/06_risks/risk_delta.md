## P0 — Risk Delta (canonical `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`)

### Risks discovered or re-confirmed during P0

| Risk ID | Trigger condition | Current evidence | Impact | Owner | Next action | Blocking gate (if any) |
|---|---|---|---|---|---|---|
| **R-1** | Implementation fixes forward against a stale audit reference | P0-R3/P0-R4 applied throughout — every historical reference reverified against canonical before use. No forward-fixing detected. | LOW at canonical (no implementation work); MEDIUM at P1/P3 when Phase-1-stashed work is reintroduced (the name-collision risk below) | Implementation lane, escalates to GLM | AM-1's halt-and-re-derive rule; P3.0 re-inventory (v4.1 AM-1) | None at P0 |
| **R-2** | A migration seam becomes permanent architecture (no weld terminal) | At canonical, no seam exists. Phase 1 work in orphan stash did create seam logic but not in a welded-terminal form. | LOW at canonical; HIGH post-P1 when seam lands | GLM (gate reviewer) | AM-4 weld discipline applies when seam lands | G3 |
| **R-3** | Floor-monotonicity gaming (tests weakened/skipped outside P9 atomic-deletion commit) | P0-R5 satisfied. FLOOR(P0)=239 from canonical green run. No tests modified. | LOW at canonical | GLM (gate reviewer) | AM-6's diff check at every gate | Every gate |
| **R-4** | Dual-loop coexistence (a second reachable cognitive entry point survives past P2) | At canonical: only one cognitive loop (`arena._run_raphael`); Phase 1's Runtime loop is in orphan stash. Post-P1 pop: TWO loops could coexist if reconciliation is not done. | LOW at canonical; HIGH post-P1 if name-collision not resolved | GLM | INV-5 + INV-6; P7a continuous divergence tracking (v4.1 AM-3) | G2, G7 |
| **R-5** | A P3 weld changes behavior the frozen arena depends on, undetected until P7 | At canonical, no weld attempted. Risk applies post-P3. | N/A at P0 | Implementation lane (P7a), reviewed by GLM | AM-3's continuous P7a tracking | Continuous from G2 |
| **R-6** | Escalation deadlock (architecture contract vs. implementation reality, neither lane can resolve) | N/A at P0 — no conflict encountered | LOW at P0; HIGH if encountered later | Both lanes | AM-12 lane mutual-constraint rule | Any future escalation |
| **R-7** | Python version mismatch: pyproject requires `<3.13`, system has 3.14.4 | 239-test baseline runs green on 3.14.4. No runtime failure observed at P0. | LOW at P0 (tests pass); MEDIUM for production runtime (unverified — no Runtime exists at canonical) | Implementation lane | Document in P1 handoff; resolve before any production deployment | None at P0 |
| **R-8** | `src/orchestrator/runtime/` name collision between canonical contents (`caido_bootstrap.py`, `docker_client.py`, `session_manager.py`, empty `__init__.py`) and Phase-1 orphan stash contents (`loop.py`, `types.py`, populated `__init__.py`) | Detected in P0 deletion inventory. If P1 begins by popping the stash, canonical Caido/Docker/session files are silently overwritten. | HIGH — risk of losing working code OR losing Phase-1 runtime | GLM (decision authority on architectural paths) | P1 must decide ownership of `src/orchestrator/runtime/` path BEFORE popping the stash; document decision in P1 evidence package | P1 start |
| **R-9** | 9 of 13 phase executors are `NOT_IMPLEMENTED` stubs; honest in source comments | Confirmed at canonical. Documented in source as honest stubs. | MEDIUM — autonomous mode is fundamentally non-functional for 9/13 phases | Implementation lane | v4.1 AM-14 (P5 task granularity); decide per-phase implementation vs. deletion in P5 | P5 |
| **R-10** | `src/raphael/main.py` CLI runs through `Executor._subprocess_fallback` without a `CapabilityBroker` on its path | Confirmed at canonical. `RaphaelOrganism` does not construct or call a broker. | HIGH — canonical CLI is the unbrokered path. Phase 3 work must address this. | Implementation lane (P3) | v4.1 AM-4 weld discipline; P3.1+ closure | G3 |
| **R-11** | `orchestrator/brain/action.py:1109` `allowed = True` hardcoded comment is misleading | Confirmed at canonical. Dead code that could be misread as a security bypass if read in isolation. | LOW (Broker IS called after selection in Arena) but MEDIUM for code-readability | Implementation lane | Document as non-authoritative; Phase 1's "marked dead" comment was applied in orphan stash | None at P0 |
| **R-12** | `Planner.decide()` selection bypasses Broker by hardcoding `allowed = True` | Confirmed at canonical. Selection != authorization (Broker is the authorization authority), but the comment is misleading. | LOW (semantics are correct, comment is misleading) | Implementation lane | Same as R-11 | None at P0 |
| **R-13** | 4 broken symlinks (`cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service`) | Confirmed at canonical. Target directory `/home/yaser/raphael-2.0` absent. | LOW (no canonical code path uses them); MEDIUM (confusing for new operators) | Implementation lane (P9) | Repair or delete | None at P0 |
| **R-14** | 14 files contain hard-coded user/workspace paths (`/home/yaser/...`) | Confirmed at canonical via grep. Includes `orchestrator/config/paths.py`, `target.py`, and 9 arena test files. | LOW (most are P0-R2-legal symlink-based) | Implementation lane (P9) | Replace with relative paths or env-driven config | None at P0 |
| **R-15** | `Planner.decide` selection bypasses Broker by hardcoding `allowed = True` — same as R-11/R-12, restated for v4.1 AM-6 floor-monotonicity invariant test | LOW | GLM (gate reviewer) | v4.1 AM-7 (invariant activation phases) | None at P0 |
| **R-16** | `adaptive_brain.py` is 31-line counter stub at canonical; v4.1 says it must be retired or repurposed by P2; orphan stash's Phase 1 did NOT touch it | LOW at canonical; MEDIUM post-P2 if not addressed | Implementation lane (P2) | v4.1 decision: Phase 2 must retire or repurpose; not a P0 action | P2 |
| **R-17** | `bridge.raphael_bridge.py` is broken at canonical (hard-coded `/home/yaser/raphael-2.0` import path); orphan stash's Phase 1 also did not touch it | LOW at canonical (no canonical caller); MEDIUM (some orchestrator Student components are bridge-only reachable) | Implementation lane (P9 or earlier if Student re-anchored) | Decide: repair or delete | None at P0 |

### Risks inherited from v4.1 AM-9 baseline

The master risk register (AM-9) lists 6 baseline risks: stale-map execution, seam becomes permanent, floor-monotonicity gaming, dual-loop coexistence, weld breaks arena parity, escalation deadlock. P0's findings align with these:

- R-1 ≡ AM-9's stale-map execution
- R-2 ≡ AM-9's seam becomes permanent
- R-3 ≡ AM-9's floor-monotonicity gaming
- R-4 ≡ AM-9's dual-loop coexistence
- R-5 ≡ AM-9's weld breaks arena parity
- R-6 ≡ AM-9's escalation deadlock

P0's R-7 through R-17 are P0-specific discoveries, not duplicates of AM-9's baseline risks.

### Risk summary

- 17 risks identified (6 from v4.1 baseline + 11 P0-discovered).
- 0 risks block G0.
- 1 risk is HIGH-severity (R-8, name collision) but is a P1-decision issue, not a G0 blocker.
- 1 risk is HIGH-severity (R-10, unbrokered CLI) and blocks G3 (Phase 3 MVP must close it).
- Other risks are LOW/MEDIUM and tracked for future phases.
