# RAPHAEL — Blocker Resolution Report (as far as executed)

**Date:** 2026-10-09
**Author:** ZCode session, working from the 2026-10-09 decision brief
("RAPHAEL: Desired State, Current Position and Blocking Issues") and operator
instruction: *fix the blockers and reach the desired state, then make a full
report on all changes.*
**Basis:** fresh repository execution on this worktree (not a synthesis of
prior reports). All test numbers below were run in `.venv` (Python 3.12.15).

---

## 0. Executive summary

Three lines of work were executed; a fourth was root-caused analytically:

1. **F-SPLIT-1 (P2 split integrity): RESOLVED at engineering level.** The
   fail-closed candidate was independently verified against the frozen
   baseline (including a 132/132 run-ID byte-stability probe), the six
   configured-suite failures were adjudicated and fixed intent-aware, the dead
   `split_of()` heuristic was removed as its own reviewed change, and the
   configured suite is fully green: **1218 passed / 0 failed**. An
   external-audit bundle (patches + SHA256SUMS + verify instructions) is
   committed. What remains is the *external* review itself — by definition not
   performable by this session — and the operator's intent ruling on 23
   historical `"validation"` call sites.
2. **Historical holdout (P1): the 1,200-vs-3,240 discrepancy is now
   EXPLAINED** by repository evidence — the manifest conflates two different
   authorized campaigns, and the 3,240-row predecessor was formally
   quarantined by the campaign's own amendment ledger. The canonical JSONL is
   nonetheless absent and unrecoverable from this worktree/git, so the formal
   UNVERIFIABLE classification record (planned next step) still has to be
   written and ratified.
3. **Policy identity (P1): derive-and-verify binding implemented as a WIP
   checkpoint** on branch `governance/rsi-1-blockers` — 16/21 of its new
   adversarial tests pass; the 5 failures are root-caused with fixes designed
   but not yet applied.
4. **Remaining blockers** (measurement contract, decision registry, snapshot
   binding, test isolation, F1/F4 register) — designed, not yet implemented.
   Full plan in §5.

**State discipline preserved:** no merge to any baseline, no Phase 3
authorization, no promotion, no invented thresholds, no synthesized holdout
rows, no touching of the digest-pinned manifest anchor. The operator-owned
decisions enumerated in the brief remain operator-owned; the engineering-side
mechanisms are being built so those decisions become *ratifiable* rather than
*improvisable*.

---

## 1. Branch topology

```
offensive-restore  b6ef24bdb   frozen RSI-1 baseline (UNTOUCHED)
   └─ audit/f-split-1
        bd1fcc109   F-SPLIT-1: expose fail-closed split checkpoint for audit   (pre-existing)
        b76639934   F-SPLIT-1: adjudicate legacy vocabulary — suite green      (new)
        8aebb5211   F-SPLIT-1: remove dead split_of() heuristic                (new)
        c1eab3dd2   F-SPLIT-1: external-audit bundle                           (new)
           └─ governance/rsi-1-blockers (stacked, separate concern)
                2079e6f6c   RSI-1 governance WIP checkpoint: policy identity  (new, WIP)
```

Stacking note: the governance branch sits on the split work so it inherits a
green suite, but every workstream is a separate commit and can be rebased off
`b6ef24bdb` if external review rejects any split commit. Nothing is merged
anywhere; `main` and `offensive-restore` are untouched.

Full hashes:

| Commit | Hash |
|---|---|
| split checkpoint (pre-existing) | `bd1fcc10946ae18cd1652af66810e2eb7c7b9191` |
| run-identity adjudication | `b766399345d828af0a22137e240caca17cbae527` |
| split_of removal | `8aebb5211a4d44aed89cbd7fd63f1dac8fe1fa8c` |
| audit bundle | `c1eab3dd2b92b2ba1163bd678cb8a1ed9c5bd292` |
| governance WIP (policy identity) | `2079e6f6c` |

---

## 2. F-SPLIT-1 — what was done, with evidence

### 2.1 Independent verification of the bd1fcc109 candidate

* **The 6 failures reproduced and diagnosed.** All six are in
  `tests/test_run_identity.py`; its helper `_make_runner` defaults
  `split="validation"`, which the correction rightly refuses. The file's
  contract is run-ID logical-cell identity, not the legacy label.
