# ADJUDICATION METHOD — historical split call sites

**Date:** 2026-10-09
**Branch:** `governance/rsi-1-provenance-correction`
**Purpose:** to state, before any ruling is made, what evidence may and may not
decide a historical split call site's intended semantics.

---

## 1. The question being asked

For each site that supplies the legacy split label `"validation"` to an
`AblationRunner`, two different questions arise. Conflating them is the error
this method exists to prevent.

| Question | Answerable from the repository? |
|---|---|
| **Q1 — What split did these runs ACTUALLY execute under?** | **Yes.** Established by the baseline resolver and corroborated by run manifests. |
| **Q2 — What split did the author INTEND?** | **No.** Not from code, filenames, run-ids, or contemporaneous prose. Only operator ratification can answer it. |

Every field in `call_site_census.json` is explicit about which question it
answers. `actual_historical_behavior` answers Q1. `proposed_ruling` answers Q2,
and is `UNKNOWN` for all 22 sites.

---

## 2. Evidence hierarchy

Strongest first. A proposed ruling may only be raised above `UNKNOWN` by
evidence at rank 1 or 2.

**Rank 1 — Operator ratification.**
A recorded human decision. Nothing in this package constitutes one.

**Rank 2 — Pre-registered intent held outside the code path.**
A frozen protocol, preregistration record, or campaign manifest that names the
intended split *before* the runs executed. No such record has been located for
any of these sites. The reproducibility manifest declares `dataset.total_rows`
and a `design` block but never names the split of these call sites.

**Rank 3 — Contemporaneous author statement in the file itself.**
A docstring written by the original author at the time. Recorded, cited, and
treated as a *lead*, not a ruling. Raises confidence from `INSUFFICIENT` to
`LOW`; it never sets `proposed_ruling`.

**Rank 4 — Implementation behavior.**
What the code did. Establishes **actual** behavior only. Cannot establish
intent, and here it is actively misleading: the implementation was the *bug*.
At the frozen baseline `b6ef24bdb`, `src/arena/ablation_runner.py:810` read
`sp = split_map.get(self.split, ScenarioSplit.DEV)`, so `"validation"` silently
became `DEV`. Using that to infer intent is circular — it would ratify the
defect as the intent.

**Rank 5 — Filename, run-id, or directory name.**
Explicitly excluded. `scripts/run_rbs_v4_validation_100.py` is the counter
example: it is named "validation" and actually runs the **HOLDOUT** split
(`SPLIT_NAME = "holdout"`, line 57). A name is not evidence of anything.

**Rank 6 — A self-authored report, including this one.**
Excluded by construction. Every citation in this package points at source,
git history, or run artifacts, never at a narrative.

---

## 3. Current code behavior is not proof of historical intent

This is stated as a rule, not a caveat.

`src/arena/ablation_runner.py` today refuses `"validation"` outright. That is
correct *now* and says nothing about what any of these sites *meant*. A site's
correctness after F-SPLIT-1 and its historical intent are independent questions.

Conversely, the pre-correction behavior proves the sites *ran* as DEV. It does
not prove they *wanted* to.

---

## 4. Missing or contradictory evidence defaults to UNKNOWN

Where evidence is absent, silent, or points in two directions at once, the
`proposed_ruling` is `UNKNOWN`. `UNKNOWN` is a real answer, not a placeholder to
be filled in later by an engineer — only an operator can close it.

Confidence describes the strength of what is *recorded*, not optimism:

| Confidence | Meaning |
|---|---|
| `HIGH` | Rank 1 or 2 evidence exists. |
| `MEDIUM` | Strong rank-3 corroboration from multiple independent statements. |
| `LOW` | Only rank-3, rank-4, or rank-5 material exists. |
| `INSUFFICIENT` | Nothing beyond the bare legacy label. |

---

## 5. UNKNOWN sites are excluded from current authoritative evaluation

No site in this package grants current authority. Every entry carries:

```
"operator_ruling_status": "PENDING_OPERATOR_RATIFICATION",
"current_authority_granted": false
```

An `UNKNOWN` site is excluded from current authoritative evaluation until it is
either ratified or explicitly retired. It remains **readable** as historical
material — the ledger's audit-only accessors are unaffected — but it is never a
current-authority input.

---

## 6. A material finding the operator must weigh

The evidence establishes something that is easy to miss and expensive to
discover later:

> **All 2,394 historical run manifests that recorded `split: "validation"` carry
> a seed in the 1000–1999 band.** Because the baseline resolver mapped the
> label to `DEV` (offset `0`), the absolute seeds those runs actually used were
> the band values themselves. Under `VAL` (offset `1000`) the absolute seeds
> would have been 1,000 higher.

Consequence: **re-deriving these historical results under `VAL` will not
reproduce them.** The seeds shift. If the operator rules `VAL` for any of these
sites, the historical evidence under that ruling does not support the label it
would carry — the label would describe an intent the runs never executed.

This is a finding about the evidence. It is not a ruling, and it does not
resolve any site.

---

## 7. What this package does not do

- It does not ratify, sign, or imply operator approval.
- It does not modify any historical script, run record, or manifest.
- It does not change the 22-site census it was built from.
- It does not alter the authoritative-anchor manifest or the holdout
  classification.
- It does not authorize Phase 3, adoption, promotion, or L2.