# RSI-1 POLICY IDENTITY — re-derivation design note and residual-risk record

**Date**: 2026-10-09
**Branch**: `governance/rsi-1-blockers` (stacked on `audit/f-split-1`, which is
stacked on the frozen baseline `b6ef24bdb`)
**Scope**: policy-identity workstream only. Not Phase 3. No commit made.

> **SUPERSEDED IN PART — 2026-10-09, operator ruling "Policy Artifact Authority
> Resolution".** §1 below records the analysis that *preceded* the ruling and is
> kept because it establishes exactly what was missing and why the answer could
> not be a parameter. The ruling has since been implemented as a campaign-scoped
> policy manifest bound to adoption state; see
> `reports/POLICY_MANIFEST_AUTHORITY_2026-10-09.md` for the implemented design,
> trust chain, and test coverage. §1's "Disposition: fail-closed, unchanged" now
> applies only to configurations with **no** manifest binding, which remains the
> correct default. §2–§5 are unchanged and remain current.

---

## 1. Strict-mode re-derivation after restart — the missing dependency

### 1.1 The observed problem

Under `require_policy_identity=True` an honestly admitted record cannot be
re-derived after the process restarts:

```
append(record, strict_config, policy_identities=derived)  -> ADMITTED
DecisionLedger(path).final_states(strict_config)          -> {}
DecisionLedger(path).current_authority(id, strict_config) -> None
```

`final_states()` (evaluation_gate.py:2245) and `current_authority()`
(evaluation_gate.py:2264) call `verify_admission(record, config)` with **no**
`policy_identities`, because those signatures have no parameter to carry them.
Every policy-identity gate is therefore `BLOCKED`, the admission guard refuses,
and the record is excluded from the re-derived surfaces. The stored claim
remains readable via `historical_states()`, which is documented as audit
material only.

This is fail-closed in the safe direction — no record regains authority it
cannot re-prove — but it is an over-restriction, not a correct answer. Pinned as
`test_f5_strict_records_are_not_re_readable_as_current_authority`.

### 1.2 Why adding a parameter is NOT sufficient

Threading `policy_identities` through `final_states()`/`current_authority()`
would let a caller re-derive a record **only if it can name the policy artifact
bytes**. The identity proof must therefore come from somewhere other than the
caller and other than the ledger file. Candidates inspected:

| Candidate source | What it offers | Why it is not usable as identity proof today |
|---|---|---|
| `D1Policy.sha256` / `D2_POLICY_PATH` (`src/orchestrator/runtime/policy.py:191`) | Real SHA-256 over real committed artifact bytes, computed at load, carried into `engagement_id` | It is the **Broker/PEP engagement policy** (`policies/engagement-d*-v1.json`), not the **exploration policy** whose hash lands in `baseline_policy_hash`/`candidate_policy_hash`. Different artifact class. Its digest is also not pinned in any `AnchorSet`. |
| `ExplorationPolicy.content_hash()` (`src/orchestrator/rsi/exploration_policy.py:143`) | SHA-256 over `canonical_dict()` — the right artifact class | Computed from an **in-memory object the caller constructed**. No committed artifact file, and nothing binds the object to bytes on disk. Trusting it means trusting the caller's object, which is exactly the C1/C2 gap. |
| `scripts/run_rsi0_eval.py::candidate_policies()` | The only place exploration policies are actually constructed today | A **script**, not a pinned artifact. Policies are built in-process and never written to a digest-pinned file. |
| The ledger JSONL itself | Contains the record's declared hashes | Explicitly excluded by the task and by the module's own design: an identity read from the ledger proves only that the ledger agrees with itself. |
| `AnchorSet` | Holds three pinned anchors: holdout manifest, evidence index, adopted-config registry | **Has no policy-artifact anchor field.** Confirmed by inspection of the dataclass. |

### 1.3 Exact missing dependency

Two things are missing, and both are operator/governance artifacts, not code:

1. **A committed exploration-policy artifact.** Exploration policies are
   currently in-memory objects. Nothing writes canonical bytes to a tracked
   file, so there is nothing for `derive_policy_identity()` to hash on a restart.
2. **A digest pin for those artifacts.** Even given (1), re-derivation needs to
   know *which* artifact is authoritative for a given campaign, without asking
   the record. `AnchorSet` has no such field, and adding one is an authority
   change with the same operator weight as the holdout anchor.

Until both exist, **no API change can make strict-mode records re-readable**, and
any that appeared to would be laundering a caller-supplied identity into
authority — precisely the defect the flag was introduced to close.

### 1.4 Minimal API proposal (NOT implemented — requires the artifacts above)

