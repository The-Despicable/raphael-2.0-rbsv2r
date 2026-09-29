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
libraries, SMTP clients, boto3/botocore cloud construction, asyncio socket
streams, Redis client construction/operations (usage-gated), file removal,
filesystem mutation calls (os.rename/chmod, shutil.copy/move, pathlib
write/unlink/rename/rmdir/chmod on proven receivers), and ``open(...)``
write modes. Dotted import aliases are resolved to canonical form before
matching (``import redis.asyncio as redis``); file-global simplification,
documented below.
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
# NOTE (001R5): smtplib/boto3/botocore are deliberately NOT roots: a bare import
# without use must not flag (negative control). Their network effects are caught
# at construction/call sites below. NOTE (001R6): same for redis/redis.asyncio.
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
    # 001R4 (AM-13.1 "all other file access ... Broker-mediated exactly like process
    # or network access"; INV-1 "file primitives"): filesystem-mutation calls in the
    # same category as the entries above.
    "os.rename",
    "os.chmod",
    "shutil.copy",
    "shutil.copy2",
    "shutil.copytree",
    "shutil.move",
    # 001R4 (INV-1 "network primitives"): SMTP constructors.
    "smtplib.SMTP",
    "smtplib.SMTP_SSL",
    # 001R5 (INV-1 "network primitives", governed cloud/socket APIs used in-tree):
    "boto3.client",
    "boto3.resource",
    "boto3.Session",
    "asyncio.open_connection",
    "asyncio.start_server",
    # 001R6 (INV-1 "network primitives", governed Redis API used in-tree by
    # raphael/eventbus/core.py): construction entry points. Bare `import redis`
    # never flags alone (usage-gated, same doctrine as boto3/smtplib).
    "redis.from_url",
    "redis.Redis",
    "redis.asyncio.from_url",
    "redis.asyncio.Redis",
}


# 001R5: pathlib-style filesystem-mutation methods. These NEVER match by bare
# method name: the receiver must be PROVEN a pathlib.Path by AST structure (see
# _PathProven below), otherwise arbitrary `.rename()`/`.unlink()` calls on
# non-file objects would false-positive. `write_text`/`write_bytes` are
# pathlib-unique names but get the same proof requirement (negative control:
# `arbitrary_object.write_text()` must stay clean).
PATH_WRITE_METHODS = {
    "write_text",
    "write_bytes",
}

# 001R5: common-name filesystem methods with the same proof requirement.
# `rmdir` is included as the exact equivalent of the already-governed `os.rmdir`;
# `mkdir` is NOT included (no governed equivalent — residual boundary, CENSUS §G).
# `chmod` method form mirrors governed `os.chmod`.
PATH_FS_METHODS = {
    "unlink",
    "rename",
    "rmdir",
    "chmod",
}

# 001R5: pure path operations — a Call to one of these on a proven Path yields a
# Path (used for transitive binding, e.g. `self.repo_path / x`, `p.with_suffix()`).
PATH_PURE_OPS = {
    "resolve",
    "absolute",
    "expanduser",
    "with_name",
    "with_suffix",
    "joinpath",
}

# 001R5: iteration sources yielding Path items (for-target binding only).
PATH_ITER_OPS = {
    "glob",
    "rglob",
    "iterdir",
}

# 001R5: network-construction names imported from client libraries. A bare
# `SMTP(...)` call counts only when the name was imported from smtplib/boto3/
# botocore in the same file (usage-gated: bare imports never flag alone).
# 001R6: subsumed by import-alias canonicalization below (from-imports populate
# `aliases`, so bare uses match canonically and emit exactly one finding).
# Kept as documentation of the usage-gated root set.
NETWORK_NAMED_IMPORT_ROOTS = {
    "smtplib",
    "boto3",
    "botocore",
}

# 001R6: usage-gated from-import roots. A from-import finding is NOT emitted
# for these (the bare import must stay clean); the usage site flags exactly
# once via canonical matching. This collapses the 001R5 double-report
# (`from boto3 import client` used to emit import-site + use-site findings).
USAGE_GATED_ROOTS = NETWORK_NAMED_IMPORT_ROOTS | {"redis"}

# 001R5: session-factory calls whose results offer `.client()`/`.resource()`.
BOTO_SESSION_CTORS = {
    "boto3.Session",
}

