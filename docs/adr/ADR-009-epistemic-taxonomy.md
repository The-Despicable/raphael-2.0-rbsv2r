# ADR-009 — Epistemic Taxonomy

| Field | Value |
|---|---|
| ADR | 009 |
| Phase | P1 (architecture freeze) → P5 (falsification) |
| Status | Accepted (per v4 §12.2 + v4.1 AM-13.6) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §6 (epistemic model) + v4.1 AM-13.6 (permission/role answer fix) |
| Authority | v4 L13 + L14 + v4.1 AM-13.6 |

## Context

v4 §6 establishes the epistemic model. v4.1 AM-13.6 corrects a defect: "§6's epistemic-class table's 'Can authorize action?' column entry for ExecutionResult ('Evidence candidate') is corrected to a direct permission answer consistent with the other rows: 'No — becomes evidence input to a Finding, does not itself authorize.' The 'evidence candidate' characterization is preserved as prose underneath the table, not as the column's answer."

## Decision

### Five epistemic classes (v4 §6)

| Class | Can authorize action? |
|---|---|
| Assertion | No |
| Observation | No |
| ExecutionResult | **No** — becomes evidence input to a Finding, does not itself authorize (per v4.1 AM-13.6) |
| Artifact | No |
| Finding | Yes (via Falsification promotion) |

### L13 — Assertions are not Findings

Evidence must be provenance-linked. An assertion is a claim without provenance; a Finding is a claim with provenance.

### L14 — Falsification controls promotion

Falsification is the only subsystem permitted to promote/demote epistemic classes. A Finding's status field takes values `active` / `refuted` / `superseded`. Only the falsification engine may write this field.

### Status vs. class (v4.1 AM-2.3)

"Refuted" is a status of a Finding, not a sixth epistemic class. §6 keeps exactly five classes. A Finding's status field takes values `active` / `refuted` / `superseded`. Only the falsification engine may write this field (consistent with L14).

## Invariants (v4 §24)

- **INV-3**: execution-derived claims require receipts (activation: P3)
- **INV-4**: assertions quarantined; falsification controls promotion (activation: P3/P5)

## Consequences

### Positive
- Clear separation between claims and findings
- Single promotion authority (falsification)
- Evidence provenance is mandatory

### Negative
- All claims must be provenance-linked (no bare assertions)
- Falsification engine is a bottleneck for promotion

### Neutral
- Contradiction predicate (v4.1 AM-2) is defined as a GLM Contract deliverable at the start of P5

## References

- v4 master roadmap §2 (L13, L14)
- v4 master roadmap §6 (epistemic model)
- v4 master roadmap §24 (INV-3, INV-4)
- v4.1 AM-2 (canonical contradiction predicate + epistemic class cleanup)
- v4.1 AM-13.6 (permission/role answer fix)
