# RSI-1 PROVENANCE CORRECTION REPORT — 2026-10-09

**Branch:** `governance/rsi-1-provenance-correction` (created from
`governance/rsi-1-phase3-readiness`; no merge, rebase, or cherry-pick)
**Audited starting commit:** `1fd7cda7610aa7a6cda56b5c5d9955aed771d674`
**Audited starting tree:** `49237b060d78ad0d9d1f9ad33b8ea073853a3b1f`
**Corrective pre-bundle commit:** `2d049e2f51f3382f06311e43907266e65fd2acc4`
**Corrective pre-bundle tree:** `191ae07eb954498b828d6668e70e6c7b0b65a73e`

> A commit cannot contain its own tree SHA any more than it can contain its own
> commit SHA. This report therefore pins the tree of the last CONTENT commit; the
> evidence-bundle commit that follows adds only files under
> `evidence/provenance_correction/`. Verify with
> `git rev-parse 2d049e2f51f3382f06311e43907266e65fd2acc4^{tree}`.

> **This report does not authorize Phase 3.**

---

## 1. Starting state

```
branch: governance/rsi-1-phase3-readiness
HEAD:   1fd7cda7610aa7a6cda56b5c5d9955aed771d674
tree:   49237b060d78ad0d9d1f9ad33b8ea073853a3b1f
working tree: clean (0 porcelain lines)
```

Baseline `b6ef24bdb` and F-SPLIT-1 checkpoint `c1eab3dd2` are both present and
are ancestors of this branch.

---

## 2. Every corrected audit finding

### 2.1 Evidence binding — **corrected**

`FINAL_COMMIT_SHA.txt` recorded `948f97c85…`, the **parent** of the audited
commit, and could never have satisfied its own check.

- Removed `evidence/phase3_readiness/FINAL_COMMIT_SHA.txt`.
- Added `evidence/phase3_readiness/EVIDENCE_BINDING.json` binding to
  `binding_type: TREE_SHA`, commit `1fd7cda76`, tree `49237b06…`, with the
  explanation and `"phase3_authorized": false`.
- `REMEDIATION_MANIFEST.json` no longer carries `final_commit_sha`; it records
  `remediation_commit_sha`, `remediation_tree_sha`, and
  `evidence_binding_explanation`.
- The false claim *"Policy identity remediation (21/69 tests pass)"* is
  removed and replaced by the verified **69/69**, backed by a new
  `policy_identity_suite_result` field.
- `SHA256SUMS` regenerated; `sha256sum -c` → 6/6 OK.

**Tests:** `tests/test_phase3_evidence_binding.py` — **21 passed**. The recorded
SHAs are re-derived from git in-test, so editing a constant on both sides cannot
pass.

### 2.2 Holdout predecessor — **claim withdrawn**

The classification asserted a quarantined 3,240-row predecessor at
`rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE.jsonl`. That artifact is absent
from the worktree and has **no git object in any branch** — verified again
before correcting.

- `status` changed `QUARANTINED` → **`ABSENT_AND_UNVERIFIABLE`**.
- Added `predecessor_dataset_digest: null`, `predecessor_dataset_commit: null`,
  `predecessor_dataset_verifiable: false`,
  `predecessor_row_count_claim: "UNVERIFIABLE"`,
  `historical_claim_status: "NOT_VERIFIABLE_FROM_REPOSITORY"`, and the required
  statement.
- **The file was NOT recreated.** The canonical holdout remains `MISSING` /
  `UNVERIFIABLE`. The authoritative-anchor manifest is unmodified (measured
  digest still equals the pinned `c26ed773ba57…7577`).

**Tests:** `tests/test_rsi1_holdout_classification.py` — **17 passed**. Includes
a test that fails if the predecessor ever appears in git history, so the
classification cannot silently go stale.

### 2.3 Measurement contract — **reimplemented**

The prior module was a skeleton: `assert_complete()` could never fire,
`UNACCOUNTED` was unreachable, `observed_evidence` was never read, and any
non-`None` digest labelled `"success"` returned `EXPECTED_SUCCESS`.