# 001R6: Redis construction entry points whose results offer the REDIS_OPS
# network operations below (mirrors BOTO_SESSION_CTORS). Canonical dotted
# forms (import aliases resolved before matching, so `import redis.asyncio
# as redis` + `redis.from_url(...)` matches `redis.asyncio.from_url`).
REDIS_CTORS = {
    "redis.from_url",
    "redis.Redis",
    "redis.asyncio.from_url",
    "redis.asyncio.Redis",
}

# 001R6: Redis client network operations. These NEVER match by bare method
# name: the receiver must be PROVEN Redis-derived (bound to a REDIS_CTORS
# call, a same-class Redis attribute, or a single-hop property returning
# one). Generic data-op names (get/set/delete/...) are included because on
# a PROVEN Redis receiver they are genuinely network round-trips; on any
# other receiver they stay clean (negative control: `cache.get()` with an
# unproven receiver must not flag).
REDIS_OPS = {
    "ping", "echo", "info", "dbsize", "close", "execute", "pipeline",
    "scan", "scan_iter", "keys", "type",
    "get", "set", "delete", "exists", "expire", "persist", "ttl",
    "incr", "decr", "hget", "hset", "hdel", "hgetall",
    "lpush", "rpush", "lpop", "rpop", "sadd", "srem", "smembers",
    "zadd", "zrem", "publish", "subscribe",
    "xadd", "xread", "xrange", "xrevrange", "xreadgroup", "xack",
    "xdel", "xtrim", "xinfo_stream", "xinfo_groups", "xinfo_consumers",
    "xpending", "xpending_range", "xclaim", "xautoclaim",
    "xgroup_create", "xgroup_setid", "xgroup_destroy",
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


def _is_path_ctor(func: ast.AST, aliases=None) -> bool:
    """True for `Path(...)`, `pathlib.Path(...)`, `Path.home()`, `Path.cwd()`.

    001R6: `aliases` resolves `from pathlib import Path as P` (Name `P` with
    aliases[P] == "pathlib.Path") and `import pathlib as pl` (`pl.Path`).
    """
    aliases = aliases or {}
    if isinstance(func, ast.Name):
        if func.id == "Path":
            return True
        if aliases.get(func.id) == "pathlib.Path":
            return True
        return False
    if isinstance(func, ast.Attribute) and func.attr == "Path":
        return True
    if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
            and func.attr in ("home", "cwd")):
        base = func.value.id
        if base in ("Path", "pathlib") or aliases.get(base) == "pathlib":
            return True
    return False


def _ann_has_path(ann) -> bool:
    """True when an annotation subtree names `Path` (covers `Path`, `pathlib.Path`,
    `str | Path`, `Optional[Path]`). Rationale: a value flowing through such an
    annotation that reaches a mutation call would have raised TypeError earlier
    if it were not a Path."""
    if ann is None:
        return False
    for node in ast.walk(ann):
        if isinstance(node, ast.Name) and node.id == "Path":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "Path":
            return True
    return False


def _proven_path(node: ast.AST, bound: set, selfbound: set, clsname,
                aliases=None) -> bool:
    """Structural proof that an expression evaluates to a pathlib.Path.

    Bounded and documented: simple assignments, `self.` attributes assigned from
    proven expressions in the same class, annotated args, module constants.
    Monotonic (a name proven once stays proven; shadowing by a non-Path value is
    a documented limitation), no closures beyond that, no cross-file inference.
    001R6: `aliases` threads import-alias resolution into constructor checks.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if _is_path_ctor(func, aliases):
            return True
        if isinstance(func, ast.Attribute) and func.attr in PATH_PURE_OPS:
            return _proven_path(func.value, bound, selfbound, clsname, aliases)
        return False
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _proven_path(node.left, bound, selfbound, clsname, aliases) or \
            _proven_path(node.right, bound, selfbound, clsname, aliases)
    if isinstance(node, ast.IfExp):
        return _proven_path(node.body, bound, selfbound, clsname, aliases) or \
            _proven_path(node.orelse, bound, selfbound, clsname, aliases)
    if isinstance(node, ast.Name):
        return node.id in bound
    if isinstance(node, ast.Attribute):
        value = node.value
        if isinstance(value, ast.Name) and value.id == "self" and clsname is not None:
            return (clsname, node.attr) in selfbound
        return False
    return False


def _canon_dotted(dotted: str, aliases: dict) -> str:
    """Resolve a dotted call name through import aliases to canonical form.

    001R6: `import redis.asyncio as redis` + `redis.from_url` →
    `redis.asyncio.from_url`; `import boto3 as b` + `b.client` → `boto3.client`;
    `from boto3 import client` + `client` → `boto3.client`. File-global
    simplification (function-level shadowing is not modelled): verified
    census-neutral in-tree (all in-tree import aliases govern roots whose
    imports already flag; only the new redis family changes verdicts).
    """
    if not dotted:
        return dotted
    head, _, rest = dotted.partition(".")
    if head in aliases:
        return aliases[head] + ("." + rest if rest else "")
    return dotted


def _ctor_call_dotted(node: ast.AST, aliases: dict):
    """Canonical dotted name of a Call's func, unwrapping `await`."""
    while isinstance(node, ast.Await):
        node = node.value
    if not isinstance(node, ast.Call):
        return None
    return _canon_dotted(_dotted_name(node.func), aliases)


