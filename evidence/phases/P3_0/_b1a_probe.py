"""B-1a evidence capture: closure instruments (read-only probe).

Runs the two arena-closure instruments against the LIVE runtime at the
ACTUAL submission HEAD and emits the machine-verifiable counts.

This script is an evidence-capture probe ONLY. It does not modify any
source or test under tests/ or src/. It is part of the G3-EN-5
evidence package.
"""
import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Instrument 1: Static transitive import-closure analysis (AST-based)
# ---------------------------------------------------------------------------

def static_closure():
    """BFS over orchestrator.* static imports starting from
    orchestrator.runtime. Returns (sorted_orch_modules, arena_in_closure)."""
    visited: set[str] = set()
    arena: list[str] = []

    def walk(module_path: str):
        if module_path in visited:
            return
        visited.add(module_path)
        if module_path.startswith("arena"):
            arena.append(module_path)
        if not module_path.startswith("orchestrator."):
            return
        # Try to locate the file (handles __init__.py).
        parts = module_path.split(".")
        for candidate in (
            SRC.joinpath(*parts).with_suffix(".py"),
            SRC.joinpath(*parts, "__init__.py"),
        ):
            if candidate.exists():
                break
        else:
            return
        try:
            tree = ast.parse(candidate.read_text())
        except SyntaxError:
            return
        package = module_path
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("orchestrator.") or alias.name.startswith("arena"):
                        walk(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = package.rsplit(".", node.level)[0] if node.level else package
                name = node.module or ""
                full = f"{base}.{name}" if node.level else name
                if full.startswith("orchestrator.") or full.startswith("arena"):
                    walk(full)

    walk("orchestrator.runtime")
    return sorted(visited), arena


# ---------------------------------------------------------------------------
# Instrument 2: Loaded modules after a complete Runtime episode
# ---------------------------------------------------------------------------

def loaded_after_episode():
    """After running one full Runtime episode, walk the closure and
    collect all orchestrator.* modules + any arena.* modules.
    Returns (sorted_runtime_closure, arena_in_closure)."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    rt.run_episode(MissionContext(
        mission_id="b1a-probe", name="b1a", objectives=["probe"],
    ))
    closure = sorted(
        m for m in sys.modules
        if m.startswith("orchestrator.") or m.startswith("arena") or m == "arena"
    )
    arena = [m for m in closure if m.startswith("arena")]
    return closure, arena


if __name__ == "__main__":
    print("=" * 70)
    print("B-1a INSTRUMENT 1: STATIC TRANSITIVE IMPORT-CLOSURE (AST)")
    print("=" * 70)
    s_static, arena_static = static_closure()
    print(f"ORCHESTRATOR_MODULES_IN_STATIC_CLOSURE={len(s_static)}")
    print(f"ARENA_MODULES_IN_STATIC_CLOSURE={len(arena_static)}")
    print("---STATIC_CLOSURE_MODULES---")
    for m in s_static:
        print(m)
    print()

    print("=" * 70)
    print("B-1a INSTRUMENT 2: LOADED-MODULE WALK AFTER FULL EPISODE")
    print("=" * 70)
    s_loaded, arena_loaded = loaded_after_episode()
    print(f"ORCHESTRATOR_AND_ARENA_MODULES_AFTER_EPISODE={len(s_loaded)}")
    print(f"ARENA_MODULES_AFTER_EPISODE={len(arena_loaded)}")
    print("---LOADED_RUNTIME_CLOSURE_MODULES---")
    for m in s_loaded:
        print(m)
    print()

    # Summary verdicts
    print("=" * 70)
    print("VERDICTS")
    print("=" * 70)
    print(f"STATIC_ARENA_FREE: {len(arena_static) == 0}")
    print(f"EPISODE_ARENA_FREE: {len(arena_loaded) == 0}")