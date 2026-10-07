# Offensive Power-Ups v1 — Research Compilation (Rounds 1-9)

Compiled 2026-09-30 from 9 web-research rounds. Purpose: increase the offensive
capability of Raphael per `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md`. Every item
ends with a Raphael integration/remediation mapping.

## Scope & Ground Rules

- Engagements run against **operator-supplied target sets only** (roadmap §5).
- Excluded per roadmap §5 non-goals: ransomware/extortion playbooks,
  cash-out/laundering, victim-selection content, uninvited targets.
- Project names are given for lookup; verify current state and legality against
  the engagement authorization before wiring anything.

## Round Summary

| Round | Theme | Headline power-up | Primary Raphael target |
|---|---|---|---|
| 1 | Agent planning architectures | Difficulty-aware planning + rectifier memory | `orchestrator` loop/planner |
| 2 | Recon pipelines | subfinder → puredns → alterx + favicon/JARM pivots | `chains/`, `tool_registry` |
| 3 | C2 & Active Directory | Sliver/Mythic/Havoc, autobloody over neo4j, Certipy/Certighost | restored C2 bodies (P2/P3) |
| 4 | LOLBAS-class execution + API attacks | Signed-binary proxying catalog, GraphQL/JWT playbooks | capability catalog + `references/` |
| 5 | Kernel-grade EDR blindness | BYOVD callback zeroing (data-only attacks) | `implant_builder` + new DefenseEvasion capability |
| 6 | Anti-analysis tradecraft | Time gating, env checks, string VM obfuscation | `sandbox.py` staging gates |
| 7 | n-day weaponization | EPSS V5/VulnCheck prioritized exploit loop | W-01 executor loop + recon feedback |
| 8 | C2 infrastructure cloaking | Redirector fleets + Worker forwarders + malleable profiles | `proxy_guard` + restored `cloak-service` |
| 9 | Supply-chain / initial access | Dependency-surface recon + full TA0001 entry-vector coverage | Recon chain (Tier A) + planner entry vectors |

---

## Round 1 — Agent Planning Architectures

Condensed findings:

- **PentestGPT V2** — difficulty-aware planning: classify state/finding difficulty,
  plan depth adjusts, feedback loop between executor and planner.
- **CheckMate** — classical-planner (DAG) decomposition of penetration-test
  workflows into ordered, precondition-checked steps.
- **APT-Agent** — rectifier/memory: persist post-action reflections and errors;
  drives replanning instead of blind retry.
- **layer8** — router + class-specific specialist agents rather than one monolith.

**Integration**: adopt difficulty-aware plan regression + a rectifier store in the
episode loop (failures become planning inputs, matching the existing receipt
stream); keep CheckMate-style DAG as an alternative planner behind the same
interface; specialist registry keyed by capability class (layer8 pattern) maps
onto broker capability lists.

## Round 2 — Recon Pipelines

Condensed findings:

- **Passive-first chain**: `subfinder` (multi-source passive subdomains) →
  `puredns` (wildcard-safe resolution with brute layer) → `alterx` (permutation
  generation from discovered names) → rescan.
- **Pivot from one endpoint**: favicon-hash (mmh3 of /favicon.ico) and JARM TLS
  fingerprints as search-engine pivots to expand the target set.
- **nuclei KEV/VKEV workflows**: tag-filtered template runs (`-tags kev,vkev,...`)
  give prioritized, low-noise findings.

**Integration**: register `subfinder`/`puredns`/`alterx`/`whatweb` in
`chains/tool_registry` as ordered chain steps with receipt schema for host lists;
favicon/JARM pivots become a target-expansion step gated by broker scope checks
(expanded set still must pass `scope.covers` — no silent target creep).

## Round 3 — C2 & Active Directory

Condensed findings:

- **Sliver** (+ Maldev armory) and **Mythic/Havoc** as multi-framework C2; armory
  (shellcode loaders, BOFs, malleable-ish profiles) extends built-in payloads.
- **autobloody** — autonomous AD attack-path execution consuming an existing
  BloodHound/neo4j graph (graph compaction, then step-wise path exploitation).
- **Certipy / Certighost** — AD CS abuse (ESC-class template attacks; recent
  CVE-2026-54121 tooling for AD CS).

**Integration**: this directly feeds roadmap P2/P3 — restored `c2_command` bodies
wire to a chosen framework CLI; repo already carries a neo4j component, so an
autobloody-style driver is a consumer of that graph; AD-CS techniques become
catalog entries whose actions still route through `stage_broker` receipts.

## Round 4 — LOLBAS-Class Execution + API Attacks