* **74 focused tests** in `tests/test_f_split_1_split_vocabulary.py` pass.
* **Run-ID byte-stability (release rule) verified mechanically:** a probe
  constructed an `AblationRunner` for every registered ablation preset ×
  {dev, val, holdout} × seeds {0, 7, 1099, 2059} on both the baseline
  (via a temporary worktree at `b6ef24bdb`) and the candidate —
  **132/132 run_ids byte-identical**, 0 differing.
* **Diff review:** vocabulary derived from `ScenarioSplit` (cannot drift),
  exact case-sensitive lookup, resolution first in `__init__` (no
  partially-initialised runner), `_build_scenario` has no fallback. No
  defect found.

### 2.2 Adjudication commit `b76639934`

* `tests/test_run_identity.py`: helper default `"validation"` → `"val"`;
  run-ID assertions `_validation` → `_val` (under the corrected vocabulary
  these name the *same intended cells* — the pre-correction string described
  a DEV scenario); the uuid-suffix regex updated accordingly; new test
  `test_legacy_validation_label_now_fails_closed` pins the refusal at the
  exact historical call site.
* Deliberately unchanged: all 23 historical `split="validation"` call sites
  (the fail-loud evidence for the operator's intent ruling).
* Suite: **1218 passed / 0 failed** (1211 + the 6 adjudicated + 1 new pin).

### 2.3 `split_of()` removal commit `8aebb5211`

* `ScenarioTemplate.split_of()` (numeric seed-range → split) had **zero
  callers** on any current path (reference census + doc census + import
  sweep), carried relative/absolute seed semantics inconsistent with the
  `resolve_seed` split-offset model, and invited the exact silent
  misclassification F-SPLIT-1 closes.
* `scripts/d6b_runner_fixed.py` defines a local same-name method inside a
  standalone historical script class — left for the historical-scripts
  review, not silently edited.
* Suite re-run after removal: **1218 passed / 0 failed**.

### 2.4 Legacy-vocabulary census (for the operator's intent ruling)

23 real `split="validation"` runner-construction sites, none on the canonical
runtime's generation path; all in historical campaign/diagnostic scripts and
their tests:

* scripts: `run_experiment0/1/2/3.py`, `run_rbsv2_campaign.py`,
  `run_rbs_v3_campaign.py`, `run_rbs_v4_pilot.py`,
  `run_rbs_v4_validation.py` (×6), `run_rbs_v4_validation_100.py` (×2),
  `run_rbs_v4_repair_verify.py`, `run_t10_fix_verify.py`
* historical diagnostics: `d8_cognitive_trace.py`, `d8_regression_test.py`,
  `d9_regression_test.py`, `d10_regression_test.py`,
  `d10_falsification_defeater_diagnostic.py`, `d11_regression_test.py`,
  `d16_holdout_runner.py`, `d7_r1_gemma_retest.py`
* nested test: `src/arena/tests/test_runconclusion.py`

(Other grep hits — `sword/report.py`, `test_cli_smoke.py`,
`test_stage1_invariants.py`, `d6_manifest.py` — are prose, dict keys, or
unrelated validation vocabulary, not split labels.)

Per the brief: these must not be rewritten en masse; each needs an intent
ruling (DEV-as-run vs mislabelled validation) before any edit or reliance on
historical results.

### 2.5 External-audit bundle commit `c1eab3dd2`

`evidence/f_split_1_audit_bundle_20261009/`:

```
38a26943866a13287e8f78a8571ad4bf6c614301496dd653814b801293282466  0001-...checkpoint...patch
1da065ba147bb8e1519320963d1d525a4383174f523569af73bede321ed05400  0002-...adjudicate...patch
51997545e77acd58ad756e9e9d8f8ba77595288d187f0acc3cb617802d2f65e7  0003-...split_of...patch
SHA256SUMS + README.md (apply instructions, expected results, reviewer questions)
```

The brief's step "verify the reviewer actually received the files" now has a
concrete, hash-addressable artifact to transmit — the transmission itself is
the operator's act.

---

## 3. Historical holdout — the 1,200-vs-3,240 discrepancy root-caused

No repository files were changed in this investigation. Findings, all
verified against artifacts in this worktree:

1. **There are two different, successively authorized holdout campaigns, and
   both producers write the same output path**
   (`evaluations/campaign/rbs_v4_holdout.jsonl`):
   * *Campaign A (predecessor):* `scripts/run_rbs_v4_holdout.py` — 12
     templates × 9 configs × 30 seeds (1072–1101, **DEV-range** by the
     split-offset model) = **3,240** rows; provider `gpt-oss:20b-cloud` via
     ollama.
   * *Campaign B (frozen terminal):*
     `evaluations/campaign/run_rbs_v4_holdout_frozen.py` — 5 fresh families ×
     4 preregistered arms × 60 seeds (relative 0–59 → **absolute 2000–2059**,
     genuine HOLDOUT split) = **1,200** runs; provider
     `nvidia/llama-3.3-nemotron-super-49b-v1`; collect-only discipline.
2. **The 3,240-row dataset was formally quarantined by the campaign's own
   governance.** `AMENDMENT_LEDGER.json` entry `AMENDMENT-HOLDOUT-LAUNCH-2026-08-07`
   (SENTINEL terminal authorization + principal methodological ruling)
   records the Aug 5 3,240-row JSONL as **CONTAMINATED telemetry of a
   DISCONTINUED instrument** (burned T1–T12 templates, no PROMPTED_AGENT arm,
   DEV-range seeds) and moved it to
   `rbs_v4_holdout_STALE_T1T12_GPTOSS_QUARANTINE.jsonl`.
3. **`rbs_v4_reproducibility_manifest.json` conflates the two campaigns** —
   the source of the brief's "unexplained" discrepancy: its *dataset* block
   declares the 1,200-row Campaign B file (sha256 `2bf614f8…`, timestamps
   Aug 7), while its *design* block still describes Campaign A (12×9×30 =
   3,240, seeds 1072–1101), and its *verification* block points at an
   integrity-gate record for **3,240/3,240 rows PASS run 2026-08-05T23:23Z**
   — i.e. the gate certified the *quarantined predecessor* and predates the
   declared dataset's end timestamp by ~2 days. The brief's suspicion
   ("gate-script digest and frozen-instrument digests do not match current
   checkout; manifest date precedes dataset end") is confirmed and now has a
   precise cause.
4. **1,200 raw per-run directories exist**
   (`evaluations/campaign/holdout_runs/raw/`), matching Campaign B's design
   — the run *telemetry* survives even though the canonical JSONL does not.
   `holdout_49b_runs/raw/` holds 3 further run dirs.
5. **The canonical `rbs_v4_holdout.jsonl` is absent** from the worktree and
   from git (`.gitignore` line 87 `evaluations/campaign/*.jsonl` blocks
   re-adding it; only raw per-run dirs exist on the remote per earlier
   investigation).

**Implication for the P1 blocker:** the analytical question "1,200 or 3,240?"
is answered (they are different campaigns; 3,240 is quarantined; 1,200 is the
frozen terminal design), but the *artifact* remains unrecoverable from this
repository — so the planned formal classification is **UNVERIFIABLE pending
provenance recovery**, with the reconciliation evidence above attached so the
operator ruling is made on facts rather than on two bare numbers. Reconstruction
or synthesis of the JSONL remains forbidden. The digest-pinned manifest anchor
in `evaluation_gate.AUTHORITATIVE_ANCHORS` was deliberately NOT modified.

---

## 4. Policy identity binding — implemented as WIP checkpoint `2079e6f6c`

Branch `governance/rsi-1-blockers`. C1/C2 finding: decision-record
`baseline_policy_hash` / `candidate_policy_hash` are caller-supplied strings
with no binding to the loaded artifact.

Implemented in `src/orchestrator/rsi/evaluation_gate.py` (section 2c):

* `PolicyIdentity` + **`derive_policy_identity()`** — artifact *content bytes*
  are hashed inside the authority module; **no function accepts a
  caller-computed digest** (enforced and tested).
* **`asserted_policy_identity()`** — records the explicitly non-authoritative
  asserted mode (`derived=False`); it can never turn the gate green.
* **`verify_policy_identity()`** — derived-vs-declared **mismatch refuses
  unconditionally** (fabrication, same class as any other record-vs-authority
  contradiction); missing/asserted-only binding is **BLOCKED** when
  `GateConfig.require_policy_identity=True`.
* `GateConfig.require_policy_identity` (default **False** — experimental
  behavior preserved; whether adopted production configs must set it is an
  operator decision, PROPOSED); strict-bool validation included.
* Gate wiring: `classify_promotion_eligibility` /
  `_classify_with_authority` accept `policy_identities` and emit
  `policy_identity_{baseline,candidate}` gates in a new section C2;
  `DecisionLedger._derive` / `verify_admission` / `append` pass the binding
  through so **ledger admission enforces it too**.
* Guard tests `test_b0` / `test_b13` (signature freezes) updated to pin the
  extended signature; the banned exploit parameters (`independent_holdout`,
  `adequacy`, `safety_outcomes`, `config_adoption`) remain banned.

Tests: new `tests/test_rsi1_policy_identity.py`, 21 adversarial cases —
**16 pass, 5 fail**, both root causes identified (see §5, item 1). The full
configured suite was **not** re-run at this WIP commit; last full-suite state
(1218 green) predates the governance branch.

---

## 5. TO-DO LIST

### In-flight (governance branch)

- [ ] **1. Finish policy identity binding** *(design done, fixes identified)*
  - [ ] Add `require_policy_identity` to `GateConfig.to_dict()` AND to the
    `config_digest` field dict (fixes `test_e2`; digests change, safe — all
    suite digests are computed dynamically, no real adoption registry exists).
  - [ ] Fix fixture: `PI_ADOPTED` campaign_id `"c"` → unique (e.g. `"pi-c"`),
    because the adoption resolver allows only one ACTIVE adoption per campaign
    (fixes `test_c1`, `test_c2`, `test_d1`, `test_d4` — the duplicate entry
    currently MALFORMS the whole fixture registry).
  - [ ] Re-run: policy-identity file 21/21, then full configured suite green.
  - [ ] Commit as the completed policy-identity workstream.

- [ ] **2. Holdout formal classification** *(evidence gathered, §3; record not
  yet written)*
  - [ ] `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json` —
    machine-readable record: status UNVERIFIABLE; the two-campaign
    reconciliation of §3; manifest conflation; quarantine reference; raw-dir
    census; explicit "do not synthesize; do not use as promotion evidence".
  - [ ] `evidence/HOLDOUT_PROVENANCE_CLASSIFICATION_20261009.md` — narrative
    with artifact paths and hashes.
  - [ ] README.md truth-sync: the 1,200-row / `2bf614f8…` citations must be
    marked UNVERIFIABLE (absent artifact), not asserted as held data.
  - [ ] Guard test: `verify_authoritative_holdout()` still returns
    `HOLDOUT_MISSING` on the real repo (fail-closed preserved); classification
    record parses and matches the documented sha256s.
  - [ ] Do NOT touch the pinned manifest anchor or `.gitignore` jsonl rule.

- [ ] **3. Measurement grid-accounting contract** *(new module, design decided)*
  - [ ] `src/orchestrator/rsi/measurement_contract.py`:
    - `OutcomeCategory` enum — COMPLETED, FAILED, DENIED, INCOMPLETE,
      UNSCORABLE, HARD_VIOLATION, MISSING, DUPLICATE, REUSED_RECEIPT, EXCLUDED
      (exclusion requires a reason code);
    - `ExperimentCell` = canonical `(config_id, template.family_id, seed,
      split)` identity aligned with the runner;
    - `GridAccounting.account(expected_cells, rows)` → report with
      per-category counts, missing-cell list, duplicate/reused-receipt lists,
      exclusion ledger; **invariants: every row classified (no silent
      dropping/imputation), every expected cell either covered or explicitly
      missing, no double counting**;
    - authoritative aggregation computed ONLY over accounted reports from
      supplied rows; caller-supplied aggregates have no parameter to occupy;
    - **no success-rate denominators adopted** — per-arm category counts only;
      any rate a caller computes is labelled unadopted-denominator.
  - [ ] `tests/test_rsi1_measurement_contract.py`: adversarial (duplicate run
    IDs, reused receipts, missing cells surfaced, exclusion without reason
    refused, double-count impossible, hard violations separately visible).

- [ ] **4. Governance decision registry** *(mechanism + PROPOSED seed records)*
  - [ ] `src/orchestrator/rsi/governance_registry.py`: append-only
    `OperatorDecisionRecord` ledger (decision_id, topic, decision_text,
    status PROPOSED/ADOPTED/REJECTED, proposer, authority principal, decided_at,
    evidence_refs, content hash). Engineering can write PROPOSED; ADOPTED
    requires an explicit authority principal distinct from the proposer,
    recorded verbatim — the mechanism cannot self-adopt.
  - [ ] Seed `evidence/GOVERNANCE_DECISIONS_20261009.jsonl` with the six
    operator decisions from the brief as **PROPOSED** records: holdout
    recovery-vs-unverifiable; policy identity mode (recommend
    derive-and-verify, flag True in adopted configs); denominator/exclusion
    semantics; adoption authority; statistical policy; snapshot/replay
    SAME/CROSS/UNVERIFIABLE semantics.
  - [ ] Tests: cannot self-adopt, cannot rewrite history, PROPOSED has no
    authority effect.

- [ ] **5. Snapshot origin binding + replay-semantics proposal**
  - [ ] Extend `ExperimentSnapshot` to bind the *authoritative evaluator
    content identity* (`EvaluatorIdentity.compute_current`), the gate-config
    digest, and the anchor identity — the current `evaluator_version` field is
    a non-authoritative label by its own docstring. Check existing content-hash
    pins in tests before changing `canonical_dict` (schema version bump if
    pinned).
  - [ ] `reports/SNAPSHOT_REPLAY_SEMANTICS_PROPOSAL_20261009.md`: immutable
    prefix/origin model PROPOSED; SAME/CROSS/UNVERIFIABLE labels stay
    unimplemented until the operator specifies their meaning (per the brief).

- [ ] **6. Test isolation for `src/arena/tests`** (P2 evidence contamination)
  - [ ] Add `src/arena/tests/conftest.py` mirroring `tests/conftest.py`'s
    autouse fixture (redirect `arena.ablation_runner.RESULTS_BASE` to tmp).
  - [ ] Proof: sha256 tree manifest of `arena/results/` + tracked evidence
    before and after running the nested suite — byte-identical.

- [ ] **7. F1/F4 defect register entries** (P3, non-blocking)
  - [ ] `evidence/DEFECT_REGISTER.md`: DR-002 (F1 — second pinned-anchor read;
    fail-closed but not literal one-observation purity), DR-003 (F4 — schema
    v2 spans old/new digest semantics; stale records refused via
    re-derivation + evaluator identity). Status DEFERRED, production
    prerequisites noted.

- [ ] **8. Close-out**
  - [ ] Full configured suite green on `governance/rsi-1-blockers`; every
    workstream its own commit; bundle/patches regenerated if reviewers want a
    governance bundle too.
  - [ ] Update this report to final state; update project memory.

### Operator-owned (explicitly NOT engineering — per the brief)

- [ ] Transmit `evidence/f_split_1_audit_bundle_20261009/` to the independent
  reviewer; record their evidence-based verdict.
- [ ] Intent ruling on the 23 historical `split="validation"` call sites
  (§2.4): per-site DEV-as-run vs mislabelled-validation; annotate historical
  evidence, no mass rewrite.
- [ ] Adjudicate/merge `audit/f-split-1` only after the reviewer verdict.
- [ ] Ratify or reject the six PROPOSED governance decisions (item 4 above).
- [ ] Holdout ruling: authorize provenance recovery attempts (the JSONL may
  exist in backups/provider storage outside this repo) or accept formal
  unverifiability.
- [ ] Credential rotation review (nvapi- history) remains open from M0.
- [ ] Only after all of the above: versioned Phase 3 design spec (itself
  independently reviewed). Promotion/rollback stay unauthorized regardless.

---

## 6. Verification commands

```bash
# suite state at audit/f-split-1 tip (c1eab3dd2)
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q          # 1218 passed

# byte-stability probe (reproduce)
git worktree add /tmp/rbase b6ef24bdb && \
  python - <<'EOF'   # construct AblationRunner grid on both trees, diff run_ids
EOF

# bundle integrity
cd evidence/f_split_1_audit_bundle_20261009 && sha256sum -c SHA256SUMS

# policy identity WIP (governance branch)
git checkout governance/rsi-1-blockers
PYTHONPATH=src .venv/bin/python -m pytest tests/test_rsi1_policy_identity.py -q
# current: 16 passed, 5 failed (root-caused; see §5 item 1)
```

## 7. Honesty notes

* The brief's step 2 ("verify the reviewer actually received the files") cannot
  be completed by this session — the bundle exists; transmission and verdict
  are external.
* The 5 failing policy-identity tests are *known and root-caused*, committed as
  an explicit WIP checkpoint (per the repo's own bd1fcc109 convention), not
  hidden.
* Nothing was merged; `main`/`offensive-restore` untouched; no governance
  decision was silently adopted — `require_policy_identity` defaults False and
  the recommendation to flip it in adopted configs is recorded as PROPOSED.
* All test counts in this report are from actual runs in this session; no
  number is carried over from prior reports without re-verification.
