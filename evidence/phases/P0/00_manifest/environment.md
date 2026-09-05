## P0 — Environment Manifest

### System

- `PYTHON=3.14.4 (main, Jun 18 2026, 14:25:02) [GCC 15.2.0]`
- `OS=Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.43`
- `ARCH=x86_64`
- `CWD=/home/yaser/external-audits/raphael-2`
- Docker available: `Docker version 29.7.2, build a7dcaa6`

### Python packages installed for prior-session probes (P0-R2 legal)

The following were installed in prior sessions via `pip install --break-system-packages` to enable runtime probes during the prior audit. They do not change application behavior; they make existing test paths runnable.

- `httpx 0.28.1` — required by `bridge.raphael_bridge`, `orchestrator.student.*`
- `aiohttp 3.14.3` — required by `orchestrator.modes.*`, `orchestrator.providers`
- `paramiko 5.0.0` — required by `orchestrator.capabilities.interactive_shell.ssh_shell`
- `pytest-asyncio 1.4.0` — required by tests using `@pytest.mark.asyncio`
- `fastapi 0.141.1` + `uvicorn 0.52.4` — required by `orchestrator.api.main` (FastAPI service)
- `pydantic`, `starlette`, `python-multipart` — transitive deps for FastAPI form handling

No package installed changes any application code, test, or fixture.

### Lockfile / constraint

- `pyproject.toml` declares `requires-python = ">=3.11,<3.13"`.
- System Python is **3.14.4** — **outside the declared range**.
- The 239-test suite runs green on 3.14.4 (verified in §5.4 / `01_test_floor/baseline.txt`).
- This is a **documented risk**, not a P0 fix. Production deployment should resolve the version mismatch; P0 does not address it.

### Environment variables (redacted; no secrets in evidence)

- `RAPHAEL_RUNTIME_V2=1` — optional, opts into the arena runtime-via-Runtime path. At canonical, this is a **no-op** (the arena has no `_run_raphael_via_runtime`).
- `RAPHAEL_USE_RUNTIME=1` — optional, opts into CLI → Runtime path. At canonical, this is a **no-op** (no Runtime exists).
- `RAPHAEL_TARGET=<target_ip>` — optional, used by the CLI's Head-1 loop. Not required for the 239-test baseline.
- `KALI_TOOLS_URL=http://kali-tools:3800` — default for `kali_tools_client`. Not used by the 239-test baseline (the only consumer is `bridge.kali_run` which is dead/broken code).
- `RAPHAEL_DB_PATH` — optional, default `data/raphael.db`. Not required for the 239-test baseline.
- No API keys, tokens, or credentials were present in any environment variable at P0 time. Confirmed by listing all `os.environ` items relevant to the test run (none of the test code reads secrets at fixture-construction time).

### Symlinks relevant to test execution

- `/home/yaser/raphael-2.0-rbsv2r -> /home/yaser/external-audits/raphael-2` — **PRESENT** (created in prior session; required by 9 arena test files that read source text by absolute path).
- `/home/yaser/raphael-2.0 -> (absent)` — **ABSENT**. 4 broken symlinks point here: `cai_service`, `cloak_service`, `mcp_hub`, `mhddos_service`. These are not exercised by the 239-test baseline.

### Test invocation (canonical baseline)

```
PYTHONPATH=src python3 -m pytest tests/ --no-header -q
```

Run from `/home/yaser/external-audits/raphael-2`. The symlink above makes the same command work from `/home/yaser/raphael-2.0-rbsv2r/`.

### Reproducibility statement

Another agent on the same Python 3.14.4 + WSL2 host, after:
1. Cloning `https://github.com/The-Despicable/raphael-2.0-rbsv2r` at `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`,
2. Installing the Python packages listed above,
3. Creating the `/home/yaser/raphael-2.0-rbsv2r -> <repo-root>` symlink,

should obtain the same 239-test baseline (modulo unrelated test-warning noise from `test_cli_smoke.py`).

**Note:** the prior sessions' test runs left 14 `episodes.jsonl` files modified inside `arena/results/raw/`. These are test artifacts regenerated on every `pytest` invocation. They are not part of the application source and do not affect the baseline.
