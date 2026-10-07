# M0 REVIEW REASSESSMENT — 2026-10-04

Independent review remediation and gate reassessment for M0 — Clean Floor, per the
review task order. Original implementation report:
`RAPHAEL_M0_IMPLEMENTATION_REPORT_20261004.md` (§3 and §4 amended in place with
dated amendment notes — see §9 of this document). Scope held to review remediation:
no policy wiring, no capability restoration, no M1 provisioning, no commits, no
history rewrite.

---

## 1. Starting state

| Item | Observed |
|---|---|
| Branch / HEAD | `offensive-restore` / `e6a8c707e` (unchanged — no commits made during M0 or this review) |
| Worktree | 28 tracked modifications + 1 deletion (`src/orchestrator/sandbox.py`) + 24 untracked paths, including all pre-existing M0 worktree artifacts (roadmaps, blueprints, `policies/engagement-open-v0.json`, contracts/, audit & gap-analysis & M0 reports) — all preserved |
| Interpreter | Python 3.14.4 (system; frozen pin `>=3.11,<3.13` still violated; still no venv — M1 scope) |
| M0 changes | All present in the worktree as reported; nothing had been committed or reverted between the M0 report and this review |

## 2. Independent diff review — per work package

**M0-A — sandbox shadow: VERIFIED.**
- `src/orchestrator/sandbox.py` deleted in worktree; `orchestrator/sandbox/__init__.py`
  defines `PatchSandbox` + `sandbox` verbatim (W-10 fail-closed stub intact;
  `enforce_broker_mediation` precedes the raise).
- Fresh process: `from orchestrator.sandbox import PatchSandbox, sandbox` succeeds
  (`PatchSandbox.__module__ == "orchestrator.sandbox"`).
- Canonical `src/orchestrator/exec/sandbox.py`: **untouched** (`git diff HEAD --stat
  -- src/orchestrator/exec/` is empty).
- W-10 fail-closed behavior: regression test `test_patchsandbox_run_code_still_fail_closed`
  passes (raises `WeldNotAuthorized` through the broker gate).
- Census/classification paths: `evidence/phases/P3_0_reinventory/{CENSUS,WELD_SET,
  CLASSIFICATION}.md` amended to `src/orchestrator/sandbox/__init__.py` with dated
  amendment notes; `test_census_covers_lexicon_selection` and the full
  `test_p3_0_reinventory_consistency.py` (11 tests) pass.
- Deleted module recoverable: `git show HEAD:src/orchestrator/sandbox.py` returns the
  original 43-line module (content also reproduced inside the package `__init__.py`).
- Weld tests: both path-referenced assertions repointed with **byte-identical
  assertion content** (no weakening); `tests/test_am4_weld_gates.py` fully green.

**M0-B — evaluation-data isolation: VERIFIED, with one evidence improvement noted.**
- Fixture: `tests/conftest.py` autouse fixture redirects
  `arena.ablation_runner.RESULTS_BASE` to a per-test `tmp_path` dir. Production
  default is untouched (module constant still `"arena/results"`; fixture only active
  under pytest).
- Writer paths genuinely exercised: pytest's retained tmp tree
  (`/tmp/pytest-of-yaser/pytest-8/`) contains `…/arena-results/raw/abl_*_dev/
  episodes.jsonl` written by the writer tests (`test_no_world_model_config_sti0`,
  `test_deterministic_replay_*`, `test_ensure_run_dir_idempotent0`, …) — i.e. the
  real `EpisodeRecorder`/`ensure_run_dir` write path executed and landed in
  per-test temp dirs, not merely a fixture-assignment assertion.
- Protected tree: `arena/results/raw` byte-identical to the recorded post-
  contamination baseline across **four** suite runs now (3 during M0 + 1 during this
  review) — see §5.
- The 14 contaminated directories are identified in
  `evidence/arena_contamination_20261004/README.md` with quarantined post-
  contamination copies; originals not recoverable locally (git-ignored files);
  nothing regenerated or presented as original.
