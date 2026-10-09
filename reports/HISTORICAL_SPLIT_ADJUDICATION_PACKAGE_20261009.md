# Historical Split Call-Site Adjudication Package — 2026-10-09

**Branch:** `governance/rsi-1-provenance-correction`
**Commit:** `9936223dc0363cc4b3f210c1c3015f20b7c379c6`
**Tree:** `d68d8e4d8fb320f2e5cfa82068facfc9efa9df9d`
**Census:** `evidence/historical_split_adjudication/call_site_census.json` (22 sites)
**Method:** `evidence/historical_split_adjudication/ADJUDICATION_METHOD.md`

> **NO OPERATOR RATIFICATION HAS OCCURRED.** Every one of the 22 entries is
> `PENDING_OPERATOR_RATIFICATION` and `current_authority_granted: false`.
> **This package does not authorize Phase 3.**

---

## 1. Independent verification performed before building this package

The census was re-derived from source rather than accepted from the prior
report, and the search was widened beyond literal labels.

| Check | Result |
|---|---|
| Literal `split="validation"` / default-arg / dict-key forms | **21 occurrences across 20 files**, plus `scripts/run_rbs_v4_validation.py` = 22 sites |
| Derived / variable split values | `run_rbs_v4_validation_100.py:57` uses `SPLIT_NAME = "holdout"` — **not** a legacy site |
| Adapters / wrappers | `d6b_runner.py`, `d6b_runner_fixed.py`, `d6c_holdout_runner.py` all **discard** `split` (`return self._factory(seed=seed)`) |
| Do any sites route through those adapters? | **No.** All 19 code files construct `AblationRunner(...)` directly |
| Indirect dispatch (`VALIDATION_SEEDS`) | Imported by 5 diagnostics; seeds derived from label `"{template}_val"` (`d6_manifest.py:191`) |

The prior 22-site count is **confirmed**. The prior 23 / 25 / "23+" figures
remain withdrawn.

---

## 2. What the evidence establishes

### 2.1 Actual historical behaviour — established, HIGH confidence

At the frozen baseline `b6ef24bdb`, `src/arena/ablation_runner.py:810`:

```python
sp = split_map.get(self.split, ScenarioSplit.DEV)
```

`"validation"` was not in the map, so **every one of these sites executed under
`ScenarioSplit.DEV`**. The fallback was still present at `bd1fcc109^` and was
removed by F-SPLIT-1 (`bd1fcc109`).

### 2.2 The seed-band finding

| Corpus | Count |
|---|---|
| Run manifests recording `split: "validation"` | **2,394** |
| …of those, seed in the 1000–1999 band | **2,394 (100%)** |
| Run-id split suffixes in the repo | 1,622 (`_dev` 222, `_val` 200, `_holdout` 1,200) |
| …validation-labelled runs carrying a split suffix | **0** (legacy format) |

Because DEV's offset is `0` and VAL's is `1000`, the 2,394 runs used the band
values as their **absolute** seeds. Re-deriving them under `VAL` would shift
every absolute seed by +1000 and would **not reproduce the historical results**.

> **Consequence for adjudication:** a `VAL` ruling would attach a label to runs
> that demonstrably did not run under `VAL`. Any site ruled `VAL` has historical
> evidence that contradicts its own label.

### 2.3 Intended semantics — NOT established

No rank-1 or rank-2 evidence was located for any site. Three files contain a
contemporaneous author statement (rank 3, unratified):

| File | Statement |
|---|---|
| `scripts/run_rbs_v4_validation.py` | docstring: "RBS-v4 VALIDATION RUN" |
| `src/arena/d7_r1_gemma_retest.py` | docstring: "Seeds: VALIDATION split (5 per template)" |
| 5 diagnostics | import `VALIDATION_SEEDS`, derived from label `"{template}_val"` |

These raise confidence to `LOW`. They do not set a ruling.

---

## 3. Census summary

| Metric | Value |
|---|---|
| Total sites | **22** |
| Live call sites | **19** |
| Non-live references (negative tests / documentation) | **3** |
| `proposed_ruling` = DEV / VAL / HOLDOUT / UNKNOWN | **0 / 0 / 0 / 22** |
| `confidence` HIGH / MEDIUM / LOW / INSUFFICIENT | **0 / 0 / 19 / 3** |
| `operator_ruling_status` | **22 × PENDING_OPERATOR_RATIFICATION** |
| `current_authority_granted` | **22 × false** |

### The 3 non-live sites

These contain the legacy label but are **not** historical call sites, and must
not be adjudicated as if they were:

| Site | Why |
|---|---|
| `tests/test_run_identity.py:92` | Negative test — asserts `InvalidScenarioSplit` **is raised** for the legacy label. It supplies `"validation"` in order to prove refusal. |
| `tests/test_run_identity.py:42` | Comment in the `_make_runner` helper describing the *pre-correction* default. Not executable. |
| `tests/test_f_split_1_split_vocabulary.py:7` | Module docstring describing the historical defect. Not executable. |

---

## 4. Which sites have sufficient evidence for a proposed ruling?

**None — for intent.**

Every site is `UNKNOWN`. That is not an omission in the work; it is the finding.
`proposed_ruling` records *intended semantics*, and intended semantics are not
derivable from:

- the implementation (rank 4) — which was the defect;
- the filename (rank 5) — demonstrated unreliable by `run_rbs_v4_validation_100.py`;
- the run-id (rank 5) — 0 of 2,394 validation-labelled runs carry a split suffix;
- author docstrings (rank 3) — unratified self-assertion;
- any prior report (rank 6) — excluded by construction.

What *is* established is actual behaviour (§2.1) and the seed-band consequence
(§2.2). Both are recorded per site under `actual_historical_behavior` and
`evidence_references`.

---

## 5. Which sites must remain UNKNOWN?

All 22, until the operator rules. The package is structured so that ratification
is a single recorded decision per site and requires no further engineering.

---

## 6. Explicit statement on ratification

**No operator ruling has been made on any of these 22 sites.**

The operator attestation at `evidence/provenance_correction/OPERATOR_ATTESTATION.md`
remains **PENDING — NOT SIGNED**; the agent performing this work does not know
the operator's identity and did not invent one.

Phase 3 readiness remains blocked while these rulings are outstanding, as
recorded in `evidence/phase3_readiness/REMEDIATION_MANIFEST.json`
(`phase3_blocked_until_ratified: true`) and
`evidence/provenance_correction/CORRECTIVE_REMEDIATION_MANIFEST.json`
(`operator_ratification_complete: false`).

---

## 7. What the operator is being asked to decide

For each of the 19 live sites, one of:

- **DEV** — the author meant DEV. Consistent with what the runs actually did.
  *Note: the executed seeds were in the validation band, so DEV is behaviourally
  accurate but the band choice would itself need explaining.*
- **VAL** — the author meant VAL. *The 2,394-run corpus contradicts this for the
  runs it covers: those runs executed under DEV and will not reproduce under VAL.*
- **HOLDOUT** — the author meant HOLDOUT. *Would contradict the corpus for the
  same reason, more strongly.*
- **RETIRE** — the site is dead and its results should be marked superseded.

The 3 non-live sites need no adjudication; they should be reclassified as
negative-test/documentation references and closed.