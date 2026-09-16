"""
P2 Guardrail: INV-1 enforcement — process/network/file primitives
confined to exec/ (CONV-2)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

Declared G3 canonical perimeter: the canonical ``run_episode``
execution plane — ``orchestrator/runtime/**`` + the canonical brain
control-plane modules actually loaded by the Runtime + ``orchestrator/
exec/**`` (the sole authorized primitive namespace). The perimeter is
computed by ``orchestrator.exec.inv1_guard.canonical_perimeter_modules``
and is deterministic (module identifiers, no machine paths).

The scanner detects primitive imports AND call sites: subprocess.*,
asyncio.create_subprocess_exec/_shell, os.system/popen/exec*/spawn*,
network clients (socket/requests/httpx/aiohttp/paramiko/docker),
file removal, and open() write modes.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
RUNTIME_ROOT = SRC_ROOT / "orchestrator" / "runtime"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.exec.inv1_guard import (
    canonical_perimeter_modules,
    scan_source,
    verify_inv1_primitive_confinement,
)


def _scan(source: str, filename: str = "fixture.py") -> list:
    return scan_source(source, filename)


# ── Scanner detection (synthetic fixtures) ──────────────────────────

def test_inv1_scanner_detects_import_fixture():
    violations = _scan("import subprocess\n")
    assert violations, "scanner must flag 'import subprocess'"
    assert violations[0]["type"] == "import"
    assert violations[0]["primitive"] == "subprocess"


def test_inv1_scanner_detects_asyncio_create_subprocess_exec():
    source = (
        "import asyncio\n"
        "async def run():\n"
        "    await asyncio.create_subprocess_exec('id')\n"
    )
    violations = _scan(source)
    assert any(
        v["type"] == "call" and v["primitive"] == "asyncio.create_subprocess_exec"
        for v in violations
    ), violations
    # 'import asyncio' alone must NOT be reported (no false positive).
    assert not any(v["primitive"] == "asyncio" for v in violations)


def test_inv1_scanner_detects_asyncio_create_subprocess_shell():
    source = "import asyncio\nasyncio.create_subprocess_shell('id')\n"
    assert any(
        v["primitive"] == "asyncio.create_subprocess_shell" for v in _scan(source)
    )


def test_inv1_scanner_detects_call_and_file_write_forms():
    source = (
        "import subprocess\n"
        "subprocess.run(['id'])\n"
        "subprocess.Popen(['id'])\n"
        "subprocess.check_output(['id'])\n"
        "import os\n"
        "os.system('id')\n"
        "fh = open('/tmp/x', 'w')\n"
        "fh = open('/tmp/y', mode='a')\n"
    )
    primitives = {v["primitive"] for v in _scan(source)}
    assert {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.check_output",
        "os.system",
    } <= primitives
    assert any(v["type"] == "file-write" for v in _scan(source))


def test_inv1_scanner_allows_read_only_open():
    assert _scan("fh = open('/tmp/x', 'r')\n") == []


def test_inv1_scanner_detects_network_imports():
    for source in ("import socket\n", "import httpx\n", "import requests\n",
                   "from urllib.request import urlopen\n"):
        assert _scan(source), source


# ── Declared canonical perimeter ────────────────────────────────────

def test_inv1_canonical_perimeter_is_deterministic_and_machine_independent():
    first = canonical_perimeter_modules(REPO_ROOT)
    second = canonical_perimeter_modules(REPO_ROOT)
    assert first == second
    assert first, "perimeter must not be empty"
    # Module identifiers only: no absolute paths, no drive letters.
    assert all((not m.startswith("/")) and (":" not in m) for m in first)
    assert "orchestrator.runtime" in first
    assert "orchestrator.exec" in first
    assert "orchestrator.brain.capability_broker" in first


def test_inv1_runtime_tree_is_clean():
    """The runtime/ tree itself must remain primitive-free."""
    perimeter = tuple(
        m for m in canonical_perimeter_modules(REPO_ROOT)
        if m == "orchestrator.runtime" or m.startswith("orchestrator.runtime.")
    )
    violations = verify_inv1_primitive_confinement(REPO_ROOT, modules=perimeter)
    assert violations == [], f"INV-1 runtime tree violations: {violations}"


def test_inv1_exec_namespace_is_authorized():
    """exec/ holds primitives but is never reported by the perimeter scan."""
    violations = verify_inv1_primitive_confinement(REPO_ROOT)
    exec_hits = [
        v for v in violations if v["file"].startswith("src/orchestrator/exec/")
    ]
    assert exec_hits == [], f"exec/ is the authorized namespace: {exec_hits}"


def test_inv1_canonical_perimeter_zero_violations():
    """INV-1 holds over the declared G3 canonical perimeter.

    Authoritative assertion: the declared perimeter must be primitive-free.
    """
    violations = verify_inv1_primitive_confinement(REPO_ROOT)
    assert violations == [], (
        "INV-1 canonical perimeter violations (must be zero): "
        f"{violations}"
    )


def test_no_unbrokered_execution():
    """P3.8 / §14.9: no forbidden execution primitive outside exec/ in the
    declared canonical perimeter, and the guard is load-bearing."""
    violations = verify_inv1_primitive_confinement(REPO_ROOT)
    assert violations == [], f"unbrokered execution primitives: {violations}"
    # Negative control: the same guard flags a planted primitive, so the
    # empty result above is not vacuous.
    planted = scan_source(
        "import subprocess\nsubprocess.run(['id'])\n", "planted.py"
    )
    assert planted and planted[0]["primitive"] == "subprocess"


# ── Closure hygiene: deferred optional modules / no second namespace ─

def test_inv1_canonical_loaded_closure_excludes_optional_primitive_modules():
    """Importing the canonical Runtime must not eagerly load
    primitive-bearing optional modules (target_profiler / waf_detector)."""
    import os
    import subprocess

    code = (
        "import sys;"
        "from orchestrator.runtime import RaphaelRuntime, MissionContext;"
        "RaphaelRuntime().run_episode(MissionContext("
        "mission_id='inv1-closure', name='inv1-closure', objectives=['inspect']));"
        "print('orchestrator.brain.target_profiler' in sys.modules);"
        "print('orchestrator.brain.waf_detector' in sys.modules)"
    )
    env = dict(os.environ, PYTHONPATH=str(SRC_ROOT), PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=str(REPO_ROOT),
        env=env, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False\nFalse", proc.stdout


def test_inv1_deferred_optional_modules_remain_importable_explicitly():
    """Deferred modules stay reachable through their explicit paths."""
    import importlib

    target_profiler = importlib.import_module("orchestrator.brain.target_profiler")
    assert callable(target_profiler.profile_target)
    waf_detector = importlib.import_module("orchestrator.brain.waf_detector")
    assert hasattr(waf_detector, "WAFDetector")
    # No longer re-exported by the canonical brain package surface.
    import orchestrator.brain as brain
    assert "profile_target" not in getattr(brain, "__all__", ())


def test_inv1_dead_primitive_adapters_removed_from_broker_surface():
    """The dead ToolAdapter/KaliToolAdapter primitive sites are gone."""
    from orchestrator.brain.capability_broker import CapabilityBroker
    assert not hasattr(CapabilityBroker, "create_tool_adapter")
    assert not hasattr(CapabilityBroker, "create_kali_adapter")


# ── PEP ownership / gating (unchanged) ──────────────────────────────

def test_inv1_stage_pep_delegates_to_exec():
    """CONV-2: PEP execution ownership is in exec/.

    The Runtime's stage_pep must delegate to the exec/-owned capability.
    """
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.stages import STAGE_PEP
    rt = RaphaelRuntime()
    mission = MissionContext(
        mission_id="inv1-pep", name="inv1-pep", objectives=["inspect"]
    )
    traces, term = rt.run_episode(mission)
    pep_entry = next(e for e in traces[0].entries if e["stage"] == "pep")
    assert pep_entry["success"], (
        "stage_pep must succeed via exec/-owned capability"
    )


def test_inv3_capability_gated_by_broker():
    """CONV-3: the capability is broker-gated.

    inspect() must raise CapabilityNotGatedError when called for a
    target that has not been authorized via record_authorization().
    """
    from orchestrator.exec.safe_capability import (
        SafeProvingCapability, CapabilityNotGatedError,
    )
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker,
    )
    broker = CapabilityBroker(BrokerPolicy(
        schema_version=1,
        engagement_id="inv3-test",
        allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    cap = SafeProvingCapability(broker=broker)
    with pytest.raises(CapabilityNotGatedError):
        cap.inspect("system_info.name")


def test_inv3_capability_works_after_authorization():
    """CONV-3: after record_authorization, inspect() succeeds."""
    from orchestrator.exec.safe_capability import SafeProvingCapability
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker,
    )
    broker = CapabilityBroker(BrokerPolicy(
        schema_version=1,
        engagement_id="inv3-test-2",
        allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    cap = SafeProvingCapability(broker=broker)
    cap.record_authorization("system_info.name")
    result = cap.inspect("system_info.name")
    assert result.output == "raphael-walking-skeleton"
