# RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1 — Full Offensive Restoration & Autonomous Operation

Status: PLANNED (build pending operator go per phase)
Base: HEAD `3b2e22db3d952622150d271c12c41d9ed21e81fd` + 91 dirty entries (worktree)
Prepared from: end-to-end audit (2026-09-30), file-level weld census, git history recovery probe.

---

## 0. Objective and Definition of Done

**Objective**: restore every welded/deleted offensive capability and convert Raphael from a
fail-closed research skeleton into a continuously operating autonomous offensive agent that
executes the full arsenal (recon → scan → exploit → C2 → post-ex → persistence → exfil)
with no operator approval inside the loop.

**Definition of Done (DoD)**:
1. All 15 weld tickets (W-01…W-15) return broker AUTHORIZED under the deployed open policy;
   execution runs (no `WeldNotAuthorized` on any path).
2. All 10 files with deleted execution bodies restored (functionally, verified by live probes).
3. Full test suite green with INV-1/guardrail structure untouched; denial-expectation tests
   re-pointed to open-policy expectations (see Phase 1.5).
4. Cold-start E2E: one command launches the agent, which autonomously runs
   recon → scan → exploit → post-ex against the lab arena and produces evidence receipts,
   with zero human approvals mid-run.
5. Episode loop runs multi-iteration continuously (operator sets target set only).

---

## 1. Restriction model (what is actually blocking execution)

Five layers, outermost first. Restoration opens them in order — each layer must be open
before the next is observable.

| Layer | What it blocks | Where |
|---|---|---|
| L1 Policy | Broker denies `tool_execute`/`agent_engage` (not in bootstrap-v0 allowlist) and impact 7–8 > budget 0.0; capability/action checks are exact-match (no wildcard) | `policies/bootstrap-v0.json`, `runtime/policy.py`, `brain/capability_broker.py:220-236` |
| L2 Weld gates | 43 files raise fail-closed `WeldNotAuthorized` unless broker AUTHORIZED with canonical dimensions | `orchestrator/auth.py::enforce_broker_mediation` + W-01…W-15 sites (§3) |
| L3 Deleted bodies | 10 files: gate passed, then unconditional raise — execution code physically removed | §3 table "BODY=DELETED" |
| L4 Dormant wiring | Canonical chain can only run `fixture.inspect`; arsenal never proposed by Student/Planner; services (kali, mcp-hub, c2, phishing…) not routed | `runtime/loop.py`, `exec/safe_capability.py`, `student/`, `chains/` |
| L5 Autonomy bounds | Episode defaults `max_iterations=1, action_cap=1`; persona `requires_approval`; command-filter Tier-1/2; Falsification blocks Student proposals; RateLimiter 60/min; engagement window | `runtime/loop.py:158-163`, `api/types.py:744`, `interactive_shell/command_filter.py`, `brain/falsification*`, `brain/rate_limiter.py` |

Also blocking at the environment layer: `reverse_shell.py` deleted in worktree (breaks all
imports — restore first), Python env drift (3.14 vs `>=3.11,<3.13`), no `python-dotenv`.

---

## 2. Phase plan

### Phase 0 — Stabilize the workspace (prerequisite, small)
1. `git checkout -- src/orchestrator/capabilities/interactive_shell/reverse_shell.py`
   (currently ` D`; whole suite fails collection without it).
2. Operator decision on the 91 dirty entries: commit as WIP on a working branch
   (`git switch -c offensive-restore && git add -A && git commit`) so all restore work
   diffs cleanly against a recorded baseline. Includes the untracked
   `tests/test_am4_weld_gates.py` — do not lose it.
3. Create venv pinned to Python 3.12; `pip install -r requirements.txt` + `python-dotenv`.
4. Optional but recommended: rotate the 3 leaked NVIDIA keys (audit C-1) and move them to
   env vars; configure the live inference endpoint (`.env`: `OPENAI_BASE_URL`/`MODEL_ID`)
   — the autonomous Student/agent needs a working LLM.

**Gate**: `PYTHONPATH=src pytest tests/ -q` = 621 passed on the committed baseline.

