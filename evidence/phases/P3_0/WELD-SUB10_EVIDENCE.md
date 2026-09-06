# RAPHAEL WELD-SUB10 — Evidence Package

> Branch: `weld-sub10-evidence`
> Weld commit (SUB-14, accepted): `740861f2e061861596bcfe9193c6bce9437dc183`
> Pre-weld base for this round: `2caeb4923a2150ceac13fa9a69bb9b2d3fbce06b` (WELD-SUB14 BD-1 records correction)
> Implementation commit (this round): `a099ba460d1cf47c5a14189b3fda7f36bd98ac61`
> Implementation/pre-evidence commit count since canonical `7272880f7`: **52** (per `git rev-list --count 7272880f7..HEAD` at implementation commit `a099ba460`).
> Final HEAD: established by external machine verification of the records-only evidence commit (see Section W-D). The final HEAD is not embedded in this file because the evidence commit cannot contain its own hash without a self-referential loop.
> Probe evidence-capture script: `evidence/phases/P3_0/_b1a_probe.py`
> Author: RAPHAEL WELD-SUB10 Audit
> Phase: WELD-SUB10 (SUB-10 weld)
> Gate: WELD-SUB10

## 1. Submission Summary

WELD-SUB10 removes the SUB-10 local-subprocess bypass in
`src/orchestrator/kali_tools_client.py` (`KaliBypassNotAuthorized`,
`_BYPASS_AUTHORIZED`, `authorize_local_bypass`, `_run_local`).
`KaliToolsClient.run()` no longer falls back to local subprocess
execution; when the remote API is unavailable it raises a fail-closed
`RuntimeError`. The prior SUB-14/SUB-13 welds are untouched and remain
accepted. SUB-10 had no canonical reachability, so parity is by
unreachability (see W-A.4 / W-C.1). SHELL remains deferred and untouched.

The code tree being proved is the tree at implementation commit
`a099ba460`. This evidence file is included in the final records-only
commit on branch `weld-sub10-evidence`.

---

## STEP 0/1 — SUB-10 BYPASS INVENTORY (pre-weld facts)

| Field | Value |
|---|---|
| Seam/path ID | SUB-10 — `src/orchestrator/kali_tools_client.py:41` (P0 inventory `evidence/phases/P0/02_execution_inventory/subprocess_sites.md`) |
| Owning module | `src/orchestrator/kali_tools_client.py` |
| Primitive invoked | `asyncio.create_subprocess_exec(*cmd_list, ...)` inside `async def _run_local` |
| Authorization mechanism (pre-weld) | Module flag `_BYPASS_AUTHORIZED: bool = False` + `KaliBypassNotAuthorized` gate in `_run_local` + `authorize_local_bypass(reason)` opt-in (module function and `KaliToolsClient.authorize_local_bypass` instance method) |
| Current callers (pre-weld) | `KaliToolsClient.run()` falls back to `_run_local` when remote check fails or remote call raises; ~30 legacy wrapper modules import the shared `kali` instance (`postex/*`, `chains/*`, `scanners/*`, `ad/*`, `agents/*`, `modes/student.py`, `bridge/raphael_bridge.py`) |
| Canonical Runtime reachability | **NONE.** `orchestrator.runtime.*` imports nothing from `kali_tools_client`. B-1a static closure (31 orchestrator modules) contains 0 occurrences of `kali_tools_client`. Loaded-module closure after a full episode contains 0 occurrences. |
| Legacy reachability | Legacy Head-1 / wrapper callers listed above; gated pre-weld by opt-in, post-weld removed. |
| Existing guardrail tests (pre-weld) | `test_sub10_kali_bypass_raises_when_not_authorized`, `test_sub10_authorize_local_bypass_exists`, `test_seam_state_consistent_across_imports` (deny file); `test_bypass_functions_only_callable_via_explicit_optin` (no-production-bypass file); `test_seam_quarantines_are_off_by_default` SUB-10 portion (runtime-no-seam file) |
| Intended weld state | Bypass symbols removed; `run()` fail-closed `RuntimeError`; no `_run_local`, no opt-in, no flag, no exception class |
| Files expected to change | `src/orchestrator/kali_tools_client.py` (production); the three guardrail files above (tests); one new institutional test file |

**Reachability verdict: SUB-10 is legacy-only.** Canonical Runtime neither imports nor invokes it (proven by B-1a closure, W-C.6).

---

## W-A — INSPECTABLE WELD DIFF

### W-A.1 — `git name-status` (pre-weld base → implementation)

```
$ git diff --name-status 2caeb4923..a099ba460
M	src/orchestrator/kali_tools_client.py
M	tests/test_p2_guardrail_deny_by_default.py
M	tests/test_p2_guardrail_no_production_bypass.py
M	tests/test_p2_guardrail_runtime_no_seam.py
A	tests/test_p2_guardrail_sub10_closed.py
```

