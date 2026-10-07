# M1 RUNNABLE ENVIRONMENT — EVIDENCE PACKAGE — 2026-10-04

Task: RAPHAEL-M1-2026-10-04, branch `offensive-restore`, per
`RAPHAEL_GAP_ANALYSIS_IMPROVEMENT_PLAN_20261004.md` §M1. Scope held to environment
provisioning and local-lab validation: no policy wiring, no capability restoration,
no autonomous operation, no commits, no destructive docker operations, no external
targets, no authenticated provider requests.

---

## 1. Starting state

| Item | Observed |
|---|---|
| Branch / HEAD | `offensive-restore` / `e6a8c707e614a1aa5468d5b93be324525513363f` (unchanged) |
| Worktree at start | 52 modified/untracked entries — all M0 + pre-existing changes preserved; nothing reverted |
| Python interpreters | system `python3` = 3.14.4 (pin-violating); `~/.local/bin/python3.11` = 3.11.16 (uv-managed, user-space); **no 3.12 preinstalled** |
| Docker | daemon 29.7.2 running; **0 containers**; 1 unrelated pre-existing volume (`chimera_bootstrap_data` — preserved) |
| Disk | 921 GB free |
| Dependency manifests | `requirements.txt` (authoritative, consolidated; "Python >=3.11,<3.13 frozen"), `configs/requirements.txt` (legacy service copy — not used) |
| `.env` | absent at start (only `.env.example`, `.env.tier2.template`) |
| Holdout dataset | absent; never committed (per M0 records) |

Discrepancy recorded (task order vs reality): the order's interpreter gate says
"Python version = 3.12.x" while the repository's own frozen constraint is
`>=3.11,<3.13` — `python3.11.16` was already available in user space as a fallback.
The discrepancy was resolved toward the stricter reading (3.12) without any
privileged or host-level change — see §2.

## 2. Python interpreter and virtual-environment evidence (M1-A)

