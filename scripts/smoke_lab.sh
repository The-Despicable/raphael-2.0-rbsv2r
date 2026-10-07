#!/usr/bin/env bash
# smoke_lab.sh — M1 local-lab smoke test (2026-10-04).
#
# Validates the M1 lab infrastructure from a cold start:
#   1. docker compose services (dvwa, kali-tools, dvwa-db) running
#   2. loopback-only exposure (no 0.0.0.0 bindings)
#   3. DVWA answering HTTP 302 on / (documented unauthenticated behavior
#      of vulnerables/web-dvwa: redirect to login)
#   4. kali-tools /health answering HTTP 200 with {"status":"ok",...}
#      (contract from src/kali-tools/server.py:55)
#   5. nmap present inside the kali-tools container
#
# Scope: infrastructure only. Does NOT invoke the offensive execution path,
# does NOT alter policy, does NOT scan any target, does NOT contact any
# non-local system.
#
# Usage:
#   bash scripts/smoke_lab.sh
# Prerequisites:
#   docker daemon reachable; lab started with the corrected safe default
#   (M2.1: base compose is loopback-safe and context-correct on its own):
#     docker compose -p raphael-m1 -f configs/docker-compose.yml \
#       up -d --build dvwa kali-tools
# Exit codes: 0 = all checks PASS, 1 = at least one FAIL.
set -u

FAIL=0
note() { printf '%s\n' "$*"; }

DC="docker compose -p raphael-m1 -f configs/docker-compose.yml"

# 0. docker daemon reachable
if docker info >/dev/null 2>&1; then note "PASS  docker daemon reachable"; else note "FAIL  docker daemon reachable"; FAIL=1; fi

# 1. required services running (state=running)
for svc in dvwa kali-tools dvwa-db; do
    state=$($DC ps --format '{{.Name}} {{.State}}' 2>/dev/null | awk -v s="$svc" '$1 == s {print $2}')
    if [ "$state" = "running" ]; then note "PASS  service running: $svc"; else note "FAIL  service running: $svc (state=${state:-absent})"; FAIL=1; fi
done

# 2. loopback-only exposure (no 0.0.0.0 bindings for the lab services)
if $DC ps --format '{{.Name}} {{.Ports}}' 2>/dev/null | grep -E "0\.0\.0\.0" >/dev/null; then
    note "FAIL  loopback boundary: 0.0.0.0 binding detected"; FAIL=1
else
    note "PASS  loopback boundary: no 0.0.0.0 bindings"
fi

# 3. DVWA responds with the repository's documented local-lab contract
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:4280/ || true)
if [ "$code" = "302" ]; then note "PASS  dvwa GET / -> HTTP 302 (login redirect)"; else note "FAIL  dvwa GET / -> HTTP ${code:-none} (expected 302)"; FAIL=1; fi

# 4. kali-tools /health -> HTTP 200 with status=ok (server.py contract)
hcode=$(curl -s -o /tmp/smoke_kali_health.json -w '%{http_code}' --max-time 10 http://127.0.0.1:3800/health || true)
if [ "$hcode" = "200" ] && grep -q '"status":"ok"\|"status": "ok"' /tmp/smoke_kali_health.json 2>/dev/null; then
    note "PASS  kali-tools /health -> HTTP 200 status=ok ($(head -c 80 /tmp/smoke_kali_health.json))"
else
    note "FAIL  kali-tools /health -> HTTP ${hcode:-none} (expected 200 + status=ok)"; FAIL=1
fi

# 5. nmap present in the kali-tools container
if docker exec kali-tools nmap --version >/dev/null 2>&1; then
    note "PASS  nmap in kali-tools ($(docker exec kali-tools nmap --version 2>/dev/null | head -1))"
else
    note "FAIL  nmap in kali-tools (missing or container unreachable)"; FAIL=1
fi

rm -f /tmp/smoke_kali_health.json
if [ "$FAIL" = "0" ]; then note "SMOKE RESULT: PASS"; exit 0; else note "SMOKE RESULT: FAIL"; exit 1; fi
