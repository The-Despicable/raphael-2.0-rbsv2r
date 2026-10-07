# RSI-0 EVALUATION REPORT (group-relative strategy evaluation)
run: 20261006T194110Z  generated: 2026-10-06T19:41:10Z

Ranking rule: lexicographic: verified_completion desc, evidence_complete desc, steps asc, policy_id asc; hard violations and unscorable runs excluded
Limits: deterministic scenarios; no statistical confidence claims; holdout-based generalization and promotion are out of scope (absent holdout)

| candidate | scenario | verified | steps | denials | violations | termination |
|---|---|---|---|---|---|---|
| rsi0-c0-canonical | S1_nominal | False | 0 | 0 | 0 |  |
| rsi0-c1-reverse | S1_nominal | False | 0 | 0 | 0 |  |
| rsi0-c2-retry-a | S1_nominal | False | 0 | 0 | 0 |  |
| rsi0-c0-canonical | S2_http_fault | False | 0 | 0 | 0 |  |
| rsi0-c1-reverse | S2_http_fault | False | 0 | 0 | 0 |  |
| rsi0-c2-retry-a | S2_http_fault | False | 0 | 0 | 0 |  |
| rsi0-c0-canonical | S3_budget | False | 0 | 0 | 0 |  |
| rsi0-c1-reverse | S3_budget | False | 0 | 0 | 0 |  |
| rsi0-c2-retry-a | S3_budget | False | 0 | 0 | 0 |  |

## Per-candidate aggregates

- **rsi0-c0-canonical**: runs=3 verified=0 evidence_complete=0 denials=0 steps_total=0 violations=0
- **rsi0-c1-reverse**: runs=3 verified=0 evidence_complete=0 denials=0 steps_total=0 violations=0
- **rsi0-c2-retry-a**: runs=3 verified=0 evidence_complete=0 denials=0 steps_total=0 violations=0

## Ranking (eligible runs, declared rule)

- rsi0-c0-canonical / S1_nominal
- rsi0-c1-reverse / S1_nominal
- rsi0-c2-retry-a / S1_nominal
- rsi0-c0-canonical / S2_http_fault
- rsi0-c1-reverse / S2_http_fault
- rsi0-c2-retry-a / S2_http_fault
- rsi0-c0-canonical / S3_budget
- rsi0-c1-reverse / S3_budget
- rsi0-c2-retry-a / S3_budget

## Excluded runs

- 
- 
- 
- 
- 
- 
- 
- 
- 

Interpretation guardrail: deterministic scenarios — these are exact observed outcomes, not statistical estimates; no promotion decision is authorized or implied (holdout absent, no lineage machinery).
