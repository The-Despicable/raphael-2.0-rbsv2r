# D2 BOUNDED EPISODE TRANSCRIPT
mission: d2-bounded-episode  generated: 2026-10-05T06:38:07Z
policy: engagement-d2-v1 v1 sha256=47f1820542b2264d…

## positive episode (2 steps, objective-terminated)
- step 0: recon_service_probe (exec.d1_lab_probe) decision_id=d720ad0ad2acc433 status=ActionProposalStatus.SUCCEEDED artifact=1b9f851d5e7e3b0bfc15afa1fcd7b94bb298fb1a911ab070e755175492dfdedb
- step 1: lab_http_probe (exec.http_probe) decision_id=34579c4ca166dc38 status=ActionProposalStatus.SUCCEEDED artifact=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- action A confirmed: True
- action B HTTP status: 302 redirect_url=http://dvwa/login.php followed=False
- termination: objective met: required evidence present for ACT-D2-PROBE-0001, ACT-D2-HTTP-0002
- evidence store: /home/yaser/external-audits/raphael-2/evidence/demo/d2/20261005T063806Z/evidence_store.jsonl (5 execution records)

## kill switch (bootstrap-v0 decision source)
- steps denied: 2; process spawns: 0; capability invocations: 0

## wrong-target control
- terminated at: broker; process spawns: 0

every denial produced a persisted receipt and zero process spawns.
