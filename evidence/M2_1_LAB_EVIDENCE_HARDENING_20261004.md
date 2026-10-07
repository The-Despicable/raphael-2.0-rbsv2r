# M2.1 LAB & EVIDENCE HARDENING — EVIDENCE PACKAGE — 2026-10-04

Task: RAPHAEL-M2.1-2026-10-04, branch `offensive-restore`, HEAD `e6a8c707e`
(unchanged; nothing committed). Bounded hardening: durable compose corrections,
loopback-by-default, durable kali import path, D1 revalidation, evidence
integrity. No architecture change, no authorization change, no D1 scope change,
no commits, no destructive docker operations.

---

## 1. Starting state

- Branch/HEAD: `offensive-restore` / `e6a8c707e614a1aa5468d5b93be324525513363f`
  (matches the expected starting assertion).
- Worktree: 65 tracked-modification/untracked entries at start (all M0/M1/M2
  work preserved); `.venv` = Python 3.12.15.
- Docker: compose v5.4.0; lab running from M2 (dvwa `Up`, kali-tools `Up`,
  dvwa-db `Up`, all loopback-bound via the M1 override); volumes
  `chimera_bootstrap_data` (unrelated, preserved) + `raphael-m1_dvwa-db-data`.
- `scripts/smoke_lab.sh`: PASS; `scripts/run_demo_d1.sh`: PASS (M2 run).
- Protected tree: identical to `evidence/arena_contamination_20261004/
  PRE_M0_SHA256SUMS.txt` (sha256 of the manifest itself, recorded for future
  verification: `d4630af3de835bb6ef3d0b36…`).

## 2. Compose configuration — before and after (exact)

**kali-tools build context + volumes** (the demonstrated breakage):
```yaml
# before                                   # after (M2.1)
build:
  context: ./src/kali-tools                context: ../src/kali-tools
volumes:
  - ./src/orchestrator:/raphael/orchestrator:ro
  - ./data:/raphael/data
```
→ after: `- ../src/orchestrator:/raphael/orchestrator:ro`, `- ../data:/raphael/data`.
Compose resolves relative paths against the compose file's own directory
(`configs/`), so root-level invocation required `../` prefixes.

**Port bindings (17 published ports total, all now loopback-only):**
```yaml
# before            # after (M2.1)
- "3800:3800"       - "127.0.0.1:3800:3800"     # kali-tools
- "4280:80"         - "127.0.0.1:4280:80"       # dvwa
# plus 15 further 0.0.0.0 bindings on non-lab services (c2-server, cai-service,
# caido, cloak-service, mhddos-service, neo4j ×2, phishing, raphael-api,
# recon-pipeline, sliver-server ×2, sword, tor-proxy ×2) — all prefixed with
# 127.0.0.1 so the WHOLE base file is safe-by-default (M2.1-B: "the effective
# configuration must fail the hardening check if a service unintentionally
# binds to 0.0.0.0"). Container-to-container traffic unchanged; no new ports.
```

**env_file declarations (8 services)** — a third hidden dependency surfaced by
this milestone: with project-directory = `configs/`, compose hard-failed
rendering the model (`env file …/configs/.env not found`) because 8 non-lab
services declare `env_file: .env`. Corrected to compose-file-relative and
optional:
```yaml
# before           # after (M2.1)
env_file: .env     env_file:
                       - path: ../.env
                         required: false
```
Behavior preserved when the repo-root `.env` exists (it does — M1 placeholder
file); no hard failure when absent. The lab services (kali-tools, dvwa,
dvwa-db) never used env_file.

**Remaining `0.0.0.0` strings in the rendered config: 3** — all inside
`command` arrays of c2-server / cloak-service / recon-pipeline: container-
INTERNAL bind addresses (required for a process to listen on its container
interface), not host publications. Host-side published ports: **0 occurrences
of 0.0.0.0** in the fully rendered configuration (verified programmatically:
`non-loopback published ports: NONE`).

## 3. Build-context verification

Rendered from the repository root with the plain documented invocation
(no `--project-directory`, no override):
```
kali-tools | context: /home/yaser/external-audits/raphael-2/src/kali-tools
             ports: [('127.0.0.1','3800',3800)]
             volumes: [repo src/orchestrator, repo data]
dvwa       | ports: [('127.0.0.1','4280',80)]
dvwa-db    | ports: [] (unpublished) | volume: dvwa-db-data (named)
```
Expected Dockerfiles/sources exist at the resolved paths
(`src/kali-tools/Dockerfile` present; context remains as narrow as before).
**Known deferred defect (same class, not demonstrated, not M1-lab):** the other
services' build contexts still use `./src/…` and will need the same `../`
correction when the full stack is ever brought up (recorded in
`evidence/DEFECT_REGISTER.md` related-classification note).

