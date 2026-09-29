"""P3.0 re-inventory probe, 001R2 complete (read-only).

Derives everything from source + the authoritative effect lexicon:
  A. effect census via the REAL `inv1_guard.scan_source` over src/** vs CENSUS.md
     (140 files), with per-file P/N/F categories cross-checked;
  B. AST import graph (function-level imports + parent-package __init__ edges) ->
     reachability from live + service entries -> dead set DERIVED, never hardcoded;
  C. bridge dispatch keys (AST, all 40 incl. c2.* digits) + per-method fail-closed proofs;
  D. API routes (AST decorators, all 27) vs CLASSIFICATION route table;
  E. canonical episode + INV-1 + zero-reference (control);
  F. SHELL live construction negatives (gate raises before any socket/PTY use);
  G. U-1/U-2/U-3 + welded-stub + tightened auth checks;
  H. PHASE_EXECUTORS == 13 with every phase classified; WELD_SET == not-yet set;
     standalone entries classified.

Never executes legacy/offensive paths, never touches the network, never runs a
primitive. The only imports beyond stdlib are the canonical Runtime/guard (same as the
gate suite), the effect lexicon itself, the phase registry (data-only), and the shell
dataclasses under test in F (construction raises first).
Exit 0 iff every check passes (non-zero on any missing coverage).
"""
from __future__ import annotations

import ast
import re
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
RDIR = REPO / "evidence" / "phases" / "P3_0_reinventory"

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def read(rel: str) -> str:
    return (REPO / rel).read_text(errors="ignore")


def tree_of(rel: str) -> ast.AST:
    return ast.parse(read(rel))


