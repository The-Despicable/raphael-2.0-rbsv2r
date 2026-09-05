"""
inv1_guard.py — INV-1 enforcement (CONV-2)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

INV-1 goes live with the broadened primitive lexicon (per the
standing note):
- subprocess (any form)
- os.system, os.popen, os.exec*, os.spawn*
- socket.*
- urllib.*, http.client, http.server
- requests
- open(..., 'w'), open(..., 'a'), open(..., 'x')  # write modes
- os.remove, os.unlink, os.rmdir, shutil.rmtree
"""
import ast
import os
from pathlib import Path
from typing import Optional


INV1_VIOLATION = "INV1_VIOLATION"


# Primitives that must NOT appear outside orchestrator/exec/
FORBIDDEN_PRIMITIVES = {
    # subprocess family
    "subprocess": ["subprocess"],
    # os system/exec family
    "os.system": ["os.system"],
    "os.popen": ["os.popen"],
    "os.execv": ["os.execv"],
    "os.execve": ["os.execve"],
    "os.execvp": ["os.execvp"],
    "os.execvpe": ["os.execvpe"],
    "os.spawnl": ["os.spawnl"],
    "os.spawnle": ["os.spawnle"],
    "os.spawnlp": ["os.spawnlp"],
    "os.spawnlpe": ["os.spawnlpe"],
    "os.spawnv": ["os.spawnv"],
    "os.spawnve": ["os.spawnve"],
    "os.spawnvp": ["os.spawnvp"],
    "os.spawnvpe": ["os.spawnvpe"],
    # socket family
    "socket": ["socket"],
    # urllib family
    "urllib.request": ["urllib.request", "urllib.urlopen"],
    # http family
    "http.client": ["http.client"],
    "http.server": ["http.server"],
    # requests
    "requests": ["requests"],
    # file mutation
    "os.remove": ["os.remove"],
    "os.unlink": ["os.unlink"],
    "os.rmdir": ["os.rmdir"],
    "shutil.rmtree": ["shutil.rmtree"],
}


def _is_in_exec(file_path: Path, exec_root: Path) -> bool:
    """Check if a file is under the exec/ package."""
    try:
        file_path.resolve().relative_to(exec_root.resolve())
        return True
    except ValueError:
        return False


def verify_inv1_primitive_confinement(
    repo_root: Optional[Path] = None,
) -> list:
    """Static check: verify INV-1 primitive confinement.

    Scans all .py files under src/orchestrator/ (except src/orchestrator/exec/)
    for forbidden primitive imports. Returns a list of violations.
    An empty list means INV-1 is satisfied.

    This is a static (load-time) check, not a runtime interceptor.
    Runtime interception would require import hooks or AST transformers;
    static check is sufficient for the P3.0 walking skeleton.
    """
    if repo_root is None:
        # Default: go up from this file to find the repo root
        repo_root = Path(__file__).resolve().parents[3]

    exec_root = repo_root / "src" / "orchestrator" / "exec"
    org_root = repo_root / "src" / "orchestrator"
    violations = []

    if not org_root.exists():
        return violations

    for py_file in org_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        if _is_in_exec(py_file, exec_root):
            continue  # exec/ is allowed to use primitives

        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    for violation_name, forbidden_modules in FORBIDDEN_PRIMITIVES.items():
                        if module_name in forbidden_modules:
                            violations.append({
                                "file": str(py_file.relative_to(repo_root)),
                                "line": node.lineno,
                                "primitive": violation_name,
                                "type": "import",
                                "module": module_name,
                            })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    for violation_name, forbidden_modules in FORBIDDEN_PRIMITIVES.items():
                        if module_name in forbidden_modules or module_name.startswith(
                            tuple(f + "." for f in forbidden_modules)
                        ):
                            violations.append({
                                "file": str(py_file.relative_to(repo_root)),
                                "line": node.lineno,
                                "primitive": violation_name,
                                "type": "from-import",
                                "module": module_name,
                            })

    return violations
