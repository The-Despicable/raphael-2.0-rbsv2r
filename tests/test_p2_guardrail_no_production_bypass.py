"""
P2 Guardrail Test 5: negative test — no production module calls authorize_* bypass APIs

Per v4 master roadmap:
- v4.1 AM-4.2: "The seam is OFF by default. Welding is P3 work."
- v4.1 AM-4.4: "Rollback discipline. If a welded site needs to be reverted
  during remediation, the fix is to rework the Broker-mediated path, never
  to re-open the deleted legacy branch or flip the seam back to a persistent
  OFF state."
- evidence/phases/P1/03_seam_work/SEAM_SITES.md: "If anyone (test, legacy code,
  future agent) needs to bypass, they must call authorize_bypass(reason=...) or
  authorize_local_bypass(reason=...) with a documented reason."

This test verifies that NO production module (under src/orchestrator/ or
src/raphael/) calls authorize_bypass() or authorize_local_bypass().

Exception: test files under tests/ MAY call these functions (they are
explicitly allowed to opt-in for testing).
"""
import ast
import inspect
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
TESTS_ROOT = REPO_ROOT / "tests"

# Functions that opt-in to the seam (must NOT be called from production code)
# Note: authorize_bypass is removed in WELD-SUB14, so we only check for authorize_local_bypass in production
# However, we keep the set for completeness and to avoid breaking the AST function if the string appears in comments.
BYPASS_FUNCTIONS = {
    "authorize_bypass",
    "authorize_local_bypass",
}


def _find_bypass_calls(py_file: Path):
    """Find all calls to bypass functions that are NOT inside the function
    definition of the same name.

    Returns a list of (line_number, function_name) tuples.
    """
    try:
        tree = ast.parse(py_file.read_text(errors="ignore"))
    except SyntaxError:
        return []

    # First, find all function definitions of bypass functions
    bypass_defs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in BYPASS_FUNCTIONS:
                bypass_defs.append(node)

    # Second, find all calls to bypass functions
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = None
            if isinstance(node.func, ast.Name):
                call_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                call_name = node.func.attr
            if call_name in BYPASS_FUNCTIONS:
                # Check if this call is inside a function definition with
                # the same name (i.e., the definition itself, not a real call)
                is_definition = False
                for fn_node in bypass_defs:
                    if fn_node.name != call_name:
                        continue
                    fn_start = fn_node.lineno
                    fn_end = fn_node.end_lineno or fn_node.lineno
                    if fn_start <= node.lineno <= fn_end:
                        is_definition = True
                        break
                if not is_definition:
                    results.append((node.lineno, call_name))
    return results


def test_no_production_module_calls_authorize_bypass():
    """No production module may call authorize_bypass() or authorize_local_bypass().

    Production = src/orchestrator/ or src/raphael/.
    Tests = tests/ (allowed to opt-in).
    """
    violations = []
    for root in [SRC_ROOT / "orchestrator", SRC_ROOT / "raphael"]:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            calls = _find_bypass_calls(py_file)
            for line_no, fn_name in calls:
                violations.append((
                    str(py_file.relative_to(REPO_ROOT)),
                    f"line {line_no}: {fn_name}",
                ))
    assert not violations, (
        f"Production modules must not call bypass opt-in functions. "
        f"The seam must remain OFF (v4.1 AM-4.2). Violations: {violations}"
    )


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
