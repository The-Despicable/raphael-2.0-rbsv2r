# D1 GOVERNED ACTION TRANSCRIPT
mission: d1-governed-action    generated: 2026-10-05T06:38:51Z

## positive
policy: engagement-d1-v1 v1 sha256=777999a3c8d5b817…
broker decision : allow (decision_id=ba8ae7390ad66b86)
action_id       : ba8ae7390ad66b86
target identity : {"container_image": "vulnerables/web-dvwa", "identity": "dvwa", "probe_container": "kali-tools", "shared_networks": ["raphael-m1_raphael-net"], "target_ip": "172.19.0.2", "verified_at": 1791182331.1818194}
probe argv      : docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa
result status   : ActionProposalStatus.SUCCEEDED  service_confirmed=True
receipt         : event=EVT_99186952815a broker_receipt=ba8ae7390ad66b86 evidence_receipt=EVT_99186952815a
artifact        : artifacts/d1_lab_probe_20261005T063851Z_86b5a23c.txt sha256=23c893a09e0d5c70fbcf22f4ef1cd9eace8f45e0da97719d623914d251dea31d (digest verified)
evidence store  : /home/yaser/external-audits/raphael-2/evidence/demo/d1/20261005T063850Z/evidence_store.jsonl (execution_result + artifact records)

## restrictive control (bootstrap-v0)
terminated at: broker  decision=deny  reason=Action type not in allowed list: recon_service_probe; Capability not in allowed list: exec.d1_lab_probe; Impact 2.0 exceeds per-action limit 0.0 (requires explicit approval)
process spawns: 0  capability invocations: 0

## kill switch (decision source swapped to bootstrap-v0)
terminated at: broker  decision=deny
process spawns: 0  capability invocations: 0

## wrong-target control
terminated at: broker  reason=Target not in allowed scope: ('dvwa',)

every denial phase spawned zero processes and invoked the capability zero times.
