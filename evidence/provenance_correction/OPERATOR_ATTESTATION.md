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

---

## Addendum (2026-10-11): delegated machine-agent authority is NOT this attestation

Added by the `executor_v-2` governance-repair session. **Nothing above is
changed by this addendum.** The status remains `PENDING — NOT SIGNED`, and every
human field above remains `*UNSET*`.

A question arose during that session: if this file is unsigned, how can any
operator-level decision be recorded at all? The answer was not to sign this
file, and not to reuse it for something it is not.

### The two things are different

| | This attestation | Delegated machine-agent authority |
|---|---|---|
| Who acts | A **human** operator, in person | A **software agent**, `agent:executor_v-2` |
| What it establishes | Human identity, review, and approval | That a named agent acted, within an enumerated scope, under a delegation record |
| Where it lives | this file | `evidence/governance/EXECUTOR_DELEGATION_20261011.json` |
| Rule | — | `docs/adr/ADR-014-bounded-operator-delegation-to-machine-agent.md` |
| Can it close this file? | it *is* this file | **No, never.** |

### What the delegation did and did not do

It permitted four ledger records
(`GD-2026-10-11-01`, `-02`, `-04`, `-05`) to be appended as `ADOPTED`, with
`authority_principal: "agent:executor_v-2"` and a `delegation_ref` pointing at
the delegation record.

It did **not**:

- supply any human identity, or fill any `*UNSET*` field above;
- make this file signed, reviewed, or ratified;
- record a GLM architecture ruling, or satisfy any gate reserved to GLM;
- accept G3 (still **NOT ACCEPTED**) or lift the P4/RSI freeze;
- grant the `agents.engage` capability or authorise engaging any target;
- adopt `GD-2026-10-11-03`, which remains `PROPOSED` because its legacy
  weld-perimeter component is reserved to the architecture authority and no GLM
  ruling exists.

### The honest limit

The delegation record was **written by the same agent that acts under it**, and
it carries `verification_status: UNVERIFIED_BY_THIRD_PARTY`. The repository can
verify that the delegation's scope, window, hash and non-self-issuance are
internally consistent; it cannot verify that a consenting human issued it,
because there is no signature or identity substrate here. Anyone auditing this
work should check the claimed session delegation against the commissioning task
packet, which is **not** stored in this repository.

So: these four decisions are structurally valid and traceable, and they are
**not** third-party authenticated. Closing the human attestation above remains
an open, separate, and still-required operator act.
