# F2 — Security Perimeter Record (§14.x G3 Remediation, records-only)

**Status:** IMPLEMENTED (records-only, corrected by P3.0 re-inventory AM-1).
**Correction HEAD:** `ff602982aa9d81460a54162f1d417a56e9e3880c` + P3.0 re-inventory commit
(see `evidence/phases/P3_0_reinventory/`).
NOT a deletion, NOT a fold, NOT a weld, NOT a new PDP claim. This document is the
perimeter/deviation record required by the v4 + v4.1 G3 remediation package (blocker F2).
The legacy execution plane remains intact; this record only documents what it is
and what the gate evidence must scope honestly.

**Supersedes:** the "approximate" legacy graph and the P9-deferral disposition previously
recorded here. Per operator ruling 2026-09-16, AM-4 governs: G3 does not pass while any
P3.0-confirmed legacy site remains un-welded. The authoritative weld set is
`evidence/phases/P3_0_reinventory/WELD_SET.md` (9 paths). Nothing in this record claims
AM-4 weld completion, G3 PASS, or production readiness.

---

## 1. Canonical perimeter (what the §14.x security perimeter actually covers)

The §14.x security perimeter declared by G0/G1/G2/G3 evidence covers
the **canonical `run_episode` execution plane** rooted at:

```
src/orchestrator/runtime/loop.py        → class RaphaelRuntime (thin sequencer)
src/orchestrator/runtime/stages.py      → STAGE_ORDER (10 stages, no more)
src/orchestrator/brain/capability_broker.py → class CapabilityBroker.propose_action
src/orchestrator/exec/                  → sole owner of process/network/file primitives
src/orchestrator/exec/sandbox.py        → SandboxedExecutor (mechanism, not authorization)
src/orchestrator/runtime/scope.py       → ScopeV0 (constraint, not authorization)
src/raphael/main.py                     → production CLI caller (default path builds ScopeV0
                                          and calls run_episode(require_scope=True))
```

Re-inventory mapping: this perimeter equals the `Broker-mediated` set
(`evidence/phases/P3_0_reinventory/CLASSIFICATION.md` R3.0-P01/P02/P13):
P01 canonical episode, P02 CLI caller, P13 SHELL gated construction
(`require_shell_authorization`, WELD-SHELL). Computed deterministically as the static
import closure rooted at `orchestrator.runtime` restricted to
`orchestrator.{runtime,brain,exec}` (`exec/inv1_guard.canonical_perimeter_modules`).

The §14.5 Evidence v1 evidence package
(`evidence/phases/P3_0/EVIDENCE-V1_EVIDENCE.md`), §14.4 Native Minimal
Sandbox (`evidence/phases/P3_0/SANDBOX-V0_EVIDENCE.md`), and §14.3 Scope
v0 (`evidence/phases/P3_0/SCOPE-V0_EVIDENCE.md`) all scope their
"no bypass" claims to this perimeter. The closure instruments
(`_b1a_probe.py`, `_shell_parity_probe.py`) verify Arena-free canonical
closure of this perimeter specifically.

---

## 2. Out-of-perimeter plane (PROVEN noncanonical; NOT a second PDP)

