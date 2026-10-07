# BLACK HAT OPERATOR BLUEPRINT

Status: RESEARCH / ARCHITECTURE
Version: 1.0
Purpose: Adversarial capability modeling
Relationship to Raphael: External capability reference

Primary sources: `references/offensive_powerups_v1.md` (Rounds 1-9),
`references/famous_group_ttps_v1.md` (Rounds 10-17), MITRE ATT&CK, CISA advisories,
vendor threat-intel reports (Microsoft MTTI, Google TI, Mandiant, Unit 42,
CrowdStrike, Recorded Future), tool documentation, academic security research.

Grounding (2026-10-01): every ATT&CK ID in this document validated against the
live ATT&CK enterprise, mobile, and ICS technique indexes using
`scripts/ground_attack_ids.py` (119/119 found, exit 0); CISA AA25-343A and
AA23-320A fetched and confirmed. Full verification record, correction log, and
toolchain executability status: `references/BLACK_HAT_GROUNDING_v1.md`.

## 1. DOCUMENT IDENTITY

```markdown
# BLACK HAT OPERATOR BLUEPRINT

Status: RESEARCH / ARCHITECTURE
Version: 1.0
Purpose: Adversarial capability modeling
Relationship to Raphael: External capability reference
```

This document is **independent of Raphael**. It describes the adversarial
capability ceiling — what a maximally capable adversarial operator looks like as a
software system. It does not assume Raphael is the only implementation. Raphael
(and any other authorized evaluation system) may later consume parts of this
blueprint as a capability/reference source; **implementation and authorization
decisions belong to the consuming system**. This document is **not** a Raphael
implementation roadmap, and `RAPHAEL_ARCHITECTURE_ROADMAP_v2.md` is not modified
by it.

Scope discipline (inherited from the research ground rules): capability behavior,
architecture, and reasoning are modeled at depth; weaponization recipes, live
criminal infrastructure, cash-out/laundering, victim selection, and guidance
against unauthorized targets are out of scope by construction — the blueprint's
own high-consequence sections (§15) exist precisely to keep those behaviors
*representable but not operational*.

---

## 2. DESIGN PHILOSOPHY

> **Model the attacker first. Constrain the operator second.**

A blueprint that starts from restrictions produces a stunted adversary model and
therefore a weak evaluator: it cannot recognize capability it never represented.
The blueprint therefore describes the full theoretical capability of a highly
capable adversarial operator, then classifies each capability by how a consuming
system may instantiate it (implement / simulate / fixture / research-only).

Ten separable concerns — the blueprint never collapses these:

```text
Capability    what the operator *can* do (families, not tools)
Reasoning     how it decides what to do next
Knowledge     what it knows about targets, tools, and itself
Tradecraft    how it avoids detection and error while doing it
Infrastructure what systems it runs on and how they are separated
Execution     how actions are issued, checked, receipted
Adaptation    how belief change drives replanning
Persistence   how state survives interruption across a campaign
Evidence      what it records and how provenance is kept
Objectives    what the campaign is for (scoped by the operator, never inferred)
```

Core principle:

> **Tools are merely implementations of capabilities.** The capability layer is
> what must be modeled; the tool layer churns monthly, the capability layer churns
> in years, and the reasoning layer barely churns at all.

Central design principle of the whole document:

> The objective is not maximum destructive power. The objective is maximum
> adversarial capability and reasoning fidelity, represented in a form that can
> later be evaluated and safely instantiated in authorized environments.

---

## 3. OPERATOR MODEL

```text
                BLACK-HAT OPERATOR
                       │
       ┌───────────────┼────────────────┐
       │               │                │
   Intelligence     Reasoning       Capability
       │               │                │
       ▼               ▼                ▼
   Target Model    Strategy Model   Tool Arsenal
       │               │                │
       └───────────────┼────────────────┘
                       │
                 Operational Loop
                       │
                       ▼
                  Environment
                       │
                       ▼
                  New Evidence
                       │
                       └──────→ Replanning
```

**Intelligence** — everything known about the environment: assets, identities,
trust, technology, controls, people, timing. Maintained as an explicitly
uncertain world model (§6) — not a fact list, a *belief state* with confidence
and provenance per claim.

**Reasoning** — hypothesis generation over the target model, attack-path
enumeration, opportunity scoring, technique selection, belief update. Reasoning
is where capability is *directed*; it is deliberately separated from Capability
so that a system can be reasoning-rich with a small arsenal (a professional red
team) or arsenal-rich with naive reasoning (a volunteer DDoS mob) — both are
real adversary classes (see §16-§18).

**Capability** — the tool arsenal: an ordered catalog of capability families
(§4) with per-tool operational characteristics (§5), power level, prerequisites,
and failure modes. Registered against ATT&CK so capability gaps are measurable.

**Operational Loop** — the cycle that couples the three: act on the environment,
receive new evidence, update the model, re-decide. The loop is the unit of
evaluation; isolated actions are not.

**Environment** — the target plus its defenders. It is not passive: it emits
signals (logs, alerts, deception) and counter-actions (§12).

**New Evidence / Replanning** — every loop iteration ends in belief update; when
expected and observed evidence diverge past a threshold, strategy is abandoned
rather than retried. Failed-path abandonment is a defining trait of a capable
operator (§13).

---

## 4. CAPABILITY TAXONOMY

Full offensive capability taxonomy. ATT&CK mappings given where the source
material supports them; IDs are the Enterprise matrix unless noted. "Model
class" indicates how a consuming evaluation system typically instantiates the
family (implement / simulate / fixture — see §15, §23).

| # | Capability family | What it is | Representative ATT&CK | Model class |
|---|---|---|---|---|
| 1 | Reconnaissance | Target observation pre-contact; passive OSINT first, active scanning last | T1593 Search open sites/domains, T1595 Active scanning, T1592, T1589, T1590, T1596, T1597, T1598 | implement (lab) |
| 2 | OSINT | People/tech/org data fusion: breach corpora, code repos, job posts, metadata | T1593, T1591, T1592 | implement (scoped) |
| 3 | Attack-surface discovery | Service/version/difference mapping of the reachable perimeter | T1595.001, T1046 Network service scanning | implement |
| 4 | Vulnerability discovery | CVE identification, n-day analysis, 0-day research, config weakness detection | T1595.002 Vulnerability scanning | implement (fixtures) |
| 5 | Initial access | First foothold: phishing, public-app exploit, valid creds, supply chain, trusted relations | T1190, T1566, T1078, T1133, T1195, T1199 | fixture |
| 6 | Exploitation | Code-exec primitive realization: web RCE, client-side, local privesc chains | T1203 Exploitation for client exec, T1068, T1059 | fixture (lab) |
| 7 | Credential access | Obtaining secrets: password attacks, kerberoasting, keylogging, credential stores | T1110, T1558.003, T1003, T1555, T1552 | fixture; simulation for bulk |
| 8 | Privilege escalation | From local user/system to admin/SYSTEM/domain-privileged | T1068, T1548, T1055, T1574 | implement (lab) |
| 9 | Persistence | Surviving reboot/re-image: services, tasks, hooks, accounts, tokens, implants | T1543, T1053, T1546, T1136, T1098, T1547 | fixture only (§15) |
| 10 | Defense evasion | Avoiding/preempting controls: obfuscation, signed-binary abuse, ETW/AMSI concepts, rootkit behavior | T1027, T1036, T1685, T1686, T1055, T1218, T1014, T1140 | concept + fixture |
| 11 | Discovery | Mapping the compromised environment: users, shares, software, topology, cloud inventory | T1082, T1087, T1049, T1018, T1069, T1083, T1057, T1518, T1580, T1619 | implement |
| 12 | Lateral movement | Leveraging access across hosts/segments: remote services, ticket abuse, coercion | T1021, T1550, T1558, T1210 | fixture (lab range) |
| 13 | Collection | Staging and staging-area discipline for target data | T1005, T1114, T1560, T1039 | implement (fixtures) |
| 14 | Command and control | Implant-channel architecture: protocols, redirectors, fronting, rotation | T1071, T1090, T1095, T1568, T1571, T1573, T1572 | implement (lab C2) |
| 15 | Exfiltration | Movement of collected data out; staging, encryption, channel choice | T1041, T1048, T1020, T1537, T1567 | fixture (canary data) |
| 16 | Impact | Disruption/destruction/manipulation — the high-consequence family | T1486, T1489, T1490, T1485, T1496, T1565 | simulate only (§15) |
| 17 | Identity attacks | Credential, session, and identity-plane abuse: MFA fatigue, token theft, consent grants | T1078, T1621, T1539, T1550.001, T1550.003, T1556, T1098 | fixture |
| 18 | AD/ADCS | Domain services as an attack surface: Kerberos abuse, ACLs, delegation, certificate services | T1558, T1484 Domain trust manipulation, T1078.002, T1556.001 | implement (lab AD) |
| 19 | Cloud | Control-plane abuse: IAM, metadata, keys, workloads, serverless | T1078.004, T1552, T1580, T1526, T1619, T1098.001 | fixture (disposable tenancy) |
| 20 | SaaS | App-level compromise: OAuth consent, admin impersonation, integration abuse, data staging | T1550, T1114.002, T1567.002, T1684.001 | fixture (tenant) |
| 21 | Edge devices | VPN/NGFW/routers/VDI/virtualization managers — unauthenticated perimeter + persistence | T1133, T1190, T1078, T1021.005 (VNC; CISA AA25-343A) | fixture |
| 22 | Web/API | Modern app surface: authz logic, GraphQL, API object-level abuse, SSRF chains | T1190, T1199 | fixture |
| 23 | Supply chain | Vendor/updater/build-system trust: code-signing, update channels, CI/CD, npm/pypi classes | T1195.001, T1195.002, T1554, T1677 | research + fixture |
| 24 | Network infrastructure | Operator-side infrastructure: domains, VPS, redirects, proxy chains, traffic separation | T1090, T1568, T1571 | implement (owned infra) |
| 25 | OT/ICS | Process-control attack surface: engineering workstations, historians, HMI, safety systems | ATT&CK for ICS: T0819, T0822, T0883, T0831, T0880 | fixture (simulated plants) |
| 26 | Mobile/device ecosystems | Handsets, MDM, app permissions, device trust | ATT&CK for Mobile: T1456, T1430.001 | fixture |
| 27 | Social-engineering surfaces | Human targets: pretexting, vishing, MFA prompt abuse, help-desk resets | T1684, T1566, T1566.004, T1621, T1598 | simulation (red-team scripts) |
| 28 | Long-horizon campaign management | Objective tracking, dormancy, staged objectives, resource/OPSEC budgeting across weeks+ | (cross-cutting; T1098, T1071 patterns) | reasoner feature |

