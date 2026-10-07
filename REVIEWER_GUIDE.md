# REVIEWER_GUIDE.md — Independent Review Orientation

## Canonical control plane

- Runtime: `src/orchestrator/runtime/loop.py` (`RaphaelRuntime`, thin sequencer)
- Stages: `src/orchestrator/runtime/stages.py` (`STAGE_ORDER`, 10 stages, no more)
- PDP: `src/orchestrator/brain/capability_broker.py` (`CapabilityBroker.propose_action`)
- PEP: `src/orchestrator/runtime/stages.py:stage_pep` → `src/orchestrator/exec/`
- exec/: sole owner of process/network/file primitives (INV-1)
- Scope: `src/orchestrator/runtime/scope.py` (`ScopeV0` — constraint, not authorization)
- Sandbox: `src/orchestrator/exec/sandbox.py` (mechanism, not authorization)
- Evidence v1: `src/orchestrator/runtime/evidence_v1.py` + `src/orchestrator/exec/evidence_store.py`
- EvidenceGraph (canonical, pre-existing): `src/orchestrator/brain/evidence.py`

## Key evidence / governance records

- `evidence/phases/P3_0/SCOPE-V0_EVIDENCE.md` (§14.3, incl. Option-B record)
- `evidence/phases/P3_0/SANDBOX-V0_EVIDENCE.md` (§14.4, incl. honest enforcement matrix)
- `evidence/phases/P3_0/EVIDENCE-V1_EVIDENCE.md` (§14.5 substrate)
- `evidence/phases/P3_0/WELD-SHELL_EVIDENCE.md` (SHELL acceptance basis)
- `evidence/phases/P3_0/_b1a_probe.py` and `_shell_parity_probe.py` (instruments)

## Test invocation

```
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
```
Expect: 621 passed / 0 failed / 0 skipped / 0 xfail (verified 2026-10-04 on
Python 3.14.4 — the frozen `>=3.11,<3.13` pin is NOT satisfiable in the
current environment; re-verify on 3.12 after M1 provisioning). Guardrails:
the 10 `tests/test_p2_guardrail_*.py` files (30 collected). Closure: run the
B-1a probe above; expect static 34/0 Arena, loaded 53/0 Arena.

## Chain (authorization flows one way)

Scope → Broker → PEP → exec/ → SandboxResult → Evidence v1 → EvidenceGraph.
Evidence never authorizes; sandbox never authorizes; scope never authorizes.
