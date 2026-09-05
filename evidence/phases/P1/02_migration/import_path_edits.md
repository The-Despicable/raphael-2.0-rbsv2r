# P1 — Import path edits (5 files, 1 line each)

Per C3, the import paths of the 5 canonical `SandboxSession` importers were updated to point at the new `sandbox/` path. Each edit is a single line inside a `if TYPE_CHECKING:` block.

## Edits

| File | Line | Before | After |
|---|---|---|---|
| `src/orchestrator/postex/pipeline.py` | 5 | `from ..runtime.session_manager import SandboxSession` | `from ..sandbox.session_manager import SandboxSession` |
| `src/orchestrator/exploit/pipeline.py` | 5 | same | same |
| `src/orchestrator/scanners/pipeline.py` | 4 | same | same |
| `src/orchestrator/exfil/pipeline.py` | 5 | same | same |
| `src/orchestrator/phishing/pipeline.py` | 4 | same | same |

All 5 imports are inside `if TYPE_CHECKING:` blocks. They are type-only; no runtime import-side effect.

## Verification

```
$ grep -rEn "from \.\.runtime\.session_manager|from orchestrator\.runtime\.session_manager" src/ --include="*.py" | grep -v __pycache__
# (empty — zero stray references)
```

```
$ grep -rEn "from \.\.sandbox\.|from \.sandbox\." src/ --include="*.py" | grep -v __pycache__ | sort
src/orchestrator/exfil/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/exploit/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/phishing/pipeline.py:4:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/postex/pipeline.py:5:    from ..sandbox.session_manager import SandboxSession
src/orchestrator/scanners/pipeline.py:4:    from ..sandbox.session_manager import SandboxSession
```

All 5 imports now correctly go through `..sandbox.session_manager`.

## Floor preservation

```
$ PYTHONPATH=src python3 -m pytest tests/ --no-header -q
239 passed, 26 warnings, 3.72s
```

Same floor as P0 baseline. No regressions.