- Gap found and closed during this review: no test previously exercised the writer
  path end-to-end under isolation beyond the hash comparison; the retained-tmp
  evidence above plus the M0 regression tests (`test_arena_results_base_redirected_
  during_tests`, `test_episode_recorder_memory_only_without_output_dir`) now cover
  both the mechanism and the outcome.

**M0-C — credential remediation: VERIFIED (cleanup only; rotation still external).**
- Fresh scans (this review): full-format `nvapi-…` literals **0**; unintended
  fragments (4+ chars) **0**; the only remaining match is the intentional
  `nvapi-REPLACE_ME` placeholder in `cli/.env.example`.
- Provider adapter: `src/orchestrator/nvidia_provider.py` — embedded default
  removed from `os.getenv("NVIDIA_API_KEY", …)`; environment is the sole source.
- Configuration references: `forge/{wire_llm_service,probe_nvidia}.py`,
  `scripts/rbs_v2r_{probe_120b,canary_phase3_B}.py` use
  `os.environ.get("NVIDIA_API_KEY", "")`; `forge/prelaunch_verify2.py` reads
  `NVIDIA_API_KEY_A/B` from the loaded `.env`.
- One-shot remediation scripts (`forge/apply_d13_blocks.py`,
  `forge/apply_d13_fixes.py`, `forge/verify_d13_patch.py`,
  `forge/prelaunch_inspect.py`): literals replaced by the marker
  `REDACTED-M0-C-20261004`; their search semantics now target the marker (documented
  in `evidence/credential_exposure_20261004/README.md`).
- Git history: `git grep nvapi- HEAD` still matches **15 files** — literals remain in
  committed history; keys must be treated as compromised.
- **Rotation: NOT performed, NOT claimed.** No external requests, no authentication
  attempts, no printed values. The security gate stays **BLOCKED** pending operator
  rotation + safe validation (`evidence/credential_exposure_20261004/README.md`, §6
  checklist).

**M0-D — import purity: VERIFIED, with one test added during review.**
- Import purity: `import phishing.main` in a subprocess with `TEMPLATE_DIR` pointed
  at a probe path creates nothing (existing regression test, still green).
- Startup correctness — **gap found and closed**: the original M0 evidence did not
  prove the startup hook still initializes the directory. Added
  `test_phishing_startup_creates_template_dir` (subprocess: import, then call
  `phishing.main._ensure_template_dir()`; asserts probe dir created). Green.
- The module is also no longer in the import-failure list (pre-M0: failed with
  `Permission denied: '/app'` at import time).

**M0-E — runtime data preservation: VERIFIED.**
- `.gitignore:117-118` covers `data/` and `src/orchestrator/data/`
  (`git check-ignore -v` confirms all three runtime DB/telemetry paths).
- Nothing deleted: `data/shell_sessions.db`, `src/orchestrator/data/{harvester.db,
  research.db,student_kb.sqlite,audit/audit_2026-10-03.jsonl}` all still on disk.
- Nothing tracked was hidden: `git ls-files data/ src/orchestrator/data/` is empty —
  the rules only affect untracked runtime artifacts.
- `.zcodeignore` custom section updated with the same paths (+ arena results tree).

**M0-F — documentation accuracy: VERIFIED.**
- README: no `docker/arena.yml` references remain; holdout dataset marked **NOT
  PRESENT** in both the results block and the artifacts table with the
  `unverifiable-in-repo` decision pointer; structure block matches `src/`-based
  reality; no stale "121/121"-as-current claims (the historical count is explicitly
  contextualized).
- `REVIEWER_GUIDE.md`: floor 621 with date, interpreter, and explicit pin-violation
  caveat.
- `launch_pilot.sh`: repo-relative + explicit M1 guard (no dead external paths).
- `forge/sweep_imports.py`: repo-relative `SRC`; runs against this repo.
- v1 roadmap supersession banner: present (pre-existing worktree edit, preserved).
- `references/INDEX.md`: pre-existing research-compilation entries, preserved.

## 3. Corrected import-failure inventory and arithmetic