### Phase 1 — Open L1: permissive policy (gates stay real, policy goes open)
Design principle: keep every gate mechanism intact; deploy an *open policy*. Tests then
prove both directions (open policy allows; a locally-constructed restrictive policy still
denies) — suite stays green without deleting guardrails.

1. New artifact `policies/engagement-open-v0.json` (project convention: named, versioned):
   - `allowed_action_classes`: `*` (all), incl. `tool_execute`, `agent_engage`, `sandboxed_exec`,
     `shell_*`, scan/exploit/postex classes.
   - `allowed_targets: ["*"]`, `allowed_capabilities: ["*"]`,
     `max_impact_per_action: 10.0`, `max_cumulative_impact: 1e9`,
     `max_actions_per_minute/hour/concurrent: 1e9`, engagement window open.
2. `brain/capability_broker.py`: add fnmatch wildcard support to
   `is_action_type_allowed` and `is_capability_allowed` (mirror `_target_matches`;
   today they are exact-membership so `["*"]` does not actually mean "all").
3. `runtime/policy.py::make_broker_from_bootstrap` → load `engagement-open-v0.json`
   (keep bootstrap-v0 loader intact for restrictive-policy tests).
4. `runtime/scope.py` ScopeV0: add `covers()` open mode (or generate mission scope with
   allow-all rules); verify `stage_broker` (`stages.py:380-431`) passes with scope=None
   and with open scope.
5. Legacy `orchestrator/scope.py::ScopeConfig`: replace implicit allow-when-empty with an
   explicit `open=True` default (behavior same, intent recorded; also fix the
   `endswith` suffix spoof while touching it).
6. RateLimiter/engagement window: defaults off in open policy (no code path change needed
   once policy fields are open — verify `propose_action` `3b` path).
7. **Probe**: replay the audit's `weld_probe.py` — all three cases must print AUTHORIZED.

### Phase 1.5 — Re-point denial tests (same phase, keeps suite green)
- `tests/test_am4_weld_gates.py` (untracked — commit in Phase 0.2) and every
  `pytest.raises(WeldNotAuthorized)` test (`test_w01…`, `test_w09`, `test_w12`,
  `test_w13`, `test_w14…`) flip to: open policy → AUTHORIZED → sink reachable.
- Machinery proof preserved: add `test_restrictive_policy_still_denies` constructing a
  `BrokerPolicy` with the old bootstrap allowlist and asserting DENY + 403 mapping.
- Keep all `test_p2_guardrail_*` (INV-1, no-bypass, single-runtime) untouched and green.

**Gate**: suite green; weld probe all-AUTHORIZED; guardrails unchanged.

### Phase 2 — Restore L3: deleted execution bodies (recover from git history)
Recovery pattern (bodies confirmed present in history at restructure `50ba7cbfe`):
```bash
DEL=$(git log --format=%H -S '<raise message>' -- <file> | tail -1)   # deletion commit
git show ${DEL}^:<path-at-that-time> > /tmp/orig.py                   # pre-deletion body
# re-insert body after the gate; keep enforce_broker_mediation call above it
```
If history lacks the body (path predates restructure), rewrite from scratch — size class M.

| # | Weld | File | Body | Restoration |
|---|---|---|---|---|
| 1 | W-01 | `chains/tool_registry.py::_run_command` | DELETED | recover asyncio `create_subprocess_exec`+`communicate`/kill; unblocks nmap/sqlmap/bloodhound/metasploit/cme/chisel executors + `POST /api/tools/{tool}` |
| 2 | W-07 | `orchestrator/kali_tools_client.py` | DELETED | recover httpx POST hop to kali service |
| 3 | W-08 | `c2/sliver_backend.py` (`_import_config`, `generate_implant`) | DELETED | recover sliver-client invocation |
| 4 | W-08 | `c2/beacon.py` (listener bind) | DELETED | recover aiohttp TCPSite listener |
| 5 | W-08 | `c2/implant_builder.py` (build dispatch) | DELETED | recover SUB-05…09 fan-out |
| 6 | W-09 | `kali-tools/server.py` (`/run`) | DELETED | recover container-side subprocess exec |
| 7 | W-10 | `orchestrator/sandbox.py::run_code` | DELETED | recover arbitrary-code exec (powers `sandboxed_exec` PEP branch already in `stages.py:_stage_pep_sandboxed`) |
| 8 | W-14 | `agent/agent.py` (exec shell, uninstall) | DELETED | recover subprocess/shutil branches |
| 9 | W-14 | `cloak-service/main.py` (Tor egress, stem control) | DELETED | recover Tor-egress + controller signaling |
| 10 | W-14 | `mhddos-service/main.py` (attack exec) | DELETED | recover Popen attack executor |

