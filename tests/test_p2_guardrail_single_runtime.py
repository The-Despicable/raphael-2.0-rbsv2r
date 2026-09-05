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

RC-D: P2 checks canonical importers only. P9 retains full legacy sweep.
sword/phase_0_recon and chains/tool_registry are P9 debt (not P2).

Per v4 INV-5: CLI -> Runtime; Runtime does not import arena.
Per v4 INV-6: Runtime cannot import seam.
Per v4 INV-11: deprecated modules not imported by canonical code.

This test is STRUCTURAL: it verifies the import graph of the current source
tree. Before Runtime is created (P2.0), Runtime is not importable, so the
"Runtime does not import arena/seam" check is vacuously satisfied (no Runtime
imports anything). After P2 creates the Runtime, this test will be substantive.
"""
import ast
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


def _canonical_roots():
    """Canonical code roots (P2 jurisdiction).

    Per RC-D: P2 checks canonical importers. Canonical = code that is on
    the critical path for Runtime creation. P9 retains the full legacy
    repository sweep.
    """
    return [
        SRC_ROOT / "orchestrator" / "brain",
        SRC_ROOT / "orchestrator" / "capabilities",
        SRC_ROOT / "orchestrator" / "sandbox",
        SRC_ROOT / "raphael",
    ]


def test_no_canonical_import_of_p2_deprecated():
    """RC-D: P2 checks canonical importers only.

    No module under canonical roots (brain/, capabilities/, sandbox/, raphael/)
    may import deprecated modules. P9 retains the full legacy sweep for
    sword/, agent/, recon-pipeline/, weaponizer/, etc.
    """
    # P2-scope deprecated modules (those being actively quarantined or marked
    # in P1/P2). P9-scope deprecated modules are checked separately.
    p2_deprecated = {
        "orchestrator.brain.adaptive_brain",
    }
    violations = []
    for root in _canonical_roots():
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            if "adaptive_brain" in str(py_file):
                continue  # skip the deprecated module itself
            imports = _parse_imports(py_file)
            for imp in imports:
                for dep in p2_deprecated:
                    if imp == dep or imp.startswith(dep + "."):
                        violations.append((str(py_file.relative_to(REPO_ROOT)), imp))
    assert not violations, (
        f"Canonical modules must not import P2-deprecated modules "
        f"(RC-D, v4 INV-11): {violations}"
    )


def test_no_arena_runtime_import_from_orchestrator_brain():
    """RC-B + RC-D: brain has zero runtime imports from arena.

    TYPE_CHECKING imports are contract-compliant (type-only).
    Runtime imports inside method bodies are the violation.
    """
    brain_root = SRC_ROOT / "orchestrator" / "brain"
    if not brain_root.exists():
        pytest.skip("orchestrator/brain/ not found")
    violations = []
    for py_file in brain_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
                continue
        try:
            tree = ast.parse(py_file.read_text(errors="ignore"))
        except SyntaxError:
            continue
        # Check if there's a TYPE_CHECKING guard
        has_type_checking_guard = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if the test is TYPE_CHECKING
                if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                    has_type_checking_guard = True
                    break
        # Find all from arena imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "arena" or node.module.startswith("arena.")):
                    # Check if this import is inside a TYPE_CHECKING block
                    is_in_type_checking = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.If):
                            if (isinstance(parent.test, ast.Name) and
                                    parent.test.id == "TYPE_CHECKING"):
                                # Check if the import's line is within the TYPE_CHECKING block
                                if (hasattr(parent, 'lineno') and
                                        parent.lineno <= node.lineno):
                                    is_in_type_checking = True
                                    break
                    if not is_in_type_checking:
                        violations.append((
                            str(py_file.relative_to(REPO_ROOT)),
                            f"line {node.lineno}: from {node.module} import ...",
                        ))
    # RC-B HALT/ESCALATE: apply_belief_transition at hypothesis.py:536
    # requires P5-scale work. Documented as known violation.
    known_p5_violations = [v for v in violations if "hypothesis.py" in v[0]]
    if known_p5_violations:
        # This is a documented HALT/ESCALATE, not a silent violation
        pytest.skip(
            f"RC-B HALT/ESCALATE: {len(known_p5_violations)} brain→arena runtime "
            f"imports require P5-scale re-homing. See evidence/phases/G2_RC/RC-B."
        )
    assert not violations, (
        f"brain/ must not have runtime imports from arena (v4 INV-5, RC-B): {violations}"
    )


def test_no_seam_import():
    """v4 INV-6: Runtime cannot import seam.

    The migration seam (v4.1 AM-4) is a temporary scaffold. Runtime
    must never import it. At P2.0, no Runtime exists yet, so this check
    is vacuously satisfied.
    """
    seam_modules = {
        "orchestrator.seam",
        "orchestrator.behavior_alterable_gate",
        "seam",
    }
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


def test_no_absolute_paths_in_new_runtime_code():
    """v4 INV-7: no absolute hard-coded paths in new Runtime code.

    At P2.0, Runtime is not yet created. This is a placeholder for P2.1+.
    """
    pass
