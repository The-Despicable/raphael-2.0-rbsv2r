# ADR-014 — Bounded Delegation of Operator Ratification to a Machine Execution Agent

| Field | Value |
|---|---|
| ADR | 014 |
| Phase | P3 (governance repair for the G3 submission workstream) |
| Status | **Recorded — prospective, and NOT independently adopted.** Effective only for a delegation whose issuer is *listed* in `evidence/governance/TRUSTED_ISSUERS.json` — which is currently empty, so no delegation is effective. Listing an issuer is **not** authentication; see §3.1a and §7.8. Revocable at any time. **The four adoptions made under it have been retracted; see §12.** |
| Deciders | **Unassigned.** No authority has adopted this ADR. It was authored by a machine agent and describes a mechanism, not an approval. |
| Supersedes | Nothing. No roadmap section, ADR, freeze notice, or gate status is amended, relaxed, or superseded by this ADR. |
| Source | `evidence/GOVERNANCE_DECISIONS_20261009.jsonl`; `RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` §1.1, §1.3, Appendix E; `evidence/provenance_correction/OPERATOR_ATTESTATION.md`; `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5; `docs/adr/ADR-013` (untracked, not adopted — cited only as the claim being examined) |
| Authority basis | **None independently established.** The claimed basis is an explicit delegation in an operator session that is **not** in this repository and **not cryptographically authenticated**. See §7.2, §12.2. |
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

### 3.1a The issuer-list boundary (added after the audit of `36329f0ab`)

Checks (1)–(10) are all satisfiable by a file the agent writes itself. The
independent audit of `36329f0ab` demonstrated the consequence directly: a
delegation naming an issuer that had never existed —
`"Queen-Of-Authority-Who-Does-Not-Exist"` — was accepted, and a decision was
adopted under it. A content hash proves only that a record is consistent with
the data used to compute that hash; it proves **nothing about who created or
authorised that data**. **Naming is not authentication.**

So authority now requires two facts from two separate artifacts:

| | Artifact | What it establishes |
|---|---|---|
| 1 | the delegation record | *what* is proposed to be authorised |
| 2 | the trusted-issuer list `evidence/governance/TRUSTED_ISSUERS.json` | *that this issuer identifier is listed* — nothing more |

A delegation's `delegating_principal` must **match** an `issuer_id` in the
trusted-issuer list. Otherwise the decision is refused.

**What the list is, precisely.** It is a tracked file in the same repository and
branch. At the audited revision, **no** repository-level `CODEOWNERS` rule,
active Git hook, pre-commit rule, CI enforcement rule, or signature-verification
mechanism was found that independently controls admission of trusted issuers.
The repository does **not** establish independent authorship or authentication
for entries in this file. *This finding is limited to the repository and the
mechanisms inspected; it does not establish the absence of external hosting
controls.*

**What `TrustedIssuer.validate()` actually does** — verified against the
implementation, not asserted:

- performs structural and format validation of the declared fields;
- rejects an `issuer_id` or `verified_by` carrying the `agent:` prefix;
- checks that `verified_at` parses as an ISO-8601 instant with an explicit offset;
- requires `evidence_refs` to be non-empty.

**What it does not do:**

- it does **not** authenticate the person behind `issuer_id` or `verified_by`;
- it does **not** verify any signature and does **not** establish a trusted key;
- it does **not** establish that the targets named in `evidence_refs` exist.

**The structural limitation, stated plainly:** adding a structurally valid
`TrustedIssuer` record causes the trust check to succeed whenever its
`issuer_id` matches the delegation's issuer and the remaining checks pass. This
was confirmed against the running implementation. The list is therefore **not
an authenticated trust boundary** — it is currently empty, and empty is the only
thing holding agent authority at zero.

**The store ships EMPTY.** This repository has no signature substrate, no
identity provider, and no trust root, so there is nothing that could honestly
verify an issuer. Populating it with an entry would record a *claim* of
verification, and would not make one. Consequently:

> **At the audited revision, with the store empty, no machine-agent delegation
> confers effective authority and no machine-agent decision can be ADOPTED.**

This is fail-closed *by configuration*, not by an enforced boundary. It must not
be "fixed" by an agent adding itself — `TrustedIssuer.validate()` refuses an
`agent:` `issuer_id` and an agent `verified_by` — but it would equally not be
stopped by an agent adding a non-`agent:` identifier. See §7.8.

Note the limit, stated rather than hidden: `TrustedIssuer` is a **claim of
verification**, not the verification. The same was true of a human principal's
name before any of this (§2.1).

### 3.2 What this prevents

| Attack | Refused by | What this actually stops |
|---|---|---|
| An agent writes its own name into `authority_principal` and nothing else | (1)+(2): no delegation ref / no delegation | yes |
| An agent writes a rule declaring itself authorized | §0: the rule names no grantee | yes |
| An agent names itself in the `agent:` namespace as the delegation's issuer | `delegating_principal` must not be an `agent:` principal and must differ | **only that naming pattern.** It does not authenticate an issuer, does not prove the issuer exists, and does not prove the issuer authorised the delegation. A fabricated **non-`agent:`** string passes this specific check. See §3.1a, §7.7, §7.8. |
| An agent widens a delegation after the fact | `scope_decision_ids` is content-hashed; changing it changes the hash and breaks the pin | yes — but a content hash shows consistency with the hashed data, **not** who created or authorised it |
| An agent acts outside its window | (9) | yes |
| An agent acts after revocation | (7) | yes |
| An agent adopts a reserved-class decision (G3, ADR, invariant extension) | (6) plus the declared-class and substantive-effect checks in §2.3 | yes, and no longer id-dependent |
| An agent lists a fabricated issuer in `TRUSTED_ISSUERS.json` and names it in a delegation | the issuer identifier must appear in the list — which is empty at the audited revision | **no.** This is a *membership* check, not authentication. Adding a structurally valid entry makes it pass. See §7.8. |
| A delegated decision is presented as a GLM ruling | §2.2: `agent:` is never GLM; test-pinned | yes |
| A delegated decision is presented as human operator attestation | §2.2 + the attestation file remains unsigned | yes |

**Summary of what this section does and does not claim.** The delegation
mechanism constrains *scope, timing, revocation, transition shape, reserved
class, and identifier namespace* — all enforced in code. It does **not** establish
who any named issuer is, whether they exist, or whether they authorised
anything. The audit's finding F2 (arbitrary-issuer authority minting) is
therefore **not fully closed**; what changed is that the empty issuer list means
no issuer currently qualifies. See §7.8.

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
| Seed generator emits proposals only | unchanged — it cannot emit a ruling. **It is not, however, protected from destroying one:** see §10.1 and the correction at §12. |
| G3 **NOT ACCEPTED** | unchanged |
| P4/RSI freeze ACTIVE | unchanged |
| `OPERATOR_ATTESTATION.md` unsigned | unchanged — see §8 |

## 7. Honest limits of this mechanism (normative disclosure)

This ADR must not be read as stronger than it is.

1. **It does not authenticate anyone.** The registry verifies that a delegation
   record exists, is internally consistent, is content-hash-pinned, is
   un-revoked, is in-window, is scoped to the decision, and that its issuer
   identifier **is listed** in `evidence/governance/TRUSTED_ISSUERS.json`
   (§3.1a). Listing is **not** authentication. It does **not** verify that the
   human behind that issuer is who they claim to be, because it cannot: there is
   no signature or identity substrate here. `TrustedIssuer` is a *claim of
   verification*. The same residual always existed for human principals (§2.1) — a
   free-text name has never been proof of anything — and §3.1a makes it explicit
   for agent principals instead of hiding it.
2. **A delegation record written by the agent is agent-authored.** In this
   workstream `evidence/governance/EXECUTOR_DELEGATION_20261011.json` was written
   by the same agent that used it. The record therefore carries
   `authored_by: "agent:executor_v-2"` and
   `verification_status: "UNVERIFIED_BY_THIRD_PARTY"`. An auditor must verify
   the claimed session delegation against the commissioning task packet, **which
   is not in this repository**. Until that check happens, decisions adopted
   under it are structurally valid but not third-party authenticated, and this
   ADR says so rather than implying otherwise. **In the event, no such check
   was forthcoming: the four adoptions made under it have been retracted. See
   §12.**
3. **This is a disclosure, not a defence.** The record can be read by anyone and
   its unverified status is stated on its face and in every decision record that
   relies on it.
4. **A test suite is not authentication.** Passing tests show the mechanism
   behaves as specified. They show nothing about who actually delegated.
5. **The reserved-class check is now two-layered but one layer is a heuristic.**
   The declared `authority_class` is structural. The substantive-effect marker
   scan looks for phrases, not meaning. See §10.2.
6. **The seed generator was unprotected.** See §10.1 and §12.
7. **The naming check in (1) of §3 is not authentication.** Rejecting an `agent:`
   issuer stops one shape of self-delegation. It never established that the
   named issuer exists. The audit proved this: any other string passed. §3.1a
   adds a *membership* check on top, which is also **not** authentication — see
   §7.8 — and §3.2 states plainly which rows are complete and which are not.
8. **Trusted-issuer admission is not independently authenticated.** See §7.8.

### 7.8 Trusted-issuer admission is not independently authenticated

Three distinct things are being claimed, and only the first is currently true.

**Current configuration.** The trusted-issuer list
`evidence/governance/TRUSTED_ISSUERS.json` is **empty** at the audited revision.
With it empty, the existing registry configuration withholds effective agent
authority: `GovernanceRegistry.effective_authoritative()` returns nothing for any
machine-agent principal, and `unverified_authority_records()` reports the four
historical adoptions as unverified.

**Structural limitation.** Adding a **structurally valid** `TrustedIssuer`
record causes the trust check to **succeed** whenever its `issuer_id` matches the
delegation's issuer and the remaining checks pass. This was confirmed against
the running implementation: a delegation naming an issuer that had never been
verified, together with a `TrustedIssuer` entry naming an unresolvable evidence
path, was sufficient for a decision to reach `ADOPTED`. The current repository
implementation does **not** independently authenticate the issuer, does not
verify any signature, does not establish a trusted key, and does not establish
that a human or the architecture authority approved the entry. The list is a
membership list, not an authenticated trust boundary. **The empty list is a
configuration state, not an enforced boundary**, and must not be described as
one.

**Runtime limitation.** The audit that produced this finding was **static**. It
did not execute the registry in a production context, and it did not establish
that any production runtime currently constructs a `GovernanceRegistry` from
these files, nor that any code path loads the trusted-issuer list at all. It is
therefore not claimed here that this is reachable through a production entry
point. Establishing reachability would require enumerating production consumers
of `GovernanceRegistry` and of the JSONL ledger, which this correction does not
attempt.

**Conclusion.** The current implementation must **not** be described as
independently authenticated, and neither the issuer list nor the delegation
record should be cited as evidence that a decision was authorised by a human or
by the architecture authority. Before any issuer could be considered
independently authenticated, an **external** identity or verification mechanism
would have to be established — for example a signature scheme with trust roots
held outside this repository, or an identity provider whose assertions the
registry could verify. No such mechanism exists here, and none was invented to
close this section.

---

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

### 10.1 The seed generator can still truncate decision history

`scripts/gen_governance_decision_seeds.py` writes the ledger from the eleven
seeds. **Re-running that script against the current ledger would overwrite the
file and delete every record the generator did not produce** — which now
includes not only the four retracted adoptions but their four retraction
records.

A refuse-to-overwrite guard was written for this, and then **deliberately
removed**. `tests/test_historical_split_adjudication_package.py::test_no_historical_script_or_test_was_modified_by_the_package`
protects the whole of `scripts/` as census input for the historical split
adjudication package (`CODE_ROOTS` includes `scripts`), and that guardrail is
not within that workstream's authority to change.

**Corrected at §12.4:** the post-audit remediation *did* obtain the narrow
exception needed and the guard now exists. The residual above is retained to
record that it was real, that it was found by an independent audit rather than
by the implementer, and that the first response to it — removing the fix — was
the wrong one.

### 10.2 The reserved-class check is two-layered, and one layer is a heuristic

Reserved protection is no longer a hard-coded id list alone:

1. **Declared `authority_class`** — every ruled record must declare what kind of
   authority act it is, and `GATE_ACCEPTANCE`, `INVARIANT_EXTENSION`,
   `ADR_ADOPTION`, `FREEZE_LIFT` are refused for a machine agent regardless of
   id. A *future* reserved decision therefore cannot slip through merely
   because nobody registered its id. This layer is structural.
2. **Substantive-effect marker scan** — a record that declares `OPERATIONAL`
   while its text announces "G3 ACCEPTED", "FREEZE LIFTED", "ADR ADOPTED" or
   similar is refused. **This layer is a heuristic**: it matches phrases, not
   meaning, and cannot be complete. It exists to close the "alter only the
   description" evasion, not to replace a reviewer reading the text.

`RESERVED_DECISION_CLASSES` (by id) remains as defence in depth. The limit of
any of this: a sufficiently determined author who writes prose that avoids the
markers *and* declares `OPERATIONAL` will pass the mechanical checks. That is
why the marker list is documented as a backstop, and why no test result is
evidence that a proposal's substantive effect was correctly classified.

### 10.3 `is_authoritative()` is structural, not contextual

The audit found that `OperatorDecisionRecord.is_authoritative()` returned
`True` for a record referencing a delegation that did not exist — it had no
registry context and therefore could not check one. It is now explicitly a
**structural** check (status, principal, declared class, delegation-ref
presence) and is documented as necessary-but-never-sufficient. The **effective**
query is `GovernanceRegistry.effective_authoritative()` (also reachable under
its former name `authoritative()`), which re-runs the full delegation and trust
check against this registry's context. `authority_problems()` reports *why* a
record was withheld rather than silently omitting it.

## 11. (intentionally unused)

This heading is retained as a deliberate placeholder so that no section number
appears to have been deleted from this document. Section 11 was reserved during
the post-audit correction and never carried content; nothing was removed. The
next substantive section is §12.

## 12. Retraction of the four adoptions made under this ADR

Added after the independent audit of `36329f0ab4278106a872574c61bcf5af02789b65`.
Everything below is read from the ledger; no identifier here is invented.

### 12.1 What happened

`36329f0ab` appended four `ADOPTED` records under delegation
`DEL-2026-10-11-01`. An independent audit concluded that those adoptions' authority
could not be established, and the four were retracted by appending four
`INVALIDATED` records. **The adoption events were preserved, not deleted.**

| Decision | adoption (ledger line, `decided_at`) | retraction (ledger line, `decided_at`) |
|---|---|---|
| `GD-2026-10-11-01` | 12, `2026-10-11T12:38:53Z`, hash `5664c624…` | 16, `2026-10-11T16:07:27Z`, hash `cd09d25a…` |
| `GD-2026-10-11-02` | 13, `2026-10-11T12:38:53Z`, hash `9ad32747…` | 17, `2026-10-11T16:07:27Z`, hash `dd3dbc5b…` |
| `GD-2026-10-11-04` | 14, `2026-10-11T12:38:53Z`, hash `8354471f…` | 18, `2026-10-11T16:07:27Z`, hash `df0997d2…` |
| `GD-2026-10-11-05` | 15, `2026-10-11T12:38:53Z`, hash `278335c1…` | 19, `2026-10-11T16:07:27Z`, hash `92cebc61…` |

Resulting ledger: **19 records — 7 `PROPOSED`, 4 `INVALIDATED`, 0
authoritative.** The eleven origin proposals (lines 1–11) are byte-identical to
the parent commit `0978d13d` and retain their original content hashes.

### 12.2 Why the adoptions' authority could not be established

1. `delegating_principal` is `operator-role:session-delegator-2026-10-11`, which
   the delegation record itself labels *"ROLE LABEL, NOT AN IDENTITY"*.
2. The delegation was `authored_by: "agent:executor_v-2"` — the same machine
   agent that acted under it.
3. It carried `verification_status: "UNVERIFIED_BY_THIRD_PARTY"` from the start.
4. The commissioning task packet it relies on **is not in this repository**.
5. `RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` §1.1 defines two lanes (GLM and the
   implementation agent) and establishes **no operator governance-ratification
   role**. The "operator is the ratifier" premise traced only to agent-authored
   proposals and to ADR-013, which is **untracked** and self-declared
   `Proposed — recorded, NOT adopted`, `Deciders: *Unassigned.*`
6. `evidence/governance/TRUSTED_ISSUERS.json` is **empty**, so no delegation in
   this repository can confer effective authority.

### 12.3 What `INVALIDATED` does and does not mean

It means: *an adoption event occurred, is preserved immutably, and confers
nothing.* It is **not**:

- a **rejection** — no human operator and no GLM ruled against the substance of
  any of the four proposals, which therefore remain **open and unratified**;
- a **supersession** — no successor decision exists;
- a claim that the proposals were wrong.

The four decisions may still be ratified later by a genuinely authorised
principal (`INVALIDATED → ADOPTED` is a legal transition).

### 12.4 Independent issuer authentication remains unavailable

No issuer authentication was achieved, and none is claimed. The registry
verifies delegation structure, scope, window, revocation, transition permission,
reserved class, and trust-store membership. It **cannot** verify that a
consenting human exists behind any issuer name: this repository has no signature
substrate, no identity provider, and no trust root, so the trusted-issuer store
ships **empty**. Populating it is a governance act reserved to a human or the
architecture authority, and `TrustedIssuer.validate()` refuses an `agent:` issuer
and an agent `verified_by`.

### 12.5 Unchanged

- `OPERATOR_ATTESTATION.md` remains **`PENDING — NOT SIGNED`**; every human
  identity field remains `*UNSET*`. No human identity was invented.
- **G3 remains `NOT ACCEPTED`**; the P4/RSI freeze remains `**ACTIVE**`;
  **ADR-013 remains `PROPOSED / NOT ADOPTED`** and untracked.
- **`GD-2026-10-11-03` remains `PROPOSED`** (ledger line 9, one version, no
  authority), pending the GLM architecture ruling its legacy weld-perimeter
  component requires. No GLM ruling was fabricated or inferred.
- **No engagement grant was issued.** `GD-2026-10-11-05` had ratified a *process*,
  never a capability — and that ratification is itself now retracted.
- **ADR-014 is not independently adopted.** Its `Status` is *recorded —
  prospective*. Nothing in this section, and nothing in the delegation it
  describes, makes it an accepted governance rule.

### 12.6 Referenced by

The four `INVALIDATED` records (lines 16–19) each cite this section in their
`decision_text` as the full account of the retraction.

## 13. References

- `RAPHAEL_MASTER_ROADMAP_v4.2_RSI.md` §1.1 (two-lane authority), §1.1
  mutual-constraint rule, §1.3 (phase lifecycle), Appendix E (precedence)
- `src/orchestrator/rsi/governance_registry.py` (authority model; `AGENT_PRINCIPAL_PREFIX`; `RESERVED_DECISION_CLASSES`; `RESERVED_AUTHORITY_CLASSES`; `DelegationRecord`; `TrustedIssuer`; `effective_authoritative`)
- `evidence/governance/EXECUTOR_DELEGATION_20261011.json` (the delegation record)
- `evidence/governance/TRUSTED_ISSUERS.json` (the trusted-issuer store — EMPTY)
- `evidence/GOVERNANCE_DECISIONS_20261009.jsonl` (ledger; lines 12–19 are the adoption and retraction history)
- `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5 (freeze lift conditions)
- `docs/adr/ADR-013` §3.5 — **UNTRACKED, `Proposed — NOT adopted`, no decider; cited only as the claim being examined, never as authority**
- `docs/adr/ADR-003-broker-pdp-pep-separation.md` (INV-2, INV-3)
- `docs/adr/ADR-006-no-second-cognitive-entry-point.md` (INV-5 single-entry doctrine)
- `evidence/provenance_correction/OPERATOR_ATTESTATION.md`

---

*Status: recorded and prospective. Does not supersede, amend, or accept any
roadmap section, ADR, gate, or freeze. Effective only for a valid, in-window,
un-revoked, correctly-scoped delegation record. Revocable at any time by the
delegating authority.*