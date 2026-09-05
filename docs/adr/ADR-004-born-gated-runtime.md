# ADR-004 — Born-Gated Runtime

| Field | Value |
|---|---|
| ADR | 004 |
| Phase | P1 (architecture freeze) |
| Status | Accepted (per v4 §12.2 + §0 executive summary) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §0 (born-gated execution) + §2 (L8) |
| Authority | v4 L8 + §0 |

## Context

v4 §0 states: "The most important sequencing rule is **born-gated execution**: the new Runtime must use `Broker.authorize -> PEP` from its first usable execution path. A temporary compatibility seam may exist only around legacy paths; it is never part of the canonical Runtime."

v4 L8 codifies: "Runtime execution is Broker-mediated from the first usable Runtime commit. No Runtime-wide OFF mode exists."

## Decision

**Runtime execution is Broker-mediated from the first usable Runtime commit. No Runtime-wide OFF mode exists.** (v4 L8)

### Implementation rule

The first Runtime execution path (v4 §13.3 P2.3) must be:
```
Runtime
  → Broker.authorize
  → PEP
  → mock capability
  → ExecutionEvent
  → EvidenceReceipt
```

There is no "Runtime OFF mode" that bypasses Broker. If a capability needs to be called, it goes through Broker. If Broker denies, the Runtime receives a denial and either halts, replans, or escalates.

### Legacy seam exception

A temporary compatibility seam (v4 L9) may exist only around pre-existing legacy paths. It is never part of the canonical Runtime. The seam:
- Is OFF = legacy delegation
- Is ON = Broker/policy-mediated behavior
- Can never be imported by canonical Runtime (v4 INV-6)
- Has owner + removal ticket
- Is temporary (welded at P3 per v4.1 AM-4)

## Consequences

### Positive
- No runtime path can bypass Broker
- Every execution event is receipt-linked (v4 INV-2)
- Single source of authorization truth

### Negative
- Legacy code paths that bypass Broker must be quarantined (P1: SUB-10, SUB-14) and welded (P3: Weld-SUB10, Weld-SUB14)
- The seam must be removed at P3 (v4.1 AM-4: "The seam's delegation capability is deleted wholesale, in one atomic commit, at the moment the last inventoried site is welded")

### Neutral
- P1 quarantines are OFF by default (per C6 / v4.1 AM-4 weld discipline)
- bootstrap-v0 (P2.0 per v4.1 AM-13.2) is the policy artifact that the first Runtime Broker-mediated path authorizes against

## References

- v4 master roadmap §0 (born-gated execution)
- v4 master roadmap §2 (L8, L9)
- v4 master roadmap §13.3 (P2.3 Broker-mediated mock path)
- v4 master roadmap §24 (INV-2, INV-6)
- v4.1 AM-4 (seam: positive interface + weld discipline)
- v4.1 AM-13.2 (bootstrap-v0 policy artifact)