Gated-intact sites (body already present behind the gate) need only Phase 1:
W-02 `api/tools_bridge.py`, W-03 `agents/engage.py` + `api/agent.py`, W-04/05 `modes/autonomous.py` + `api/ci.py`,
W-08 `c2/dga.py`, W-10 `agents/exploit.py`, W-11 `exploit/mcp_bridge.py` + `relay_chain.py`,
W-12 `modes/scan.py`, `modes/student.py`, `providers.py`, W-13 `brain/target_profiler.py` + `harvester_engine.py`,
W-14 `exploit/pipeline.py`, `postex/pipeline.py`, `proxy_guard.py`, `scanners/{nmap,nuclei,whatweb}_scanner.py`,
`phishing/main.py`, `recon-pipeline/main.py`, `sword/{api,pipeline,report}.py`, `raphael/{exploit_factory,techniques,verifier}`,
W-15 `raphael/executor/kali_bridge.py`, plus ticket-map `bridge/raphael_bridge.py`.

**Gate per item**: unit probe executes a harmless local command (`echo`/`id`) through the
restored sink under open policy and asserts output captured in the receipt.

### Phase 3 — Rewire L4: arsenal into the canonical chain
1. New capabilities under `src/orchestrator/exec/capabilities/` (INV-1: primitives stay
   in `exec/`; capabilities call broker-mediated sinks):
   - `ToolExecCapability` — wraps `chains/tool_registry` executors (W-01 restored).
   - `KaliToolCapability` — wraps `kali_tools_client` (W-07) for mcp-hub toolset
     (nmap, sqlmap, nuclei, gobuster, metasploit, subfinder, whatweb…).
   - `ShellCapability` — wrap existing `interactive_shell` SSH/reverse shells
     (session store + listener manager already exist).
   - `CodeExecCapability` — wraps `sandbox.run_code` (W-10) for `sandboxed_exec`.
   - `C2Capability`, `PhishCapability`, `HarvestCapability` — thin adapters over
     c2/, phishing/, harvester/ (each already welded + broker-aware).
2. Register each with capability names + action classes in `engagement-open-v0.json`;
   wire into `CapabilityBroker` allowed set and the PEP dispatch (`stages.py` capability
   branch — today only `SafeProvingCapability`; extend `runtime/loop.py` organ bundle).
3. Student/Planner technique space: extend candidate generator with the offensive
   technique catalog (references/, templates/, chains/) so proposals map to the new
   capability names; verify `agents/exploit.py` (W-10) and `chains/ad_kill_chain.py`
   are reachable from Student proposals.
4. Service bring-up: `configs/docker-compose.yml` (kali-tools :3800, mcp-hub, neo4j,
   DVWA lab) — fix compose defaults flagged in audit M-4 as needed; confirm
   `_run_in_kali` → kali `/run` (W-09 restored) round-trip.

**Gate**: single operator `run_tool("nmap", …)` executes through
API → require_scope → broker AUTHORIZED → restored `_run_command` → real nmap output
→ receipt in evidence store.