## 4. kali-tools import path — authoritative fix (M2.1-C)

- **Authoritative fix: `src/kali-tools/Dockerfile`** — added
  `ENV PYTHONPATH=/raphael` (with root-cause comment) before the CMD.
  Root cause: the compose contract mounts the single orchestrator source at
  `/raphael/orchestrator:ro`, but the image runs `/app/server.py`, whose own
  `sys.path` insert resolves to `/` → `ModuleNotFoundError: No module named
  'orchestrator'` → crash loop (observed in M1).
- No duplicate orchestrator copy is baked into the image (mount-only, read-only);
  no broader sys.path changes; health behavior unchanged.
- **Verification with the ordinary service definition only** (base compose, no
  `--project-directory`, no override): `up -d --build dvwa kali-tools` →
  kali-tools recreated and `Up`; `docker exec kali-tools env` shows
  `PYTHONPATH=/raphael` **from the image itself**; `/health` → HTTP 200
  `{"status":"ok","tools":1015}`; dvwa → HTTP 302.
- **M1 override (`configs/docker-compose.m1-loopback.yml`) disposition:** kept,
  now documented in-file as **redundant-but-harmless** — merging it re-applies
  identical 127.0.0.1 bindings and the same PYTHONPATH value; rendered merge
  introduces no exposure change. Do not extend it.

## 5. Service health and smoke test (post-hardening)

`scripts/smoke_lab.sh` (updated to the corrected default invocation
`docker compose -p raphael-m1 -f configs/docker-compose.yml …`): all 8 checks
PASS, exit 0 (daemon, three services running, no 0.0.0.0 bindings, dvwa 302,
kali /health 200 + status=ok, nmap 7.99 in-container).

## 6. D1 revalidation without authorization changes (M2.1-D)

`bash scripts/run_demo_d1.sh` → exit 0. Fresh transcript:
`evidence/demo/d1/20261004T172731Z/` (prior runs untouched):

| Phase | Result |
|---|---|
| Positive | decision `allow`, decision_id/action_id `44b5079f4ada9f29`, status `SUCCEEDED`, `service_confirmed=true`, artifact sha256 `7b7ec9ecbb046991…` digest-verified |
| Restrictive control (`bootstrap-v0`) | DENIED at broker stage, 0 spawns, 0 capability invocations |
| Kill switch (decision-source swap) | DENIED at broker stage, 0 spawns |
| Wrong target (`example.invalid`) | DENIED at broker stage |

D1 files (`engagement-d1-v1.json`, `runtime/policy.py` D1 loader,
`exec/capabilities/d1_lab_probe.py`, demo scripts) were **not modified** in
M2.1 — the policy still authorizes exactly one action/capability/target.
`engagement-open-v0.json` remains unwired and inactive.

## 7. Receipt, evidence-store, and artifact integrity

The fresh D1 run's evidence store contains the linked `execution_result`
(decision allow, action ACT-D1-PROBE-0001) and `artifact` records
(sha256 + execution_ref parentage); the artifact digest was recomputed from the
stored bytes and matched in-run (the driver exits 1 on any mismatch). M2's
original archived runs (`20261004T163946Z`, `…T164000Z`, `…T164502Z`) remain
byte-intact; every new demo uses a fresh timestamped directory.

## 8. Test results (M2.1-F)

- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/ --no-header -q`
- Interpreter: Python **3.12.15** (repository `.venv`; uv-managed)
- Result: **660 collected — 660 passed / 0 failed / 0 skipped / 0 xfailed — 24.98 s**
  (identical counts to the M2 baseline: no test added, removed, weakened, or
  suppressed in M2.1).

## 9. Historical-data integrity (M2.1-E)

- Baseline manifest `PRE_M0_SHA256SUMS.txt` exists and is unmodified
  (sha256 prefix `d4630af3de835bb6ef3d0b36` recorded above for future checks).
- Pre-suite comparison: identical; post-suite: **identical** (7th/8th
  consecutive byte-identical comparisons).
- Test-isolation fixture (`tests/conftest.py` RESULTS_BASE redirect) confirmed
  active (it is imported by the suite; the identical hashes confirm it).
- Smoke/demo output paths write only under `evidence/demo/d1/<timestamp>/` — no
  collision with `arena/results/raw` or `evaluations/campaign/`. The 14
  potentially contaminated directories remain recorded as such; nothing
  regenerated.

## 10. `sword.phase_2_exploit` disposition (M2.1-G)

Cause established precisely: the sword service imports and awaits
`validate_exploit_results(raw_results, target)` — an **async results-validator**
— while `orchestrator/validation/exploit_validator.py` exposes only the **sync
config-validator** `validate_exploit(exploit_config, target)`. The signatures,
sync/async shape, and input semantics differ; no behavior-preserving interface
correction exists without designing the missing results-validation semantics.
**Formally deferred** as **DR-001** in the new `evidence/DEFECT_REGISTER.md`
(owner: sword workstream, gap-plan M4/M6). Impact unchanged: 1 of the 19
remaining fresh-process import failures; no canonical Runtime path imports it.
No exploit functionality implemented, restored, or fabricated.

## 11. Credential rotation status

**`BLOCKED — OPERATOR ACTION REQUIRED`.** No provider requests, no credential
reads, no secrets printed anywhere in this milestone. The M0 security gate
remains NOT closed. D1/M2.1 evidence contains no credential-bearing files.

## 12. Criterion-by-criterion gate

| Criterion | Verdict | Proof |
|---|---|---|
| Base compose contexts resolve at root-level documented invocation | **PASS** | §3 rendered paths |
| Default exposure loopback-only without override | **PASS** | §2 — 17/17 published ports 127.0.0.1; rendered config has zero host-side 0.0.0.0 |
| kali-tools imports intended orchestrator source, starts normally | **PASS** | §4 — image-level ENV, base-only recreation healthy |
| Service health (dvwa, db, kali) | **PASS** | §5 smoke 8/8 PASS |
| D1 positive path | **PASS** | §6 — fresh SUCCEEDED run |
| Restrictive control | **PASS** | §6 — DENIED, 0 spawns |
| Kill switch | **PASS** | §6 — DENIED, 0 spawns |
| Wrong-target control | **PASS** | §6 — DENIED pre-process |
| Receipt/artifact integrity | **PASS** | §7 — linkage + digest verified; archives intact |
| Guardrails pass unweakened | **PASS** | §8 — 660/660, zero test changes |
| Historical evidence byte-identical | **PASS** | §9 |
| Worktree integrity | **PASS** | §14 — pre-existing work preserved; changes scoped to compose/Dockerfile/scripts/evidence |
| Documentation uses corrected safe default | **PASS** | scripts updated; README invocation now valid as written |
| Credential safety | **PASS** (M2.1 scope) | §11 — rotation itself still operator-blocked |

**M2.1 gate: PASS** (with the standing condition that the M0 security gate
remains open and operator-owned).

## 13. File-by-file diff summary (M2.1 only)

| File | Change |
|---|---|
| `configs/docker-compose.yml` | kali-tools context/volumes → `../`-relative; 17 published ports → 127.0.0.1; 8 × `env_file` → optional `../.env` (commented) |
| `src/kali-tools/Dockerfile` | `ENV PYTHONPATH=/raphael` + root-cause comment |
| `scripts/smoke_lab.sh`, `scripts/run_demo_d1.sh` | documented invocation updated to the corrected default (no `--project-directory`, no override) |
| `configs/docker-compose.m1-loopback.yml` | M2.1 disposition note appended (redundant-but-harmless, kept) |
| `evidence/DEFECT_REGISTER.md` | new — DR-001 sword validator drift, formally deferred |
| `evidence/M2_1_LAB_EVIDENCE_HARDENING_20261004.md` | this package |
| New evidence dirs | `evidence/demo/d1/20261004T172731Z/` (fresh timestamped D1 run) |

Preserved untouched: all 65 pre-existing M0/M1/M2 worktree entries, the D1
implementation files, both policy artifacts' roles, weld gates, protected
evidence trees, unrelated docker resources. Nothing committed.

## 14. Remaining blockers and next milestone

- **Rotation (operator)** → M0 security gate stays open; M3 endpoint config
  waits on it.
- **Holdout dataset** recovery decision (operator) — `unverifiable-in-repo`.
- **Commit authorization** — the whole worktree (M0→M2.1) is uncommitted.
- **DR-001** + 18 structural import failures — deferred (defect register).
- **Recommended next milestone:** M3 (Autonomous Episode, D2), gated on operator
  rotation confirmation + live LLM endpoint decision. Not started; awaiting
  review of this package.
