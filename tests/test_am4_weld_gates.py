"""AM-4 weld-gate tests (ADR-012): every WELD_SET path denies without Broker AUTHORIZED.

Per v4.1 AM-4 weld discipline (weld semantics: seam fixed ON = permanently
routed through Broker/PEP; legacy branch deleted; named policy artifact):
- each weld-item entry/sink raises fail-closed (WeldNotAuthorized / HTTP 403)
  without a Broker AUTHORIZED decision;
- deleted legacy branches stay absent (AST);
- P17 dead-end behaviors are preserved (no gate where no weld applies);
- the gate itself is not blanket-deny (canonical fixture capability AUTHORIZEs).

 deepenings: W-15 branch deletion, W-01/W-02 sinks, W-07/W-15 client tests live
 in test_p2_guardrail_sub10_closed.py / test_p2_guardrail_sub13_closed.py.
"""
import ast
import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from orchestrator.auth import (
    WeldNotAuthorized,
    enforce_broker_mediation,
)


def _src(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


def _tree(rel: str) -> ast.AST:
    return ast.parse(_src(rel))


def _has_gate_call(tree: ast.AST, func_names) -> bool:
    """True iff one of the named functions contains an enforce_broker_mediation call."""
    if isinstance(func_names, str):
        func_names = {func_names}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in func_names:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    name = f.attr if isinstance(f, ast.Attribute) else (
                        f.id if isinstance(f, ast.Name) else "")
                    if name == "enforce_broker_mediation":
                        return True
    return False


# ── gate unit ──────────────────────────────────────────────────────────

def test_gate_denies_by_default_with_path_and_ticket():
    with pytest.raises(WeldNotAuthorized) as exc_info:
        enforce_broker_mediation(
            target="t", action_type="tool_execute", capability="nmap",
            method="run", impact_estimate=5.0, path_id="R3.0-P04",
            weld_ticket="W-01",
        )
    msg = str(exc_info.value)
    assert "R3.0-P04" in msg and "W-01" in msg and "Broker" in msg


def test_gate_authorizes_canonical_fixture_capability():
    receipt = enforce_broker_mediation(
        target="t", action_type="safe_proving_capability",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
        path_id="R3.0-P01", weld_ticket="W-00",
    )
    assert receipt is not None


# ── W-15: legacy CLI branch deleted ────────────────────────────────────

def test_w15_legacy_branch_deleted():
    text = _src("src/raphael/main.py")
    assert "os.environ.get('RAPHAEL_USE_LEGACY'" not in text
    assert "await organism.run()" not in text
    assert "RaphaelOrganism(config)" not in text
    assert "run_episode" in text  # canonical path intact


# ── W-01: tools sink + route ───────────────────────────────────────────

def test_w01_run_command_denies():
    from orchestrator.chains.tool_registry import _run_command
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(_run_command(["echo", "hi"], timeout=5))
    assert "R3.0-P04" in str(exc_info.value) and "W-01" in str(exc_info.value)


def test_w01_route_and_sink_reference_gate():
    assert "require_broker_mediation" in _src("src/orchestrator/api/tools.py")
    assert _has_gate_call(_tree("src/orchestrator/chains/tool_registry.py"), "_run_command")


# ── W-02: tools_bridge sink ────────────────────────────────────────────

def test_w02_run_in_kali_denies():
    # Direct file load: orchestrator.api.__init__ is unimportable in-tree
    # (pre-existing agents/exploit sandbox collision); tools_bridge itself
    # has no orchestrator imports.
    mod = _load_module("tools_bridge", "src/orchestrator/api/tools_bridge.py")
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(mod._run_in_kali("nmap", ["-F", "t"], timeout=5))
    assert "R3.0-P05" in str(exc_info.value) and "W-02" in str(exc_info.value)


# ── W-03/W-05/W-08-adjacent: engage + agent/ci routes reference gates ──

def test_w03_w05_engage_and_routes_reference_gate():
    assert _has_gate_call(_tree("src/orchestrator/agents/engage.py"), "run_agent_engage")
    for rel in ("src/orchestrator/api/agent.py", "src/orchestrator/api/ci.py"):
        assert "require_broker_mediation" in _src(rel), rel


# ── W-04/W-06: autonomous.handle ───────────────────────────────────────

def test_w04_autonomous_handle_denies():
    from orchestrator.modes.autonomous import handle
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(handle("t", phases=["recon"]))
    assert "R3.0-P07" in str(exc_info.value) and "W-04" in str(exc_info.value)


# ── W-06..W-13: bridge dispatch gate ───────────────────────────────────

def _weld_bridge_table():
    tree = _tree("src/bridge/raphael_bridge.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_WELD_BRIDGE_METHODS":
                    return {k.value: v.value for k, v in zip(node.value.keys, node.value.values)
                            if isinstance(k, ast.Constant)}
    return {}


def test_bridge_weld_table_covers_all_weld_path_methods():
    table = _weld_bridge_table()
    expected = {
        "mode.autonomous",
        "kali.run", "kali.nuclei", "kali.sqlmap", "kali.hashcat",
        "kali.impacket", "kali.list_tools",
        "c2.build_implant", "c2.deploy", "c2.list_beacons",
        "c2.task_beacon", "c2.sliver_connect",
        "exploit.generate", "exploit.relay_chain", "exploit.mcp_start",
        "exploit.mcp_exploit",
        "mode.community", "mode.debate", "mode.deep_research",
        "mode.scan", "mode.student",
        "harvester.run_cycle", "harvester.search_techniques",
        "harvester.get_cves",
        "model.call", "target.profile",
    }
    assert set(table) == expected, f"table={sorted(table)}"
    assert set(table.values()) == {"R3.0-P09", "R3.0-P10", "R3.0-P11",
                                   "R3.0-P18", "R3.0-P19", "R3.0-P20"}


def test_bridge_p17_methods_not_gated():
    table = _weld_bridge_table()
    for m in ("agent.recon", "agent.exploit", "agent.postex", "agent.engage",
              "exploit.payload_db", "conductor.call", "conductor.select_strategy",
              "brain.analytics", "brain.memory_store", "brain.memory_recall",
              "persona.set", "persona.resolve", "target.set", "scope.set"):
        assert m not in table, f"P17 method must keep exact behavior: {m}"


def test_bridge_handle_request_enforces_before_dispatch():
    tree = _tree("src/bridge/raphael_bridge.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle_request":
            src = ast.unparse(node)
            assert "enforce_broker_mediation" in src
            assert "_WELD_BRIDGE_METHODS" in src
            return
    raise AssertionError("handle_request not found")


# ── W-09: kali-tools server ────────────────────────────────────────────

def _load_module(name: str, rel: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(REPO_ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_package(mod_name: str, rel: str):
    """Load a hyphenated service module with package context for relatives."""
    import types
    import importlib.util
    pkg_name, _, _ = mod_name.rpartition(".")
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(REPO_ROOT / rel.rsplit("/", 1)[0])]
    sys.modules[pkg_name] = pkg
    spec = importlib.util.spec_from_file_location(mod_name, str(REPO_ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_w09_kali_server_run_denies_403():
    from fastapi import HTTPException
    mod = _load_module("kalisrv", "src/kali-tools/server.py")
    with pytest.raises(HTTPException) as exc_info:
        mod.run_tool("nmap", "-F t", 5)
    assert exc_info.value.status_code == 403
    assert "R3.0-P12" in exc_info.value.detail and "W-09" in exc_info.value.detail


# ── W-10: sandbox sink + exploit dispatcher (AST: shadowed package) ────

def test_w10_run_code_and_dispatcher_reference_gate():
    assert _has_gate_call(_tree("src/orchestrator/sandbox.py"), "run_code")
    assert _has_gate_call(_tree("src/orchestrator/agents/exploit.py"), "execute")


# ── W-12/W-13 sinks ────────────────────────────────────────────────────

def test_w12_scan_handle_denies():
    from orchestrator.modes.scan import handle
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(handle("t"))
    assert "R3.0-P19" in str(exc_info.value) and "W-12" in str(exc_info.value)


def test_w12_student_handle_denies():
    from orchestrator.modes.student import handle
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(handle("t"))
    assert "R3.0-P19" in str(exc_info.value) and "W-12" in str(exc_info.value)


def test_w12_call_model_denies():
    from orchestrator.providers import call_model
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(call_model("x", [{"role": "user", "content": "hi"}]))
    assert "R3.0-P19" in str(exc_info.value) and "W-12" in str(exc_info.value)


def test_w13_harvester_denies(tmp_path):
    from orchestrator.harvester.harvester_engine import HarvesterEngine
    eng = HarvesterEngine(db_path=str(tmp_path / "h.db"))
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(eng.run_full_cycle(target="t"))
    assert "R3.0-P20" in str(exc_info.value) and "W-13" in str(exc_info.value)
    with pytest.raises(WeldNotAuthorized):
        eng.search("q")


def test_w13_profile_target_denies():
    from orchestrator.brain.target_profiler import profile_target
    with pytest.raises(WeldNotAuthorized) as exc_info:
        profile_target("t")
    assert "R3.0-P20" in str(exc_info.value) and "W-13" in str(exc_info.value)


def test_w08_implant_builder_denies(tmp_path, monkeypatch):
    import orchestrator.c2.implant_builder as ib
    monkeypatch.setattr(ib, "IMPLANT_DIR", str(tmp_path / "implants"))
    b = ib.ImplantBuilder()
    with pytest.raises(WeldNotAuthorized) as exc_info:
        asyncio.run(b.build())
    assert "R3.0-P11" in str(exc_info.value) and "W-08" in str(exc_info.value)


def test_w14_pipelines_and_scanners_deny():
    from orchestrator.exploit.pipeline import ExploitPipeline
    from orchestrator.postex.pipeline import PostExploitPipeline
    from orchestrator.scanners.nmap_scanner import NmapScanner
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(ExploitPipeline().run("t"))
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(PostExploitPipeline().run("t"))
    with pytest.raises(WeldNotAuthorized):
        NmapScanner().scan_ports("t")


# ── W-14 service entries ───────────────────────────────────────────────

def test_w14_mhddos_attack_denies_403():
    from fastapi import HTTPException
    mod = _load_module("mhddos_main", "src/mhddos-service/main.py")
    req = mod.AttackRequest(target="t", method="GET")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mod.launch_attack(req))
    assert exc_info.value.status_code == 403


def test_w14_sword_run_denies_403():
    from fastapi import HTTPException
    from sword.api import sword_run, SwordRequest
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sword_run(SwordRequest(target="t")))
    assert exc_info.value.status_code == 403


def test_w14_agent_implant_denies():
    import agent.agent as agent_mod
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(agent_mod.main())


def test_w14_cai_entries_deny():
    mod = _load_module("cai_main", "src/cai-service/main.py")
    out = asyncio.run(mod.agent_scan(mod.ScanRequest(target="t")))
    assert isinstance(out, dict) and "W-14" in out.get("error", "")
    out = asyncio.run(mod.agent_exploit(mod.ExploitRequest(target="t")))
    assert isinstance(out, dict) and "W-14" in out.get("error", "")
    out = asyncio.run(mod.agent_chat(mod.ChatRequest(messages=[])))
    assert isinstance(out, dict) and "error" in out


def test_w14_fast_port_scan_denies(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["fast_port_scan", "--target", "t"])
    mod = _load_module("fast_scan", "src/raphael/techniques/fast_port_scan.py")
    with pytest.raises(WeldNotAuthorized):
        mod.main()


def test_w14_cloack_phishing_recon_factory_verifier_reference_gate():
    for rel in ("src/cloak-service/main.py",
                "src/phishing/main.py",
                "src/recon-pipeline/main.py",
                "src/raphael/exploit_factory/__main__.py",
                "src/raphael/verifier/__main__.py"):
        assert "enforce_broker_mediation" in _src(rel), rel


def _func_calls(tree: ast.AST, func_name: str) -> set:
    """Dotted names of calls inside the named function (comments excluded)."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == func_name:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f, parts = sub.func, []
                    while isinstance(f, ast.Attribute):
                        parts.append(f.attr)
                        f = f.value
                    if isinstance(f, ast.Name):
                        parts.append(f.id)
                        out.add(".".join(reversed(parts)))
    return out


# ── AM-4-R2 branch deletion (ADR-012 §2: legacy branch deleted) ─────────

def test_r2_w01_run_command_body_deleted():
    calls = _func_calls(_tree("src/orchestrator/chains/tool_registry.py"), "_run_command")
    assert "asyncio.create_subprocess_exec" not in calls
    assert _has_gate_call(_tree("src/orchestrator/chains/tool_registry.py"), "_run_command")


def test_r2_w09_kali_server_body_deleted():
    calls = _func_calls(_tree("src/kali-tools/server.py"), "run_tool")
    assert "subprocess.run" not in calls


def test_r2_w07_kali_client_body_deleted():
    calls = _func_calls(_tree("src/orchestrator/kali_tools_client.py"), "run")
    assert not any(c.startswith("httpx.") for c in calls)


def test_r2_w10_run_code_body_deleted():
    calls = _func_calls(_tree("src/orchestrator/sandbox.py"), "run_code")
    assert "subprocess.run" not in calls


def test_r2_w08_build_dispatch_deleted():
    tree = _tree("src/orchestrator/c2/implant_builder.py")
    calls = _func_calls(tree, "build")
    assert not calls - {"enforce_broker_mediation", "WeldNotAuthorized"}
    assert _has_gate_call(tree, "build")


def test_r2_w08_sliver_bodies_deleted():
    tree = _tree("src/orchestrator/c2/sliver_backend.py")
    for fn in ("generate_implant", "_import_config"):
        calls = _func_calls(tree, fn)
        assert "asyncio.create_subprocess_exec" not in calls, fn
        assert "os.unlink" not in calls, fn


def test_r2_w08_beacon_start_body_deleted():
    tree = _tree("src/orchestrator/c2/beacon.py")
    assert _has_gate_call(tree, "start")
    calls = _func_calls(tree, "start")
    assert not any(c.startswith("web.") for c in calls)


def test_r2_w14_mhddos_branches_deleted():
    tree = _tree("src/mhddos-service/main.py")
    calls = _func_calls(tree, "rotate_proxy")
    assert not any(c.startswith("socket.") for c in calls)
    assert _has_gate_call(tree, "rotate_proxy")


def test_r2_w14_cloak_helpers_deleted():
    tree = _tree("src/cloak-service/main.py")
    for fn in ("get_tor_ip", "rotate_tor_identity"):
        assert _has_gate_call(tree, fn), fn
    health_calls = _func_calls(tree, "health")
    assert "get_tor_ip" not in health_calls
    assert not any(c.startswith("httpx.") for c in health_calls)


def test_r2_w14_agent_branches_deleted():
    calls = _func_calls(_tree("src/agent/agent.py"), "execute_task")
    assert "subprocess.run" not in calls
    assert "shutil.rmtree" not in calls
    assert "os._exit" not in calls


def test_r2_w14_sword_health_gated_not_deleted():
    # Census-blocked deletion (§2-deferred with rationale in source):
    # os.popen retained behind the gate so CENSUS row #48 keeps its hit.
    tree = _tree("src/sword/api.py")
    assert _has_gate_call(tree, "health")
    assert "os.popen" in _func_calls(tree, "health")


# ── AM-4-R2 new gates (repairs + §4 internal helpers) ───────────────────

def test_r2_mhddos_rotate_denies_403():
    from fastapi import HTTPException
    mod = _load_module("mhddos_main", "src/mhddos-service/main.py")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mod.rotate_proxy())
    assert exc_info.value.status_code == 403


def test_r2_cloak_identities_denies_403():
    from fastapi import HTTPException
    mod = _load_package("cloakpkg.main", "src/cloak-service/main.py")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mod.identities())
    assert exc_info.value.status_code == 403


def test_r2_cloak_helpers_deny():
    # Helpers map denial to 403 (service-internal convention).
    from fastapi import HTTPException
    mod = _load_package("cloakpkg2.main", "src/cloak-service/main.py")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mod.get_tor_ip())
    assert exc_info.value.status_code == 403
    with pytest.raises(HTTPException) as exc_info:
        mod.rotate_tor_identity()
    assert exc_info.value.status_code == 403


def test_r2_sword_health_denies_403():
    from fastapi import HTTPException
    from sword.api import health as sword_health
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sword_health())
    assert exc_info.value.status_code == 403


def test_r2_phishing_status_routes_deny_403(tmp_path, monkeypatch):
    # phishing/main.py mkdirs /app/templates at import; point it at tmp.
    from fastapi import HTTPException
    monkeypatch.setenv("TEMPLATE_DIR", str(tmp_path))
    import phishing.main as ph
    with pytest.raises(HTTPException) as exc_info:
        ph.list_tools()
    assert exc_info.value.status_code == 403
    with pytest.raises(HTTPException) as exc_info:
        ph.health()
    assert exc_info.value.status_code == 403


def test_r2_agent_execute_task_denies():
    import agent.agent as agent_mod
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(agent_mod.execute_task({"type": "exec", "payload": {"command": "id"}}))


def test_r2_proxyguard_report_helpers_deny():
    from orchestrator.proxy_guard import ProxyGuard
    pg = ProxyGuard()
    with pytest.raises(WeldNotAuthorized):
        pg.verify()
    with pytest.raises(WeldNotAuthorized):
        pg.new_circuit()
    from sword.report import SwordReport
    rep = SwordReport({"target": "t", "phases": {}})
    with pytest.raises(WeldNotAuthorized):
        rep.save(directory="/tmp/sword_probe_test")


def test_r2_sliver_beacon_relay_mcp_dga_helpers_deny():
    from orchestrator.c2.sliver_backend import SliverBackend
    from orchestrator.c2.beacon import BeaconHTTPServer
    from orchestrator.exploit.relay_chain import RelayChain
    from orchestrator.exploit.mcp_bridge import MCPBridge
    from orchestrator.c2.dga import DGAResolver
    sb = SliverBackend.__new__(SliverBackend)
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(sb.generate_implant.__get__(sb, SliverBackend)({"name": "x", "os": "linux", "arch": "amd64", "format": "exe"}))
    bc = BeaconHTTPServer.__new__(BeaconHTTPServer)
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(bc.start())
    rc = RelayChain.__new__(RelayChain)
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(rc.execute_chain())
    mb = MCPBridge.__new__(MCPBridge)
    with pytest.raises(WeldNotAuthorized):
        mb.start()
    dga = DGAResolver()
    with pytest.raises(WeldNotAuthorized):
        dga.resolve_domain("example.com")


def test_r2_recon_helpers_and_sinks_reference_gate():
    # recon-pipeline/main.py is not importable in-tree (pre-existing broken
    # `from .case_api` + missing `case_store` dep); assert gates statically.
    # run_subfinder holds the file's sole direct exec call; the chain fns and
    # both routes reference the gate.
    tree = _tree("src/recon-pipeline/main.py")
    assert _has_gate_call(tree, "run_subfinder")
    assert _has_gate_call(tree, "run_recon_chain")
    assert _has_gate_call(tree, "run_deep_recon")
    assert _has_gate_call(tree, "recon_run")
    assert _has_gate_call(tree, "recon_deep")
    from orchestrator.brain.target_profiler import _nmap_scan
    with pytest.raises(WeldNotAuthorized):
        _nmap_scan("t")
    from orchestrator.brain.target_profiler import _nmap_scan
    with pytest.raises(WeldNotAuthorized):
        _nmap_scan("t")


def test_r2_shared_sink_chokes_deny():
    from orchestrator.exploit.pipeline import ExploitPipeline
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(ExploitPipeline.__new__(ExploitPipeline).run("t"))
    from orchestrator.postex.pipeline import PostExploitPipeline
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(PostExploitPipeline.__new__(PostExploitPipeline).run("t"))
    from orchestrator.chains.tool_registry import execute_tool as reg_exec
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(reg_exec("nmap", {"target": "t"}))
    from sword.pipeline import run_sword
    with pytest.raises(WeldNotAuthorized):
        asyncio.run(run_sword("t"))
