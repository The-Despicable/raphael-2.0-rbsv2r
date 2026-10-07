# RAPHAEL GAP ANALYSIS & IMPROVEMENT PLAN — 2026-10-04

**Basis**: `RAPHAEL_E2E_AUDIT_20261004.md` (same-day E2E audit, branch `offensive-restore`,
HEAD `e6a8c707e`). **Alignment**: `RAPHAEL_ARCHITECTURE_ROADMAP_v2.md` §6 F-phases (F0–F9)
and §1 end-state. This document converts the audit findings into (a) explicit target
states, (b) a gap matrix, and (c) a sequenced improvement plan with gates — the fastest
route to a demonstrable system, then the route to end-product state.

**Correction to audit E-03**: the dead external tree (`/home/yaser/raphael-2.0/`) was a
*duplicate*. All compose build contexts exist in-repo (`src/{cai,cloak,mhddos}-service`,
`src/{c2-server,phishing,recon-pipeline,kali-tools,mcp-hub}`, `sliver/`), and
`configs/docker-compose.yml` includes DVWA (`vulnerables/web-dvwa`). The arena is
self-contained; Phase-2 items #9–10 (cloak/mhddos bodies) **are** recoverable locally at
`src/cloak-service/`, `src/mhddos-service/`.

---

## 1. TARGET STATES

Three concrete, verifiable states. Each has a checklist (§8) and a demo script (§6).

### D1 — "Governed Action" demo (no LLM required)
One command (`scripts/run_demo_d1.sh`) brings up a minimal lab, and the canonical chain
executes **for real**, on record:

> operator runs demo → ScopeV0 open-mode check → **CapabilityBroker AUTHORIZED** under
> wired `engagement-open-v0` → PEP dispatch → restored exec sink → **real nmap output
> against the local DVWA container** → ActionReceipt + evidence persisted → printed
> transcript with decision IDs → **kill-switch demonstrator**: swap decision source to
> `bootstrap-v0`, same action → DENIED, exit 403.

Proves: gates real, restoration real, receipts real, deny-by-default reversible. This is
the smallest honest demo of the platform's core thesis (mediated execution, not raw
tool-calling).

### D2 — "Autonomous Episode" demo (LLM required)
One command runs a **multi-iteration autonomous episode** (≥3 iterations, `action_cap`
open) against the lab: recon → world-model update → next-action selection →
execution → receipts for every action, **zero human approvals**, ending in an honest
terminal state (objective met / REFUSE / dead-end report). Recorded artifacts under
`evidence/demo/`.

### P — End-product state (v2 §1, six properties simultaneously)
Armed + Continuous + Absorbing + Self-validating + Self-red-teaming + Improving, with
F0–F9 gates green, DoD-7 scale invariance, ops hardening, and a truthful README. This is
the v2 roadmap's own Definition of Done; the plan below reaches it via D1→D2→F3→F4/F5/F6
→F8/F9.

---

## 2. GAP MATRIX (current → D1 → D2 → P)

Gap class: ENV = environment bring-up, CODE = source work, DATA = artifact/data
integrity, HYG = hygiene, DOC = documentation. Effort: S/M/L per v2 conventions.

