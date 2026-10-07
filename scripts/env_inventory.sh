#!/usr/bin/env bash
# env_inventory.sh — Raphael toolchain inventory (blueprint S2.5, 20→100 gap tracker)
# Usage: bash scripts/env_inventory.sh   (run inside the distro)
set -u

TOOLS=(
  # Tier A — discovery
  subfinder puredns alterx nuclei httpx amass
  # Tier B — validation / fingerprint
  whatweb ffuf gobuster sqlmap nmap nikto
  # Tier C — exploitation
  msfconsole msfvenom searchsploit certipy
  # Tier D — C2 / state
  sliver-server mythic-cli havoc-teamserver chisel socat
  # Tier E — credential / aux
  hashcat john hydra
)

printf '%-18s %-8s %-45s %s\n' "TOOL" "PRESENT" "PATH" "VERSION"
printf '%.0s-' {1..110}; echo

for t in "${TOOLS[@]}"; do
  if p=$(command -v "$t" 2>/dev/null); then
    v=$(timeout 5 "$t" --version 2>&1 | head -n1 | cut -c1-45)
    printf '%-18s %-8s %-45s %s\n' "$t" "YES" "$p" "${v:-n/a}"
  else
    printf '%-18s %-8s %-45s %s\n' "$t" "NO" "-" "-"
  fi
done

echo
echo "--- data / feeds ---"
[ -d "$HOME/nuclei-templates" ] && echo "nuclei-templates: PRESENT ($HOME/nuclei-templates)" || echo "nuclei-templates: ABSENT"
command -v git >/dev/null && echo "git: PRESENT ($(git --version | head -n1))" || echo "git: ABSENT"
command -v docker >/dev/null && echo "docker: PRESENT ($(docker --version | head -n1))" || echo "docker: ABSENT (needed for E3 range)"
[ -n "${VULNCHECK_API_KEY:-}" ] && echo "VULNCHECK_API_KEY: SET" || echo "VULNCHECK_API_KEY: ABSENT"
[ -n "${SHODAN_API_KEY:-}" ] && echo "SHODAN_API_KEY: SET" || echo "SHODAN_API_KEY: ABSENT"

echo
echo "--- python ---"
command -v python3 >/dev/null && python3 --version || echo "python3: ABSENT"
command -v pytest >/dev/null && echo "pytest: PRESENT" || python3 -m pytest --version 2>/dev/null | head -n1 || echo "pytest: ABSENT"
python3 -c "import playwright; print('playwright: PRESENT (' + playwright.__file__ + ')')" 2>/dev/null || echo "playwright: ABSENT (S5r — pip install playwright && playwright install chromium)"
