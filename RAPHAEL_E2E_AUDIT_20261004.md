# END-TO-END AUDIT — raphael-2 (branch `offensive-restore`) — 2026-10-04

**Scope**: Full E2E audit of the worktree at HEAD `e6a8c707e` (baseline "P0 snapshot
before offensive restoration") + dirty state, per the audit convention established by
`forge/AUDIT_REPORT_20260808.md` and the 2026-09-30 audit cited in
`RAPHAEL_ARCHITECTURE_ROADMAP_v2.md`. Method: read-only inspection, full test-suite run,
one read-only inventory script (`scripts/env_inventory.sh`), import-map sweep. **No
offensive capability was executed, restored, or wired during this audit.** Secret values
are deliberately redacted (locations only).

---

## 1. EXECUTIVE VERDICT

| Dimension | Status | Verdict |
|---|---|---|
| Test suite (`PYTHONPATH=src pytest tests/ -q`) | **621 passed / 0 failed / 0 skipped, 30.3s** | ✅ GREEN — roadmap P0 gate floor (621) holds |
| Restoration phase vs plan (v2 §6) | **P0 complete; P1 artifact-only (unwired)** | ⚠️ AMBER — no P1.2–P1.5 code landed |
| Fail-closed posture (L1/L2/L3) | Decision source = `bootstrap-v0`; 43 weld-gate sites intact; all 10 deleted bodies **still deleted** | ✅ INTACT — `engagement-open-v0.json` is currently a **no-op artifact** |
| Import map (381 src modules) | 344 resolve / 37 fail | ❌ RED for `api/` + `agents/` — 14 modules broken by sandbox package/module shadow |
| Environment | Python 3.14.4 (pin `<3.13` violated), no `.venv`, no `.env`, no `python-dotenv` | ❌ RED — blocks autonomy workstream |
| Service tree & toolchain | `/home/yaser/raphael-2.0/` **gone** (4 dangling symlinks); Docker daemon up, **0 containers**; arsenal toolchain **1/24** | ❌ RED — blocks P3/P5 |
| Evaluation-artifact integrity | `evaluations/campaign/rbs_v4_holdout.jsonl` (frozen 1,200-row dataset) **absent, never committed**; `pytest` rewrites 14 historical `arena/results/raw/abl_*` dirs as a side effect | ❌ RED |
| Secrets (C-1) | 5 distinct full-format `nvapi-` key strings across 13 files | ❌ OPEN — rotation still not done |
| Cold-start E2E (DoD 4) | 3 attempts on 2026-10-03, all failed at `phase:recon`; zero successful engagements on record | ❌ expected given env gaps |

**Headline**: The repository is exactly at "P0 done, P1 half-done on paper." Every
safety-critical mechanism — broker exact-match checks, weld gates, deleted execution
bodies, `bootstrap-v0` decision source — remains fail-closed and the deployed open
engagement policy is inert (nothing loads it, and even if loaded it would not open the
action/capability dimensions). The suite is green at the 621 floor. Two real defects
stand out beyond plan status: (a) a pre-baseline `orchestrator.sandbox` package/module
shadow that breaks 14 imports including the entire `api` package, and (b) `pytest`
mutating historical arena evaluation data on every run.

---

## 2. WHAT CHANGED SINCE THE 2026-09-30 AUDIT (v2 §0 baseline)

| Item | 2026-09-30 (v2 §0) | 2026-10-04 (this audit) |
|---|---|---|
| `interactive_shell/reverse_shell.py` | deleted | **restored** — 457 lines, tracked, real implementation behind WELD-SHELL broker-receipt gating (commit `784d3fddb`) |
| P1 worktree edits | present, uncommitted | **committed into baseline** `e6a8c707e` (P0.2 done); fnmatch now present in `_target_matches` only |
| `policies/engagement-open-v0.json` | absent | present (P1.1 artifact) — **unwired** (0 references in `src/`) |
| Research layer | rounds 1–17 compiled | + `BLACK_HAT_OPERATOR_BLUEPRINT.md` (119/119 ATT&CK-grounded 2026-10-01 via `scripts/ground_attack_ids.py`), `references/ARCHITECTURAL_LEXICON.md`, `papers/AutoPen_2025_CSAE.pdf`, `scripts/env_inventory.sh`; INDEX updated (uncommitted) |
| `brain/contracts/` | absent | new spec layer (outcomes, action_spec, identity, goal) — explicitly **proposed/unwired**, honestly self-documented |
| Runtime activity | none recorded | 3 cold-start attempts 2026-10-03 06:11–06:16Z (`src/orchestrator/data/audit/audit_2026-10-03.jsonl`), target `t`, **all fail at `phase:recon`** — consistent with no LLM endpoint and no toolchain |
| Roadmap governance | v1 live | v1 marked SUPERSEDED by v2 (**uncommitted** worktree edit) |

---

## 3. ENVIRONMENT (E-series)

| ID | Finding | Severity |
|---|---|---|
| E-01 | System Python **3.14.4**; no `.venv` in repo; frozen pin `>=3.11,<3.13` violated. Suite still passes on 3.14 (621/621), but this is unverified territory vs the frozen instrument. | HIGH (reproducibility) |
| E-02 | `python-dotenv` missing; **no `.env`** — no LLM endpoint configured. Student/agent autonomy is inert by environment, not by code. | HIGH (blocks P4) |
| E-03 | **`/home/yaser/raphael-2.0/` no longer exists** — `cai_service`, `cloak_service`, `mhddos_service`, `mcp_hub` symlinks dangle; `cloak-service/main.py` and `mhddos-service/main.py` (roadmap Phase-2 targets #9–10) are unrecoverable from local disk. Docker daemon runs (29.7.2) with **zero containers** — kali-tools :3800, mcp-hub, neo4j, DVWA all down. | CRITICAL (blocks P3/P5) |
| E-04 | Arsenal toolchain **1/24 present** (`httpx` only); nuclei-templates absent. Matches v2 §0 "0/24" claim (now 1/24). P2 per-item probes and P5 scenarios have nothing to execute through restored sinks even if bodies return. | HIGH |

---

## 4. TEST SUITE & EVALUATION INTEGRITY

- **621 passed / 0 failed / 0 skipped / 0 xfail** in 30.3s — the P0 gate floor from the
  restoration roadmap holds on the committed baseline.
- Guardrail files (`tests/test_p2_guardrail_*.py`) green; weld tests
  (`tests/test_am4_weld_gates.py`, tracked since baseline) still assert **DENY** —
  Phase 1.5 re-pointing not started, consistent with the inert open policy.
- **TI-1 (new, HIGH)**: running the suite **rewrites 14 historical result dirs**
  `arena/results/raw/abl_{FULL_RAPHAEL,NO_WORLD_MODEL,PROMPTED_AGENT,SCRIPTED_BASELINE}_T1_NEGATIVE_CONTROL_s{0000,0003,0007,0042,0099,0123}_dev/episodes.jsonl`
  (observed mtimes = this audit's pytest run; last-row epoch timestamps = run time).
  Mechanism: deterministic run-id collision + `"w"`-mode write in
  `src/arena/episode.py:145` and `src/arena/ablation_runner.py:3345`. The properly
  hash-suffixed sibling dirs (428 of them) are untouched. This violates the repo's own
  Rule-1/E2E-dataflow append-only expectations (forge audit 2026-08-08). Quarantine and
  identify the writer test before the next campaign.
- **TI-2 (HIGH)**: `evaluations/campaign/rbs_v4_holdout.jsonl` — the frozen 1,200-row
  dataset with recorded SHA-256 `2bf614f8eafa0253…` — is **absent from the worktree and
  was never committed** (`git log --all` on the path is empty). `rbs_v4_reproducibility_manifest.json`,
  `rbs_v4_claim_ledger.json`, `FINAL_VERDICT_RECORD.md` etc. are present, so the
  reproducibility chain references data that does not exist here. Recover from origin or
  mark the manifest unverifiable.
- Stale floors: `REVIEWER_GUIDE.md` says "expect 357"; README says "121/121" — actual floor is 621.

---

## 5. WELD CENSUS & POLICY LAYER (L1/L2/L3)

Gate machinery: `orchestrator/auth.py::enforce_broker_mediation` present; 13 files under
`src/orchestrator` carry `WeldNotAuthorized` sites; canonical PDP remains
`brain/capability_broker.py::propose_action` (stages bind broker-authorized dimensions —
INV-2 intact).

**Deleted bodies — all 10 still deleted** (fail-closed stubs behind intact gates):

| # | Site | Status |
|---|---|---|
| 1 | `chains/tool_registry.py:90` `_run_command` | DELETED stub ("AM-4-R2 … body DELETED") |
| 2 | `orchestrator/kali_tools_client.py:70` + `:80 RuntimeError("Not implemented")` | DELETED |
| 3 | `c2/sliver_backend.py` (3 raise sites) | DELETED |
| 4 | `c2/beacon.py:218` listener bind | DELETED stub |
| 5 | `c2/implant_builder.py` (2 sites) | DELETED |
| 6 | `kali-tools/server.py` `/run` | file exists, no weld markers — **service tree gone**, unverifiable |
| 7 | `orchestrator/exec/sandbox.py::run_code` | present (canonical native sandbox, §14.4) — separate from legacy `PatchSandbox` |
| 8 | `src/agent/agent.py:99,:117` (exec shell / uninstall) | DELETED stubs |
| 9–10 | `cloak-service/main.py`, `mhddos-service/main.py` | **files do not exist** (external tree removed) |

**Policy layer facts**:
- Decision source: `runtime/policy.py` loads **`policies/bootstrap-v0.json` only**
  (`POLICY_PATH`, line 45); described as CONV-1 non-decision-source for the P2 mock path.
  **Zero** references to `engagement-open-v0.json` in `src/` (grep) — the open policy is
  deployed as an artifact and wired to nothing.
- Wildcard support (P1.2): `_target_matches` (`capability_broker.py:196–218`) supports
  exact/CIDR/fnmatch. `is_action_type_allowed` (:220) and `is_capability_allowed` (:229)
  remain **exact membership** — a policy with `allowed_action_types: ["*"]` would still
  DENY every concrete action type. The deployed open policy is therefore ineffective on
  2 of its 5 dimensions even hypothetically.
- ScopeV0 (`runtime/scope.py`) has no open mode; `covers()` (:301) is a thin view over
  `check()`. P1.4 not started.
- **Kill switch (v2 §2.2)**: trivially satisfied — the current state *is* the deny-all
  state. The one-file revert test is moot until the open policy is actually wired.

---

## 6. IMPORT MAP (381 modules)

**344 resolve / 37 fail.** Failure classes:

| Class | Count | Modules | Assessment |
|---|---|---|---|
| `PatchSandbox` ImportError | 14 | `api.{main,agent,ci,session,session_manager,tools,tools_bridge}`, `agents.{engage,exploit,postex}`, `bridge.raphael_bridge`, `sword.phase_2_exploit`, … | **REAL REGRESSION** — `orchestrator/sandbox.py` (module, defines `PatchSandbox`, mtime Sep 17) is shadowed by `orchestrator/sandbox/` (package, empty `__init__.py`, Sep 6). Python resolves the package; every consumer of `PatchSandbox` breaks. Pre-dates baseline (both mtimes < Sep 30) but was not caught by the Sep-30 audit. The whole API surface + agent engagement modules are import-broken. |
| Missing deps | 7 | `redis` ×4 (`raphael.eventbus`, `vhost_enum`, `integration.*`), `dns` ×2 (`raphael.verifier.*`) | known E-02-class gap (forge audit: deps only in `configs/requirements.txt`) |
| Service-local naming | 8 | `mcp-hub.*` ×3, `config.*` ×2, `recon-pipeline` `case_store` ×3 | structural (dash-packages), consistent with forge audit |
| cwd-based runners | 10 | `arena.d7…d16_*` | structural (depend on `scripts/d6c_holdout_runner` by design) |
| Import side effect | 1 | `phishing.main` — attempts `mkdir '/app'` at import time | hygiene defect; currently fails with Permission denied, which is the only thing preventing a root-owned dir creation at import |
| Stale sweep tooling | — | `forge/sweep_imports.py`, `launch_pilot.sh` hardcode dead `/home/yaser/raphael-2.0-rbsv2r` paths | doc/tool rot |

---

## 7. SECURITY FINDINGS

| ID | Finding | Status |
|---|---|---|
| S-1 (C-1) | **5 distinct full-format `nvapi-` key strings across 13 files**: `forge/apply_d13_blocks.py`, `forge/apply_d13_fixes.py`, `forge/prelaunch_verify2.py`, `forge/probe_nvidia.py`, `forge/verify_d13_patch.py`, `forge/wire_llm_service.py`, `scripts/rbs_v2r_canary_phase3_B.py`, `scripts/rbs_v2r_probe_120b.py`, `src/orchestrator/nvidia_provider.py:42`, `src/arena/manifests/D6C_HOLDOUT_MANIFEST.json:171`, `evaluations/campaign/PROVIDER_GATE_report.md:119` (values redacted here by policy). Rotate at provider, then purge from files/history. | **OPEN** |
| S-2 (C-2) | API unauthenticated-surface remediation not re-verifiable this pass (no services running, no container stack). Standing item. | OPEN |
| S-3 | `phishing/main.py` import-time filesystem side effect (`/app`). | NEW, LOW |
| S-4 | Runtime databases inside source trees: `src/orchestrator/data/{harvester,research,student_kb}.sqlite`, `data/shell_sessions.db` — untracked, unignored, and mutated by runs/tests. | hygiene |
| S-5 | `.zcodeignore` and the two governance doc edits uncommitted; runtime data dirs unignored. | hygiene |

---

## 8. DOCUMENTATION TRUTHFULNESS (spot check)

| Claim | Reality | Status |
|---|---|---|
| README: "121/121 tests passing" | 621 collected, 621 passed | stale (understates) |
| README: `docker compose -f docker/arena.yml up -d` | `docker/` contains only `api.Dockerfile` — **no arena.yml** | FALSE |
| README: `python scripts/smoke_test.py` | file exists now | fixed since forge audit |
| README: results incl. `rbs_v4_holdout.jsonl` | file absent, never committed | FALSE (TI-2) |
| README project structure: `orchestrator/` at root | code lives at `src/orchestrator/` | stale |
| REVIEWER_GUIDE: "expect 357" | actual floor 621 | stale |
| v2 §0 "toolchain 0/24" | 1/24 | approximately accurate |

---

## 9. RECOMMENDATIONS (prioritized)

1. **R-1 (CRITICAL)** Rotate the exposed NVIDIA keys and purge all `nvapi-` literals from
   the 13 files (S-1/C-1). Open since the 2026-09-30 audit.
2. **R-2 (HIGH)** Rebuild the environment before any P2 work: Python **3.12** venv,
   `requirements.txt` + `python-dotenv`, `.env` with LLM endpoint (E-01/E-02).
3. **R-3 (HIGH)** Fix the `orchestrator.sandbox` shadow (fold `sandbox/` package into the
   module or re-export `PatchSandbox` from the package) — the api/agents import base is
   broken and Phase-2 weld work lands on it.
4. **R-4 (HIGH)** Stop the suite from mutating `arena/results/raw` (route test episodes
   through `tmp_path`; make `run_id` unique per invocation). Quarantine the writer test.
5. **R-5 (HIGH)** Recover `rbs_v4_holdout.jsonl` (origin/backup) or amend the manifest to
   declare it unverifiable; do not let the reproducibility manifest keep pointing at
   absent data (TI-2).
6. **R-6 (MEDIUM)** Decide the service-tree story: `/home/yaser/raphael-2.0/` is gone —
   either restore that tree (cloak/mhddos bodies for Phase-2 items #9–10 are unrecoverable
   from this repo alone) or re-point compose/kali/mcp-hub provisioning into this repo.
7. **R-7 (MEDIUM)** Commit the governance state (v1-supersession banner, INDEX update,
   `.zcodeignore`, blueprint/reference set) so the branch records its own paper trail.
8. **R-8 (when P1 resumes)** Wiring `engagement-open-v0.json` is currently three-way
   inconsistent: artifact exists, no loader references it, and the broker cannot honor
   `["*"]` on action/capability dimensions anyway. Do P1.2 (wildcards), P1.3 (loader),
   P1.4 (scope open mode) and the v2 §2.2 kill-switch test as one atomic change or not
   at all.

---

## 10. AUDIT TRAIL

- Commands: `git status/log/diff`, file reads/greps, `PYTHONPATH=src python3 -m pytest
  tests/ --no-header -q` (621 passed), `bash scripts/env_inventory.sh` (read-only
  inventory), inline import sweep (read-only), `sha256sum` attempt on the holdout file.
- No network calls to any target; no offensive capability executed; no body restored; no
  policy wired or edited by this audit.
