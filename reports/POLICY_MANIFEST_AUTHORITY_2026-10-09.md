# RSI-1 POLICY MANIFEST AUTHORITY — implementation report

**Date**: 2026-10-09
**Branch**: `governance/rsi-1-blockers` (stacked on `audit/f-split-1`, stacked on
frozen baseline `b6ef24bdb`)
**Authority for the design**: operator ruling, "RAPHAEL — Policy Artifact
Authority Resolution", 2026-10-09.
**Status**: implemented, uncommitted, not adopted. **No production adoption
record was created. No promotion. Not Phase 3.**

---

## 1. What the ruling required, and how it was met

| Ruling requirement | Implementation |
|---|---|
| Exploration-policy artifacts committed and digest-pinned for campaigns seeking authoritative results | `resolve_policy_identities()` reads artifact **bytes** and verifies SHA-256. Artifact format is the canonical `ExplorationPolicy` serialization, so the byte digest **is** the policy identity. |
| Campaign-scoped policy manifest | `POLICY_MANIFEST_SCHEMA_VERSION = 1`; manifest declares exactly `schema_version`, `campaign_id`, `source_revision`, `policies`. |
| Bound to trusted configuration/adoption state | `GateConfig.policy_manifest_file` / `policy_manifest_sha256` are fields of `to_dict()` and of `config_digest`. An ADOPTED registry entry therefore transitively pins the manifest. |
| **Do not** add per-campaign policies to `AnchorSet` | `AnchorSet` is unchanged. Pinned by `test_k26_anchor_set_has_no_policy_anchor`, which walks the dataclass fields. |
| Avoid a generic registry / second independent authority | The manifest is reachable **only** through `resolve_config_adoption()`, which requires `ADOPTED`. There is no code path that reads a manifest without passing the adoption gate. Mutation-verified — see §5. |
| Resolver used by `final_states()` / `current_authority()` | Neither signature changed. `resolve_policy_identities()` is called inside `_classify_with_authority`, so **every** classification and admission path — including post-restart re-reads — resolves trusted identity with zero caller input. |
| Never trust an identity from the ledger or from a caller-asserted identity | The resolver takes only `config` and `anchors`. `test_k2` pins the parameter set to exactly `{config, anchors}`. Asserted identities are superseded by the trusted resolution (`test_k17`) and still BLOCKED without one (`test_k20`). |
| No public pass-through API laundering caller identities | `final_states(self, config)` and `current_authority(self, decision_id, config)` are unchanged. No `policy_identities` parameter was added to either. |
| Fail closed when artifact/binding unavailable | Ten explicit failure statuses, all listed in `POLICY_MANIFEST_FAILURE_STATUSES`; every one returns `identities == ()`. |

---

## 2. Manifest schema (as implemented)

```json
{
  "schema_version": 1,
  "campaign_id": "<must equal the adopted config's campaign_id>",
  "source_revision": "<non-empty provenance string>",
  "policies": [
    {"role": "baseline",  "policy_id": "...",
     "artifact": "<repo-relative path>", "sha256": "<64-hex>",
     "policy_schema_version": 1},
    {"role": "candidate", "policy_id": "...",
     "artifact": "<repo-relative path>", "sha256": "<64-hex>",
     "policy_schema_version": 1}
  ]
}
```

Enforced by construction: exact top-level key set, exact entry key set, int
schema versions (bools rejected), exactly one entry per role with both roles
required, 64-hex digests, repo-relative artifact paths that may not escape the
repository root, and a bounded read (`_MAX_PINNED_BYTES`).

The resolver also requires the artifact to agree with **itself**: a
`content_hash` field inside the artifact, if present, must equal the digest of
the artifact's own committed bytes (`test_k16`). This catches a manifest that
pins well-formed bytes which do not describe themselves.

---

## 3. Trust chain

```
AUTHORITATIVE_ANCHORS.adopted_config_registry_sha256      pinned IN evaluation_gate.py
  └─ _read_pinned_json()          registry bytes, digest-verified, repo-contained
       └─ entry.config_digest  ==  config.config_digest
            └─ entry.config["policy_manifest_file" / "policy_manifest_sha256"]
                 └─ _read_pinned_json()   manifest bytes, digest-verified
                      └─ entry.artifact + entry.sha256
                           └─ _read_pinned_artifact_bytes()   EXACT bytes, digest-verified
                                └─ derive_policy_identity(role, policy_id, raw)
                                     └─ PolicyIdentity(derived=True)
                                          └─ verify_policy_identity() vs record's DECLARED hash
```

Two properties make this a projection of existing authority rather than a new
one:

1. **Adoption is the only door.** `resolve_policy_identities()` checks
   `resolve_config_adoption(config).adopted` *before* reading the manifest. A
   config that pins a manifest but is not adopted returns
   `POLICY_MANIFEST_CONFIG_NOT_ADOPTED` (`test_k11`). Without this check the
   "binding" would be a caller-chosen string and the whole mechanism would be a
   laundering path.
2. **Precedence, not merge.** When the trusted resolution verifies, it *is* the
   identity set. A caller-supplied **derived** identity that contradicts it is
   refused as a contradiction between two derivations, never resolved in favour
   of the caller (`test_k18`). A caller-supplied **asserted** identity is simply
   discarded (`test_k17`).

**Establishing that a verified identity is the one authorized for the record's
campaign and role** — four independent checks, each separately pinned:

1. the config is ADOPTED, so its `campaign_id` is the adopted campaign;
2. the manifest's `campaign_id` must equal that campaign (`test_k7` — proven as
   a live control by building a chain where nothing is tampered, so the campaign
   binding is the only thing that can refuse);
