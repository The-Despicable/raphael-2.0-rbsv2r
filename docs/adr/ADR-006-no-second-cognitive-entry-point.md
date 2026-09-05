# ADR-006 — No Second Cognitive Entry Point

| Field | Value |
|---|---|
| ADR | 006 |
| Phase | P1 (architecture freeze) |
| Status | Accepted (per v4 §12.2) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L1) + §3.1 (dual-loop risk) |
| Authority | v4 L1 + §1.1 |

## Context

v4 L1: "One Raphael, one repository identity, one canonical Runtime, one canonical cognitive loop."

v4 §3.1 documents the historical risk: "After P1 lands, both [loops] would coexist temporarily; AM-3's P7a tracking would catch drift."

v4.1 AM-4 (R-2 in risk register): "Seam becomes permanent architecture — A legacy site's seam stays default-ON with legacy branch still present past its welding deadline."

## Decision

**There is exactly one canonical cognitive entry point.** This is the `RaphaelRuntime` per ADR-002, and the Arena's `_run_raphael` is the only alternative entry that delegates to it.

### Rules

1. **No second cognitive loop** in the repository. If a second loop appears (e.g., legacy Head-1 internal loop), it must be deprecated (v4 P1.2) and eventually deleted (v4 P9).
2. **The Arena is not a second brain.** The Arena is a driver/scorer/environment layer (v4 L15), not a cognitive entry point. Arena calls Runtime; Runtime does not call Arena.
3. **The CLI routes through Runtime.** v4 INV-5: "CLI → Runtime; Runtime does not import arena."
4. **AdaptiveBrain is deprecated.** v4 P1.2 lists AdaptiveBrain as a deprecation target. It is a 31-line counter stub at canonical; it is not an orchestrator.

### Invariants (v4 §24)

- **INV-5**: CLI → Runtime; Runtime does not import arena (activation: P2)
- **INV-13**: arena scoring does not affect Runtime decisions (activation: P7/P8)

### Dual-loop risk (v4.1 AM-9 risk register)

- **R-4 (HIGH, G2 blocker)**: Dual-loop coexistence — a second reachable cognitive entry point survives past P2. Detection: `test_import_graph_single_runtime`; INV-5/INV-6. Owner: GLM (gate reviewer).

## Consequences

### Positive
- Single cognitive loop eliminates the "two brains" confusion
- Arena is unambiguously a driver, not a brain
- Clear migration path from current state to canonical state

### Negative
- Legacy Head-1 internal loop must be deprecated (P1.2) and removed (P9)
- Duplicate planner code must be deprecated and removed

### Neutral
- The legacy CLI flag may remain available only through a separately documented migration path (v4 §13.5)
- P7a continuous arena divergence tracking (v4.1 AM-3) catches any drift

## References

- v4 master roadmap §2 (L1, L15)
- v4 master roadmap §3.1 (Head 1/Head 2 disposition)
- v4 master roadmap §12.2 (ADR set)
- v4 master roadmap §13.5 (Runtime proof)
- v4 master roadmap §24 (INV-5, INV-13)
- v4.1 AM-3 (P7a continuous tracking)
- v4.1 AM-4 (seam becomes permanent risk)
- v4.1 AM-9 (risk register R-4)
