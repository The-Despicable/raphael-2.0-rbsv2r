# M3 / D2 DESIGN FREEZE & AUTHORIZATION PACKAGE — 2026-10-04

**Status: DESIGN READY FOR OPERATOR REVIEW** — design only. Nothing implemented,
activated, authorized, or tested as D2. No production source, runtime behavior,
capability, or active policy was modified. The single file this task created is
this report.

---

## 1. Current baseline (direct observations, this audit)

| Item | Observed |
|---|---|
| Branch / HEAD | `offensive-restore` / `e6a8c707e` — matches all prior reports |
| Worktree | 70 modified/untracked entries (M0→M2.1 work + `reports/`); all preserved; nothing committed |
| Python | `.venv` = 3.12.15 |
| Policies on disk | `bootstrap-v0.json` (restrictive control / kill switch), `engagement-d1-v1.json` (**the only active policy**), `engagement-open-v0.json` (unwired). **No `engagement-d2*` artifact exists** and none was created |
| D1 policy integrity | sha256 `777999a3c8d5b817…` — byte-identical to the M2 record |
| D1 guarantees | `tests/test_m2_d1_governed_action.py` **23/23 pass** (broker-authorizes-before-PEP, denied ⇒ zero capability invocations ⇒ zero subprocess spawns via spy, kill-switch swap denies, CONV-3 gating, malformed-policy fail-closed, receipt/artifact binding) |
| Evidence | M0 baseline manifest unchanged (sha256 `d4630af3de835bb6…`); all four D1 demo transcript dirs intact (`163946Z`, `164000Z`, `164502Z`, `172731Z`) |
| Lab | dvwa / kali-tools / dvwa-db running, loopback-only, per M2.1 |

## 2. Endpoint execution-context analysis (Action B)

The entry-gate proposal wrote `http://127.0.0.1:4280/`. **That address is
context-dependent and must not be assumed.** Resolution from configuration and
existing evidence only (no HTTP request was made for this analysis):

**Where the capability process would run.** Following the D1 pattern
(`exec/capabilities/d1_lab_probe.py`), an Action-B capability runs **in-process
on the host** (inside the Runtime) and, like D1, may execute a fixed argv inside
the `kali-tools` container. Two candidate execution contexts exist:

| Context | What `127.0.0.1` means there | Does `dvwa` resolve? | Endpoint that reaches ONLY DVWA |
|---|---|---|---|
| **Host (Runtime process)** | The host loopback → reaches whatever is bound to `127.0.0.1:4280`, which is dvwa **only while** the hardened mapping (`127.0.0.1:4280→80`, verified in rendered compose and live `docker ps`) exists | Not a docker-DNS name on the host | `http://127.0.0.1:4280/` — but ONLY after binding the mapping to the verified container identity (inspect `NetworkSettings.Ports` = `127.0.0.1:4280→80`) |
| **In-container (`docker exec kali-tools …`)** | **kali-tools' own loopback — i.e. the wrong target.** `127.0.0.1` must be explicitly prohibited in this context | **Yes** — docker DNS on the shared compose network; demonstrated by existing D1 evidence (nmap inside kali resolved `dvwa (172.19.0.4)`, `80/tcp open http`) | `http://dvwa/` (fixed constant, port 80) — resolves only on `raphael-m1_raphael-net`, which contains only lab services |

**Decision (narrowest fixed, deterministic endpoint): Action B executes
in-container and targets the fixed constant `http://dvwa/`.** Rationale:

1. **No host-network dependence at all** — it works with zero published ports;
   reachability is structurally limited to the compose network, which contains
   only lab services.
2. **Identity-bound by construction** — `dvwa` resolves only on the shared
   network; the capability re-verifies identity before dispatch exactly like D1
   (both containers Running, dvwa image prefix `vulnerables/web-dvwa`, shared
   network set non-empty), and refuses any other target.
3. **Client constraints are enforceable in fixed argv**: `curl --max-redirs 0`
   (redirects are never followed — a 302 is recorded as metadata),
   `--max-time 60` (bounded), `--max-filesize 65536` (bounded body), plain GET
   (no `-X`, no `-d`, no headers beyond defaults). `curl` is present in the
   kali image (Dockerfile apt list).
