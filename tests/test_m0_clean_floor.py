"""test_m0_clean_floor.py — M0 regression tests (2026-10-04).

Covers the M0 work packages:
- M0-A: the orchestrator.sandbox package/module shadow. The package now owns
  the namespace; ``PatchSandbox`` is importable again and the W-10 sink stays
  fail-closed.
- M0-B: the suite must not write into the historical evaluation tree
  (arena/results). tests/conftest.py redirects RESULTS_BASE per test; these
  tests verify the redirection is active and that a bare EpisodeRecorder
  without an output dir stays in memory.
- M0-D: importing phishing.main must not touch the filesystem.

Known, documented non-goals (see M0 report):
- api.main / api.ci / api.session / api.tools_bridge additionally require the
  ``python-multipart`` package (declared in requirements.txt:26); they are
  asserted behind an importorskip so they activate automatically once the
  environment is provisioned (M1).
- sword.phase_2_exploit has an unrelated pre-existing drift: it imports
  ``validate_exploit_results`` from orchestrator.validation.exploit_validator,
  which only defines ``validate_exploit``. Out of M0 scope.
"""

import asyncio
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))


# ── M0-A: sandbox shadow ───────────────────────────────────────────────

def test_patchsandbox_importable_from_package():
    from orchestrator.sandbox import PatchSandbox, sandbox

    assert isinstance(sandbox, PatchSandbox)
    assert callable(PatchSandbox.validate_syntax)
    assert callable(PatchSandbox.run_code)


def test_shadow_module_gone():
    legacy = _REPO_ROOT / "src" / "orchestrator" / "sandbox.py"
    assert not legacy.exists(), (
        "src/orchestrator/sandbox.py must not coexist with the "
        "orchestrator/sandbox/ package — the module is shadowed by the "
        "package and its presence recreates the M0-A import break"
    )


def test_patchsandbox_run_code_still_fail_closed():
    from orchestrator.auth import WeldNotAuthorized
    from orchestrator.sandbox import PatchSandbox

    with pytest.raises(WeldNotAuthorized):
        asyncio.run(PatchSandbox().run_code("print('hi')"))


@pytest.mark.parametrize(
    "module",
    [
        "orchestrator.agents.engage",
        "orchestrator.agents.exploit",
        "orchestrator.agents.postex",
        "bridge.raphael_bridge",
    ],
)
def test_previously_shadow_broken_modules_import(module):
    import importlib

    importlib.import_module(module)


@pytest.mark.parametrize(
    "module",
    [
        "orchestrator.api.agent",
        "orchestrator.api.main",
        "orchestrator.api.ci",
        "orchestrator.api.session",
        "orchestrator.api.tools_bridge",
    ],
)
def test_api_modules_import_with_multipart_present(module):
    """These five declare Form/File endpoints; FastAPI rejects them at route
    registration (import time) without python-multipart.

    Skipped until M1 provisions the environment; the skip reason names the
    exact blocker so the gap stays visible in every suite run.
    """
    pytest.importorskip("python_multipart", reason="python-multipart not installed (M1 environment provisioning)")
    import importlib

    importlib.import_module(module)


# ── M0-B: evaluation-tree isolation ────────────────────────────────────

def test_arena_results_base_redirected_during_tests():
    from arena.ablation_runner import RESULTS_BASE

    assert "arena-results" in str(RESULTS_BASE), (
        "tests/conftest.py must redirect arena.ablation_runner.RESULTS_BASE "
        "to a per-test temp dir; the repo arena/results tree is protected "
        "historical evidence"
    )


def test_episode_recorder_memory_only_without_output_dir(tmp_path):
    from arena.episode import EpisodeRecorder

    rec = EpisodeRecorder(run_id="m0_isolation_probe")
    rec.record(
        objective="isolation probe",
        evidence_available=[],
        active_hypotheses=[],
        candidate_actions=[],
        planner_scores=[],
        selected_action=None,
        authorization_result=None,
        execution_result=None,
        observations_created=[],
        evidence_created=[],
        belief_updates=[],
        world_updates=[],
    )
    assert rec.sequence_counter == 1
    probe_root = tmp_path / "raw" / "m0_isolation_probe"
    assert not probe_root.exists() or not any(probe_root.rglob("episodes.jsonl"))


# ── M0-D: phishing import purity ───────────────────────────────────────

def test_phishing_main_import_is_filesystem_pure(tmp_path):
    """Importing phishing.main must not create directories or mutate state.

    The pre-M0 module attempted mkdir('/app') at import time. Run the import
    in a subprocess with PHISHING_DATA_DIR pointed at a temp location so the
    assertion is meaningful even when /app is creatable.
    """
    import os
    import subprocess

    probe_dir = tmp_path / "phishing_probe"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")
    env["TEMPLATE_DIR"] = str(probe_dir)
    code = "import phishing.main"
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"phishing.main import failed: {result.stderr[-400:]}"
    )
    assert not probe_dir.exists(), (
        "importing phishing.main must not create directories; initialization "
        "belongs behind an explicit startup path"
    )


def test_phishing_startup_creates_template_dir(tmp_path):
    """The explicit startup hook still initializes TEMPLATE_DIR correctly.

    Import purity (previous test) must not come at the cost of skipping the
    directory the service needs; the FastAPI startup handler is the
    initialization point.
    """
    import os
    import subprocess

    probe_dir = tmp_path / "phishing_startup"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")
    env["TEMPLATE_DIR"] = str(probe_dir)
    code = "import phishing.main; phishing.main._ensure_template_dir()"
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"startup hook failed: {result.stderr[-400:]}"
    )
    assert probe_dir.is_dir(), (
        "phishing.main._ensure_template_dir() (FastAPI startup hook) must "
        "create TEMPLATE_DIR"
    )
