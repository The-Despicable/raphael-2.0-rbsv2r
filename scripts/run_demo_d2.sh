#!/usr/bin/env bash
# run_demo_d2.sh — one-command D2 bounded-episode demonstration (2026-10-05).
#
# Precondition: the lab (dvwa + kali-tools) is up on the loopback boundary
# (M2.1: base compose is loopback-safe by default).
#
# Usage: bash scripts/run_demo_d2.sh
# Exit 0 only if: lab healthy, both approved actions execute through the
# canonical governance path with verified artifacts and an objective-met
# termination, and every negative control (kill switch, wrong target) denies
# with zero process spawns. Evidence lands under evidence/demo/d2/<timestamp>/.
set -u
cd "$(dirname "$0")/.."

FAIL=0

echo "[d2] 1/3 lab health (scripts/smoke_lab.sh)"
if ! bash scripts/smoke_lab.sh; then
    echo "[d2] FAIL: lab is not healthy; refusing to run D2" >&2
    exit 1
fi

IMAGE=$(docker inspect dvwa --format '{{.Config.Image}}' 2>/dev/null || true)
STATE=$(docker inspect dvwa --format '{{.State.Running}}' 2>/dev/null || true)
NETS=$(docker inspect dvwa --format '{{range $k,$_ := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || true)
if [ "$STATE" != "true" ]; then echo "[d2] FAIL: dvwa not running" >&2; exit 1; fi
case "$IMAGE" in
    vulnerables/web-dvwa*) : ;;
    *) echo "[d2] FAIL: dvwa identity mismatch (image='$IMAGE')" >&2; exit 1 ;;
esac
case "$NETS" in
    *raphael-m1*) : ;;
    *) echo "[d2] FAIL: dvwa not on the raphael-m1 compose network" >&2; exit 1 ;;
esac
echo "[d2] 2/3 target identity verified: image=$IMAGE nets=$NETS"

echo "[d2] 3/3 bounded two-action episode + negative controls"
PYTHONPATH=src .venv/bin/python scripts/run_demo_d2.py || FAIL=1

if [ "$FAIL" = "0" ]; then
    echo "[d2] D2 demonstration PASSED (transcript under evidence/demo/d2/)"
else
    echo "[d2] D2 demonstration FAILED" >&2
fi
exit $FAIL