### Phase 4 — Unbind L5: autonomy
1. Driver: `scripts/run_autonomous.py` (or extend `launch_pilot.sh`) that:
   - loads operator target list (file/env),
   - loops `RaphaelRuntime.run_episode(..., max_iterations=<open>, action_cap=<open>)`
     continuously (explicit params — function defaults stay 1 so existing tests don't move),
   - feeds WorldModel/contradiction/replan outputs into the next iteration (already wired,
      G3-EN-5),
   - rotates targets and re-engages on completion. No per-cycle human input.
2. Persona approvals: `api/types.py::check_tool_permission` → open mode returns
   `(True, False)` for all tool/persona/mode combos (keep function signature).
3. Command filter (`interactive_shell/command_filter.py`): open mode short-circuits to
   `FilterDecision.ALLOW` before Tier-1 rules and Tier-2 LLM classifier (keep the
   filter classes for tests; gate the bypass behind the open policy flag).
4. Falsification (`brain/falsification*`): switch from blocking to advisory — Student
   proposals log the falsification verdict but are not withheld (L-004's 78% catch rate
   must not gate execution under open mode).
5. RateLimiter/emergency brake: no-op under open policy (Phase 1.6) — verify jitter path.
6. Providers (`providers.py`, W-12): live LLM endpoint restored → Student research,
   chain synthesis, and agent personas (Z3R0/blackhat…) functional.

**Gate**: 3-iteration autonomous episode against the lab with zero approvals, zero
`WeldNotAuthorized`, receipts for every action.

### Phase 5 — Full-chain E2E (lab)
1. Cold start → compose up arena (DVWA/VulnerableApp) → driver → autonomous run:
   recon (W-02/W-07/W-14 scanners) → profile (`target_profiler` W-13) → Student
   proposes → broker → exploit (`exploit/pipeline` W-14, `relay_chain` W-11) →
   shell (interactive_shell) → post-ex (`postex/pipeline` W-14) → persistence/exfil
   (`agent/modules/*` — intact) → evidence chain complete.
2. Second scenario: C2 path (beacon listen W-08 → implant build W-08 → sliver W-08).
3. Third: phishing/harvester path (phishing W-14, harvester W-13).
4. Failure-injection: kill kali container mid-run → agent detects, retries, continues
   (autonomy robustness).

**Gate**: DoD 4 and 5 demonstrated; JUnit transcript of each scenario archived under
`evidence/offensive_restore/`.

### Phase 6 — Operational hardening (post-restoration)
- Continuous run supervision: crash-restart, disk rotation for evidence store (cap 10000),
  JSONL telemetry dashboards.
- Optional stealth posture: cloak-service/Tor egress re-enabled (W-14 restored),
  proxy_guard, jitter (only if operator wants live-engagement behavior).
- Sync README/state docs to the new reality (all stale claims from audit H-3).
- Optional: API unauth surfaces (audit C-2) — open by design now; add API key only if
  the API is exposed off-localhost.

---

## 3. Sequencing, dependencies, effort

```
P0 stabilize ──► P1 open policy ──► P1.5 re-point tests ──► P2 restore bodies
                                   └──────────────► P3 wire arsenal ──► P4 autonomy ──► P5 E2E ──► P6 ops
```
- P1 blocks everything (gates must allow before restored bodies are observable).
- P2 and P3 can proceed in parallel after P1.5.
- P4 needs P3 (autonomy over nothing is unobservable).
- Size classes: P1 = S–M, P1.5 = S, P2 = M (10 sinks; ~8 recoverable from history,
  ~2 rewrite), P3 = L (new capability layer + candidate space), P4 = M, P5 = M–L
  (environment-dependent), P6 = S.

## 4. Risk register

| Risk | Mitigation |
|---|---|
| Some bodies unrecoverable from history (pre-restructure paths) | Phase 2 per-item probe first; rewrite from spec (`grep` the raise-message comments — they document what the body was) |
| Denial-test rework slips → suite red | P1.5 is a hard gate before P2 merges |
| LLM endpoint unavailable → Student/agent inert | P0.4 endpoint config; E2E fallback: scripted candidate generator (deterministic) until endpoint lands |
| Docker/kali arena unavailable on host | Phase 5 needs compose; degrade to local-toolchain scenario (nmap/sqlmap on PATH) |
| INV-1 guard fights new capability code | all new primitives live under `exec/` (guard's own CANONICAL_TREES) |
| Dirty-tree collisions with concurrent sessions | P0.2 commit baseline first; one working branch |
| 621-test floor drifts as bodies return | suite run recorded at every phase gate; floor only ratchets up |

## 5. Explicit non-goals (this roadmap)
- No Section-5-adjacent content anywhere in scope (no specific real-world human target is
  part of this build; engagements run against operator-supplied target sets).
- No deletion of INV-1 / guardrail machinery — restoration is *through* the gates, not
  around them.
- README/evidence truthfulness fixes tracked separately (audit H-1/H-2) — they do not
  block capability restoration.