def defined_names(rel: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def module_imports(rel: str) -> set[str]:
    """All imported module names (absolute + resolved relative), any depth."""
    found: set[str] = set()
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return found
    parts = Path(rel).with_suffix("").parts[1:]
    is_init = bool(parts) and parts[-1] == "__init__"
    pkg = ".".join(parts[:-1])
    base_mod = ".".join(parts)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # containing package P = parts[:-1]; `from .` (L1) stays in P.
                up = node.level - 1
                p = pkg
                for _ in range(up):
                    p = p.rsplit(".", 1)[0] if "." in p else ""
                base = f"{p}.{node.module}" if node.module else p
            else:
                base = node.module or ""
            if base:
                found.add(base)
            for a in node.names:
                if a.name != "*":
                    found.add(f"{base}.{a.name}" if base else a.name)
    return found


def call_sites(rel: str) -> set[str]:
    """Dotted names of every Call func in the file (comments/strings excluded)."""
    out: set[str] = set()
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f, parts = node.func, []
            while isinstance(f, ast.Attribute):
                parts.append(f.attr)
                f = f.value
            if isinstance(f, ast.Name):
                parts.append(f.id)
                out.add(".".join(reversed(parts)))
    return out


# ---------------------------------------------------------------- census (A)
# Authoritative lexicon: the REAL scan_source (no reimplementation, no regex copy).
sys.path.insert(0, str(SRC))
from orchestrator.exec.inv1_guard import scan_source  # noqa: E402

LEX_P = {"subprocess", "asyncio"}
LEX_N = {"socket", "requests", "httpx", "aiohttp", "paramiko", "docker", "urllib", "http",
         "smtplib", "boto3", "botocore", "redis"}
LEX_FCALLS = {"os.remove", "os.unlink", "os.rmdir", "shutil.rmtree", "os.rename", "os.chmod",
              "shutil.copy", "shutil.copy2", "shutil.copytree", "shutil.move"}
LEX_METHODS = {"write_text", "write_bytes", "unlink", "rename", "rmdir", "chmod"}
# asyncio root covers process creation, but these two are network sockets.
LEX_NET_CALLS = {"asyncio.open_connection", "asyncio.start_server"}


def lex_category(violations: list) -> set:
    cats = set()
    for v in violations:
        typ, prim, mod = v.get("type", ""), v.get("primitive", ""), v.get("module", "")
        if typ == "file-write" or prim.startswith("open("):
            cats.add("F")
            continue
        if prim in LEX_FCALLS:
            cats.add("F")
            continue
        if "." in prim and prim.rsplit(".", 1)[1] in LEX_METHODS:
            cats.add("F")
            continue
        if prim in LEX_NET_CALLS:
            cats.add("N")
            continue
        root = (mod or prim).split(".")[0]
        if root in LEX_N:
            cats.add("N")
            continue
        if root in LEX_P or prim.startswith("os.system") or prim.startswith("os.popen") \
                or ".exec" in prim or ".spawn" in prim:
            cats.add("P")
            continue
    return cats


census_files: set[str] = set()
census_cats: dict[str, set] = {}
for py in sorted(SRC.rglob("*.py")):
    if "__pycache__" in str(py):
        continue
    rel = str(py.relative_to(REPO)).replace("\\", "/")
    try:
        text = py.read_text(errors="ignore")
    except OSError:
        continue
    try:
        viols = scan_source(text, rel)
    except Exception:
        viols = []
    if viols:
        census_files.add(rel)
        census_cats[rel] = lex_category(viols)

doc_files: set[str] = set()
doc_disp: dict[str, str] = {}
doc_cats: dict[str, set] = {}
for line in (RDIR / "CENSUS.md").read_text().splitlines():
    m = re.match(r"\|\s*\d+\s*\|\s*`(src/[^`]+)`\s*\|(.*)$", line)
    if m and m.group(1).endswith(".py"):
        rest = m.group(2).split("|")
        cats = {c.strip() for c in rest[0].split(",") if c.strip() in ("P", "N", "F")}
        disp = rest[-2].strip() if len(rest) >= 2 else ""
        # table header/separator lines yield empty cats+disp: skip them
        if not cats and not disp:
            continue
        doc_files.add(m.group(1))
        doc_disp[m.group(1)] = disp
        doc_cats[m.group(1)] = cats
check("A/census-count", len(census_files) == 150, f"lexicon census={len(census_files)}")
check("A/census-equals-doc", census_files == doc_files,
      f"only_live={sorted(census_files - doc_files)[:3]} only_doc={sorted(doc_files - census_files)[:3]}")
cat_bad = sorted(f for f in census_files & doc_files if census_cats.get(f) != doc_cats.get(f))
check("A/categories-match", not cat_bad,
      f"mismatched={[(f, sorted(census_cats.get(f, set())), sorted(doc_cats.get(f, set()))) for f in cat_bad[:5]]}")

# ---------------------------------------------------------------- graph (B)
mods: dict[str, str] = {}
for py in sorted(SRC.rglob("*.py")):
    if "__pycache__" in str(py):
        continue
    rel = str(py.relative_to(SRC).with_suffix("")).replace("\\", "/")
    parts = rel.split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    mods[".".join(parts)] = str(py.relative_to(REPO)).replace("\\", "/")
check("B/mods-sane", len(mods) > 400 and "orchestrator.exec" in mods
      and "orchestrator.capabilities.interactive_shell" in mods,
      f"modules={len(mods)}; package inits keyed without suffix")


def to_mod(name: str):
    if name in mods:
        return name
    parts = name.split(".")
    for i in range(len(parts) - 1, 0, -1):
        cand = ".".join(parts[:i])
        if cand in mods:
            return cand
    return None


adj: dict[str, set[str]] = {m: set() for m in mods}
for mod, rel in mods.items():
    for imp in module_imports(rel):
        t = to_mod(imp)
        if t and t != mod:
            adj[mod].add(t)
            # importing a.b.c executes the parent packages' __init__ first:
            # the importer therefore depends on every parent of t as well.
            parts = t.split(".")
            for i in range(len(parts) - 1, 0, -1):
                parent = ".".join(parts[:i])
                if parent in mods and parent != mod:
                    adj[mod].add(parent)
    parts = mod.split(".")
    for i in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:i])
        if parent in mods and parent != mod:
            adj[mod].add(parent)
# mcp-hub entry brokenness (CENSUS M-1): the package cannot load as committed.
# No synthetic registry edge is added — the graph must yield these 9 as dead.
try:
    import mcp_hub.core.server  # noqa: F401
    check("B/mcphub-broken", False, "mcp_hub unexpectedly importable")
except ModuleNotFoundError as e:
    check("B/mcphub-broken", "mcp_hub" in str(e), f"ModuleNotFoundError: {e}")
check("B/mcphub-noalias", not (SRC / "mcp_hub").exists(), "no mcp_hub alias dir")
_nomain = True
for py in (SRC / "mcp-hub" / "tools").rglob("*.py"):
    if "__pycache__" in str(py):
        continue
    try:
        t = ast.parse(py.read_text(errors="ignore"))
    except SyntaxError:
        continue
    if any(isinstance(n, ast.If) and getattr(n.test, "left", None) is not None
           and getattr(getattr(n.test, "left", None), "id", "") == "__name__" for n in ast.walk(t)):
        _nomain = False