- Python 3.12 was not installed. Obtained it **without privileged or host-level
  changes**: installed the `uv` binary in user space (`~/.local/bin/uv`, official
  installer — the same tool family that already managed this host's 3.11) and ran
  `uv python install 3.12` → `cpython-3.12.15` under `~/.local/share/uv/python/`.
- `uv venv --python 3.12 .venv` → repository-local `.venv`.
- Interpreter gate:

```text
Python version      = 3.12.15          (satisfies >=3.11,<3.13)
Active interpreter  = /home/yaser/external-audits/raphael-2/.venv/bin/python (sys.prefix verified)
Declared deps       = installed (§3)
```

- Fallback path (not needed): `python3.11.16` venv would have satisfied the frozen
  pin; recorded as the no-new-tool alternative.

## 3. Dependency manifest and installation summary

- Authoritative manifest: `requirements.txt` (root). **One M1-scoped, evidence-
  supported correction made:** added `python-dotenv` (undeclared; required by the
  restoration roadmap P0.3 and gap-analysis M1-A for `.env` loading). Comment in the
  manifest records the rationale. No version constraints loosened; no dependencies
  replaced.
- Install command: `~/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt`
  — exit 0. Full resolver snapshot: `evidence/M1_python_312_package_versions.txt`
  (117 packages). Key versions: torch 2.14.1, transformers 5.18.0, fastapi 0.142.2,
  pydantic 2.13.5, python-multipart 0.0.32, redis 8.1.0, fakeredis 2.39.0,
  dnspython 2.8.0, python-dotenv 1.2.4, uvicorn 0.54.0, httpx 0.28.1, pytest 9.1.1,
  pytest-asyncio 1.4.0, sqlalchemy 2.1.3, aiohttp 3.14.3, docker 7.2.0, paramiko 5.0.0,
  mcp 2.3.0, neo4j 6.3.1, numpy 2.5.3, pandas 3.0.6.
- Observation (not changed): the manifest's constraints are all `>=` lower bounds, so
  the resolver selected current-newest versions (e.g. pandas 3.x). Reproducibility
  would benefit from an upper-bound pin set — left to a later, explicitly authorized
  change.

## 4. Safe local configuration (M1-B)

- `.env` created with **placeholders only** (no real credentials; zero `nvapi-`
  strings): `MODEL_ID=PLACEHOLDER_SET_AFTER_KEY_ROTATION`, commented
  `# OPENAI_API_KEY=PLACEHOLDER_SET_AFTER_KEY_ROTATION`, local `API_KEY` placeholder,
  blank `TOR_PROXY`. `.env` is git-ignored (verified via `git check-ignore`).
- No historic credentials copied from source, history, manifests, or reports. No
  authenticated external model requests were made. The live LLM endpoint remains
  **unset** — prerequisite for M3, not M1; recorded as an explicit follow-up gated on
  operator key rotation.

## 5. Docker local-lab bring-up (M1-C)

**Two repository-config defects were surfaced by bring-up (recorded as
discrepancies; worked around without modifying `configs/docker-compose.yml` or any
Dockerfile):**

1. **Relative build contexts resolve against `configs/`** (the compose file's own
   directory), so the README/roadmap invocation from the repo root fails with
   `unable to prepare context: …/configs/src/kali-tools not found`. Workaround:
   invoke with `--project-directory .` (contexts then resolve to repo root).
2. **kali-tools crash-loop:** the Dockerfile copies `server.py` to `/app`, whose
   `sys.path` insert resolves to `/`, but the compose mount places `orchestrator`
   at `/raphael/orchestrator` → `ModuleNotFoundError: No module named 'orchestrator'`.
   Fix via the M1 override file (no Dockerfile change): `PYTHONPATH: /raphael` for
   the kali-tools service.
3. **Boundary defect:** the base compose publishes `4280:80` and `3800:3800` on
   `0.0.0.0`. New file `configs/docker-compose.m1-loopback.yml` re-binds both to
   `127.0.0.1` (`!override` port blocks) and is part of every invocation.

**Cold-start reproduction (exact):**

```bash
docker compose --project-directory . -p raphael-m1 \
  -f configs/docker-compose.yml -f configs/docker-compose.m1-loopback.yml \
  up -d --build dvwa kali-tools
```

**Resulting state (verified):**

| Container | State | Ports |
|---|---|---|
| dvwa | Up | **127.0.0.1:**4280→80 |
| kali-tools | Up | **127.0.0.1:**3800→3800 |
| dvwa-db | Up | 3306 internal only (no host publish) |

- Health: `curl http://127.0.0.1:4280/` → **HTTP 302 → /login.php** (matches the
  documented unauthenticated DVWA behavior); `curl http://127.0.0.1:3800/health` →
  **HTTP 200** `{"status":"ok","tools":1015}` (contract `src/kali-tools/server.py:55`).
- New volume `raphael-m1_dvwa-db-data` created by compose (expected; no existing
  volume touched). Unrelated pre-existing volume `chimera_bootstrap_data` preserved.
- No scans, no offensive execution path, no policy changes.

## 6. Toolchain inventory (M1-D)

- **Host** (`bash scripts/env_inventory.sh`): **1/24** (`httpx`) — unchanged from M0.
- **kali-tools container** (`docker exec -i kali-tools bash -s < scripts/env_inventory.sh`):
  **14/24 present** — nmap 7.99, nuclei v3.11.0, whatweb 0.6.4, ffuf, gobuster 3.8.2,
  sqlmap 1.10.9, nikto, msfconsole/msfvenom, socat, hashcat v7.1.2, john, hydra v9.7,
  httpx. Missing 10: subfinder, puredns, alterx, amass, searchsploit, certipy,
  sliver-server, mythic-cli, havoc-teamserver, chisel. Also: nuclei-templates ABSENT,
  in-container docker ABSENT (flagged by the inventory script itself for the E3 range).
- **M1-required tool: nmap — PRESENT and versioned inside the intended lab execution
  environment** (`kali-tools`, matching its service contract). Full inventory recorded
  above as planning evidence for M2+/M4; **no broad arsenal installed during M1**.

## 7. Fresh-process import sweep (M1-E)

Methodology per M0 review: one fresh subprocess per module (380 subprocesses),
`.venv/bin/python` 3.12.15, `PYTHONPATH=src`, `importlib.import_module`.

**Result: 361 OK / 19 FAIL** (was 339/41 under 3.14 pre-M1). **Every dependency-class
failure resolved:**

| Class | Pre-M1 (fresh, 3.14) | Post-M1 (fresh, 3.12.15) |
|---|---|---|
| `python-multipart` (8 × `orchestrator.api.*`) | 8 | **0** |
| `redis` | 11 | **0** |
| `dns`/dnspython | 3 | **0** |
| Structural: arena `d6c_holdout_runner` cwd-based | 10 | 10 |
| Structural: `mcp-hub.*` internal naming | 3 | 3 |
| Structural: `config` vs `configs/` | 2 | 2 |
| Structural: `case_store` (recon-pipeline) | 3 | 3 |
| Code drift: `sword.phase_2_exploit` | 1 | 1 |
| **Total** | **41** | **19** |

The 19 remaining failures are exactly the structural set (dash-package service-local
naming and by-design cwd-based arena runners) plus the separately documented
`sword.phase_2_exploit` validator drift — **not** dependency failures, not M1 scope.
Full per-module classification retained from the M0 reassessment; error classes
unchanged except the resolved dependency classes. No errors suppressed.

## 8. Full test suite (M1-F)

- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/ --no-header -q`
- Interpreter: **Python 3.12.15 (repository `.venv`)**
- Result: **637 collected — 637 passed / 0 failed / 0 skipped / 0 xfailed — 41.13 s**
- Skip accounting: **0 skips.** The 5 M0-era skips
  (`test_api_modules_import_with_multipart_present[*]`) converted to real passes once
  `python-multipart` was installed — the exact conversion the skip design anticipated.
- M0 regression and guardrail tests (`test_m0_clean_floor.py`,
  `test_p2_guardrail_*.py`, `test_am4_weld_gates.py`) all pass within the run.
- Protected evidence safety: pre-suite hash comparison — identical to the M0 baseline;
  post-suite — identical (4th and 5th consecutive byte-identical comparisons;
  baseline untouched). No contamination regression.

## 9. Historical-data integrity

- Baseline: `evidence/arena_contamination_20261004/PRE_M0_SHA256SUMS.txt` (52,022
  files) — unchanged, not modified.
- Comparisons this milestone: pre-suite identical, post-suite identical.
- Contamination record and 14 quarantined directories preserved untouched.

## 10. Holdout-dataset recovery decision (M1-G)

Recorded SHA-256 (from `evaluations/campaign/rbs_v4_reproducibility_manifest.json`):
`2bf614f8eafa02533bfb522fa50ac1f1827acb0951eeeb42eff6b845a8e586b4`.

Bounded recovery attempts (all non-destructive; no branch change, no reset):

1. `git log --all -- evaluations/campaign/rbs_v4_holdout.jsonl` — no commits touch the
   path.
2. `git rev-list --objects --all` — filename absent from every tracked object.
3. `git fsck --dangling` — 1 dangling blob, <100 KB (not the dataset). Not a shallow
   clone; 72,714 packed objects searched by name.
4. `git ls-remote origin` — single ref `main`.
5. `git fetch --depth=1 origin main` (creates `FETCH_HEAD`; no branch/ref change) —
   the file is **absent from origin/main's tree**. origin/main does carry the
   campaign's **per-run raw directories** (`evaluations/campaign/holdout_runs/raw/
   abl_*_holdout/`, `dev_runs/raw/…`) and unrelated jsonl artifacts — but not the
   aggregated dataset.

**Conclusion: `unverifiable-in-repo` stands.** Reconstruction from the raw run
directories is explicitly forbidden by the task order and was not attempted; no data
fabricated. Noted discrepancy for the record: the README says "1,200 rows" while
`rbs_v4_holdout_integrity_gate.json` records `total_rows_expected: 3240` — unresolved
documentation question, irrelevant to the absence itself. (Also noted: the
`evaluations/campaign/*.jsonl` ignore rule predates the dataset and would block re-
adding it; amending that rule requires the operator decision already flagged in M0.)

## 11. Smoke test (M1-H)

`scripts/smoke_lab.sh` (new) — infrastructure-only checks: docker daemon; the three
services running; loopback-only exposure (fails on any `0.0.0.0` binding); DVWA
HTTP 302; kali `/health` HTTP 200 + `status=ok`; nmap inside the container. Expecta-
tions verified against the actual implementations (`server.py:55` returns
`{"status":"ok","tools":N}`; DVWA 302 observed live) — no false expectation hardcoded.
No offensive path, no scans, no external contact.

| Run | Result | Exit |
|---|---|---|
| Healthy lab | all PASS → `SMOKE RESULT: PASS` | **0** |
| `docker stop kali-tools` (negative path) | FAIL lines → `SMOKE RESULT: FAIL` | **1** |
| `docker start kali-tools` (restored) | all PASS → `SMOKE RESULT: PASS` | **0** |

Invocation + prerequisites documented in the script header. One script bug found and
fixed during validation (awk substring match counted `dvwa-db` as `dvwa`).

## 12. Credential status (operator-owned)

- Working tree: clean (M0-C). `.env` placeholders only; zero credential literals in
  any new M1 artifact (`configs/docker-compose.m1-loopback.yml`,
  `scripts/smoke_lab.sh`, evidence files — scanned).
- No unrotated keys used; **no authenticated provider requests performed**.
- **Provider-side rotation: `BLOCKED — OPERATOR ACTION REQUIRED`** (revoke → replace →
  env-only storage → safe validation → record fingerprints). **The M0 security gate
  remains NOT closed.**

## 13. Acceptance matrix

| Criterion | Verdict | Evidence |
|---|---|---|
| Python environment (3.12 venv, pin satisfied) | **PASS** | §2 — 3.12.15, repo `.venv`, frozen pin satisfied |
| Dependencies installed + version record | **PASS** | §3 — exit 0 install; `evidence/M1_python_312_package_versions.txt`; dotenv correction documented |
| Lab services start + validated health checks | **PASS** | §5 — dvwa 302, kali /health 200, dvwa-db up; 2 compose defects fixed via documented override; cold-start command recorded |
| Local toolchain detected + versioned | **PASS** | §6 — nmap 7.99 in kali-tools; host 1/24, container 14/24 recorded |
| Import verification (fresh-process, M1-targeted imports resolved) | **PASS** | §7 — 361/380; all 22 dependency failures resolved; 19 structural/drift classified separately |
| Test suite, no unexplained failures | **PASS** | §8 — 637/637/0/0 on 3.12.15; skip conversion explained |
| Historical evidence hashes unchanged | **PASS** | §9 — identical pre/post-suite |
| Dataset recovered+verified OR recovery failure documented | **PASS** (documented-failure branch) | §10 — `unverifiable-in-repo`, attempts enumerated |
| Smoke script reproducible, fails on unhealthy services | **PASS** | §11 — PASS/FAIL/PASS cycle with exit codes 0/1/0 |
| Credential safety (no exposure, rotation status disclosed) | **PASS** (M1 scope) | §12 — but rotation itself `BLOCKED — OPERATOR ACTION REQUIRED`; M0 security gate not closed |
| Worktree integrity (M0 + pre-existing preserved; no unrelated changes) | **PASS** | §14 — all 52 pre-existing entries untouched; 5 new M1 artifacts enumerated |

**M1 gate: PASS** — with the explicit, standing caveat that **the M0 security gate
(rotation) remains open and operator-owned**, and that M2 authorization must not be
treated as automatic (task-order rule).

## 14. Diff summary

New (untracked) M1 artifacts:
- `.venv/` (git-ignored)
- `.env` (git-ignored, placeholders only)
- `configs/docker-compose.m1-loopback.yml` (loopback re-binding + kali PYTHONPATH fix)
- `scripts/smoke_lab.sh`
- `evidence/M1_python_312_package_versions.txt`
- `evidence/M1_RUNNABLE_ENVIRONMENT_20261004.md` (this file)

Modified (tracked):
- `requirements.txt` — one evidenced addition (`python-dotenv`)

Preserved untouched: all 52 M0/pre-existing worktree entries (M0 code changes, tests,
conftest, governance amendments, contamination + credential evidence, untracked
roadmaps/blueprints). Docker: 3 lab containers running (loopback-only), 1 new named
volume; no existing volumes/containers altered; nothing pruned. Git: no commits; one
depth-1 `fetch` of `origin main` recorded (FETCH_HEAD only).

## 15. Remaining work, risk, and owners

| Item | Risk | Owner |
|---|---|---|
| Key rotation + safe validation (M0 security gate) | compromised keys usable until rotated | **Operator** |
| Live LLM endpoint configuration (post-rotation) | M3 autonomy inert without it | Operator provides; engineer configures — M3 |
| Holdout dataset recovery from non-local backups | reproducibility manifest unverifiable | Operator decision; engineer executes |
| `requirements.txt` upper bounds for reproducibility | resolver drift between environments | Engineer — needs authorization (manifest change beyond M1's single correction) |
| 19 structural import failures + sword drift | none for M0–M3 critical path | Engineer — defect tickets, M4+ |
| Compose base-file defects (context resolution, 0.0.0.0 publish, kali import path) | cold-start fails if invoked per README without `--project-directory`; wider exposure; kali crash-loop | Engineer — propose minimal fixes to `configs/docker-compose.yml`/Dockerfile for operator approval (M1 deliberately did not modify them) |
| Lab lifecycle | containers run `restart: unless-stopped` | Operator decides whether to keep the lab up between milestones |

## 16. Recommendation for the next task

**M2 — Governed-Action demo (gap plan §3)**: the atomic policy-wiring milestone
(broker wildcards + open-policy loader + ScopeV0 open mode + test-regime flip +
restrictive-still-denies proof + kill-switch test), then W-01 body restoration and the
`exec/capabilities` PEP branch. Its lab prerequisite now exists (dvwa + kali-tools
healthy on loopback; nmap 7.99 available in-container). Not started; awaiting operator
review of this evidence package and explicit M2 authorization.
