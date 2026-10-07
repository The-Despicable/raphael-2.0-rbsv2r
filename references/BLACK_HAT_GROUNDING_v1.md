# BLACK_HAT_GROUNDING_v1

Status: VERIFICATION RECORD
Date: 2026-10-01
Scope: `BLACK_HAT_OPERATOR_BLUEPRINT.md` — every citable ATT&CK ID and CISA
advisory reference checked against primary sources; §5 safe-lab executability
audited against the build host.
Method: primary-source fetch (live) + automated ID validation + negative
control + manual line-level correction. Repository code untouched; no tools
installed (read-only environment actions).

## 1. Sources fetched (primary)

| Source | URL | Result (2026-10-01) |
|---|---|---|
| ATT&CK enterprise index | `https://attack.mitre.org/techniques/enterprise/` | 222 techniques, 475 sub-techniques (697 IDs) |
| ATT&CK mobile index | `https://attack.mitre.org/techniques/mobile/` | 79 techniques, 49 subs (126 IDs) |
| ATT&CK ICS index | `https://attack.mitre.org/techniques/ics/` | 80 techniques, 18 subs (98 IDs) |
| CISA AA25-343A | `https://www.cisa.gov/news-events/alerts` (advisory page) | fetched, confirmed (see §5) |
| CISA AA23-320A | `https://www.cisa.gov/news-events/alerts` (advisory page) | fetched, confirmed (see §5) |

Enterprise counts cross-checked by two independent parses (href-extraction
from live HTML; line-anchored parse of the converted-text index): identical
222/475. ID extraction from the blueprint: `\bT\d{4}(\.\d{3})?\b` over the
whole file (placeholders like `T08xx` cannot match — `xx` are not digits).

## 2. ATT&CK ID verdict

**Before corrections:** 106 unique IDs → **101 OK, 5 failures:**

| ID | Verdict | Resolution |
|---|---|---|
| `T1456` | exists only in **Mobile** matrix (Drive-By Compromise) | kept, now cited in Mobile row 26 with matrix label |
| `T1473` | **does not exist in any matrix** (probed: absent enterprise/mobile/ICS) | removed; replaced with prose "a sudden defender-response event" |
| `T1562` (Impair Defenses) | **retired from current enterprise index** | row 10 → `T1685, T1686`; row 16 (impact) → dropped (defense impairment ≠ impact) |
| `T1562.010` (Network Device Defense Evasion) | retired with parent | row 21 → `T1078, T1021.005 (VNC; CISA AA25-343A)` |
| `T1656` (Impersonation, ATT&CK v17 per CISA) | **renumbered**; absent from current index | row 20 → `T1684.001` (Impersonation, sub of T1684 Social Engineering) |

**After corrections:** 119 unique IDs → **119 OK, exit 0** via
`scripts/ground_attack_ids.py` (live, all three matrices).

**Negative control** (synthetic file citing `T9999`, `T1562.010`, `T1485`):
validator exits 1 and flags exactly `T9999` + `T1562.010`; `T1485` passes —
the green result above is not vacuous.

## 3. Corrections applied to the blueprint (15 edits)

| # | Location | Was | Now |
|---|---|---|---|
| 1 | row 10 defense evasion | `T1562` | `T1685, T1686` |
| 2 | row 16 impact | `..., T1565, T1562` | `..., T1565` |
| 3 | row 17 identity | `T1550.001/003` (ambiguous slash form) | `T1550.001, T1550.003` |
| 4 | row 19 cloud | `T1098.007*` (nonexistent) | `T1098.001` (Additional Cloud Credentials) |
| 5 | row 20 SaaS | `T1656` | `T1684.001` |
| 6 | row 21 edge devices | `T1562.010? (…where mapped)` | `T1133, T1190, T1078, T1021.005 (VNC; CISA AA25-343A)` |
| 7 | row 23 supply chain | `T1195.001, T1195.002, T1554` | `+ T1677` (Poisoned Pipeline Execution) |
| 8 | row 25 OT/ICS | `ATT&CK for ICS (T08xx series)` | `ATT&CK for ICS: T0819, T0822, T0883, T0831, T0880` |
| 9 | row 26 mobile | `ATT&CK for Mobile` | `ATT&CK for Mobile: T1456, T1430.001` |
| 10 | row 27 social eng. | `T1566, T1456?, T1621, T1598` | `T1684, T1566, T1566.004, T1621, T1598` |
| 11 | §5 Certipy row | `T1553? (pre-auth bypass context), AD CS T-numbers per version` | `T1553, T1649` |
| 12 | §5 MFA-harness row | `T1621, T1456` | `T1621, T1566.004, T1598.004` |
| 13 | §5 hash-theft row / C2 row | `T1550.002/.003`, `T1090.002/.003` | explicit `T1550.002, T1550.003`, `T1090.002, T1090.003` |
| 14 | §5 CALDERA row | `T14xx (emulated)` | `T1059, T1021, T1110, T1218 (emulated)` |
| 15 | §6 reasoning prose | `T1473-class defender response` | `a sudden defender-response event` |