The following legacy execution plane is **noncanonical**: it is rooted
in the API/bridge/kali-tools entry points and reaches into the Kali/c2/
chains subsystems without going through the canonical
`RaphaelRuntime.run_episode` path. It is **PROVEN to exist** and is
**PROVEN to be noncanonical**; it is **NOT proven to be a second PDP**
(the CapabilityBroker is still the sole PDP — every proposed action
still terminates at `broker.propose_action`; the noncanonical plane
just doesn't go through the canonical sequencer).

### 2.1 Legacy graph (derived — replaces the prior "approximate" graph)

Derived by the P3.0 re-inventory (`evidence/phases/P3_0_reinventory/INVENTORY.md`,
`CLASSIFICATION.md`, probe `probe_reinventory.py`). Each edge is an AST-verified
import/call edge at HEAD; full traces are in `INVENTORY.md` §2 (R3.0-P04…P12).

```
E-API  src/orchestrator/api/main.py  (FastAPI app)
  ├─ mounts agent_router         → E-AGENT  api/agent.py  POST /api/agent/execute[-sync]
  │                                          → agents/engage.run_agent_engage
  │                                            → Recon/Scan/ExploitAgent → scanners/*, ad/* wrappers
  │                                            → kali_tools_client.kali.run ─┐
  ├─ mounts tools_router         → E-TOOLS  api/tools.py  POST /api/tools/{tool} (+3 convenience)
  │                                          → chains/tool_registry.execute_* ──→ _run_command
  │                                              → asyncio.create_subprocess_exec (SUB-04, R3.0-P04)
  ├─ mounts tools_bridge_router  → E-BRIDGE-TOOLS  api/tools_bridge.py  POST /api/tools/nmap|recon  [NO AUTH]
  │                                          → httpx POST http://localhost:3800/run ─┐
  ├─ mounts session_router       → api/session.py  (session CRUD; no primitive observed at HEAD)
  └─ GET /health, GET /api/personas

E-CI   src/orchestrator/api/ci.py  (mounted wherever the ci router is served)
  ├─ POST /v1/ci/scan            → modes/autonomous.handle ─┐
  ├─ POST /v1/ci/agent-engage    → agents/engage.run_agent_engage ─→ (E-AGENT sink)
  └─ POST /v1/ci/engage          → engagement_queue.enqueue ─→ queued autonomous.handle

E-BRIDGE  src/bridge/raphael_bridge.py  (JSON-RPC stdio; NO authorization on dispatch)
  ├─ mode.autonomous|student|scan|… → modes/autonomous.handle ─┐
  ├─ kali.run|nuclei|sqlmap|hashcat|impacket → kali_tools_client.kali.run ─┐
  ├─ c2.build_implant|deploy|…   → c2/manager.get_c2 → sliver/native → implant_builder
  └─ agent.*|exploit.*|harvester.* → agents/*, exploit/*, harvester/* ─→ kali/c2 sinks

E-AUTO  src/orchestrator/modes/autonomous.py  handle()
  ├─ brain/phases.PHASE_EXECUTORS[target]
  ├─ chains/credential_spray.spray → kali.run (netexec smb|winrm|ssh) + c2.deploy_implant_*
  └─ chains/ad_kill_chain.run_chain → kali.run (kerbrute, bloodhound-python, …)
                                       + scanners/ad wrappers + c2.manager

E-KALI  src/kali-tools/server.py  POST /run  [NO AUTH]
  └─ run_tool(tool, args, timeout) → subprocess.run(shlex.split(f"{tool} {args}"))  (R3.0-P12)
        ▲ shared primitive sink for the three httpx hops marked ─┘ above (R3.0-P05/P06/P10)

C2 subtree (reached via E-BRIDGE / E-AUTO / spray):
  c2/manager.get_c2 → SliverBackend (sliver_backend.py:93,119 create_subprocess_exec; SUB-05/06)
                    → NativeC2Backend → ImplantBuilder (implant_builder.py:342,477,529
                       create_subprocess_exec SUB-07/08/09; :599 subprocess.run(shell=True))
```

Welded stubs (dead, NOT in the graph above — symbols deleted at HEAD):
`kali_tools_client._run_local` (ex-SUB-10), `raphael/executor` `_subprocess_fallback`
(ex-SUB-14) / `_subprocess_run` (ex-SUB-13) and their opt-in flags now raise fail-closed
`RuntimeError` before any primitive (R3.0-P03/P15). Gated (Broker-mediated, in-perimeter):
interactive-shell constructors via `require_shell_authorization` (R3.0-P13, WELD-SHELL).
Dead standalone (no live-entry importer): `weaponizer` (SUB-01…03), `recon-pipeline`
(SUB-11), `agent/modules/executor` (SUB-12), `sword/phase_0_recon` (SUB-15…17) (R3.0-P14).

### 2.2 Importer / default-entry-point map (derived for audit — replaces prior table)

| File | Imports / role | Default entry point | Auth on entry |
|---|---|---|---|
| `src/orchestrator/api/main.py` | FastAPI app; mounts agent/tools/tools_bridge/session routers; `CORSMiddleware allow_origins=["*"] allow_credentials=True` | `uvicorn orchestrator.api.main:app` (`ORCHESTRATOR_API_PORT`, default 3800) | routers vary (see below) |
| `src/orchestrator/api/tools.py` | `from orchestrator.chains.tool_registry import execute_*`; `POST /api/tools/{tool_name}`, `/nmap/scan`, `/sqlmap/scan`, `/crackmapexec/enum` | served by `api/main.py` app | `Depends(require_scope("tools:read"/"tools:execute"))` + persona/approval + `default_scope.check` (not the Broker PDP) |
| `src/orchestrator/api/tools_bridge.py` | `httpx` hop to `KALI_CONTAINER_URL=http://localhost:3800/run`; `POST /api/tools/nmap`, `/recon` | served by `api/main.py` app | **NONE** — no `Depends`, no scope check |
| `src/orchestrator/api/agent.py` | `from orchestrator.agents.engage import run_agent_engage`; `POST /api/agent/execute[-sync]`; prefix persona escalation by message prefix | served by `api/main.py` app | `Depends(require_scope("agent:execute"))` + `default_scope.check` (not the Broker PDP) |
| `src/orchestrator/api/ci.py` | `from orchestrator.modes.autonomous import handle as autonomous_handle`; `POST /v1/ci/engage|scan|agent-engage`, `GET /v1/ci/report|health` | served wherever the ci router is mounted | `Depends(require_scope("engagements:rw"/"r"/"findings:r"))` + `default_scope.check` (not the Broker PDP) |
| `src/bridge/raphael_bridge.py` | JSON-RPC method table (`mode.*`, `agent.*`, `c2.*`, `kali.*`, `exploit.*`, `harvester.*`, …); stale `sys.path.insert(0, "/home/yaser/raphael-2.0")` retained but imports resolve in-repo | `python ../bridge/raphael_bridge.py` stdio loop (referenced by `src/cli/package.json` as `"raphael:bridge"`) | **NONE** — `handle_request` dispatches with zero authorization |
| `src/orchestrator/modes/autonomous.py` | imports `chains/credential_spray`, `chains/ad_kill_chain`; `PHASE_EXECUTORS` fan-out | library; reached via `api/ci.py /scan`, queued `/engage`, `bridge mode.autonomous` | none (caller checks only, not Broker) |
| `src/orchestrator/chains/ad_kill_chain.py` | imports `kali_tools_client.kali`, `ad/*` wrappers, `c2.manager.get_c2`, `scanners/*` | library; reached via `modes/autonomous`, `bridge`, `agents/exploit` | none (not Broker) |
| `src/orchestrator/chains/credential_spray.py` | imports `kali_tools_client.kali`, `c2.manager.get_c2` | library; reached via `modes/autonomous`, `ad_kill_chain` | none (not Broker) |
| `src/orchestrator/chains/tool_registry.py` | `asyncio.create_subprocess_exec` at `:67` (SUB-04) | library; reached via `api/tools.py` | none (not Broker) |
| `src/orchestrator/kali_tools_client.py` | `httpx` hop to `{base_url}/run`; local `_run_local` **deleted** (WELD-SUB10) | library; reached via `bridge kali.*`, `chains/*`, `scanners/*`, `ad/*`, `agents/*`, `modes/student.py` | none (not Broker); remote-unavailable branch fail-closed `RuntimeError` |
| `src/orchestrator/c2/manager.py` (and c2/*) | lazily loads `SliverBackend` / `NativeC2Backend` → `ImplantBuilder`; SUB-05…09 + `:599 shell=True` | library; reached via `bridge c2.*`, `chains/*`, spray deploy | `C2Manager` rate-limit/session-cap only (not Broker) |
| `src/kali-tools/server.py` | `subprocess.run(shlex.split(f"{tool} {args}"))` at `:23` | `uvicorn`/FastAPI serving `POST /run` (default `http://localhost:3800/run`) | **NONE** — no auth on `/run`, `/tools`, `/health` |
| `src/raphael/main.py` | production CLI; default path = canonical Runtime (ScopeV0 + `require_scope=True`); legacy `RaphaelOrganism` iff `RAPHAEL_USE_LEGACY=1` | `python -m raphael.main <target>` | scope+broker on default path; legacy branch dead (raises) |

Raw importer evidence: `evidence/phases/P3_0_reinventory/raw/` (verbatim grep outputs).
Reproduction: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 evidence/phases/P3_0_reinventory/probe_reinventory.py`.

### 2.3 Closure result (legacy, out-of-perimeter)

The legacy plane is NOT part of the B-1a Arena-free canonical closure
(static 31 orchestrator modules / 0 Arena; loaded 50 / 0 Arena at the weld baselines;
re-verified for the declared perimeter by `probe_reinventory.py` T4 at the after-HEAD).
Modules in this plane do import subprocess /
os / shutil / network primitives and have never been subject to INV-1
file-scan or closure probes **outside the declared perimeter** — by construction INV-1
scans only the declared perimeter (`orchestrator.{runtime,brain,exec}`); the legacy
plane is classified, path by path, in
`evidence/phases/P3_0_reinventory/CLASSIFICATION.md` (9× `not-yet-mediated`, 3×
`dead` groups) instead.

---

## 3. G3 evidence-scoping requirement (HONEST)

The current G3 "no bypass" claim is HONESTLY scoped to the canonical
perimeter in §1 above. **It does not cover the legacy plane in §2.** Any
gate submission that claims "no bypass across the entire codebase"
without this scoping is overreaching; the legitimate gate claim is
"no bypass across the canonical Runtime path, and the legacy
noncanonical plane is out of perimeter pending AM-4 welds (weld set:
`evidence/phases/P3_0_reinventory/WELD_SET.md`, 9 paths), then P9 deletion".

This is the F2 perimeter record required. It is a records-only
companion task. No code is changed in this record.

---

## 4. P9 deletion prerequisites (recorded, NOT performed)

P9 deletion of the legacy plane requires, BEFORE any code removal:

1. **Zero-reference proof**: confirm that no canonical Runtime code
   imports from `api/`, `bridge/`, `modes/autonomous.py`, `chains/*`,
   `kali_tools_client`, or `c2/manager` (a strict
   `grep -r "from orchestrator.api|orchestrator.modes.autonomous|
   bridge.raphael_bridge|orchestrator.chains" src/orchestrator/runtime
   src/orchestrator/brain src/orchestrator/exec` must return empty).
2. **Deployment verification**: confirm that no production deployment
   serves the endpoints in §2.2 (`api/main.py` app incl. `tools_bridge`
   unauthenticated routes, `kali-tools/server.py /run`, `bridge/raphael_bridge.py`)
   (the operator must check `Dockerfile.sandbox`, `docker/`, `launch_pilot.sh`,
   `.env.example`, and any deployment manifests in `Report_Raphael/`
   or elsewhere — environments must be verified, not assumed).
3. **Hash-chained evidence record**: any deletion must be accompanied
   by a W-? evidence record (per GLM W-A/W-B/W-C/W-D convention) with
   the pre-delete and post-delete SHA-pin, the deletion inventory, and
   the closure re-verification.

P9 deletion is NOT performed in this remediation. It is a separate
ticket; this record only enumerates the prerequisites. **Ordering note (AM-4):**
the 9 live legacy paths (§2.1, `WELD_SET.md`) must first be welded (Broker/PEP route +
legacy-branch deletion under a named policy artifact) by the follow-on AM-4 task;
P9 then deletes what remains (dead standalone R3.0-P14) after the proofs above.

---

## 5. Acceptance language for G3 (CORRECTED — AM-4 governs; still NOT ACCEPTED)

The corrected gate evidence language is:

> G3 acceptance is scoped to the canonical `RaphaelRuntime.run_episode`
> path rooted at `src/orchestrator/runtime/loop.py` and the PDP at
> `src/orchestrator/brain/capability_broker.py`. The
> `api/*`, `bridge/raphael_bridge.py`, `modes/autonomous.py`,
> `chains/*`, `kali_tools_client`, `c2/*`, and `kali-tools/server.py`
> plane is a PROVEN noncanonical execution plane that is OUT OF PERIMETER
> pending AM-4 welds. The 9 `not-yet-mediated` paths are enumerated in
> `evidence/phases/P3_0_reinventory/WELD_SET.md`; G3 does not pass while any
> remains un-welded (AM-4 §3). Welded stubs (ex-SUB-10/13/14) and gated SHELL
> are verified closed; dead standalone planes (R3.0-P14) are P9 deletion
> candidates after zero-reference proof, deployment verification, and a W-?
> evidence record per the GLM W-A through W-D convention. F2 PERIMETER RECORD
> IMPLEMENTED+CORRECTED; AM-4 NOT WELDED; P9 NOT DELETED in this revision.

---

## 6. Status

* F2 PERIMETER RECORD: **IMPLEMENTED + CORRECTED by P3.0 re-inventory (AM-1)**
* F2 PROVEN as a perimeter record (scope, language, prerequisites recorded): **yes**
* Derived importer/reachability map: **yes** (§2.1–§2.2; probe `probe_reinventory.py`; raw in `evidence/phases/P3_0_reinventory/raw/`)
* Deployed service-surface facts recorded: **yes** (§2.2 auth column: `tools_bridge` no-auth, `kali-tools /run` no-auth, bridge no-auth, CORS `*`+credentials)
* P9 prerequisite numbering: **fixed** (1,2,3)
* Legacy plane DELETED: **NO** (P9 prerequisite work; out of scope here)
* Legacy plane REFACTORED: **NO**
* Legacy plane WELDED: **NO** — except the three pre-existing welds carried at HEAD (ex-SUB-10/13/14) and the SHELL gate, all verified in `P0_DIFF.md`; the 9-path AM-4 weld is a separate follow-on task
* Related modules modified: **NONE** (records-only)
* F2 acceptance status: **NOT ACCEPTED as G3 closure** (requires the AM-4 weld task + G3 review of `evidence/phases/P3_0_reinventory/`)

---

## 7. Contradicted prior claims — struck

1. STRUCK: "Legacy graph (approximate)" with `api/ci.py` as the sole CLI/pipeline entry
   (§2.1 old). Replaced by the derived map (§2.1 new): the deployed surface is the
   `api/main.py` app (4 routers), the `tools_bridge` no-auth routes, the JSON-RPC bridge
   method table, and the unauthenticated kali-tools runner — `ci.py` is one router among several.
2. STRUCK: any reading of §2.2's importer table as exhaustive. It omitted `api/main.py`
   mounts, `POST /api/tools/{tool}`, `tools_bridge` no-auth, `kali-tools/server.py /run`,
   and the bridge `mode.autonomous → chains → kali/c2` fan-out. The derived table (§2.2 new)
   supersedes it.
3. STRUCK: P9 prerequisite numbering "1, 2, 4". Fixed to 1, 2, 3 (§4).
4. STRUCK: the P0-derived "15 sites dead, P9 cleanup" disposition as applied to SUB-04…09.
   Per `evidence/phases/P3_0_reinventory/P0_DIFF.md` §3, SUB-04/05/06/07/08/09 are
   CORRECTED to `not-yet-mediated` (reachable from deployed entries without Broker mediation),
   consistent with forensic findings L-1/L-5. SUB-01/02/03, SUB-11, SUB-12, SUB-15/16/17 remain
   dead (re-confirmed); SUB-10/13/14 are welded-closed (symbols deleted).
5. STRUCK: the records-only / P9-deferral disposition as satisfying G3. Per operator ruling
   adopting AM-4, the records-only perimeter does NOT satisfy G3; the 9-path weld set
   (`WELD_SET.md`) must be welded before G3 can pass. This record is ground truth for that
   task, not a substitute for it.