Evidence base: capability families 1-16 track the ATT&CK enterprise chain
(TA0043→TA0040); families 17-27 correspond to the expansion surfaces documented
in Rounds 11, 15, 16 (identity/cloud/SaaS/edge/supply chain) of
`famous_group_ttps_v1.md`; family 28 corresponds to the campaign-management
patterns distilled in Round 11 lessons and the APT profile (§18).

---

## 5. OFFENSIVE ARSENAL

Structured arsenal catalog. Every entry follows the field template; classes
distinguish *threat-actor tooling*, *legitimate red-team tooling*, *dual-use*,
*adversary-emulation*, *research tooling*, and *destructive tooling* (the last is
described behaviorally only — never operationally).

> Environment status (grounded 2026-10-01): `scripts/env_inventory.sh` reports
> **0/24** arsenal tools installed on the current build host (docker, git,
> python3, pytest present; no API keys; playwright absent). "Safe-lab equivalent"
> cells are **install targets with verification commands**, not current
> capabilities. Bring-up and re-verification procedure:
> `references/BLACK_HAT_GROUNDING_v1.md` §6.

### 4.1 Field template

```text
Tool | Capability | Category | ATT&CK Mapping | Typical Role | Platform |
Prerequisites | Threat-Actor Usage | Red-Team Usage | Capability Level |
Dependencies | Operational Characteristics | Safe-Lab Equivalent | Evidence Source
```

### 4.2 Arsenal catalog

**Discovery & recon**

| Tool | Capability / Category | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| nmap | network mapping, service/version discovery; dual-use | T1046, T1595 | perimeter cartography | cross | universal (all classes) | universal | medium | identical (own lab) | tool docs, every APT report |
| subfinder / amass / assetnote-class DNS recon | attack-surface discovery, subdomain enum | T1593, T1595 | surface enumeration | cross | documented (esp. hacktivist + ransomware initial-access: R14, R16) | universal | medium | identical (scoped domains) | tool docs, R14/R16 |
| puredns / massdns | high-volume DNS resolution with wildcard filtering | T1595 | resolve validation | cross | paired with above | universal | medium | identical | tool docs |
| httpx / web fingerprinting stacks | HTTP service identification, technology fingerprint | T1046 | stack fingerprint | cross | common | universal | medium | identical | tool docs |
| nuclei | template-driven vulnerability validation | T1595.002 | automated check execution | cross | documented abuse for initial access (R14, R16) | universal | high | identical, allowlisted templates | tool docs, CISA AA25-343A-class advisories |
| theHarvester / holehe-class OSINT | people/mail/domain OSINT fusion | T1589, T1591 | identity-side recon | cross | common | common | low | identical (scraped-from-sources only) | tool docs |

**Web/API exploitation**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Burp Suite (or equivalent proxy) | HTTP interception/modification, scanner | T1190 | manual web testing | cross | common | universal | medium | identical (lab apps) | tool docs |
| sqlmap | SQL-injection detection & data extraction | T1190 | automated SQLi | cross | documented | universal | high | identical (DVWA/lab) — methodology applies, lab targets only | tool docs; osmania-lab methodology |
| ffuf / feroxbuster / gobuster | content/vhost/API fuzzing | T1046, T1190 | surface brute-force enum | cross | common | universal | medium | identical | tool docs |
| kiterunner / API route fuzzing | API route discovery at scale | T1190 | API mapping | cross | growing | common | medium | identical | tool docs |
| wpscan / CMS scanners | CMS-specific vuln discovery | T1190 | platform recon | cross | documented for initial access | common | medium | identical | tool docs |
| commix / argument-injection tooling | OS command injection automation | T1190 | injection validation | cross | common | common | high | identical (lab) | tool docs |

**Exploitation frameworks**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Metasploit Framework | exploit module corpus, post modules, payload handling | T1203, T1068, T1190 | exploitation + post framework | cross | documented (esp. ransomware crews via public exploits) | universal | very high | identical (lab range) | tool docs, vendor reports |
| exploit-db / nuclei exploit templates / n-day corpora | known-exploit catalog | T1190 | exploit retrieval | cross | universal | common | high | lookup only, execute in lab | primary repos |
| exploit-dev toolchain (Ghidra, Binary Ninja/IDA, x64dbg/gdb, angr) | vulnerability research, 0/n-day analysis | T1595.002, T1027 | vuln research | cross | documented (APT + mercenary) | common | very high | identical (research on own/authorized code) | tool docs, papers |
| browser-exploit chains (historical) | client-side RCE delivery | T1203, T1566 | drive-by delivery | cross | documented (Mercenary/APT vendors) | rare | very high | fixture: simulate delivery, never real chains | R11, vendor reports |
| n-day weaponization pipeline (concept) | patch→diff→PoC→reliability engineering | T1190 | exploit readiness | cross | documented (Equation/FuzzBunch class: R11; CVE-2025-31324-class: R15) | N/A | very high | research-only + range verification | R7 |

**Credential access & identity**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Hashcat / John the Ripper | offline password cracking | T1110.002 | credential recovery | GPU/CPU | universal | universal | medium | identical (own hashes) | tool docs |
| Responder / NTLM relaying stacks | LLMNR/NBT-NS poisoning, relay capture | T1557, T1021 | credential interception | Windows/Linux | documented (R15: coercion/relay class, UNC3886-class) | universal | high | identical (isolated LAN) | tool docs, CISA/Mandiant |
| Impacket suite (secretsdump, psexec, getTGT, ntlmrelayx) | AD/Kerberos protocol abuse | T1550.002, T1558, T1021.002 | domain abuse toolkit | cross | documented (many groups) | universal | very high | identical (lab AD) | tool docs |
| Rubeus / kekeo-class Kerberos tooling | ticket request/abuse, AS-REP, roasting | T1558 | Kerberos abuse | Windows | documented (FIN7-class: R12; APT) | universal | high | identical (lab AD) | tool docs |
| mimikatz-class credential extraction | LSASS/token/specialized access | T1003 | credential dump | Windows | universal (threat + ransomware) | universal | very high | identical (lab) | tool docs |
| Certipy / ADCS abuse tooling | certificate template/ESC misconfig exploitation | T1553, T1649 | AD CS privilege paths | cross | documented (APT: R11) | universal | very high | identical (lab AD CS) | tool docs, SpecterOps-class research |
| ROADtools / AADInternals / GraphRunner | Entra/O365 identity plane assessment | T1078.004, T1550 | cloud identity abuse | cross | documented (ShinyHunters OAuth year: R16) | universal | very high | identical (lab tenant) | tool docs, R16 |
| TokenTactics-class token manipulation | refresh-token/request abuse | T1539, T1550.001 | token replay | cross | documented (R16) | common | high | identical (lab tenant) | R16 |
| Kerbrute / password-spray tooling | domain account validation & spray | T1110.003 | identity enum | cross | universal | universal | medium | identical (lab AD) | tool docs |
| hash-theft / MFA-fatigue harness (concept) | push-spam, help-desk reset pretexts | T1621, T1566.004, T1598.004 | MFA defeat | cross | documented (Lapsus$-class: R12; Scattered Spider: R12/R16) | scripted in red teams | high | simulation scripts + consenting test users | R12/R16, CISA AA23-320A |

**AD / post-exploitation / lateral movement**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| netexec (successor of CredMapExec) | spray, exec, module framework across protocols | T1021, T1078 | domain lateral framework | cross | documented | universal | high | identical (lab) | tool docs |
| BloodHound / SharpHound | AD relationship graph → privilege paths | T1087.002, T1484 | attack-path analysis | cross | documented (ransomware pre-encryption: R16) | universal | very high | identical (lab AD) | tool docs, R16 |
| Coercer / PetitPotam-class coercion | force authentication toward attacker listener | T1210?, T1557 | relay staging | cross | documented (R15 UNC3886-class) | universal | high | identical (lab) | tool docs, vendor |
| WMI/SCM/WinRM/SSH exec modules | remote execution primitives | T1021 | lateral exec | Windows/Linux | universal | universal | medium | identical (lab) | tool docs |
| DCSync / directory replication abuse | credential replication from DC | T1003.006 | domain compromise finalization | Windows | documented (many) | universal | very high | identical (lab AD) | tool docs |
| Hashpass/pass-the-hash/pass-the-ticket | alternate credential use | T1550.002, T1550.003 | credential reuse | cross | universal | universal | high | identical (lab) | tool docs |
| ACL/delegation abuse tooling (e.g. autoblood-class) | AD ACL path automation | T1484 | trust-graph abuse | cross | documented (R11 lessons) | common | very high | identical (lab AD) | research, R11 |