(`--stat`: kali_tools_client.py 107 changed lines, 16 insertions, 87 deletions; deny file 57 changed; no-production-bypass 16 changed; runtime-no-seam 21 changed; sub10_closed 66 added.)

### W-A.2 — Removed symbols (verified at `a099ba460`)

- `class KaliBypassNotAuthorized` → NOT FOUND (removed)
- `_BYPASS_AUTHORIZED: bool = False` → NOT FOUND (removed)
- `def authorize_local_bypass(reason` (module) → NOT FOUND (removed)
- `async def _run_local(` → NOT FOUND (removed)
- `def authorize_local_bypass(self` (instance method) → NOT FOUND (removed)
- `return await _run_local(tool, args, timeout)` (2 call sites in `KaliToolsClient.run`) → REMOVED, both replaced with fail-closed `RuntimeError`

Verbatim diff excerpt (header + bypass removal):

```diff
-# ── P1 SEAM (per C6, AM-4) — quarantine on _run_local ──────────────────
+# ── P1 SEAM (per C6, AM-4) — WELDED in WELD-SUB10 ────────────────────────────
 # Path ID: SUB-10 (canonical P0 inventory: evidence/phases/P0/02_execution_inventory/subprocess_sites.md)
-# Weld ticket: Weld-SUB10 (P3)
-# Without explicit authorize_local_bypass(reason), _run_local raises
-# KaliBypassNotAuthorized. The seam is OFF by default per C6.
-# Runtime (when it exists, post-P2) is the consumer of authorize_local_bypass;
-# this module is the seam, not Runtime.
-class KaliBypassNotAuthorized(Exception):
-    """Raised when KaliToolsClient._run_local is invoked without explicit
-    authorize_local_bypass(reason) opt-in. See evidence/phases/P0/03_historical_reverification/bypass_reverification.md."""
-    pass
-
-_BYPASS_AUTHORIZED: bool = False
-
-def authorize_local_bypass(reason: str = "") -> None:
-    """Explicitly opt-in to the local subprocess fallback. Tests/legacy code
-    that genuinely need it must call this with a reason. Production code
-    must invoke _run_local only through a broker-gated capability (P3)."""
-    global _BYPASS_AUTHORIZED
-    _BYPASS_AUTHORIZED = True
-    logger.warning(
-        "kali_tools_client._BYPASS_AUTHORIZED=True (reason=%r). "
-        "Local subprocess fallback is now reachable. P1 seam is ON for this site.",
-        reason,
-    )
```

Verbatim diff excerpt (`KaliToolsClient.run` fail-closed replacement):

```diff
             except (GuardTimeout, httpx.ConnectError, Exception) as e:
-                logger.debug(f"Remote execution failed for {tool}, falling back to local: {e}")
-                return await _run_local(tool, args, timeout)
+                logger.debug(f"Remote execution failed for {tool}, no local fallback (WELD-SUB10): {e}")
+                raise RuntimeError(
+                    "kali_tools_client._run_local is removed in WELD-SUB10. "
+                    "All execution must go through the broker-gated capability."
+                )

-        return await _run_local(tool, args, timeout)
+        # SUB-10 welded: local subprocess fallback removed
+        raise RuntimeError(
+            "kali_tools_client._run_local is removed in WELD-SUB10. "
+            "All execution must go through the broker-gated capability."
+        )
```

Additionally, one adjacent latent defect was fixed because it was strictly necessary for the fail-closed path to raise the documented error instead of an unrelated `NameError`: the module used `logger.*` but never defined `logger`. Added `logger = logging.getLogger(__name__)` after the hardening imports. Without this, `KaliToolsClient.run()` raised `NameError: name 'logger' is not defined` in `_check_remote` before reaching the documented `RuntimeError`.

### W-A.3 — Resulting routing

Post-weld `KaliToolsClient.run()`:
1. Rate-limits, then checks remote availability via `_check_remote()` (httpx `/health`).
2. If remote: attempts the broker/HTTP `/run` call under the timeout guard; on success returns the result.
3. If remote check fails, remote call raises, or `FORCE_LOCAL`/`_use_local` is set: raises fail-closed `RuntimeError("kali_tools_client._run_local is removed in WELD-SUB10. ...")`.
4. No subprocess, no `shlex.split`, no `shutil.which`, no `asyncio.create_subprocess_exec` reachable anywhere in the module. (Unused imports `asyncio`/`subprocess` remain as dead imports; no behavior.)

### W-A.4 — Governance / reachability analysis (corrected)

