"""P3.0 re-inventory probe (read-only; reproduces every CLASSIFICATION.md trace).

Reads source via AST. Never imports legacy/offensive modules, never touches the
network, never executes a primitive. The single canonical import (RaphaelRuntime +
inv1_guard) is the same import the gate suite already performs.

Run:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 evidence/phases/P3_0_reinventory/probe_reinventory.py
Exit 0 iff every check passes.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def read(rel: str) -> str:
    return (REPO / rel).read_text(errors="ignore")


def tree_of(rel: str) -> ast.AST:
    return ast.parse(read(rel))


def src_has(rel: str, needle: str) -> bool:
    return needle in read(rel)


def ast_imports(rel: str) -> set[str]:
    found: set[str] = set()
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
                for a in node.names:
                    found.add(f"{node.module}.{a.name}")
    return found


def ast_calls(rel: str) -> set[str]:
    out: set[str] = set()

    def dotted(n: ast.AST) -> str:
        parts: list[str] = []
        while isinstance(n, ast.Attribute):
            parts.append(n.attr)
            n = n.value  # type: ignore[assignment]
        if isinstance(n, ast.Name):
            parts.append(n.id)
            return ".".join(reversed(parts))
        return ""

    try:
        tree = tree_of(rel)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            d = dotted(node.func)
            if d:
                out.add(d)
    return out


def defined_names(rel: str) -> set[str]:
    """Code-level defined names (ignores comments/docstrings): every
    FunctionDef/AsyncFunctionDef/ClassDef name plus every assigned target id."""
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


def route_paths(rel: str) -> list[str]:
    paths: list[str] = []
    try:
        tree = tree_of(rel)
    except SyntaxError:
        return paths
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                try:
                    s = ast.unparse(dec)
                except Exception:
                    s = ""
                if "router." in s and ("post" in s or "get" in s):
                    paths.append(f"{node.name}:{s.strip()}")
    return paths


# ---------------------------------------------------------------- T1: api/tools -> tool_registry (SUB-04)
main_src = read("src/orchestrator/api/main.py")
check("T1/mount-tools", "tools_router" in main_src and "include_router" in main_src,
      "api/main.py mounts tools_router")
tools_routes = route_paths("src/orchestrator/api/tools.py")
check("T1/route-tools-exec", any("{tool" in r or "tool_name" in r for r in tools_routes),
      f"tools routes={len(tools_routes)}")
check("T1/tools-imports-registry",
      "orchestrator.chains.tool_registry" in ast_imports("src/orchestrator/api/tools.py"),
      "tools.py imports chains.tool_registry")
check("T1/sub04-site", "create_subprocess_exec" in read("src/orchestrator/chains/tool_registry.py"),
      "tool_registry._run_command primitive present")
check("T1/no-broker-tools",
      "propose_action" not in read("src/orchestrator/api/tools.py")
      and "propose_action" not in read("src/orchestrator/chains/tool_registry.py"),
      "no broker on tools path")

# ------------------------------------------------- T1b: tools_bridge (unauthenticated hop)
tb_routes = route_paths("src/orchestrator/api/tools_bridge.py")
check("T1b/routes", any("nmap" in r for r in tb_routes) and any("recon" in r for r in tb_routes),
      f"bridge routes={tb_routes}")
check("T1b/no-auth", "require_scope" not in read("src/orchestrator/api/tools_bridge.py")
      and "Depends" not in read("src/orchestrator/api/tools_bridge.py"),
      "tools_bridge declares no auth dependency")
check("T1b/hop", "KALI_CONTAINER_URL" in read("src/orchestrator/api/tools_bridge.py")
      and "/run" in read("src/orchestrator/api/tools_bridge.py"),
      "bridge posts to kali-tools /run")

# ------------------------------------------------- T2: kali-tools/server.py /run sink
srv = read("src/kali-tools/server.py")
check("T2/route-run", '"/run"' in srv and "def run_tool" in srv, "POST /run present")
check("T2/sink", "subprocess.run" in srv, "subprocess.run sink present")
check("T2/no-auth", "Depends" not in srv and "require_scope" not in srv
      and "APIKey" not in srv and "Authorization" not in srv
      and "require_scope" not in srv.split("def run_tool")[0],
      "no auth on runner")
check("T2/no-broker", "propose_action" not in srv, "no broker in runner")

# ------------------------------------------------- T3: bridge -> autonomous -> chains -> kali/c2
br = read("src/bridge/raphael_bridge.py")
check("T3/bridge-method", '"mode.autonomous"' in br and "async def mode_autonomous" in br,
      "bridge exposes mode.autonomous")
check("T3/bridge-kali-c2", '"kali.run"' in br and '"c2.build_implant"' in br,
      "bridge exposes kali.* and c2.*")
auto = read("src/orchestrator/modes/autonomous.py")
check("T3/auto-imports-chains",
      "chains.credential_spray" in auto and "chains.ad_kill_chain" in auto,
      "autonomous imports both chains")
adk = read("src/orchestrator/chains/ad_kill_chain.py")
spr = read("src/orchestrator/chains/credential_spray.py")
check("T3/chains-import-kali-c2",
      "kali_tools_client" in adk and "c2.manager" in adk
      and "kali_tools_client" in spr and "c2.manager" in spr,
      "chains import kali + c2.manager")
check("T3/no-broker-chain",
      "propose_action" not in auto and "propose_action" not in adk and "propose_action" not in spr
      and "propose_action" not in br,
      "no broker on bridge->autonomous->chains path")

# ------------------------------------------------- P11: c2 primitive sites
slv = read("src/orchestrator/c2/sliver_backend.py")
ibl = read("src/orchestrator/c2/implant_builder.py")
mgr = read("src/orchestrator/c2/manager.py")
check("P11/sliver-sites", slv.count("create_subprocess_exec") >= 2, "SUB-05/06 present")
check("P11/implant-sites", ibl.count("create_subprocess_exec") >= 3, "SUB-07/08/09 present")
check("P11/implant-shell", "subprocess.run" in ibl, "implant_builder shell=True path present")
check("P11/manager-loads-backends", "SliverBackend" in mgr and "NativeC2Backend" in mgr,
      "c2.manager reaches both backends")
check("P11/no-broker-c2", "propose_action" not in slv and "propose_action" not in ibl
      and "propose_action" not in mgr, "no broker in c2/*")

# ------------------------------------------------- T4: canonical run_episode -> exec/ (control)
sys.path.insert(0, str(SRC))
try:
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.scope import ScopeV0
    from orchestrator.exec.inv1_guard import (
        canonical_perimeter_modules,
        verify_inv1_primitive_confinement,
    )
    scope = ScopeV0(mission_id="probe", targets=("system_info.name",),
                    allowed_action_types=("safe_proving_capability",),
                    allowed_capabilities=("fixture.inspect",), max_impact=0.0)
    rt = RaphaelRuntime()
    mission = MissionContext(mission_id="probe", name="probe", objectives=["probe"],
                             constraints={"default_target": "system_info.name"}, scope=scope)
    traces, term = rt.run_episode(mission, require_scope=True)
    stages = [e["stage"] for e in traces[0].entries] if traces else []
    check("T4/episode-runs", bool(traces) and "broker" in stages and "pep" in stages and "receipt" in stages,
          f"stages={stages}")
    mods = canonical_perimeter_modules(REPO)
    viol = verify_inv1_primitive_confinement(REPO, mods)
    check("T4/inv1-perimeter-clean", viol == [], f"modules={len(mods)} violations={len(viol)}")
    legacy_needles = ("orchestrator.modes", "orchestrator.api", "orchestrator.chains",
                      "orchestrator.c2", "kali_tools_client")
    zero = all(not any(m == n or m.startswith(n + ".") for m in mods) for n in legacy_needles)
    check("T4/canonical-zero-reference", zero, f"perimeter_modules={len(mods)}")
except Exception as e:  # fail-closed: a broken canonical path is itself a finding
    check("T4/episode-runs", False, f"raised {type(e).__name__}: {e}")
    check("T4/inv1-perimeter-clean", False, "episode failed first")
    check("T4/canonical-zero-reference", False, "episode failed first")

# ------------------------------------------------- T4b: CLI caller
cli = read("src/raphael/main.py")
check("T4b/cli-imports-runtime", "from orchestrator.runtime import RaphaelRuntime" in cli,
      "CLI imports canonical Runtime")
check("T4b/cli-scope", "ScopeV0(" in cli and "require_scope=True" in cli,
      "CLI binds ScopeV0 + require_scope")
check("T4b/cli-legacy-guarded", "RAPHAEL_USE_LEGACY" in cli, "legacy branch opt-in only")

# ------------------------------------------------- P13: SHELL gating
cap = read("src/orchestrator/capabilities/interactive_shell/capability.py")
rev = read("src/orchestrator/capabilities/interactive_shell/reverse_shell.py")
ssh = read("src/orchestrator/capabilities/interactive_shell/ssh_shell.py")
lst = read("src/orchestrator/capabilities/interactive_shell/listener_manager.py")
check("P13/gate-present", "class ShellNotAuthorized" in cap and "def require_shell_authorization" in cap,
      "gate helper present")
check("P13/ctors-gated", "require_shell_authorization" in rev and "require_shell_authorization" in ssh
      and "require_shell_authorization" in cap and "require_shell_authorization" in lst,
      "all constructors + listener methods gated")
check("P13/broker-string", 'authorized_by="capability_broker"' in read("src/orchestrator/brain/capability_broker.py"),
      "receipt authorizer is capability_broker")

# ------------------------------------------------- P14: dead standalone (importer search)
SEARCH_ROOTS = ["src/orchestrator/runtime", "src/orchestrator/brain", "src/orchestrator/exec",
                "src/orchestrator/api", "src/orchestrator/modes", "src/orchestrator/chains",
                "src/orchestrator/c2", "src/orchestrator/agents", "src/bridge",
                "src/raphael/main.py"]
dead_markers = {"weaponizer": "weaponizer", "recon-pipeline": "recon-pipeline",
                "agent.modules.executor": "agent.modules.executor",
                "sword.phase_0_recon": "sword.phase_0_recon"}
blob: list[str] = []
for r in SEARCH_ROOTS:
    p = SRC / Path(r).name if r.startswith("src/") and "/" not in r[4:] else REPO / r
    if p.is_file():
        blob.append(p.read_text(errors="ignore"))
    elif p.is_dir():
        for f in sorted(p.rglob("*.py")):
            if "__pycache__" in str(f):
                continue
            blob.append(f.read_text(errors="ignore"))
big = "\n".join(blob)
for label, needle in dead_markers.items():
    check(f"P14/dead-{label}", needle not in big, f"zero importers of {needle}")

# ------------------------------------------------- P15/P03: welded stubs absent (code-level:
# the WELD header comments name the removed symbols, so substring search would
# false-positive on comments; AST definitions are the ground truth, matching the
# gate suite's hasattr/definition-string assertions)
kali_defs = defined_names("src/orchestrator/kali_tools_client.py")
exec_defs = defined_names("src/raphael/executor/executor.py")
kbr_defs = defined_names("src/raphael/executor/kali_bridge.py")
check("P15/absent-_run_local", "_run_local" not in kali_defs, "_run_local def deleted")
check("P15/absent-KaliBypassNotAuthorized", "KaliBypassNotAuthorized" not in kali_defs,
      "KaliBypassNotAuthorized class deleted")
check("P15/absent-_BYPASS_AUTHORIZED", "_BYPASS_AUTHORIZED" not in kali_defs,
      "_BYPASS_AUTHORIZED flag deleted")
check("P15/absent-authorize_local_bypass", "authorize_local_bypass" not in kali_defs,
      "authorize_local_bypass opt-in deleted")
check("P15/absent-_subprocess_fallback", "_subprocess_fallback" not in exec_defs,
      "_subprocess_fallback method deleted")
check("P15/absent-_subprocess_run", "_subprocess_run" not in kbr_defs,
      "_subprocess_run method deleted")
check("P15/absent-authorize_bypass",
      "authorize_bypass" not in exec_defs and "authorize_bypass" not in kbr_defs,
      "authorize_bypass opt-in deleted")
check("P15/absent-BypassNotAuthorized", "BypassNotAuthorized" not in exec_defs,
      "BypassNotAuthorized class deleted")
check("P03/no-create-subprocess-raphael",
      "create_subprocess" not in read("src/raphael/executor/executor.py")
      and "create_subprocess" not in read("src/raphael/executor/kali_bridge.py"),
      "zero create_subprocess under src/raphael/")
check("P15/fail-closed-strings",
      "_run_local is removed in WELD-SUB10" in read("src/orchestrator/kali_tools_client.py")
      and "_subprocess_fallback() is removed in WELD-SUB14" in read("src/raphael/executor/kali_bridge.py"),
      "documented fail-closed RuntimeErrors present")

# ------------------------------------------------- agent/ci reachability (P06-P08)
ag = read("src/orchestrator/api/agent.py")
ci = read("src/orchestrator/api/ci.py")
check("P06/agent-imports-engage", "agents.engage" in ag and "run_agent_engage" in ag,
      "agent.py reaches engage")
check("P07/ci-imports-auto", "modes.autonomous" in ci and "autonomous_handle" in ci,
      "ci.py reaches autonomous.handle")
check("P08/ci-imports-engage", "run_agent_engage" in ci, "ci.py reaches engage")
check("P0608/no-broker", "propose_action" not in ag and "propose_action" not in ci
      and "propose_action" not in auto, "no broker on agent/ci paths")

print()
print(f"SUMMARY  pass={len(PASS)} fail={len(FAIL)} "
      f"paths=15 mediated=3 not-yet-mediated=9 dead-groups=3")
if FAIL:
    print("FAILURES:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
print("REINVENTORY-PROBE-OK")
