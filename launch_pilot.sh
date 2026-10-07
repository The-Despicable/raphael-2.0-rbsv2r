#!/bin/bash
# Launch the RBS-v4 pilot from this repository.
# NOTE (M0, 2026-10-04): requires the M1 environment (repo-local .venv with
# requirements installed). Paths are now repo-relative; no external tree.
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
    echo "launch_pilot.sh: .venv not found — provision the environment first (milestone M1)." >&2
    exit 1
fi
.venv/bin/python -u scripts/run_rbs_v4_pilot.py 2>&1 | tee evaluations/campaign/rbs_v4_pilot.log
echo "Pilot exited with code $?"
