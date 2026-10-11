# ADR-015 — G1 Read-Only Governance Status Integration

| Field | Value |
|---|---|
| ADR | 015 |
| Milestone | **G1 — governance integration (observability only)** |
| Status | **Proposed — not independently adopted.** This ADR is authored by a machine agent. Its existence is not approval of it. |
| Deciders | **Unassigned.** No authority has adopted this ADR. It records a scoped implementation; it grants nothing. |
| Supersedes | Nothing. No roadmap section, ADR, freeze notice, gate status, or enforcement path is amended by this ADR. |
| Scope | Adds a read-only loader and one read-only status surface. **No enforcement, no capability grant, no new decision authority.** |
| Date | 2026-10-11 |

---

## 0. Status semantics (read first)

- This ADR is a **record of a scoped change**, not an approval and not an
  authority. Creating it confers nothing.
- G1 introduces **no enforcement**. The production Broker/PEP decision path is
  byte-unchanged by this milestone.
- G1 grants **no capability** and creates **no decision authority**.
- The trusted-issuer store remains **empty**. G1 did not populate it.
- **Independent issuer authentication remains unresolved** — see §5.
- **G2 and G3 are out of scope** and were not implemented.

---

## 1. Context — why this milestone exists

An independent audit classified the governance registry as **`DORMANT`**: no
production consumer existed, so nothing in the runtime could observe what the
ledger actually says. That is an observability and integration-testability gap,
not an authorization gap.

The registry itself was sound. It was simply invisible. A governance record that
cannot be inspected cannot be audited, and an audit that cannot see the current
state cannot tell "nothing is in force" apart from "nothing was checked".

**G1's goal is observability. It is explicitly not authorization.**

## 2. What G1 adds

### 2.1 `src/orchestrator/rsi/governance_registry_io.py` — one reusable loader

A single read-only entry point, `load_ledger(repo_root)`, that:

