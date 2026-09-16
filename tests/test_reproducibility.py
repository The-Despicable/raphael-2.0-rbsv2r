"""Clean-checkout reproducibility (§14.11.5).

Proves the suite resolves the repository root from its own location and
uses only checkout-local resources, so a fresh clone at any filesystem
path collects and executes without developer host paths.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"


def test_repository_root_discovered_dynamically():
    """The root comes from this file's location, not a hardcoded host path."""
    assert Path(__file__).resolve().parent == (REPO_ROOT / "tests").resolve()
    assert (REPO_ROOT / "pyproject.toml").is_file()
    assert (REPO_ROOT / "src" / "orchestrator" / "runtime" / "loop.py").is_file()
    assert (REPO_ROOT / "tests" / Path(__file__).name).resolve() == Path(__file__).resolve()


def test_required_fixtures_resolve_from_checkout():
    """Fixtures used by the canonical tests live inside the checkout."""
    for rel in (
        "tests/p311_mvp_mission.json",
        "policies/bootstrap-v0.json",
    ):
        resolved = (REPO_ROOT / rel).resolve()
        assert resolved.is_file(), rel
        assert resolved.is_relative_to(REPO_ROOT.resolve()), rel


def test_subprocess_anchored_at_checkout_resolves_local_package():
    """Subprocess-based tests use the current checkout path."""
    env = dict(os.environ, PYTHONPATH=str(SRC_ROOT))
    proc = subprocess.run(
        [sys.executable, "-c",
         "import os, orchestrator; print(os.path.dirname(orchestrator.__file__))"],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    resolved = Path(proc.stdout.strip()).resolve()
    assert resolved == (SRC_ROOT / "orchestrator").resolve()