3. the manifest must declare exactly one entry per role, and each entry's
   artifact must declare the same `policy_id` the manifest pins
   (`test_k14`);
4. the derived digest is compared against the record's declared hash; a
   disagreement is `REFUSE` (`test_k8` for a role swap).

---

## 4. Historical provenance findings

**No existing record can be bound, because no decision record exists.**

Verified: no `EvaluationDecisionRecord` is serialized anywhere in the repository.
A repo-wide grep for decision-record field names (`evaluator_identity`,
`gate_config_digest`, `holdout_evaluation_refs`) returns **zero** matches outside
tests. There is no ledger file, and `classify_promotion_eligibility` /
`build_authority` have no caller anywhere in `src/`.

What *does* exist is historical **policy content**:

| Artifact | Status |
|---|---|
| `evidence/rsi0/20261006T194110Z/manifest.json` | git-tracked, contains 3 full `ExplorationPolicy` dicts with `content_hash` |
| `evidence/rsi0/20261006T194147Z/manifest.json` | same |
| `evidence/rsi0/20261006T194314Z/manifest.json` | same |
| `evidence/rsi0/20261006T194851Z/manifest.json` | same |

Findings, all verified by re-derivation rather than by reading a claim:

- All three candidate policies reconstruct exactly:
  `ExplorationPolicy.from_dict()` re-derives `content_hash` and accepts each one.
- `content_hash == sha256(canonical_json_bytes)` holds exactly for all three. So
  the identity is the digest of canonical bytes, which is the property the
  manifest design depends on.
- All four runs agree on all three identities, so there is no cross-run drift:
  `rsi0-c0-canonical 6fae82c2…`, `rsi0-c1-reverse 0bde82cf…`,
  `rsi0-c2-retry-a d4702b0c…`.

**Classification of historical material:**

- The RSI-0 candidate policy **content** is *attested and verifiable* from
  committed evidence.
- There is **no baseline policy** in that evidence — only three candidates — so
  no baseline identity exists historically at all.
- Nothing **pins** those manifests: they are not in `AUTHORITATIVE_ANCHORS`, no
  adopted config references them, and git blob digests are a version-control
  fact, not an authority anchor. They are therefore **not** trusted artifacts
  today and cannot become so without an operator decision.
- These are RSI-0 evaluation manifests, not promotion-authoritative decision
  records. Even fully bound they would not support promotion.

**Provenance honesty caveat — this needs an operator ruling.** The original
policies were never written as standalone files; `run_rsi0_eval.py` embeds them
as a `candidates` sub-object. Committing `policies/<id>.json` files now would be
a **transcription from a run manifest**, not recovery of an original artifact.
Doing that is legitimate going forward but must not be described as recovering
the historical artifact. **No such file was created.**

**Nothing was reconstructed or synthesized. No artifact was written. No
historical result was relabelled as verified.**

---

## 5. Adversarial coverage

| Test | Attack |
|---|---|
| `k3`, `k4` | tampered artifact bytes (candidate, baseline) |
| `k5` | changed manifest digest |
| `k6`, `k7` | wrong campaign (digest-caught, and campaign-caught with nothing tampered) |
| `k8` | swapped baseline/candidate roles → both gates `REFUSE` |
| `k9`, `k10` | missing artifact, missing manifest |
| `k11` | **unadopted config cannot read a manifest** (the load-bearing gate) |
| `k12` | config with no manifest binding stays `UNPINNED` |
| `k13`, `k14` | malformed manifests; duplicate and missing roles |
| `k15` | artifact path escape |
| `k16` | artifact that lies about its own `content_hash` |
| `k17` | caller-asserted identity cannot satisfy a bound config |
| `k18` | caller-derived identity contradicting the artifact → refused |
| `k20` | asserted identity still BLOCKED when no manifest exists |
| `k21` | **positive proof**: honest record regains authority after restart with no caller input |
| `k22` | positive grant revoked by tampering the artifact |
| `k23` | positive grant revoked by withdrawing adoption |
| `k24` | injected record still cannot beat the manifest |
| `k25` | manifest binding is part of `config_digest` |
| `k26` | `AnchorSet` has no policy field |
| `k27`, `k28` | partial binding refused; defaults unchanged |

**Mutation verification.** Disabling the adoption gate
(`if False and not adoption.adopted:`) was applied to the source, section K
re-run, and the source restored and SHA-256 verified:

```
MUTATION APPLIED: adoption gate disabled
FAILED tests/test_rsi1_policy_identity.py::test_k11_unadopted_config_cannot_read_a_manifest
1 failed, 13 passed, 55 deselected
restored sha: 63bb50cc58fd94f5c92999956ce0b36b5391be5fc77ce80f1eb829f167e3c8cd
RESTORE VERIFIED: byte-identical
```

---

## 6. Preserved invariants

- `require_policy_identity` default `False`; empty manifest binding by default
  (`test_k28`).
- `PROMOTION_REQUIREMENTS` unchanged — neither `require_policy_identity` nor
  `policy_manifest_file` was added (`test_k28`).
- `AnchorSet` unchanged (`test_k26`).
- Holdout anchors untouched. Production adoption artifacts untouched. No
  measurement aggregation. No promotion.
- Non-strict classification behavior is unchanged: `effective_policy_identities`
  returns the caller's identities untouched when the flag is False.
- Every fixture is under pytest `tmp_path`. **No adoption record, manifest, or
  policy artifact was created in the repository.**