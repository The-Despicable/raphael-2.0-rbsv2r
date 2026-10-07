# D2 BOUNDED EPISODE TRANSCRIPT
mission: d2-bounded-episode  generated: 2026-10-07T05:37:23Z
policy: engagement-d2-v1 v1 sha256=7cd6b566220a8e86…

## positive episode (2 steps, objective-terminated)
- step 0: recon_service_probe (exec.d1_lab_probe) decision_id=8ab256e988e58ee4 status=ActionProposalStatus.SUCCEEDED artifact=8e41a2d2dede4f6bacc55be37a6c34142a07ba449f1023023f19931f39c5f1fa
- step 1: lab_http_probe (exec.http_probe) decision_id=c9be5f541f344937 status=ActionProposalStatus.SUCCEEDED artifact=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- action A confirmed: True
- action B HTTP status: 302 redirect_url=http://dvwa/login.php followed=False
- termination: objective met: verified execution evidence present for ACT-D2-PROBE-0001, ACT-D2-HTTP-0002
- evidence store: /home/yaser/external-audits/raphael-2/evidence/demo/d2/20261007T053721Z/evidence_store.jsonl (5 execution records)

## kill switch (bootstrap-v0 decision source)
- steps denied: 2; process spawns: 0; capability invocations: 0

## wrong-target control
- terminated at: broker; process spawns: 0

every denial produced a persisted receipt and zero process spawns.
