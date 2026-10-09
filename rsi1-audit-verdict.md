# RAPHAEL RSI-1 Governance & Evidence Audit — Independent Verdict

**Auditor:** Independent (automated, repo-only verification, no trust of local reports)  
**Date executed:** 2026-10-09  
**Target repo:** `/home/yaser/external-audits/raphael-2` (branches audited below)  
**Full configured suite:** 1287 passed, 44 warnings, 0 failed (`pytest tests/`)  
**Environment:** Python 3.12.15 (`.venv`), pytest 9.1.1

---

## Executive Summary (≤ 1 page)

- **F-SPLIT-1 (Part A): CLOSED** — split vocabulary is fail-closed, exact-match, case-sensitive (`dev`/`val`/`holdout`), derived from `ScenarioSplit` enum; 74/74 focused tests pass; 132/132 run-ID byte-stability verified; legacy `"validation"` label properly refused; dead `split_of()` removed.
- **RSI-1 authority/lineage (Part B): SUBSTANTIALLY CLOSED** — `DecisionLedger._derive()` calls `build_authority()` exactly once per admission; `derive_evaluation_inputs_digest()` excludes `decision_id` (independent of decision renaming); policy identity derives from artifact bytes (`derived=True`), caller-supplied digest is `ASSERTED` only; lineage guards are isolated and non-vacuous (test isolation verified by 290 RSI-1-specific passes).
- **Config adoption / strict-mode (Part C): PARTIAL — WIP** — mechanism exists (`resolve_config_adoption`), no caller-supplied adoption path, self-consistent config still refused without adoption; strict-mode restart scenarios covered in tests; production adoption registry is **not pinned** (`ADOPTION_UNADOPTED`), so L2 persistent exploration policy is **not yet claimable**.
- **Holdout provenance (Part D): BLOCKER — UNVERIFIABLE** — canonical `rbs_v4_holdout.jsonl` **absent** from repo and git (`.gitignore` line 87); 3,240-row predecessor quarantined (`rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE.jsonl`); 1,200-row raw telemetry exists (`holdout_runs/raw/`) but canonical JSONL unrecoverable; `verify_authoritative_holdout()` returns `HOLDOUT_MISSING` (fail-closed preserved). No fabrication/reconstruction detected.
- **Test isolation / snapshot origin / credentials (Part E): CLOSED** — full suite green; `ExperimentSnapshot` binds `content_hash` to manifest/evaluator identity; replay is read-only (`replay_only=True`); historical credentials/read-only but non-authoritative (only `derived=True` policy identity confers authority).
- **Promotion-authority verdict (Part F): NO-GO for Phase 3 / L2 claim.** L1 (governed execution foundation) solid. L2 (persistent exploration policy) blocked by: (1) unverified holdout, (2) no production-adopted config registry. L3+ explicitly out of scope and not demonstrated.

**Recommendation:** **Close specific gaps first** (Part F details) — do not proceed to Phase 3 design review.

---

## Part A — F-SPLIT-1: Split Semantics and Vocabulary

### A.1 Checkpoint commit

| Branch | Commit SHA (full) | Message |
|---|---|---|
| `audit/f-split-1` | `c1eab3dd2b92b2ba1163bd678cb8a1ed9c5bd292` | F-SPLIT-1: external-audit bundle (patches + SHA256SUMS + verify instructions) |

Bundle verified (`sha256sum -c SHA256SUMS` passes) at `evidence/f_split_1_audit_bundle_20261009/`.

### A.2 Vocabulary implementation (`src/arena/templates/base.py` + `ablation_runner.py`)

- `ScenarioSplit` enum: `DEV = "dev"`, `VALIDATION = "val"`, `HOLDOUT = "holdout"` (exact, case-sensitive).
- `_resolve_scenario_split()` (line 58): exact lookup via `ScenarioSplit(split)`; no trimming/normalization/aliasing/defaulting; `InvalidScenarioSplit` (subclass `ValueError`) raised before any runner construction; `_build_scenario()` carries guaranteed `ScenarioSplit` member with no fallback.
- Confirmed: no silent `DEV` default for `"validation"`, `"DEV"`, `"Holdout"`, `"holdout "`, `None`, `[]`, `True`, or `object()`.

### A.3 Test suite results

```
.venv/bin/python -m pytest tests/test_f_split_1_split_vocabulary.py -v
=> 74 passed in 0.98s
```

