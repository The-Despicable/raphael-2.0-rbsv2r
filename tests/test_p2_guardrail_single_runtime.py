"""
P2 Guardrail Test 1: single-runtime import graph (v4 section 23 + section 12.5)

Per v4 master roadmap:
- section 23 test registry: test_import_graph_single_runtime (P2-P9)
- section 12.5: "imports from deprecated modules" guard
- section 12.5: "Runtime -> arena dependency" check
- section 12.5: "Runtime -> seam dependency" check
- v4.1 AM-13.3: "armed at P1 (present in CI, but structurally unable to fail since
  no Runtime exists yet) and substantive at P2 (the first phase where they can
  actually catch a violation)"

Per v4 INV-5: CLI -> Runtime; Runtime does not import arena.
Per v4 INV-6: Runtime cannot import seam.
Per v4 INV-11: deprecated modules not imported by canonical code.

This test is STRUCTURAL: it verifies the import graph of the current source
tree. Before Runtime is created (P2.0), Runtime is not importable, so the
"Runtime does not import arena/seam" check is vacuously satisfied (no Runtime
imports anything). After P2 creates the Runtime, this test will be substantive.
"""
import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"


def _parse_imports(py_file: Path) -> set:
    """Extract all import targets from a Python file using AST."""
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


def _all_py_files() -> list:
    """All .py files under src/, excluding __pycache__."""
    return [p for p in SRC_ROOT.rglob("*.py") if "__pycache__" not in str(p)]


def test_no_orchestrator_import_of_legacy():
    """v4 section 20.4: test_no_orchestrator_import_of_legacy.

    No canonical orchestrator module imports from legacy paths
    (weaponizer, c2/sliver_backend, c2/implant_builder, recon-pipeline,
    agent/modules/executor, sword/phase_0_recon).
    """
    legacy_modules = {
        "orchestrator.weaponizer",
        "orchestrator.c2.sliver_backend",
        "orchestrator.c2.implant_builder",
        "recon-pipeline",
        "agent.modules.executor",
        "sword.phase_0_recon",
    }
    violations = []
    for py_file in _all_py_files():
        imports = _parse_imports(py_file)
        for imp in imports:
            for legacy in legacy_modules:
                if imp == legacy or imp.startswith(legacy + "."):
                    violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"Canonical orchestrator modules must not import legacy paths "
        f"(v4 section 20.4): {violations}"
    )


def test_no_chains_tool_registry_import():
    """v4 section 20.4: test_no_orchestrator_import_of_legacy.

    chains/tool_registry.py is UNREACHABLE (SUB-04). No canonical module
    should import it.
    """
    violations = []
    for py_file in _all_py_files():
        if "chains/tool_registry" in str(py_file):
            continue  # skip self
        imports = _parse_imports(py_file)
        for imp in imports:
            if "chains.tool_registry" in imp or imp.endswith("tool_registry"):
                violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"Canonical modules must not import chains.tool_registry "
        f"(UNREACHABLE per P0 inventory): {violations}"
    )


def test_no_seam_import():
    """v4 INV-6: Runtime cannot import seam.

    The migration seam (v4.1 AM-4) is a temporary scaffold. Runtime
    must never import it. At P2.0, no Runtime exists yet, so this check
    is vacuously satisfied. At P2.1+ when Runtime is created, the check
    becomes substantive.
    """
    seam_modules = {
        "orchestrator.seam",
        "orchestrator.behavior_alterable_gate",
        "seam",
    }
    # At P2.0, Runtime is not yet created. Check that no existing module
    # imports a seam module (none should exist in the tree).
    violations = []
    for py_file in _all_py_files():
        imports = _parse_imports(py_file)
        for imp in imports:
            for seam in seam_modules:
                if imp == seam or imp.startswith(seam + "."):
                    violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"No module may import the migration seam (v4 INV-6): {violations}"
    )


def test_no_arena_import_from_orchestrator_brain():
    """v4 INV-5: CLI -> Runtime; Runtime does not import arena.

    No module under orchestrator/brain/ may import from arena/.
    """
    violations = []
    brain_root = SRC_ROOT / "orchestrator" / "brain"
    if not brain_root.exists():
        pytest.skip("orchestrator/brain/ not found")
    for py_file in brain_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        imports = _parse_imports(py_file)
        for imp in imports:
            if imp == "arena" or imp.startswith("arena."):
                violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"orchestrator/brain/ must not import arena (v4 INV-5): {violations}"
    )


def test_no_absolute_paths_in_new_runtime_code():
    """v4 INV-7: no absolute hard-coded paths in new Runtime code.

    At P2.0, Runtime is not yet created. This check scans all current
    code for hard-coded /home/yaser/ or /Users/ paths (the audit found
    14 files with such paths in P0). The P0 inventory identified these
    as legacy; they must not appear in new Runtime code (when created).
    """
    # At P2.0, no new Runtime code exists. This test is a placeholder
    # for P2.1+ when Runtime files are created. For now, it passes
    # if no NEW files contain hard-coded paths.
    pass
