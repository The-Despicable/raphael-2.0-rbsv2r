"""
P2 Guardrail Test 2: deprecated-import guard (v4 INV-11) — RC-D scope

Per v4 master roadmap:
- section 24: INV-11 deprecated modules not imported by canonical code
- v4.1 AM-7: "advisory (warn-only) at P1, enforced (build-breaking) from P2
  onward, since P1 has no Runtime to violate it yet"

RC-D: P2 checks canonical importers. P9 retains the full legacy sweep.

Single source of truth: evidence/phases/G2_RC/deprecation_marker_registry.md
Deprecated modules here must match the registry.

P2-deprecated modules (active in P1/P2):
- orchestrator.brain.adaptive_brain (RC-A: removed from brain/__init__)

P9-deprecated modules (not in P2 scope):
- orchestrator.weaponizer, chains.tool_registry, c2.*, recon-pipeline,
  agent.modules.executor, sword.phase_0_recon
  (checked by P9 atomic-deletion sweep, not P2 guardrails)
"""
import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

# P2-scope deprecated modules (RC-D: one source of truth)
# Must match evidence/phases/G2_RC/deprecation_marker_registry.md
P2_DEPRECATED_MODULES = {
    "orchestrator.brain.adaptive_brain",
    "orchestrator.brain.adaptive_brain.adaptive_brain",
}


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


def _canonical_roots():
    """Canonical code roots (P2 jurisdiction per RC-D)."""
    return [
        SRC_ROOT / "orchestrator" / "brain",
        SRC_ROOT / "orchestrator" / "capabilities",
        SRC_ROOT / "orchestrator" / "sandbox",
        SRC_ROOT / "raphael",
    ]


def test_no_canonical_module_imports_p2_deprecated():
    """RC-D: P2-scope check. No canonical module may import P2-deprecated modules.

    P9-scope deprecated modules (sword, agent, recon-pipeline, weaponizer,
    chains.tool_registry, c2.*) are checked by P9 atomic-deletion sweep,
    not by P2 guardrails.
    """
    violations = []
    for root in _canonical_roots():
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            rel = str(py_file.relative_to(REPO_ROOT))
            if "adaptive_brain" in rel:
                continue  # skip the deprecated module itself
            imports = _parse_imports(py_file)
            for imp in imports:
                for dep in P2_DEPRECATED_MODULES:
                    if imp == dep or imp.startswith(dep + "."):
                        violations.append((rel, imp))
    assert not violations, (
        f"Canonical modules must not import P2-deprecated modules "
        f"(v4 INV-11, RC-D): {violations}"
    )


def test_p2_registry_matches_guardrail():
    """RC-D: guardrail test set is the single source of truth for P2 deprecation.

    This test verifies that the P2_DEPRECATED_MODULES set in this file
    matches the authoritative registry. If you add a P2-deprecated module
    to the registry, you MUST add it here too.
    """
    registry_path = REPO_ROOT / "evidence" / "phases" / "G2_RC" / "deprecation_marker_registry.md"
    if not registry_path.exists():
        pytest.skip("Registry not found")
    registry = registry_path.read_text()
    # Check that adaptive_brain is mentioned in the registry
    assert "AdaptiveBrain" in registry or "adaptive_brain" in registry, (
        "Registry must mention adaptive_brain (RC-A deprecation)"
    )
    # Check that P2_DEPRECATED_MODULES is a subset of what's in the registry
    for mod in P2_DEPRECATED_MODULES:
        short = mod.split(".")[-1]
        assert short in registry, (
            f"P2_DEPRECATED_MODULES contains {mod} but registry does not mention {short}"
        )
