# RC-3: Real pre/post import graph (AST-derived from the repository)

Generation method:
- `pre` = imports extracted by `ast` from the file content at `HEAD` (commit `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`).
- `post` = imports extracted by `ast` from the working tree (post-P1 edits, uncommitted).
- For files that did not exist at HEAD (the 4 ADDED: `src/orchestrator/sandbox/__init__.py` + 3 renames whose new path is `sandbox/*` and old path was `runtime/*`), the pre slot is marked `<NEW in working tree>` or `<renamed from runtime/*>`.

Per-file inventories are in:
- `evidence/g1_corrections/import_graph_pre.txt` (HEAD, 436 files)
- `evidence/g1_corrections/import_graph_post.txt` (working tree, 440 files)

## Aggregate diff

- POST = 440 Python files under `src/`
- PRE  = 436 Python files under `src/` (at HEAD)
- ADDED  = 4 (working-tree new files not present at HEAD)
- CHANGED = 5 (existing files with different import set)
- REMOVED = 0

## The 4 ADDED files

1. `src/orchestrator/sandbox/__init__.py` — empty (per C4, no re-export shim). New package boundary.
2. `src/orchestrator/sandbox/caido_bootstrap.py` — renamed from `src/orchestrator/runtime/caido_bootstrap.py`. Byte-identical content; only path changed.
3. `src/orchestrator/sandbox/docker_client.py` — renamed from `src/orchestrator/runtime/docker_client.py`. Byte-identical.
4. `src/orchestrator/sandbox/session_manager.py` — renamed from `src/orchestrator/runtime/session_manager.py`. Byte-identical.

## The 5 CHANGED files (import-set delta)

All 5 are the `SandboxSession` importer pipelines. The change is the single-line import path update recorded in `evidence/phases/P1/02_migration/import_path_edits.md`.

| File | Pre (HEAD) import | Post (working tree) import |
|---|---|---|
| `src/orchestrator/exfil/pipeline.py` | `from ..runtime.session_manager import SandboxSession` | `from ..sandbox.session_manager import SandboxSession` |
| `src/orchestrator/exploit/pipeline.py` | same | same |
| `src/orchestrator/phishing/pipeline.py` | same | same |
| `src/orchestrator/postex/pipeline.py` | same | same |
| `src/orchestrator/scanners/pipeline.py` | same | same |

The 5 imports are inside `if TYPE_CHECKING:` blocks; they are type-only and have no runtime side effect. This is consistent with the pre-migration import graph in `evidence/phases/P1_0/collision_inventory.md` §2 and the post-migration import graph in `evidence/phases/P1/04_import_graph/POST_MIGRATION_GRAPH.md`.

## Dependency direction (per ADR-011, verified at P1 end-state)

```
runtime/  →  brain/  →  capabilities/  →  sandbox/
  ↑           ↑            ↑
no deps    authorizes    may use
```

CHECK 1 (sandbox/ has no upstream imports): PASS (`grep -rEn "from orchestrator\.(runtime|brain|capabilities)" src/orchestrator/sandbox/` returns empty).
CHECK 2 (runtime/ has no imports of other layers): PASS vacuously (runtime/ is empty in P1 per C1).
CHECK 3 (brain/ does not import from sandbox/): PASS.
CHECK 4 (capabilities/ does not import from sandbox/): PASS.
CHECK 5 (other sub-packages reach sandbox/ only via the 5 pipeline importers): PASS.

## Net effect of P1 on the import graph

- One new leaf package (`orchestrator.sandbox/`) with no upstream references.
- One package (`orchestrator.runtime/`) is now empty (`__init__.py` only, 0 bytes) — reserved for P2 Runtime creation. No shims, no re-exports (per C4).
- 5 single-line TYPE_CHECKING-block path updates; no runtime import-graph change.

## Evidence files

- `evidence/g1_corrections/import_graph_pre.txt` (raw AST output, HEAD state)
- `evidence/g1_corrections/import_graph_post.txt` (raw AST output, working tree)
- `evidence/g1_corrections/import_graph_diff.txt` (the 2-line unified diff of changed import lines)
- `evidence/phases/P1/04_import_graph/POST_MIGRATION_GRAPH.md` (canonical P1 import graph)
- `evidence/phases/P1/04_import_graph/dependency_direction_check.txt` (canonical direction check)
- `evidence/phases/P1/02_migration/import_path_edits.md` (the 5 import edits)
- `docs/adr/ADR-011-sandbox-layer-mechanisms-not-authorization.md` (architectural decision)
