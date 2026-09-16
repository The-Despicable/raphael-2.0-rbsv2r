"""
inv1_guard.py — INV-1 enforcement (CONV-2)

Per v4 L6: "exec/ is the Policy Enforcement Point (PEP). It is the
only package permitted to hold process/network/file primitives."

Declared G3 canonical perimeter
-------------------------------
The §14.x security perimeter declared by the G0/G1/G2/G3 evidence and
the F2 record (evidence/g3_remediation/F2_PERIMETER_RECORD.md) is the
canonical ``run_episode`` execution plane:

  src/orchestrator/runtime/**
  the canonical brain control-plane modules it loads
  src/orchestrator/exec/**   (the sole authorized primitive namespace)

The perimeter is computed deterministically from the static import
closure rooted at ``orchestrator.runtime`` (the existing closure model)
and restricted to the three declared trees above. It is NOT the whole
monorepo: legacy/offensive packages (api/, bridge/, chains/, c2/,
exploit/, scanners/, ...) are a separate, noncanonical plane and are
not silently folded into the claim.

Invocation boundary
-------------------
This is a STATIC (AST) verifier. It is invoked by the gate/test suite
(tests/test_p2_guardrail_inv1.py). It is deliberately NOT wired into
``exec/`` package import: a full-perimeter scan at import time would be
an expensive side effect on every process start and would raise at
import on any violation. The authoritative assertion is at gate/test
time. (The previous docstring's claim of "package load time"
enforcement was false and is corrected here.)

Primitive lexicon
-----------------
Process / network / file-mutation primitives are forbidden outside
``exec/``: subprocess (any form), asyncio subprocess creation,
os.system/popen/exec*/spawn*, socket/network clients, request/HTTP
libraries, file removal, and ``open(...)`` write modes.
"""
import ast
from pathlib import Path
from typing import Optional

INV1_VIOLATION = "INV1_VIOLATION"

# The three package trees that make up the declared G3 canonical perimeter.
CANONICAL_TREES = (
    "orchestrator.runtime",
    "orchestrator.brain",
    "orchestrator.exec",
)

# Root of the canonical Runtime closure (the existing reachability model).
CANONICAL_ROOT = "orchestrator.runtime"

# Forbidden primitive module roots (import X / from X import ...).
FORBIDDEN_IMPORT_ROOTS = {
    "subprocess",
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "paramiko",
    "docker",
}

# Forbidden fully-qualified module names (submodule forms).
FORBIDDEN_IMPORTS = {
    "urllib.request",
    "urllib.urlopen",
    "http.client",
    "http.server",
    "asyncio.subprocess",
}

# Forbidden primitive call sites (dotted name as written in source).
FORBIDDEN_CALLS = {
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
    "asyncio.subprocess.create_subprocess_exec",
    "asyncio.subprocess.create_subprocess_shell",
    "os.system",
    "os.popen",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "shutil.rmtree",
}


def _is_in_exec(file_path: Path, exec_root: Path) -> bool:
    """Check if a file is under the exec/ package."""
    try:
        file_path.resolve().relative_to(exec_root.resolve())
        return True
    except ValueError:
        return False


def _module_matches(name: str, forbidden_roots: set, forbidden_full: set) -> bool:
    """True when an imported module name is a forbidden primitive.

    ``import asyncio`` alone is NOT a violation; only ``asyncio.subprocess``
    (and the subprocess creation calls) are. Matching is therefore exact
    or submodule-of-forbidden, never a bare prefix of a forbidden name.
    """
    if not name:
        return False
    if name in forbidden_full:
        return True
    root = name.split(".")[0]
    if root in forbidden_roots:
        return True
    # from urllib import request  ->  urllib.request
    return any(name.startswith(full + ".") for full in forbidden_full)