1. The canonical Runtime (`orchestrator.runtime.RaphaelRuntime`) does NOT import `orchestrator.kali_tools_client` and does NOT use `KaliToolsClient`. The B-1a static transitive closure (starting from `orchestrator.runtime`) contains only `orchestrator.*` modules and zero `arena.*` modules; `kali_tools_client` occurs 0 times in both the static and loaded closures.
2. Therefore parity is **PARITY-BY-UNREACHABILITY**: the canonical Runtime never reached SUB-10 before the weld and does not reach it after the weld. The weld does not alter any canonical Runtime behavior.
3. The ~30 wrapper modules that import the shared `kali` instance (`postex/*`, `chains/*`, `scanners/*`, `ad/*`, `agents/*`, `modes/student.py`, `bridge/raphael_bridge.py`) are legacy-envelope callers. Post-weld they receive the fail-closed `RuntimeError` on the remote-unavailable path instead of silent local execution.
4. `KaliToolsClient.run` retains its pre-existing `httpx.AsyncClient` HTTP primitive. That HTTP behavior is legacy behavior and was not introduced by this weld.
5. This weld strictly **narrows** the legacy envelope: local subprocess execution is removed; failure now raises instead of executing locally.
6. Consequences: no new unbrokered primitive path exists on the canonical surface; canonical Runtime behavior is unaffected; legacy behavior is narrowed, not expanded.

---

## W-B — GUARDRAIL LINEAGE / HONEST −/+ TRANSITION

### W-B.1 — Pre-weld test definitions (at `2caeb4923`, verbatim SUB-10 portions)

**`tests/test_p2_guardrail_deny_by_default.py`:**
```python
def test_sub10_kali_bypass_raises_when_not_authorized():
    """SUB-10: kali_tools_client._run_local raises KaliBypassNotAuthorized
    when _BYPASS_AUTHORIZED is False (default)."""
    from orchestrator.kali_tools_client import (
        _BYPASS_AUTHORIZED,
        KaliBypassNotAuthorized,
        _run_local,
    )

    # Verify default state
    assert _BYPASS_AUTHORIZED is False, (
        "SUB-10: _BYPASS_AUTHORIZED must default to False (v4.1 AM-4)"
    )

    # Verify _run_local raises when not authorized
    with pytest.raises(KaliBypassNotAuthorized):
        asyncio.run(_run_local("echo", "test", 5))
```
```python
def test_sub10_authorize_local_bypass_exists():
    """SUB-10: authorize_local_bypass() opt-in function exists.

    This is the only way to turn the seam ON. It logs a WARNING.
    """
    from orchestrator import kali_tools_client

    assert hasattr(kali_tools_client, "authorize_local_bypass"), (
        "SUB-10: authorize_local_bypass() opt-in function must exist"
    )
    sig = inspect.signature(kali_tools_client.authorize_local_bypass)
    assert "reason" in sig.parameters, (
        "SUB-10: authorize_local_bypass must accept a 'reason' parameter"
    )
```
```python
def test_seam_state_consistent_across_imports():
    ...(SUB-10 portion)...
    from orchestrator.kali_tools_client import _BYPASS_AUTHORIZED
    ...
    assert _BYPASS_AUTHORIZED is False
```

**`tests/test_p2_guardrail_no_production_bypass.py`:**
```python
def test_bypass_functions_only_callable_via_explicit_optin():
    """The bypass opt-in functions must require an explicit 'reason' parameter.

    This ensures that any future opt-in is documented.
    Note: authorize_bypass is removed in WELD-SUB14, so we only check authorize_local_bypass.
    """
    sys.path.insert(0, str(SRC_ROOT))

    from orchestrator import kali_tools_client

    # Check authorize_local_bypass
    sig_kali = inspect.signature(kali_tools_client.authorize_local_bypass)
    assert "reason" in sig_kali.parameters, (
        "authorize_local_bypass must require a 'reason' parameter"
    )

    # Note: authorize_bypass is removed in WELD-SUB14, so we do not check it.
```

**`tests/test_p2_guardrail_runtime_no_seam.py`:**
```python
def test_seam_quarantines_are_off_by_default():
    """SUB-14 seam: _subprocess_fallback method is removed after WELD-SUB14.
    SUB-10 seam: _BYPASS_AUTHORIZED flag is OFF by default."""
    # Check SUB-10: _BYPASS_AUTHORIZED must be False
    kali_file = SRC_ROOT / "orchestrator" / "kali_tools_client.py"
    if kali_file.exists():
        content = kali_file.read_text()
        # Check that _BYPASS_AUTHORIZED is defined as False
        assert "_BYPASS_AUTHORIZED: bool = False" in content, (
            "SUB-10 seam: _BYPASS_AUTHORIZED must default to False "
            "(v4.1 AM-4 weld discipline)"
        )
        # Check that the gate raises when not authorized
        assert "KaliBypassNotAuthorized" in content, (
            "SUB-10 seam: must raise KaliBypassNotAuthorized when not authorized"
        )
```