Two sweep methodologies were run; they disagree, and the disagreement is itself
diagnosed and documented.

**Methodology A (used in the M0 report and the 2026-10-04 audit):** all 380 modules
imported in ONE process via `importlib`. Result: 350 OK / 30 FAIL.
**Methodology B (ground truth, this review):** one fresh subprocess per module
(380 subprocesses, `importlib.import_module`, `PYTHONPATH=src`). Result:
**339 OK / 41 FAIL**.

**Why they differ (reproduced and instrumented).** When a submodule import fails
inside its package `__init__`, CPython leaves the **partially-initialized parent
package** in `sys.modules`; later imports of *sibling* submodules find the parent
cached, skip the failing `__init__`, and succeed if they do not (transitively) touch
the failed module. Demonstrated: after `import orchestrator.api.main` fails, a
spy-instrumented retry of `orchestrator.api.session_manager` succeeds with **zero
additional** `ensure_multipart_is_installed` calls, with
`orchestrator.api.session` absent from `sys.modules` (partial-parent state).
Methodology A therefore under-counts by up to 11 modules; every pre-M0/M0 count
produced with Methodology A (37 before, 30 after) is a masked lower bound. A
fresh-process pre-M0 baseline was not captured — noted as an audit limitation, not
reconstructed.

**Single root cause behind all 8 api failures:** `orchestrator/api/__init__.py:5`
unconditionally imports the session router; `orchestrator/api/session.py:140`
(`POST /api/sessions/{session_id}/messages`) declares `tool_calls: Optional[list]`,
which this FastAPI version infers as a **Form** field, and `analyze_param` then
requires `python-multipart` (absent; declared at `requirements.txt:26`). One param
therefore makes every `orchestrator.api.*` import fail in a fresh process.

**Full inventory (41 failures, 339 of 380 resolve):**

