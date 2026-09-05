# ADR-002 — RaphaelRuntime

| Field | Value |
|---|---|
| ADR | 002 |
| Phase | P1 (architecture freeze) → P2 (implementation) |
| Status | Accepted (per v4 §12.2 + §13.1) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L4) + v4 §13.1 (Runtime contract) |
| Authority | v4 L4 + §13.1 |

## Context

v4 L1 mandates "one canonical Runtime." v4 L4 specifies that `RaphaelRuntime` is a thin sequencer. v4 §13 (P2) provides the detailed Runtime contract: "build the smallest real Runtime with a canonical loop and Broker-mediated execution from its first usable commit."

The canonical loop per v4 §0 is:
```
observe → understand → generate candidates → plan → authorize → execute
→ collect evidence → update WorldModel → falsify/check contradictions
→ replan → learn (post-MVP) → repeat/terminate
```

## Decision

**`RaphaelRuntime` is a thin sequencer. It owns stage order, termination, and stage contracts, not domain logic.** (v4 L4)

`RaphaelRuntime` must:
- own sequence and termination
- call stage handlers
- have no domain logic
- have no policy logic
- have no migration-seam dependency
- enter Broker/PEP for EXECUTE
- expose a stable trace interface

The Runtime uses Head 2 organs as handlers rather than rewriting their internal logic.

### Runtime interface (v4 §13.2)

At minimum, define conceptual contracts for:
- `RuntimeContext`
- `MissionContext`
- `StageResult`
- `ActionRequest`
- `PolicyDecision`
- `ExecutionEvent`
- `EvidenceReceipt`
- `LoopTermination`

Exact Python class names may change during implementation, but behavior and ownership must remain consistent.

### P2 implementation tasks (v4 §13.3)

- **P2.1** — Runtime skeleton: create under `orchestrator/runtime/`; initialize context, execute stage sequence, capture stage outputs, terminate cleanly, emit trace
- **P2.2** — Wire stage handlers: observation, WorldModel read, Student candidate generation in recording mode, Planner request generation, Broker call, PEP invocation, receipt emission, minimal WorldModel integration, minimal contradiction/failure trigger, replan
- **P2.3** — Broker-mediated mock path: `Runtime → Broker.authorize → PEP → mock capability → ExecutionEvent → EvidenceReceipt`
- **P2.4** — Safe proving capability: one low-risk, deterministic, Raphael-native capability (read-only fixture inspection preferred)
- **P2.5** — CLI entry: wire operator-facing CLI to invoke Runtime for a one-iteration run
- **P2.6** — Trace: produce minimal `DecisionTrace` (stage, candidate/request, policy decision, execution linkage, receipt id, next-stage outcome)
- **P2.7** — Arena oracle: record historical arena stage sequence as behavioral oracle; do not copy arena orchestration into Runtime

## Consequences

### Positive
- Clear separation between sequencing and domain logic
- Runtime is testable as a sequencer independent of domain modules
- Stage contracts enable incremental implementation

### Negative
- P2 work required to materialize the Runtime (C1: no Runtime in P1)
- Runtime must not import arena (v4 INV-5) or seam (v4 INV-6)

### Neutral
- Runtime is born-gated per ADR-004
- Runtime is broker-mediated per ADR-003

## References

- v4 master roadmap §2 (L4)
- v4 master roadmap §13.1–13.7 (P2 contract)
- v4 master roadmap §24 (INV-5, INV-6)
- v4.1 AM-4 (seam discipline)
- v4.1 AM-13.2 (bootstrap-v0 policy artifact)
