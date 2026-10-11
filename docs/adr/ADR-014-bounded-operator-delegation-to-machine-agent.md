# ADR-014 — Bounded Delegation of Operator Ratification to a Machine Execution Agent

| Field | Value |
|---|---|
| ADR | 014 |
| Phase | P3 (governance repair for the G3 submission workstream) |
| Status | **Recorded — prospective. Effective only for the delegation record it validates (`DEL-2026-10-11-01`), and revocable at any time.** |
| Deciders | The operator role, for the four decisions whose own recorded text designates them operator-ratifiable. **GLM: not consulted, not required, and not claimed.** |
| Supersedes | Nothing. No roadmap section, ADR, freeze notice, or gate status is amended, relaxed, or superseded by this ADR. |
| Source | `evidence/GOVERNANCE_DECISIONS_20261009.jsonl` (the four proposals that name their own ratifying role); `RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` §1.1, §1.3, Appendix E; `evidence/provenance_correction/OPERATOR_ATTESTATION.md`; `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5; `docs/adr/ADR-013` §3.5 |
| Authority basis | Explicit delegation in the active operator session commissioning `executor_v-2`, recorded verbatim in `evidence/governance/EXECUTOR_DELEGATION_20261011.json`. **Not cryptographically authenticated — see §7.** |
| Date recorded | 2026-10-11 |

---

## 0. Status semantics (read first)

- This ADR is a **procedure**, not a grant. It defines *how* a machine execution
  agent may exercise an operator role, *under what evidence*, and *what it may
  never do*.
- **It names no grantee.** There is deliberately no agent identifier anywhere in
  this document's normative sections. A rule that names its own beneficiary is
  self-authorizing; this one cannot confer authority on anyone by itself.
  Authority comes only from a separate delegation record (§3).
- It does **not** accept G3. G3 remains **NOT ACCEPTED**.
- It does **not** lift the P4/RSI freeze.
- It does **not** adopt ADR-013.
- It does **not** grant, imply, or substitute for any GLM architecture ruling.

---

## 1. The gap this closes

Three repository facts, each independently verifiable:

1. `src/orchestrator/rsi/governance_registry.py` requires that a ruled record
   name an `authority_principal` **distinct from the proposer**, non-empty, and
   carrying a `decided_at`. That is the whole of the ledger's authority model.
2. `evidence/provenance_correction/OPERATOR_ATTESTATION.md` is
   `PENDING — NOT SIGNED`; its human identity fields are `*UNSET*`. The agent
   performing this remediation does not know the operator's legal name, GitHub
   handle, or email, and inventing any of them would be precisely the
   manufactured provenance this workstream exists to remove.
3. No accepted rule in this repository defines how bounded operator authority
   may be **delegated to a machine execution agent**, or what evidence such a
   delegation requires.

The result was a deadlock: the ledger requires a named ratifier; the only
ratifier the repository recognises is a human whose identity nobody may
fabricate; therefore no ratification could ever be recorded truthfully.

**Fabricating a human identity, or treating the unsigned attestation as signed,
is not an acceptable way out.** This ADR is the narrow way out.

## 2. Principal taxonomy (normative)

A **principal** is any value in `authority_principal`. Exactly two kinds exist.

### 2.1 Human principal

A natural person acting in an operator or reviewer role. Recorded as a free
string. **The registry does not and cannot authenticate a human principal.** A
free-text name is a *claim*, not a *proof*; this was already true before this
ADR and remains true after it. Naming a human is neither sufficient nor
necessary to be legitimate — it must additionally be scoped by whatever rule
governs the decision class.

### 2.2 Machine-agent principal

A software execution agent. **Reserved namespace: `agent:`.** A principal
beginning with `agent:` is a machine principal by definition, and is treated as
such by the registry without consulting any data file. This is a **code-level
structural rule**, not a configurable list, so it cannot be edited away by
removing a name from a registry.

Three consequences, all enforced:

- An `agent:` principal is **never** a human principal, and the registry must
  never let one be reported as one.
- An `agent:` principal is **never** the architecture authority (GLM). An agent
  decision can never satisfy a gate that requires a GLM ruling.
- An `agent:` principal may appear as `authority_principal` on a ruled record
  **only** when a valid delegation record covers that exact decision (§3).

### 2.3 Reserved decision classes (normative)

Some decisions may **never** be exercised by a machine agent under any
delegation, because they change what the architecture authority owns under
roadmap §1.1 — invariants, interface contracts, phase acceptance criteria, gate
decisions, or scope control. The following are reserved:

| Reserved class | Example in this repository |
|---|---|
| Extending or reinterpreting an accepted invariant beyond its documented closure | extending ADR-003 INV-2/INV-3 receipt binding into the legacy weld perimeter (`GD-2026-10-11-03`, component 2) |
| Accepting, rejecting, or altering a roadmap gate (G3 or any other) | G3 acceptance |
| Lifting the P4/RSI freeze | `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5 |
| Adopting or superseding an ADR | ADR-013 |
| Any disposition that creates a second enforcement surface or second authorization authority | ADR-006 single-entry doctrine |