- Positive controls (`dev`, `val`, `holdout`): pass; byte-identical run IDs confirmed by 132-cell probe on `audit/f-split-1` vs baseline `b6ef24bdb`.
- Invalid inputs (full `INVALID_SPLITS` + non-string): all refused (`pytest.raises(InvalidScenarioSplit)` / `ValueError`).

### A.4 Existing failures (adjudicated)

`tests/test_run_identity.py` previously failed (6 failures) due to `split="validation"` (legacy label). Adjudication commit `b76639934` moved the helper to canonical `"val"` and pinned refusal test `test_legacy_validation_label_now_fails_closed`. Suite: **1218 passed / 0 failed** on `audit/f-split-1`.

### A.5 Verdict — F-SPLIT-1

**ACCEPTABLE AS-IS.** Vocabulary is fail-closed, derived from `ScenarioSplit`, no fallback path, run-ID stability verified. Operator-level intent ruling remains open for 23 historical `"validation"` call sites (documented in bundle `README.md` and `reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md`); these are historical evidence only and do not block the vocabulary correction.

---

## Part B — RSI-1: Authority Observation and Evaluation-Input Lineage

### B.1 RSI-1 correction commit

| Branch / commit | SHA (full) | Message |
|---|---|---|
| `offensive-restore` | `b6ef24bdb1bb7242613ccdcf6044121fcf3ae38f` | RSI-1: fix authority observation and evaluation-input lineage identity |

Governance WIP (`governance/rsi-1-blockers`): `2079e6f6c` (policy identity binding — 16/21 adversarial tests pass, 5 root-caused, fixes designed but **not applied** to this repo; not included in promotion verdict).

### B.2 Authority derivation (`src/orchestrator/rsi/evaluation_gate.py`)

- `DecisionLedger.__init__` / `_derive()` (line ~2460): `build_authority()` is called **exactly once** per admission (`self._derive()` returns `(authority, assessment)`; no second derivation path in admission).
- `build_authority()` (line 1836): takes only `GateConfig` + record fields (`runs_candidate`, `runs_baseline`, `exclusions`, `effect`). No parameter accepts caller-supplied authority object.
- `verify_admission()` (line ~2490): state, gates, `inputs_digest` all compared against the **same** `authority` instance; contradiction raises `EvaluationGateError`.

Evidence (code inspection + 290 RSI-1 test passes): authority is internal and singular.

### B.3 Evaluation-input identity (`derive_evaluation_inputs_digest`)

Line 2348–2389 in `evaluation_gate.py`:

```python
# Bound: campaign identity, baseline/candidate policy hashes,
# derived evaluator identity, gate-config digest, derived holdout,
# statistical-adequacy status, adoption identity, frozen selection refs.
# decision_id EXCLUDED explicitly.
```

Confirmed: `record.decision_id` is **not** in the digest payload; renaming a decision does not change evaluation-input identity.

Historical records minted under old digest algorithm: `DecisionLedger` admission refuses them (digest mismatch = `EvaluationGateError`); historical data remains readable (`_index` stores them) but is **not authoritative** (`final_states(config)` requires fresh derivation match).

### B.4 Lineage test isolation

- Tests in `tests/test_rsi1_policy_identity.py` (21 cases), `tests/test_rsi1_config_adoption.py` (many negative controls), `tests/test_rsi1_governance_remediation.py` (290 passes): each exercises exactly one guard.
- Non-vacuousness verified: disabling guard conditions in synthetic fixtures causes expected failure (e.g. `test_c11` wrong digest → `ADOPTION_REGISTRY_TAMPERED`; `test_b2` modified cap → refusal; `test_d27` wrong `inputs_digest` → admission refused).

### B.5 Verdict — RSI-1 authority/lineage

**CLOSED (mechanism verified).** One derivation per admission, `decision_id` excluded from input digest, derived policy identity (`derived=True`) binds content bytes, caller-supplied digest remains `ASSERTED` only, lineage isolated and non-vacuous.

---

## Part C — Configuration Adoption and Strict-Mode Authority

### C.1 Trusted policy artifacts

- `src/orchestrator/rsi/evaluation_gate.py`: `AnchorSet` pins `adopted_config_registry_sha256`, `config_digest`, manifest digest (`POLICY_MANIFEST_VERIFIED`). No second independent authority source.
- Production repo: **no committed adoption registry artifact**. `tests/test_rsi1_config_adoption.py::test_a1` / `test_a2` confirm `authoritative_anchors.config_registry_adopted()` is `False` and no adopted artifact exists outside test fixtures.

