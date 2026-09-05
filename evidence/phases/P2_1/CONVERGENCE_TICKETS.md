# G2-C3 / G2-FR-1 — Convergence Tickets (P2 → P3)

Created per G2-C3 and finalized per G2-FR-1. Owner + target-phase
tickets for P3 convergence items. **Do not prematurely perform the
P3 migration.** These are tickets, not tasks. P3 remains unauthorized.

---

## Ticket CONV-1: BootstrapPolicy → single canonical PDP at P3

**Ticket subject:** Retire `BootstrapPolicy` (P2 placeholder PDP in
`src/orchestrator/runtime/policy.py`) and route the Runtime's
`stage_broker` through the brain's `CapabilityBroker`
(`src/orchestrator/brain/capability_broker.py`) as the single canonical
Policy Decision Point (PDP).

**Owner:** GLM (gate reviewer) + implementation lane.

**Target phase:** P3 (when Scope v0 lands per v4 §14.3).

**G3 verification criterion:**
At G3 review, the gate reviewer must confirm:
1. `src/orchestrator/runtime/policy.py` no longer exists (file deleted
   or reduced to a re-export shim with no policy logic).
2. `stage_broker` in `src/orchestrator/runtime/stages.py` invokes
   `CapabilityBroker.propose_action()` (or equivalent brain-owned PDP
   method) — not a local policy.
3. `CapabilityBroker` is the sole PDP reachable from the Runtime's
   transitive closure. No second PDP exists.
4. Scope v0 is committed and applied. `bootstrap-v0.json` is retired.

**Current state (P2.1):**
- `src/orchestrator/runtime/policy.py` contains `BootstrapPolicy`,
  a minimal named/versioned policy artifact (v4.1 AM-13.2) that
  the P2 Broker-mediated mock path and P2.4 safe capability authorize
  against.
- `BootstrapPolicy` is loaded from `policies/bootstrap-v0.json` at
  Runtime construction.
- Default decision: deny. 5 rules (BOOT-001..005).
- The Runtime injects `BootstrapPolicy` into the stage context
  as the policy input to `stage_broker`.