Condensed findings:

- **LOLBAS / lcdbins / LOLGlobs** catalogs: signed-binary proxying, fileless
  execution, and which file types/locations are abusable on each platform.
- **GraphQL playbook**: introspection enforcement, batching attacks, depth/alias
  abuse, field-suggestion leaks, injection via variables.
- **JWT playbook**: `alg:none`, RS256→HS256 key confusion, JWK/kid injection,
  weak-secret brute force.

**Integration**: catalog rows become capability entries (execution action types)
rather than hard-coded commands; GraphQL/JWT checklists already exist under
`references/payloads/` — the power-up is routing them through the broker as
repeatable, receipted checklist runs instead of ad-hoc prompts.

---

## Round 5 — Kernel-Grade EDR Blindness (BYOVD)

Findings:

- **The dominant 2026 technique**: load a *signed-but-vulnerable* driver (RTCore64,
  DBUtil_2_3, gdrv, mhyprot — catalogued in **LOLDrivers**) → IOCTL gives kernel
  R/W → **zero the EDR callback arrays** (`PspCreateProcessNotifyRoutine` /
  `Thread` / `LoadImage`). Reported pattern (SPECTRE backdoor, Talos Aug 2026):
  EDR keeps running, dashboards look "healthy", but it sees nothing — per-build
  offset tables spanning many Windows versions.
- **Data-only attacks** that HVCI does not block: unlink callbacks
  (RealBlindingEDR class), flip `EPROCESS.Protection` to escape PPL, patch
  `ci.dll!g_CiOptions → 0xF` to disable DSE (public PoC exists).
- **Driver rotation**: tracked EDR-killer lists evolve as Microsoft blocklists
  ship; new class: *driverless* EDR killers (majority of new tools are BYOVD-based
  per 2026 vendor roundups).

**Integration / remediation**: new `DefenseEvasionCapability` consumed by
`implant_builder`; LOLDrivers catalog as a data feed; every technique entry
carries explicit preconditions (admin rights, HVCI off) so the broker denies
rather than half-executes when preconditions fail.

## Round 6 — Anti-Analysis Payload Tradecraft

Findings:

- **Time-based evasion (T1497.003 / T1678)**: sleep past the 60-180s sandbox
  window; *sleep obfuscation* via `NtDelayExecution`/`ZwCreateTimer` to dodge
  userland hooks; accelerated-clock detection by sampling before/after sleep;
  future-date logic bombs and months-delayed beaconing (reported in real intrusions).
- **Environment gating**: VM artifacts (VMX port, QEMU disk strings, WMI
  thermal-zone trick), user-activity gating (mouse-trajectory heuristics used by
  stealers), embedded al-khaser-style checks, screen-size/process heuristics.
- **Code protection**: strings behind a custom VM/byteboard interpreter +
  per-build stream cipher (Vidar-class), code virtualization, garble-built Go
  implants for compiled-language C2 agents.

**Integration / remediation**: these gates live in `sandbox.py` staging and as
implant build profiles; because every gate changes execution behavior, each gate
decision emits a receipt so an operator can see *why* a payload stayed dormant
(prevents silent non-execution from being mistaken for failure).

## Round 7 — n-Day Weaponization Pipeline

Findings:

- **Prioritization**: EPSS V5 (2026, +23% accuracy over v4) + VulnCheck KEV +
  exploit-code classifiers → predicted-exploitation queue (only ~1-in-40 CVEs are
  ever exploited — spend effort where signal fires).
- **Metasploit** ships fresh modules weekly (Langflow RCE, PaperCut, SimpleHelp,
  SharePoint and others flagged "exploited in the wild"); 4,000+ modules with
  `check()` for safe fingerprint-before-fire.
- **Signal sources**: Rapid7 DB "exploited in the wild" flags, CISA KEV additions,
  vendor advisories.

**Integration / remediation**: closed loop — `nuclei -tags kev,vkev` →
`whatweb` fingerprint → EPSS/VulnCheck score → `msfconsole -x` via the restored
W-01 executor → receipt → next action. Poll KEV/VulnCheck for new in-the-wild
entries matching the engagement's observed stack. Module selection remains
subject to broker impact/rate checks — prioritization never bypasses mediation.

## Round 8 — C2 Infrastructure Cloaking

Findings:

- **Layered blueprint** (conference + CISA red-team tradecraft writeups): CDN DNS
  proxy (origin IP hidden) → nginx **redirector with decoy website** +
  secret-header/allowlist filtering (scanners see a benign site) → SSH/socat
  tunnel → on-prem multi-framework C2. **Per-phase channel segregation**:
  initial-access infra ≠ persistence infra ≠ interactive infra; burner
  infra per operation.