check("B/mcphub-tools-no-main", _nomain, "tool files have no __main__ entry")

LIVE = ["bridge.raphael_bridge", "orchestrator.api.main", "orchestrator.api.agent",
        "orchestrator.api.tools", "orchestrator.api.tools_bridge", "orchestrator.api.session",
        "orchestrator.modes.autonomous", "orchestrator.modes.community",
        "orchestrator.modes.debate", "orchestrator.modes.deep_research",
        "orchestrator.modes.scan", "orchestrator.modes.student",
        "orchestrator.agents.engage", "orchestrator.agents.recon", "orchestrator.agents.scan",
        "orchestrator.agents.exploit", "orchestrator.agents.postex",
        "orchestrator.chains.ad_kill_chain", "orchestrator.chains.credential_spray",
        "orchestrator.chains.tool_registry", "orchestrator.c2.manager",
        "orchestrator.kali_tools_client", "raphael.main", "orchestrator.runtime.loop",
        "orchestrator.engagement_queue"]
SVC = ["kali-tools.server", "mhddos-service.main", "recon-pipeline.main", "sword.api",
       "agent.agent", "phishing.main",
       "cai-service.main", "raphael.exploit_factory.__main__", "orchestrator.modes.scan",
       "cloak-service.main", "raphael.verifier.__main__",
       "raphael.techniques.fast_port_scan"]
# NOTE: mcp-hub.main / mcp-hub.core.server are DELIBERATELY absent: B/mcphub-broken
# proves every run that the package cannot load (ModuleNotFoundError), so no import
# edge out of it can execute; listing them as entries would over-approximate dead
# code as reachable. If the package is repaired, B/mcphub-broken FAILS and forces
# reclassification (CENSUS M-1 resurrection clause).
ENTRIES = [e for e in LIVE + SVC if e in mods]
check("B/entries-resolve", len(ENTRIES) == len(LIVE) + len(SVC),
      f"{len(ENTRIES)}/{len(LIVE) + len(SVC)}")

seen = set(ENTRIES)
stack = list(ENTRIES)
while stack:
    cur = stack.pop()
    for d in adj[cur]:
        if d not in seen:
            seen.add(d)
            stack.append(d)

DEAD_TAGS = ("P14", "P24", "P25")
LIVE_TAGS = ("P01", "P02", "P04", "P05", "P06", "P07", "P08", "P09", "P10", "P11",
             "P12", "P13", "P16", "P18", "P19", "P20", "P23")
def path_mod(f: str) -> str:
    parts = list(Path(f).with_suffix("").parts[1:])
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def disp_class(disp: str) -> str:
    if any(disp == t or disp.startswith(t + " ") or disp.startswith(t + ",") for t in DEAD_TAGS):
        return "dead"
    if "no path" in disp or "perimeter doc" in disp:
        return "literal-doc"
    return "live"


OK = True
doc_dead_all = sorted(f for f in census_files if disp_class(doc_disp.get(f, "")) == "dead")
doc_dead_set = set(doc_dead_all)


def _top_defs(rel: str) -> set:
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _imports_module(rel: str, target_mod: str) -> bool:
    """True iff rel has an import that can actually bind a name from target_mod.

    Resolution must be EXACT (no prefix fallback): `from P.Q import X` where P.Q
    does not exist as a module always raises at runtime (e.g. llm_exploit_engine's
    guarded `from orchestrator.checkpoint.checkpoint_manager import ...` targets a
    nonexistent package), so it can never invoke the target's effects.
    """
    for imp in module_imports(rel):
        if imp == target_mod or imp.startswith(target_mod + "."):
            if imp in mods:
                return True
    return False


def _effect_confined(f: str) -> bool:
    """Dead-effect rule (derived, no hardcoded names, no path exemptions): every
    in-tree invocation of F's top-level definitions must stay inside other dead-doc
    files, tests, or unreachable files. Invocation from ANY reachable non-dead module
    FAILS (the file must be classified not-yet-mediated instead)."""
    fmod = path_mod(f)
    for d in sorted(_top_defs(f)):
        for r in mods.values():
            if r == f or "__pycache__" in r or not r.endswith(".py"):
                continue
            if "/tests/" in r or r.startswith("tests/"):
                continue
            if not _imports_module(r, fmod):
                continue
            try:
                txt = read(r)
            except OSError:
                continue
            if re.search(r"\b%s\s*\(" % re.escape(d), txt):
                rmod = path_mod(r)
                allowed = (r in doc_dead_set or rmod not in seen)
                if not allowed:
                    print(f"   LIVE-INVOCATION (must be not-yet): {d}() in {r} (effect of {f})")
                    return False
    return True


