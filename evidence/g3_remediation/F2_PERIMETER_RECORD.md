# F2 — Security Perimeter Record (§14.x G3 Remediation, records-only)

**Status:** IMPLEMENTED (records-only). NOT a deletion, NOT a fold, NOT a
new PDP claim. This document is the perimeter/deviation record required
by the v4 + v4.1 G3 remediation package (blocker F2). The legacy
execution plane remains intact; this record only documents what it is
and what the gate evidence must scope honestly.

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
```

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
in the API/bridge/cli entry points and reaches into the Kali/c2/
chains subsystems without going through the canonical
`RaphaelRuntime.run_episode` path. It is **PROVEN to exist** and is
**PROVEN to be noncanonical**; it is **NOT proven to be a second PDP**
(the CapabilityBroker is still the sole PDP — every proposed action
still terminates at `broker.propose_action`; the noncanonical plane
just doesn't go through the canonical sequencer).

### 2.1 Legacy graph (approximate)

```
api/ci.py                        → CLI / pipeline entry point
bridge/raphael_bridge.py         → IPC bridge to a downstream UI process
        │
        ▼
modes/autonomous.py              → autonomous-mode orchestrator (CLI-internal)
        │
        ▼
chains/ad_kill_chain.py          → AD attack-chain driver
chains/credential_spray.py       → credential-spray driver
chains/tool_registry.py          → legacy tool lookup
        │
        ▼
kali_tools_client / c2.manager   → legacy primitives (subprocess, network, file)
```

### 2.2 Importer / default-entry-point map (recorded for GLM audit)

| File                                          | Imports / role                                | Default entry point |
|-----------------------------------------------|-----------------------------------------------|---------------------|
| `src/orchestrator/api/ci.py`                  | legacy CI entry point                          | `python -m orchestrator.api.ci` |
| `src/bridge/raphael_bridge.py`                | JSON-RPC bridge to TS/Node UI                  | `python ../bridge/raphael_bridge.py` (referenced by `src/cli/package.json` as `"raphael:bridge"`) |
| `src/orchestrator/modes/autonomous.py`        | autonomous-mode driver                         | legacy CLI driver   |
| `src/orchestrator/chains/ad_kill_chain.py`    | AD attack chain                                | library only        |
| `src/orchestrator/chains/credential_spray.py` | credential spray                               | library only        |
| `src/orchestrator/chains/tool_registry.py`    | tool lookup                                   | library only        |
| `src/orchestrator/kali_tools_client.py`       | Kali-tools client (subprocess)                 | library only        |
| `src/orchestrator/c2/manager.py` (and c2/*)   | c2 subsystem                                   | library only        |

Verified by `grep -rln "raphael:bridge|raphael_bridge|api/ci|chains/ad_kill_chain|chains/credential_spray" src cli` (raw grep output preserved in
`evidence/g3_remediation/import_graph_legacy.txt`).

### 2.3 Closure result (legacy, out-of-perimeter)

The legacy plane is NOT part of the B-1a Arena-free canonical closure
(static 34/0, loaded 53/0). Modules in this plane do import subprocess /
os / shutil / network primitives and have never been subject to INV-1
file-scan or closure probes.

---

## 3. G3 evidence-scoping requirement (HONEST)

The current G3 "no bypass" claim is HONESTLY scoped to the canonical
perimeter in §1 above. **It does not cover the legacy plane in §2.** Any
gate submission that claims "no bypass across the entire codebase"
without this scoping is overreaching; the legitimate gate claim is
"no bypass across the canonical Runtime path, and the legacy
noncanonical plane is out of perimeter pending P9 deletion".

This is the F2 perimeter record GLM required. It is a records-only
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
   serves `api/ci.py` or `bridge/raphael_bridge.py` (the operator
   must check `Dockerfile.sandbox`, `docker/`, `launch_pilot.sh`,
   `.env.example`, and any deployment manifests in `Report_Raphael/`
   or elsewhere — environments must be verified, not assumed).
4. **Hash-chained evidence record**: any deletion must be accompanied
   by a W-? evidence record (per GLM W-A/W-B/W-C/W-D convention) with
   the pre-delete and post-delete SHA-pin, the deletion inventory, and
   the closure re-verification.

P9 deletion is NOT performed in this remediation. It is a separate
ticket; this record only enumerates the prerequisites.

---

## 5. Acceptance language for G3 (PROPOSED — pending GLM ruling)

The proposed gate evidence language is:

> G3 acceptance is scoped to the canonical `RaphaelRuntime.run_episode`
> path rooted at `src/orchestrator/runtime/loop.py` and the PDP at
> `src/orchestrator/brain/capability_broker.py`. The legacy
> `api/ci.py`, `bridge/raphael_bridge.py`, `modes/autonomous.py`,
> `chains/*`, `kali_tools_client`, and `c2/manager` plane is a PROVEN
> noncanonical execution plane that is OUT OF PERIMETER pending P9
> deletion. The P9 deletion is gated on zero-reference proof,
> deployment verification, and a W-? evidence record per the GLM W-A
> through W-D convention. F2 PERIMETER RECORD IMPLEMENTED; P9 NOT
> DELETED in this revision.

This language must be reviewed and ACCEPTED by GLM before being
incorporated into any G3 evidence package.

---

## 6. Status

* F2 PERIMETER RECORD: **IMPLEMENTED**
* F2 PROVEN as a perimeter record (scope, language, prerequisites recorded): **yes**
* Legacy plane DELETED: **NO** (P9 prerequisite work; out of scope here)
* Legacy plane REFACTORED: **NO**
* Related modules modified: **NONE** (records-only)
* F2 acceptance status: **NOT ACCEPTED** (requires GLM ruling)