def _proven_redis(node: ast.AST, rbound: set, rself: set, clsname,
                  rprops=None, aliases=None) -> bool:
    """Structural proof that an expression evaluates to a Redis client.

    001R6: mirrors _proven_path's bounded philosophy for REDIS_CTORS results:
    simple assignments (incl. `await`ed construction), `self.` attributes
    assigned from proven exprs, single-hop properties returning a proven
    receiver (`return self._redis`), `.pipeline()` chaining on proven
    receivers, BoolOp/IfExp unwrapping. Monotonic, same documented limits.
    `fakeredis` and friends are never constructors, so fakes stay clean.
    """
    rprops = rprops or set()
    aliases = aliases or {}
    while isinstance(node, ast.Await):
        node = node.value
    if isinstance(node, ast.Call):
        func = node.func
        if _canon_dotted(_dotted_name(func), aliases) in REDIS_CTORS:
            return True
        if isinstance(func, ast.Attribute) and func.attr == "pipeline":
            return _proven_redis(func.value, rbound, rself, clsname, rprops,
                                 aliases)
        return False
    if isinstance(node, ast.BoolOp):
        return any(_proven_redis(v, rbound, rself, clsname, rprops, aliases)
                   for v in node.values)
    if isinstance(node, ast.IfExp):
        return _proven_redis(node.body, rbound, rself, clsname, rprops,
                             aliases) or \
            _proven_redis(node.orelse, rbound, rself, clsname, rprops, aliases)
    if isinstance(node, ast.Name):
        return node.id in rbound
    if isinstance(node, ast.Attribute):
        value = node.value
        if isinstance(value, ast.Name) and value.id == "self" and clsname is not None:
            return (clsname, node.attr) in rself or (clsname, node.attr) in rprops
        return False
    return False


