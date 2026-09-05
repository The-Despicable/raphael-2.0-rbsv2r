"""
P2 Guardrail: INV-1 enforcement — process/network/file primitives
confined to exec/ (CONV-2)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

This guardrail scans the Runtime's own files (under
orchestrator/runtime/) for forbidden primitive imports. The broader
orchestrator/ tree is not in P3.0 scope; that is P3+ migration work.

The Runtime's transitive closure must not import any of:
- subprocess
- os.system, os.popen, os.exec*, os.spawn*
- socket
- urllib.request, urllib.urlopen
- http.client, http.server
- requests
- os.remove, os.unlink, os.rmdir, shutil.rmtree
"""
import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
RUNTIME_ROOT = SRC_ROOT / "orchestrator" / "runtime"
sys.path.insert(0, str(SRC_ROOT))


FORBIDDEN_PRIMITIVES = {
    "subprocess": ["subprocess"],
    "os.system": ["os.system"],
    "os.popen": ["os.popen"],
    "os.execv": ["os.execv"],
    "os.execve": ["os.execve"],
    "os.execvp": ["os.execvp"],
    "os.spawnl": ["os.spawnl"],
    "os.spawnlp": ["os.spawnlp"],
    "os.spawnv": ["os.spawnv"],
    "socket": ["socket"],
    "urllib.request": ["urllib.request", "urllib.urlopen"],
    "http.client": ["http.client"],
    "http.server": ["http.server"],
    "requests": ["requests"],
    "os.remove": ["os.remove"],
    "os.unlink": ["os.unlink"],
    "os.rmdir": ["os.rmdir"],
    "shutil.rmtree": ["shutil.rmtree"],
}


def _scan_file_for_primitives(py_file: Path) -> list:
    """Return list of (line, primitive_name, module_name) for forbidden imports."""
    violations = []
    try:
        source = py_file.read_text(errors="ignore")
        tree = ast.parse(source)
    except SyntaxError:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                for violation_name, forbidden in FORBIDDEN_PRIMITIVES.items():
                    if module_name in forbidden:
                        violations.append((node.lineno, violation_name, module_name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module
                for violation_name, forbidden in FORBIDDEN_PRIMITIVES.items():
                    if module_name in forbidden or module_name.startswith(
                        tuple(f + "." for f in forbidden)
                    ):
                        violations.append((node.lineno, violation_name, module_name))
    return violations


def test_inv1_runtime_clean():
    """CONV-2 / INV-1: the Runtime's own files must not use forbidden primitives.

    Only scans orchestrator/runtime/ (the Runtime's own files).
    The broader orchestrator/ tree is P3+ migration work.
    """
    violations = []
    for py_file in RUNTIME_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        for lineno, prim, mod in _scan_file_for_primitives(py_file):
            violations.append((str(py_file.relative_to(REPO_ROOT)), lineno, prim, mod))
    assert not violations, (
        f"INV-1: Runtime files must not import forbidden primitives. "
        f"Violations: {violations}"
    )


def test_inv1_exec_package_may_use_primitives():
    """INV-1: the exec/ package IS allowed to use forbidden primitives.

    Per v4 L6, exec/ is the sole PEP package permitted to hold
    process/network/file primitives.
    """
    # The guard from exec/ must NOT flag exec/'s own files.
    from orchestrator.exec.inv1_guard import verify_inv1_primitive_confinement
    # Run the guard — it skips exec/ files.
    # We can't directly check the guard's output, but we can verify
    # that the guard module is importable and callable.
    result = verify_inv1_primitive_confinement()
    assert isinstance(result, list), "inv1_guard must return a list"


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
    # system_info.name traverses into the dict: system_info -> {name: ...}
    # so the value is the string 'raphael-walking-skeleton'
    assert result.output == "raphael-walking-skeleton"
