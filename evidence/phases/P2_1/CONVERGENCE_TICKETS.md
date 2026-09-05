# G2-C3 — Convergence Tickets (P2 → P3)

Created per G2-C3: owner + target-phase tickets for P3 convergence
items. **Do not prematurely perform the P3 migration.** These are
tickets, not tasks. P3 remains unauthorized.

---

## Ticket CONV-1: BootstrapPolicy → single canonical PDP at P3

**Current state (P2):**
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
- A single canonical PDP (Policy Decision Point) must exist at P3.
  Per v4 L5: "Broker is the Policy Decision Point (PDP). It decides
  allow/deny and constraints." The current `BootstrapPolicy` is a
  P2 placeholder; the canonical PDP is the `CapabilityBroker` in
  `src/orchestrator/brain/capability_broker.py`.
- Owner: GLM (gate reviewer) + implementation lane.
- Convergence: P3 scope v0 lands → BootstrapPolicy deleted → Runtime
  injects CapabilityBroker (brain-owned) as the single canonical PDP.

**Do not perform in P2.** Do not modify BootstrapPolicy beyond
G2-C2 fail-closed hardening. Do not wire CapabilityBroker into
Runtime in P2.

---

## Ticket CONV-2: Runtime PEP stage → exec/ at P3

**Current state (P2):**
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
- Owner: GLM + implementation lane.
- Convergence: exec/ package created at P3 → SafeProvingCapability
  relocated → Runtime PEP stage delegates to exec/.

**Do not perform in P2.** Do not create `src/orchestrator/exec/`.
Do not move SafeProvingCapability. Do not delegate PEP to exec/.

---

## Ticket CONV-3: safe_proving_capability.py → capabilities namespace / approved ADR-011 exception, with P3 convergence

**Current state (P2):**
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
- Owner: GLM + implementation lane.
- Convergence: ADR for the move → file relocated → Runtime PEP
  imports updated.

**Do not perform in P2.** Do not move the file. Do not create a
new ADR. The Runtime currently injects the capability directly
into the stage context.

---

## Ticket CONV-4: no second PDP or orphaned scaffolding survives to G3

**Current state (P2):**
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

| Ticket | Owner | Target phase | P2 action |
|---|---|---|---|
| CONV-1: BootstrapPolicy → canonical PDP | GLM + impl | P3 | None (retired at P3) |
| CONV-2: Runtime PEP → exec/ | GLM + impl | P3 | None (exec/ created at P3) |
| CONV-3: SafeProvingCapability → capabilities/ | GLM + impl | P3 | None (moved at P3) |
| CONV-4: no second PDP / orphaned scaffolding | GLM | G3 | None (verified at G3) |

**No P3 migration performed.** P3 remains unauthorized.