effect_ok = set()
_fx_ok = True
for f in doc_dead_all:
    if path_mod(f) not in seen:
        continue
    if _effect_confined(f):
        effect_ok.add(f)
        print(f"   DEAD-EFFECT-OK: {f} (module reachable, effects uninvoked outside dead/test/unreachable)")
    else:
        _fx_ok = False
check("B/dead-effect-confined", _fx_ok,
      "doc-dead-but-reachable effects invoked only from dead/test/unreachable code")
for f in sorted(census_files):
    mod = path_mod(f)
    disp = doc_disp.get(f, "")
    cls = disp_class(disp)
    if not disp:
        OK = False
        print(f"   MISMATCH (no CENSUS row): {f}")
        continue
    reachable = mod in seen
    if cls == "dead" and reachable and f not in effect_ok:
        OK = False
        print(f"   MISMATCH (doc-dead but reachable): {f} disp={disp}")
    if cls == "live" and not reachable:
        OK = False
        print(f"   MISMATCH (doc-live but unreachable): {f} disp={disp}")
check("B/dead-derived-not-hardcoded", OK, "every census disposition matches graph BFS")
dead_derived = sorted(f for f in census_files
                      if path_mod(f) not in seen
                      and disp_class(doc_disp.get(f, "")) == "dead")
doc_dead = sorted(f for f in census_files if disp_class(doc_disp.get(f, "")) == "dead"
                  and f not in effect_ok)
check("B/dead-set-equals", dead_derived == doc_dead,
      f"derived_dead={len(dead_derived)} doc_dead={len(doc_dead)}")

# ---------------------------------------------------------------- bridge (C)
btree = tree_of("src/bridge/raphael_bridge.py")
keys: list[str] = []
vals: dict[str, str] = {}
for node in ast.walk(btree):
    if isinstance(node, ast.ClassDef) and node.name == "RaphaelBridge":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name == "__init__":
                for n2 in ast.walk(sub):
                    if isinstance(n2, ast.Dict):
                        for k, v in zip(n2.keys, n2.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Attribute):
                                keys.append(str(k.value))
                                vals[str(k.value)] = str(v.attr)
check("C/method-count", len(keys) == 40, f"dispatch_keys={len(keys)}")
cls_text = (RDIR / "CLASSIFICATION.md").read_text()
missing = [k for k in keys if k not in cls_text]
check("C/every-method-classified", not missing, f"missing={missing[:5]}")
# the §12 grep misses c2.* (digit); prove we exceed it:
check("C/c2-covered", all(f'"c2.{s}"' in read("src/bridge/raphael_bridge.py")
      for s in ("build_implant", "deploy", "list_beacons", "task_beacon", "sliver_connect")),
      "5 c2 keys present + classified (grep [a-z_] misses digits)")
# per-method fail-closed proofs (P17):
AGENTS = ["recon", "exploit", "postex", "engage"]
for a in AGENTS:
    defs = defined_names(f"src/orchestrator/agents/{a}.py")
    check(f"C/agent-{a}-no-handle", "handle" not in defs, f"bridge agent.{a} -> AttributeError")
check("C/config-shims-broken",
      "def set_target" not in read("src/orchestrator/config/target.py")
      and "def set_scope" not in read("src/orchestrator/config/paths.py"),
      "target.set/scope.set -> ImportError")
NOPRIM = {
    "src/orchestrator/exploit/payloads_db.py", "src/orchestrator/conductor.py",
    "src/orchestrator/brain/neural_memory.py",
    "src/orchestrator/brain/adaptive_brain.py",
}
NETM = ("socket", "httpx", "requests", "aiohttp", "paramiko", "urllib.request", "http.client",
        "http.server", "subprocess", "os.system", "os.popen", "create_subprocess")
for rel in sorted(NOPRIM):
    imps = module_imports(rel)
    bad = {i for i in imps for n in NETM if i == n or i.startswith(n + ".")}
    check(f"C/noprim-{Path(rel).name}", not bad, f"bad_imports={sorted(bad)[:3]}")

# ---------------------------------------------------------------- routes (D)
def route_paths(rel: str) -> list[str]:
    out: list[str] = []
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                try:
                    s = ast.unparse(dec)
                except Exception:
                    s = ""
                if ".get(" in s or ".post(" in s or ".put(" in s or ".patch(" in s or ".delete(" in s:
                    m = re.search(r"""["']([^"']*)["']""", s)
                    out.append(f"{rel.split('/')[-1]}:{m.group(1) if m is not None else '?'}")
    return out