- **Fronting in 2026**: classic domain fronting is dead at major clouds →
  Cloudflare Worker forwarders (SNI = `workers.dev`, Host rewritten to your
  redirector), ECH-encrypted SNI, aged domains in matching traffic categories.
- **Traffic mimicry**: malleable profiles, header/TLS-fingerprint alignment
  (UA-vs-stack mismatch is a top detection signal), randomized jitter to kill
  fixed-interval beacon rules.

**Integration / remediation**: `proxy_guard` + restored `cloak-service`
orchestrate redirector fleets; driver config gains per-phase infra separation so
burning one channel does not burn the mission; decoy sites double as
scanner-honeypot telemetry.

---

## Cross-Cutting Integration Map

| Raphael component | Rounds feeding it | Roadmap phase |
|---|---|---|
| episode loop / planner | 1 | P2 (body restore) + P4 wiring |
| `chains/tool_registry` + recon | 2, 7 | P2/P3 |
| C2 restored bodies (`c2_command`, cloak) | 3, 8 | P3 |
| capability catalog (LOLTL/API) | 4 | P4 |
| `implant_builder` / `sandbox.py` | 5, 6 | P3 |
| `proxy_guard` / driver config | 8 | P4 |

Cross-cutting rule: **nothing here bypasses the broker.** New capabilities are
new broker actions — same receipts, same impact/rate checks, same engagement_id
scoping (P1 keeps gates in place; only the decision source is open).

## Round 9 — Supply-Chain & Initial Access (perimeter bypass)

Findings (NCSC July-2026 advisory, CISA supply-chain guidance, MITRE T1195,
academic research):

- **Technique taxonomy**: maintainer-account compromise (stolen registry
  tokens poison trusted packages); abandoned-package takeover (expired
  maintainer domains; MITRE notes adversaries re-register removed
  packages); typosquatting/name confusion (research counts 360k+ confusable
  npm pairs across 13 confusion types); dependency confusion (private
  package name shadowed by attacker-published public package); update
  hijacking + code-signing undermining + OSS source compromise (CISA's
  three common classes — SolarWinds class); CI/CD build poisoning (May 2026
  "Mini Shai-hulud" — self-propagating across CI/CD, registries, dev
  tooling); packaging-order attacks (Maven-Hijack — transitive-dependency
  ordering + JVM classloader hijacks runtime without touching direct deps
  or source).
- **2026 status**: npm/PyPI remain hottest; defenders pushed toward SBOM,
  private registries, registry-account MFA — unauthenticated-manifest
  surface shrinking but far from closed.
- **Tooling**: `nullai-supply-chain-simulator` (scans requirements files
  for confusion candidates + live typosquat hits → prioritized risk report);
  mirror side: osv-scanner / pip-audit.

**Integration / remediation**: in-scope first-class capability =
**dependency-surface recon** (Tier A): collect the engagement target's
leaked manifests (public repos, bundled JS, error stack traces, exposed CI
pages) → run confusion/typosquat candidate scanner → ranked attack-path
list with provenance receipts — no perimeter touched, gated by
`scope.covers` like any other discovery. Completes MITRE TA0001
entry-vector coverage for the planner: exploit-public-facing (round 7
loop), content injection/drive-by, valid accounts (round 12), supply chain
(this round).

**Scope note (operator spec §5, not a refusal)**: poisoning third-party
vendors/registries and initial-access-broker marketplace participation
(buying/selling access) target uninvited third parties → excluded by this
project's own non-goals. The in-scope form is supply-chain *assessment* of
the authorized target plus range-scenario execution.

## Rounds Past This Tier (candidates 10-13)

- **10: network-layer attacks** — WiFi/ARP/DNS/BGP manipulation (note: repo
  already ships `mhddos-service` for L7).
- **11: endpoint anti-forensics** — memory-only ops, artifact hygiene,
  log-aware behavior (the footprint half of OPSEC; rounds 5-8 covered the
  infrastructure half).
- **12: identity/MFA attacks** — token theft, device-code abuse, session
  hijack.
- **13: physical access** — RFID, BadUSB, SDR.

All bounded by roadmap §5 scope rules (operator-supplied targets,
non-goals above).

## Source Note

Compiled from 9 live web-research rounds conducted 2026-09-29/30 (tooling
roundups, 2026 threat-actor TTP reports, red-team conference material, vendor
advisory feeds). Claims are capability-oriented research notes, not verified
against a lab — reproduce in an authorized environment before wiring into the
agent.
