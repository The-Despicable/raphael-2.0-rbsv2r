#!/usr/bin/env python3
"""Work tool: dry-run extended lexicon rules + INV-1 perimeter pre-check (no src changes)."""
import ast
import sys
from pathlib import Path

REPO = Path("/home/yaser/external-audits/raphael-2")
sys.path.insert(0, str(REPO / "src"))
from orchestrator.exec.inv1_guard import (  # noqa: E402
    scan_source, canonical_perimeter_modules, verify_inv1_primitive_confinement,
    FORBIDDEN_IMPORT_ROOTS, FORBIDDEN_IMPORTS, FORBIDDEN_CALLS)

NEW_CALLS = {"os.rename", "os.chmod", "shutil.copy", "shutil.copy2",
             "shutil.copytree", "shutil.move", "smtplib.SMTP", "smtplib.SMTP_SSL"}
NEW_METHODS = {"write_text", "write_bytes", "unlink", "rename", "rmdir"}
NEW_ROOTS = {"smtplib"}


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def extended_scan(source, filename):
    base = scan_source(source, filename)
    extra = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return base
    top_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top_imports.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_imports.add(node.module.split(".")[0])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in NEW_ROOTS:
                    extra.append({"file": filename, "line": node.lineno,
                                  "primitive": a.name, "type": "import", "module": a.name})
        elif isinstance(node, ast.ImportFrom):
            base_mod = node.module or ""
            for a in node.names:
                full = f"{base_mod}.{a.name}" if base_mod else a.name
                if base_mod.split(".")[0] in NEW_ROOTS or full in NEW_CALLS:
                    extra.append({"file": filename, "line": node.lineno,
                                  "primitive": full, "type": "from-import", "module": base_mod})
        elif isinstance(node, ast.Call):
            d = dotted(node.func)
            if d in NEW_CALLS:
                extra.append({"file": filename, "line": node.lineno,
                              "primitive": d, "type": "call", "module": d.split(".")[0]})
            elif "." in d:
                attr = d.rsplit(".", 1)[1]
                if attr in NEW_METHODS and ({"pathlib", "os"} & top_imports):
                    extra.append({"file": filename, "line": node.lineno,
                                  "primitive": d, "type": "call", "module": d.split(".")[0]})
    return base + extra


new_files = {}
for py in sorted((REPO / "src").rglob("*.py")):
    if "__pycache__" in str(py):
        continue
    rel = str(py.relative_to(REPO)).replace("\\", "/")
    text = py.read_text(errors="ignore")
    old = scan_source(text, rel)
    new = extended_scan(text, rel)
    if len(new) > len(old):
        new_files[rel] = [(v["type"], v["primitive"], v["line"]) for v in new if v not in old]

print(f"NEW_FILES={len(new_files)}")
for rel in sorted(new_files):
    print(f"--- {rel}")
    for t, p, ln in sorted(new_files[rel])[:10]:
        print(f"    L{ln} {t} {p}")

print("=== INV-1 perimeter pre-check with extended rules ===")
perim = canonical_perimeter_modules(REPO)
print(f"perimeter_modules={len(perim)}")
src_root = REPO / "src"
exec_root = src_root / "orchestrator" / "exec"


def mod_to_file(mod):
    parts = mod.split(".")
    for cand in (src_root.joinpath(*parts).with_suffix(".py"),
                 src_root.joinpath(*parts, "__init__.py")):
        if cand.exists():
            return cand
    return None


viols = []
for mod in perim:
    p = mod_to_file(mod)
    if p is None or "__pycache__" in str(p):
        continue
    try:
        relp = p.relative_to(exec_root)
        in_exec = True
    except ValueError:
        in_exec = False
    if in_exec:
        continue
    rel = str(p.relative_to(REPO)).replace("\\", "/")
    for v in extended_scan(p.read_text(errors="ignore"), rel):
        viols.append(v)
print(f"PERIMETER_VIOLATIONS_EXTENDED={len(viols)}")
for v in sorted(viols, key=lambda x: (x["file"], x["line"]))[:20]:
    print("   ", v["file"], v["line"], v["primitive"], v["type"])