### W-B.2 — Post-weld test definitions (at `a099ba460`, verbatim SUB-10 portions)

**`tests/test_p2_guardrail_deny_by_default.py`:**
```python
def test_sub10_kali_bypass_removed():
    """SUB-10: kali_tools_client._run_local is removed after WELD-SUB10."""
    from orchestrator import kali_tools_client

    assert not hasattr(kali_tools_client, "_run_local"), (
        "SUB-10: kali_tools_client._run_local must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "KaliBypassNotAuthorized"), (
        "SUB-10: KaliBypassNotAuthorized must be removed after WELD-SUB10"
    )
    assert not hasattr(kali_tools_client, "_BYPASS_AUTHORIZED"), (
        "SUB-10: _BYPASS_AUTHORIZED must be removed after WELD-SUB10"
    )
```
```python
def test_sub10_authorize_local_bypass_removed():
    """SUB-10: authorize_local_bypass() opt-in is removed after WELD-SUB10."""
    from orchestrator import kali_tools_client
    from orchestrator.kali_tools_client import KaliToolsClient

    assert not hasattr(kali_tools_client, "authorize_local_bypass"), (
        "SUB-10: authorize_local_bypass() must be removed after WELD-SUB10"
    )
    assert not hasattr(KaliToolsClient, "authorize_local_bypass"), (
        "SUB-10: KaliToolsClient.authorize_local_bypass must be removed after WELD-SUB10"
    )
```
```python
def test_seam_state_consistent_across_imports():
    """SUB-10 seam: bypass symbols are removed (OFF by construction).
    SUB-14 seam: _subprocess_fallback method is removed (so OFF by construction)."""
    ...
    from orchestrator import kali_tools_client
    from raphael.executor.executor import Executor

    assert not hasattr(kali_tools_client, "_BYPASS_AUTHORIZED")
    assert not hasattr(kali_tools_client, "authorize_local_bypass")
    assert not hasattr(kali_tools_client, "_run_local")
    # The Executor seam is removed, so we check for the absence of the field/method
    assert not hasattr(Executor, "_bypass_authorized")
    assert not hasattr(Executor, "_subprocess_fallback")
```

**`tests/test_p2_guardrail_no_production_bypass.py`:**
```python
def test_bypass_functions_only_callable_via_explicit_optin():
    """The bypass opt-in functions must require an explicit 'reason' parameter.

    This ensures that any future opt-in is documented.
    Note: authorize_bypass is removed in WELD-SUB14 and authorize_local_bypass
    is removed in WELD-SUB10, so both must now be absent.
    """
    sys.path.insert(0, str(SRC_ROOT))

    from orchestrator import kali_tools_client
    from raphael.executor.executor import Executor

    # Both opt-in functions are removed by their welds; absence is the proof.
    assert not hasattr(kali_tools_client, "authorize_local_bypass"), (
        "authorize_local_bypass must be removed after WELD-SUB10"
    )
    assert not hasattr(Executor, "authorize_bypass"), (
        "Executor.authorize_bypass must be removed after WELD-SUB14"
    )
```

**`tests/test_p2_guardrail_runtime_no_seam.py`:**
```python
def test_seam_quarantines_are_off_by_default():
    """SUB-14 seam: _subprocess_fallback method is removed after WELD-SUB14.
    SUB-10 seam: bypass symbols are removed after WELD-SUB10."""
    # Check SUB-10: bypass symbols must be absent from the source
    kali_file = SRC_ROOT / "orchestrator" / "kali_tools_client.py"
    if kali_file.exists():
        content = kali_file.read_text()
        assert "_BYPASS_AUTHORIZED: bool = False" not in content, (
            "SUB-10 seam: _BYPASS_AUTHORIZED flag must be removed after WELD-SUB10"
        )
        assert "class KaliBypassNotAuthorized" not in content, (
            "SUB-10 seam: KaliBypassNotAuthorized must be removed after WELD-SUB10"
        )
        assert "async def _run_local" not in content, (
            "SUB-10 seam: _run_local must be removed after WELD-SUB10"
        )
        assert "def authorize_local_bypass" not in content, (
            "SUB-10 seam: authorize_local_bypass must be removed after WELD-SUB10"
        )
```

**New institutional test `tests/test_p2_guardrail_sub10_closed.py::test_sub10_kali_client_fails_closed`** (verbatim; see W-C.2 for full source).

### W-B.3 — Transition table (R-W2 dispositions)

