"""
P2 Guardrail Test 2: deprecated-import guard (v4 INV-11)

Per v4 master roadmap:
- section 24: INV-11 deprecated modules not imported by canonical code
- v4.1 AM-7: "advisory (warn-only) at P1, enforced (build-breaking) from P2
  onward, since P1 has no Runtime to violate it yet"

Deprecated modules (per v4 P1.2 + P0 inventory):
- orchestrator.weaponizer (SUB-01,02,03)
- orchestrator.chains.tool_registry (SUB-04)
- orchestrator.c2.sliver_backend (SUB-05,06)
- orchestrator.c2.implant_builder (SUB-07,08,09)
- recon-pipeline (SUB-11)
- agent.modules.executor (SUB-12)
- sword.phase_0_recon (SUB-15,16,17)
- orchestrator.brain.adaptive_brain (31-line counter stub, v4 P1.2)
- orchestrator.brain.adaptive_brain.adaptive_brain
"""
import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

DEPRECATED_MODULES = {
    "orchestrator.weaponizer",
    "orchestrator.weaponizer.weaponizer_engine",
    "orchestrator.chains.tool_registry",
    "orchestrator.c2.sliver_backend",
    "orchestrator.c2.implant_builder",
    "recon-pipeline",
    "recon-pipeline.main",
    "agent.modules.executor",
    "sword",
    "sword.phase_0_recon",
    "orchestrator.brain.adaptive_brain",
    "orchestrator.brain.adaptive_brain.adaptive_brain",
}


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


def test_no_canonical_module_imports_deprecated():
    """v4 INV-11: deprecated modules not imported by canonical code.

    Canonical code is defined as: code under src/orchestrator/brain/,
    src/orchestrator/capabilities/, src/orchestrator/sandbox/, and
    src/raphael/ (Head 1 organics being absorbed).
    """
    canonical_roots = [
        SRC_ROOT / "orchestrator" / "brain",
        SRC_ROOT / "orchestrator" / "capabilities",
        SRC_ROOT / "orchestrator" / "sandbox",
        SRC_ROOT / "raphael",
    ]
    violations = []
    for root in canonical_roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            # Skip deprecated files themselves (they may import each other)
            rel = str(py_file.relative_to(REPO_ROOT))
            if any(dep in rel for dep in ["adaptive_brain", "weaponizer",
                                           "tool_registry", "sliver_backend",
                                           "implant_builder", "phase_0_recon"]):
                continue
            imports = _parse_imports(py_file)
            for imp in imports:
                for dep in DEPRECATED_MODULES:
                    if imp == dep or imp.startswith(dep + "."):
                        violations.append((rel, imp))
    assert not violations, (
        f"Canonical modules must not import deprecated modules "
        f"(v4 INV-11): {violations}"
    )


def test_adaptive_brain_not_imported_by_canonical():
    """v4 P1.2: AdaptiveBrain is a deprecation target.

    AdaptiveBrain is a 31-line counter stub. It must not be imported
    by canonical code.
    """
    violations = []
    canonical_roots = [
        SRC_ROOT / "orchestrator" / "brain",
        SRC_ROOT / "orchestrator" / "capabilities",
        SRC_ROOT / "orchestrator" / "sandbox",
        SRC_ROOT / "raphael",
    ]
    for root in canonical_roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            if "adaptive_brain" in str(py_file):
                continue
            imports = _parse_imports(py_file)
            for imp in imports:
                if "adaptive_brain" in imp:
                    violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"AdaptiveBrain must not be imported by canonical code "
        f"(v4 P1.2 deprecation): {violations}"
    )