def _dotted_name(node: ast.AST) -> str:
    """Best-effort dotted name for a Name/Attribute chain."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _open_write_mode(node: ast.Call) -> Optional[str]:
    """Return the mode string of an ``open(...)`` call when it is a write mode."""
    mode = None
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        mode = node.args[1].value
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        return mode
    return None


def scan_source(source: str, filename: str) -> list:
    """Static scan of one source string for forbidden primitives.

    Returns a list of violation dicts (deterministic order). Empty list
    means the source is clean.
    """
    violations = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_matches(alias.name, FORBIDDEN_IMPORT_ROOTS, FORBIDDEN_IMPORTS):
                    violations.append({
                        "file": filename,
                        "line": node.lineno,
                        "primitive": alias.name,
                        "type": "import",
                        "module": alias.name,
                    })
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                full = f"{base}.{alias.name}" if base else alias.name
                if (
                    _module_matches(base, FORBIDDEN_IMPORT_ROOTS, FORBIDDEN_IMPORTS)
                    or _module_matches(full, FORBIDDEN_IMPORT_ROOTS, FORBIDDEN_IMPORTS)
                    or full in FORBIDDEN_CALLS
                ):
                    violations.append({
                        "file": filename,
                        "line": node.lineno,
                        "primitive": full,
                        "type": "from-import",
                        "module": base,
                    })
        elif isinstance(node, ast.Call):
            dotted = _dotted_name(node.func)
            if dotted in FORBIDDEN_CALLS:
                violations.append({
                    "file": filename,
                    "line": node.lineno,
                    "primitive": dotted,
                    "type": "call",
                    "module": dotted.split(".")[0],
                })
            elif dotted in ("open", "io.open"):
                mode = _open_write_mode(node)
                if mode is not None:
                    violations.append({
                        "file": filename,
                        "line": node.lineno,
                        "primitive": f"open(mode={mode!r})",
                        "type": "file-write",
                        "module": "open",
                    })
    return violations


# ── Declared canonical perimeter ─────────────────────────────────────

def _module_to_file(src_root: Path, module: str) -> Optional[Path]:
    parts = module.split(".")
    for candidate in (
        src_root.joinpath(*parts).with_suffix(".py"),
        src_root.joinpath(*parts, "__init__.py"),
    ):
        if candidate.exists():
            return candidate
    return None


def _orchestrator_imports(path: Path, package: str) -> set:
    """Collect orchestrator.* modules imported at module-import time.

    Only imports that execute when the module is imported are followed:
    imports inside function bodies are lazy (they run only when called)
    and are therefore NOT part of the loaded closure. Class bodies and
    module-level ``try``/``if`` blocks execute at import time and ARE
    followed. Package ``__init__`` semantics are modelled separately by
    the caller (parent-package edges).
    """
    found = set()
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError):
        return found

    def add(name: str) -> None:
        if name and name.startswith("orchestrator."):
            found.add(name)

    def walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # lazy scope: not executed at import time
            if isinstance(child, ast.Import):
                for alias in child.names:
                    add(alias.name)
            elif isinstance(child, ast.ImportFrom):
                base = child.module or ""
                if child.level:
                    pkg = package
                    for _ in range(child.level):
                        pkg = pkg.rsplit(".", 1)[0] if "." in pkg else pkg
                    base = f"{pkg}.{base}" if base else pkg
                add(base)
                for alias in child.names:
                    add(f"{base}.{alias.name}" if base else alias.name)
            walk(child)

    walk(tree)
    return found


def canonical_perimeter_modules(repo_root: Optional[Path] = None) -> tuple:
    """Return the deterministic module list of the declared G3 perimeter.

    Static AST import closure rooted at ``orchestrator.runtime`` (the
    existing reachability model), following orchestrator imports including
    parent package ``__init__`` edges, restricted to the declared trees
    (runtime / brain / exec). It is computed purely from source, so it is
    independent of process import order, has no side effects, and uses no
    developer-machine absolute paths. Only real module files are returned.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    src_root = repo_root / "src"

    visited = set()
    stack = [CANONICAL_ROOT]
    while stack:
        module = stack.pop()
        if module in visited:
            continue
        visited.add(module)
        path = _module_to_file(src_root, module)
        if path is not None:
            for referenced in _orchestrator_imports(path, module):
                if referenced not in visited:
                    stack.append(referenced)
        # Model package __init__ execution: importing a.b.c runs a.b.
        if "." in module:
            parent = module.rsplit(".", 1)[0]
            if parent not in visited:
                stack.append(parent)

    perimeter = [
        module for module in visited
        if any(module == tree or module.startswith(tree + ".")
               for tree in CANONICAL_TREES)
        and _module_to_file(src_root, module) is not None
    ]
    return tuple(sorted(perimeter))


def verify_inv1_primitive_confinement(
    repo_root: Optional[Path] = None,
    modules: Optional[tuple] = None,
) -> list:
    """Static check: primitive confinement over the declared perimeter.

    Scans every module of the declared G3 canonical perimeter and returns
    a list of violations. ``exec/`` is the authorized primitive namespace
    and is never reported. An empty list means INV-1 holds for the
    declared perimeter.

    Pass ``modules`` to scan an explicit module list (used by tests).
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    src_root = repo_root / "src"
    exec_root = src_root / "orchestrator" / "exec"

    if modules is None:
        modules = canonical_perimeter_modules(repo_root)

    violations = []
    for module in modules:
        path = _module_to_file(src_root, module)
        if path is None or "__pycache__" in str(path):
            continue
        if _is_in_exec(path, exec_root):
            continue  # exec/ is the authorized primitive namespace
        try:
            source = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        violations.extend(scan_source(source, rel))

    violations.sort(key=lambda v: (v["file"], v["line"], v["primitive"]))
    return violations
