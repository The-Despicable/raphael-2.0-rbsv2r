# ADR-008 — Decepticon Fenced Post-MVP Integration

| Field | Value |
|---|---|
| ADR | 008 |
| Phase | P1 (architecture freeze) + PD (parallel track) |
| Status | Accepted (per v4 §12.2) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L11) + §9 (Decepticon placement) + §21.3 (PD track) |
| Authority | v4 L11 + §9 |

## Context

v4 L11: "Decepticon is selectively absorbed only for execution/sandbox/capability infrastructure, post-MVP and off the critical path."

v4 §9 establishes Decepticon placement: below the broker, in the execution/sandbox/capability layer only.

v4 §21.3 establishes the Decepticon parallel track (PD): "Decepticon investigation runs in parallel with the active phase, but does not gate any phase transition."

## Decision

**Decepticon is selectively absorbed only for execution/sandbox/capability infrastructure, post-MVP and off the critical path.** (v4 L11)

### Fence (v4 INV-9)

Decepticon imports are confined to `exec/`. This is a hard fence: no other package may import from Decepticon directly. All Decepticon-mediated capabilities must go through `exec/`, which in turn goes through the Broker (per ADR-003).

### Post-MVP timing

Decepticon absorption happens after MVP (G3). It is not on the critical path for G3. The PD track may run in parallel, but does not gate any phase.

### What is absorbed

Only execution/sandbox/capability infrastructure:
- Process execution primitives
- Network primitives
- File primitives
- Sandbox/container infrastructure
- Capability implementations (not cognitive machinery)

### What is NOT absorbed

- Cognitive machinery (Planner, WorldModel, Falsification, etc.)
- Arena orchestration
- CLI/operator-facing surface
- Student learning

## Invariants (v4 §24)

- **INV-9**: Decepticon imports confined to `exec/` (activation: PD track)

## Consequences

### Positive
- Clear fence prevents Decepticon from leaking into cognitive layers
- Post-MVP timing keeps MVP on the critical path
- Parallel track (PD) allows investigation without blocking

### Negative
- Decepticon integration is deferred until after G3
- All Decepticon imports must be audited against the fence

### Neutral
- Decepticon is not part of the P2.0 entry sequence
- Decepticon is not part of the P3 MVP

## References

- v4 master roadmap §2 (L11)
- v4 master roadmap §9 (Decepticon placement)
- v4 master roadmap §21.3 (PD parallel track)
- v4 master roadmap §24 (INV-9)
- v4.1 AM-5 (pattern-provenance ledger, for T3MP3ST — Decepticon has its own fence)
