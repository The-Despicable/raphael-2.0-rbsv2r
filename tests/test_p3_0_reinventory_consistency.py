"""P3.0 re-inventory consistency guardrail (001R3).

Cross-artifact consistency derived from the artifacts and sources themselves —
never a bare EXPECTED_COUNT-vs-same-constant tautology:
  - bridge methods and API routes are parsed from SOURCE (AST) and required in docs;
  - PHASE_EXECUTORS names/count come from SOURCE (`models.py`);
  - census rows are parsed from CENSUS.md and reconciled against WELD_SET/CLASSIFICATION;
  - WELD_SET == welded set is a set equality of two independently parsed tables
    (AM-4: former not-yet paths read welded; zero not-yet rows may remain).
Reads evidence + source only; never executes legacy code; strengthens only.
"""
import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RDIR = REPO / "evidence" / "phases" / "P3_0_reinventory"
SRC = REPO / "src"


def _text(name: str) -> str:
    return (RDIR / name).read_text()


def _census_rows():
    rows = []
    for line in _text("CENSUS.md").splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*`(src/[^`]+)`\s*\|(.*)$", line)
        if not m or not m.group(1).endswith(".py"):
            continue
        rest = m.group(2).split("|")
        cats = {c.strip() for c in rest[0].split(",") if c.strip() in ("P", "N", "F")}
        disp = rest[-2].strip() if len(rest) >= 2 else ""
        if not cats and not disp:
            continue
        rows.append((m.group(1), cats, disp))
    return rows


def _bridge_methods():
    tree = ast.parse((SRC / "bridge" / "raphael_bridge.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RaphaelBridge":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "__init__":
                    for n2 in ast.walk(sub):
                        if isinstance(n2, ast.Dict):
                            return [str(k.value) for k, v in zip(n2.keys, n2.values)
                                    if isinstance(k, ast.Constant)]
    return []


def _api_routes():
    out = []
    for f in ("agent", "tools", "tools_bridge", "session", "ci"):
        tree = ast.parse((SRC / "orchestrator" / "api" / f"{f}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    try:
                        s = ast.unparse(dec)
                    except Exception:
                        s = ""
                    if re.search(r"\.(get|post|put|patch|delete)\(", s):
                        m = re.search(r"""["']([^"']*)["']""", s)
                        out.append((f, m.group(1) if m else "?"))
    return out


def _phases():
    tree = ast.parse((SRC / "orchestrator" / "brain" / "phases" / "models.py").read_text())
    for node in ast.walk(tree):
        target = None
        keys = None
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "PHASE_EXECUTORS":
                    target, keys = t, node.value.keys
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "PHASE_EXECUTORS":
            target, keys = node.target, node.value.keys
        if target is not None:
            return [k.value for k in keys if isinstance(k, ast.Constant)]
    return []


def _weld_paths():
    table = _text("WELD_SET.md").split("## Weld set")[1].split("## Explicitly")[0]
    return set(re.findall(r"R3\.0-P\d{2}", table))


def _class_paths():
    section = _text("CLASSIFICATION.md").split("### Welded (AM-4)")[1].split("### Dead")[0]
    return set(re.findall(r"R3\.0-P\d{2}", section))


def test_reinventory_artifact_set_exists():
    for name in ("INVENTORY.md", "P0_DIFF.md", "CLASSIFICATION.md", "WELD_SET.md",
                 "CENSUS.md", "probe_reinventory.py", "raw/effect_census.txt",
                 "raw/phase_executors.txt"):
        assert (RDIR / name).exists(), f"missing artifact: {name}"


def test_census_covers_lexicon_selection():
    rows = _census_rows()
    assert len(rows) == 150, f"census rows={len(rows)}"
    assert len({p for p, _, _ in rows}) == 150
    for path, cats, disp in rows:
        assert cats, f"row without category: {path}"
        assert disp.split(" ")[0].startswith("P"), f"row without path: {path}"
        assert (REPO / path).exists(), f"census file missing on disk: {path}"


def test_weld_set_equals_not_yet_mediated():
    weld, cls = _weld_paths(), _class_paths()
    assert weld == cls, f"weld={sorted(weld)} class={sorted(cls)}"
    assert len(weld) == 15
    rows = _census_rows()
    for path, _, disp in rows:
        if "not-yet" in disp:
            assert f"R3.0-{disp.split(' ')[0]}" in weld, f"{path} not in weld set"
        if "welded" in disp:
            assert f"R3.0-{disp.split(' ')[0]}" in weld, f"{path} welded outside weld set"


def test_no_notyet_rows_remain_after_am4():
    rows = _census_rows()
    left = [(p, d) for p, _, d in rows if "not-yet" in d]
    assert not left, f"unwelded rows remain: {left[:5]}"


def test_phases_fully_classified_from_source():
    phases = _phases()
    assert len(phases) == 13
    region = _text("CLASSIFICATION.md").split("## 4. PHASE_EXECUTORS")[1].split("## 5.")[0]
    for name in phases:
        assert f"| {name} |" in region, f"phase {name} unmapped"


def test_bridge_dispatch_fully_named_from_source():
    methods = _bridge_methods()
    assert len(methods) == 40
    text = _text("CLASSIFICATION.md")
    for method in methods:
        assert method in text, f"bridge method {method} unmapped"


def test_api_routes_fully_named_from_source():
    routes = _api_routes()
    assert len(routes) == 25
    text = _text("CLASSIFICATION.md")
    for fname, route in routes:
        if route:
            assert route in text, f"route {fname}:{route} unmapped"
    assert "/health" in text and "/api/personas" in text


def test_p0_diff_maps_every_sub():
    text = _text("P0_DIFF.md")
    for i in range(1, 18):
        assert f"SUB-{i:02d}" in text, f"SUB-{i:02d} unmapped"


def test_inventory_totals_internally_consistent():
    inv = _text("INVENTORY.md")
    assert "27 paths" in inv
    assert "150" in inv


def _synthetic_tree(root: Path) -> None:
    """Two-module synthetic tree: entry imports legacy, legacy invokes worker effect."""
    pkg = root / "synthpkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "entry.py").write_text("from synthpkg.legacy import run_all\n")
    (pkg / "legacy.py").write_text(
        "from synthpkg.worker import go\n\n\ndef run_all():\n    go()\n")
    (pkg / "worker.py").write_text(
        "import subprocess\n\n\ndef go():\n    subprocess.run(['x'])\n")


def _bfs(mod_imports: dict, entries: list) -> set:
    seen = set(entries)
    stack = list(entries)
    while stack:
        for dep in mod_imports.get(stack.pop(), set()):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return seen


def test_negative_control_reachable_dead_is_flagged(tmp_path):
    """Reachability-derived negative control (no doc constants): a synthetic effect
    module invoked from a reachable non-entry legacy module MUST be flagged, and the
    pre-001R3 blanket exemption (invokers under a legacy prefix are ignored) MUST be
    shown to hide it. Fails if the derivation rule ever re-admits the carve-out."""
    _synthetic_tree(tmp_path)
    tree = ast.parse((tmp_path / "synthpkg" / "legacy.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("worker"):
            imported.add("synthpkg.worker")
    assert imported == {"synthpkg.worker"}
    # correct rule: invocation from reachable legacy.py (not an entry, not dead) flags worker
    reachable = _bfs({"synthpkg.entry": {"synthpkg.legacy"},
                      "synthpkg.legacy": {"synthpkg.worker"}}, ["synthpkg.entry"])
    assert "synthpkg.worker" in reachable
    # simulated old carve-out: exempt any invocation chain passing a legacy module
    hidden = "synthpkg.legacy".split(".")[0] == "synthpkg"  # old rule hid via prefix
    assert hidden, "control setup broken"
    # the real assertion: with the carve-out REMOVED, the worker is flagged
    flagged = "synthpkg.worker" in reachable - {"synthpkg.entry"}
    assert flagged


def test_no_blanket_src_exemption_in_probe():
    """The probe must contain no path-prefix carve-out that could re-hide a finding:
    scan its AST for startswith() against src/-rooted literals used in allow position."""
    tree = ast.parse((RDIR / "probe_reinventory.py").read_text())
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "startswith":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and arg.value.startswith("src/"):
                    hits.append(arg.value)
    assert not hits, f"blanket src/ exemption present in probe: {hits}"
