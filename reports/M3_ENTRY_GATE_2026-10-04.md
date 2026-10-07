# M3 ENTRY GATE & D2 READINESS AUDIT — 2026-10-04

**Scope**: readiness audit only. No M3/D2 implementation, no policy changes, no
provider requests, no commits. Read-only inspection plus this report.
**Report location note**: this is the first report under `reports/` (created for
this audit per the task-order convention); all prior milestone evidence remains
under `evidence/` and was not modified.

---

## 1. Audit timestamp, branch, HEAD, worktree state

| Item | Observed (direct) |
|---|---|
| Audit time | 2026-10-04 ~17:40 UTC |
| Branch / HEAD | `offensive-restore` / `e6a8c707e614a1aa5468d5b93be324525513363f` — matches every prior milestone report |
| Worktree | **69** modified/untracked entries — the entire M0→M2.1 body of work remains **uncommitted** (as previously reported) |
| Stashes | **9 pre-existing git stashes** recorded (earlier project phases, `main`-era; not created or touched by this audit or prior milestones in this workstream) |
| Interpreter | `.venv` = Python **3.12.15** (pin `>=3.11,<3.13` satisfied) |
| Docker | compose v5.4.0; dvwa + kali-tools + dvwa-db **Up**, all published ports loopback-bound |