| # | Import target | Failure class | Cause | Existed before M0? | M0 introduced/changed? | Resolution milestone |
|---|---|---|---|---|---|---|
| 1 | orchestrator.api.agent | dep | `python-multipart` (declared, req.txt:26) via session.py:140 Form-inferred param + package `__init__` chain | cause pre-existing; pre-M0 the module failed earlier at the shadow (masked) | M0-A **unmasked** it; introduced nothing | M1 (env); optional code hardening (explicit `Body`/scalar annotation) decouples api imports from multipart — later milestone, non-blocking |
| 2 | orchestrator.api.ci | dep | same | same | same | M1 |
| 3 | orchestrator.api.main | dep | same | same | same | M1 |
| 4 | orchestrator.api.session | dep | same (own route hosts the param) | same | same | M1 |
| 5 | orchestrator.api.session_manager | dep | same (fails via `__init__`, not own routes) | same | same | M1 |
| 6 | orchestrator.api.tools | dep | same | same | same | M1 |
| 7 | orchestrator.api.tools_bridge | dep | same | same | same | M1 |
| 8 | orchestrator.api.types | dep | same (fails via `__init__`) | same | same | M1 |
| 9 | raphael.eventbus.core | dep | `redis` (declared, req.txt:36) | pre-existing | unchanged | M1 |
| 10 | raphael.exploit_factory.core | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 11 | raphael.exploit_factory.cve_database | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 12 | raphael.exploit_factory.delivery | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 13 | raphael.exploit_factory.payload_templates | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 14 | raphael.exploit_factory.types | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 15 | raphael.integration.harness | dep | `redis` | pre-existing | unchanged | M1 |
| 16 | raphael.integration.test_pipeline | dep | `redis` | pre-existing | unchanged | M1 |
| 17 | raphael.techniques.vhost_enum.core | dep | `redis` | pre-existing | unchanged | M1 |
| 18 | raphael.techniques.vhost_enum.enumerators | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 19 | raphael.techniques.vhost_enum.types | dep | `redis` (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 20 | raphael.verifier.channels | dep | `dns`/dnspython (declared, req.txt:27) | pre-existing | unchanged | M1 |
| 21 | raphael.verifier.core | dep | `dns`/dnspython | pre-existing | unchanged | M1 |
| 22 | raphael.verifier.types | dep | `dns`/dnspython (transitive) | pre-existing (masked in-proc) | unchanged | M1 |
| 23 | arena.d7_r1_gemma_retest | structural | cwd-based runner: imports `scripts/d6c_holdout_runner` by design | pre-existing | unchanged | documented design; optional M6 tooling cleanup |
| 24 | arena.d7_regression_test | structural | same | pre-existing | unchanged | same |
| 25 | arena.d8_cognitive_trace | structural | same | pre-existing | unchanged | same |
| 26 | arena.d8_regression_test | structural | same | pre-existing | unchanged | same |
| 27 | arena.d9_regression_test | structural | same | pre-existing | unchanged | same |
| 28 | arena.d10_falsification_defeater_diagnostic | structural | same | pre-existing | unchanged | same |
| 29 | arena.d10_regression_test | structural | same | pre-existing | unchanged | same |
| 30 | arena.d11_regression_test | structural | same | pre-existing | unchanged | same |
| 31 | arena.d13_diagnostic_runner | structural | same | pre-existing | unchanged | same |
| 32 | arena.d16_holdout_runner | structural | same | pre-existing | unchanged | same |
| 33 | mcp-hub.main | structural | dash-dir standalone service; internal `import mcp_hub` | pre-existing | unchanged | service bring-up (M4/M6), standalone PYTHONPATH design |
| 34 | mcp-hub.tests.test_server | structural | same | pre-existing | unchanged | same |
| 35 | mcp-hub.core.server | structural | internal `import config` vs repo `configs/` | pre-existing | unchanged | service bring-up (M4/M6) |
| 36 | orchestrator.config.paths | structural | `import config` vs `configs/` (forge-audit E-04 class) | pre-existing | unchanged | defect ticket, M4+ non-blocking |
| 37 | orchestrator.config.target | structural | same | pre-existing | unchanged | defect ticket, M4+ non-blocking |
| 38 | recon-pipeline.case_api | structural | internal `case_store` import (service-local naming) | pre-existing | unchanged | service bring-up (M4/M6) |
| 39 | recon-pipeline.main | structural | same | pre-existing | unchanged | service bring-up (M4/M6) |
| 40 | recon-pipeline.stale_recovery | structural | same | pre-existing | unchanged | service bring-up (M4/M6) |
| 41 | sword.phase_2_exploit | **code drift** (kept separate from deps per review order) | imports non-existent `validate_exploit_results` (validator defines `validate_exploit`) | cause pre-existing; pre-M0 masked by the shadow (observed as a `PatchSandbox` error) | M0-A unmasked it; introduced nothing | defect ticket (M4+), non-blocking for M0–M3 |

**Arithmetic reconciliation.**

| Class | Methodology A (one process) | Methodology B (fresh process, ground truth) |
|---|---|---|
| Missing declared deps — `python-multipart` | 5 | **8** |
| Missing declared deps — `redis` | 4 | **11** |
| Missing declared deps — `dns` | 2 | **3** |
| **Deps subtotal** | **11** | **22** |
| Structural (arena 10, mcp-hub 3, config 2, recon-pipeline 3) | 18 | **18** |
| Code drift (sword.phase_2_exploit) | 1 | **1** |
| **Total** | **30** | **41** |

The original M0 report's bucket totals ("10 deps / 15 structural / 1 drift = 26")
were arithmetic errors inconsistent with both its own itemization (11/18/1 = 30) and
the fresh-process truth (22/18/1 = 41). The original report has been amended in
place (§3, §4) with dated amendment notes preserving what changed and why.

## 4. Verification performed (exact commands and results)

| # | Command | Result |
|---|---|---|
| 1 | `git status --porcelain`, `git rev-parse HEAD` | state recorded (§1) |
| 2 | Fresh-process sweep: 380 × `python3 -c "import importlib…import_module(<mod>)"` subprocesses, `PYTHONPATH=src`, 8 workers | 339 OK / **41 FAIL** (list in §3) |
| 3 | One-process sweep (Methodology A, reproduced) | 350 OK / 30 FAIL — masking mechanism demonstrated via spy (retry of `api.session_manager` after failed `api.main`: 0 additional multipart-check calls; partial parent package persisted) |
| 4 | `PYTHONPATH=src python3 -m pytest tests/test_m0_clean_floor.py -q` | 11 passed / 5 skipped (5 = multipart-gated api imports, reason documented in test) |
| 5 | `PYTHONPATH=src python3 -m pytest tests/test_p3_0_reinventory_consistency.py -q` | 11 passed |
| 6 | Full suite: `PYTHONPATH=src python3 -m pytest tests/ --no-header -q` (protected tree verified before and after) | **637 collected — 632 passed / 0 failed / 5 skipped — 58.30 s** (M0 report's 631 + 1 new startup test) |
| 7 | `find arena/results/raw -type f \| sort \| xargs sha256sum` vs `evidence/arena_contamination_20261004/PRE_M0_SHA256SUMS.txt` | byte-identical (4th consecutive) |
| 8 | `grep -rnE "nvapi-[A-Za-z0-9_-]{20,}" …` / `{4,}` (redacted output) | 0 / 0 (only intentional `nvapi-REPLACE_ME` placeholder) |
| 9 | `git grep nvapi- HEAD` | 15 files still in committed history (rotation mandatory; no rewrite performed) |
| 10 | `git show HEAD:src/orchestrator/sandbox.py`, `git diff HEAD --stat -- src/orchestrator/exec/` | deleted module recoverable; `exec/` untouched |
| 11 | Writer-path evidence: `find /tmp/pytest-of-yaser -name episodes.jsonl -path "*abl_*"` | retained per-test tmp dirs contain the `abl_*` episode files written by the writer tests |

The five suite skips: `test_api_modules_import_with_multipart_present[*]` — one per
blocked `api.*` module, each naming `python-multipart` (M1) as the blocker. The
interpreter-pin violation remains: results are from Python 3.14.4 against a frozen
`>=3.11,<3.13` instrument; M1 must re-verify on 3.12.

## 5. Historical-data integrity status

- Baseline `PRE_M0_SHA256SUMS.txt` (52,022 files) **not modified** during this review.
- Four consecutive suite runs (3 in M0 + 1 here) leave `arena/results/raw`
  byte-identical to the baseline.
- 14 contaminated directories remain recorded as potentially contaminated with
  quarantined copies; no regeneration, no claims of recovery.
- TI-2 status unchanged: `rbs_v4_holdout.jsonl` absent, never committed,
  **unverifiable-in-repo**; recovery from origin recommended; the
  `evaluations/campaign/*.jsonl` ignore rule (pre-dating the dataset) must be
  amended for that file if/when recovered — operator decision.

## 6. Credential-remediation status

- **Cleanup (M0 work): complete and re-verified** — 0 full-format literals, 0
  unintended fragments in the working tree; provider adapter env-only; configuration
  via environment; one-shot scripts marker-based and documented; no values printed in
  any artifact.
- **Rotation (operator action): NOT DONE, NOT CLAIMED.** 15 files in committed git
  history still contain literals; all five keys (fingerprints `58356654`, `06323f90`,
  `c5fdb929`, `94652146`, `d98e6170`) must be treated as compromised until the
  operator executes the checklist in `evidence/credential_exposure_20261004/README.md`
  (revoke → replace → store env-only → safe validation → record fingerprints).
- **The M0 security gate remains BLOCKED until the operator confirms rotation and
  safe validation.**

## 7. Criterion-by-criterion gate assessment

| Criterion | Disposition | Evidence / condition |
|---|---|---|
| Suite green at or above the 621 baseline, variance explained | **PASS** | 632 passed / 0 failed / 5 skipped (637 collected) = 621 baseline + 16 M0 regression tests, 5 of them documented env-gated skips; reproduced under review |
| Previously shadow-broken imports resolve | **BLOCKED** | Shadow eliminated and proven for all 14 modules (0 shadow-class failures); `agents.*` (3/3) and `bridge.*` (1/1) resolve; but all 8 `api.*` modules still fail in fresh processes on the declared `python-multipart` dependency — resolvable only by M1 environment provisioning, which is outside M0's boundary. Per review instruction this is **not** reinterpreted as PASS |
| Repeated suite runs preserve the protected result tree | **PASS** | 4 consecutive byte-identical comparisons vs the untouched baseline |
| No credential literals remain in the working tree | **PASS** | 0 full-format / 0 fragments (redacted scans); placeholder only |
| Documentation accurately reflects observed state | **PASS** | §2 M0-F; corrected claims all evidence-backed; missing dataset still recorded as absent |
| No unrelated changes introduced | **PASS** | Diff reviewed file-by-file; one new test added during review (M0-D startup) is review-remediation scope, documented |
| Provider-side credential rotation confirmed | **BLOCKED** | External operator action pending; cleanup ≠ rotation |

## 8. Remaining blockers and owners

| Blocker | Owner | Unblocks |
|---|---|---|
| Rotate the five exposed NVIDIA keys + safe validation of replacements | **Operator** (external) | M0 security gate closure; M3 endpoint configuration |
| Provision Python 3.12 venv + `requirements.txt` (incl. `python-multipart`, `redis`, `dnspython`) | Implementation engineer — **M1** | Import criterion for the 8 api modules + 14 dep-blocked `raphael.*` modules; pin compliance |
| Recover `rbs_v4_holdout.jsonl` from origin (or accept `unverifiable-in-repo`) | **Operator** decision + engineer recovery attempt — M1 | Reproducibility-manifest closure |
| `sword.phase_2_exploit` validator drift | Implementation engineer — defect ticket, M4+ | sword module importability (non-blocking for M0–M3) |
| `api/session.py:140` `tool_calls` Form-inference hardening | Implementation engineer — optional ticket | Decouples api imports from multipart (nice-to-have after M1) |
| Commit authorization for the M0 worktree | **Operator** | Recording M0 as history |

## 9. Regressions, scope deviations, unresolved uncertainty

- **Regression found and fixed during review:** none in code; the review added one
  test (`test_phishing_startup_creates_template_dir`) closing an evidence gap in M0-D
  (startup-path correctness was previously unproven). Suite went 631 → 632 passed.
- **Corrections to the original M0 report (amended in place, dated notes preserved):**
  (a) §3 bucket arithmetic (10/15/1 → corrected itemization; in-process totals 30 /
  fresh-process 41) and the api-module count (5 → 8); (b) §4 suite counts updated with
  the review reproduction (637/632/5). No claim was strengthened; two were weakened to
  match evidence.
- **Scope deviations:** none beyond the one added test; no policy, capability,
  autonomy, or architecture changes; no commits; protected tree untouched.
- **Unresolved uncertainty:** the exact CPython rule that leaves the partially
  initialized parent package in `sys.modules` after a failed submodule-in-`__init__`
  import was reproduced and instrumented but not pinned to a versioned interpreter
  behavior reference; the practical consequence (one-process sweeps under-count) is
  fully documented. Fresh-process pre-M0 import baseline was never captured; "existed
  before M0" for the 22 dep/18 structural/1 drift failures rests on cause analysis
  (none of these errors involve code M0 touched) plus the audit's in-process
  observations.

## 10. Recommendation for the next authorized task

**M1 — Runnable Environment** (gap plan §3), unchanged as the next milestone, now
carrying two extra inputs from this review: (a) the environment provisioning should
close the import criterion (8 api modules + 14 dep-blocked `raphael.*` modules) and
re-run the fresh-process sweep as its gate; (b) the operator checklist items (key
rotation confirmation, holdout-dataset recovery decision) should be resolved alongside
M1 so the M0 security gate can formally close. Awaiting operator review of this
reassessment before any M1 work begins.
