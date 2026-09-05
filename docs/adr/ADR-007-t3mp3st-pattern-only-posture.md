# ADR-007 — T3MP3ST Pattern-Only Posture

| Field | Value |
|---|---|
| ADR | 007 |
| Phase | P1 (architecture freeze) |
| Status | Accepted (per v4 §12.2) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L10) + v4.1 AM-5 (pattern-provenance ledger) |
| Authority | v4 L10 + v4.1 AM-5 |

## Context

v4 L10: "T3MP3ST is a pattern source only. No AGPL source is incorporated without a new explicit legal ADR."

v4.1 AM-5: "T3MP3ST is tracked with a clean conceptual table (§8) but, unlike Decepticon, has no fencing mechanism, no dedicated invariant, and no record of which native Raphael type derives from which T3MP3ST concept — which matters because the AGPL exposure risk for T3MP3ST is conceptual-derivation adequacy, not copied code, and that risk is invisible without a ledger."

## Decision

**T3MP3ST is a pattern source only. No AGPL source is incorporated without a new explicit legal ADR.** (v4 L10)

### Pattern-provenance ledger (v4.1 AM-5)

A third-party-pattern ledger (`docs/PATTERN_PROVENANCE.md`) records, for every native Raphael type informed by a T3MP3ST concept, which concept informed it and a one-line statement of what was and was not carried over (naming, interface shape vs. no source).

Activation: P1 onward (parallel to INV-10's AGPL rule).

### G4 gate (v4.1 AM-5)

P4's MissionSpec/Scope/AuthorizationContext/EvidenceReceipt/ArtifactRef/ProvenanceRecord types may not be considered complete until the corresponding ledger entries exist. This is a documentation-gate, not a legal ruling.

### Legal review trigger

This ADR explicitly flags a legal-review trigger, not a technical judgment. If the pattern-ledger surfaces closer-than-expected derivation, that is escalated outside the dual-lane process (GLM/HackerAI), not adjudicated by either lane.

## Invariants (v4 §24)

- **INV-10**: no AGPL source without explicit legal ADR (activation: P1 onward)

## Consequences

### Positive
- Clear boundary between pattern inspiration and source incorporation
- Documentation trail enables legal review without archaeology
- G4 gate ensures ledger is populated before P4 types are considered complete

### Negative
- Every native type informed by T3MP3ST must be documented
- Legal review may be required for borderline cases

### Neutral
- The ledger is documentation, not code; it does not affect runtime behavior
- T3MP3ST patterns may inform naming, interface shape, and design without source incorporation

## References

- v4 master roadmap §2 (L10)
- v4 master roadmap §8 (T3MP3ST tracking)
- v4 master roadmap §24 (INV-10)
- v4.1 AM-5 (pattern-provenance ledger)