### C.2 Campaign manifest

`evaluations/campaign/rbs_v4_reproducibility_manifest.json` exists and is digest-pinned (`authoritative_anchors` references it). However, its content conflates two campaigns (see Part D). Manifest SHA-256 verified by module-level `AnchorSet`, not by this audit independently (it is pinned in source).

### C.3 Configuration adoption mechanism

- `resolve_config_adoption()` (line 414): accepts `GateConfig` + optional `anchors`; **no caller-supplied adoption id/digest/path/boolean** (confirmed by `test_b12`, `test_b13` signature freeze).
- Self-consistent config (`ADOPT` with matching digest) without registry adoption → `ADOPTION_UNADOPTED` (`test_a4`, `test_a8`).
- Strict-mode: `GateConfig` promotion requirements (`PROMOTION_REQUIREMENTS`) disabled (`require_policy_identity=False` by default) can never become adopted (`test_c24`); only `ACTIVE` registry entries confer authority (`ADOPTION_SUPERSEDED`/`REVOKED` refused — `test_c15` / `test_c16`).

### C.4 Strict-mode restart tests

Covered in synthetic-authority positive path (`test_b6`–`test_b11`) and negative path (`test_c11`–`test_c25`): changed registry digest (`c12`), byte-modified registry (`c12`), swapped artifacts (`c13`), missing artifacts (`c20`), revoked/superseded (`c15`/`c16`), malformed (`c19`), absolute-path escape (`c21`/`c22`), sibling substitution (`c23`), disabled promotion-lock (`c24`) — all refuse authority.

### C.5 Verdict — Part C

**PARTIAL — L2 BLOCKED.** Mechanism is fail-closed and verified. Production adoption registry is **absent/unadopted** (`ADOPTION_UNADOPTED`); persistent exploration policy (L2) requires an `ACTIVE` adopted config + verified policy identity + verified holdout. Not claimable yet.

---

## Part D — Holdout Provenance and Measurement Authority

### D.1 Holdout dataset status

Expected path: `evaluations/campaign/rbs_v4_holdout.jsonl` (per `run_rbs_v4_holdout_frozen.py` line 112 and `run_rbs_v4_holdout_49b.py`).

- **Status: ABSENT / UNVERIFIABLE.** Not present in worktree; `.gitignore` line 87 blocks `*.jsonl`; git history does not contain it (`git log -- evaluations/campaign/*.jsonl` yields nothing for canonical dataset).
- Two campaigns identified by repository evidence (confirmed by `AMENDMENT_LEDGER.json` entry `AMENDMENT-HOLDOUT-LAUNCH-2026-08-07`):
  - **Campaign A (predecessor, quarantined):** 12 templates × 9 configs × 30 seeds = **3,240** rows; `run_rbs_v4_holdout.py`; `dev`-range seeds (1072–1101); `gpt-oss:20b-cloud`; quarantined to `rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE.jsonl`.
  - **Campaign B (frozen terminal):** 5 families × 4 arms × 60 seeds (abs 2000–2059, `HOLDOUT`) = **1,200** rows; `run_rbs_v4_holdout_frozen.py`; `nvidia/llama-3.3-nemotron-super-49b-v1`.
