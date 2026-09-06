"""
P2 Guardrail Test 3: Runtime -> seam prohibition (v4 INV-6 + v4.1 AM-4)

Per v4 master roadmap:
- section 24: INV-6 Runtime cannot import seam
- section 12.4: "seam cannot be imported by Runtime"
- section 12.5: "Runtime -> seam dependency" check
- v4.1 AM-4.1: "seam can never be imported by canonical Runtime"
- v4.1 AM-13.3: "armed at P1 (present in CI, but structurally unable to fail
  since no Runtime exists yet) and substantive at P2"

At P2.0, Runtime is not yet created. This test verifies:
1. No existing module under orchestrator/ or raphael/ imports a seam module
2. The seam interface (if it exists) is never imported by code that could
   become Runtime
After WELD-SUB14, the _subprocess_fallback method is removed from Executor.
"""
import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

# Seam module names (per v4.1 AM-4: single typed proxy SeamRoute)
SEAM_MODULE_PATTERNS = [
    "orchestrator.seam",
    "orchestrator.behavior_alterable_gate",
    "seam",
    "behavior_alterable_gate",
    "seam_route",
]


def _parse_imports(py_file: Path) -> set:
    try:
        tree = ast.parse(py_file.read_text(errors="ignore"))
    except SyntaxError:
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_no_seam_module_exists():
    """v4.1 AM-4: the seam is a single typed proxy.

    At P2.0, the seam exists only as quarantine flags on SUB-10 and SUB-14
    (not as a separate module). No module named 'seam' or
    'behavior_alterable_gate' should exist.
    """
    for pattern in SEAM_MODULE_PATTERNS:
        parts = pattern.split(".")
        candidate = SRC_ROOT.joinpath(*parts).with_suffix(".py")
        if candidate.exists():
            pytest.fail(
                f"Seam module {pattern} exists as a separate file. "
                f"Per v4.1 AM-4, the seam is a single typed proxy, not a "
                f"separate module. File: {candidate}"
            )
        candidate_dir = SRC_ROOT.joinpath(*parts)
        if candidate_dir.is_dir():
            init_file = candidate_dir / "__init__.py"
            if init_file.exists():
                pytest.fail(
                    f"Seam package {pattern} exists. Per v4.1 AM-4, the seam "
                    f"is a single typed proxy, not a separate package. "
                    f"Directory: {candidate_dir}"
                )


def test_no_orchestrator_imports_seam_pattern():
    """v4 INV-6: Runtime cannot import seam.

    No module under orchestrator/ or raphael/ should import a seam
    module by name.
    """
    violations = []
    for root_name in ["orchestrator", "raphael"]:
        root = SRC_ROOT / root_name
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            imports = _parse_imports(py_file)
            for imp in imports:
                for pattern in SEAM_MODULE_PATTERNS:
                    if imp == pattern or imp.startswith(pattern + "."):
                        violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"No module under orchestrator/ or raphael/ may import the seam "
        f"(v4 INV-6): {violations}"
    )


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
    # Check SUB-14: _subprocess_fallback method is removed
    executor_file = SRC_ROOT / "raphael" / "executor" / "executor.py"
    if executor_file.exists():
        content = executor_file.read_text()
        # The method should not exist
        assert "_subprocess_fallback" not in content, (
            "SUB-14 seam: _subprocess_fallback method must be removed after WELD-SUB14"
        )
        # Also check that the field _bypass_authorized is removed
        assert "_bypass_authorized" not in content, (
            "SUB-14 seam: _bypass_authorized field must be removed after WELD-SUB14"
        )
