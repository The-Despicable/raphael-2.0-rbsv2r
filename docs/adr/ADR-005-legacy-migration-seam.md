# ADR-005 — Legacy Migration Seam

| Field | Value |
|---|---|
| ADR | 005 |
| Phase | P1 (architecture freeze) + P3 (welding) |
| Status | Accepted (per v4 §12.2 + v4.1 AM-4) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L9) + §12.3 (P1.3) + v4.1 AM-4 (weld discipline) |
| Authority | v4 L9 + v4.1 AM-4 |

## Context

v4 L9: "Legacy behavior-parity seam exists only as migration scaffolding around pre-existing legacy paths and is removed after migration."

v4 §12.3 P1.3: "Implement a seam that can wrap only existing legacy call sites. Rules: OFF = legacy delegation; ON = Broker/policy-mediated behavior; seam can never be imported by canonical Runtime; seam has owner + removal ticket; seam is temporary."

v4.1 AM-4 (the dominant amendment): "A migration seam without both a defined interface and a defined death is how 'temporary scaffolding' becomes a permanent, ungated second execution path — which is exactly the defect (Head-1 `_subprocess_fallback`-style bypass) the whole program exists to close."

## Decision

### Positive interface (v4.1 AM-4.1)

The seam is a single, typed proxy with one operation: `SeamRoute(legacy_site_id) -> PolicyDecision`. It never holds business logic, never grows additional legacy sites beyond the P0/P3.0-confirmed inventory, and never becomes a general policy layer — its own interface is intentionally too narrow to compete with the Broker it sits beneath.

### Weld semantics (v4.1 AM-4.2)

"Welding closed" a legacy site means:
1. The seam is fixed ON for that site's call path (i.e., permanently routed through Broker/PEP)
2. The legacy branch at that call site is deleted
3. This happens under a named, versioned policy artifact (`bootstrap-v0` at P2, superseded by Scope v0 at P3)

A site is not considered welded if the seam merely defaults to ON while the legacy branch still exists in the tree.

### G3 exit condition (v4.1 AM-4.3)

G3 does not pass while any P3.0-confirmed legacy site remains un-welded. Partial welding is a G3 FAIL, not a partial pass.

### Rollback discipline (v4.1 AM-4.4)

If a welded site needs to be reverted during remediation, the fix is to rework the Broker-mediated path, never to re-open the deleted legacy branch or flip the seam back to a persistent OFF state.

### Deletion (v4.1 AM-4.5)

The seam's delegation capability is deleted wholesale, in one atomic commit, at the moment the last inventoried site is welded — not gradually filed away per-site across P3 into P9 as separate cleanup items.

## P1 implementation

Per v4 §12.3 P1.3, P1 implemented a seam candidate `BehaviorAlterableGate` (informal name; the actual implementation uses quarantine flags + opt-in functions). Two sites were wrapped:
- **SUB-10**: `src/orchestrator/kali_tools_client.py:_run_local` → `_BYPASS_AUTHORIZED` flag + `authorize_local_bypass(reason)` opt-in
- **SUB-14**: `src/raphael/executor/executor.py:_subprocess_fallback` → `_bypass_authorized` flag + `authorize_bypass(reason)` opt-in

Both seams are OFF by default per C6. Welding is P3 work (Weld-SUB10, Weld-SUB14).

One seam was deferred to P3: **Weld-SHELL** (`src/orchestrator/capabilities/interactive_shell/capability.py`), because applying it in P1 broke one canonical test (C7 forbids test edits).

## Consequences

### Positive
- Positive interface prevents the seam from becoming a general policy layer
- Weld discipline ensures the seam is temporary, not permanent
- G3 exit condition prevents partial welding

### Negative
- P3 must weld all P3.0-confirmed legacy sites (no partial pass)
- Atomic deletion of the seam at P3 is a one-shot event

### Neutral
- The seam is never part of the canonical Runtime (v4 L9)
- The seam is never imported by Runtime (v4 INV-6)

## References

- v4 master roadmap §2 (L9)
- v4 master roadmap §12.3 (P1.3)
- v4 master roadmap §24 (INV-6)
- v4.1 AM-4 (full seam contract: positive interface + weld discipline + G3 exit + rollback + deletion)
- evidence/phases/P1/03_seam_work/SEAM_SITES.md (SUB-10, SUB-14, Weld-SHELL)
