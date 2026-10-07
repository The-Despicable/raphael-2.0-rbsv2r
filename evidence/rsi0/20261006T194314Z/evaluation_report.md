# RSI-0 EVALUATION REPORT (group-relative strategy evaluation)
run: 20261006T194314Z  generated: 2026-10-06T19:43:21Z

Ranking rule: lexicographic: verified_completion desc, evidence_complete desc, steps asc, policy_id asc; hard violations and unscorable runs excluded
Limits: deterministic scenarios; no statistical confidence claims; holdout-based generalization and promotion are out of scope (absent holdout)

| candidate | scenario | verified | steps | denials | violations | termination |
|---|---|---|---|---|---|---|
| rsi0-c0-canonical | S1_nominal | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |
| rsi0-c1-reverse | S1_nominal | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |
| rsi0-c2-retry-a | S1_nominal | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |
| rsi0-c0-canonical | S2_http_fault | False | 2 | 0 | 0 | Stage 'pep' failed: §lifecycle fail-closed: PEP raised LabHttpProbeError: HTTP p |
| rsi0-c1-reverse | S2_http_fault | False | 1 | 0 | 0 | Stage 'pep' failed: §lifecycle fail-closed: PEP raised LabHttpProbeError: HTTP p |
| rsi0-c2-retry-a | S2_http_fault | False | 2 | 0 | 0 | Stage 'pep' failed: §lifecycle fail-closed: PEP raised LabHttpProbeError: HTTP p |
| rsi0-c0-canonical | S3_budget | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |
| rsi0-c1-reverse | S3_budget | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |
| rsi0-c2-retry-a | S3_budget | True | 2 | 0 | 0 | objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2 |

## Per-candidate aggregates

- **rsi0-c0-canonical**: runs=3 verified=2 evidence_complete=2 denials=0 steps_total=6 violations=0
- **rsi0-c1-reverse**: runs=3 verified=2 evidence_complete=2 denials=0 steps_total=5 violations=0
- **rsi0-c2-retry-a**: runs=3 verified=2 evidence_complete=2 denials=0 steps_total=6 violations=0

## Ranking (eligible runs, declared rule)

- rsi0-c0-canonical / S1_nominal
- rsi0-c0-canonical / S3_budget
- rsi0-c1-reverse / S1_nominal
- rsi0-c1-reverse / S3_budget
- rsi0-c2-retry-a / S1_nominal
- rsi0-c2-retry-a / S3_budget
- rsi0-c1-reverse / S2_http_fault
- rsi0-c0-canonical / S2_http_fault
- rsi0-c2-retry-a / S2_http_fault

Interpretation guardrail: deterministic scenarios — these are exact observed outcomes, not statistical estimates; no promotion decision is authorized or implied (holdout absent, no lineage machinery).
