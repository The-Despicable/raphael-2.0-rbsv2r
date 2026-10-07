#!/usr/bin/env bash
# run_demo_d1.sh — one-command M2/D1 demonstration (2026-10-04).
#
# Precondition: the lab (dvwa + kali-tools) is up on the loopback boundary
# (M2.1: the base compose configuration is loopback-safe by default).
# This script NEVER contacts an external target, never issues an LLM-provider
# request, and never touches the offensive execution path beyond the single
# bounded D1 probe.
#
# Usage:  bash scripts/run_demo_d1.sh
# Exit 0 only if: lab healthy, positive action authorized+executed+receipted
# with a verified artifact digest, and every denial control (restrictive
# policy, kill switch, wrong target) denies with zero process spawns.
set -u
cd "$(dirname "$0")/.."

FAIL=0

# 1. lab health via the M1 smoke test (includes loopback-boundary check)
echo "[d1] 1/4 lab health (scripts/smoke_lab.sh)"
if ! bash scripts/smoke_lab.sh; then
    echo "[d1] FAIL: lab is not healthy; refusing to run D1 against an unknown target" >&2
    exit 1
fi

# 2. target identity must resolve to the intended DVWA service before anything runs
echo "[d1] 2/4 target identity verification (dvwa on the raphael-m1 compose network)"
IMAGE=$(docker inspect dvwa --format '{{.Config.Image}}' 2>/dev/null || true)
STATE=$(docker inspect dvwa --format '{{.State.Running}}' 2>/dev/null || true)
NETS=$(docker inspect dvwa --format '{{range $k,$_ := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true)
if [ "$STATE" != "true" ]; then
    echo "[d1] FAIL: dvwa container is not running" >&2
    exit 1
fi
case "$IMAGE" in
    vulnerables/web-dvwa*) : ;;
    *) echo "[d1] FAIL: dvwa identity mismatch (image='$IMAGE')" >&2; exit 1 ;;
esac
case "$NETS" in
    *raphael-m1*) : ;;
    *) echo "[d1] FAIL: dvwa is not on the raphael-m1 compose network (nets='$NETS')" >&2; exit 1 ;;
esac
echo "[d1]     dvwa: image=$IMAGE state=running nets=$NETS"

# 3. the governed demonstration (positive + restrictive + kill switch + wrong target)
echo "[d1] 3/4 governed demonstration (canonical Runtime -> Broker -> PEP -> exec)"
PYTHONPATH=src .venv/bin/python scripts/run_demo_d1.py || FAIL=1

# 4. verdict
if [ "$FAIL" = "0" ]; then
    echo "[d1] 4/4 D1 demonstration PASSED (transcript under evidence/demo/d1/)"
else
    echo "[d1] 4/4 D1 demonstration FAILED" >&2
fi
exit $FAIL
