# ADR-003 — Broker PDP / PEP Separation

| Field | Value |
|---|---|
| ADR | 003 |
| Phase | P1 (architecture freeze) |
| Status | Accepted (per v4 §12.2 + §5.1) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L5, L6) + v4 §5.1 (PDP/PEP separation) |
| Authority | v4 L5 + L6 |

## Context

v4 §5.1 establishes the PDP/PEP split: Broker is the Policy Decision Point (PDP), `exec/` is the Policy Enforcement Point (PEP). v4 §5.2 establishes the universal Broker rule. v4 L5 and L6 codify this as locked decisions.

The audit found that historically, execution paths bypassed Broker (e.g., `raphael/executor/executor.py:_subprocess_fallback`, `orchestrator/kali_tools_client.py:_run_local`). P1 introduced quarantines (SUB-10, SUB-14) to gate these paths; P3 will weld them (Weld-SUB10, Weld-SUB14).

## Decision

**Broker is the Policy Decision Point (PDP). It decides allow/deny and constraints.** (v4 L5)
**`exec/` is the Policy Enforcement Point (PEP). It is the only package permitted to hold process/network/file primitives.** (v4 L6)

### PDP/PEP separation (v4 §5.1)

```
┌─────────────────────────────────────────┐
│  Planner / Runtime / Capability         │  ← decision REQUEST
│  ↓                                      │
│  Broker (PDP)                           │  ← decision: allow/deny + constraints
│  ↓                                      │
│  exec/ (PEP)                            │  ← enforcement: process/network/file
│  ↓                                      │
│  Sandbox                                │  ← isolation: capabilities execute under it
└─────────────────────────────────────────┘
```

### Universal Broker rule (v4 §5.2)

Execution primitives (process, network, file) are licensed exclusively to `exec/`. The one sanctioned internal exception is `exec/`'s own writes to the receipt store, artifact store, and ledger — these are PEP-internal persistence operations, not environment interactions, and do not require a separate Broker decision per write. All other file access, by any other package, is Broker-mediated exactly like process or network access.

### Invariants (v4 §24)

- **INV-1**: process/network/file primitives confined to `exec/` (activation: P2)
- **INV-2**: every execution event has Broker `decision_id` (activation: P2/P3)
- **INV-3**: execution-derived claims require receipts (activation: P3)

## Consequences

### Positive
- Single authorization authority (Broker)
- Single enforcement boundary (`exec/`)
- Receipts link every execution event to a Broker decision
- Historical bypasses are explicitly quarantined (SUB-10, SUB-14) and will be welded (Weld-SUB10, Weld-SUB14)

### Negative
- All execution paths must route through Broker (v4 L8: "No Runtime-wide OFF mode exists")
- P3 must weld all P3.0-confirmed legacy sites (v4.1 AM-4: "G3 does not pass while any P3.0-confirmed legacy site remains un-welded")

### Neutral
- Sandbox is a PEP enforcement mechanism (v4 L7), not a separate authorization layer
- Decepticon imports must be confined to `exec/` (v4 INV-9, PD track)

## References

- v4 master roadmap §2 (L5, L6, L7, L8)
- v4 master roadmap §5.1 (PDP/PEP separation)
- v4 master roadmap §5.2 (universal Broker rule)
- v4 master roadmap §24 (INV-1, INV-2, INV-3)
- v4.1 AM-4 (weld discipline)
- evidence/phases/P1/03_seam_work/SEAM_SITES.md (SUB-10, SUB-14 quarantines)
