# ADR-011 — `orchestrator/sandbox/` is Mechanisms-Only, Not the Authorization Boundary

| Field | Value |
|---|---|
| ADR | 011 |
| Phase | P1.0 → P1.1 transition (P0 baseline `7272880f7`, P1.0 pre-migration `raphael-p1-pre-migration-7272880f`) |
| Status | Accepted (per GLM correction C5) |
| Deciders | Implementation lane + GLM gate lane |
| Date | 2026-09-04 |
| Source | v4.1 master roadmap §5.2 (capability/sandbox below broker), §9 (Decepticon placement), AM-4 (seam discipline) |
| Authority | GLM correction C5 (P1 implementation authorization) |

## Context

The canonical checkout at `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` has three sandbox-related files at `src/orchestrator/runtime/`:

- `caido_bootstrap.py` — `CaidoProxy` class (130 LOC)
- `docker_client.py` — `DockerSandbox` class (132 LOC)
- `session_manager.py` — `SandboxSession` class (116 LOC, depends on the other two)

These are the *mechanisms* used to run an isolated capability execution environment: a Docker container plus a Caido HTTP-interception proxy. They live below the capability layer (which itself is below the broker).

The orphan Phase 1+2 work in `git stash@{4}` (preserved durably as `raphael-orphan-phase12-preserved`) introduced `RaphaelRuntime` to the same path. The two artifacts target the same `src/orchestrator/runtime/` directory with disjoint contents — a packaging collision.

Per v4.1 locked decisions:
- **L7** (capability/sandbox below broker): mechanisms are below the authorization boundary; they do not authorize.
- **L8** (single canonical execution boundary): the broker is the only authority for execution.

A path decision is required: is `src/orchestrator/runtime/` the orchestration layer (RaphaelRuntime) or the mechanisms layer (Caido/Docker/session)?

## Decision

**`src/orchestrator/runtime/` is the orchestration layer. The mechanisms layer is `src/orchestrator/sandbox/`. Capabilities remain in `src/orchestrator/capabilities/`. The broker remains the single authorization boundary in `src/orchestrator/brain/capability_broker.py`.**

### Architectural layering (canonical after P1 migration)

```
┌────────────────────────────────────────────────────────────────┐
│ orchestrator.runtime/      ORCHESTRATION  (RaphaelRuntime)    │
│  ├─ __init__.py                                               │
│  ├─ loop.py                                                   │
│  └─ types.py                                                  │
└──────────────────────┬─────────────────────────────────────────┘
                       │ composes (no authorization)
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ orchestrator.brain/        COGNITION (Planner, Broker, ...)    │
│  └─ capability_broker.py   AUTHORIZATION BOUNDARY (5-dim)     │
└──────────────────────┬─────────────────────────────────────────┘
                       │ authorizes
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ orchestrator.capabilities/  CAPABILITY INTERFACES (E-Series)  │
│  └─ interactive_shell/                                       │
└──────────────────────┬─────────────────────────────────────────┘
                       │ may use
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ orchestrator.sandbox/       MECHANISMS (below broker)         │
│  ├─ caido_bootstrap.py     (moved from runtime/)              │
│  ├─ docker_client.py       (moved from runtime/)              │
│  └─ session_manager.py     (moved from runtime/)              │
└────────────────────────────────────────────────────────────────┘
```

### Why this layering

- **runtime/ = orchestration:** RaphaelRuntime composes the cognitive loop. It selects candidates, calls the planner, calls the broker, executes via the environment, ingests evidence. It does not implement mechanisms; it composes them.
- **brain/ = cognition + authorization:** Planner, WorldModel, HypothesisManager, ContradictionManager, CapabilityBroker. The broker is the single authorization gate.
- **capabilities/ = capability interfaces:** SSH, reverse shell, command filter, TTY normalizer. These are the broker-authorized action surfaces.
- **sandbox/ = mechanisms:** Docker containers, Caido proxy, session lifecycle. These are the runtime infrastructure that *implements* a capability's environment.

The capabilities/ layer is the broker's contract. The sandbox/ layer is what the capabilities/ layer invokes to actually do work in an isolated environment. The runtime/ layer is the orchestrator that drives capabilities/ through the broker.

### Dependency direction (enforced)

```
runtime/  →  brain/  →  capabilities/  →  sandbox/
  ↑           ↑            ↑
no deps    authorizes    may use
```

Reverse dependencies are FORBIDDEN:
- `sandbox/` MUST NOT import from `runtime/`, `brain/`, or `capabilities/` directly. The sandbox is a passive mechanism.
- `capabilities/` MUST NOT import from `runtime/`. Capabilities are driven by the runtime, not the other way.
- `brain/` MUST NOT import from `runtime/`. The brain is composition target, not driver.

This is a structural invariant. It is enforced by import-graph test in P2 (post-Runtime-creation). For P1, the orphan's quarantine markers do not violate this invariant.

### Why sandbox/ is NOT the authorization boundary