4. The host-loopback alternative (`http://127.0.0.1:4280/`) is documented as
   **considered and not selected**: it is valid only for a host-context
   capability and would additionally require binding the endpoint to the
   verified container's port mapping each run. If the operator prefers the
   host context, that binding requirement becomes mandatory design text.

**Expected behavior (from existing evidence, not a new request):** the M1/M2.1
smoke checks have long observed `GET / → 302 → /login.php` on the published
mapping; the in-container GET is expected to observe the same DVWA redirect.
**Implementation-time local verification required (standard acceptance, not a
design blocker):** the first Action-B implementation run must confirm the
captured response metadata (status 302, `Location: /login.php`, body digest)
against this expectation. If, at implementation time, the in-container GET
cannot be proven to reach only the verified DVWA container, Action B is
**excluded from implementation until separately resolved** — per the task
order.

## 3. Proposed D2 action contract

### Action A — existing D1 service probe (reused unmodified)
Capability `exec.d1_lab_probe`; fixed argv `docker exec kali-tools nmap -Pn -sT
-p 80 --host-timeout 45s dvwa`; existing live identity validation; no new
arguments. Purpose: port/service evidence for the planner.

### Action B — proposed fixed HTTP probe (design only)
New capability `exec.capabilities.d1_http_probe`-class (naming at
implementation), in-container per §2. Captures **bounded response metadata
only**: status code, `Content-Type`, final-URL-after-no-redirects, body
**sha256 + size** (digest, not content). No credentials, no form posts, no
sensitive application content in evidence. Purpose: HTTP-layer evidence so the
planner has two distinct evidence modalities.

### Proposed episode limits (for operator review) and their enforcement