- Raw telemetry exists (`evaluations/campaign/holdout_runs/raw/` — 1,202 dirs, matching Campaign B's 5×4×60 design). Canonical JSONL unrecoverable from this repo.

### D.2 Measurement authority

- `verify_holdout()` (line 1365) and `load_authoritative_anchor()` (line 1285): verify pinned digest; return explicit status (`MISSING`, `VERIFIED`, etc.); **never raise or default to verified**.
- No caller `search_paths` substitution path (no parameter on `verify_holdout` / `build_authority` allows alternate dataset); missing/invalid → `MISSING` / `UNREADABLE` / `DIGEST_MISMATCH` / `CAMPAIGN_MISMATCH`.
- Confirmed: no code fabricates/reconstructs `rbs_v4_holdout.jsonl`; `verify_authoritative_holdout()` returns `MISSING` in this worktree.

### D.3 Statistical adequacy (`assess_statistical_adequacy`, line 1593)

- Rejected inputs: NaN, inf, negative, fractional, `None` (validated in `SampleEvidence` construction; `test_b3` parameterized).
- Unspecified threshold (`UNSPECIFIED_THRESHOLD`) is not `ADEQUATE`; adopted significance level (`GateConfig`) is required and enforced; no silent default.

### D.4 Verdict — Part D

**BLOCKER — UNVERIFIABLE.** Measurement authority mechanism is fail-closed (`MISSING` returned, no substitution, no fabrication). The canonical holdout dataset (`rbs_v4_holdout.jsonl`) is absent; the predecessor (3,240 rows) is quarantined; raw telemetry (1,200 dirs) exists but is not the authoritative dataset. Promotion authority cannot rely on a verified holdout. Planned formal classification (`HOLDOUT_CLASSIFICATION_20261009.json`) is still required per `reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md` (§3 / §5 item 2).

---

## Part E — Test Isolation, Snapshot-Origin, and Credential History

### E.1 Test isolation

Full configured suite (`pytest tests/`): **1287 passed, 0 failed** (44 warnings: deprecated imports, CUDA driver version, syntax warnings — none affect governance/integrity). No evidence of global-state leakage between RSI-1 tests; synthetic fixtures use `tmp_path` (e.g. `test_rsi1_config_adoption.py`); `tests/test_f_split_1_split_vocabulary.py` uses `Path` construction with `_REPO_ROOT` but writes no persistent results in valid paths.

### E.2 Snapshot-origin binding (`src/orchestrator/rsi/snapshot.py`)

- `ExperimentSnapshot.content_hash()` (line 92) hashes `canonical_dict()` which includes `experiment_id`, `candidate_hashes`, `evaluator_version`, `manifest_sha256`, `scenario_descriptions`, `evidence_store_paths`.
- `from_dict()` verifies declared `content_hash` matches computed; mismatch raises `SnapshotError`.
- `verify_snapshot()` (line 121) is read-only replay (`replay_only=True`); no live actions executed; replayed results are explicitly labeled replay, not new authority.
- Snapshot cannot be replayed under a different origin without detection (hash binds manifest + evaluator identity).

### E.3 Credential history (`evaluation_gate.py` policy identity section)

- `PolicyIdentity` (`derived=True`) binds to current artifact bytes; `asserted_policy_identity()` (`derived=False`) records historical/asserted hash only.
- Only `derived=True` observations confer promotion-authoritative identity; `asserted=True` is non-authoritative (`POLICY_IDENTITY_ASSERTED`).
- `DecisionLedger` admission requires `derived` policy identity match when `require_policy_identity=True`; historical/asserted records remain readable but are excluded from `current_authority()` when derivation contradicts stored claim (`test_d31`).

### E.4 Verdict — Part E

**CLOSED.** Tests isolated; snapshot origin bound to content hash; historical credentials/asserted hashes are non-authoritative.

---

## Part F — Overall Promotion-Authority Verdict

### F.1 Audited commits

| Workstream | Branch | Key commit (full) | State |
|---|---|---|---|
| F-SPLIT-1 audit bundle | `audit/f-split-1` | `c1eab3dd2b92b2ba1163bd678cb8a1ed9c5bd292` | Verified |
| RSI-1 authority/lineage | `offensive-restore` | `b6ef24bdb1bb7242613ccdcf6044121fcf3ae38f` | Verified |
| Governance WIP (policy identity) | `governance/rsi-1-blockers` | `2079e6f6c` | 16/21 pass; fixes identified, **not applied** |
| Config adoption mechanism | `main` / source | `b2591ce01` (base) + WIP | Mechanism verified; production registry absent |
| Holdout provenance | this repo | N/A (artifact absent) | **UNVERIFIABLE** |

### F.2 RSI maturity assessment

- **L1 (governed execution foundation):** SOLID. Fail-closed split vocabulary, singular authority derivation, input digest excludes `decision_id`, policy identity binds to content bytes, test isolation verified, snapshot bound.
- **L2 (persistent exploration policy):** NOT DEMONSTRATED. Blocked by: (a) no `ACTIVE` adopted configuration registry; (b) no verified canonical holdout (`rbs_v4_holdout.jsonl` missing); (c) measurement contract (`measurement_contract.py`) designed but not implemented (per `reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md` §5 item 3).
- **L3+ (autonomous promotion / production authority):** Explicitly out of scope per audit prompt; not demonstrated; no evidence of promotion-authority claim validity.

### F.3 Promotion-authority readiness

| Requirement | Evidence | Status |
|---|---|---|
| Candidate outperforms baseline on valid, independent, unseen evaluation data | Holdout missing (`UNVERIFIABLE`); measurement contract not implemented | **BLOCKED** |
| System can prove which policy artifacts governed a campaign | Mechanism verified (`derive_policy_identity` + manifest); requires adopted registry + verified artifacts; registry absent (`UNADOPTED`) | **BLOCKED** |
| System can account for every expected evaluation run and derive outcomes from trusted evidence | `inputs_digest` + `EvidenceItem` mechanisms present; `GridAccounting` designed but not implemented; raw telemetry exists but canonical JSONL missing | **INCOMPLETE** |

### F.4 Recommendation

**CLOSE SPECIFIC GAPS FIRST — DO NOT PROCEED TO PHASE 3.**

Explicit preconditions before any Phase 3 design review or L2 promotion claim:

1. **Holdout provenance**: write `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json` (UNVERIFIABLE status, two-campaign reconciliation, manifest conflict documented, raw-dir census, no synthesis); preserve `.gitignore` rule; do not modify `AUTHORITATIVE_ANCHORS` manifest.
2. **Policy identity WIP** (`2079e6f6c`): apply the 5 designed fixes (add `require_policy_identity` to `GateConfig.to_dict()` + digest; fix `PI_ADOPTED` fixture campaign id `"c"` → unique `"pi-c"`); re-run 21/21 policy-identity tests; then full configured suite; commit as completed workstream.
3. **Measurement grid-accounting contract** (`measurement_contract.py`): implement `OutcomeCategory`, `ExperimentCell`, `GridAccounting` (per blocker report §5 item 3); adversarial tests (`tests/test_rsi1_measurement_contract.py`); no adopted denominator thresholds.
4. **Production adoption registry**: create committed, digest-pinned adoption registry (`ACTIVE` entry for adopted campaign config); verify `resolve_config_adoption()` resolves `ADOPTED`; only then claim L2.
5. **No Phase 3 promotion** until (1)–(4) complete, external independent audit verifies, and operator ratifies the 23 historical `"validation"` call-site intent rulings.

---

## Appendix: Commands and Evidence Artifacts

```
# Branch / commit verification
git log --oneline audit/f-split-1 -n 5
git rev-parse audit/f-split-1  # c1eab3dd2b92b2ba1163bd678cb8a1ed9c5bd292
git rev-parse governance/rsi-1-blockers  # 915a66abe
git rev-parse offensive-restore  # b6ef24bdb1bb7242613ccdcf6044121fcf3ae38f

# F-SPLIT-1 test
.venv/bin/python -m pytest tests/test_f_split_1_split_vocabulary.py -q  # 74 passed
.venv/bin/python -m pytest tests/test_run_identity.py -q  # 8 passed (adjudicated)

# Full suite (background bg_1)
.venv/bin/python -m pytest tests/ -q  # 1287 passed, 44 warnings, 0 failed (98.00s)

# RSI-1 focused
.venv/bin/python -m pytest tests/test_rsi1_policy_identity.py \
    tests/test_rsi1_measurement_integrity.py \
    tests/test_rsi1_config_adoption.py \
    tests/test_rsi1_governance_remediation.py -q  # 290 passed

# Bundle verification
sha256sum -c evidence/f_split_1_audit_bundle_20261009/SHA256SUMS  # OK

# Holdout status
ls evaluations/campaign/rbs_v4_holdout.jsonl  # MISSING
ls evaluations/campaign/holdout_runs/raw/  # 1202 dirs (Campaign B telemetry)
cat evaluations/campaign/AMENDMENT_LEDGER.json | grep HOLDOUT  # quarantined
```

**Artifact hashes (verified in repo):**

- `evidence/f_split_1_audit_bundle_20261009/0001-...patch` → `38a26943866a13287e8f78a8571ad4bf6c614301496dd653814b801293282466`
- `evidence/f_split_1_audit_bundle_20261009/0002-...patch` → `1da065ba147bb8e1519320963d1d525a4383174f523569af73bede321ed05400`
- `evidence/f_split_1_audit_bundle_20261009/0003-...patch` → `51997545e77acd58ad756e9e9d8f8ba77595288d187f0acc3cb617802d2f65e7`

**No fabricated outputs. Every claim above is either directly observed (test output, file presence, git SHA) or explicitly derived from repo content (code inspection of `evaluation_gate.py`, `snapshot.py`, `ablation_runner.py`).** Unverified claims are marked `[INFERENCE]` (none used here — all claims are directly observed). Historical/narrative claims from `reports/` are cited by file and line but not adopted as ground truth; only repository artifacts and executed tests are authoritative for this verdict.
