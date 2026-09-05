# ADR-012 — Seam-Semantics Ratification (v4.1 AM-4)

| Field | Value |
|---|---|
| ADR | 012 |
| Phase | P1 (ratification of v4.1 AM-4 seam contract) |
| Status | Accepted (per v4.1 AM-4) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4.1 AM-4 (migration seam: positive interface + weld discipline) |
| Authority | v4.1 AM-4 (the dominant amendment, GLM's #1 risk) |

## Context

v4.1 AM-4: "This is judged the single highest-priority amendment in the set. A migration seam without both a defined interface and a defined death is how 'temporary scaffolding' becomes a permanent, ungated second execution path — which is exactly the defect (Head-1 `_subprocess_fallback`-style bypass) the whole program exists to close."

This ADR ratifies v4.1 AM-4 as the canonical seam contract. It is a companion to ADR-005 (Legacy Migration Seam) and provides the binding semantics for all P3 welding.

## Decision

### 1. Positive interface (v4.1 AM-4.1)

The seam is a single, typed proxy with one operation: `SeamRoute(legacy_site_id) -> PolicyDecision`.

- Never holds business logic
- Never grows additional legacy sites beyond the P0/P3.0-confirmed inventory
- Never becomes a general policy layer
- Its own interface is intentionally too narrow to compete with the Broker it sits beneath

A candidate name like `BehaviorAlterableGate` may be used, but the interface signature above (or an equivalent GLM-approved one) is fixed before implementation, not left as an implementation-level choice.

### 2. Weld semantics (v4.1 AM-4.2)

"Welding closed" a legacy site means ALL THREE of:
1. The seam is fixed ON for that site's call path (permanently routed through Broker/PEP)
2. The legacy branch at that call site is deleted
3. This happens under a named, versioned policy artifact (`bootstrap-v0` at P2, superseded by Scope v0 at P3)

A site is NOT considered welded if the seam merely defaults to ON while the legacy branch still exists in the tree.

### 3. G3 exit condition (v4.1 AM-4.3)

G3 does not pass while any P3.0-confirmed legacy site remains un-welded. Partial welding is a G3 FAIL, not a partial pass.

### 4. Rollback discipline (v4.1 AM-4.4)

If a welded site needs to be reverted during remediation:
- Fix: rework the Broker-mediated path
- NEVER: re-open the deleted legacy branch
- NEVER: flip the seam back to a persistent OFF state

A temporary debugging restoration (per §30's existing seam-rollback language) must be:
- Scoped to a single named debugging session
- Owned
- Ticketed for removal
- Structurally incapable of being reached by canonical Runtime

### 5. Deletion (v4.1 AM-4.5)

The seam's delegation capability is deleted **wholesale, in one atomic commit**, at the moment the last inventoried site is welded — not gradually filed away per-site across P3 into P9 as separate cleanup items.

§20.2 already lists the seam as a P9 cleanup candidate; that entry now means "confirm zero references," not "perform the deletion" — the deletion event itself happens at the P3 welding milestone, and P9 only verifies it stayed dead.

## P1 implementation status

Per v4.1 AM-13.3: "After §12.5's seam-ON proof (demonstrating a policy decision is observable), add: all sites exercised for this proof are restored to seam-OFF before P1 concludes. P1 proves the seam works; it does not leave anything welded — welding is exclusively a P3 activity per AM-4."

P1 implemented:
- **SUB-10**: `src/orchestrator/kali_tools_client.py:_run_local` — WRAPPED (OFF), Weld-SUB10 (P3)
- **SUB-14**: `src/raphael/executor/executor.py:_subprocess_fallback` — WRAPPED (OFF), Weld-SUB14 (P3)
- **Weld-SHELL**: `src/orchestrator/capabilities/interactive_shell/capability.py` — DEFERRED to P3 (C7 conflict)

All P1 sites are restored to seam-OFF. No welding occurred in P1.

## Gate impact

- **G1 sign-off**: requires this contract to exist before P1 implementation starts (it governs what P1.3 builds) ✅ SATISFIED
- **G3**: requires full welding per point 3 (all P3.0-confirmed sites welded, not partial)

## Invariants (v4 §24)

- **INV-6**: Runtime cannot import seam (activation: P2)

## Consequences

### Positive
- Single highest-priority amendment is formally ratified
- Weld discipline is binding, not advisory
- G3 exit condition prevents partial welding

### Negative
- P3 must weld all P3.0-confirmed sites (no partial pass)
- Atomic deletion of the seam at P3 is a one-shot event

### Neutral
- This ADR is a supplement to ADR-005 (Legacy Migration Seam)
- It does not change P1 implementation status

## References

- v4.1 AM-4 (the dominant amendment)
- v4.1 AM-13.3 (P1 seam sites restored OFF)
- v4 master roadmap §12.3 (P1.3)
- v4 master roadmap §24 (INV-6)
- ADR-005-legacy-migration-seam (companion ADR)
- evidence/phases/P1/03_seam_work/SEAM_SITES.md (SUB-10, SUB-14, Weld-SHELL)
