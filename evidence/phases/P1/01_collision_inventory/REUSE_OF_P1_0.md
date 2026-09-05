# P1.0 collision inventory — reused as P1 baseline

The P1.0 evidence package is the authoritative collision inventory and path-decision record for P1.

See:

- `evidence/phases/P1_0/P1_0_DECISION.md` — Option A path decision (split into `runtime/` and `sandbox/`)
- `evidence/phases/P1_0/collision_inventory.md` — full collision matrix, dependency analysis, migration sequence
- `docs/adr/ADR-011-sandbox-layer-mechanisms-not-authorization.md` — the architectural decision record

**P1 follows Option A as decided in P1.0.** No re-decision in P1; only execution.

**P1.0-mandated rollback anchor (re-verified in P1):** `raphael-p1-pre-migration-7272880f` → `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`.

**P1.0-mandated orphan provenance (re-implemented in P1 per C2):** `raphael-orphan-phase12-preserved` tag replaces the prior `git stash@{4}` provenance with a durable SHA-addressable artifact.
