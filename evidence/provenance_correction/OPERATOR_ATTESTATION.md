# OPERATOR ATTESTATION — RSI-1 Provenance Correction

**STATUS: PENDING — NOT SIGNED**

This file records where operator attribution is missing. It is deliberately
**not** signed, because the agent performing this remediation does not know the
operator's legal name, GitHub handle, or email address. Inventing any of them
would be exactly the manufactured provenance this workstream exists to remove.

## What a human operator must supply to close this item

| Field | Value |
|---|---|
| Operator name | *UNSET* |
| Operator GitHub handle | *UNSET* |
| Operator email | *UNSET* |
| Date of review | *UNSET* |
| Signature | *UNSET* |

## Commit identity actually used

Every commit on `governance/rsi-1-provenance-correction` was authored and
committed by:

```
OMP Agent <agent@local>
```

This is an **agent identity, not a human operator identity**. It is recorded
here so the audit trail is truthful about who produced the work. It is not, and
must not be treated as, operator approval.

## Scope of this remediation

This branch:

- removes fabricated provenance (adoption registry, quarantine claim, false
  test-count claim, unverifiable rulings);
- corrects evidence binding to a verifiable tree SHA;
- re-implements the measurement contract with behavioural tests;
- re-derives the historical call-site census from source.

This branch does **not**:

- authorize Phase 3;
- enable promotion, deployment, rollback, or production adoption;
- adopt any campaign configuration;
- fabricate, reconstruct, or synthesize any missing dataset.

## Statements awaiting operator signature

An operator signing this file would confirm:

1. The operator has reviewed the provenance corrections listed in
   `reports/PROVENANCE_CORRECTION_REPORT_20261009.md`.
2. The operator knows that **no fabricated evidence was introduced** by this
   remediation, and that every previously fabricated artifact was removed rather
   than repaired.
3. The operator understands that the historical `validation` call-site rulings
   remain **PENDING_OPERATOR_RATIFICATION**, and that Phase 3 readiness remains
   blocked until they are ratified.
4. The operator authorizes requesting a **fresh independent audit**. It does not
   authorize Phase 3.

Until this file is completed and signed, **operator attribution for this
remediation is recorded as absent**, and that absence is itself a finding for
the fresh audit.