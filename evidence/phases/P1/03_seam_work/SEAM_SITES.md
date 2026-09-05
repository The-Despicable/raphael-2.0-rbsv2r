# P1 Seam Sites (per C6)

This document records every wrapped seam site in P1, mapped to its P0 Path ID and its P3 weld ticket. Per C6: "Map every wrapped site to its Path ID and weld ticket. Restore live seams OFF after the named-policy proof."

## Applied in P1 (live seams OFF)

| Path ID | Site | Quarantine mechanism | Weld ticket | Status |
|---|---|---|---|---|
| SUB-10 | `src/orchestrator/kali_tools_client.py:41` (inside `_run_local`) | `KaliBypassNotAuthorized` + module-level `_BYPASS_AUTHORIZED` flag + `authorize_local_bypass(reason=...)` opt-in | Weld-SUB10 (P3) | OFF |
| SUB-14 | `src/raphael/executor/executor.py:79` (inside `_subprocess_fallback`) | `BypassNotAuthorized` + class-level `_bypass_authorized` flag + `authorize_bypass(reason=...)` opt-in | Weld-SUB14 (P3) | OFF |
| (no ID) | `src/orchestrator/brain/action.py` (Planner `allowed = True` line ~1109) | comment-only: documents that `allowed` is selection-only, not authorization | n/a (clarity correction; P3 broker closure makes this trivially true) | n/a (no live seam) |

## Deferred to P3 (documented exceptions per C7)

| Path ID | Site | Weld ticket | Reason for deferral |
|---|---|---|---|
| Weld-SHELL | `src/orchestrator/capabilities/interactive_shell/capability.py` (base class for SSH/Reverse/Bind/Meterpreter) | Weld-SHELL (P3) | Applying the shell-capability quarantine in P1 broke one canonical P0 test (`tests/e1_interactive_shell_test.py::test_adversarial_unauthorized_callback`). C7 forbids test edits. The quarantine is recorded as deferred; the Weld-SHELL closure will land in P3 when the capability layer is fully broker-gated. |

The deferral is fail-closed (no production code can reach the unbrokered shell path during P1 → P2 → P3 because no production code reaches it at canonical, per the P0 inventory: all 5 consumers of `SandboxSession` are only reachable through services behind broken symlinks).

## Not in P1 scope

| Path ID | Site | Why out of scope |
|---|---|---|
| SUB-01, SUB-02, SUB-03 | `src/orchestrator/weaponizer/weaponizer_engine.py:94,152,199` | UNREACHABLE_FROM_CANONICAL at P0. P9 cleanup. |
| SUB-04 | `src/orchestrator/chains/tool_registry.py:58` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |
| SUB-05, SUB-06 | `src/orchestrator/c2/sliver_backend.py:75,101` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |
| SUB-07, SUB-08, SUB-09 | `src/orchestrator/c2/implant_builder.py:315,450,502` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |
| SUB-11 | `src/recon-pipeline/main.py:80` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |
| SUB-12 | `src/agent/modules/executor.py:7` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |
| SUB-15, SUB-16, SUB-17 | `src/sword/phase_0_recon.py:88,126,165` | UNREACHABLE_FROM_CANONICAL. P9 cleanup. |

These 15 sites are unreachable from canonical Arena/CLI entry points per the P0 inventory. They are not seam sites; they are dead code (P9 cleanup). P3 will not close them; P9 will delete or quarantine them.

## Weld tickets (P3 deliverables)

| Ticket | What P3 must do |
|---|---|
| Weld-SUB10 | Replace `authorize_local_bypass(reason)` opt-in with a broker-gated capability. Delete `KaliBypassNotAuthorized` exception and `_BYPASS_AUTHORIZED` flag. The `_run_local` call is reached only through `CapabilityBroker.propose_action` → capability execution. |
| Weld-SUB14 | Replace `authorize_bypass(reason)` opt-in with a broker-gated capability. Delete `BypassNotAuthorized` exception and `_bypass_authorized` flag. The `_subprocess_fallback` is reached only through `CapabilityBroker.propose_action` → capability execution. |
| Weld-SHELL | Apply the deferred shell-capability quarantine (`BypassNotAuthorized` for `InteractiveShellCapability` subclasses). Replace the test's opt-in call with a broker-gated capability invocation. Reduce the 5 `SandboxSession` importers to 1 (single broker-gated dispatcher). |

## Live seam state at end of P1

```python
# src/orchestrator/kali_tools_client.py
_BYPASS_AUTHORIZED = False

# src/raphael/executor/executor.py
class Executor:
    _bypass_authorized: bool = False
```

Both are at their default `False`. Any production code reaching `_run_local` or `_subprocess_fallback` without explicit opt-in raises.

## Seams must remain OFF (per C6: "Restore live seams OFF after the named-policy proof")

The named-policy artifact `bootstrap-v0` is a P2.0 deliverable (per v4.1 AM-13.2). Until `bootstrap-v0` exists, no production code should be turning these seams ON. The seams are correctly OFF at end of P1.

If anyone (test, legacy code, future agent) needs to bypass, they must call `authorize_bypass(reason=...)` or `authorize_local_bypass(reason=...)` with a documented reason. The opt-in is logged at WARNING level.
