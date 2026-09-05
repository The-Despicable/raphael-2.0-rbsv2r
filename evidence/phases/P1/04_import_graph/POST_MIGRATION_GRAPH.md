# P1 — Post-migration import graph (per C3)

This document is the post-move import graph for `sandbox/`. It is the actual current state, not a projection.

## External importers of `sandbox/`

```
$ grep -rEn "from \.\.sandbox\.|from \.sandbox\.|from orchestrator\.sandbox\." src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | sort
src/orchestrator/exfil/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/exploit/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/phishing/pipeline.py:4:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/postex/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/scanners/pipeline.py:4:    from ..sandbox.session_manager import SandboxSession
```

5 importers, all in `if TYPE_CHECKING:` blocks. None import any other `sandbox.*` submodule directly.

## Internal sandbox/ graph

```
$ for f in src/orchestrator/sandbox/*.py; do echo "--- $f ---"; grep -nE "^(import |from )" $f; done

--- src/orchestrator/sandbox/__init__.py ---
(empty)

--- src/orchestrator/sandbox/caido_bootstrap.py ---
import asyncio, json, logging
from typing import Optional

--- src/orchestrator/sandbox/docker_client.py ---
import json, logging, os, time, uuid
from typing import Optional

--- src/orchestrator/sandbox/session_manager.py ---
import logging, os, time
from typing import Optional
from .docker_client import DockerSandbox
from .caido_bootstrap import CaidoProxy
```

Internal graph:

```
session_manager.py ────→ docker_client.py (DockerSandbox)
       │
       └─────────────→ caido_bootstrap.py (CaidoProxy)
```

`caido_bootstrap.py` and `docker_client.py` are sibling leaves. No cross-dependency between them. No cycles.

## Dependency direction (per ADR-011)

```
runtime/  →  brain/  →  capabilities/  →  sandbox/
  ↑           ↑            ↑
no deps    authorizes    may use
```

Verified by:

```
$ grep -rEn "from orchestrator\.(runtime|brain|capabilities)" src/orchestrator/sandbox/ 2>/dev/null | grep -v __pycache__
# (empty — sandbox/ does NOT import from runtime/, brain/, or capabilities/)
```

The dependency direction is **correct**: `sandbox/` is a leaf package, mechanisms only, with no upstream references.

## Cross-cutting state

`runtime/` package state at end of P1 (per C1, per C4):

```
$ ls src/orchestrator/runtime/
__init__.py     (empty, 0 bytes — no re-exports, no shims)
__pycache__/    (build artifact, gitignored)
```

Per C1, no `RaphaelRuntime` is created in P1. The package is reserved for P2.
Per C4, no re-export shims — `__init__.py` is empty (0 bytes).

## `runtime/` does not have a Python-level dependency on `sandbox/`

```
$ grep -rEn "from sandbox|from orchestrator\.sandbox|import sandbox" src/orchestrator/runtime/ 2>/dev/null | grep -v __pycache__
# (empty)
```

`runtime/` is empty in P1, so this is vacuously true. But the architectural intent (per ADR-011) is that `runtime/` composes `capabilities/` and `brain/`, not `sandbox/`. The P2 Runtime, when created, must NOT import from `sandbox/` directly.

## `brain/` and `capabilities/` do not import from `sandbox/`

```
$ grep -rEn "from \.sandbox|from \.\.sandbox|from orchestrator\.sandbox" src/orchestrator/brain/ src/orchestrator/capabilities/ 2>/dev/null | grep -v __pycache__
# (empty)
```

Confirmed. `brain/` and `capabilities/` reach `sandbox/` only through the 5 pipeline files (which are themselves only reachable from broken-symlink services per the P0 inventory).