Discrepancies against prior reports: **none of substance.** Two new observations:
(a) the 9 pre-existing stashes (first inventoried here — earlier reports did not
mention them; they predate this workstream); (b) one `engagement-open` string
now exists in `src/` — it is a **comment** in the M2 D1 policy loader ("the
opposite of engagement-open-v0.json"), not wiring; the open policy remains
unreferenced by any code path.

## 2. Gate-by-gate status

| # | Gate | Status | Basis |
|---|---|---|---|
| G1 | Worktree & baseline integrity | **PASS** | branch/HEAD match; all milestone work present; no unexpected changes |
| G2 | M2.1 hardening intact (compose) | **PASS** | rendered config: lab ports `127.0.0.1:4280/3800`, dvwa-db unpublished, kali context resolves to `src/kali-tools`; non-loopback published ports: NONE; smoke 8/8 PASS |
| G3 | D1 policy boundary | **PASS** | `engagement-d1-v1.json`: exactly {`recon_service_probe`} × {`exec.d1_lab_probe`} × {`dvwa`}; zero wildcards; mode BOUNDED_LAB; 6/6 fail-closed flags true; `engagement-open-v0.json` unwired |
| G4 | D1 guarantees (tests) | **PASS** | 23 D1 tests green (authorization, wrong target/capability/action, malformed-policy fail-closed, restrictive control, kill switch, no-bypass gating, receipt/artifact binding, zero-spawn proofs) |
| G5 | Full test suite | **PASS** | 660 collected — **660 passed / 0 failed / 0 skipped**, 28.39 s, Python 3.12.15 |
| G6 | Historical evidence integrity | **PASS** | `arena/results/raw` byte-identical to the M0 baseline after the suite; baseline manifest unmodified (sha256 prefix `d4630af3de835bb6ef3d0b36`) |
| G7 | Credential security (working tree) | **PASS** | 0 full-format literals, 0 fragments in the worktree; uncommitted diff: **0 added / 14 removed** literal lines (the M0-C cleanup hunks themselves — keys already in HEAD history, nothing new exposed); runtime config is env-based (`nvidia_provider.py` reads `NVIDIA_API_KEY`/`NVIDIA_API_BASE`/`OPENROUTER_API_KEY` via `os.getenv`; zero literals) |
| G8 | Credential rotation (provider side) | **BLOCKED — OPERATOR CONFIRMATION REQUIRED** | literals remain in committed history (`git grep` HEAD: 15 files); no trustworthy confirmation of rotation exists; environment variable *names* absent from the process environment — and presence would not prove rotation anyway |
| G9 | LLM readiness (for a bounded D2) | **NOT VERIFIED** (structure only) | `.env` declares names `MODEL_ID`, `OPENAI_BASE_URL` (placeholder `https://integrate.api.nvidia.com/v1`), `API_KEY`, `TOR_PROXY`; `OPENAI_API_KEY` commented placeholder. No live call ever made in this workstream; **availability undemonstrated**. D2 does **not** need a provider: the canonical loop accepts mission-declared deterministic candidates (proven by D1's no-LLM runs) |
| G10 | Holdout dataset integrity | **BLOCKED** | `evaluations/campaign/rbs_v4_holdout.jsonl` absent; never committed (`git log --all`: 0 commits); manifest SHA `2bf614f8…` unverifiable-in-repo (M1-G recovery attempts stand) |
| G11 | D2 scope authorization | **NOT AUTHORIZED** | no multi-action policy exists or is proposed for installation; the scope contract below is a **PROPOSAL** for operator review |
| G12 | Guardrails / architecture | **PASS** | single Runtime, single PDP (Broker), single PEP unchanged; weld/guardrail tests green (103 targeted: D1 + M0 + guardrail + weld files); kill-switch semantics intact |

## 3. Exact commands executed (audit)

| Command | Outcome |
|---|---|
| `git branch/rev-parse/status --porcelain/stash list` | state above |
| `docker compose -p raphael-m1 -f configs/docker-compose.yml config --format json` | loopback-only ports, context resolved, no non-loopback publications |
| `grep`-based redacted credential scans (worktree, `{20,}` and `{4,}` patterns; `git diff HEAD` classification; `git diff --cached`) | 0 / 0 / 0 added–14 removed / 0 |
| `python3 -c` env-var name presence check | all five names absent from process env (names only; values never read) |
| `bash scripts/smoke_lab.sh` | PASS, exit 0 |
| `pytest tests/test_m2_d1_governed_action.py tests/test_m0_clean_floor.py tests/test_p2_guardrail_inv1.py tests/test_am4_weld_gates.py -q` | 103 passed |
| `pytest tests/ --no-header -q` | 660 passed / 0 failed / 0 skipped |
| sha256 comparison of `arena/results/raw` vs baseline | identical |
| `git log --all -- evaluations/campaign/rbs_v4_holdout.jsonl` | 0 commits (file absent) |

## 4. Credential-security findings (no secrets shown)

- Working tree: **0** full-format `nvapi-…` literals, **0** unintended fragments.
- Uncommitted diff: **0 added** literal lines; **14 removed** lines — these are
  the M0-C cleanup hunks (the historical keys appear only as deletions, local
  only; the same keys are already in committed history, so the diff adds no new
  exposure surface). Staged area: empty.
- The one suspicious-looking added line ("Key replacement in source | DONE … in
  `src/arena/ablation_runner.py` (2 locations) and `scripts/smoke_llm_usage.py`")
  is **pre-existing August-era content** of `evaluations/campaign/
  PROVIDER_GATE_report.md`, redacted in place by M0-C — not a new claim, and
  consistent with the current 0-literal worktree.
- Runtime credential source: environment variables only (verified in provider
  code); `.env` (git-ignored) holds placeholder values under clearly named keys.
- **Git history at HEAD still contains the literals (15 files) — rotation at the
  provider remains mandatory and is the single security blocker.**

## 5. LLM readiness findings (no network calls made)

- Configuration source: `.env` (git-ignored) + env-var contract in
  `src/orchestrator/nvidia_provider.py` (`NVIDIA_API_KEY`, `NVIDIA_API_BASE`
  default `https://integrate.api.nvidia.com/v1`, `OPENROUTER_API_KEY`).
- Names present in `.env`: `MODEL_ID`, `OPENAI_BASE_URL`, `API_KEY`,
  `TOR_PROXY`; `OPENAI_API_KEY` present as a commented placeholder. Values are
  placeholders by M1-B design.
- **Endpoint/model are configured in shape but NOT operational**: no evidence
  anywhere in this workstream demonstrates a successful authenticated provider
  call; availability is unverified and must not be assumed from configuration.
- Future-D2 design assumptions if a live provider is ever approved: timeout +
  offline fallback handling, no retries that mask auth failure, and no
  billboarded failures — none of this exists yet.
- **A bounded D2 can be tested fully deterministically without a provider** —
  the canonical loop's `mission.constraints["candidates"]` path was proven by
  every D1 run.

## 6. Holdout dataset status

Absent from the worktree and from all local history; the recorded manifest SHA
`2bf614f8eafa02533bfb522fa50ac1f1827acb0951eeeb42eff6b845a8e586b4` cannot be
verified in-repo (`unverifiable-in-repo`, per M1-G). Integrity uncertainty is
unresolved until recovery from a non-local backup, or an explicit operator
decision to amend the manifest. This blocks any future claim that RAPHAEL's
evaluation baseline is reproducible, but does not block M3/D2 implementation
itself.

## 7. Proposed D2 scope contract — `PROPOSAL — NOT AUTHORIZED`

> **STATUS: PROPOSAL — NOT AUTHORIZED.** Nothing below is installed. The active
> policy remains `engagement-d1-v1.json` (single action). Multi-action D2
> requires explicit operator approval of this contract (or an amended one) and
> a corresponding named, versioned policy artifact (e.g. `engagement-d2-v1`)
> reviewed before any runtime use.

1. **Permitted target**: exactly the local DVWA lab identity `dvwa` (container
   verified live per the D1 identity check: image prefix `vulnerables/web-dvwa`,
   shared `raphael-m1` compose network). No other target resolves.
2. **Candidate action types under consideration** (each purpose-bounded):
   - `recon_service_probe` — capability `exec.d1_lab_probe` — the existing D1
     nmap probe (fixed argv `nmap -Pn -sT -p 80 --host-timeout 45s`, in-container).
   - `lab_http_probe` — **new, to be implemented and reviewed**: a fixed-method
     HTTP GET against the DVWA loopback endpoint resolved from the lab identity
     (`http://127.0.0.1:4280/`), fixed headers, no user-supplied URLs, response
     status + body digest only. Purpose: give the planner a second, distinct
     evidence source so multi-step planning is meaningful.
   - Nothing else. No exploit/C2/postex/persistence/stealth classes; no
     arbitrary command or URL capabilities.
3. **Bounds**: max **5** steps per episode; ≤ **6** actions/minute; concurrency
   **1**; per-action timeout **90 s**; output cap **64 KiB** per result artifact.
4. **Authorization**: every action individually broker-decided (AUTHORIZED
   receipt with decision_id) AND scope-contained (ScopeV0) before its PEP
   dispatch — the planner proposes; it never authorizes.
5. **Receipts**: one immutable, decision-linked receipt per attempted action —
   including denied ones (denial receipts record reason; no execution fields).
6. **Replanning evidence**: a replan may fire only on receipted evidence
   (execution_result/artifact records or a persisted denial), never on
   un-evidenced model assertions.
7. **Halt rules**: any broker denial of a *required* action halts the episode
   (denial feedback recorded); a tool failure/timeout marks the step FAILED and
   consumes the step budget; missing evidence for a claimed outcome halts;
   contradictory evidence routes to the contradiction stage, not silent retry.
8. **Kill switch**: each D2 run performs the bootstrap-v0 swap check (same
   episode request → denied, zero spawns) before the positive run, exactly as
   D1 does today.
9. **No-spawn proof**: the subprocess spy pattern from D1 extends to every
   episode step: denied actions must show zero capability invocations and zero
   process spawns, asserted per step.
10. **Explicit exclusions**: external targets; arbitrary commands/executable
    paths; arbitrary URLs; wildcard targets/actions/capabilities; scope
    escalation mid-episode; newly restored offensive execution bodies; LLM
    provider calls (unless the operator separately resolves G8/G9 and amends
    this contract); commitments, C2, credential harvesting, stealth/evasion.

Architecture invariants carried forward: one Runtime, one production cognitive
loop, one Broker (PDP), one PEP, evidence-backed replanning; no second loop, no
Runtime-wide OFF mode.

## 8. Overall decision

### `READY FOR OPERATOR REVIEW`

Technical prerequisites (G1–G7, G12) are satisfied by current, reproducible
evidence: hardened lab, exact D1 policy with intact guarantees, green 660-test
suite on the pinned interpreter, unbroken historical-evidence integrity. The
following must be resolved by the operator before any M3/D2 implementation is
authorized — none of them can be closed by tests:

1. **Credential rotation confirmation** (G8) — `BLOCKED — OPERATOR
   CONFIRMATION REQUIRED`; provider-side revocation/replacement for the five
   fingerprints in `evidence/credential_exposure_20261004/README.md`.
2. **Provider decision** (G9) — either authorize a bounded live-endpoint
   configuration path (post-rotation) or confirm D2 runs deterministic
   (no-LLM) episodes; the deterministic route is already technically proven.
3. **D2 scope authorization** (G11) — approve, amend, or reject the §7
   contract; approval must precede any `engagement-d2-v1` artifact.
4. **Holdout dataset decision** (G10) — recover from a non-local backup or
   formally amend the reproducibility manifest.
5. **Commit authorization** — the complete M0→M2.1 worktree remains
   uncommitted.

`READY FOR M3 IMPLEMENTATION` is explicitly **not** claimed: it requires items
1–3 (and, for evaluation claims, 4) to be closed by the operator.

## 9. Files modified by this audit

Exactly one new file: `reports/M3_ENTRY_GATE_2026-10-04.md` (plus the
`reports/` directory itself). No other file was created, modified, or deleted;
no docker state changed; no network calls to any non-local system.