| Old test | New test | Commit | Pre-assertion | Post-assertion | Reason / disposition |
|---|---|---|---|---|---|
| `test_sub10_kali_bypass_raises_when_not_authorized` | `test_sub10_kali_bypass_removed` | `a099ba460` | `_BYPASS_AUTHORIZED is False`; `_run_local` raises `KaliBypassNotAuthorized` | `not hasattr` for `_run_local`, `KaliBypassNotAuthorized`, `_BYPASS_AUTHORIZED` | **REPLACED (required by weld):** quarantine gate removed with the bypass; absence check is stronger. |
| `test_sub10_authorize_local_bypass_exists` | `test_sub10_authorize_local_bypass_removed` | `a099ba460` | `hasattr(authorize_local_bypass)` + `reason` param check | `not hasattr` (module + instance) | **REPLACED (required by weld):** opt-in removed; absence is the proof. |
| `test_seam_state_consistent_across_imports` (deny file) | same name, edited | `a099ba460` | `from ... import _BYPASS_AUTHORIZED`; `assert _BYPASS_AUTHORIZED is False` | reload + `not hasattr` ×3 (SUB-10), SUB-14 asserts unchanged | **EDITED (required by weld):** flag no longer importable; absence checks replace value checks. |
| `test_bypass_functions_only_callable_via_explicit_optin` | same name, edited | `a099ba460` | `inspect.signature(authorize_local_bypass)` has `reason` | `not hasattr` both opt-ins | **EDITED (required by weld):** no signature left to check; absence is the proof. |
| `test_seam_quarantines_are_off_by_default` | same name, edited | `a099ba460` | `"_BYPASS_AUTHORIZED: bool = False" in content`; `"KaliBypassNotAuthorized" in content` | `... not in content` for all four definition strings | **EDITED (required by weld):** definitions removed; absence checks replace presence checks. |
| — | `test_sub10_kali_client_fails_closed` (new) | `a099ba460` | — | asserts symbol absence + `run()` raises documented `RuntimeError` | **ADDED:** institutional fail-closed proof for the welded path. |

**Test-count delta:** deny file 5→5, no-production-bypass 2→2, runtime-no-seam 3→3, new file +1. Guardrail total 26 (was 25 at SUB-14 acceptance: 24 + SUB-13 test; now +1 SUB-10 test). Full floor 292→293 (+1).

**No weakening:** every replacement swaps a presence/default check for an absence check on the same symbol; SUB-14 assertions untouched.

---

## W-C — COMPLETE WELD CONTRACT PROOF

### W-C.1 — Parity: PARITY-BY-UNREACHABILITY

The canonical Runtime does not import `orchestrator.kali_tools_client` (0 occurrences in the B-1a static closure of 31 orchestrator modules; 0 in the loaded closure of 50 modules). It never reached SUB-10 before the weld and does not reach it after. Canonical behavior is therefore unchanged. Full floor 292→293 with 0 failures confirms no canonical regression.

### W-C.2 — Bypass negative proof (institutional test)

**Test source** (`tests/test_p2_guardrail_sub10_closed.py`, verbatim — see file, 66 lines; key body):
```python
    from orchestrator import kali_tools_client
    from orchestrator.kali_tools_client import KaliToolsClient

    # 1. Legacy bypass symbols must be removed.
    assert not hasattr(kali_tools_client, "_run_local")
    assert not hasattr(kali_tools_client, "authorize_local_bypass")
    assert not hasattr(kali_tools_client, "KaliBypassNotAuthorized")
    assert not hasattr(KaliToolsClient, "authorize_local_bypass")

    # 2. run() must raise the documented RuntimeError when the API is unavailable.
    client = KaliToolsClient(base_url="http://127.0.0.1:1")
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(client.run("echo", "test", 5))

    error_msg = str(exc_info.value)
    assert "kali_tools_client._run_local is removed in WELD-SUB10" in error_msg
    assert "All execution must go through the broker-gated capability" in error_msg
```

**Actual targeted transcript:**
```
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_sub10_closed.py tests/test_p2_guardrail_deny_by_default.py tests/test_p2_guardrail_no_production_bypass.py tests/test_p2_guardrail_runtime_no_seam.py -v --no-header
... 10 passed, 1 failed (pre-logger-fix NameError) ...
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_sub10_closed.py -v --no-header
tests/test_p2_guardrail_sub10_closed.py::test_sub10_kali_client_fails_closed PASSED [100%]
1 passed in 0.13s
```
(Note: the first run exposed the latent missing-`logger` defect; after adding the one-line `logger` definition, the test passes. See W-A.2.)