A delegation record that names a reserved-class decision id is **invalid** and
every record relying on it is refused. The check is mechanical
(`RESERVED_DECISION_CLASSES` in `governance_registry.py`) and does not depend on
the delegation record being well-intentioned.

**A delegation cannot manufacture a higher-authority decision.** If the reserved
gate is not crossed, the answer is `PROPOSED` and it stays `PROPOSED`.

## 3. Delegation records (normative)

A **delegation record** is a separate, content-hashed evidence artifact. It is
*not* a decision record and can never satisfy `ALLOWED_TRANSITIONS`. One lives
at `evidence/governance/EXECUTOR_DELEGATION_20261011.json`.

Required fields, all enforced by `DelegationRecord.validate()`:

| Field | Requirement |
|---|---|
| `delegation_id` | Non-empty, unique within the delegation set. |
| `agent_principal` | **Must** be in the `agent:` namespace (§2.2). |
| `delegating_principal` | **Must not** be in the `agent:` namespace, and **must differ** from `agent_principal`. This is the structural anti-self-delegation rule. |
| `authority_source` | How the delegation was conveyed. The literal `agent_self_assertion` is refused. |
| `scope_decision_ids` | Enumerated. A decision id absent from this list is out of scope, always. |
| `permitted_transitions` | Enumerated `FROM->TO` pairs. Default and usual value: `["PROPOSED->ADOPTED"]`. |
| `effective_from`, `expires_at` | ISO-8601 instants. A decision outside this window is refused. |
| `revoked` | Boolean. A revoked delegation authorises nothing, ever again. |
| `authored_by`, `verification_status` | Who wrote the record and whether any third party checked it. Recorded truthfully; see §7. |
| `evidence_refs`, `decision` | The substance: what the delegation authorises and on what grounds. |
| `content_hash` | SHA-256 over the canonical content; re-derived and compared on load. |

### 3.1 The authorisation check

When a record with an `agent:` authority principal is appended, the registry
requires **all** of the following. Any failure raises `GovernanceRegistryError`;
there is no warn-and-continue path.

1. The record carries a non-empty `delegation_ref`.
2. A delegation with that id exists in the supplied delegation set.
3. That delegation's re-derived `content_hash` equals its declared hash.
4. `record.authority_principal == delegation.agent_principal`.
5. `record.decision_id in delegation.scope_decision_ids`.
6. `record.decision_id` is not a reserved-class decision id (§2.3).
7. `delegation.revoked` is false.
8. The transition actually performed (`prior.status -> record.status`) is listed
   in `delegation.permitted_transitions`.
9. `effective_from <= record.decided_at <= expires_at`.
10. `record.proposer != delegation.agent_principal` (a rule already enforced for
    every principal, retained).

**If no delegation set is supplied, any `agent:`-principal decision is refused.**
The default is fail-closed, not permissive.

### 3.2 What this prevents

| Attack | Refused by |
|---|---|
| An agent writes its own name into `authority_principal` and nothing else | (1)+(2): no delegation ref / no delegation |
| An agent writes a rule declaring itself authorized | §0: the rule names no grantee; only a delegation record can |
| An agent issues itself a delegation | `delegating_principal` must not be an `agent:` principal and must differ |
| An agent widens a delegation after the fact | `scope_decision_ids` is content-hashed; changing it changes the hash and breaks the pin |
| An agent acts outside its window | (9) |
| An agent acts after revocation | (7) |
| An agent adopts a reserved-class decision (G3, ADR, invariant extension) | (6) |
| A delegated decision is presented as a GLM ruling | §2.2: `agent:` is never GLM; test-pinned |
| A delegated decision is presented as human operator attestation | §2.2 + the attestation file remains unsigned |

## 4. Evidence required to audit a delegated action

For every decision adopted under a delegation, the repository must contain, and
the ledger must reference:

1. the **delegation record** (`delegation_ref` on the decision record);
2. the **original proposal**, unmodified, in ledger history;
3. the **adoption record**, a new appended version — never a rewritten one;
4. the **rule** that made the delegation admissible (this ADR);
5. the **audit trail of what changed**, i.e. the commit.

The decision's `decision_text` must carry the original proposal verbatim,
followed by an explicit `ADOPTED …` clause naming the delegating authority, the
delegation id, and what the adoption does **not** authorise.

## 5. Scope, expiry, completion, revocation

- **Scope** is enumerated per delegation (`scope_decision_ids`), never global.
- **Expiry** is a hard instant (`expires_at`), enforced on every append and on
  every import.
- **Completion condition**: each authorised decision id may be transitioned at
  most once under a given delegation, because `ADOPTED -> ADOPTED` is not a
  legal transition. A delegation is spent once its scope is exhausted.
- **Revocation** is `revoked: true` on the record. Revocation is prospective and
  never erases history; already-adopted records stay in the ledger with their
  original hashes and are contestable through `SUPERSEDED`, not by deletion.
- **Amendment** of a delegation requires a *new* record with a new id. Records
  are content-hashed; editing one in place breaks its hash on the next load.

## 6. Interaction with existing governance (must not be weakened)

| Existing property | Effect of this ADR |
|---|---|
| A `PROPOSED` record carries no authority | unchanged |
| A ruled record needs a distinct authority principal | unchanged, and strengthened for `agent:` |
| Self-adoption is refused | unchanged |
| `ADOPTED -> ADOPTED`, `ADOPTED -> REJECTED` illegal | unchanged |
| Append-only API surface; history never truncated | unchanged |
| Content hash re-derived on every load path | unchanged, extended to delegations |
| Seed generator emits proposals only | unchanged; generator additionally refuses to clobber decision history |
| G3 **NOT ACCEPTED** | unchanged |
| P4/RSI freeze ACTIVE | unchanged |
| `OPERATOR_ATTESTATION.md` unsigned | unchanged — see §8 |

## 7. Honest limits of this mechanism (normative disclosure)

This ADR must not be read as stronger than it is.

1. **It does not authenticate anyone.** The registry verifies that a delegation
   record exists, is internally consistent, is content-hash-pinned, is
   un-revoked, is in-window, is scoped to the decision, and was **not**
   self-issued. It does **not** verify that a real human exists behind
   `delegating_principal`, and it cannot: this repository has no signature, no
   identity substrate, and no external notarisation. That residual already
   existed for human principals (§2.1); this ADR makes it explicit for agent
   principals rather than hiding it.
2. **A delegation record written by the agent is agent-authored.** In this
   workstream `evidence/governance/EXECUTOR_DELEGATION_20261011.json` was written
   by the same agent that uses it. The record therefore carries
   `authored_by: "agent:executor_v-2"` and
   `verification_status: "UNVERIFIED_BY_THIRD_PARTY"`. An auditor must verify
   the claimed session delegation against the commissioning task packet, **which
   is not in this repository**. Until that check happens, decisions adopted
   under it are structurally valid but not third-party authenticated, and this
   ADR says so rather than implying otherwise.
3. **This is a disclosure, not a defence.** The record can be read by anyone and
   its unverified status is stated on its face and in every decision record that
   relies on it.
4. **A test suite is not authentication.** Passing tests show the mechanism
   behaves as specified. They show nothing about who actually delegated.
5. **The reserved-class check is enumerated.** See §10.2.
6. **The seed generator remains unguarded.** See §10.1.

## 8. The human attestation is not replaced by this ADR

`evidence/provenance_correction/OPERATOR_ATTESTATION.md` remains
`PENDING — NOT SIGNED` with every human field `*UNSET*`.

Delegated agent ratification and human operator attestation are **different
things** and this ADR does not let one stand in for the other:

- The delegation mechanism lets an *agent* record a decision **as an agent**.
- It does not let anyone record a human identity, and it does not make the
  attestation signed.
- Only the human operator can close that attestation, and only by supplying
  their own name, handle, and review.

`OPERATOR_ATTESTATION.md` §68 and statement 3 remain accurate: the historical
`validation` call-site rulings are `PENDING_OPERATOR_RATIFICATION` and Phase 3
readiness remains blocked on them.

## 9. Consequence for this workstream

`DEL-2026-10-11-01` scopes exactly four decision ids. Applying §2.3:

