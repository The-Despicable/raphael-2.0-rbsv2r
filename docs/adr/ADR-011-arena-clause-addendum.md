# ADR-011 — Arena-Clause Addendum (companion to ADR-011 sandbox-layer-mechanisms)

| Field | Value |
|---|---|
| ADR | 011 (arena-clause addendum) |
| Phase | P2.0 (addendum to existing ADR-011) |
| Status | Accepted (per v4 L15 + v4.1 AM-3) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L15) + v4.1 AM-3 (P7a continuous tracking) |
| Authority | v4 L15 + v4.1 AM-3 |

## Context

v4 L15: "Arena is a driver/scorer/environment layer, not a second brain."

v4.1 AM-3: "Reword §18.1: P7a is not 'may start after G2' — it must start immediately after G2 and run continuously through P3–P6 as a standing, low-priority parallel track."

The existing ADR-011 (sandbox-layer-mechanisms-not-authorization) establishes the sandbox/ as mechanisms-only. This addendum establishes the arena/ role and the P7a continuous tracking requirement.

## Decision

### Arena is not a second brain (v4 L15)

The Arena is a driver/scorer/environment layer. It:
- Drives the Runtime for evaluation purposes
- Scores Runtime outputs
- Provides environment interactions
- Does NOT implement cognitive machinery
- Does NOT contain a second cognitive loop
- Does NOT affect Runtime decisions (v4 INV-13)

### P7a continuous tracking (v4.1 AM-3)

P7a is not "may start after G2" — it must start immediately after G2 and run continuously through P3–P6 as a standing, low-priority parallel track.

P7a's continuous job during P3–P6: after each phase's gate passes, run the same fixed-seed scenarios through both the (frozen) legacy arena loop and the current Runtime state, and record divergence — not to fix it yet (P7b still owns the actual switch-over), but to catch contract drift at the phase where it was introduced instead of discovering it all at once at P7.

This does not change P7b's scope or gate criteria (G7 stays as specified in §18.6). It only front-loads detection.

### Arena-via-Runtime seam (deferred to P2)

Per v4 §13.5: "The legacy Head-1 loop may remain available only through a separately documented migration path; the canonical Runtime must not invoke it."

The Arena's `_run_raphael_via_runtime` seam depends on Runtime and is deferred to P2 (not P2.0). P2.0 creates the Runtime skeleton; P2.1+ wires the arena seam.

## Invariants (v4 §24)

- **INV-5**: CLI → Runtime; Runtime does not import arena (activation: P2)
- **INV-13**: arena scoring does not affect Runtime decisions (activation: P7/P8)

## Consequences

### Positive
- Clear role separation: Arena drives, Runtime thinks
- P7a continuous tracking catches contract drift early
- No "two brains" confusion

### Negative
- P7a is a standing workstream through P3–P6 (not a one-time task)
- Arena-via-Runtime seam is deferred to P2 (not in P2.0)

### Neutral
- The existing ADR-011 (sandbox-layer-mechanisms) is unchanged
- This addendum is a supplement, not a replacement

## References

- v4 master roadmap §2 (L15)
- v4 master roadmap §13.5 (Runtime proof)
- v4 master roadmap §18.1 (P7a)
- v4 master roadmap §24 (INV-5, INV-13)
- v4.1 AM-3 (P7a continuous tracking)
- ADR-011-sandbox-layer-mechanisms-not-authorization (existing ADR)
