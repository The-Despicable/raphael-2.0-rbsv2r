# D1 GOVERNED ACTION TRANSCRIPT
mission: d1-governed-action    generated: 2026-10-04T16:45:04Z

## positive
policy: engagement-d1-v1 v1 sha256=777999a3c8d5b817…
broker decision : allow (decision_id=86d95a9496432f2c)
action_id       : 86d95a9496432f2c
target identity : {"container_image": "vulnerables/web-dvwa", "identity": "dvwa", "probe_container": "kali-tools", "shared_networks": ["raphael-m1_raphael-net"], "target_ip": "172.19.0.4", "verified_at": 1791132303.2785308}
probe argv      : docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa
result status   : ActionProposalStatus.SUCCEEDED  service_confirmed=True
receipt         : event=EVT_48a4217588bb broker_receipt=86d95a9496432f2c evidence_receipt=EVT_48a4217588bb
artifact        : artifacts/d1_lab_probe_20261004T164504Z_d8f54efd.txt sha256=1c719dacb91d96cee0f1da0ba80a1cc304ec331855b1a684e8ee13c7adc6dd09 (digest verified)
evidence store  : /home/yaser/external-audits/raphael-2/evidence/demo/d1/20261004T164502Z/evidence_store.jsonl (execution_result + artifact records)

## restrictive control (bootstrap-v0)
terminated at: broker  decision=deny  reason=Action type not in allowed list: recon_service_probe; Capability not in allowed list: exec.d1_lab_probe; Impact 2.0 exceeds per-action limit 0.0 (requires explicit approval)
process spawns: 0  capability invocations: 0

## kill switch (decision source swapped to bootstrap-v0)
terminated at: broker  decision=deny
process spawns: 0  capability invocations: 0

## wrong-target control
terminated at: broker  reason=Target not in allowed scope: ('dvwa',)

every denial phase spawned zero processes and invoked the capability zero times.