ROUTE_COUNTS = {"agent": 4, "tools": 5, "tools_bridge": 2, "session": 8, "ci": 6}

routes: list[str] = []
for f in ("agent", "tools", "tools_bridge", "session", "ci"):
    got = route_paths(f"src/orchestrator/api/{f}.py")
    check(f"D/routes-{f}", len(got) == ROUTE_COUNTS[f], f"{got}")
    routes += got
routes += ["main.py:/health", "main.py:/api/personas"]
check("D/route-count", len(routes) == 27, f"routes={len(routes)}")
rmissing = [r for r in routes
            if r.split(":", 1)[1] not in ("", "(root)") and r.split(":", 1)[1] not in cls_text]
check("D/every-route-classified", not rmissing, f"missing={rmissing[:5]}")
# tightened mount/auth checks (verdict §76.4):
main_src = read("src/orchestrator/api/main.py")
check("T1/mount-tools",
      all(f"app.include_router({r})" in main_src
          for r in ("agent_router", "tools_router", "tools_bridge_router", "session_router"))
      and "ci_router" not in main_src,
      "exactly 4 routers mounted; ci unmounted")
for rel, label in (("src/orchestrator/api/tools_bridge.py", "T1b"),
                   ("src/kali-tools/server.py", "T2")):
    src = read(rel)
    check(f"{label}/no-auth",
          "require_scope" not in src and "Depends(" not in src and "Security(" not in src
          and "OAuth2" not in src and "APIKey" not in src and "HTTPBearer" not in src,
          f"{label} declares no auth mechanism")
    check(f"{label}/routes-nodeps", "dependencies=" not in src, "no router-level dependencies")

# ---------------------------------------------------------------- legacy traces (kept, tightened)
check("T1/tools-imports-registry",
      "orchestrator.chains.tool_registry" in module_imports("src/orchestrator/api/tools.py"),
      "AST import edge")
check("T1/sub04-site",
      "asyncio.create_subprocess_exec" not in call_sites("src/orchestrator/chains/tool_registry.py")
      and "enforce_broker_mediation" in read("src/orchestrator/chains/tool_registry.py"),
      "SUB-04 call deleted; broker gate present (AM-4-R2 W-01)")
check("T1/no-broker-tools",
      "require_broker_mediation" in read("src/orchestrator/api/tools.py")
      and "enforce_broker_mediation" in read("src/orchestrator/chains/tool_registry.py"),
      "broker gate on tools route + SUB-04 sink (AM-4 W-01)")
tb_routes = route_paths("src/orchestrator/api/tools_bridge.py")
check("T1b/routes", any("/nmap" in r for r in tb_routes) and any("/recon" in r for r in tb_routes),
      f"{tb_routes}")
check("T1b/hop", "KALI_CONTAINER_URL" in read("src/orchestrator/api/tools_bridge.py"),
      "bridge posts to kali-tools /run")
srv = read("src/kali-tools/server.py")
check("T2/route-run", '"/run"' in srv and "def run_tool" in srv, "POST /run")
check("T2/sink",
      "subprocess.run" not in call_sites("src/kali-tools/server.py")
      and "enforce_broker_mediation" in srv,
      "subprocess call deleted from /run; broker gate present (AM-4-R2 W-09)")
check("T2/no-broker", "enforce_broker_mediation" in srv, "broker gate on /run (AM-4 W-09)")
br = read("src/bridge/raphael_bridge.py")
check("T3/bridge-method", '"mode.autonomous"' in br, "method present")
auto = read("src/orchestrator/modes/autonomous.py")
check("T3/auto-imports-chains",
      "orchestrator.chains.credential_spray" in module_imports("src/orchestrator/modes/autonomous.py")
      and "orchestrator.chains.ad_kill_chain" in module_imports("src/orchestrator/modes/autonomous.py"),
      "AST edges")
check("T3/no-broker-chain",
      "enforce_broker_mediation" in auto
      and "enforce_broker_mediation" in br,
      "broker gate on autonomous.handle + bridge dispatch (AM-4 W-04/W-06)")
check("P11/sites",
      "asyncio.create_subprocess_exec" not in call_sites("src/orchestrator/c2/sliver_backend.py")
      and read("src/orchestrator/c2/implant_builder.py").count("create_subprocess_exec") >= 3,
      "sliver exec calls deleted; _build_* leaves retained as dead code for P9 (AM-4-R2 W-08)")