**Direct negative-path transcript (machine-captured):**
```
has _run_local: False
has authorize_local_bypass: False
has KaliBypassNotAuthorized: False
has _BYPASS_AUTHORIZED: False
has instance authorize_local_bypass: False
AttributeError: module 'orchestrator.kali_tools_client' has no attribute '_run_local'
```

**Documented RuntimeError** (`src/orchestrator/kali_tools_client.py`, both `run()` failure branches):
```python
raise RuntimeError(
    "kali_tools_client._run_local is removed in WELD-SUB10. "
    "All execution must go through the broker-gated capability."
)
```

**Logging:** `run()` logs `logger.debug("Remote execution failed for {tool}, no local fallback (WELD-SUB10): {e}")` in the remote-failure branch before raising; the `RuntimeError` itself surfaces in the exception traceback (no speculative DecisionTrace claim: DecisionTrace capture for legacy-envelope errors is NOT ESTABLISHED BY AVAILABLE EVIDENCE beyond the logged debug line and the raised error).

### W-C.3 — Invariants (machine-captured)

```
$ PYTHONPATH=src python3 -m pytest tests/test_g3_en5_organ_wiring.py tests/test_p2_guardrail_inv1.py tests/test_g2_c2_fail_closed.py --no-header -q
25 passed, 1 warning in 0.80s
```
- Single PDP (`test_g3_en5_single_pdp`), single loop (`test_g3_en5_single_cognitive_loop`), INV-2 (`test_g3_en5_inv2_preserved`), INV-1/CONV-3 (`test_p2_guardrail_inv1.py`), fail-closed (`test_g2_c2_fail_closed.py`) all pass.
- SUB-14/SUB-13 behavior untouched: `grep` confirms no `authorize_bypass`/`_subprocess_fallback` reintroduction; SUB-14 guardrail asserts unchanged and passing.

### W-C.4 — P3.1 reconciliation (post-organ-wiring inventory)

- **SUB-14:** WELDED / ACCEPTED (unchanged)
- **SUB-13:** CLOSED-BY-FOLD / ACCEPTED as part of SUB-14 (unchanged)
- **SUB-10:** WRAPPED/LIVE → **WELDED** (this round, commit `a099ba460`)
- **SHELL:** DEFERRED, untouched

### W-C.5 — Seam ledger

- **SUB-10:** WRAPPED → WELDED at commit `a099ba460`
- **SUB-13/SUB-14:** unchanged, accepted
- **Policy artifact:** none (removal weld; fail-closed `RuntimeError` is the enforcement)

### W-C.6 — Post-weld Arena closure (machine-captured)

```
ORCHESTRATOR_MODULES_IN_STATIC_CLOSURE=31
ARENA_MODULES_IN_STATIC_CLOSURE=0
ORCHESTRATOR_AND_ARENA_MODULES_AFTER_EPISODE=50
ARENA_MODULES_AFTER_EPISODE=0
STATIC_ARENA_FREE: True
EPISODE_ARENA_FREE: True
kali_tools_client occurrences in closure: 0
```

---

## W-D — PROVENANCE (three-state model)

### W-D.1 — Implementation / pre-evidence capture state

```
$ git rev-parse HEAD
a099ba460d1cf47c5a14189b3fda7f36bd98ac61

$ git branch --show-current
weld-sub10-evidence

$ git rev-list --count 7272880f7..HEAD
52

$ git status -sb
## weld-sub10-evidence
 M src/orchestrator/kali_tools_client.py
 M tests/test_p2_guardrail_deny_by_default.py
 M tests/test_p2_guardrail_no_production_bypass.py
 M tests/test_p2_guardrail_runtime_no_seam.py
?? tests/test_p2_guardrail_sub10_closed.py
```
(Pre-commit capture; the five files above are exactly the implementation set.)

```
$ git rev-list --parents -n 1 a099ba460
a099ba460d1cf47c5a14189b3fda7f36bd98ac61 2caeb4923a2150ceac13fa9a69bb9b2d3fbce06b
```

### W-D.2 — Final actual repository state (post-evidence commit)

Established by external machine verification of the records-only evidence commit that adds this file. The evidence file cannot embed the hash of the commit that contains it (self-reference rule). Final HEAD is the direct child of `a099ba460` on branch `weld-sub10-evidence`; final count is therefore 53 (52 + 1 evidence commit). Verify externally with `git log --oneline -n 2 weld-sub10-evidence`.

### W-D.3 — Evidence commit relationship

Implementation commit `a099ba460` (parent) → evidence commit (child, this file only). Verifiable by `git diff <impl>..<final> --stat` showing only `evidence/phases/P3_0/WELD-SUB10_EVIDENCE.md`.

## Final test floor

