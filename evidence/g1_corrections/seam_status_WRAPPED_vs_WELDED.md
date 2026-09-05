# RC-1: WRAPPED vs WELDED status for every seam site (G1 correction)

Status definition (per v4.1 AM-4, C6):
- **WRAPPED**: a quarantine / opt-in flag is in place at the seam site; the bypass is *reachable* only via explicit `authorize_bypass(...)` call, otherwise the call raises. The seam is **OFF by default** in P1.
- **WELDED**: the quarantine opt-in is removed; the seam is replaced by a single broker-gated capability. The call site is reachable only via `CapabilityBroker.propose_action`. No opt-in flag exists.

Per C6: "Restore live seams OFF after the named-policy proof." WELDING happens at P3 (weld tickets).
The named-policy artifact `bootstrap-v0` is P2.0; until it exists, no seam may be turned ON.

## Inventory of every seam site in the working tree

| # | Path ID | Site (file:symbol) | Status (P1 end-state) | Weld ticket | Weld closure phase |
|---|---|---|---|---|---|
| 1 | SUB-10 | `src/orchestrator/kali_tools_client.py:_run_local` | **WRAPPED** (gate = `_BYPASS_AUTHORIZED=False`; `authorize_local_bypass(reason)` opt-in; raises `KaliBypassNotAuthorized` otherwise) | Weld-SUB10 | P3 |
| 2 | SUB-14 | `src/raphael/executor/executor.py:Executor._subprocess_fallback` | **WRAPPED** (gate = `Executor._bypass_authorized=False`; `authorize_bypass(reason)` opt-in; raises `BypassNotAuthorized` otherwise) | Weld-SUB14 | P3 |
| 3 | (no ID) | `src/orchestrator/brain/action.py` Planner `allowed = True` | **NOT A SEAM** — comment-only correction. Planner is selection-only; broker is the sole authorization authority. No runtime bypass exists. | n/a | n/a (clarity; P3 broker closure makes comment trivially true) |
| 4 | Weld-SHELL | `src/orchestrator/capabilities/interactive_shell/capability.py` (base for SSH/Reverse/Bind/Meterpreter) | **DEFERRED to P3** — quarantine was reverted during P1 because it broke canonical test `tests/e1_interactive_shell_test.py::test_adversarial_unauthorized_callback` and C7 forbids test edits. The seam is **not** WRAPPED today; it is **deferred**. This is the single P1 scope deviation (SD-1). | Weld-SHELL | P3 (when capability layer is fully broker-gated) |

## Non-seam subprocess sites (documented in P0 inventory; NOT seam sites)

Per `evidence/phases/P0/02_execution_inventory/subprocess_sites.md` and `evidence/phases/P1/03_seam_work/SEAM_SITES.md`, the following 15 P0 subprocess sites are **UNREACHABLE_FROM_CANONICAL** (not exercised by any canonical Arena/CLI entry point). They are **not** seam sites; they are dead code scheduled for P9 cleanup, not P3 weld.

| Path ID | Site | Status |
|---|---|---|
| SUB-01,02,03 | `src/orchestrator/weaponizer/weaponizer_engine.py:94,152,199` | Not a seam. Dead code. P9 cleanup. |
| SUB-04 | `src/orchestrator/chains/tool_registry.py:58` | Not a seam. Dead code. P9 cleanup. |
| SUB-05,06 | `src/orchestrator/c2/sliver_backend.py:75,101` | Not a seam. Dead code. P9 cleanup. |
| SUB-07,08,09 | `src/orchestrator/c2/implant_builder.py:315,450,502` | Not a seam. Dead code. P9 cleanup. |
| SUB-11 | `src/recon-pipeline/main.py:80` | Not a seam. Dead code. P9 cleanup. |
| SUB-12 | `src/agent/modules/executor.py:7` | Not a seam. Dead code. P9 cleanup. |
| SUB-15,16,17 | `src/sword/phase_0_recon.py:88,126,165` | Not a seam. Dead code. P9 cleanup. |

## Verdict

- **WRAPPED seams at end of P1:** 2 (SUB-10, SUB-14). Both OFF (default state). Per C6, must remain OFF until `bootstrap-v0` (P2.0).
- **WELDED seams at end of P1:** 0. Welding is a P3 deliverable per the weld tickets.
- **Deferred seams:** 1 (Weld-SHELL). Documented exception SD-1, fail-closed, broker-gated closure scheduled for P3.
- **Live-state assertion:** `kali_tools_client._BYPASS_AUTHORIZED = False` and `Executor._bypass_authorized = False` in the working tree (verified by file inspection; not asserted via execution per "do not modify/execute" constraint).

## Evidence sources

- `src/orchestrator/kali_tools_client.py:18-58` (SUB-10 quarantine, WRAPPED)
- `src/raphael/executor/executor.py:31-105` (SUB-14 quarantine, WRAPPED)
- `src/orchestrator/brain/action.py:1109-1117` (Planner comment correction, not a seam)
- `src/orchestrator/capabilities/interactive_shell/capability.py` (Weld-SHELL deferred)
- `evidence/phases/P1/03_seam_work/SEAM_SITES.md` (canonical P1 seam manifest)
- `evidence/phases/P1/EVIDENCE_PACKAGE.md` §5.6 (security proof)
- `evidence/phases/P0/02_execution_inventory/subprocess_sites.md` (P0 17-site inventory)
- `evidence/phases/P0/03_historical_reverification/bypass_reverification.md` (P0 10-bypass reverification)