check("P16/sandbox-sink",
      "subprocess.run" not in call_sites("src/orchestrator/sandbox.py")
      and "enforce_broker_mediation" in read("src/orchestrator/sandbox.py")
      and "orchestrator.sandbox" in module_imports("src/orchestrator/agents/exploit.py")
      and "custom_payload" in read("src/orchestrator/agents/exploit.py"),
      "run_code body deleted, gate present; dispatcher edge intact (AM-4-R2 W-10)")

# ---------------------------------------------------------------- control (E)
sys.path.insert(0, str(SRC))
try:
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.scope import ScopeV0
    from orchestrator.exec.inv1_guard import (
        canonical_perimeter_modules, verify_inv1_primitive_confinement)
    scope = ScopeV0(mission_id="probe", targets=("system_info.name",),
                    allowed_action_types=("safe_proving_capability",),
                    allowed_capabilities=("fixture.inspect",), max_impact=0.0)
    rt = RaphaelRuntime()
    mission = MissionContext(mission_id="probe", name="probe", objectives=["probe"],
                             constraints={"default_target": "system_info.name"}, scope=scope)
    traces, _ = rt.run_episode(mission, require_scope=True)
    stages = [e["stage"] for e in traces[0].entries] if traces else []
    check("T4/episode-runs", {"broker", "pep", "receipt"} <= set(stages), f"{stages}")
    perim = canonical_perimeter_modules(REPO)
    viol = verify_inv1_primitive_confinement(REPO, perim)
    check("T4/inv1-perimeter-clean", viol == [], f"modules={len(perim)}")
    legacy = ("orchestrator.modes", "orchestrator.api", "orchestrator.chains",
              "orchestrator.c2", "kali_tools_client")
    check("T4/canonical-zero-reference",
          all(not any(m == n or m.startswith(n + ".") for m in perim) for n in legacy),
          f"perimeter={len(perim)}")
except Exception as e:
    check("T4/episode-runs", False, f"{type(e).__name__}: {e}")
    check("T4/inv1-perimeter-clean", False, "episode failed first")
    check("T4/canonical-zero-reference", False, "episode failed first")

# ---------------------------------------------------------------- SHELL live (F)
try:
    from orchestrator.capabilities.interactive_shell.capability import (
        ShellCapabilityFactory, ShellCapabilityType, ShellConnectionInfo, ShellNotAuthorized)
    from orchestrator.capabilities.interactive_shell.reverse_shell import (
        ReverseShellCapability, ReverseShellConnectionInfo)
    from orchestrator.capabilities.interactive_shell.ssh_shell import SSHShellCapability
    from orchestrator.capabilities.interactive_shell.session import is_shell_session_authorized

    rinfo = ReverseShellConnectionInfo(capability_type=ShellCapabilityType.REVERSE_TCP,
                                       target="127.0.0.1")
    sinfo = ShellConnectionInfo(capability_type=ShellCapabilityType.SSH, target="127.0.0.1")
    forged = types.SimpleNamespace(session_id="probe-forged-0000", authorized=True,
                                   authorized_by="capability_broker")
    check("S0/registry-miss", is_shell_session_authorized("probe-forged-0000") is False,
          "forged id unknown to broker registry")
    for name, fn in (
        ("S1/reverse-none", lambda: ReverseShellCapability(rinfo, authorization=None)),
        ("S2/reverse-forged", lambda: ReverseShellCapability(rinfo, authorization=forged)),
        ("S3/ssh-none", lambda: SSHShellCapability(sinfo, authorization=None)),
        ("S4/factory-none", lambda: ShellCapabilityFactory.create(sinfo, authorization=None)),
    ):
        try:
            fn()
            check(name, False, "constructed WITHOUT authorization (gate bypass!)")
        except Exception as e:
            check(name, type(e).__name__ == "ShellNotAuthorized", f"raised {type(e).__name__}")
