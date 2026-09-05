# ADR-010 — Falsification as Claim Promotion Engine

| Field | Value |
|---|---|
| ADR | 010 |
| Phase | P1 (architecture freeze) → P5 (falsification) |
| Status | Accepted (per v4 §12.2) |
| Deciders | GLM architecture authority + HackerAI implementation |
| Source | v4 master roadmap §2 (L14) + §16 (P5 contract) + v4.1 AM-2 + AM-14 |
| Authority | v4 L14 + v4.1 AM-2 + AM-14 |

## Context

v4 L14: "Falsification is the only subsystem permitted to promote/demote epistemic classes."

v4 §16 (P5) establishes the falsification phase. v4.1 AM-2: "Define the contradiction predicate as a typed comparison: given a Finding F and a new receipt-backed Observation or ExecutionResult O, specify the exact structural condition under which O is classified as contradicting F (e.g., same claim-key, incompatible value, receipt timestamp newer than F's verification timestamp). This must be a data-level rule, not a prose description."

v4.1 AM-14: "Before P5 execution begins (not during), GLM produces a P5-specific task breakdown at the same granularity as §14's P3 bypass-closure matrix."

## Decision

**Falsification is the only subsystem permitted to promote/demote epistemic classes.** (v4 L14)

### Contradiction predicate (v4.1 AM-2.1)

Given a Finding `F` and a new receipt-backed Observation or ExecutionResult `O`, specify the exact structural condition under which `O` is classified as contradicting `F`. This must be a data-level rule, not a prose description — a reviewer must be able to construct a synthetic (F, O) pair and mechanically determine the predicate's output without reading implementation code.

### Falsification probes (v4.1 AM-2.2)

Specify whether falsification's own verification probes are first-class Broker-mediated actions (per §5.2, they must be) or whether falsification only ever consumes observations produced by other stages. Pick one; do not leave it ambiguous.

### Refuted status (v4.1 AM-2.3)

"Refuted" is a status of a Finding, not a sixth epistemic class. A Finding's status field takes values `active` / `refuted` / `superseded`. Only the falsification engine may write this field.

### P5 task matrix (v4.1 AM-14)

Before P5 execution begins, GLM produces a P5-specific task breakdown at the same granularity as §14's P3 bypass-closure matrix:
- P5.0 re-inventory of defeater/arena coupling post-P4
- P5.1–P5.8 as currently listed but each with an explicit "required outcome" column
- AM-2 contradiction-predicate contract as first deliverable

### G5 gate

P5 cannot be considered complete until the contradiction predicate exists and the test suite is actually testing against it (v4.1 AM-2 test consequence: `test_contradiction_changes_next_decision` is not satisfied until run against the typed predicate).

## Invariants (v4 §24)

- **INV-4**: assertions quarantined; falsification controls promotion (activation: P3/P5)

## Consequences

### Positive
- Single promotion authority prevents epistemic drift
- Typed contradiction predicate enables mechanical verification
- P5 task matrix ensures P5 is specified before implementation

### Negative
- Falsification engine is a bottleneck for promotion
- P5 requires GLM Contract deliverables before implementation can begin

### Neutral
- Falsification probes must be Broker-mediated (per v4 §5.2)
- Falsification's own verification probes may require a P5-specific capability (if they are first-class Broker-mediated actions)

## References

- v4 master roadmap §2 (L14)
- v4 master roadmap §6 (epistemic model)
- v4 master roadmap §16 (P5 contract)
- v4 master roadmap §24 (INV-4)
- v4.1 AM-2 (canonical contradiction predicate + epistemic class cleanup)
- v4.1 AM-14 (P5 task granularity elevated to P3-grade detail)