Rewritten with: `OutcomeCategory` (6 members), `ExperimentCell` (all 9 required
bindings), `GridSpec`, `EvidenceIndex` (digest-pinned, repo-contained),
`GridAccounting`. Every outcome now requires locating the evidence bytes,
recomputing SHA-256 against the digest in the committed index, parsing the JSON,
and confirming the record's own `run_id`. Expected cells use the **real**
`AblationRunner` scheme `abl_{config_id}_{family_id}_s{seed:04d}_{split}`, pinned
by a test that evaluates the assignment read out of the live runner source.

**Mutation-verified** — each mutation was applied, the suite run, and the source
restored and SHA-256 verified:

| Mutation | Result |
|---|---|
| `assert_complete()` made a no-op | **9 failed** |
| digest verification removed | **3 failed** |
| missing treated as failure | **9 failed** |
| `UNACCOUNTED` made unreachable | **3 failed** |

`restore sha: 209e8105e7e09335278c428ab840d7f4cf02377b36c3c53584aa98cedbea1fcb`
→ byte-identical.

**Tests:** `tests/test_rsi1_measurement_contract.py` — **47 passed**, every one
behavioural. All `assert callable(...)` / `assert not hasattr(...)` tests removed.

### 2.4 Production adoption registry — **deleted (Path A)**

The committed registry carried six fabricated values: `aabbccddeeff…`, 72
characters of `abcd`, sequential hex, and the free-text strings
`evaluator-v1-rsi-1-authority`, `baseline_policy_digest_20261009`,
`candidate_policy_digest_20261009`. It named `pi-campaign` — the **test fixture
campaign** — used a schema the resolver cannot parse, and was pinned by nothing.

**Path A was chosen deliberately**: no real adopted campaign configuration,
policy manifest, evaluator identity, or policy artifact set can be verified from
committed bytes, so no replacement registry was created.

- `evaluations/adoption/production_adoption_registry.json` deleted; the empty
  directory removed. Verified absent from the tip tree, the index, and disk.
- `resolve_config_adoption()` returns **`UNADOPTED_CONFIG`** for every config.
- `AUTHORITATIVE_ANCHORS` still pins no registry and no evidence index.

**Tests:** `tests/test_rsi1_production_adoption_registry.py` — **26 passed**.
Refusal paths (tampered registry, revoked, superseded, duplicate ACTIVE, extra
keys, missing `config`, digest mismatch, tampered payload, absent file,
malformed bytes, path escape) are exercised against synthetic registries built
from **real digests** of synthetic files under `tmp_path`.

### 2.5 Historical call-site census — **re-derived**

Prior figures were mutually inconsistent (prompt said 23, JSON said 25,
manifest said "23+"), 10 of 19 paths pointed at `scripts/` for files that live in
`src/arena/`, and **every** entry was `operator_ruling_pending: true` with no
ruling field while the document was titled a "ruling".

- Census re-derived from source: **22 verified call sites**.
- Every path verified with `test -f`; every cited line re-read and compared.
- **4,788 occurrences inside generated historical run data** are counted and
  reported separately — they record what a past run *did*, not intent, and are
  neither ruled nor rewritten.
- Every entry carries `historical_only: true`,
  `current_authority_granted: false`, and
  `ruling_status: "PENDING_OPERATOR_RATIFICATION"`.
- JSON, Markdown and manifest now agree on the count. The withdrawn 23/25
  figures are stated as withdrawn.

**No operator ruling was invented.** Operator input is genuinely unavailable, so
the entries are classified pending, and the manifest records
`phase3_blocked_until_ratified: true`.

**Tests:** `tests/test_rsi1_historical_call_site_rulings.py` — **19 passed**.
Includes an independent re-scan that fails on any drift between the recorded
census and the source tree.

### 2.6 Audit-trail hygiene — **corrected**

- `rsi1-audit-verdict.md` moved to
  `reports/historical/rsi1-audit-verdict-20261009-self-reported.md` with a
  **SUPERSEDED / SELF-REPORTED** banner naming its three stale claims (1287 vs
  1318 suite count, "16/21 not applied" vs 69/69, and the nonexistent quarantine).