except Exception as e:
    for name in ("S0/registry-miss", "S1/reverse-none", "S2/reverse-forged",
                 "S3/ssh-none", "S4/factory-none"):
        check(name, False, f"harness failed: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- U + welds (G)
kali_defs = defined_names("src/orchestrator/kali_tools_client.py")
exec_defs = defined_names("src/raphael/executor/executor.py")
kbr_defs = defined_names("src/raphael/executor/kali_bridge.py")
for sym, d in (("_run_local", kali_defs), ("KaliBypassNotAuthorized", kali_defs),
               ("_BYPASS_AUTHORIZED", kali_defs), ("authorize_local_bypass", kali_defs),
               ("_subprocess_fallback", exec_defs), ("_subprocess_run", kbr_defs),
               ("BypassNotAuthorized", exec_defs)):
    check(f"P15/absent-{sym}", sym not in d, "welded")
check("P15/absent-authorize_bypass",
      "authorize_bypass" not in exec_defs and "authorize_bypass" not in kbr_defs, "welded")
check("U1/ci-unmounted",
      "ci_router" not in read("src/orchestrator/api/main.py")
      and all("ci_router" not in read(r) for r in mods.values()
              if r.endswith(".py") and "__pycache__" not in r),
      "zero mount/import edges repo-wide")
check("U1/queue-write-only",
      "handle_queue_loop" not in read("src/bridge/raphael_bridge.py")
      and "handle_queue_loop" not in "".join(
          read(r) for r in mods.values() if r.endswith(".py")
          and r not in ("src/orchestrator/modes/autonomous.py",)
          and "__pycache__" not in r),
      "no consumer caller outside its own module")
check("U2/session-no-primitive",
      scan_source(read("src/orchestrator/api/session.py"),
                  "src/orchestrator/api/session.py") == []
      and scan_source(read("src/orchestrator/api/session_manager.py"),
                      "src/orchestrator/api/session_manager.py") == [],
      "zero lexicon hits (sqlite not in lexicon)")

# ---------------------------------------------------------------- phases + weld + standalone (H)
from orchestrator.brain.phases.models import PHASE_EXECUTORS  # noqa: E402 (data-only)
PHASES = list(PHASE_EXECUTORS.items())
check("H/phase-count", len(PHASES) == 13, f"phases={len(PHASES)}")
phase_region = cls_text.split("## 4. PHASE_EXECUTORS")[1].split("## 5.")[0] \
    if "## 4. PHASE_EXECUTORS" in cls_text else ""
phase_missing = [name for name, _ in PHASES if f"| {name} |" not in phase_region]
check("H/every-phase-classified", not phase_missing, f"missing={phase_missing[:5]}")
import inspect as _inspect  # noqa: E402
stub_set = {name for name, fn in PHASES if "NOT_IMPLEMENTED" in _inspect.getsource(fn)}
check("H/stub-derived", len(stub_set) == 9, f"source-derived stubs={len(stub_set)}")
stub_unmarked = [n for n in stub_set if f"| {n} |" not in phase_region
                 or "P26" not in phase_region.split(f"| {n} |")[1].split("\n")[0]]
check("H/stubs-to-P26", not stub_unmarked, f"unmarked={stub_unmarked[:5]}")
live_unmarked = [n for n, _ in PHASES if n not in stub_set
                 and (f"| {n} |" not in phase_region
                      or "P07" not in phase_region.split(f"| {n} |")[1].split("\n")[0])]
check("H/real-to-P07", not live_unmarked, f"unmarked={live_unmarked[:5]}")
weld_text = (RDIR / "WELD_SET.md").read_text()
weld_paths = set(re.findall(r"R3\.0-P\d{2}", weld_text.split("## Weld set")[1].split("## Explicitly")[0]))
class_paths = set(re.findall(r"R3\.0-P\d{2}",
                             cls_text.split("### Welded (AM-4)")[1].split("### Dead")[0]))
check("H/weld-set-reconciled", weld_paths == class_paths,
      f"weld={len(weld_paths)} class={len(class_paths)}")
def _tag(disp):
    return disp.split(" ")[0] if disp else ""


uncovered = sorted(f for f in census_files if "not-yet" in doc_disp.get(f, "")
                   and f"R3.0-{_tag(doc_disp.get(f, ''))}" not in weld_paths)
check("H/every-notyet-in-weld", not uncovered, f"uncovered={uncovered[:5]}")
welded = sorted(f for f in census_files if "welded" in doc_disp.get(f, ""))
unmapped = sorted(f for f in welded
                  if f"R3.0-{_tag(doc_disp.get(f, ''))}" not in weld_paths)
check("H/every-welded-in-weld", not unmapped, f"unmapped={unmapped[:5]}")
check("H/no-notyet-remain", not any("not-yet" in d for d in doc_disp.values()),
      "all former not-yet rows read welded")
# AM-4 gate presence at the choke points (fail-closed Broker mediation).
_chokes = {
    "src/orchestrator/api/tools.py": "require_broker_mediation",
    "src/orchestrator/chains/tool_registry.py": "enforce_broker_mediation",
    "src/orchestrator/api/tools_bridge.py": "enforce_broker_mediation",
    "src/kali-tools/server.py": "enforce_broker_mediation",
    "src/orchestrator/kali_tools_client.py": "enforce_broker_mediation",
    "src/orchestrator/agents/engage.py": "enforce_broker_mediation",
    "src/orchestrator/agents/exploit.py": "enforce_broker_mediation",
    "src/orchestrator/sandbox.py": "enforce_broker_mediation",
    "src/orchestrator/modes/autonomous.py": "enforce_broker_mediation",
    "src/bridge/raphael_bridge.py": "enforce_broker_mediation",
    "src/raphael/executor/kali_bridge.py": "enforce_broker_mediation",
    "src/raphael/main.py": "run_episode",
}
_ungated = [f for f, tok in _chokes.items() if tok not in read(f)]
check("H/weld-gates-present", not _ungated, f"ungated={_ungated[:5]}")
SVC_FRAGS = ["mhddos", "recon-pipeline", "sword/api", "agent/agent", "phishing/main",
             "cai-service", "cloak", "exploit_factory", "verifier", "kali-tools",
             "mcp-hub", "modes/scan", "c2-server"]
svc_missing = [s for s in SVC_FRAGS if s not in cls_text]
check("H/standalone-classified", not svc_missing, f"missing={svc_missing[:5]}")

# ---------------------------------------------------------------- legacy CLI branch (L)
def _calls_in(fn_node: ast.AST) -> set:
    out = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call):
            f, parts = n.func, []
            while isinstance(f, ast.Attribute):
                parts.append(f.attr)
                f = f.value
            if isinstance(f, ast.Name):
                parts.append(f.id)
                out.add(".".join(reversed(parts)))
    return out


