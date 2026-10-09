# Historical Validation Call-Site Ruling — 2026-10-09

## Scope

23 historical `split="validation"` call sites identified by F-SPLIT-1 audit bundle (`evidence/f_split_1_audit_bundle_20261009/README.md` and `reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md` §2.4). Each requires an operator ruling before any rewrite or reliance for promotion authority.

## Ruling

Every historical site is classified as `HISTORICAL_ONLY` unless independently re-derived under current vocabulary (`"val"`), current split resolution, and current adoption authority.

No historical site grants current promotion authority. Historical evidence remains readable but is excluded from `current_authority()` unless re-derived.

## Key call-site categories

1. Historical experiment scripts (`run_experiment0/1/2/3.py`, `run_rbsv2_campaign.py`, etc.) — 6 sites.
2. Historical campaign scripts (`run_rbs_v3_campaign.py`, `run_rbs_v4_pilot.py`, etc.) — 6 sites.
3. Historical validation scripts (`run_rbs_v4_validation.py` × 6, `run_rbs_v4_validation_100.py` × 2) — 8 sites.
4. Historical diagnostics (`d7_r1_gemma_retest.py`, `d8_cognitive_trace.py`, etc.) — 3 sites.

Each site is listed individually in `evidence/historical_validation_call_site_rulings.json`.

## Operator decision required

For each site, the operator must confirm:
- The intended split (`dev`, `val`, `holdout`, or `unknown`).
- Whether the historical result remains valid for historical reference.
- Whether it may contribute to current promotion authority (default: NO).

No mass rewrite permitted. No historical result promoted to authority without independent re-derivation.
