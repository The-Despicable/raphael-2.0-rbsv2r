"""tests/conftest.py — suite-wide test isolation guards.

M0-B (2026-10-04): AblationRunner defaults its output to the repo-relative
``arena/results`` tree, and its run IDs are deterministic by design
(C1/W0.8: same (config, template, seed, split) -> same run_id). Any test
that constructs a runner without an explicit ``output_dir`` therefore
overwrites historical evaluation evidence on every suite run — this is how
14 ``arena/results/raw/abl_*_dev`` directories were rewritten on 2026-10-04
(see evidence/arena_contamination_20261004/README.md).

This autouse fixture redirects every runner's results base to a per-test
temporary directory. Production behavior is unchanged: with the fixture not
active (real runs), ``arena.ablation_runner.RESULTS_BASE`` still resolves to
``arena/results`` and the deterministic run-ID semantics are preserved.

Writers covered:
- AblationRunner.save() / ensure_run_dir()        (module-global RESULTS_BASE)
- EpisodeRecorder / EventsRecorder                (output_dir from runner)
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_arena_results_base(tmp_path, monkeypatch):
    """Point arena.ablation_runner.RESULTS_BASE at a per-test temp dir."""
    monkeypatch.setattr(
        "arena.ablation_runner.RESULTS_BASE", tmp_path / "arena-results"
    )
