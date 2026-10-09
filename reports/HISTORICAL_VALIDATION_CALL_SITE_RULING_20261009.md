# Historical `validation` Call-Site Ruling — corrected 2026-10-09

**STATUS: CENSUS VERIFIED. RULINGS PENDING OPERATOR RATIFICATION.**

**Verified call sites: 22** (prior reports variously claimed 23, 25, and "23+"; those numbers are withdrawn).

## How this census was produced

A repository-wide regex scan of SOURCE CODE for `split="validation"`,
`split: str = "validation"` defaults, and `{"split": "validation"}`
dict keys. Every entry below was verified twice: the file must exist
(`test -f`), and the recorded line must still contain the matched text.
No entry is carried over from a prior report.

Occurrences of the string inside generated historical run data
(`arena/**`, 4788 occurrences across 4788 files) are NOT call sites. They record which
split a past run actually used. They are counted, reported, and not
rewritten.

## Ruling status

Every site carries the default ruling `HISTORICAL_ONLY` with
`current_authority_granted: false` and
`ruling_status: PENDING_OPERATOR_RATIFICATION`.

**No operator ruling has been issued.** The prior version of this
document and its JSON claimed `QUARANTINED`-style authority without one.
That claim is withdrawn. Phase 3 readiness remains blocked until the
operator ratifies each site's intended split.

## Sites by class

| Class | Count |
|---|---|
| historical_diagnostic | 8 |
| historical_script | 10 |
| library_code | 1 |
| test_code | 3 |

## Full census

| id | class | symbol |
|---|---|---|
| `scripts/run_experiment0.py:50` | historical_script | `def run_single(seed: int, run_id: str, split: str = "validation") -> dict:` |
| `scripts/run_experiment1.py:38` | historical_script | `split="validation"` |
| `scripts/run_experiment2.py:37` | historical_script | `split="validation"` |
| `scripts/run_experiment3.py:47` | historical_script | `split="validation"` |
| `scripts/run_rbs_v3_campaign.py:278` | historical_script | `split="validation",` |
| `scripts/run_rbs_v4_pilot.py:165` | historical_script | `split="validation",` |
| `scripts/run_rbs_v4_repair_verify.py:130` | historical_script | `split="validation",` |
| `scripts/run_rbs_v4_validation.py:90` | historical_script | `split="validation",` |
| `scripts/run_rbsv2_campaign.py:314` | historical_script | `split="validation",` |
| `scripts/run_t10_fix_verify.py:41` | historical_script | `seed=seed, split="validation", llm_config_override=OVERRIDE,` |
| `src/arena/d10_falsification_defeater_diagnostic.py:70` | historical_diagnostic | `split="validation",` |
| `src/arena/d10_regression_test.py:144` | historical_diagnostic | `split="validation",` |
| `src/arena/d11_regression_test.py:134` | historical_diagnostic | `split="validation",` |
| `src/arena/d13_diagnostic_runner.py:192` | historical_diagnostic | `split='validation',` |
| `src/arena/d16_holdout_runner.py:144` | historical_diagnostic | `split="validation",` |
| `src/arena/d7_r1_gemma_retest.py:74` | historical_diagnostic | `split="validation",` |
| `src/arena/d8_cognitive_trace.py:47` | library_code | `split="validation",` |
| `src/arena/d8_regression_test.py:68` | historical_diagnostic | `split="validation",` |
| `src/arena/d9_regression_test.py:71` | historical_diagnostic | `split="validation",` |
| `tests/test_f_split_1_split_vocabulary.py:7` | test_code | `The most consequential instance was ``split="validation"``: the canonical` |
| `tests/test_run_identity.py:42` | test_code | `# split="validation" — an invalid label under the corrected vocabulary` |
| `tests/test_run_identity.py:92` | test_code | `_make_runner(seed=7, split="validation")` |

## Operator decision required

For each site the operator must confirm:
- the intended split (`dev`, `val`, `holdout`, or `unknown`);
- whether the historical result remains valid as historical reference;
- whether it may contribute to current promotion authority (default: NO).

No mass rewrite is permitted. No historical result is promoted to
authority without independent re-derivation under current rules.