| # | Dimension | Current (audit ref) | D1 needs | D2 needs | P needs | Class | Effort to D1 |
|---|---|---|---|---|---|---|---|
| G-1 | Interpreter/env | Python 3.14.4 system, no venv, no dotenv (E-01/E-02) | venv 3.12 + deps | + `.env` live LLM endpoint | + multi-key rotation design (docs exist) | ENV | S |
| G-2 | Lab infrastructure | Docker up, **0 containers**, compose never validated end-to-end (E-03) | `dvwa` + `kali-tools` (or host toolchain) healthy | + neo4j if world-model persists | full stack incl. c2/sliver/phish/recon | ENV | S–M |
| G-3 | Toolchain | 1/24 tools (`httpx` only) | nmap (+1 scanner) in kali container or host | + nuclei/sqlmap class | 24/24 per `env_inventory.sh` | ENV | S |
| G-4 | Policy wiring (P1) | `engagement-open-v0.json` unwired; action/capability checks exact-match; ScopeV0 no open mode (§5 audit) | loader + fnmatch on action/capability dims + scope open mode, **atomic** | same (D2 runs on it) | + per-engagement generated policies | CODE | M |
| G-5 | Test regime | weld tests assert DENY; no restrictive-still-denies proof | flip ~40 sites + `test_restrictive_policy_still_denies` + kill-switch test | same | suite ≥621, floor ratchet | CODE | S–M |
| G-6 | Execution bodies | 10/10 deleted (§5 audit) | **2 restored**: W-01 `_run_command` + W-07/W-09 kali path | + W-10 sandbox `run_code`, W-14 agent exec | 10/10 + probes | CODE | S (per-item M) |
| G-7 | Capability layer | `exec/` has only `SafeProvingCapability`; no `exec/capabilities/` (F3 not started) | thin `ToolExecCapability` + PEP dispatch branch | + `KaliToolCapability`, `CodeExecCapability` | full 7-capability set + TP-01…09 wiring | CODE | M |
| G-8 | Candidate source | nothing proposes arsenal actions (L4 dormant) | deterministic scripted candidate (recon plan: nmap → fingerprint) | live Student/Planner proposals | technique catalog + patterns | CODE | S |
| G-9 | Autonomy bounds | `max_iterations=1`, approvals on, filter Tier-1/2, falsification blocking (L5) | n/a (single action) | driver script; approvals→open; filter short-circuit; falsification→advisory; **replan trigger re-base** (F7 note: open policy deletes `DenialClass.PERSISTENT`, the only current trigger — `stages.py:756/796`) | + continuous loop, target rotation | CODE | M |
| G-10 | LLM providers | no endpoint, providers dead (W-12 class) | not needed | live endpoint verified by probe script | dual-key failover (probe exists in forge) | ENV/CODE | S (D2) |
| G-11 | Cognition F4/F5/F6 | absent; `brain/contracts/` is an unwired spec | not needed | optional (hypothesis engine improves D2 narrative) | Target Model, 3 graphs, hypothesis engine, DAG planner | CODE | — (P: L+M+L) |
| G-12 | Evidence/eval integrity | pytest rewrites 14 arena dirs (TI-1); holdout dataset absent (TI-2) | TI-1 fixed (tests → `tmp_path`); TI-2 decision recorded | same | recovered dataset or amended manifest | CODE/DATA | S |
| G-13 | Import health | `PatchSandbox` shadow breaks 14 modules incl. all `api/` | fixed (needed for API tools route) | same | + redis/dns deps, `phishing` import side effect | CODE | S |
| G-14 | Secrets | 5 `nvapi-` keys in 13 files (S-1) | rotated + purged (hard gate before any endpoint use) | same | history purge if repo ever goes public | HYG | S |
| G-15 | Docs truth | README false claims (arena.yml, holdout file, 121 tests); dead paths in `launch_pilot.sh`, `forge/sweep_imports.py` | README D1 section truthful; floors updated | + D2 runbook | full sync (v2 F9) | DOC | S |
| G-16 | Service bodies #9–10 | cloak/mhddos mains deleted; source dirs exist in-repo | out of scope for D1/D2 | optional (Tor egress demo) | restored if stealth posture wanted | CODE | 0 (de-scoped) |

---

## 3. MILESTONE PLAN

Sequencing with hard gates. Sizes: M0 ≈ 1–2 sessions, M1 ≈ 1–2, M2 ≈ 2–3, M3 ≈ 2–3,
M4 ≈ 3–5, M5 ≈ 5+, M6 ≈ 2–3 (environment-dependent at M2/M6).

### M0 — Clean Floor (hygiene; no behavior change)
Work: fix `orchestrator.sandbox` shadow (fold package into module or re-export
`PatchSandbox`) [G-13]; test isolation for arena writers + quarantine the 14 mutated
dirs [G-12]; rotate & purge `nvapi-` keys [G-14]; `phishing/main.py` import-time mkdir
guard [HYG]; commit governance docs (v1 banner, INDEX, `.zcodeignore`, blueprint set);
README truth pass for current state [G-15]; ignore runtime DBs (`data/`,
`src/orchestrator/data/*.db`).
**Gate (all)**: suite 621 green; import sweep — `api.*`, `agents.*`, `bridge.*` resolve;
second suite run leaves `arena/results/raw` byte-identical; zero `nvapi-` hits repo-wide.

### M1 — Runnable Environment
Work: venv 3.12 + `requirements.txt` + `python-dotenv` [G-1]; `docker compose -f
configs/docker-compose.yml up -d dvwa kali-tools` and fix what breaks (compose untested
since restructure; expect path/env fixes) [G-2]; nmap present in kali container
(`env_inventory.sh` inside container or against it) [G-3]; TI-2 decision recorded
(recover `rbs_v4_holdout.jsonl` from origin/backup, else amend manifest to
"unverifiable-in-repo") [G-12]; write `scripts/smoke_lab.sh` (DVWA answers 302,
kali `/health` 200).
**Gate**: smoke script green from cold start; suite still 621 on venv 3.12.

