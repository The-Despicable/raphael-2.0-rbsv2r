# D1 GOVERNED ACTION TRANSCRIPT
mission: d1-governed-action    generated: 2026-10-05T07:32:53Z

## positive
policy: engagement-d1-v1 v1 sha256=777999a3c8d5b817…
broker decision : allow (decision_id=7baf12f6bae80325)
action_id       : 7baf12f6bae80325
target identity : {"container_image": "vulnerables/web-dvwa", "identity": "dvwa", "probe_container": "kali-tools", "shared_networks": ["raphael-m1_raphael-net"], "target_ip": "172.19.0.2", "verified_at": 1791185572.3152099}
probe argv      : docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa
result status   : ActionProposalStatus.SUCCEEDED  service_confirmed=True
receipt         : event=EVT_0d89b11c4de3 broker_receipt=7baf12f6bae80325 evidence_receipt=EVT_0d89b11c4de3
artifact        : artifacts/d1_lab_probe_20261005T073253Z_9078d957.txt sha256=86eefa8f2d9cac4d538612d938c10884d37fc85d0011e293c9fdbaf6754f4384 (digest verified)
evidence store  : /home/yaser/external-audits/raphael-2/evidence/demo/d1/20261005T073251Z/evidence_store.jsonl (execution_result + artifact records)

## restrictive control (bootstrap-v0)
terminated at: broker  decision=deny  reason=Action type not in allowed list: recon_service_probe; Capability not in allowed list: exec.d1_lab_probe; Impact 2.0 exceeds per-action limit 0.0 (requires explicit approval)
process spawns: 0  capability invocations: 0

## kill switch (decision source swapped to bootstrap-v0)
terminated at: broker  decision=deny
process spawns: 0  capability invocations: 0

## wrong-target control
terminated at: broker  reason=Target not in allowed scope: ('dvwa',)

every denial phase spawned zero processes and invoked the capability zero times.