Previous floor (SUB-14 acceptance): 292 passed, 0 failed, 0 skipped, 0 xfail.
New floor: **293 passed**, 0 failed, 0 skipped, 0 xfail (delta **+1**, the new SUB-10 institutional test).
Guardrails: **26** (was 25 at SUB-14 acceptance).

## Seam ledger / SUB-10 disposition

**SUB-10: WRAPPED/LIVE → WELDED** at commit `a099ba460`. SUB-14/SUB-13 accepted states unchanged. SHELL deferred, untouched.

## Outstanding caveats

1. Unused imports (`asyncio`, `subprocess`) remain in `kali_tools_client.py` as dead imports; no behavior. Left intentionally to keep the diff minimal.
2. DecisionTrace capture for legacy-envelope `RuntimeError`s is NOT ESTABLISHED BY AVAILABLE EVIDENCE beyond the logged debug line and raised error.
3. `KaliToolsClient.run()` remote-success path (httpx) is legacy behavior, preserved unchanged.

## GLM adjudication handoff

SUB-10 evidence prepared for GLM artifact-only adjudication.

---

## BD-S10 COMPLETION APPENDIX (post-weld verification at current HEAD)

This appendix was added in a records-only commit on top of the
implementation commit. No source or test files changed in this appendix
round; this is an evidence-only update (R-W2: no implementation tests
removed or rewritten here).

### BD-S10-1 — Post-weld closure instruments (re-run at current HEAD)

Command:

```
$ PYTHONPATH=src python3 evidence/phases/P3_0/_b1a_probe.py
```

STATIC (verbatim):

```
======================================================================
B-1a INSTRUMENT 1: STATIC TRANSITIVE IMPORT-CLOSURE (AST)
======================================================================
ORCHESTRATOR_MODULES_IN_STATIC_CLOSURE=31
ARENA_MODULES_IN_STATIC_CLOSURE=0
---STATIC_CLOSURE_MODULES---
orchestrator.brain.action
orchestrator.brain.belief_transition_policy
orchestrator.brain.candidate_generators.student_generator
orchestrator.brain.capability_broker
orchestrator.brain.contradiction
orchestrator.brain.defeater_types
orchestrator.brain.evidence
orchestrator.brain.hypothesis
orchestrator.brain.plan_decision
orchestrator.brain.rate_limiter
orchestrator.brain.scope_parser
orchestrator.brain.semantic_types
orchestrator.brain.trust
orchestrator.brain.waf_detector
orchestrator.brain.world
orchestrator.capabilities.interactive_shell.capability
orchestrator.capabilities.interactive_shell.command_filter
orchestrator.capabilities.interactive_shell.listener_manager
orchestrator.capabilities.interactive_shell.session
orchestrator.exec.safe_capability
orchestrator.hardening.action_receipt
orchestrator.runtime
orchestrator.runtime.loop
orchestrator.runtime.organs
orchestrator.runtime.policy
orchestrator.runtime.safe_proving_capability
orchestrator.runtime.stages
orchestrator.runtime.types
orchestrator.student.payload_mutator
orchestrator.student.stack_matcher
orchestrator.student.student
```

LOADED (verbatim):

```
======================================================================
B-1a INSTRUMENT 2: LOADED-MODULE WALK AFTER FULL EPISODE
======================================================================
ORCHESTRATOR_AND_ARENA_MODULES_AFTER_EPISODE=50
ARENA_MODULES_AFTER_EPISODE=0
---LOADED_RUNTIME_CLOSURE_MODULES---
orchestrator.brain
orchestrator.brain.action
orchestrator.brain.candidate_generators
orchestrator.brain.candidate_generators.student_generator
orchestrator.brain.capability_broker
orchestrator.brain.contradiction
orchestrator.brain.evidence
orchestrator.brain.hypothesis
orchestrator.brain.neural_memory
orchestrator.brain.phases
orchestrator.brain.phases.models
orchestrator.brain.rate_limiter
orchestrator.brain.scope_parser
orchestrator.brain.skill_indexer
orchestrator.brain.strategy_learner
orchestrator.brain.target_profiler
orchestrator.brain.target_state
orchestrator.brain.trust
orchestrator.brain.waf_detector
orchestrator.brain.world
orchestrator.capabilities
orchestrator.capabilities.interactive_shell
orchestrator.capabilities.interactive_shell.capability
orchestrator.capabilities.interactive_shell.command_filter
orchestrator.capabilities.interactive_shell.listener_manager
orchestrator.capabilities.interactive_shell.reverse_shell
orchestrator.capabilities.interactive_shell.session
orchestrator.capabilities.interactive_shell.ssh_shell
orchestrator.capabilities.interactive_shell.tty_normalizer
orchestrator.exec
orchestrator.exec.inv1_guard
orchestrator.exec.safe_capability
orchestrator.hardening
orchestrator.hardening.action_receipt
orchestrator.runtime
orchestrator.runtime.loop
orchestrator.runtime.organs
orchestrator.runtime.policy
orchestrator.runtime.safe_proving_capability
orchestrator.runtime.stages
orchestrator.runtime.types
orchestrator.student
orchestrator.student.chain_synthesizer
orchestrator.student.coverage_gap_filler
orchestrator.student.integration_pipeline
orchestrator.student.knowledge_background_service
orchestrator.student.payload_mutator
orchestrator.student.research_scheduler
orchestrator.student.stack_matcher
orchestrator.student.student

======================================================================
VERDICTS
======================================================================
STATIC_ARENA_FREE: True
EPISODE_ARENA_FREE: True
```