### M2 — D1: Governed Action demo (= F1 + minimal F2/F3)
Work, as **one atomic change** (v2 risk: wiring the policy without the test flip, or vice
versa, leaves the suite red or the policy inert):
1. Broker: fnmatch on `is_action_type_allowed`/`is_capability_allowed` (mirror
   `_target_matches`) [G-4].
2. `runtime/policy.py`: loader for `engagement-open-v0.json` (bootstrap loader kept) [G-4].
3. ScopeV0 open mode / generated allow-all mission scope [G-4].
4. Test regime flip + `test_restrictive_policy_still_denies` + kill-switch test
   (`bootstrap-v0` swap → DENY) [G-5].
5. Restore W-01 `chains/tool_registry.py::_run_command` (asyncio subprocess; recover from
   history per roadmap pattern) + W-07 `kali_tools_client` / W-09 `kali-tools /run` body
   [G-6].
6. `exec/capabilities/tool_exec.py` — broker-mediated ToolExecCapability + PEP dispatch
   branch in `stages.py` [G-7].
7. Deterministic recon candidate generator (nmap → service fingerprint) [G-8].
8. `scripts/run_demo_d1.sh` + transcript renderer (decision IDs, receipt hashes).
**Gate (D1 checklist §8)**: cold-start single command; live nmap output in receipt;
restrictive control denies; kill-switch denies; suite green (≥621, floor ratcheted);
guardrails untouched.