| Limit | Value | Enforced by | New component needed? |
|---|---|---|---|
| Steps per episode | 5 | `RaphaelRuntime.run_episode(max_iterations=5, action_cap=5)` — explicit params exist; defaults stay 1 | **No** |
| Actions per minute | 6 | `BrokerPolicy.max_actions_per_minute` field exists, but the broker's `rate_limiter` is **unbound by default** (`propose_action` applies it only when wired) | **Partially** — wire the existing `brain/rate_limiter.py` component onto the D2 broker at implementation, or driver-side pacing; either is bounded, no new mechanism |
| Concurrency | 1 | `max_concurrent=1` policy dimension + the Runtime is inherently sequential (one loop, synchronous stage order) | **No** |
| Per-action timeout | 90 s | Action A: existing `TIMEOUT_SECONDS=90`. Action B: `curl --max-time 60` + subprocess timeout ≤ 90 s | **No** (capability-local constant, part of B's reviewed implementation) |
| Result artifact size | 64 KiB | Action A: existing `MAX_OUTPUT_BYTES=65536`. Action B: `--max-filesize` + same constant; evidence_v1 additionally caps records (`MAX_RECORD_BYTES`) | **No** |

### Authorization and evidence flow (all preserved, nothing new invented)

```text
mission (deterministic candidates, ScopeV0 d2-lab scope)
  → stage_broker: CapabilityBroker.propose_action (sole PDP)
       ALLOW  → scope.covers() conjunction → AUTHORIZED receipt (decision_id)
       DENY   → denial receipt (reason; NO execution fields) → halt rule §4
  → stage_pep: AUTHORIZED→STARTED→exec capability→SUCCEEDED/FAILED (truthful)
  → stage_receipt: EvidenceReceipt(event, decision_id, broker_receipt_id,
       scope_hash, argv, artifact_refs)
  → evidence_v1 store: ExecutionResult / Artifact / Finding records
  → stage_replan: fires only on receipted evidence (denial feedback /
       reconciliation), never on model assertions
```

- **Observation / ExecutionResult / Artifact / Finding** map to the canonical
  objects: `stage_observe` output; `EvidenceRecord.execution_result`;
  `EvidenceRecord.artifact` (relpath + sha256 + execution_ref);
  `EvidenceRecord.finding` (requires `derived_from` parents — a Finding cannot
  exist without recorded evidence, by constructor contract).
- **Halt responses**: broker denial of a required action → episode halts at the
  broker stage (denial feedback recorded); tool failure/timeout → truthful
  FAILED terminal receipt, step budget consumed; missing evidence for a claimed
  outcome → halt (Finding construction fails closed without parents);
  contradictory evidence → canonical contradiction stage (both sides immutable),
  not silent discard; identity mismatch → capability refuses (D1LabProbeError-
  class) before any network/exec; kill-switch activation → decision source is
  `bootstrap-v0` ⇒ every request denied at the broker stage, zero spawns.
- **Denied attempts**: denial receipts are persisted (attempt-level
  accountability); the spy assertion (zero capability invocations, zero process
  spawns) extends per-step.
- **Non-authority**: the Planner proposes only; the evidence store records only
  (never authorizes); the Student is recording-only; no component can modify
  policy. One Runtime, one loop, one Broker, one PEP — no second anything.

## 4. Test matrix (design; no tests added or changed by this task)

| # | Test | Expected | Invariant protected | Proving artifact |
|---|---|---|---|---|
| T1 | D1 probe episode (reuse) | AUTHORIZED → SUCCEEDED → linked receipt + digest-verified artifact | canonical ordering, INV-2 linkage | demo transcript + evidence_store.jsonl |
| T2 | Action-B episode (implemented) | AUTHORIZED → SUCCEEDED, metadata + body digest only | bounded capture; no content exfiltration | same |
| T3 | Wrong target (`example.invalid`) | DENIED at broker; no PEP output | exact-match scope | test + spy counter |
| T4 | Wrong action (`tool_execute`) | DENIED (also explicitly prohibited) | allowlist deny-by-default | test |
| T5 | Wrong capability (`chains.tool_registry`) | DENIED | capability allowlist | test |
| T6 | Malformed/missing/stale policy | `PolicyLoadError`, no broker | fail-closed loading | loader unit tests (exist for D1; extended for D2 artifact) |
| T7 | Kill-switch swap | every request DENIED at broker stage | one-file revert to deny-all | demo phase + test |
| T8 | Scope validation failure | DENIED at scope conjunction before PEP | scope is not authorization; conjunction | test |
| T9 | Every denial: zero capability calls, zero spawns | spy delta = 0; invocation_count unchanged | denied ≠ executed | spy instrumentation per step |
| T10 | Timeout (`--max-time` breached) | truthful FAILED receipt, no fabricated success | failed ≠ succeeded | transcript + receipt status |
| T11 | Oversized response (>64 KiB) | truncated/capped artifact + recorded size, digest of stored bytes | bounded artifacts | artifact record |
| T12 | Redirect attempt (302) | recorded as metadata; never followed | containment against bounce | response metadata in artifact |
| T13 | Unexpected target identity (image/network mismatch) | capability refuses pre-dispatch | identity binding | capability error path test |
| T14 | Failed action | FAILED receipt; NO Finding derived from it | failed ≠ finding | evidence store graph |
| T15 | Replan consumes only receipted evidence | replan trigger references existing record identities | evidence-backed replanning | stage outputs + store parents |
| T16 | Contradictory evidence | contradiction recorded (both sides immutable) | no silent discard | contradiction stage output |
| T17 | Episode limits (6th action attempt) | episode terminated by action_cap/iteration bounds | bounded autonomy | LoopTermination record |
| T18 | D1 + guardrail + weld tests | unchanged and green | no regression, no weakened assertions | full suite run |

## 5. Unresolved technical issues (reported, not repaired)

1. **Rate-limit wiring** — the broker's rate-limiter component exists but is
   unbound; D2 implementation must wire it (or pace in the driver) for the
   6/min limit to be real rather than nominal.
2. **Action-B capability does not exist** — this design is the specification;
   implementation is a later, separately authorized task.
3. **Sword drift (DR-001)** and the 18 structural import failures — unchanged,
   deferred; no D2 dependency.
4. **Replan-trigger re-base (v2 F7 note)** — under a fully-open policy the
   current `DenialClass.PERSISTENT` trigger never fires; under the bounded D2
   policy denials still occur (wrong-target etc.), so the existing trigger
   remains meaningful for D2. Any broader future policy must revisit this.

## 6. Operator decision checklist (separate, non-fungible decisions)

- [ ] **A. Credential rotation** — revoke/replace the five exposed keys at the
  provider; confirm with replacement fingerprints. **Still
  `BLOCKED — OPERATOR ACTION REQUIRED`.** M3/D2 design runs without a provider
  regardless.
- [ ] **B. Model strategy** — default: **deterministic, no-provider D2
  episodes** (proven path). Live LLM calls are excluded from this design and
  require a separate authorization after A and demonstrated endpoint readiness.
- [ ] **C. D2 scope authorization** — approve/amend/reject §3 (action set,
  limits, endpoint decision, halt semantics). Until explicit approval, the D2
  contract is `NOT AUTHORIZED` and no `engagement-d2-v1.json` may be created.
- [ ] **D. Holdout dataset** — choose: (i) recover the original
  `rbs_v4_holdout.jsonl` and verify SHA-256 `2bf614f8…586b4`, or (ii) formally
  amend `rbs_v4_reproducibility_manifest.json` through the governed process.
  Fabricating data or hashes is prohibited. This blocks evaluation-baseline
  claims, not D2 execution.
- [ ] **E. Commit authorization** — the M0→M2.1 worktree (70 entries) remains
  uncommitted; a commit decision is independent of A–D and needed before the
  history grows further.

## 7. Files inspected and commands executed

**Inspected (read-only):** `policies/{engagement-d1-v1,bootstrap-v0}.json`;
`src/orchestrator/runtime/{policy,stages,loop,scope,types,organs}.py`;
`src/orchestrator/brain/capability_broker.py`; `src/orchestrator/exec/
{capabilities/d1_lab_probe.py,safe_capability.py,evidence_store.py}`;
`src/orchestrator/runtime/evidence_v1.py`; `src/kali-tools/Dockerfile`;
`configs/docker-compose.yml` (rendered via `config --format json`);
`scripts/run_demo_d1.py`; `tests/test_m2_d1_governed_action.py`;
`evidence/DEFECT_REGISTER.md`; prior reports (M0/M1/M2/M2.1/entry-gate).

**Executed:** `git branch/rev-parse/status`; `sha256sum
policies/engagement-d1-v1.json` (integrity vs M2 record);
`pytest tests/test_m2_d1_governed_action.py -q` (23 passed);
`ls policies/engagement-d2*` (absent — none created); evidence-manifest and
transcript-dir listing (intact). No HTTP request, no provider call, no docker
state change, no file outside this report modified.

## 8. Distinction: current implementation vs proposed design vs verified behavior

| Layer | State |
|---|---|
| **Current implementation** | D1 single-action governed probe (policy, loader, capability, demo, 23 tests) — all verified repeatedly |
| **Proposed design (this document)** | D2 two-action bounded episode (Action A reused unmodified; Action B specified: in-container fixed GET `http://dvwa/`, metadata+digest only), 5-step limits, halt semantics, test matrix |
| **Verified behavior** | D1 path end-to-end incl. real execution and real denials; canonical stage contracts (broker→scope→PEP→receipt→evidence) exercised; deterministic no-LLM episode driving proven; docker-DNS `dvwa` resolution and DVWA `80/tcp open` proven inside kali (D1 evidence); DVWA 302 behavior proven on the published mapping (smoke evidence) |
| **Not yet verified (by design)** | Action-B HTTP capture behavior (first implementation run); rate-limiter wiring effect; any multi-episode replay at the 5-step bound |

## 9. Final status

**`DESIGN READY FOR OPERATOR REVIEW`.** The endpoint ambiguity is resolved
(in-container `http://dvwa/`; `127.0.0.1` explicitly prohibited in that
context), the contract is complete and bounded, and every enforcement mechanism
is either existing or a bounded capability-local constant. D2 remains
**NOT AUTHORIZED** until the operator closes checklist items A–E as applicable —
minimum: C (scope authorization) to implement, A (rotation) before any live
provider work, D before evaluation-baseline claims.
