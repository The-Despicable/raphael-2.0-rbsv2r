#!/usr/bin/env python3
"""Work tool: FINAL importer dump (variable bug fixed). Saved to raw/ as evidence."""
import ast
from pathlib import Path

REPO = Path("/home/yaser/external-audits/raphael-2")
SRC = REPO / "src"
mods = {}
for py in sorted(SRC.rglob("*.py")):
    if "__pycache__" in str(py):
        continue
    parts = list(py.relative_to(SRC).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    mods[".".join(parts)] = str(py.relative_to(REPO))


def to_mod(name):
    if name in mods:
        return name
    p = name.split(".")
    for i in range(len(p) - 1, 0, -1):
        c = ".".join(p[:i])
        if c in mods:
            return c
    return None


adj = {m: set() for m in mods}
for mod, rel in mods.items():
    try:
        tree = ast.parse((REPO / rel).read_text(errors="ignore"))
    except SyntaxError:
        continue
    parts = list(Path(rel).with_suffix("").parts[1:])
    pkg = ".".join(parts[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                t = to_mod(a.name)
                if t and t != mod:
                    adj[mod].add(t)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                up = node.level - 1
                b = pkg
                for _ in range(up):
                    b = b.rsplit(".", 1)[0] if "." in b else ""
                base = f"{b}.{node.module}" if node.module else b
            else:
                base = node.module or ""
            for a in node.names:
                if a.name == "*":
                    continue
                t = to_mod(f"{base}.{a.name}" if base else a.name) or to_mod(base)
                if t and t != mod:
                    adj[mod].add(t)
    for i in range(len(mod.split(".")) - 1, 0, -1):
        par = ".".join(mod.split(".")[:i])
        if par in mods and par != mod:
            adj[mod].add(par)

rev = {m: set() for m in mods}
for _m, _ds in adj.items():
    for _d in _ds:
        rev[_d].add(_m)

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
       "agent.agent", "mcp-hub.main", "mcp-hub.core.server", "phishing.main",
       "cai-service.main", "raphael.exploit_factory.__main__", "orchestrator.modes.scan",
       "cloak-service.main", "raphael.verifier.__main__"]
ENTRIES = [e for e in LIVE + SVC if e in mods]
seen = set(ENTRIES)
stack = list(ENTRIES)
pred = {}
while stack:
    cur = stack.pop()
    for d in adj[cur]:
        if d not in seen:
            seen.add(d)
            pred[d] = cur
            stack.append(d)


def trace(m):
    path = [m]
    while path[-1] in pred:
        path.append(pred[path[-1]])
    return " <- ".join(reversed(path))


print(f"MODULES={len(mods)} ENTRIES={len(ENTRIES)} REACHABLE={len(seen)}")
queries = [
    "orchestrator.ad.planner", "raphael.cortex.planner", "raphael.cognitive",
    "raphael.cognitive.reflection", "raphael.cognitive.hypothesizer",
    "raphael.hippocampus.episode_store", "raphael.limbic.parallel_recon",
    "raphael.circulatory.spinal_reflex", "raphael.executor.executor",
    "raphael.integration.harness", "raphael.verifier.channels", "raphael.verifier.core",
    "raphael.verifier.__main__", "orchestrator.mesh.mesh_engine",
    "orchestrator.nvidia_provider", "orchestrator.tactics.anonymous_ttp",
    "orchestrator.utils.retry", "raphael.scripts.blind_probe_runner",
    "orchestrator.brain.waf_detector", "orchestrator.social.social_engine",
    "orchestrator.privesc.privesc_engine", "orchestrator.modes.postmortem",
    "orchestrator.exfil.pipeline", "orchestrator.phishing.pipeline",
    "orchestrator.exfil.redcloud", "mcp-hub.core.registry", "mcp-hub.core.security",
    "agent.modules.cleanup", "agent.modules.executor", "agent.audit",
    "raphael.techniques.ad1_xor_sweep",
]
for q in queries:
    if q not in mods:
        print(f"--- {q}: NO-MODULE")
        continue
    imps = sorted(rev.get(q, []))
    r = q in seen
    print(f"--- {q}: reachable={r} importers={imps[:10]}")
    if r:
        print(f"    trace={trace(q)}")