Explicit verdicts: STATIC — 31 orchestrator modules / 0 Arena; LOADED — 50 modules / 0 Arena. `orchestrator.kali_tools_client` occurrences in both closures: 0. No canonical Runtime reachability to SUB-10. PARITY-BY-UNREACHABILITY confirmed at the current post-weld HEAD.

### BD-S10-2 — Source-side routing statement

1. `KaliToolsClient.run()` first uses the pre-existing remote HTTP/API path (`httpx.AsyncClient` POST to `{base_url}/run` under the timeout guard).
2. The retained `httpx` network primitive is pre-existing legacy behavior; it was not introduced by this weld.
3. SUB-10 is legacy-envelope-only: the ~30 wrapper callers and the deprecated Head-1 loop sit outside the canonical Runtime closure.
4. The canonical Runtime does not import or invoke `kali_tools_client` (0 occurrences in both B-1a closures above).
5. On remote failure (`GuardTimeout`, `httpx.ConnectError`, any `Exception`) or local-force conditions (`FORCE_LOCAL` / `_use_local`), execution now FAILS CLOSED with `RuntimeError("kali_tools_client._run_local is removed in WELD-SUB10. All execution must go through the broker-gated capability.")`.
6. The local subprocess fallback (`_run_local`, `asyncio.create_subprocess_exec`) has been removed; `grep` at the implementation commit confirms `async def _run_local` NOT FOUND and `class KaliBypassNotAuthorized` NOT FOUND.
7. No new unbrokered canonical primitive path exists: the canonical surface never reached this module.
8. The weld narrows the legacy envelope: local subprocess execution → fail-closed RuntimeError.

### BD-S10-3 — Seam ledger (exact sequence state)

- SUB-14: WELDED — `740861f2e` (accepted, unchanged)
- SUB-13: CLOSED-BY-FOLD — `740861f2e` (accepted as part of SUB-14, unchanged)
- SUB-10: WELDED — `a099ba460` (this round; third closed seam in the sequence)
- SHELL: DEFERRED / SD-1 — next in fixed sequence, locked pending SUB-10 acceptance

### BD-S10-4 — P3.1 reconciliation (SUB-10 row)

| Seam | Previous state | Current disposition | Implementation commit | Evidence status |
|---|---|---|---|---|
| SUB-10 | WRAPPED / LIVE | WELDED | `a099ba460` | prepared for artifact-only adjudication |
| SUB-14 | WELDED / ACCEPTED | unchanged, accepted | `740861f2e` | accepted |
| SUB-13 | CLOSED-BY-FOLD / ACCEPTED | unchanged, accepted | `740861f2e` (+ `258a9894` institutional proof) | accepted |
| SHELL | DEFERRED | deferred, untouched | — | pending SUB-10 acceptance |

### Riding one-liners

1. FLOOR BREAKDOWN: 239 legacy + 8 P2.1 walking skeleton + 9 G2-C2 fail-closed + 26 P2 guardrail + 11 G3-EN-5 = 293.
2. GUARDRAIL REGISTER: 25 → 26 due to the new SUB-10 institutional test (`test_sub10_kali_client_fails_closed`).
3. GIT LINEAGE (machine-captured at implementation commit, pre-evidence commit): `2caeb4923 ↓ a099ba460 ↓ evidence commit` (this file only). Implementation/pre-evidence count: 52. Final count is 53 after the evidence commit (52 + 1); see W-D.2. The guardrail count changed 25 → 26 (it did not stay unchanged).

### R-W1 provenance note for this appendix

A. Implementation state: commit `a099ba460`, count 52, five implementation files (one production, three guardrail rewrites, one new test).
B. Evidence-commit state: this file added on top of `a099ba460`; count therefore 53.
C. Authoritative current state: established by external machine verification after this records-only commit (see W-D pattern). This file does not embed its own commit hash (self-reference rule).

### R-W2 note for this appendix

This appendix round is evidence-only: no implementation tests were removed or rewritten here. The accepted W-B transition record above is unchanged.