**C2 frameworks**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Cobalt Strike | full-spectrum commercial C2: profiles, malleable configs, team servers | T1071, T1090, T1568 | C2 + post framework | cross | stolen/pirated by virtually every major group (APT28: R11; FIN7: R12) | commercial license, universal | very high | identical (lab) | vendor, reports |
| Sliver | modern open-source C2 (Go) | T1071, T1090 | C2 | cross | documented (APT: R11) | universal | very high | identical (lab) | tool docs, R11 |
| Mythic / Havoc / Covenant / Brute Ratel / PoshC2 / Empire-class | alternative C2 frameworks | T1071, T1090 | C2 variety | cross | mixed documented use | common | high | identical (lab) | tool docs |
| Metasploit meterpreter | payload channel + post | T1071 | framework C2 | cross | common | universal | high | identical (lab) | tool docs |
| Residential-proxy + VPS + domain stacks | C2 transport concealment | T1090.002, T1090.003, T1571 | channel camouflage | infra | documented (APT29, APT28: R11) | common | high | owned infra only | R11, vendor reports |
| Domain fronting / CDN fronting (concept) | hiding true C2 endpoint behind shared infra | T1090.004 | fronting | infra | documented historically | rare, policy-sensitive | high | research-only classification | vendor research |
| DoH/tunneling (concept: T1572) | protocol tunneling through allowed channels | T1572 | tunneling | cross | documented | common | high | lab | ATT&CK |

**Network assessment / adversary emulation / research**

| Tool | Capability | ATT&CK | Role | Platform | Threat usage | Red-team usage | Level | Safe-lab equivalent | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Callee-less network scanners (nmap-class above) | — | — | — | — | — | — | — | — | — |
| CALDERA | adversary emulation platform, planning/agent loops | T1059, T1021, T1110, T1218 (emulated) | emulation engine | cross | N/A (defender-side) | universal | high | identical | MITRE |
| Atomic Red Team | tiny ATT&CK tests | per-test | control validation | cross | N/A | universal | low | identical | GitHub |
| AttackIQ / commercial BAS | continuous control testing | per-scenario | control testing | cross | N/A | enterprise | medium | subscription/lab | vendor |
| Atomic/Nuclei/CVE recon fusion (concept) | intelligence→check loop | T1595.002 | continuous vuln awareness | cross | universal | common | high | E2 feed design (roadmap) | R9 |
| Sysmon/EDR telemetry + YARA/Sigma | defensive analysis, detection engineering (dual-use) | N/A (blue) | understanding the blue side | cross | both sides | universal | medium | identical | tool docs |
| Jamf/Intune/MDM admin tooling | device fleet control (abuse potential: R14 wiper case) | T1484-class, device control | fleet reach | cross | documented (Handala/Intune: R14) | N/A (defense) | high | fixture (fake fleet) | R14, vendor |

### 4.3 Arsenal classification rules

```text
threat-actor tooling        used as-documented by a named group (cite the report)
legitimate red-team tooling licensed/professional use, same tool different intent
dual-use                     nature depends entirely on authorization (majority)
adversary-emulation          CALDERA/Atomic/CS profiles — built to *reproduce* threat behavior
research tooling             Ghidra/angr/Semgrep — capability sits in the analyst, not the tool
destructive tooling          represented ONLY behaviorally in §15 — never as an operable entry
```

