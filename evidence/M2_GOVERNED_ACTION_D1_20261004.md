# M2 GOVERNED ACTION (D1) — EVIDENCE PACKAGE — 2026-10-04

Task: RAPHAEL-M2-D1-2026-10-04, branch `offensive-restore`, HEAD `e6a8c707e`
(unchanged; nothing committed). Scope held to the bounded D1 demonstration: one
policy artifact, one strict loader, one narrow exec/ capability, one demo, one
test file. No LLM, no external targets, no policy broadening, no other weld
restoration, no commits.

---

## 1. Starting state

- Branch/HEAD: `offensive-restore` / `e6a8c707e614a1aa5468d5b93be324525513363f`.
- Worktree at start: all M0+M1 changes preserved (56 tracked-modification/
  untracked entries), `.venv` = Python 3.12.15, lab containers (dvwa,
  kali-tools, dvwa-db) running loopback-only from M1, `smoke_lab.sh` PASS.
- `policies/engagement-open-v0.json` inspected: still **unwired** — zero code
  references; it grants nothing in D1. Not used.
- `tests/test_am4_weld_gates.py` + `tests/test_p2_guardrail_*.py`: green at
  start (M1 suite 637/0/0); preserved unmodified.

## 2. Changes made (file-by-file)

| File | Change | Rationale |
|---|---|---|
| `policies/engagement-d1-v1.json` (new) | Named, versioned BOUNDED_LAB policy: allowed = exactly {action `recon_service_probe`} × {capability `exec.d1_lab_probe`} × {target `dvwa`}; explicit prohibited action/capability classes; tight rate limits (6/min, 1 concurrent); impact caps (2.0/action); `fail_closed` block (all flags mandatory-true); kill-switch = swap decision source to `bootstrap-v0` | The active D1 policy is the opposite of an open policy: one exact request |
| `src/orchestrator/runtime/policy.py` | Added `D1Policy` (strict loader: missing/malformed/stale/unsupported → `PolicyLoadError`, no BrokerPolicy produced; refuses `prohibited.targets: "*"` as self-contradictory; carries artifact sha256 in `engagement_id` for auditability) + `make_broker_from_policy()` factory. `BootstrapPolicy`/`make_broker_from_bootstrap` untouched (still the restrictive control + kill-switch target) | Deterministic, auditable policy loading without touching the canonical PDP |
| `src/orchestrator/exec/capabilities/__init__.py` (new) | Package docstring (INV-1 home for broker-gated capabilities) | — |
| `src/orchestrator/exec/capabilities/d1_lab_probe.py` (new) | The single D1 capability (CONV-3 gated): `inspect(target)` verifies the lab identity against the LIVE compose containers (running + image prefix `vulnerables/web-dvwa` + shared network with `kali-tools`), then runs the **fixed** argv `docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa` (no shell, no free-form args, timeout 90s, output capped 64 KiB), writes the raw output artifact (relpath + sha256), raises on failure/timeout (truthful FAILED). Refuses any non-`dvwa` target and refuses to run ungated | Smallest execution path that satisfies M2-C; NOT a restoration of W-01's general-purpose `_run_command` |
| `scripts/run_demo_d1.py` (new) | Deterministic driver (no LLM): positive phase through the full canonical 10-stage episode (`require_scope=True`, deterministic mission candidate), then restrictive control, kill switch, and a wrong-target control; subprocess spy proves zero spawns on every denial; verifies decision↔event↔receipt↔artifact linkage and the artifact digest; persists transcript + evidence store under a timestamped dir (never overwrites) | Reproducible D1 proof |
| `scripts/run_demo_d1.sh` (new) | One-command wrapper: lab health (smoke), target-identity verification (container + image + compose network) BEFORE anything runs, driver, verdict; nonzero exit on any failure | Required entry point |
| `tests/test_m2_d1_governed_action.py` (new) | 23 tests across the 10 required groups | §5 below |

**No changes** to: `runtime/stages.py`, `runtime/loop.py`, `runtime/scope.py`,
`brain/capability_broker.py`, `hardening/action_receipt.py`, `exec/evidence_store.py`,
`runtime/evidence_v1.py`, any weld gate or deleted body, any existing test.

## 3. Effective D1 policy and exact scope

- Policy artifact: `policies/engagement-d1-v1.json`, sha256
  `777999a3c8d5b8175d848e8c7b6de28a9499bd46f8ce566830e350c417032b59` (recorded in
  every decision's engagement_id).
- ScopeV0 (mission `d1-governed-action`): targets `(dvwa,)`; allowed action types
  `(recon_service_probe,)`; allowed capabilities `(exec.d1_lab_probe,)`;
  max_impact `2.0`. Scope check = the canonical `ScopeV0.covers()` conjunction in
  `stage_broker` (not a second PDP).
- Authorization = Broker's 5 dimensions (exact-match: target `dvwa`, action
  `recon_service_probe`, capability `exec.d1_lab_probe`, method `nmap`, impact
  2.0 ≤ 2.0) AND ScopeV0 containment AND policy validity. Anything else denies.

