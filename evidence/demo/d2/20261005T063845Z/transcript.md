# D2 BOUNDED EPISODE TRANSCRIPT
mission: d2-bounded-episode  generated: 2026-10-05T06:38:47Z
policy: engagement-d2-v1 v1 sha256=47f1820542b2264d…

## positive episode (2 steps, objective-terminated)
- step 0: recon_service_probe (exec.d1_lab_probe) decision_id=675840a3ec279563 status=ActionProposalStatus.SUCCEEDED artifact=cf9bb059234e53f4d011a72bf5e4141e65348315cc8dce426fc1e4fed4b758de
- step 1: lab_http_probe (exec.http_probe) decision_id=a9bbf621c6bf8f26 status=ActionProposalStatus.SUCCEEDED artifact=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- action A confirmed: True
- action B HTTP status: 302 redirect_url=http://dvwa/login.php followed=False
- termination: objective met: required evidence present for ACT-D2-PROBE-0001, ACT-D2-HTTP-0002
- evidence store: /home/yaser/external-audits/raphael-2/evidence/demo/d2/20261005T063845Z/evidence_store.jsonl (5 execution records)

## kill switch (bootstrap-v0 decision source)
- steps denied: 2; process spawns: 0; capability invocations: 0

## wrong-target control
- terminated at: broker; process spawns: 0

every denial produced a persisted receipt and zero process spawns.