## 4. ATT&CK renumbering log (name-verified against live index)

- **T1562 Impair Defenses retired.** Promotions: `T1685` Disable or Modify
  Tools, `T1686` Disable or Modify System Firewall, related `T1687`
  Exploitation for Defense Impairment.
- **T1656 Impersonation → `T1684.001`.** New parent `T1684` Social
  Engineering (`.002` Email Spoofing). CISA AA23-320A still prints `T1656`
  because it pins ATT&CK **v17**.
- **Name confirmations used in the report:** `T1566.004`/`T1598.004`
  Spearphishing Voice, `T1021.005` VNC, `T1090.003` Multi-hop Proxy,
  `T1550.003` Pass the Ticket, `T1098.001` Additional Cloud Credentials,
  `T1553` Subvert Trust Controls, `T1649` Steal or Forge Authentication
  Certificates, `T1677` Poisoned Pipeline Execution, `T1456` Drive-By
  Compromise (Mobile), `T1430.001` Remote Device Management Services
  (Mobile), `T0819` Exploit Public-Facing Application, `T0822` External
  Remote Services, `T0883` Internet Accessible Device, `T0831` Manipulation
  of Control, `T0880` Loss of Safety.
- **Dead-end probes recorded:** `T1473`, `T1656`, `T1562(.010)`, `T0812`
  absent from all three current indexes.

## 5. CISA advisory verification

- **AA25-343A** ✓ — "Pro-Russia Hacktivists Conduct Opportunistic Attacks
  Against US and Global Critical Infrastructure" (Dec 2025, rev. Dec 2025).
  Content matches the blueprint's hacktivist profile: CARR, Z-Pentest,
  NoName057(16), Sector16; VNC/remote-access and unauthenticated OT/HMI
  exposure; brute-force entry; opportunistic/low-sophistication claims.
  The advisory's own ATT&CK mapping (pins **v18**) supplies `T1021.005` (VNC)
  and ICS IDs now cited in rows 21/25.
- **AA23-320A** ✓ — "Scattered Spider" (Nov 2023, rev. Jul 2025). Content
  matches rows 12/20/27 use: help-desk vishing/MFA reset tradecraft; cites
  `T1566.004`/`T1598.004` Spearphishing Voice and (under **v17** numbering)
  `T1656` — renumbered to `T1684.001` in the current index (§4).

## 6. Executability status (§5 safe-lab equivalents)

`scripts/env_inventory.sh` (re-run 2026-10-01):

| Item | Status |
|---|---|
| 24 named arsenal tools (subfinder…hydra) | **0/24 present** |
| nuclei-templates | ABSENT |
| docker | PRESENT 29.7.2 (fixture-service path viable) |
| git | PRESENT 2.53.0 |
| python3 / pytest | PRESENT 3.14.4 / 9.1.1 |
| playwright (S5r) | ABSENT — `pip install playwright && playwright install chromium` |
| VULNCHECK_API_KEY / SHODAN_API_KEY | ABSENT |

Implication: blueprint "identical (lab)" cells are **install targets, not
current capabilities** (now annotated in the blueprint's §5 preamble).
Bring-up classes: distro packages (apt: nmap, sqlmap, hydra, john, hashcat),
`go install` for the ProjectDiscovery suite (subfinder, nuclei, httpx,
puredns, alterx), pip/pipx (certipy-ad), vendor release binaries or containers
for C2 frameworks, `git clone` for theHarvester/nikto/searchsploit-class
tools, plus `nuclei-templates` via its git repository. Verification loop:
install → re-run `scripts/env_inventory.sh` until the row reads PRESENT with a
version. Environment left unchanged by this session.

## 7. Re-grounding procedure

```bash
# from repo root, inside WSL
python3 scripts/ground_attack_ids.py BLACK_HAT_OPERATOR_BLUEPRINT.md
# offline: --cache enterprise=/path/to/saved/index.txt
```

Exit codes: 0 = all cited IDs exist; 1 = grounding failure (IDs listed);
2 = source/usage error (never treat as pass). Re-run after **any** edit that
touches a `T\d{4}` token, and after MITRE releases a new ATT&CK version —
renumbering (§4) is the failure mode this exists to catch. The synthetic-file
negative control from §2 can be re-created any time to prove the tool works.

## 8. Explicitly NOT verified in this session

- Group-attribution and tool-behavior claims in §8/§12/§16 — traced to
  `references/offensive_powerups_v1.md` / `famous_group_ttps_v1.md` (Rounds
  1-17), which carry their own source trails; not re-audited here.
- Vendor threat-intel reports and academic references — not fetched.
- 13 offensive-architecture paper fetches + 4 paywalled IEEE papers — offer
  still unanswered.
- Arsenal installation (§6) — deliberately not performed (read-only session).
