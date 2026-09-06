"""Seeded parity probe for WELD-SHELL (evidence only, not part of the floor).

Runs one deterministic canonical Runtime episode (max_iterations=3) and
prints the comparable decision/evidence sequence. Timing fields are
excluded because they vary run to run. Feed nothing back into Runtime.

R-W1a: every run block self-binds to its tree state — the probe prints
git rev-parse HEAD, branch, status, and rev-list count at startup, so a
transcript is never separated from the commit it describes.
"""
import random
import subprocess
import sys

SEED = 20260906
CANONICAL_BASE = "7272880f7"


def _git(*args):
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip()
    except Exception as e:
        return f"<git unavailable: {e}>"


def main():
    print(f"HEAD={_git('rev-parse', 'HEAD')}")
    print(f"BRANCH={_git('branch', '--show-current')}")
    print(f"STATUS={_git('status', '-sb')}")
    print(
        f"COUNT={_git('rev-list', '--count', f'{CANONICAL_BASE}..HEAD')}"
    )
    random.seed(SEED)
    try:
        import numpy as np
        np.random.seed(SEED)
    except ImportError:
        pass
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    rt = RaphaelRuntime()
    traces, termination = rt.run_episode(MissionContext(
        mission_id="shell-parity", name="shell-parity",
        objectives=["probe"],
    ), max_iterations=3)
    print(f"SEED={SEED}")
    print(f"TERMINATED={termination.terminated}")
    print(f"REASON={termination.reason}")
    print(f"ITERATIONS={termination.iterations}")
    for ti, trace in enumerate(traces):
        for ev in trace.entries:
            print(f"TRACE t{ti} stage={ev.get('stage')} "
                  f"success={ev.get('success')} error={ev.get('error')}")


if __name__ == "__main__":
    main()