- `GD-2026-10-11-01` (B2 bridge quarantine) — operator-ratifiable per its own
  text → **in scope**.
- `GD-2026-10-11-02` (P3 PostEx agent-path quarantine) — operator-ratifiable →
  **in scope**.
- `GD-2026-10-11-04` (H2 `RAPHAEL_HITL_BYPASS` prohibition) — operator-ratifiable;
  a prohibition, so ratifying it cannot expand authority → **in scope**.
- `GD-2026-10-11-05` (E2 engagement grant-by-process) — operator-ratifiable per
  its own text, which also names the operator "the ratifying owner of record" →
  **in scope**. Ratifying the *process* grants **no** capability and issues
  **no** engagement grant.
- `GD-2026-10-11-03` (R1 receipt binding) — component 2 is an explicit
  extension of ADR-003 INV-2/INV-3 beyond their documented closure, i.e. an
  invariant-scope change reserved to the architecture authority. No GLM ruling
  exists. Searched: `evidence/`, `reports/`, `docs/`, `evidence/g3_remediation/`;
  the `GLM_GOVERNANCE_VERDICT.md` cited at
  `evidence/g3_remediation/F2_PERIMETER_RECORD.md:318` is **absent** from the
  repository; `evidence/g3_remediation/STATUS.md:17` records
  `G3 NOT ACCEPTED (no GLM ruling yet)`. → **RESERVED. Remains `PROPOSED`.**

Component 1 of `GD-2026-10-11-03` being already implemented does not adopt the
decision; the ledger records a single status per decision id.

## 10. Known residuals (recorded, not engineered away)

### 10.1 The seed generator can still truncate ratified decisions

`scripts/gen_governance_decision_seeds.py` writes the ledger from the eleven
seeds. Now that the ledger also holds four ratified records, **re-running that
script would overwrite the file and delete those ratifications.**

A refuse-to-overwrite guard was written for this, and then **deliberately
removed**. `tests/test_historical_split_adjudication_package.py::test_no_historical_script_or_test_was_modified_by_the_package`
protects the whole of `scripts/` as census input for the historical split
adjudication package (`CODE_ROOTS` includes `scripts`), and that guardrail is
not within this workstream's authority to change. Editing the guardrail to make
room for a convenience fix would have been the tail wagging the dog — so the
guard was removed and the hazard recorded instead.

Until the owner of that guardrail acts, the minimum correct external action is
**one** of:

1. narrow the protected-path list to the adjudication package's own scripts, and
   let the generator refuse to overwrite a ledger holding non-seed records; or
2. have the generator write to a separate seeds-only path, leaving the ledger
   append-only.

`tests/test_rsi1_governance_registry.py::test_committed_ledger_has_diverged_from_the_seed_set`
pins the divergence so it cannot be lost silently. Until then: **do not re-run
the seed generator against this ledger.**

### 10.2 The reserved-class check is enumerated, not general

`RESERVED_DECISION_CLASSES` is a code-level list, not a classifier. It is
enforced mechanically for the ids it names, and adding one is a visible,
reviewable code edit. A future reserved decision is therefore protected only
once someone adds it here. This is a real limit of a mechanical rule and is
stated rather than glossed.

## 11. References

- `RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` §1.1 (two-lane authority), §1.1
  mutual-constraint rule, §1.3 (phase lifecycle), Appendix E (precedence)
- `src/orchestrator/rsi/governance_registry.py` (authority model; `AGENT_PRINCIPAL_PREFIX`; `RESERVED_DECISION_CLASSES`; `DelegationRecord`)
- `evidence/governance/EXECUTOR_DELEGATION_20261011.json` (the delegation record)
- `evidence/GOVERNANCE_DECISIONS_20261009.jsonl` (ledger)
- `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5 (freeze lift conditions)
- `docs/adr/ADR-013` §3.5 (operator owns task packets and ratification; GLM owns architecture/gate adjudication)
- `docs/adr/ADR-003-broker-pdp-pep-separation.md` (INV-2, INV-3)
- `docs/adr/ADR-006-no-second-cognitive-entry-point.md` (INV-5 single-entry doctrine)
- `evidence/provenance_correction/OPERATOR_ATTESTATION.md`

---

*Status: recorded and prospective. Does not supersede, amend, or accept any
roadmap section, ADR, gate, or freeze. Effective only for a valid, in-window,
un-revoked, correctly-scoped delegation record. Revocable at any time by the
delegating authority.*