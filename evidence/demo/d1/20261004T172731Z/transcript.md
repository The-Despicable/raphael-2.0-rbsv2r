# D1 GOVERNED ACTION TRANSCRIPT
mission: d1-governed-action    generated: 2026-10-04T17:27:32Z

## positive
policy: engagement-d1-v1 v1 sha256=777999a3c8d5b817…
broker decision : allow (decision_id=44b5079f4ada9f29)
action_id       : 44b5079f4ada9f29
target identity : {"container_image": "vulnerables/web-dvwa", "identity": "dvwa", "probe_container": "kali-tools", "shared_networks": ["raphael-m1_raphael-net"], "target_ip": "172.19.0.4", "verified_at": 1791134851.7034876}
probe argv      : docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa
result status   : ActionProposalStatus.SUCCEEDED  service_confirmed=True
receipt         : event=EVT_f97fb0fb8998 broker_receipt=44b5079f4ada9f29 evidence_receipt=EVT_f97fb0fb8998
artifact        : artifacts/d1_lab_probe_20261004T172732Z_856dff95.txt sha256=7b7ec9ecbb046991b55bb285622f2019b1f646b1bdad7984b8fb34266c6b6c08 (digest verified)
evidence store  : /home/yaser/external-audits/raphael-2/evidence/demo/d1/20261004T172731Z/evidence_store.jsonl (execution_result + artifact records)

## restrictive control (bootstrap-v0)
terminated at: broker  decision=deny  reason=Action type not in allowed list: recon_service_probe; Capability not in allowed list: exec.d1_lab_probe; Impact 2.0 exceeds per-action limit 0.0 (requires explicit approval)
process spawns: 0  capability invocations: 0

## kill switch (decision source swapped to bootstrap-v0)
terminated at: broker  decision=deny
process spawns: 0  capability invocations: 0

## wrong-target control
terminated at: broker  reason=Target not in allowed scope: ('dvwa',)

every denial phase spawned zero processes and invoked the capability zero times.