Should the operator adopt committed, digest-pinned exploration-policy artifacts,
the minimal shape is a **keyword-only** pass-through on the two re-derivation
surfaces, mirroring the existing `verify_admission` signature:

```python
def final_states(self, config, *, policy_identities: Tuple[PolicyIdentity, ...] = ()
                 ) -> Dict[str, str]: ...

def current_authority(self, decision_id: str, config, *,
                      policy_identities: Tuple[PolicyIdentity, ...] = ()
                      ) -> Optional[EligibilityAssessment]: ...
```

Invariants this proposal must preserve:

- default `()` preserves today's fail-closed behavior exactly;
- keyword-only, so no positional widening of an authority-adjacent API;
- callers pass `PolicyIdentity` objects built by `derive_policy_identity` from
  **bytes they can name from a pinned source**, never a digest string — the
  existing `derive_policy_identity` already refuses non-bytes content and takes
  no digest parameter (`test_a2`, `test_a3`);
- no ledger-sourced identity path may be added.

The trust source for re-derivation would then be: **the committed, digest-pinned
exploration-policy artifact**, named by an `AnchorSet` field — the same shape as
`adopted_config_registry_file`. That field does not exist and this note does not
create it.

### 1.5 Disposition

**Fail-closed, unchanged.** No implementation, no new anchor field, no new
registry. Awaiting operator decision on whether exploration-policy artifacts
should be committed and digest-pinned at all.

---

## 2. Classification semantics — investigated, no defect found

### 2.1 Why `INDEPENDENT_HOLDOUT` while the candidate gate is `BLOCKED`

The state ladder in `_classify_with_authority` is strictly ordered
(evaluation_gate.py:1851–1879):

1. any `REFUSE` gate → `UNVERIFIABLE_INPUTS`
2. record claims no holdout evaluation → `LOCAL_REPLAY`
3. anchored holdout not `VERIFIED` → `UNVERIFIABLE_INPUTS`
4. adequacy not `ADEQUATE` → `STATISTICALLY_INADEQUATE`
5. **any** `BLOCKED` gate → `INDEPENDENT_HOLDOUT`
6. otherwise → `PROMOTION_ELIGIBLE`

A blocked policy-identity gate is not special-cased at step 5, so it lands in
the generic "open conditions remain" bucket. That is semantically correct:
`INDEPENDENT_HOLDOUT` means *"a verified holdout was evaluated and open
conditions remain"* — which is precisely the true description of a record with
one verified and one unverified policy role. It is not a weaker form of
promotion; it is the absence of promotion.

### 2.2 Downstream consumers — none

Verified by inspection and now pinned by `test_j3_no_production_consumer_treats_the_state_as_promotion`:

- `STATE_INDEPENDENT_HOLDOUT` and `STATE_PROMOTION_ELIGIBLE` have **zero**
  references outside `evaluation_gate.py` itself. Repo-wide grep over `*.py`
  excluding `tests/` returns nothing.
- `classify_promotion_eligibility` and `build_authority` are called only from
  within `evaluation_gate.py`. No production module imports them.
- `snapshot.py` does not consume classification state.
- Promotion, deployment, and rollback entry points do not exist for this
  subsystem. Promotion is a report, never an action.

### 2.3 The state cannot be mistaken for promotion

- `PROMOTION_ELIGIBLE` is reachable only when `blocked` is empty, so a
  `BLOCKED` policy gate and `PROMOTION_ELIGIBLE` are mutually exclusive by
  construction. Pinned by `test_j1`.
- A record declaring the weaker `INDEPENDENT_HOLDOUT` under a config that
  derives `PROMOTION_ELIGIBLE` is refused on `final_state mismatch` — it cannot
  be laundered upward or downward past the fresh derivation. Pinned by
  `test_j2`.
- The admission guard independently refuses the blocked record regardless of
  the state it declares (`test_i2`).

**No authority inconsistency. No correction made** — changing the ladder would
alter behavior for every blocked gate, which is out of scope and unjustified.

---

## 3. Residual: direct JSONL injection into the decision ledger

### 3.1 Trust boundary

`DecisionLedger.append()` is the only sanctioned write path. The ledger file is
plain JSONL and `DecisionLedger.__init__` re-reads it **without re-running
admission**. The boundary is therefore:

- **Enforced (verified):** anything that consults *re-derived* authority. An
  injected record cannot appear in `final_states()` or
  `current_authority()`, because both re-run `verify_admission` against
  currently derived authority. Proven for four distinct attack shapes:
  - `test_f2` — a record admission refused, then written directly: no
    authoritative state surfaces.
  - `test_f3` — a forged record claiming `PROMOTION_ELIGIBLE`: stored claim
    readable, derived authority `None`, `final_states()` empty.
  - `test_g3` — mixed derived/asserted identity written directly: excluded on
    re-read.
  - `test_f5` — honest strict-mode record: admitted, then also excluded on
    re-read (the §1 over-restriction, fail-closed).