def _collect_proven(tree: ast.AST):
    """Return (module_bound, self_bound, func_scopes, module_sessions,
    module_redis, redis_self).

    module_bound: Names bound to proven Path exprs at module level.
    self_bound: (class, attr) pairs assigned from proven exprs in that class.
    func_scopes: (class|None, func) -> {"args": set, "bound": dict,
      "sessions": set, "redis": dict}.
    `sessions` holds Names bound to boto3.Session(...) results (for chained
    `.client()`/`.resource()` network construction). `redis` holds Names bound
    to REDIS_CTORS results (for REDIS_OPS receiver proof). module_redis and
    redis_self/redis_props are the module/class-level counterparts.
    001R6: also returns import `aliases` (appended last) mapping imported
    aliases to canonical dotted roots (`import redis.asyncio as redis`,
    `from pathlib import Path as P`, `from boto3 import client`).
    """
    module_bound: dict = {}
    self_bound: set = set()
    func_scopes: dict = {}
    module_sessions: dict = {}
    module_redis: dict = {}
    redis_self: set = set()
    redis_props: set = set()

    aliases: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                aliases[alias.asname or alias.name] = \
                    f"{base}.{alias.name}" if base else alias.name

    def _iter_scope_nodes(body):
        """Yield Assign/AnnAssign/For nodes in a function body, descending into
        plain blocks (if/try/with/for/while) but NOT into nested defs/classes."""
        stack = list(body)
        while stack:
            node = stack.pop(0)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Lambda)):
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.For,
                                 ast.comprehension)):
                yield node
            for child in ast.iter_child_nodes(node):
                stack.append(child)

    def _scope_assigns(body, bound, clsname, args, sessions, rbound=None):
        if rbound is None:
            rbound = {}

        def _bind_iter_target(target, source):
            if isinstance(target, ast.Name) and isinstance(source, ast.Call) \
                    and isinstance(source.func, ast.Attribute) \
                    and source.func.attr in PATH_ITER_OPS \
                    and _proven_path(source.func.value, bound, self_bound,
                                     clsname, aliases):
                bound[target.id] = True

        for _ in range(3):  # fixpoint for alias chains (a=Path(); b=a/...)
            for node in _iter_scope_nodes(body):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    for target in targets:
                        if isinstance(target, ast.Name) and value is not None:
                            if _proven_path(value, bound, self_bound, clsname,
                                            aliases):
                                bound[target.id] = True
                            if _proven_redis(value, rbound, redis_self, clsname,
                                             redis_props, aliases):
                                rbound[target.id] = True
                            if isinstance(value, ast.Call):
                                dotted = _dotted_name(value.func)
                                if _canon_dotted(dotted, aliases) in BOTO_SESSION_CTORS:
                                    sessions[target.id] = True
                elif isinstance(node, ast.For):
                    _bind_iter_target(node.target, node.iter)
                elif isinstance(node, ast.comprehension):
                    # 001R6: comprehension targets bind exactly like For targets
                    # (`[f.write_text() for f in Path().glob()]` — CLOSED FN).
                    _bind_iter_target(node.target, node.iter)

    def _func_args(item):
        found = set()
        for arg in list(item.args.args) + list(item.args.kwonlyargs):
            if _ann_has_path(arg.annotation):
                found.add(arg.arg)
        return found

    # 001R6: module-level fixpoint — module constants, `for f in Path().glob()`
    # targets, and comprehension targets all bind identically to the
    # function-level model (closes the module-level-glob and comprehension FNs).
    _scope_assigns(tree.body, module_bound, None, [], module_sessions,
                   module_redis)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = _func_args(node)
            bound = dict(module_bound)
            sessions: dict = {}
            rbound = dict(module_redis)
            bound.update({a: True for a in args})
            _scope_assigns(node.body, bound, None, args, sessions, rbound)
            func_scopes[(None, node.name)] = {"args": args, "bound": bound,
                                              "sessions": sessions,
                                              "redis": rbound}
        elif isinstance(node, ast.ClassDef):
            clsname = node.name
            for _ in range(2):  # self-attrs may be defined in any method order
                for item in node.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for sub in ast.walk(item):
                        if not isinstance(sub, (ast.Assign, ast.AnnAssign)):
                            continue
                        targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                        for target in targets:
                            if isinstance(target, ast.Attribute) \
                                    and isinstance(target.value, ast.Name) \
                                    and target.value.id == "self" and sub.value is not None:
                                probe_bound = dict(module_bound)
                                probe_redis = dict(module_redis)
                                if _proven_path(sub.value, probe_bound, self_bound,
                                                clsname, aliases):
                                    self_bound.add((clsname, target.attr))
                                if _proven_redis(sub.value, probe_redis, redis_self,
                                                clsname, redis_props, aliases):
                                    redis_self.add((clsname, target.attr))
            for _ in range(2):  # properties may chain via one another
                for item in node.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    # 001R6: single-hop Redis properties (`def redis(self):
                    # `return self._redis`) let `self.redis.xadd(...)` resolve.
                    for sub in ast.walk(item):
                        if isinstance(sub, ast.Return) and sub.value is not None:
                            if _proven_redis(sub.value, dict(module_redis),
                                             redis_self, clsname, redis_props,
                                             aliases):
                                redis_props.add((clsname, item.name))
            redis_self.update(redis_props)
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                args = _func_args(item)
                bound = dict(module_bound)
                bound.update({a: True for a in args})
                sessions = {}
                rbound = dict(module_redis)
                _scope_assigns(item.body, bound, clsname, args, sessions, rbound)
                func_scopes[(clsname, item.name)] = {"args": args, "bound": bound,
                                                     "sessions": sessions,
                                                     "redis": rbound}
    return (module_bound, self_bound, func_scopes, module_sessions,
            module_redis, redis_self, aliases)


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

    # 001R6: import aliases for canonical matching (`import redis.asyncio
    # as redis`, `from pathlib import Path as P`, `from boto3 import client`).
    # From-imports populate aliases, so bare uses match canonically and emit
    # exactly one finding at the use site (de-duped; 001R5 double-report gone).
    _module_bound, _self_bound_set, _func_scopes, _module_sessions, \
        _module_redis, _redis_self, _aliases = _collect_proven(tree)
    _parents = {}
    for _node in ast.walk(tree):
        for _child in ast.iter_child_nodes(_node):
            _parents[_child] = _node

    def _scope_for(node):
        clsname, chain = None, []
        cursor = node
        while cursor in _parents:
            cursor = _parents[cursor]
            if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chain.append(cursor.name)
            if isinstance(cursor, ast.ClassDef) and clsname is None:
                clsname = cursor.name
        for fname in chain:
            info = _func_scopes.get((clsname, fname))
            if info is not None:
                return clsname, info["bound"], info["sessions"], info["redis"]
        return None, _module_bound, _module_sessions, _module_redis

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
            base_root = base.split(".")[0]
            for alias in node.names:
                full = f"{base}.{alias.name}" if base else alias.name
                # 001R6: usage-gated roots (smtplib/boto3/botocore/redis) never
                # emit an import-site finding for construction names — the use
                # site flags exactly once via canonical matching (de-dup).
                if base_root in USAGE_GATED_ROOTS and (
                        full in FORBIDDEN_CALLS or full in REDIS_CTORS):
                    continue
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
            # 001R6: canonical form (import aliases resolved). Literal source
            # spelling wins when it matches, else the canonical form.
            canon = _canon_dotted(dotted, _aliases)
            prim = dotted if dotted in FORBIDDEN_CALLS or dotted in REDIS_CTORS \
                else canon
            if prim in FORBIDDEN_CALLS or prim in REDIS_CTORS:
                violations.append({
                    "file": filename,
                    "line": node.lineno,
                    "primitive": prim,
                    "type": "call",
                    "module": prim.split(".")[0],
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
            else:
                func = node.func
                if isinstance(func, ast.Attribute):
                    attr = func.attr
                    # 001R5: botocore dotted network construction.
                    if dotted.startswith("botocore.") or \
                            canon.startswith("botocore."):
                        violations.append({
                            "file": filename,
                            "line": node.lineno,
                            "primitive": dotted,
                            "type": "call",
                            "module": "botocore",
                        })
                    elif attr in PATH_WRITE_METHODS or attr in PATH_FS_METHODS:
                        # 001R5: method-form filesystem mutation ONLY on proven
                        # Path receivers (no import-gate fallback, no bare-name
                        # matching). Dotted stdlib forms (os.rename, ...) are
                        # already caught above, so no double-reporting.
                        _cls, _bound, _sessions, _rbound = _scope_for(node)
                        if _proven_path(func.value, _bound, _self_bound_set,
                                        _cls, _aliases):
                            violations.append({
                                "file": filename,
                                "line": node.lineno,
                                "primitive": dotted or f"Path.{attr}",
                                "type": "call",
                                "module": dotted.split(".")[0] if dotted else "pathlib",
                            })
                    elif attr in REDIS_OPS:
                        # 001R6: Redis client operations ONLY on proven
                        # Redis-derived receivers (construction-bound names,
                        # same-class Redis attrs, single-hop properties).
                        # `fakeredis` receivers are never proven (not a ctor),
                        # and arbitrary `.ping()`/`.get()` receivers stay clean.
                        _cls, _bound, _sessions, _rbound = _scope_for(node)
                        if _proven_redis(func.value, _rbound, _redis_self,
                                         _cls, None, _aliases):
                            violations.append({
                                "file": filename,
                                "line": node.lineno,
                                "primitive": f"redis.{attr}",
                                "type": "call",
                                "module": "redis",
                            })
                    elif attr in ("client", "resource"):
                        # 001R5: chained boto3 session construction
                        # (session = boto3.Session(...); session.client("s3")).
                        # 001R6: also inline `boto3.Session().client("s3")`.
                        recv = func.value
                        _cls, _bound, _sessions, _rbound = _scope_for(node)
                        chained = isinstance(recv, ast.Name) and \
                            recv.id in _sessions
                        if not chained and isinstance(recv, ast.Call):
                            chained = _canon_dotted(
                                _dotted_name(recv.func),
                                _aliases) in BOTO_SESSION_CTORS
                        if chained:
                            violations.append({
                                "file": filename,
                                "line": node.lineno,
                                "primitive": f"boto3.Session.{attr}",
                                "type": "call",
                                "module": "boto3",
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