- `reports/PHASE3_READINESS_REMEDIATION_REPORT_20261009.md` carries a
  **SUPERSEDED IN PART** banner correcting all five workstream claims.
- `.zcodeignore` **removed** — a duplicate of `.gitignore` referenced by nothing
  and carrying no governance role.
- `evidence/provenance_correction/OPERATOR_ATTESTATION.md` created with status
  **PENDING — NOT SIGNED**. This agent does not know the operator's name,
  handle, or email. **They were not invented.** The agent identity actually used
  is recorded explicitly.

---

## 3. Test results

| Suite | Result |
|---|---|
| `tests/test_phase3_evidence_binding.py` | **21 passed** |
| `tests/test_rsi1_holdout_classification.py` | **17 passed** |
| `tests/test_rsi1_measurement_contract.py` | **47 passed** |
| `tests/test_rsi1_production_adoption_registry.py` | **26 passed** |
| `tests/test_rsi1_historical_call_site_rulings.py` | **19 passed** |
| Focused suite (10 files) | **494 passed, 0 failed** |
| **Full configured suite** | **1417 passed, 0 failed, 44 warnings** (103.37s) |
| `tests/test_f_split_1_split_vocabulary.py` | **74 passed** |
| `tests/test_rsi1_policy_identity.py` | **69 passed** |

No skips or xfails were added. The two pre-existing docker-dependent `skipif`
markers are untouched.

Integrity: SHA-256 over 122,315 tracked/evidence/report files taken before and
after the runs; `git status` identical. `src/arena/tests` was not run (separately
scoped).

---

## 4. Explicit confirmations

**No placeholder provenance remains.** No fabricated digest, identity, campaign
id, registry entry, row count, or commit reference exists on this branch. Where
evidence is absent it is classified absent, not described.

**No canonical holdout was fabricated or reconstructed.** The canonical
`rbs_v4_holdout.jsonl` remains absent; `verify_authoritative_holdout()` returns
`MISSING`; `reconstruction_permitted` is `false`; the quarantined predecessor was
**not** recreated; the authoritative-anchor manifest is unmodified and still
verifies against the digest pinned in `evaluation_gate.py`.

**Phase 3 remains unauthorized.** No Phase 3 capability is implemented. No
promotion, deployment, rollback, autonomous improvement, or production adoption
is enabled. L2 is not claimed. `require_policy_identity` remains `False` by
default and is not in `PROMOTION_REQUIREMENTS`.

---

## 5. Remaining blockers for Phase 3 readiness

These are **not** fixed by this branch, and each needs an operator decision:

1. **Historical call-site rulings are still pending.** 22 sites await the
   operator's intended-split ruling. Phase 3 readiness is blocked until they are
   ratified.
2. **No adopted campaign exists.** `UNADOPTED_CONFIG` is correct, but there is no
   real adopted configuration, policy manifest, or policy artifact set. L2
   requires one, built from real committed artifacts.
3. **The holdout remains `UNVERIFIABLE`.** It must be recovered with provenance
   or formally classified as permanently unrecoverable with an adopted
   alternative measurement contract.
4. **Operator attestation is unsigned.** The operator's identity was not
   available to this agent and was not invented. All commits are authored by
   `OMP Agent <agent@local>`.
5. **`_check_lineage` still reads the stored ledger index** (documented
   denial-only residual; unchanged by this branch).
6. **`src/arena/tests` remains unverified** — test isolation is separately scoped.

---

## 6. Request

**A fresh independent audit is requested.** This branch does not request Phase 3
authorization and does not claim L2. The audit should specifically re-verify:

- that no fabricated artifact or claim remains;
- that `assert_complete()` genuinely raises on an incomplete grid (mutation
  table in §2.3);
- that the adoption registry is genuinely absent and adoption genuinely
  fail-closed;
- that the 22-site census matches an independent re-scan;
- that operator attribution is recorded as absent rather than invented.