- **Not enforced:** anything that reads *stored* state as if it were authority.
  `get()`, `all()`, and `historical_states()` return injected bytes. This is
  documented and deliberate — the ledger is append-only and truthful about what
  it physically holds.

### 3.2 The residual that remains

`_check_lineage()` (evaluation_gate.py:2119) reads `self._index`, the **stored**
index, and calls `self._latest_for_candidate()`. An injected record therefore
participates in lineage reasoning.

- **Cannot grant authority.** Proven by `test_f4`: a planted record with a
  conflicting candidate hash neither gains authority nor displaces a later
  honestly admitted record.
- **Can deny later honest writes.** `_check_lineage` raises when a candidate
  moves from one state to `PROMOTION_ELIGIBLE` without a genuinely new
  `inputs_digest` and a named parent. A planted record claiming
  `PROMOTION_ELIGIBLE` for a candidate hash can therefore make a subsequent
  legitimate record for that hash fail admission. This is a **denial-of-service
  against the ledger**, not a privilege escalation.

### 3.3 Why no hardening was added

The injection vector requires filesystem write access to the ledger file. An
attacker with that access can already delete or rewrite history outright, and
the ledger is explicitly append-only by *convention* rather than by
cryptographic chaining. Mitigating the lineage-specific consequence would mean
either:

- binding stored lineage entries to re-derived authority (a behavioral change to
  `_check_lineage` affecting non-strict configs too), or
- chaining ledger records by content hash (a new integrity subsystem).

Both exceed this bounded review-resolution task. **Scope change deliberately not
taken.** Recorded here instead.

### 3.4 Relevant tests

`test_f1`, `test_f2`, `test_f3`, `test_f4`, `test_f5`, `test_g3`, plus the
append-side `test_d1`–`test_d4`.

---

## 4. `policy_identities` and the banned-parameter guards

**Determination: `policy_identities` must NOT be added to the `test_b0` /
`test_b13` banned-parameter guards.**

Those guards exist to pin the *absence* of the audit's decisive exploit
parameters — `independent_holdout`, `adequacy`, `safety_outcomes`,
`config_adoption` — each of which let a caller assert authority directly. Both
guards assert an **exact parameter set**:

```python
assert set(params) == {"record", "config", "blocking_conditions", "policy_identities"}
```

`policy_identities` is categorically different. It carries **evidence content
derived inside the authority module**, not authority asserted by the caller:

- `derive_policy_identity()` takes artifact **bytes**, never a digest, and
  raises on non-bytes content (`test_a2`) and exposes no `digest`/`sha256`/
  `hash` parameter (`test_a3`).
- `asserted_policy_identity()` marks `derived=False`, and that mode can never
  turn a gate green (`test_c3`, `test_g4`).
- A derived-vs-declared mismatch refuses **unconditionally**, independent of the
  flag (`test_b2`, `test_b3`, `test_c5`).

Adding the name to a ban list would be asserting that supplying policy identity
is itself the exploit, which inverts the mechanism's purpose and would block the
only honest path (`test_d1`).

**The correct guard for this parameter is the one already present**: the exact-set
assertion in `test_b0` and `test_b13` freezes the signature so no *further*
authority-shaped parameter can be added later without failing a test. That
requirement is met. No guard was changed.

Residual: the exact-set assertion pins the *name set*, not the *type discipline*
of the values. Type discipline is covered separately by `test_a2`/`test_a3`/
`test_a5`. Adequate for the current API.

---

## 5. Summary of dispositions

| Item | Disposition |
|---|---|
| Strict-mode re-derivation | **Unresolved — needs operator decision.** Missing: a committed exploration-policy artifact and a digest pin for it. No API implemented; path stays fail-closed. Pinned by `test_f5`. |
| Admission guard non-vacuity | Pinned by `test_i1`–`test_i4`; mutation-verified (deleting the guard fails 4 tests). |
| `INDEPENDENT_HOLDOUT` semantics | **No defect.** State is non-promotional by construction; zero production consumers. Pinned by `test_j1`–`test_j3`. No code changed. |
| Planted-record lineage residual | Recorded (§3). Denial-only, requires ledger write access. Hardening deliberately out of scope. |
| `policy_identities` in ban guards | **Must not be added** (§4). Guards already freeze the signature by exact set. No guard changed. |
| `require_policy_identity` default | Remains `False`; not in `PROMOTION_REQUIREMENTS`; no adoption record created. Pinned by `test_h3`. |