The arsenal is deliberately modeled as *capability implementations*, never as a
"what to run against X" guide: every entry declares its prerequisites, its
evidence source, and its safe-lab equivalent (§20 answers the question "what
decision does this tool enable").

---

## 6. OPERATOR BRAIN

Cognitive architecture — ten components.

### 5.1 Perception

What the operator observes: raw signals from passive OSINT, active probing,
response artifacts, timing behavior, error strings, certificate transparency,
code repositories, employee-facing surfaces. Perception is lossy and biased — it
records *observed* vs *inferred* separately; the blueprint treats observation
provenance as first-class (§8 evidence provenance).

### 5.2 World Model

What the operator believes about the environment: an uncertain, versioned graph
of assets, identities, trust, controls, and unknowns (§8). Every claim carries
`(value, confidence, provenance, last-observed, expiry)`. Unknowns are explicit
nodes — a capable operator models *what it does not know* and prices that in.

### 5.3 Hypothesis Engine

What explanations it considers: "this service is a legacy SSH gateway with shared
creds", "this org uses one IdP for all SaaS", "this segment is flat". Hypotheses
have priors, candidate evidence, and info-gain-ranked tests. Refuted hypotheses
are retained (negative knowledge prevents revisiting dead paths).

### 5.4 Strategy Engine

Which attack paths it considers: generates candidate paths over the attack-path
graph (§8), scores on (probability of success × value − detection risk × cost),
keeps top-k, re-scores on every belief update. Strategy has an explicit *depth
budget* and a *dormancy posture* (speed-vs-stealth, §7).

### 5.5 Capability Selector

Which capability can advance the mission: given target characteristics, current
access, evidence, confidence, failure history, available tools, authorization,
time/rate budgets, detection risk, expected information gain — returns ranked
capability options (§20 and §21 define the selection function). Failure memory is an
input, not an afterthought.

### 5.6 Execution Manager

How actions are coordinated: preconditions → authorization gate → action →
receipt → artifact capture. Sequencing, parallelism limits, rollback/recovery
points, kill-switch, and per-action scope checks. In evaluation systems this is
the broker/ActionReceipt layer; in a human crew it is the operator's checklist.

### 5.7 Evidence Engine

How results affect beliefs: converts execution output into claims with
provenance, confidence, and machine-checkable receipts; updates the world model;
flags divergence between predicted and observed outcome (the trigger for
replanning). Evidence quality is a graded property (receipt-backed > log-backed
> narrative).

### 5.8 Failure Memory

How failed actions influence future decisions: a keyed store
`(capability, target-class, failure-class)` of attempts and their taxonomies
(§13). Retryable classes get retried under changed conditions; structural classes
(patched vuln, wrong topology hypothesis) suppress the path, not just the action.

### 5.9 Replanning Engine

How strategy changes when assumptions fail: threshold-triggered, not
every-step-triggered. Three escalation levels — adjust parameters (same path),
switch path (same strategy), switch strategy (new hypothesis about the
environment). Abandonment is a feature: sunk-cost continuation is the most
common documented operator failure (R13 OPSEC taxonomy).

### 5.10 Long-Term Memory

How knowledge persists between operations: target profiles, control baseline
fingerprints, "this org's IR responds within 24h", technique effectiveness
statistics, tool reliability notes. Stored with the same provenance discipline as
live evidence. For evaluation systems, this is the rectifier/after-action store;
for crews, it is tradecraft lore (R12: Scattered Spider's playbooks were
explicitly shared across operations — memory transfer between operators).

---

## 7. ADVERSARIAL DECISION LOOP

```text
Observe
  ↓
Interpret
  ↓
Generate hypotheses
  ↓
Enumerate attack paths
  ↓
Estimate opportunity
  ↓
Select strategy
  ↓
Select capability
  ↓
Execute
  ↓
Collect evidence
  ↓
Evaluate result
  ↓
Update beliefs
  ↓
Learn from failure
  ↓
Replan
```

| Stage | Inputs | Outputs | State touched | Uncertainty handled | Failure modes | Handoff to next |
|---|---|---|---|---|---|---|
| Observe | sensor feeds (OSINT, probes, telemetry) | raw observations + provenance | perception buffer | noisy/ambiguous signals | incomplete coverage, poisoning, deception | interpretation-ready observations |
| Interpret | raw observations | classified/normalized claims | world model | ambiguity resolution; observed vs inferred flags | misfingerprinting, stale data | claims with confidence |
| Generate hypotheses | claims, world model | ranked candidate explanations | hypothesis set | prior assignment, calibration | fixation on first hypothesis; anchoring | hypotheses with test designs |
| Enumerate attack paths | hypotheses + graph | candidate paths | attack-path graph | unknown edges = possible edges | combinatorial blowup; missing edges | path set with edge confidence |
| Estimate opportunity | paths, budgets, detection surface | scored paths (value, P(success), cost, risk) | strategy model | P(success) estimation error | overconfidence, ignored cost | ordered path ranking |
| Select strategy | scored paths, posture, objectives | chosen strategy + depth budget | campaign strategy | exploration vs exploitation tradeoff | greedily taking highest-score path only | strategy + constraints |
| Select capability | strategy step, arsenal, budgets, failure memory | ranked capability options | selector state | capability reliability uncertainty | tool-driven plans (choosing tool before path) | capability + preconditions |
| Execute | capability + preconditions + authz | action, artifacts, receipt | execution state, receipts | preconditions may be wrong | partial execution; side effects | artifacts + exit status |
| Collect evidence | artifacts, environment signals | evidence records, provenance | evidence ledger | artifact ambiguity | noisy logs; false positives | evidence set |
| Evaluate result | evidence, expected outcome | verdict (match/diverge) | evaluation state | verdict uncertainty | premature success claim | divergence signal |
| Update beliefs | verdict, evidence | world-model updates, confidence deltas | world model | Bayesian update over claims | confirmation bias; slow updating | updated model |
| Learn from failure | divergences, failure evidence | failure-class records | failure memory | classifying ambiguous failures | blaming the tool for a hypothesis error | class + strategy impact |
| Replan | failure classes, updated model, budgets | parameter/path/strategy change | strategy model | knowing when to abandon | sunk-cost continuation; thrashing | new strategy → loop |

Design requirements for a reasoning architecture (translation of the loop):

1. The loop is a **state machine with explicit handoff contracts** — each stage's
   output schema is the next stage's input schema.
2. **Belief update must be able to reach the strategy stage directly** — a
   single surprising observation can invalidate a path (a sudden defender-
   response event, deception artifacts, or simply "port closed that was open").
3. **Uncertainty is never silently discarded** — confidence deltas flow forward;
   downstream stages either use them or explicitly ignore them (and that
   ignoring is itself auditable).
4. **Failure classification precedes replanning** — action failed ≠ path failed
   ≠ hypothesis failed (§13).
5. **Stealth-vs-speed is a first-class parameter**, not an emergent property
   (documented tradeoff in every APT-vs-cybercrime comparison: R11 vs R12).

---

## 8. ATTACK-PATH GRAPH

```text
Asset
  ↓
Observation
  ↓
Weakness
  ↓
Technique
  ↓
Capability
  ↓
Access
  ↓
Privilege
  ↓
Trust relationship
  ↓
Next asset
  ↓
Objective
```

### 7.1 Node types

`Asset` (host, service, cloud resource, SaaS app, network segment, human) ·
`Identity` (user, service account, admin) · `Credential` (password class,
ticket, key, token, session) · `Vulnerability` (CVE, misconfig, design flaw) ·
`Weakness` (pre-CVE class observation) · `Technique` (ATT&CK-mapped) ·
`Capability` (operator tool family) · `Access` (foothold instance) ·
`Privilege` (local admin, domain tier, cloud role, tenant admin) ·
`Trust relationship` (ACL, federation, conditional-access grant, VPN trust,
vendor link) · `Session` (replayable artifacts) · `Security control` (EDR, WAF,
MFA policy, segmentation — nodes too, because paths must route *around* or
*through* them) · `Objective` (scoped outcome node).

### 7.2 Edge types

`access` (can reach) · `authenticates-to` · `trusts` (delegation, ACL, federation)
· `depends-on` (technical dependency) · `exploitable-by` (weakness→technique,
weighted by confidence) · `privilege-grants` · `lateral-movement-capable` ·
`data-flows-to` · `observed-by` (control→asset: needed for detection modeling) ·
`reached-via` (evidence-backed vs inferred edges).

Every edge carries `(confidence, provenance, observed_at, expires_at, detection_risk)`.

### 7.3 Search & scoring (what state Raphael must maintain)

To reason across dozens/hundreds of paths, the system maintains:

* **The graph itself**, append-only per observation, with explicit unknown-edge
  markers (frontier).
* **Per-path score vectors** (not scalar): `⟨P(success), objective-value,
  action-cost, time-cost, detection-risk, information-gain⟩`. Scalarization only
  at selection time with a posture-dependent weighting (stealth posture raises
  detection-risk weight).
* **Path set with beam pruning** — top-k paths plus one random exploration path;
  keeps search tractable at 100+ node graphs.
* **Bayesian belief updates** — an observation updates *edge weights globally*,
  not just the path where it landed (finding MFA everywhere kills
  credential-reuse edges everywhere).
* **Hypothesis overlay** — candidate edges from untested hypotheses live in a
  *shadow layer*; promotion to the real graph requires evidence (prevents
  hallucinated reachability from polluting planning).
* **Dead-end detection** — a node whose all outgoing edges are (a) failed,
  (b) blocked by control, (c) out-of-scope, (d) cost-prohibitive, is marked
  `dead-end` with reason; downstream search never re-expands it except on
  belief change (new edge appears).
* **Alternative-path generation** — k-shortest-path plus edge-substitution
  search over the *unfailed* subgraph; plus "same-objective via different
  asset-class" diversions (identity path when network path dies).
* **Evidence provenance ledger** — every promoted edge cites the receipt/
  artifact that proved it; replayable.
* **Causal reasoning hooks** — distinguishing `necessary` (edge must exist for
  observed effect) from `sufficient` (edge alone enables next step); used to
  avoid correlational overreach ("port 8080 open ⇒ path exists" is the classic
  false positive).

Research references: attack-path graph literature (attack graphs of the
Ammann–Noel–Jajodia family), Bayesian network inference for attack graphs,
hypothesis-graph planning (STRIPS/PDDL planning as graph search), and the
strategy-selector design already in the Raphael roadmap (E1.5a held-out suite).

---

## 9. CAMPAIGN ARCHITECTURE

An operation is a long-running campaign, not a command sequence.

```text
Campaign
 ├── Objective            (scoped outcome, operator-defined)
 ├── Target Model         (world model subset for this campaign)
 ├── Attack Paths         (scored set, current + shadow layer)
 ├── Current Access       (footholds, privileges, sessions — live inventory)
 ├── Known Assets         (confirmed)
 ├── Unknowns             (explicit frontier)
 ├── Capabilities         (available arsenal subset + readiness state)
 ├── Infrastructure       (campaign-owned: C2, redirects, staging, domains)
 ├── Evidence             (ledger + receipts)
 ├── Failures             (failure memory, campaign-scoped)
 ├── Hypotheses           (active, refuted, dormant)
 ├── Constraints          (authorization, time, rate, detection budget, ethics)
 └── Current Strategy     (posture, depth budget, dormancy, next actions)
```

### 8.1 Campaign state transitions

```text
INIT → RECON → SURFACE_MAPPING → HYPOTHESIS_TESTING → INITIAL_ACCESS
     → EXPANSION (discovery/credential/lateral)
     → OBJECTIVE_ADVANCEMENT → OBJ_ACHIEVED
     any state ──detection_event──→ DEGRADED (dormancy/retreat/rotate)
     any state ──budget_exhausted──→ PAUSE / TERMINATE
     DEGRADED ──reassess──→ prior state or TERMINATE
     PAUSE ──resume──→ state restored from durable checkpoint
```

Rules:

* **Transitions are belief-driven, not script-driven** — entering
  OBJECTIVE_ADVANCEMENT requires evidenced access, not just elapsed time.
* **DORMANT is a first-class state** — documented APT behavior (weeks of
  silence after initial access; R11 APT29, R18-equivalent literature); in
  evaluation systems, simulated as a re-planning delay, never as real waiting
  on unauthorized targets.
* **All state is durable and resumable** — crash/restart must preserve
  campaign continuity (recovery is a metric: resume with zero evidence loss).
* **Constraints are campaign members** — authorization scope, time budget, rate
  budget, and detection budget live *inside* the campaign object, so any planner
  step can be checked against them mechanically (fail-closed).

---

## 10. INFRASTRUCTURE MODEL

Architecture and tradecraft — no deployment recipes.

```text
Campaign Infrastructure
 ├── Command & Control      operator-side controllers (lab instances)
 │     ├── controllers (where decisions/agents live)
 │     ├── listeners (where implants/callbacks land)
 │     └── staging (payload/artifact hosting, isolated)
 ├── Redirectors            hop hosts between target and controller
 ├── Domain infrastructure  campaign domains, staging sites
 ├── Proxy layers           VPS → residential-class → tor-class separation
 ├── Traffic separation     target-facing vs operator-facing must never share
 │                          egress (the #1 infrastructure deanonymizer)
 ├── Rotation capability    replaceable components with state handover
 ├── Communication channels operator-side (chat/automation), separate identity
 └── Operational segmentation  per-objective isolation; compromise of one
                                campaign must not expose another
```

Tradecraft principles (documented across R11/R14/R16 infrastructure sections):

1. **Separation of planes**: target-facing traffic, controller traffic, and
   operator management traffic are distinct systems. Failure to separate them is
   how crews get mapped end-to-end (SEA → HBGary-style pivoting; Sabu's
   exposure in R10 — one console, cross-campaign linkage).
2. **Redirector depth is proportional to campaign duration**: long-horizon APT
   infra is multi-hop and burnable; opportunistic crews share one VPS.
3. **Rotation with state handover**: rotating a component without losing
   operator sessions requires state migration (beacon configs, domain
   inventory) — modeled as a campaign operation with receipts.
4. **Trust but verify**: redirectors are semi-trusted; controller assumes any
   redirector may be seized (hold minimal state on it).
5. **Infrastructure reuse = correlation surface**: reusing a domain/ACROSS
   campaigns links them for defenders (R13 OPSEC taxonomy).
6. **In evaluation systems**: all infrastructure is lab-owned or simulated;
   "target-facing" components point at fixtures; rotation is exercised against
   fixture fleets.

---

## 11. OPSEC MODEL

### 10.1 OPSEC concern areas

| Concern | Exposure vector | Documented failure example | Model control |
|---|---|---|---|
| Attribution exposure | tooling fingerprints, language artifacts, working hours | R13/R17 taxonomy: language metadata, reused handles | persona/timing/tool-profile budget |
| Infrastructure exposure | domain/VPS linkage, shared certs, hosting patterns | SEA trusted-chain; Sabu pivot (R10) | per-campaign isolation, rotation records |
| Identity exposure | operator accounts, marketplace handles, chat presence | Lapsus$ arrests via ops-chatter (R12/R16) | identity compartmentalization (modeled, never operated) |
| Behavioral fingerprints | scheduling regularity, burst patterns | R17: AI-generated uniformity as a new fingerprint | timing jitter budgets |
| Logging/telemetry | what the target records of each action | every red-team lesson | per-action detection-risk estimate |
| Detection events | alerts fired, IR triggered | NotPetya-class blast (R12) | detection budget as campaign constraint |
| Infrastructure reuse | cross-campaign correlation | R13 | inventory expiry, no-shared-components rule |
| Tool fingerprints | unique strings/configs in used tools | R17 | tool-variation discipline (research) |
| Communication patterns | operator chat/automation egress correlated with target activity | Sabu (R10) | plane separation (§10) |

### 10.2 OPSEC state model

```text
OPSEC_STATE ∈ { GREEN, WATCH, DEGRADED, COMPROMISED }

GREEN      no observed defensive attention; planned cadence OK
WATCH      suspicious activity noted by target (log spikes, canaries);
           reduce rate, increase jitter, pause active probing
DEGRADED   partial exposure likely (one component burned); prepare rotation
COMPROMISED evidence of IR targeting the operator's infrastructure/persona;
           retreat to dormant posture, rotate, re-plan or terminate
```

Transitions are driven by **defensive-awareness signals** (§12): alert
evidence, deception artifacts, unexpected control behavior, IR time-of-response.
The OPSEC state is an *input to strategy selection* — in WATCH, capability
selection weights detection-risk much higher; in COMPROMISED, active exploitation
capabilities are suppressed entirely. Evaluation systems reproduce this against
fixture blue teams (R14 range scenarios).

---

## 12. DEFENSIVE-AWARENESS MODEL

```text
Target
   ↓
Security Controls
   ↓
Detection Surface
   ↓
Defender Response
   ↓
Adversary Observation
   ↓
Strategy Adjustment
```

Represented entities: `EDR` (visibility, tamper-resistance class) · `SIEM` (log
correlation, alert latency) · `IDS/IPS` (signature vs anomaly posture) ·
`authentication monitoring` (impossible-travel, spray detection) · `cloud
monitoring` (control-plane audit, CSPM) · `network segmentation` (lateral
barriers) · `honeypots/deception` (must be *detectable as unknown-value* nodes,
never treated as real assets — false-realism trap) · `incident response`
(response-time distribution, containment patterns) · `security-team behavior`
(on-call cadence, escalation habits).

Model requirements:

1. **Per-control observability estimate**: for each control, a belief about what
   it sees, with confidence. Used by the strategy engine to estimate detection
   risk per action.
2. **Deception handling**: observations that are "too good" (an admin share with
   everything, a perfectly-titled credential file) create a *deception
   hypothesis* with real probability mass, not an immediate path. Distinguishing
   fact → assessment → inference applies here too.
3. **Response modeling**: IR response time and containment style change which
   paths are viable (fast-containment environments favor quick objectives;
   slow-response favors persistence modeling — in lab, these are fixture
   timers).
4. **The defender is an agent with beliefs too** — classical red-vs-blue
   modeling: the operator's model includes "what the blue team currently thinks"
   (compromised or not), because that drives blue's next action (§12 loop).

---

## 13. FAILURE AND ADAPTATION

Formal failure taxonomy — every failure passes the same pipeline:

```text
Failure
 → Classification
 → Evidence
 → Belief Update
 → Strategy Impact
 → Retry Decision
 → Alternative Path
```

| Failure class | What actually happened | Belief update | Strategy impact | Retry decision | Alternative path |
|---|---|---|---|---|---|
| Reconnaissance failure | surface evidence unreachable/absent | target model: assumption X unsupported | shrink/grow scope hypothesis | retry only with different source | passive OSINT vs active probing switch |
| False positive | observation classified wrongly (port/banner misread) | downgrade sensor reliability for that class | deprioritize that signal source | re-verify with second method | independent confirmation path |
| Incorrect hypothesis | tested hypothesis refuted | hypothesis → refuted (retained as negative knowledge) | path cascade invalidated | no retry of the path | sibling hypothesis selection |
| Exploit failure | primitive did not produce intended effect | vulnerability edge confidence → low; environment version assumption re-checked | path marked dead unless precondition failure | retry iff failure class = environmental (version/waf), with changed parameters | different technique on same weakness, or different weakness |
| Credential failure | auth rejected | credential edge invalid; spray/exposure hypotheses updated | credential-reuse path dead | retry only if class = rate-limit (budget-aware) | different identity source or different auth surface |
| Privilege failure | elevation blocked | privilege edge requires unmodeled control | local plan downgraded | no (structural) | trust-relationship re-analysis |
| Lateral-movement failure | remote exec/service refused | segmentation belief strengthened; topology graph updated | segment-isolated strategy | no (structural) | alternative protocol/segment path |
| C2 failure | channel blocked/degraded | detection-surface estimate raised | OPSEC state → WATCH/DEGRADED; rotate | with changed channel (rotation is a strategy, not a retry) | alternate channel class |
| Detection event | alert/EDR/IR response observed | detection-risk beliefs raised globally for similar actions | posture shift, rate cut, dormancy consideration | no active retry while WATCH+ | lower-signature technique class |
| Environmental mismatch | wrong version/OS/config assumption | world-model attribute corrected | affected paths rescanned | yes (corrected assumption) | any path surviving the correction |
| Tool failure | tool crashed/errored without signal about target | no target belief change (tool reliability down) | capability weight down for that tool | yes, different tool for same capability | capability substitution (§20) |
| Misleading evidence | evidence contradicted by later, stronger evidence | source reliability downgraded; claim reverted | re-evaluate paths built on it | re-derive from primary source | provenance-diverse re-observation |
| Deception/honeypot | suspicious asset was planted | deception-control belief added; asset class re-tagged | avoid or treat as monitored | never engage as real | genuine-asset re-scan |
| Unexpected infrastructure | target architecture differs (CDN, HA, third-party) | asset ownership/dependency edges updated | paths crossing that boundary re-scored | conditional | alternate entry asset |

**Integration contract** (how a rectifier/failure-memory system consumes this):

1. Every failure produces a **failure class** written to the keyed store
   `(capability, target-class, failure-class)` — matches the Raphael rectifier
   design (E1) and the `failure_class` field already seeded from its error
   diagnoser vocabulary.
2. **Structural classes suppress paths; environmental classes re-score them;
   transient classes allow bounded retry.** The three retry dispositions are
   computed from the class, never improvised per-execution.
3. Belief updates are **recorded on the world model**, not only in the failure
   log — a failure that changed no belief was a wasted execution and is itself a
   measurable anti-pattern (unnecessary-action metric, §22).
4. **Deception is a first-class failure class** — the single most important
   adaptation lesson from documented defense (honeypots, canary tokens, bait
   shares: §12).
5. Repeat-failure rate (same key, same class, twice) is a hard metric — a
   capable operator's failure memory makes it trend to zero.

---

## 14. CAPABILITY MATURITY

Adversarial capability ladder. Higher tiers add *reasoning and state depth*, not
destructive potential.

### A — Discovery

* **Capabilities**: passive/active recon, surface enumeration, fingerprinting,
  vulnerability identification.
* **Knowledge**: ATT&CK basics, platform fundamentals, OSINT methodology.
* **Reasoning**: evidence → finding; single-path planning.
* **Infrastructure**: none (or one scanner host).
* **State**: per-task; no cross-operation memory.
* **Evaluation**: discovery coverage vs ground truth; false-positive rate.

### B — Validation

* **Capabilities**: controlled exploitation of identified weaknesses, safe
  verification, post-exploitation *demonstration* without persistence.
* **Knowledge**: exploit preconditions, lab safety, evidence capture.
* **Reasoning**: hypothesis → test → consequence loop (§7); failed-path
  abandonment.
* **Infrastructure**: controlled listener/staging (lab-owned).
* **State**: per-engagement.
* **Evaluation**: validated findings / attempted validations; every claim
  receipt-backed; zero scope creep.

### C — Enterprise Compromise

* **Capabilities**: credential access, AD/identity abuse, privilege escalation,
  lateral movement across a modeled enterprise.
* **Knowledge**: Kerberos/ACL/delegation, IdP/cloud control planes, tiering.
* **Reasoning**: attack-path graph search (§8), multi-path evaluation, dead-end
  detection.
* **Infrastructure**: relay/listener separation (lab).
* **State**: enterprise model + current-access inventory.
* **Evaluation**: path quality vs red-team ground truth; lateral coverage;
  unnecessary-action rate.

### D — Campaign Operations

* **Capabilities**: multi-stage attack paths, persistent mission state,
  collection staging, C2 maintenance across sessions.
* **Knowledge**: OPSEC, IR behavior, campaign hygiene, dormancy concepts.
* **Reasoning**: strategy engine with posture/stealth budgets; long-horizon
  replanning (§9); OPSEC state machine (§11).
* **Infrastructure**: redirectors + plane separation (§10) — lab fleet.
* **State**: durable, resumable campaign object; failure memory across runs.
* **Evaluation**: long-horizon consistency; resume-after-interruption with zero
  evidence loss; defender-awareness fidelity.

### E — Advanced Adversarial Operations

* **Capabilities**: adaptive strategy under active defense, C2 under pressure,
  evasion *research* (behavioral modeling), multi-week planning.
* **Knowledge**: control internals (EDR/SIEM behavior classes), deception
  catalogs, supply-chain surface, container/cloud depth.
* **Reasoning**: Bayesian belief updates over control models; deception
  recognition; capability switching mid-campaign; exploration/exploitation
  management.
* **Infrastructure**: full campaign infra lifecycle incl. rotation with state
  handover.
* **State**: world model + defender model + campaign model simultaneously.
* **Evaluation**: strategy survival vs adaptive blue; defender-model accuracy;
  replanning quality (held-out scenarios).

### F — Multi-Domain Adversarial Operations

* **Capabilities**: coordinated reasoning across identity + cloud + SaaS + edge
  + web/API + enterprise simultaneously — cross-domain attack paths.
* **Knowledge**: all prior domains plus cross-domain trust semantics (federation,
  conditional access, third-party integrations).
* **Reasoning**: heterogeneous graph (§8 with cloud/SaaS/edge node types);
  domain-agnostic verbs (the tool/capability abstraction).
* **Infrastructure**: multi-plane, multi-domain fixtures.
* **State**: unified cross-domain target model.
* **Evaluation**: cross-domain path discovery; no domain is a blind spot.

### G — Research-Grade Adversarial Operations

* **Capabilities**: OT/ICS simulation paths, supply-chain reasoning, mobile
  ecosystems, novel-weakness analysis (research on authorized code), campaign
  design against multi-environment targets.
* **Knowledge**: process-control safety models, build/release trust, mobile
  platform security, vulnerability research methodology.
* **Reasoning**: causal reasoning under high uncertainty; research-grade
  hypothesis formation (a new weakness class, not a known CVE); adversarial
  self-evaluation.
* **State**: multi-environment, multi-campaign; organizational (long-term
  memory across operations, §6.10).
* **Evaluation**: capability coverage vs the taxonomy (§4) per domain; Target
  Complexity Invariance — graceful degradation as size/heterogeneity grows.

Acceptance principle: **each tier is certified by objective criteria**
(coverage, evidence quality, reasoning quality, state discipline) — never by the
severity of damage the tier could theoretically cause.

---

## 15. HIGH-CONSEQUENCE CAPABILITY CLASSES

Capabilities whose real-world execution can cause substantial harm exist in this
blueprint **only** as classified knowledge classes — with an explicit safe
functional equivalent that reproduces the *decision-making and evidence* without
creating an operational weapon.

| Capability class | Adversary's capability (behavioral description) | Why an advanced operator possesses it | Technical knowledge required | Evidence of understanding | Safe simulator/lab equivalent |
|---|---|---|---|---|---|
| Disruption / DDoS | availability exhaustion at scale | leverage (hacktivism), extortion pressure, distraction during intrusion | protocol amplification theory, capacity modeling, target-surface math | correct architecture analysis; capacity estimate on fixture; recognition of platform classes (R14) | rate-limited traffic generator against instrumented fixture host; platform catalog as knowledge (R14 botnet taxonomy) |
| Destructive action | data/availability destruction | coercion, cover, geopolitical signaling | filesystem/volume semantics, recovery dependencies | explaining destruction mechanics + recovery preconditions analytically | destructive *function call* on disposable fixture dataset with receipts proving intent + blast radius computation, never real payload |
| Ransomware-like behavior | encryption-for-extortion + leak pressure | monetization (criminal class only) | crypto, backup/IR evasion theory | modeling stages: access→lateral→collection→encryption-sim | "encryption" against fixture with test keys + shadowed deletion *simulated*; leak-site modeling as knowledge only; NO extortion playbooks |
| Credential theft (bulk) | large-scale secret harvesting | persistence, monetization, access brokering | OS credential storage, token lifetimes | demonstrating retrieval on lab identities only | fixture identities/credentials; canary credentials to measure acquisition; never real corp/user creds |
| Large-scale phishing | mass target deception | initial access at volume, MFA defeat | pretext design, deliverability theory, IdP flow abuse | campaign design artifact + fixture results | consenting-user simulation + fixture mail infra; templates evaluated by blue fixture, never sent to real people |
| Kernel/driver-level evasion | disabling control visibility via kernel/driver primitives | evading EDR during long operations | driver signing, kernel API surface, EDR architecture | behavioral analysis of documented cases (BYOVD class, R5) | model + detect against fixture telemetry: write detections for the behavior class; BYOVD policy gate (already non-negotiable in Raphael) |
| Destructive OT actions | process/manufacturing/safety impact | coercive/kinetic objectives (state actors) | ICS protocols, process dynamics, safety interlocks | simulating process consequences analytically on a digital twin | ICS digital-twin fixtures (HVAC/plant simulators); safety-interlock bypass = forbidden; modeled as detection/emulation scenario |
| Mass exploitation | wormable/automated exploitation at internet scale | scale economics (criminal) | vulnerability class mechanics, propagation theory | capacity analysis; recognition of n-day-to-worm pipelines (R15-16) | fixture fleet in lab network segment; automation runs only against enumerated lab assets; rate ceilings enforced |
| Botnet operation | durable distributed victim infrastructure | DDoS capacity, proxying, monetization | implant lifecycle, peer/p2p architecture, tasking | architecture modeling + fixture multi-node fleet | 5-node fixture botnet (containers) with tasking receipts; real botnet operation is out of scope entirely |

Rule: for each class, **understanding is demonstrated by analysis + fixture
behavior, never by production-capable artifacts**. The blueprint tracks these
capabilities as *knowledge* and *simulation-class* entries in the capability
registry; autonomous execution classes stay at simulation/fixture/research level
permanently (§23 "not appropriate for autonomous execution").

---

## 16. HACKTIVIST OPERATOR PROFILE

Distinguishes historical vs current documented behavior — not one homogenous
capability profile.

| Axis | Historical (2010-2016 era) | Current documented (2022-2026) |
|---|---|---|
| Representative groups | Anonymous/Op* (LOIC swarms), LulzSec, SEA, TeaMp0isoN | NoName057(16), Z-Pentest, Sector16, Handala/Stryker, KillNet-ecosystem |
| DDoS | volunteer LOIC/DDoS tooling, botnet rentals, layer-7 rotation | platform-complex (VNC/OT-abuse, NTP/DNS amplification classes), sustained multi-week #Op campaigns (R14) |
| Web defacement | mass SQLi via automated scanners (sqlmap-class), CMS vulns | persists but secondary; smaller surface (WAF maturity) |
| Credential abuse | exposed-credential replay, simple spray | OAuth/identity-level abuse where skills allow; mostly opportunistic reuse |
| Exposed-service exploitation | basic RDP/SSH/VNC open to internet | **current signature**: VNC/remote-access + unauthenticated OT exposure (CISA AA25-343A class: R14) |
| OT/ICS targeting | very rare (Vulnhub-class curiosity) | *threat rhetoric* vs demonstrated depth — mostly disruption, not process manipulation (assess claims carefully) |
| Hack-and-leak | SEA (trust-chain hijack, Taboola/Forbes-class), Ops data-leak | data-leak channels via Telegram publication; limited exfiltration depth |
| Volunteer infrastructure | forum coordination, shared tools | Telegram bot/tasking channels; *gamified* (leaderboards, crypto rewards: R14) |
| Motivation | ideology, publicity, protest | ideology + geo-political alignment + payment (hybrid mercenary streak) |
| OPSEC | notoriously weak (Sabu case: R10) | still weak but improved: proxy rotation, regional coordination; arrests still documented |
| Notable failure patterns | hubris (LulzSec 50-day overreach), trusted-channel compromise (Sabu), founder attribution (HBGary) | tool/tooling reuse correlation; operational chatter metadata (R16: Scattered Spider arrests) |

**Capability vs tools**: hacktivist capability is characterized by *breadth of
low-to-mid sophistication* and *logistics* (coordination at scale) rather than
depth. Raphael-relevant understanding: the *pattern* (which low-hanging surfaces
get weaponized by crowds), the *platform economics* (botnet-rental/DDoS-as-
service catalog from R14 as knowledge), and the *amplification path* from open
service to operational disruption.

**Per-capability determination** (the 5 questions): what the capability does ·
which groups documented it · current relevance · legitimate red-team/lab
equivalent · model / simulate / integrate decision — this maps directly onto the
`Model class` column of §4 and the registry of §21. Destructive capabilities are
researched as **behavior and architecture only** (per §15).

---

## 17. CYBERCRIME OPERATOR PROFILE

Capability modeling only — monetization is described strictly as *incentive
structure*, never as procedure.

* **Initial access brokers**: marketplaces where access (VPN, RDP, phishing
  footholds) is a commodity — capability = obtaining and *validating* access
  reliably (validation is the skill; sales are not modeled).
* **Credential markets**: where stolen credential classes circulate; relevant
  capability = acquisition + *testing* against fixtures, and recognizing
  credential classes as an analyst.
* **Identity compromise**: password spray, token/session abuse, MFA
  push-fatigue, help-desk social engineering (Scattered Spider documented
  pattern: R12/R16) — capability = the human-system interface, not any specific
  script.
* **SaaS compromise**: OAuth consent grants, integration abuse, data-staging in
  cloud storage (ShinyHunters 2025 OAuth year: R16).
* **Affiliate models**: ransomware-as-service structure — architecturally
  notable as *division of labor* (developer/affiliate/access-broker): a
  multi-role operator model, directly relevant to §3's separation of
  reasoning vs capability.
* **Persistence + lateral movement**: documented preference for speed-to-impact
  over stealth (contrast §18): hands-on-keyboard rapid movement, living-off-
  land binaries.
* **Ransomware ecosystems**: covered as recognition + behavioral modeling only
  (§15, §16-class rule) — the blueprint models *stages and evidence*, never
  extortion tradecraft.
* **Decision characteristics**: ROI-driven, opportunity-cost aware, detection
  as *cost* not *threat*, heavy opportunistic pivoting, tool-driven planning
  (known-exploit-first).

Separation rule: **capability modeling (which access paths, which identity
techniques, which lateral patterns) is in scope; monetization mechanics (pricing,
negotiation, laundering) are permanently out of scope** — out of scope by
construction, not by omission.

---

## 18. NATION-STATE / APT OPERATOR PROFILE

Documented behavior focus (sources: R11 + R15 vendor reporting).

* **Long-horizon reconnaissance**: months-to-years passive collection before
  contact; organizational mapping ahead of technical mapping (SolarWinds-class
  prep: R11).
* **Supply-chain access**: trusted-relationship and vendor-build compromise
  preferred over direct attack (SUNBURST distribution, npm/package classes:
  R11/R15) — access *sublet through infrastructure the defender trusts*.
* **Identity compromise**: token/federation abuse, password-less & MFA
  bypass via stolen-session and app-password classes; identity-plane as the
  primary persistence surface (R15: password-sprays→OAuth, NOBELIUM-class).
* **Stealth**: long dwell, minimal tooling on disk, use of native admin tooling
  (Living-off-the-land), careful log-awareness, environment-aware opsec
  (fileless wmi, event logs cleared rarely — they prefer *not* touching).
* **Persistence**: multiple redundant persistence channels (Scheduled tasks +
  services + registry + identity-level: mailbox rules, OAuth grants).
* **Infrastructure depth**: multi-tier redirectors, aged domains, campaign-
  dedicated infra with strict plane separation (§10), heavy use of trusted
  cloud/SaaS fronting (UNC3886: appliances; NOBELIUM: cloud infra).
* **Operational compartmentalization**: strict OPSEC, operator discipline,
  regional working-hour patterns as the rare fingerprint (R17: behavioral
  fingerprints).
* **Intelligence collection**: objectives are *collection-first* — impact
  (wiper/disclosure) is a secondary, separately-authorized act (destructive
  cases are the minority of operations).
* **Advanced C2**: trusted-channel blending (cloud/SaaS channels the defender
  already allows), dead-drop resolution, infrequent beaconing.
* **Adaptive campaign management**: replan on exposure; abandon compromised
  tooling entirely rather than debug it (tool-burning is a documented
  sophistication marker).

APT-relevant reasoning traits for Raphael: *patience as strategy* (dormancy is a
decision), *evidence discipline* (never act on unverified reachability),
*compartmentalization* (infrastructure and identity separation), *assumption
testing before commitment* (R11 lessons).

---

## 19. CROSS-ACTOR SYNTHESIS

| Axis | Hacktivist | Cybercrime | APT | Professional Red Team |
|---|---|---|---|---|
| Reconnaissance | opportunistic, scanner-driven | opportunistic + access-market intel | deep, long-horizon, multi-source | scoped, rules-of-engagement-driven |
| Sophistication | low-mid (breadth) | mid (tool-using) | high (custom + depth) | mid-high (but breadth-capped by scope) |
| Speed | burst (hours-days) | fast (days-weeks) | slow (months-years) | engagement-window-bounded |
| Stealth | low | medium (cost-aware) | very high (defense-aware) | very high (measured against blue) |
| Infrastructure | rented/shared/volunteer | shared VPS/panels | dedicated, aged, multi-tier | commercial/red-team infrastructure |
| Persistence | rarely durable | rapid re-entry (stolen access) | redundant long-term channels | scope-temporary |
| Identity targeting | opportunistic | heavy (spray, MFA bypass) | core surface (federation, tokens) | heavy (assessment-focused) |
| Exploitation | known/scanner-class | n-day-first | n-day/0-day + supply chain | lab-validated techniques |
| C2 | minimal (tool defaults) | panel-based, pragmatic | trusted-channel blending, low-volume | profiled/emulated C2 |
| Objectives | publicity/pressure | monetization (not modeled) | collection/intelligence | proving scoped objectives |
| Operational discipline | weak | moderate | strict | strict by methodology |
| Adaptability | reactive | pivots on opportunity | strategic replanning | replans within engagement rules |

**No "strongest actor" ranking.** Instead — which capabilities and behaviors
Raphael should understand *from each class*:

* **From hacktivism**: low-hanging-surface intelligence (what open services +
  identity gaps enable at scale), platform-economy awareness, the
  coordination/logistics pattern, and claim-skepticism about OT rhetoric.
* **From cybercrime**: speed-optimized path selection, opportunistic pivoting,
  identity-attack pragmatics, tool-reliability priors, and the *division-of-
  labor* model (broker/affiliate/developer as separate capability roles).
* **From APT**: long-horizon state, supply-chain reasoning, stealth-as-
  strategy, infrastructure compartmentalization, defense-aware replanning,
  evidence discipline.
* **From professional red teams**: methodology rigor (scoped hypothesis→test→
  finding loops), reproducibility, reporting/evidence standards, and — most
  importantly — the *authorized* operational pattern Raphael itself must
  embody: objective-driven, receipt-backed, scope-fenced.

The cross-actor view feeds §20: identical capability families (§4) are selected
and sequenced differently per actor class — the *selection policy* differs, the
*capability vocabulary* doesn't. That is precisely the abstraction Raphael's
strategy engine needs: model actor-class priors over the same graph.

---

## 20. TOOL → CAPABILITY → REASONING MAPPING

Three-layer matrix. The research question is **"What decision does the tool
enable?"**, never merely "What command does the tool execute?"

```text
Tool
  ↓
Capability
  ↓
Reasoning Function
```

### 20.1 Mapping (representative)

| Tool (layer 1) | Capability (layer 2) | Reasoning function it enables (layer 3) |
|---|---|---|
| subfinder/amass-class enumeration | attack-surface discovery | "what exists that I did not know about?" → frontier expansion of world model |
| nuclei-class template validation | vulnerability discovery | "is weakness H real on asset A?" → hypothesis test; edge promotion on proof |
| Burp/sqlmap-class web tooling | web/API exploitation | "does the authz boundary hold under transformation?" → boundary-hypothesis testing |
| AD assessment tool (BloodHound-class) | identity/trust discovery | "which privilege paths exist?" → viability ranking over identity graph edges |
| Kerberos abuse tooling (Impacket/Rubeus-class) | credential/identity validation | "is this credential class usable *here*?" → credential-edge test with receipt |
| Cloud assessment tool (Pacu/ScoutSuite-class) | cloud control-plane discovery | "which roles/keys/trust exceed need?" → cloud-graph exposure hypothesis |
| C2 framework (CS/Sliver/Mythic-class) | channel management | "can managed access survive defender response?" → channel-health belief + OPSEC state |
| Credential testing suite | credential access (validation class) | "do these credentials work on reachable services?" → identity hypothesis confirmation |
| Exploitation framework (MSF-class) | exploitation | "does V yield code-exec on A under precondition P?" → exploit-edge confidence update |
| Network scanner (nmap-class) | network assessment | "what is reachable/filtering?" → segmentation hypothesis correction |
| Adversary emulation platform (CALDERA-class) | technique reproduction | "does the control detect technique T?" → defensive-observability belief update |
| Proxy/redirector tooling (§10 class) | infrastructure separation | "can planes be decoupled?" → attribution-risk reduction decision |
| LOLBAS/native-tooling | execution via trusted binaries | "can required effect be reached without novel artifacts?" → detection-risk minimization choice |
| Research tooling (Ghidra/angr/Semgrep-class) | vulnerability analysis | "does this code contain reachable weakness W?" → candidate-vulnerability hypothesis, verified on fixture |

### 20.2 The capability-selection function (conceptual)

For authorized adversarial simulation / penetration testing, given state
`S = {target model, current access, evidence, confidence, failure memory,
authorization scope, time budget, rate budget, detection budget}`, choose the
next capability `c ∈ C`:

```text
score(c) = w1 · ExpectedInformationGain(c | S)        # what will we LEARN
         + w2 · P(advances objective | c, S)          # progress toward scoped goal
         + w3 · EvidenceQuality(c | S)                # will the result be verifiable
         - w4 · DetectionRisk(c | S)                  # blue-team observability
         - w5 · Cost(c)                               # time + rate budget consumed
         - w6 · RepeatPenalty(c, failure_memory)      # this failed here before
         hard constraint: Authorization(c, S) == ALLOWED   # fail-closed
```

Design properties:

1. **Expected information gain is first-class** — before objective progress, a
   capable operator buys *knowledge* (the black-hat decision-process lesson:
   hypothesis testing beats opportunistic exploitation; §7).
2. **Authorization is a hard constraint, not a weight** — nothing outside the
   declared engagement scope is scoreable at all (fail-closed selection).
3. **Failure memory is a negative term, not a veto for transient classes**
   (§13 dispositions: structural classes *do* veto).
4. **Budgets are explicit** — time and rate budgets make capability selection
   finite-horizon; rate budget doubles as stealth control (§11).
5. **The function is posture-conditioned** — stealth posture re-weights
   detection risk up (§14-D/E).
6. **Selection is per-step and re-evaluated every loop** — never a fixed
   multi-step script.

### 20.3 Selection anti-patterns (what capability research warns against)

* **Tool-first planning** (choose tool, then look for somewhere to use it) —
  the inverse of the loop in §7; measurable as high unnecessary-action rate.
* **Ignoring repeat-failure signals** — same tool, same key, same failure.
* **Score-by-damage** — selection weights damage/potential as value: an invalid
  policy in every consuming system (§24 final principle).
* **Authorization-as-weight** — scope violations becoming "acceptable risk"
  under scoring: categorically forbidden.

---

## 21. AUTONOMOUS OPERATOR ARCHITECTURE

```text
                   OPERATOR
                       │
             ┌─────────▼─────────┐
             │ Mission Controller │
             └─────────┬─────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
 Intelligence      Reasoning        Arsenal
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                Strategy Engine
                       │
                       ▼
                Action Planner
                       │
                       ▼
                    Executor
                       │
                       ▼
                    Target
                       │
                       ▼
                   Evidence
                       │
                       └──────→ Memory
```

Subsystem definitions and interfaces:

| Subsystem | Responsibility | Inputs | Outputs | Key invariants |
|---|---|---|---|---|
| **Mission Controller** | owns objective, budgets, authorization scope, state machine (§9) | operator-declared objective + constraints | phase transitions, termination authority | never expands scope; budgets fail-closed |
| **Intelligence** | world model maintenance: observation → belief | observations, evidence records | versioned target model with confidence/provenance | observed vs inferred always distinguished |
| **Reasoning** | hypotheses, attack-path search, opportunity scoring (§7, §8) | target model, failure memory | ranked strategies/paths | hypotheses must be testable; refuted retained |
| **Arsenal** | capability registry (§4, §5, §22-registry) | capability requests | capability + preconditions + risk class | high-consequence classes return simulation-only artifacts (§15) |
| **Strategy Engine** | posture + strategy selection, replanning triggers | ranked paths, OPSEC state, budgets | chosen strategy + depth budget | postures drive weights; no tool-first planning |
| **Action Planner** | strategy step → ordered capability calls with preconditions | strategy, selector function (§20) | execution plan | every action passes authorization gate |
| **Executor** | action dispatch via controlled broker; sequencing; rate control | plan, scope rules | receipts + artifacts + exit status | all actions receipted; fail-closed on scope/rate |
| **Target (Environment)** | lab/fixture environment responding to actions | executed actions | observable effects | fixture realism documented (no false-genuine assets) |
| **Evidence** | provenance-preserving capture, quality grading | artifacts, effects | evidence ledger entries | every claim cites a receipt |
| **Memory** | long-term store: campaign state, failure memory, lessons | evidence, failure records, after-action | retrievable knowledge for next loop/operation | replayable, hash-verified where receipted |

Interface contracts (schema level):

```text
MissionController → StrategyEngine : Campaign{objective, budgets, scope, posture}
StrategyEngine    → ActionPlanner  : Strategy{path, depth_budget, next_hypothesis}
ActionPlanner     → Arsenal        : CapabilityRequest{verb, target_ref, preconditions}
Arsenal           → ActionPlanner  : Capability{interface, risk_class, prerequisites}
ActionPlanner     → Executor       : Action{capability, args, scope_proof, budgets}
Executor          → Evidence       : ActionReceipt{outcome, failure_class?, artifacts}
Evidence          → Intelligence   : Claims{value, confidence, provenance}
Evidence          → Memory         : LedgerEntry{receipt, hash, campaign_ref}
Memory            → Reasoning      : FailureMemory{key, class, disposition} + Lessons
Reasoning         → StrategyEngine : {new_paths, refuted_hypotheses, belief_delta}
StrategyEngine    → MissionController : status{phase, degradation, termination_req}
```

The architecture is deliberately split: **capability → reasoning → authorization
→ execution → evidence** as five separable concerns — so each can be evaluated,
restricted, or replaced independently (this separation is the architectural
thesis of the whole blueprint).

---

## 22. EVALUATION FRAMEWORK

Controlled environments, reproducible scenarios, defense-aware scoring.

| Measure | Definition | How measured |
|---|---|---|
| Discovery coverage | known ground-truth surface found / total | fixture with declared ground truth |
| Hypothesis quality | precision/recall of hypotheses vs fixture reality | refutable-hypothesis ledger scored post-run |
| Attack-path quality | found paths vs red-team reference paths; optimality gap | path set comparison on fixture graph |
| Tool selection fitness | selection-function decisions vs reference policy | replay logged states through both policies |
| Evidence quality | % claims receipt-backed; provenance completeness | evidence audit |
| Failure recovery | correct classification + disposition rate | failure log vs ground-truth classes |
| Replanning quality | post-failure strategy improvement on held-out scenarios | before/after objective progress under same budget |
| Long-horizon consistency | campaign state coherence over N loops (no amnesia, no drift) | state-audit checkpoints |
| Defender awareness | predicted vs actual blue response | blue fixture logs vs stated predictions |
| Capability coverage | exercised capability families / taxonomy (§4) | registry exercise report |
| False-positive rate | claims asserting effects that did not occur | evidence audit vs fixture truth |
| Unnecessary-action rate | actions with zero information gain *and* zero progress | action log classification |
| Target Complexity Invariance | slope of all above across size/heterogeneity ladders | repeated runs at increasing fixture scale |
| Scope discipline | out-of-scope attempts (must be 0; fail-closed gate test) | broker logs, always zero |
| High-consequence safety | any operational (non-simulated) high-consequence action (must be 0) | execution-class audit, always zero |

Rules: scenarios are **versioned fixtures**; runs are **reproducible** (seeded);
the evaluator is **external to the operator** (self-scoring is not scoring —
the operator must not be able to grade its own exam); hard-zero safety metrics
(§22 scope + high-consequence rows) gate every other metric's interpretation.

---

## 23. RESEARCH-TO-RAPHAEL INTERFACE

*(Interface only — Raphael's roadmap is not rewritten here.)*

```text
BLACK_HAT_OPERATOR_BLUEPRINT
              │
              ▼
       Capability Catalog
              │
              ▼
      Raphael Research
              │
              ▼
      Lab Verification
              │
              ▼
      Broker Integration
```

### 23.1 Raphael Consumption Model

**Directly transferable** — capabilities Raphael can eventually implement
(most of §4 families at lab scope): discovery, surface mapping, web/API
assessment classes, AD/identity assessment on lab ranges, cloud fixture
assessment, C2 *lab instances*, evidence/failure/campaign architecture, the
reasoning components (§6-§8, §13, §20), OPSEC-state and defender-model logic
against fixture blues, evaluation framework (§22).

**Adaptable** — capabilities requiring safe abstraction/simulation: bulk
credential testing (canary-credential fixtures), MFA-fatigue/human-factor
techniques (consenting-user simulations), destructive/impact classes (§15
simulators), supply-chain and mass-exploitation reasoning (analytical +
fixture-fleet), DDoS/platform classes (rate-limited fixture load), OT/ICS
(digital-twin fixtures), persistence (fixture-only implementations behind the
§15 rule).

**Research-only** — remain conceptual or laboratory-only: 0-day exploit
development pipelines, kernel-grade evasion internals, domain-fronting-class
evasion research, botnet architecture, live infrastructure tradecraft at APT
depth — documented here as knowledge/analysis, not implementation tickets.

**Not appropriate for autonomous execution** — must never become unrestricted
autonomous functionality: anything in §15's operational classes (disruption,
destructive payloads, ransomware-like behavior, bulk credential theft outside
fixtures, mass phishing, destructive OT), plus any capability whose
authorization check cannot be made mechanically fail-closed. These remain
simulation/fixture/research classes permanently in any consuming registry.

### 23.2 What Raphael would need in order to reason at adversary level
(final assessment, answer to the blueprint's driving question)

To reason against a highly capable modern adversary, a consuming system needs,
in priority order:

1. **A belief-state world model with provenance** (§6) — capability without a
   model is a tool collection.
2. **A hypothesis engine with retained negative knowledge** (§6.3, §13).
3. **An attack-path graph with uncertainty, dead-end detection, and
   alternative-path generation** (§8) — the core state for cross-domain
   reasoning.
4. **A capability-selection function that optimizes information gain under
   authorization, budget, and detection constraints** (§20.2).
5. **Failure classification wired into strategy** (§13) — repeat-failure → 0.
6. **Campaign-grade durable state with resume** (§9).
7. **Defender modeling + OPSEC state** (§11-§12) — adversary reasoning without
   modeling the blue side is incomplete.
8. **The full taxonomy as a measurable registry** (§4, §24) — so capability
   gaps are visible rather than assumed absent.
9. **External, hard-zero-gated evaluation** (§22).
10. **The capability→simulation split enforced structurally** (§15) — depth of
    understanding without depth of weaponization.

The prioritization criterion throughout: **capability depth, adversarial
reasoning, adaptability, evidence quality, and authorized execution** — not the
number of hacking tools catalogued.

---

## 24. FINAL BLUEPRINT REQUIREMENTS

This document is: standalone · technically deep · internally consistent ·
architecture-focused · source-backed · modular · extensible · suitable for
future implementation planning.

It is deliberately **not** a generic cybersecurity overview and **not** a tool
list: the sections above describe how a highly capable adversarial operator
thinks, learns, plans, selects capabilities, adapts to failure, models defenders,
manages campaigns, and operates across heterogeneous environments.

Central design principle:

> **The objective is not maximum destructive power. The objective is maximum
> adversarial capability and reasoning fidelity, represented in a form that can
> later be evaluated and safely instantiated in authorized environments.**

### Closing index — required elements and where they live

| # | Required element | Section |
|---|---|---|
| 1 | Capability taxonomy | §4 |
| 2 | Operator architecture | §3, §21 |
| 3 | Cognitive architecture | §6, §7 |
| 4 | Campaign model | §9 |
| 5 | Attack-path model | §8 |
| 6 | Arsenal model | §5, §20 |
| 7 | OPSEC model | §11 |
| 8 | Defender model | §12 |
| 9 | Failure/adaptation model | §13 |
| 10 | Maturity ladder | §14 |
| 11 | Actor profiles | §16, §17, §18, §19 |
| 12 | Evaluation framework | §22 |
| 13 | Raphael integration interface | §23 |
| 14 | Open research questions | A below |
| 15 | Capability gaps requiring further research | B below |

### A. Open research questions

1. **Belief calibration**: how to calibrate confidence values in the world model
   so that P(success) estimates in path scoring are empirically reliable —
   current literature on attack-graph Bayesian updating assumes better priors
   than operators actually have.
2. **Hypothesis generation at scale**: generating *good* hypotheses over graphs
   with hundreds of unknown edges without combinatorial explosion — no mature
   method; beam/pruning heuristics are unvalidated against red-team ground
   truth.
3. **Selection-function learning**: can the §20.2 weights be learned from
   external-evaluated trajectories (E1.5-class) rather than hand-set — and how
   to detect weight-degradation (policy overfitting) in deployment?
4. **Defender-model fidelity**: how accurate must the §12 model be before it
   improves strategy vs. misleads it (wrong blue-model is worse than none)?
5. **Deception robustness**: distinguishing genuinely weak assets from
   planted ones from limited observations — statistical framing exists,
   practical thresholds unknown.
6. **Cross-domain path semantics**: unified graph over identity+cloud+SaaS+OT
   needs a common privilege/trust algebra — no standard representation exists.
7. **Complexity invariance measurement**: defining a *normalized* difficulty
   metric so performance slopes across ladders (§22) are comparable between
   environments.
8. **Long-horizon credit assignment**: attributing campaign success/failure to
   decisions made dozens of loops earlier — sparse-reward problem, unsolved in
   this domain.
9. **Actor-class priors**: empirically grounded priors (from §19) for
   "how would class X behave here" reasoning without stereotyping every group
   into one profile.
10. **Evaluation integrity**: preventing an increasingly capable operator from
    *gaming* its evaluator (reward hacking on held-out suites) — external
    evaluation helps but is not sufficient at high autonomy levels.

### B. Capability gaps requiring further research

| Gap | Why it matters | Research direction |
|---|---|---|
| OT/ICS reasoning depth | F/G-tier capability; process consequences not reducible to IT graphs | digital-twin fixtures + process-dynamics modeling (ATT&CK for ICS) |
| Mobile/device ecosystem | largely unrepresented in current taxonomies vs its real surface | ATT&CK Mobile mapping into the registry; MDM-abuse fixtures |
| Supply-chain trust modeling | hardest high-consequence class to fixture honestly | build-system/update-channel simulators; code-signing trust graphs |
| SaaS/identity federation depth | the current primary battlefield (R16 OAuth year) | disposable-tenant fixtures; consent/conditional-access testbeds |
| 0-day reasoning (research-grade) | APT-class depth; needed for understanding, not production exploits | authorized code-review methodology; vuln-class taxonomies as knowledge |
| AI-era tradecraft | GTG-1002-class autonomous execution, AI fingerprinting, adversarial ML | continued monitoring of the AI-orchestration inflection (R17) |
| Browser-delivery chains | client-side exploit delivery remains a documented APT/mercenary capability | behavioral modeling + fixture delivery, never real chains |
| Post-quantum credential implications | future credential-access landscape | monitoring + analysis only |
| Multi-environment (hybrid on-prem+cloud+edge) path algebra | unifies the hardest real-world campaigns | common trust/privilege representation (open question A.6) |
| Human-factor modeling beyond phishing | help-desk, MFA-prompt, physical-pretext interfaces | consenting-user simulation design patterns |

---

*End of blueprint. Companion research: `references/offensive_powerups_v1.md`
(Rounds 1-9), `references/famous_group_ttps_v1.md` (Rounds 10-17).
Consuming systems: see §23; `RAPHAEL_ARCHITECTURE_ROADMAP_v2.md` unchanged.*