### M3 — D2: Autonomous Episode demo (= F7 subset)
Work: `.env` live endpoint + provider probe [G-10]; `scripts/run_autonomous.py` driver
(explicit `max_iterations`/`action_cap` params — defaults stay 1) [G-9]; approvals →
`(True, False)` under open policy; command-filter short-circuit behind open flag;
falsification → advisory (log verdict, don't withhold); **replan trigger re-based** to
reconciliation-invalid / evidence-divergence (else the planner never re-plans under open
policy — F7 note in v2 §6); evidence/demo/ recording.
**Gate (D2 checklist)**: ≥3-iteration episode, zero approvals, zero `WeldNotAuthorized`,
receipt for every action, honest terminal state; rerun reproducible from cold start.

### M4 — Arsenal completion (= F2 done + F3)
Remaining bodies W-08 (sliver/beacon/implant), W-10 sandbox `run_code`, W-14 agent exec;
cloak/mhddos only if stealth demo wanted [G-16]; full capability set + TP-01…09 pattern
wiring; toolchain to 24/24 (or documented subset); failure-injection probe (kill kali
mid-run → agent retries).
**Gate**: v2 F2 (per-file probe + receipt) and F3 gates (recon→queue→exec receipts;
restrictive control denies).

### M5 — Cognition (= F4 + F5 + F6, the v2.1 differentiators)
Target Model + complexity model + three graphs (F4); hypothesis engine with honest
REFUSE/UNAUTHORIZED/UNSUPPORTED outcomes and info-gain selection (F5); hierarchical DAG
planner on §3 graphs (F6). `brain/contracts/` is the spec anchor — wire it or prune it;
don't leave it half-claimed.
**Gate**: v2 F4/F5/F6 gates (nine-question model per node; proven + refused hypotheses
both receipted; planner branches from model not tool list).

### M6 — E2E, scale, ops (= F8 + F9, product state)
Full-chain scenarios (exploit chain, C2, phish/harvest); horizontal/vertical scale
ladders → DoD-7 invariance; crash-restart + evidence rotation + resume-from-checkpoint;
README/state sync; final security pass (API exposure decision, history purge if public).
**Gate**: v2 DoD 1–5 + DoD-7; continuous supervised run incl. interruption-resume.

### Critical path
```
M0 ─► M1 ─► M2 (D1) ─► M3 (D2) ─► M4 ─► M6 (P)
                     └───────────► M5 ──┘   (M4 ∥ M5 after D2)
```
G-14 (keys) is a hard gate before M3 (endpoint use). G-13 (import fix) blocks M2's API
route variant — do it in M0 regardless. M2 is the pivotal milestone: everything after it
is repetition and depth on a proven chain.

---

## 4. DE-SCOPING OPTIONS (fastest honest D1)

If the goal is "demo this week": 
1. Host toolchain instead of containers (`apt nmap` on host, target = a second localhost
   port) — drops G-2/G-3 container work; target then is "authorized localhost" which the
   policy model already handles (`allowed_targets: ["*"]`).
2. Single restored body (W-01 only, direct local exec) — skips W-07/W-09.
3. Scripted candidate only — no LLM anywhere in D1.
4. Skip C2/phish/cloak entirely — they are D2+/P scope anyway.
Not de-scopable under any circumstances (they *are* the demo's claim): broker mediation,
weld gates, receipts, kill-switch reversibility, restrictive-policy denial proof.

---

## 5. WHAT "DONE" IS NOT

Per the audit: `engagement-open-v0.json` sitting in `policies/` is not "open policy
deployed" (it is a no-op artifact — audit §5); a green suite is not "restored"
(weld tests still assert DENY); containers existing is not "arena" (they were never up).
Every milestone gate above is phrased as an observable event, not a file's existence.

---

## 6. DEMO SCRIPTS (acceptance narratives)

**D1 (target ≤ M2 exit):**
1. `bash scripts/run_demo_d1.sh` (cold start: brings up dvwa + kali, loads open policy).
2. Screen shows: mission → scope ALLOW → broker `AUTHORIZED decision_id=…` (all 5
   dimensions) → PEP dispatch → nmap runs → open ports of the DVWA container listed.
3. Receipt printed: action_id, decision_id, output digest, artifact hash; stored in
   evidence store (queryable).
4. Operator flips `POLICY_PATH` to `bootstrap-v0` (or env var), re-runs: `DENIED —
   action type not in allowed list`, mapped to 403, no process spawned. Transcript
   archived under `evidence/demo/d1/<ts>/`.

**D2 (target ≤ M3 exit):** same cold start + `.env`; agent runs ≥3 iterations
unattended: scan → world model gains services → proposes fingerprint/next scan →
executes → concludes with a summary report of what it learned + evidence links; no
approval prompt at any point; optional kill mid-run → restart → resumes from durable
state (stretch: F9 preview).

---

## 7. RISK REGISTER (delta on v2 App. A)

| Risk | Mitigation |
|---|---|
| Compose stack bit-rotted since restructure (never validated) | M1 is exactly this validation, isolated before policy work |
| Test-regime flip ~40 sites larger than estimated | Count first in M2 step 0 (`grep -c WeldNotAuthorized tests/`); mechanical replace, machinery proof preserved |
| History recovery of W-01 body fails | Rewrite is ~30 lines of asyncio subprocess; spec is in the raise-message comment |
| Open-policy wiring accidentally weakens guardrails | Atomic M2 change + `test_restrictive_policy_still_denies` + INV-1/P2 guardrail suite must stay green; kill-switch test is a release gate, not a nice-to-have |
| Replan trigger loss under open policy (F7 note) | M3 gates on a proven non-denial replan before D2 is claimed |
| Demo day infra flake (docker pull, endpoint down) | D1 de-scope path (§4) is the fallback; record demo artifacts as primary evidence |

---

## 8. DEFINITION-OF-DONE CHECKLISTS

**D1**: ☐ single cold-start command ☐ dvwa+kali (or host toolchain) healthy ☐ broker
AUTHORIZED on record ☐ real nmap output in a persisted receipt ☐ restrictive policy
denies (test + live) ☐ kill-switch denies (test + live) ☐ suite ≥621 green ☐ guardrails
green ☐ README D1 section truthful ☐ transcript archived.

**D2**: ☐ D1 holds ☐ live LLM endpoint probe green ☐ ≥3 iterations unattended ☐ zero
approvals / zero WeldNotAuthorized ☐ receipt per action ☐ honest terminal state ☐
≥1 replan from non-denial trigger ☐ reproducible rerun ☐ artifacts under
`evidence/demo/d2/`.

**P (v2 DoD, abridged)**: ☐ 15/15 welds AUTHORIZED under open policy ☐ 10/10 bodies
restored + live probes ☐ suite green, INV-1/guardrails untouched ☐ cold-start
autonomous E2E, zero approvals ☐ continuous episode loop ☐ feeds enter as queued tasks
with provenance ☐ lab-range self-validation before "verified" ☐ self-red-team jobs ☐
measured improvement on held-out scenarios (external verdict) ☐ DoD-7 invariance on both
ladders ☐ ops hardening + truthful README.

---

## 9. IMMEDIATE NEXT ACTIONS (this week, in order)

1. M0 key rotation + purge (S-1/C-1) — unblocks endpoint config ethically.
2. M0 sandbox-shadow fix (one commit, restores 14 modules).
3. M0 test isolation for arena writers (stops ongoing data corruption).
4. M1 venv 3.12 + compose bring-up of `dvwa` + `kali-tools`.
5. M2 atomic policy-wiring PR skeleton (broker wildcards + loader + scope + test flip,
   behind a flag until the whole set lands).