## 4. Positive action — broker decision, execution, receipt, artifact

From the archived demo run `evidence/demo/d1/20261004T164502Z/transcript.json`:

| Field | Value |
|---|---|
| Broker decision | `allow`, decision_id `86d95a9496432f2c` |
| Action id | `86d95a9496432f2c` (ACT-D1-PROBE-0001) |
| Target identity (verified live) | `dvwa`, image `vulnerables/web-dvwa`, ip `172.19.0.4`, shared network `raphael-m1_raphael-net`, probe container `kali-tools` |
| Probe argv (fixed) | `docker exec kali-tools nmap -Pn -sT -p 80 --host-timeout 45s dvwa` |
| Result status | `ActionProposalStatus.SUCCEEDED` (AUTHORIZED → STARTED → SUCCEEDED lifecycle on the broker receipt) |
| Service confirmed | `true` — real nmap output: `80/tcp open http` for `dvwa (172.19.0.4)` |
| Receipt | event `EVT_…`, broker_receipt `86d95a9496432f2c`, EvidenceReceipt linked (decision_id + broker_receipt_id + scope_hash + artifact_refs) |
| Artifact | `artifacts/d1_lab_probe_20261004T164504Z_d8f54efd.txt`, 294 bytes, sha256 `1c719dacb91d96cee0f1da0ba80a1cc304ec331855b1a684e8ee13c7adc6dd09`, digest verified against stored bytes |
| Evidence store | `evidence/demo/d1/20261004T164502Z/evidence_store.jsonl` — `execution_result` record (`ev1_c3d78c3a…`) + `artifact` record (`ev1_4fc75569…`, execution_ref → execution record, parents linked) |
| Subprocess spawns in the positive phase | 3 — exactly the approved action (2× `docker inspect` identity verification + 1× `docker exec nmap`) |

Note: the broker logs an ALLOW decision (INV-2) and the receipt carries
`authorized_argv=()` — the argv-binding variant of the contract is exercised by the
sandbox path, not this capability class; the D1 capability binds its argv by code.

## 5. Denial evidence (restrictive, kill switch, wrong target)

From the same transcript (`transcript.md` / `transcript.json`):

| Phase | Terminated at | Reason | Process spawns | Capability invocations |
|---|---|---|---|---|
| Restrictive control (`bootstrap-v0` decision source) | broker stage | `Action type not in allowed list: recon_service_probe; Capability not in allowed list: exec.d1_lab_probe; Impact 2.0 exceeds per-action limit 0.0` | **0** | **0** |
| Kill switch (documented decision-source swap to `bootstrap-v0`) | broker stage | same deny class | **0** | **0** |
| Wrong target (`example.invalid`) | broker stage | `Target not in allowed scope: ('dvwa',)` | **0** | **0** |

Spy-based proof: `subprocess.run` is instrumented for the whole driver; the spawn
counter did not advance during any denial phase (asserted in code, exit 1 on
violation), and each denial phase used a fresh capability instance whose
invocation counter stayed 0.

## 6. Proof that denied paths do not spawn a process

Three independent layers, all asserted:
1. canonical ordering: a denial at `stage_broker` fails the stage before
   `stage_pep` exists in the outputs (`assert "pep" not in out`);
2. spy: instrumented `subprocess.run` counts zero calls during denials;
3. capability counter: `D1LabProbeCapability.invocation_count == 0` after denials
   (the CONV-3 gate was never opened).

Additionally, `test_pep_stage_refuses_denied_receipt` proves a DENIED receipt
cannot even be *started* through the broker's lifecycle (`start_execution`
raises; no spawn).

## 7. Tests

- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/ --no-header -q`
- Interpreter: Python **3.12.15** (repository `.venv`)
- Full suite: **660 collected — 660 passed / 0 failed / 0 skipped — 22.08 s**
  (637 M0/M1 tests + 23 new D1 tests). M0 regression tests, P2 guardrails, and
  all weld tests pass **unmodified** — no denial test was flipped.
- D1 file alone: 23 passed (includes one live-lab test, executed here: the real
  probe against the running dvwa container).
- Protected historical tree: byte-identical before/after the suite (5th and 6th
  consecutive identical comparisons against the M0 baseline).

## 8. Historical-data integrity

`arena/results/raw` (52,022 files) compared against
`evidence/arena_contamination_20261004/PRE_M0_SHA256SUMS.txt`: **identical**.
Baseline untouched; contamination record and 14 quarantined dirs preserved.

## 9. D1 transcript and reproduction

```bash
# prerequisites: M1 lab running (docker compose --project-directory . -p raphael-m1 \
#   -f configs/docker-compose.yml -f configs/docker-compose.m1-loopback.yml \
#   up -d --build dvwa kali-tools)
bash scripts/run_demo_d1.sh        # exits 0 only if ALL phases hold
```

Archived runs (never overwritten): `evidence/demo/d1/20261004T163946Z` (loader
bug found+fixed), `20261004T164000Z` (first full pass), `20261004T164502Z`
(final, cited above). Each contains `transcript.md`, `transcript.json`,
`evidence_store.jsonl`, `artifacts/`.

## 10. Acceptance gate

| Criterion | Verdict | Proof |
|---|---|---|
| Cold-start operation | **PASS** | §9 — documented one-command reproduction |
| Local lab healthy, loopback-safe | **PASS** | `smoke_lab.sh` PASS inside the demo; override file in every invocation |
| Scope — exact target identity validated | **PASS** | live docker-inspect identity check (§4) + ScopeV0 |
| Broker AUTHORIZED for the permitted request | **PASS** | decision `allow`, decision_id `86d95a9496432f2c` |
| PEP mediation (canonical Broker → PEP route) | **PASS** | receipt lifecycle AUTHORIZED→STARTED→SUCCEEDED driven by `stage_pep`; no side path exists |
| Actual execution — genuine nmap output vs local DVWA | **PASS** | `80/tcp open http`, 294-byte artifact |
| Persisted receipt linking action, decision, evidence | **PASS** | EvidenceReceipt + evidence store records with execution_ref linkage |
| Artifact integrity | **PASS** | sha256 recomputed from stored bytes, matches |
| Restrictive policy denies the same request | **PASS** | §5 restrictive row |
| Kill switch denies, no process spawned | **PASS** | §5 kill-switch row + spy proof |
| Other welds remain fail-closed | **PASS** | weld/guardrail tests green unmodified; `test_d1_broker_denies_unimplemented_welded_capabilities`; W-01 body still raises |
| Tests pass without weakened assertions | **PASS** | 660/660; zero assertion changes to existing tests |
| Scope discipline | **PASS** | no external targets, no provider requests, no unrelated restoration, no commits |

**M2/D1 gate: PASS.**

## 11. Differences from the broader gap plan (justified)

The gap plan's M2 sketch proposed: broker wildcard support for action/capability
dimensions, a ScopeV0 "open mode", loading `engagement-open-v0.json`, flipping
~40 denial tests, and restoring the W-01 `_run_command` body. The task order
narrows all of this, and D1 was implemented within the narrower contract:

1. **No wildcard changes** — the D1 policy is exact-match on every dimension;
   wildcards are unnecessary and would broaden the PDP. The open-policy wiring
   (P1.2) remains future work, explicitly not done here.
2. **No `engagement-open-v0.json` activation** — the D1 policy
   (`engagement-d1-v1.json`) is a different, bounded artifact; the open policy
   remains unwired (verified).
3. **No ScopeV0 open mode** — a minimal explicit lab scope is used.
4. **No test flips** — denial tests untouched; positive assertions added only
   for the D1 path.
5. **No W-01 restoration** — W-01's deleted body is the general-purpose
   arbitrary-command executor; reviving it would conflict with M2-C's fixed-
   argv requirement. Instead, a new single-purpose capability
   (`exec.d1_lab_probe`) implements the one permitted action. The other nine
   bodies remain deleted. Consequence: the D1 capability is demo-scoped; the
   broader arsenal wiring (gap-plan F3) is unaffected and still future work.

## 12. M0 security status and outstanding blockers

- **Provider-side NVIDIA key rotation: still pending — operator-owned.** No
  provider requests, no history reads for credentials, no secrets printed. The
  **M0 security gate remains NOT closed**.
- D1 is no-LLM by design; nothing in the positive path depends on credentials.
- Outstanding (unchanged from M1): holdout dataset `unverifiable-in-repo`;
  commit authorization for the whole worktree; permanent fixes for the base
  compose defects (loopback override is currently invocation-scoped);
  19 structural import failures + sword drift (M4+ tickets).

## 13. Diff summary

New: `policies/engagement-d1-v1.json`,
`src/orchestrator/exec/capabilities/{__init__.py,d1_lab_probe.py}`,
`scripts/run_demo_d1.py`, `scripts/run_demo_d1.sh`,
`tests/test_m2_d1_governed_action.py`,
`evidence/M2_GOVERNED_ACTION_D1_20261004.md`, `evidence/demo/d1/<3 runs>/`.
Modified: `src/orchestrator/runtime/policy.py` (append-only: D1 loader + factory).
Preserved untouched: all M0/M1 changes, all weld gates, `bootstrap-v0.json`,
`engagement-open-v0.json` (unwired), protected evidence trees. Nothing committed.

## 14. Recommendation for the next task

M3 (Autonomous Episode, D2) is the natural successor but is **gated on the
operator**: (a) confirmed key rotation + live LLM endpoint configuration, and
(b) an explicit decision on whether the D1 policy should be widened to a small
per-engagement allowlist (still exact, still bounded) for multi-action episodes.
A lower-risk interim step is a small hardening ticket: permanently fix the base
compose defects (loopback binding, build-context invocation, kali PYTHONPATH)
and the `sword.phase_2_exploit` drift. Not started; awaiting operator review.