- The sandbox/ layer provides a *mechanism* for execution (Docker container, Caido proxy). It does not decide whether an action is allowed.
- Authorization is the broker's job (L8). The broker decides, then the capability invokes sandbox/ to execute.
- A capability may use sandbox/ infrastructure without going through the broker only if it has already been broker-authorized. This is the same authorization discipline that applies to all execution paths.
- **P3 importer contraction:** the 5 importers of `SandboxSession` (`postex/pipeline.py`, `exploit/pipeline.py`, `scanners/pipeline.py`, `exfil/pipeline.py`, `phishing/pipeline.py`) are reachable only from services behind broken symlinks (`mcp-bridge`, `cai-service`). At P3, when the broker-gated capability path is enforced, the broker will require a registered capability for each of these pipeline constructions. P3 will add the capability registration and reduce the number of pipeline-instantiation sites from 5 to 1 (the single broker-gated capability that dispatches to the appropriate pipeline by action_type).

## Consequences

### Positive

- Architectural layering is now self-documenting at the directory level.
- The orphan's Runtime and the canonical sandbox infrastructure no longer conflict.
- New contributors can locate mechanisms (sandbox/), interfaces (capabilities/), and orchestration (runtime/) without reading source.
- The dependency direction is enforceable by import-graph testing.

### Negative

- The 5 pipeline files (`postex/`, `exploit/`, `scanners/`, `exfil/`, `phishing/`) need their imports updated from `..runtime.session_manager` to `..sandbox.session_manager`. This is a mechanical 1-line edit per file (5 files, 5 edits).
- The test `tests/test_cli_smoke.py:1405` has a stale label "Runtime session management" for the directory `orchestrator/runtime` — directory is now the orchestration layer, not session management. Per GLM C7 (zero test edits in P1), the label discrepancy is recorded for P9 cleanup, not fixed now.

### Neutral

- The orphan's quarantine markers (BypassNotAuthorized, authorize_bypass, etc.) are unaffected by this ADR. They live in capability constructors, not in the package layout.
- The orphan's runtime-seam work in `arena/ablation_runner.py` and `raphael/main.py` is unaffected.

## P3 importer contraction (concrete numbers)

| Phase | Sites importing `SandboxSession` | Sites broker-gated | Unbrokered sites |
|---|---|---|---|
| Canonical (pre-P1) | 5 (5 pipelines) | 0 | 5 |
| Post-P1 migration | 5 (paths updated) | 0 | 5 (same sites, new path) |
| Post-P3 broker closure | 1 (single capability dispatcher) | 1 | 0 |

The P3 reduction from 5 → 1 is achieved by introducing a `BrokeredPipeline` capability that:
- Receives a broker authorization receipt.
- Dispatches to the appropriate pipeline by `action_type`.
- Returns a broker-routable result.

The 5 pipeline files are not deleted; they are demoted to internal helpers called only by the brokered dispatcher.

## Alternatives considered

### Option B — Runtime at `cognition/`, sandbox stays at `runtime/`

- Runtime at `orchestrator/cognition/`, sandbox at `orchestrator/runtime/`.
- Naming overlap: `cognition/` is broader than orchestration; it could include the brain too.
- Rejected: invites confusion with `orchestrator.brain/`.

### Option C — Runtime at top-level `src/runtime/`, sandbox stays

- Runtime at `src/runtime/`, sandbox at `src/orchestrator/runtime/`.
- Top-level path collides with stdlib `runtime` references in some test frameworks.
- Requires `pyproject.toml` update for package discovery.
- Rejected: too generic; doesn't match architectural layer.

### Option D — Runtime absorbed into `orchestrator.brain/`

- Runtime as a sub-module of brain.
- Violates L4 (Head 2 is canonical cognition, not orchestration).
- Rejected: violates locked decision.

### Option E — Discard orphan work, rebuild from scratch

- The orphan work is discarded; P1 rebuilds `RaphaelRuntime` at a new path.
- Highest wasted-work cost (~1000 lines of audited code).
- Rejected: not necessary; the orphan can be referenced without being popped.

## Migration (this ADR's actionable consequence)

The migration is recorded in `evidence/phases/P1_0/collision_inventory.md` and implemented in P1:

1. `git mv` the 3 sandbox files from `src/orchestrator/runtime/` to `src/orchestrator/sandbox/`.
2. Create empty `src/orchestrator/sandbox/__init__.py`.
3. Update 5 pipeline import paths from `..runtime.session_manager` to `..sandbox.session_manager`.
4. Verify 239 tests still pass.
5. Tag `raphael-p1-post-migration-7272880f`.

## References

- v4.1 master roadmap §5.2 (capability/sandbox below broker)
- v4.1 master roadmap §9 (Decepticon placement — below broker)
- v4.1 master roadmap L7, L8 (locked decisions)
- v4.1 AM-4 (seam discipline)
- v4.1 AM-8 (evidence schema)
- `evidence/phases/P1_0/collision_inventory.md` (full evidence)
- `evidence/phases/P1_0/P1_0_DECISION.md` (decision record)
- Orphan provenance tag: `raphael-orphan-phase12-preserved` (4b960496…)
- Pre-migration rollback tag: `raphael-p1-pre-migration-7272880f` (215c4b76…)