def _methods_of(tree: ast.AST, cls: str) -> dict:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            return {s.name: s for s in node.body
                    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {}


def _top_fn(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


leg = tree_of("src/raphael/main.py")
_main_fn = _top_fn(leg, "main")
_main_calls = _calls_in(_main_fn) if _main_fn is not None else set()
_main_src = read("src/raphael/main.py")
check("L/legacy-removed",
      "os.environ.get('RAPHAEL_USE_LEGACY'" not in _main_src
      and "await organism.run()" not in _main_src
      and "RaphaelOrganism(config)" not in _main_src
      and any("run_episode" in c for c in _main_calls),
      "main() legacy branch deleted; canonical run_episode only")
check("L/organism-dead",
      "RaphaelOrganism(" not in _main_src.replace("class RaphaelOrganism", ""),
      "no Organism instantiation site remains (class kept for P9)")
# AM-4: the legacy chain is dead code — its effects are confined to the
# unreachable Organism class (no live callers outside it).
_hyp_sites = []
for rel in sorted(census_files):
    if rel in ("src/raphael/cortex/hypothesizer.py",
               "src/raphael/hippocampus/episode_store.py"):
        continue
    if disp_class(doc_disp.get(rel, "")) == "dead":
        continue  # dead-plane internal calls (e.g. planner) are not live sites
    try:
        t = read(rel)
    except OSError:
        continue
    if "hypothesizer.hypothesize(" in t or "hippocampus.store(" in t:
        _hyp_sites.append(rel)
check("L/legacy-confined", _hyp_sites == [],
      f"hypothesize/store invoked only inside dead legacy code (sites={_hyp_sites[:3]})")
kb_src = read("src/raphael/executor/kali_bridge.py")
check("L/kalibridge-gated",
      "enforce_broker_mediation" in kb_src
      and "create_subprocess" not in kb_src,
      "kali_bridge.run proposes to Broker first; no subprocess")
_p27_files = sorted(f for f in census_files if doc_disp.get(f, "").startswith("P27 "))
check("L/p27-set",
      _p27_files == ["src/raphael/cortex/hypothesizer.py",
                     "src/raphael/executor/kali_bridge.py",
                     "src/raphael/hippocampus/episode_store.py"],
      f"p27={_p27_files}")
check("L/p27-in-weld", "R3.0-P27" in weld_paths, "P27 welded-tracked")

print()
print(f"SUMMARY  pass={len(PASS)} fail={len(FAIL)} paths=27 mediated=3 "
      f"welded=15 not-yet=0 dead-groups=9 census=150 bridge=40 routes=27 phases=13")
if FAIL:
    print("FAILURES:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
print("REINVENTORY-PROBE-OK")