**P3 target:**
- `BootstrapPolicy` must be **retired** when Scope v0 lands (v4.1 AM-13.2:
  "This is explicitly superseded by Scope v0 at P3 (v4 §14.3) —
  bootstrap-v0 is not extended or reused past P2, it is retired when
  Scope v0 lands").
- A single canonical PDP must exist at P3. Per v4 L5: "Broker is
  the Policy Decision Point (PDP). It decides allow/deny and
  constraints." The current `BootstrapPolicy` is a P2 placeholder;
  the canonical PDP is the `CapabilityBroker` in
  `src/orchestrator/brain/capability_broker.py`.
- Owner: GLM (gate reviewer) + implementation lane.
- Convergence: P3 scope v0 lands → BootstrapPolicy deleted → Runtime
  injects CapabilityBroker (brain-owned) as the single canonical PDP.

**Do not perform in P2.** Do not modify BootstrapPolicy beyond
G2-C2 fail-closed hardening. Do not wire CapabilityBroker into
Runtime in P2.

---

## Ticket CONV-2: Runtime PEP stage → exec/ at P3

**Ticket subject:** Move the Runtime's PEP enforcement
(`stage_pep` in `src/orchestrator/runtime/stages.py`) into the
brain-owned `src/orchestrator/exec/` package, so that
process/network/file primitives are confined to `exec/` per v4 L6.

**Owner:** GLM (gate reviewer) + implementation lane.

**Target phase:** P3.

**G3 verification criterion:**
At G3 review, the gate reviewer must confirm:
1. `src/orchestrator/exec/` directory exists and is the sole
   package permitted to hold process/network/file primitives.
2. `stage_pep` in the Runtime delegates to an exec/-owned capability
   — not to a `Runtime/safe_proving_capability.py` module.
3. The Runtime's transitive import closure does not include any
   `orchestrator/runtime/safe_proving_capability` module (it has
   been relocated).
4. No `subprocess`, `os.system`, `socket.*`, or `urllib.*` import
   exists outside `src/orchestrator/exec/`.

**Current state (P2.1):**
- `src/orchestrator/runtime/stages.py:stage_pep` calls the capability
  directly: `capability.inspect(request.target)`.
- The capability (`SafeProvingCapability`) is an in-process dict
  reader — no subprocess, no network, no file mutation.
- The PEP (Policy Enforcement Point) is the Runtime itself, which
  mints the `ExecutionEvent` and `EvidenceReceipt`.

**P3 target:**
- Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
  only package permitted to hold process/network/file primitives."
- The Runtime's PEP stage must route through `src/orchestrator/exec/`
  (which does not yet exist in the repository at the time of P2.1).
- At P3, `SafeProvingCapability` must be moved to
  `src/orchestrator/exec/` (or to `src/orchestrator/capabilities/`
  per ADR-011 arena-clause addendum) and the Runtime's PEP stage
  must delegate to it.
- Owner: GLM (gate reviewer) + implementation lane.
- Convergence: exec/ package created at P3 → SafeProvingCapability
  relocated → Runtime PEP stage delegates to exec/.

**Do not perform in P2.** Do not create `src/orchestrator/exec/`.
Do not move SafeProvingCapability. Do not delegate PEP to exec/.

---

## Ticket CONV-3: safe_proving_capability.py → capabilities namespace / approved ADR-011 exception, with P3 convergence

**Ticket subject:** Move `SafeProvingCapability` from
`src/orchestrator/runtime/safe_proving_capability.py` to
`src/orchestrator/capabilities/` (or a new approved namespace) per
ADR-011 arena-clause addendum.

**Owner:** GLM (gate reviewer) + implementation lane.

**Target phase:** P3.

**G3 verification criterion:**
At G3 review, the gate reviewer must confirm:
1. `src/orchestrator/runtime/safe_proving_capability.py` no longer
   exists (file deleted or reduced to a re-export shim).
2. `SafeProvingCapability` lives under
   `src/orchestrator/capabilities/` (or an ADR-approved location).
3. An ADR exists that approves the move (per v4.1 amendment
   discipline).
4. The Runtime's `stage_pep` imports `SafeProvingCapability` from
   its new location.

**Current state (P2.1):**
- `src/orchestrator/runtime/safe_proving_capability.py` contains
  `SafeProvingCapability` (a read-only fixture inspection capability).
- It lives under `orchestrator/runtime/` because it is the P2.4
  "safe proving capability" (v4 §13.3 P2.4).

**P3 target:**
- Per v4 §3.1: "capabilities: keep and universalize" (under
  `orchestrator/capabilities/`).
- Per ADR-011 arena-clause addendum: "the sandbox/ layer is
  mechanisms-only; capabilities remain in `capabilities/`".
- `SafeProvingCapability` must be moved from
  `src/orchestrator/runtime/` to
  `src/orchestrator/capabilities/` (or to a new capabilities
  subdirectory approved by an ADR).
- The Runtime's PEP stage must import from the new location.
- Owner: GLM (gate reviewer) + implementation lane.
- Convergence: ADR for the move → file relocated → Runtime PEP
  imports updated.

**Do not perform in P2.** Do not move the file. Do not create a
new ADR. The Runtime currently injects the capability directly
into the stage context.

---

## Ticket CONV-4: no second PDP or orphaned scaffolding survives to G3

**Ticket subject:** At G3 (MVP gate), verify that there is exactly
one PDP, exactly one PEP, and no orphaned P2 scaffolding.

**Owner:** GLM (gate reviewer).

**Target phase:** G3.

**G3 verification criterion:**
At G3 review, the gate reviewer must confirm:
1. Exactly one PDP exists: `CapabilityBroker` in
   `src/orchestrator/brain/capability_broker.py`. No
   `BootstrapPolicy`, no other policy module reachable from Runtime.
2. Exactly one PEP exists: `src/orchestrator/exec/`. No
   `Runtime/safe_proving_capability.py` PEP emulation.
3. The `src/orchestrator/runtime/` directory contains only:
   `__init__.py`, `loop.py` (thin sequencer), `types.py` (contracts),
   `stages.py` (stage handlers). No policy module, no capability
   module.
4. No P2 walking-skeleton scaffolding survives (no
   `BootstrapPolicy`, no in-process dict fixtures, no
   `RAPHAEL_USE_LEGACY` flag, no `PYTHONPATH=src` test-only paths).

**Current state (P2.1):**
- Single PDP: `BootstrapPolicy` (P2 placeholder).
- Single PEP: Runtime `stage_pep` (delegates to injected capability).
- No second PDP exists.
- No orphaned scaffolding exists beyond the items in CONV-1..3.

**P3 target:**
- Verify that at G3 (MVP gate), there is exactly one PDP
  (`CapabilityBroker` in brain), exactly one PEP (`exec/`), and
  no orphaned scaffolding from the P2 walking skeleton.
- Specifically: `BootstrapPolicy` deleted (CONV-1),
  `SafeProvingCapability` relocated (CONV-3), Runtime PEP delegates
  to `exec/` (CONV-2).
- The `src/orchestrator/runtime/` directory should contain only the
  thin sequencer (`loop.py`), the type contracts (`types.py`), the
  stage handlers (`stages.py`), and the policy stub (deleted at P3).
- Owner: GLM (gate reviewer).
- Convergence: G3 review checks for exactly one PDP, exactly one PEP,
  and no P2 scaffolding.

**Do not perform in P2.** This is a G3 verification ticket.

---

## Summary

| Ticket | Owner | Target phase | G3 verification |
|---|---|---|---|
| CONV-1: BootstrapPolicy → canonical PDP | GLM + impl | P3 | policy.py deleted; stage_broker → CapabilityBroker; Scope v0 applied |
| CONV-2: Runtime PEP → exec/ | GLM + impl | P3 | exec/ exists; stage_pep delegates to exec/; no primitives outside exec/ |
| CONV-3: SafeProvingCapability → capabilities/ | GLM + impl | P3 | safe_proving_capability.py deleted from runtime/; ADR exists; new location imports work |
| CONV-4: no second PDP / orphaned scaffolding | GLM | G3 | exactly one PDP, exactly one PEP, no P2 scaffolding in runtime/ |

**No P3 migration performed.** P3 remains unauthorized.