1. resolves the ledger, delegation record, and trusted-issuer store relative to
   an **explicitly supplied** repository root (no default, no search-up-tree, so
   a caller cannot accidentally load a different repository's governance state);
2. reads without modifying;
3. parses the ledger through the canonical
   `GovernanceRegistry.from_jsonl(...)`;
4. loads delegations and issuers through the registry's supported interfaces
   (`load_delegations`, `load_trusted_issuers`);
5. returns the inspectable registry **plus** a structured account of authority
   problems and unverified historical records;
6. preserves historical decision events even when their authority is unverified;
7. reports unverified records explicitly rather than discarding them;
8. returns effective authority via the **contextual** API
   `effective_authoritative()` — never the structural-only `is_authoritative()`;
9. fails closed on a missing, unreadable, malformed or inconsistent **required**
   artifact; and
10. distinguishes an *invalid artifact* (hard error) from a *valid historical
    ledger whose authority cannot be verified* (loads, and is reported).

The loader **cannot** append, update, invalidate, or adopt a decision; write or
repair JSONL; populate the trust store; generate a delegation; change policy or
capability configuration; or trigger actions or network requests.

### 2.2 `scripts/raphael_governance_status.py` — one status surface

Exactly one. It delegates all parsing and authorization to the loader and
contains no ledger logic of its own. It reports record counts by status,
historical adoption-event count and ids, effective-authority count and ids,
unverified-authority records with reasons, authority problems by decision id,
whether the trusted-issuer store is empty, GD-03's status, the unresolved
authentication limitation, and the fact that reading status authorises nothing.

All counts are **derived from the loaded registry**. None are hardcoded.

Exit codes distinguish the states a caller must not confuse:

| Code | Meaning |
|---|---|
| `0` | governance state was **observed** successfully |
| `1` | a required artifact was missing, unreadable, or invalid (**fail-closed**) |
| `2` | usage error |

`0` means "read successfully" — it does **not** mean "authority granted". A
failure is never reported as an empty registry, never silently skips invalid
records, and never reports zero authority when the loader actually failed.

## 3. Loading is not authorising

These are kept separate, because conflating them is what made the registry
untrustworthy before:

- **Loading** reads the ledger into memory. A *valid historical* ledger whose
  delegation evidence cannot be independently verified still loads — otherwise
  the record of an unauthorised adoption would become unauditable, which is the
  opposite of what an audit trail is for.
- **Authorising** is what `effective_authoritative()` computes. It re-runs the
  full delegation and trust-store checks and returns nothing when they fail.
- An **invalid** artifact is a third thing entirely, and is always a hard error.

The status surface surfaces all three distinctly. A consumer can tell "nothing
is in force" from "we could not read" from "this is unverified history".

## 4. What G1 does NOT do

G1 **did not** modify:

- `src/orchestrator/auth.py`
- `src/orchestrator/brain/capability_broker.py`
- `src/orchestrator/runtime/policy.py`
- `src/orchestrator/runtime/types.py`
- `src/orchestrator/exec/`
- any policy file
- the governance decision ledger
- the delegation record
- the trusted-issuer store
- the operator attestation

G1 introduces **no production authorization decision dependent on the registry
result**. The status surface is observational only. It is asserted in the tests:
the loader's and the surface's only orchestrator dependency is
`orchestrator.rsi.governance_registry`, verified by AST-level import inspection
rather than by substring matching, because both modules legitimately *mention*
the Broker in prose to say they leave it alone.

## 5. Security limitations carried forward — unchanged by G1

G1 makes these **visible**, and does not fix any of them:

- **Independent issuer authentication is NOT available.**
  `evidence/governance/TRUSTED_ISSUERS.json` is an empty list. This repository
  has no signature substrate, no identity provider, and no trust root.
- `TrustedIssuer.validate()` performs structural and format validation only. It
  does not authenticate a person, verify a signature, establish a trusted key, or
  confirm that `evidence_refs` targets exist. See ADR-014 §3.1a and §7.8.
- A content hash shows consistency with the hashed data, **not** who created or
  authorised it.
- Audit finding **F2** (arbitrary-issuer authority minting) is **not fully
  closed**. What changed is that the empty list means no issuer currently
  qualifies. G1 observes that state; G1 does not change it.

## 6. Current audited state, as reported by the surface

| Item | Value |
|---|---|
| Ledger records | 19 |
| Current `PROPOSED` | 7 |
| Current `INVALIDATED` | 4 |
| Current `ADOPTED` | 0 |
| Historical adoption events (preserved) | 4 |
| **Effective authority** | **0** |
| Unverified authority records | 4 |
| Trusted issuers | 0 (store empty) |
| `GD-2026-10-11-03` | `PROPOSED` |

The four invalidated decisions remain invalidated; their adoption events remain
discoverable as history.

## 7. Unchanged governance state

- **G3 remains `NOT ACCEPTED`.** G1 does not advance or accept any gate.
- **The P4/RSI freeze remains `ACTIVE`.** G1 lifts nothing.
- **ADR-013 remains `PROPOSED / NOT ADOPTED`** and untracked. G1 does not adopt
  it, and nothing here implies adoption.
- **`OPERATOR_ATTESTATION.md` remains `PENDING — NOT SIGNED`**, with every human
  identity field `*UNSET*`. G1 fills no human identity field.
- **`GD-2026-10-11-03` remains `PROPOSED`**, pending the GLM architecture ruling
  its legacy weld-perimeter component requires. No GLM ruling was fabricated.
- **No engagement grant was issued.**
- The four earlier proposals remain **open and unratified**.

## 8. Out of scope

**G2** (governance enforcement / Broker integration) and **G3** (gate
submission) are **not** implemented and **not** authorised by this milestone.
G1 is observability only; wiring governance into an authorization decision is
explicitly out of scope and would require its own authority.

## 9. Tests

`tests/test_rsi1_governance_registry_io.py` — 27 focused tests covering: valid
ledger loading; read-only behaviour with byte-level artifact digests; historical
adoption events remaining visible; the four invalidated decisions not counting as
authoritative; zero effective authority with the empty trust store; authority
problems and unverified records reported; fail-closed handling of missing,
malformed, and hash-inconsistent ledgers; fail-closed handling of malformed
delegation and trust-store artifacts; a malformed trust store never silently
granting authority; the surface exposing no mutating operation; the surface
leaving all input bytes unchanged; structural-only results never presented as
effective authority; valid-but-unverified remaining distinct from unreadable;
exit codes distinguishing observation from failure; and AST-level proof that the
enforcement path is not imported.

Malformed-input cases use isolated `tmp_path` fixtures. The real repository
ledger is only ever read, and its digest is asserted unchanged.

## 10. References

- `src/orchestrator/rsi/governance_registry_io.py` (the loader)
- `scripts/raphael_governance_status.py` (the status surface)
- `tests/test_rsi1_governance_registry_io.py`
- `src/orchestrator/rsi/governance_registry.py` (canonical registry; unmodified by G1)
- `docs/adr/ADR-014-bounded-operator-delegation-to-machine-agent.md` §3.1a, §7.8
  (the trust-boundary limitations G1 reports)
- `evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md` §5 (freeze remains active)
- `evidence/g3_remediation/STATUS.md` (G3 remains NOT ACCEPTED)
- `docs/adr/ADR-013` — **untracked, NOT adopted**; not modified and not endorsed here

---

*Status: Proposed — not independently adopted. Deciders: Unassigned. G1 is
observability only: no enforcement, no capability grant, no new decision
authority, no trust-store population, no freeze lifting, and no re-adoption of
the invalidated decisions.*