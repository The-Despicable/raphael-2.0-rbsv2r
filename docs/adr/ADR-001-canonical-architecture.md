# ADR-001 — Canonical Architecture

| Field | Value |
|---|---|
| ADR | 001 |
| Phase | P1 (architecture freeze) |
| Status | Accepted (per v4 §12.2) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (Locked Architectural Decisions L1–L20) + v4 §12.2 (ADR set) |
| Authority | v4 §1.1 (GLM owns final architecture) |

## Context

Raphael currently contains two internally divergent architectural realities:
- **Head 1** (`src/raphael/`): live/minimal operator-facing surface, `RaphaelOrganism`-style shell/runtime, simple Planner→Executor→State flow
- **Head 2** (`src/orchestrator/`): deeper Planner, WorldModel, hypothesis/contradiction/falsification, CapabilityBroker, Student, evidence machinery

Per v4 §3.1, the project direction is to produce **one Raphael** rather than a federation of systems. The canonical cognitive machinery comes from Head 2; the useful operator-facing shell and selected live Head-1 organics are absorbed into a new production runtime.

## Decision

**There is one Raphael, one repository identity, one canonical Runtime, one canonical cognitive loop.** (v4 L1)

Specifically:
- Head 2 (`src/orchestrator/brain/`) is canonical for cognition (v4 L2)
- Head 1's useful operator-facing and runtime-supporting organics may be absorbed into the canonical Runtime; its old internal loop is superseded (v4 L3)
- `RaphaelRuntime` is a thin sequencer owning stage order, termination, and stage contracts, not domain logic (v4 L4)
- Broker is the Policy Decision Point (PDP) — decides allow/deny and constraints (v4 L5)
- `exec/` is the Policy Enforcement Point (PEP) — only package permitted to hold process/network/file primitives (v4 L6)
- Sandbox is a PEP enforcement mechanism; capabilities execute under it and cannot self-authorize (v4 L7)
- Runtime execution is Broker-mediated from the first usable Runtime commit; no Runtime-wide OFF mode exists (v4 L8)
- Legacy behavior-parity seam exists only as migration scaffolding around pre-existing legacy paths and is removed after migration (v4 L9)

## Consequences

### Positive
- Single source of architectural truth
- No dual-brain confusion between Head 1 and Head 2
- Clear migration path from current state to canonical state
- Bound creep via locked L1–L20 decisions

### Negative
- Head 1's internal loop must be deprecated and removed (L3, P9 work)
- Migration seam introduces temporary complexity (L9, P3 weld)
- All subsequent phases must respect L1–L20

### Neutral
- ADR-011 (sandbox/ mechanisms-only) is a sub-decision of L6/L7
- ADR-003 (Broker/PEP separation) is a sub-decision of L5/L6
- ADR-004 (born-gated Runtime) is a sub-decision of L8

## References

- v4 master roadmap §2 (L1–L20)
- v4 master roadmap §3.1 (Head 1/Head 2 disposition)
- v4 master roadmap §12.2 (ADR set)
- v4.1 AM-1 (halt-and-re-derive)
- v4.1 AM-4 (migration seam: positive interface + weld discipline)
