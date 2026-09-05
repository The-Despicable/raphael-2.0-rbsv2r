# P1 — File moves (per C3, ADR-011)

Three sandbox infrastructure files were relocated from `src/orchestrator/runtime/` to `src/orchestrator/sandbox/`. Content is byte-identical; only the path changes.

## Move list

| Source | Destination | Lines | Content change |
|---|---|---|---|
| `src/orchestrator/runtime/caido_bootstrap.py` | `src/orchestrator/sandbox/caido_bootstrap.py` | 130 | none (byte-identical) |
| `src/orchestrator/runtime/docker_client.py` | `src/orchestrator/sandbox/docker_client.py` | 132 | none (byte-identical) |
| `src/orchestrator/runtime/session_manager.py` | `src/orchestrator/sandbox/session_manager.py` | 116 | none (byte-identical) |

## Mechanism

```
git mv src/orchestrator/runtime/caido_bootstrap.py src/orchestrator/sandbox/
git mv src/orchestrator/runtime/docker_client.py   src/orchestrator/sandbox/
git mv src/orchestrator/runtime/session_manager.py src/orchestrator/sandbox/
touch src/orchestrator/sandbox/__init__.py
git add src/orchestrator/sandbox/__init__.py
```

`git mv` preserves git history (the file's blob identity is unchanged; only the path is updated). All three files retain their original blob hashes in the working tree.

## Verification

```
$ git diff --stat --find-renames HEAD | grep -E "caido_bootstrap|docker_client|session_manager"
 .../{runtime => sandbox}/caido_bootstrap.py        |   0
 .../{runtime => sandbox}/docker_client.py          |   0
 .../{runtime => sandbox}/session_manager.py        |   0
```

The `| 0` confirms zero content delta — pure rename.

## Resulting state

- `src/orchestrator/runtime/` now contains only `__init__.py` (empty) — reserved for P2 Runtime creation.
- `src/orchestrator/sandbox/` now contains the 3 mechanisms + empty `__init__.py`.
- All canonical imports updated (see `import_path_edits.md`).
- No content lost.
