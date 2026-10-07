# Famous Group TTPs v1 — Research Compilation (Rounds 10-17)

Compiled 2026-09-30 from 8 web-research rounds (websearch-grounded). Rounds 10-13
cover the classic/archetypal groups; rounds 14-17 were added same-day after an
operator request for **recency** and cover the 2025-2026 campaign landscape.
Purpose: extract how the most-studied offensive groups actually operated, and map
the patterns onto Raphael per `RAPHAEL_ROADMAP_OFFENSIVE_RESTORE_v1.md` and
`RAPHAEL_EVOLUTION_BLUEPRINT_v1.md`. Companion to `offensive_powerups_v1.md`
(Rounds 1-9, capability research) — this file is adversary-behavior research.

## Scope & Ground Rules

- Historical/public reporting only (court records, vendor advisories, press).
- Engagements run against **operator-supplied target sets only** (roadmap §5).
- Excluded per roadmap §5 non-goals: ransomware/extortion playbooks,
  cash-out/laundering, victim-selection content, uninvited targets. Impact-stage
  techniques below appear only as defender-side recognition patterns.
- Every round ends with a Raphael integration mapping.

## Round Summary

| Round | Theme | Headline pattern | Primary Raphael target |
|---|---|---|---|
| 10 | Hacktivism | Noise+skill split: mass DDoS masks small skilled crews | recon/web-app checks, OPSEC lessons |
| 11 | Nation-state | Supply-chain + identity abuse + edge-device 0-days | Tier A recon, E1.5 strategy depth |
| 12 | Cybercrime | Humans as the exploit: vishing, token theft, insider buying | capability catalog gaps, defensive report items |
| 13 | Synthesis (classic) | Cross-group ATT&CK taxonomy + OPSEC-failure analysis | planner difficulty ladder, metrics, E1.5 candidates |
| 14 | Hacktivism 2025-26 | Gamified DDoS + opportunistic OT/VNC intrusion; arrests don't deter | DoS-recognition checks, OT recon items |
| 15 | Nation-state 2025-26 | Telco/edge rootkits, captive-portal AiM, npm/SaaS supply chain | Tier A edge+SaaS inventory, E3 fixtures |
| 16 | Cybercrime 2025-26 | OAuth-token supply chains; SaaS config abuse; helpdesk SE | SaaS trust-surface checks, identity report items |
| 17 | Synthesis 2025-26 | AI-orchestrated attacks (80-90% autonomous) + updated taxonomy | E1.5/INV-1 justification, metrics update |

---

## Round 10 — Hacktivism Majors

### Anonymous (2006→)

- Loose coordination, not an org: announcements on chan/IRC, volunteer tooling.
- **LOIC "hivemind"**: volunteers point a DDoS tool at a target, optionally
  "GET IRC MODE" — which routes the attack through an IRC-controlled backend
  (botnet). Safety-in-numbers theory failed: ~14 PayPal convictions from
  network/IRC/credit-card records; LulzSec crew separately unmasked.
- OpPayback cycle (retaliation loop): anti-piracy DDoS (Aiplex) → MPAA/RIA →
  Gene Simmons (38h) → Dec 2010 WikiLeaks-adjacent: MasterCard, Visa, PayPal,
  PostFinance, Swedish prosecution authority. 27k+ LOIC downloads by FBI count.
- Real intrusions were done by small skilled sub-crews inside the noise —
  e.g. HBGary: ColdFusion object-injection chain + reused admin password from
  a sister company → 71k email archive dumped; Stratfor Christmas 2011
  (Sabu/LulzSec crew: SQLi + dumped emails + fake $1 vendor donation).
- Other techniques: mass doxxing/OSINT aggregation, website defacements,
  operational sub-campaigns with named "ops" (OpISIS with ghostSEC/TeaMp0isoN
  co-ops).

### LulzSec (May–July 2011, "50-day spree")

- Sony Pictures: SQLi ("from a single injection we accessed EVERYTHING") —
  1M+ records, many plaintext passwords. Also NHS, CIA.gov (DDoS only),
  Senate ×2, InfraGard chapter (SQLi + data dump), PBS CMS (defaced with
  "Tupac lives" meme), Nintendo/EA/Minecraft/Eve (SQLi, dumped, not published),
  Stratfor (Christmas, 5GB email dump).
- Tooling was simple: Havij/SQLMap-class SQLi, manual chaining, LOIC/HOIC
  DDoS, credential publication. The novelty was publicity, not technique.
- **OPSEC failure (the durable lesson)**: Sabu flipped by the FBI Jan 2012;
  IRC logs, reused handles across forums, hosted-VM/payment trails and webcam
  self-identification brought the rest (Kretsinger/"Phoenix", Rivera,
  Miranda). The loudest group fell to identity-level forensics, not a
  counter-hack.

### Syrian Electronic Army (SEA, 2011–2014)

- Mostly trust-chain attacks, not perimeter exploitation:
  - Spear-phish a **Melbourne IT reseller** → altered DNS records for
    nytimes.com (2013), twimg/t.co redirects, Huffington Post, Politico;
  - Panel/account compromise of **MarkMonitor** (facebook.com WHOIS attempt);
  - Hosting-provider intrusion → defacements (Harvard 2011, The Onion,
    later AP/PBS Twitter takeovers used for market-moving headlines);
  - Third-party content widgets: Taboola/Outbrain compromise redirected
    Reuters/CNN readers to SEA landing pages;
  - Forbes WordPress: steal editorial creds → install plugin/backdoor →
    fake headlines + ~1M reader-credential harvest.
- Pattern: registrar/agency/CDN/CMS trust is the actual attack surface.

### TeaMp0isoN (brief)

- UK group, SQLi + "w0rm" defacement kits, Vodafone UK outage, Israeli
  government targets; co-ran Anonymous-adjacent ops. Representative of
  script-kid-to-crew pipeline.

### Round 10 lessons

1. Mass-participation tooling scales the noise but guarantees terrible OPSEC;
   the actual compromise work is 2–5 people with SQLi + credential reuse.
2. The winning vectors were **trust-chain**: registrar, reseller, CMS,
   ad network — not the target's own perimeter.
3. Publicity-seeking (taunts, dumps) is what converts intrusion into arrest.

**Integration**: validates recon/web-app check depth (SQLi detection,
credential-exposure items — cf. the osmania.ac.in exercise) as high-yield;
drives "third-party trust surface" checks (DNS provider, widgets, CMS admin)
into Tier A recon; OPSEC lessons feed the report-side hardening guidance we
give the operator, not our own tradecraft (we operate under declared scope).

---

## Round 11 — Nation-State Majors

### APT29 / SVR (Cozy Bear) — SolarWinds (SUNBURST, 2019-2020)

- Supply-chain implant at build time: **SUNSPOT** monitored the Orion build
  and injected SUNBURST DLL; code-signed, plus later second-stage loaders.
- Dormancy 12–14 days before any C2; C2 domains chosen to mimic OIP telemetry
  (`avsvmcloud.com`) with victim hostname encoded into subdomain chunks
  (14-char triage encoding) — victim selection at the DNS resolver side.
- Evasion: FNV-1a hashed AV/EDR product blocklist (skip if monitored),
  CNAME-chaining to legitimate cloud hosting, Cobalt Strike only on
  allowlisted victim profiles.
- Identity tradecraft: password spraying, token theft, SAML-signing-cert
  forgery, mailbox export via `New-MailboxExportRequest`, MFA bypass by
  registering attacker devices/enrolling MFA on the victim account,
  OWA/Exchange HTTPS exfil, VPN egress from the victim's own country,
  "name-matching" attacker infrastructure hostnames to the victim org.
- Follow-on campaigns: NOBELIUM cloud password-spray + OTP-session implants,
  UNC3524 quiet OWA persistence (mailbox rules deleted after read),
  Midnight Blizzard (2024): legacy-app OAuth grant → Microsoft production
  tenant keys.

### APT28 / GRU 26165 (Fancy Bear)

- Spear-phish with hard-to-fail lures (Podesta fake OWA page, "Do you want
  to change your password?"); typosquat + iFrame exploit kits; macro docs.
- Implants: X-Agent (multi-platform), XTunnel, Cannon (postal-file C2),
  CHOPSTICK; retooled constantly (Kaspersky + Mandiant 2024/2025/2026
  reporting shows same-era tradecraft persisting: GooseETextWriter /
  BeardShell steganographic C2, NotDoor Outlook-rule backdoor, NTLM leak
  via CVE-2023-23397, Jaguar Tooth SNMP spray on Cisco, Responder +
  ntlmrelayx against Ubiquiti EdgeRouter captive portals).
- Password-spray campaigns against Microsoft 365 / Entra tenants remain
  their steady-state entry method (MSFT 2023–2024 bulletins).

### Equation Group / Shadow Brokers (pre-2017)

- Kaspersky 2015: the Equation platform — ~10 exploit chains, multiple
  stolen code-signing certs (nVidia etc.), **Fanny** USB tool for air-gapped
  mapping (launched from interdicted CD shipments), GrayFish persistence.
- April 2017: FUZZBUNCH framework leak (EternalBlue/EternalRomance/
  EternalChampion, DOUBLEPULSAR implant, EXPLOITABLE/virtualized targets),
  Cisco EXTRABACON, **SWIFT Alliance Access operations**, edge-device
  exploits (AT&T Secure Edge / VPN appliances).
- Consequence chain: leaked tooling + unpatched MS17-010 → **WannaCry**
  (May 2017) and **NotPetya** (June 2017, EternalRomance via M.E.Doc) —
  ~$4B combined damage. The theft of *legitimate* capability reshaped the
  threat landscape more than any novel exploit.

### Lazarus / BlueNoroff (DPRK)

- Origins: DDoS (2009) → 45+ distinct malware families documented by
  AlienVault/NCC: serious actors.
- **Sony Pictures 2014**: spear-phish into IT admin → Destover wiper +
  100TB-scale data theft; "Guardians of Peace" cover story; wiped in a
  way that looked like insider sabotage.
- **Bangladesh Bank SWIFT 2016**: used stolen SWIFT credentials in
  Alliance Access on a weekend, killed printer spooler to blind log review,
  requested $951M, $81M extracted before the NY Fed cutoff (rest partially
  recovered), $1B+ attempted across 2016's full run (Vietnam, Ecuador,
  Poland banks); cash-out via Manila casinos (GRCT) later joined the
  ATM-jackpotting and crypto-exchange heist era (2017 onward; Bybit 2025
  $1.5B ETH theft).
- Pattern: one unit's TTPs (spear-phish → live network ops → wiper
  disguises) are reused across finance/espionage sub-units with code-sharing.

### Stuxnet (2010, historical archetype)

- Four zero-days, stolen certs, air-gap USB propagation, Siemens WinCC
  PLC-specific payload — the template for physically-damaging malware and
  for the Equation ecosystem above.

### Round 11 lessons

1. Edge devices + supply chains are the durable entry surface; perimeter
   hardening misses it.
2. Identity abuse (spray → token → SAML/MFA bypass) is cheaper and quieter
   than exploits even for state actors.
3. Stolen legitimate tooling scales globally overnight (Shadow Brokers).
4. Long dormancy + victim-conditional C2 is what makes these hard to detect.

**Integration**: S7 planner difficulty ladder top tier should model
supply-chain and identity-attack *scenarios* (as read-only recon + design
recommendations); DNS/DGA-shaped C2 patterns (avsvmcloud encoding) give E3
blue fixtures for detection exercises; RAT/persistence knowledge feeds
`reference/` checklists for defense-evasion review in reports.

---

## Round 12 — Cybercrime / Financial Majors

### Carbanak / FIN7 (2013–2018+)

- Kaspersky "great bank robbery": video/screen recording of admins to map
   verification processes, then fake transactions appearing legitimate
   (no money moves until the operator verifies), ATM cash-out scripts timed
   to physical windows, SWIFT interface abuse. ~$1B, 100+ institutions.
- FIN7 tradecraft: spear-phish Word docs with follow-up **phone calls**
   ("did you get my resume?") to induce macro enable; Carbanak backdoor;
   video capture of back-office; **shim persistence** (`sdbinst` +
   patched `services.exe`); LNK-in-DOCX/RTF, Mshta, scheduled tasks;
   signed/allowlisted tool reuse; POS memory-scrapers (~15–20M cards,
   6,500 terminals) sold via JokerStash.
- Outcome: arrests of Fedorov/Hladyr/Kopakov (US/Ukraine), Kolpakov (7y)
   — OPSEC failures in money movement and communications.

### NotPetya (2017) — destructive wiper disguised as ransomware

- Supply-chain entry: M.E.Doc Ukrainian tax software update → EternalRomance/
  EternalBlue lateral + Mimikatz-class credential harvesting + `psexec`/
   WMI → full-domain wipe in hours (Maersk ~$300M, Merck, FedEx TNT, ~$10B
   total). Sandworm-attributed.
- Defense-relevant: ransomware *facade* (fake key requirement, unrecoverable
   payload) — recognition pattern for reports, not a playbook.

### Lapsus$ / DEV-0537 (2021–2022, teens UK/BR)

- Microsoft/Google/CISA advisories give the full recipe of human-layer attacks:
  - **SIM-swap** (even paid a telecom insider ~$20k/wk);
  - **MFA push fatigue** (spam prompts until the user taps approve);
  - buying creds/session cookies (Redline stealer, Russian Market);
  - **paying insiders** for VPN/Citrix/Okta access (recruiting ads);
  - helpdesk social engineering for resets; then live in chat/SharePoint/
    GitHub/Confluence sweeping for secrets (Ubiquiti, Nvidia, Samsung,
    T-Mobile, Microsoft 50k lines of source, Okta via the **Sitel** RDP
   foothold — 5 days of screenshots).
- No infra-covering: wrote their own GPOs, left READMEs, public Telegram
  taunting; arrested Mar 2022 (seven UK teenagers) + later US minors.

### Scattered Spider / UNC3944 / Octo Tempest (2022–2023, CISA AA23-320A)

- English-fluent young actors, **no malware authored** — B2B attack markets,
  then ALPHV deployment:
  - **vishing**: call helpdesk impersonating the employee, use target's real
    background from LinkedIn/OSINT, call repeatedly across shifts;
  - **smishing** fake SSO pages: `victimname-okta.com` / `victimname-sso.com`;
  - SIM swap + MFA push bombing + OTP harvesting via proxied sign-in;
  - stolen session tokens replayed (bypasses MFA entirely);
  - **BYOVD** (STONESTOP/POORTRY to kill EDR) + living-off-the-land +
    allowlisted remote tools (AnyDesk/Splashtop/TacticalRMM);
  - ESXi encryption; insider-recruitment language ("we buy creds").
- MGM: one LinkedIn-researched employee, one helpdesk call, 10-day outage,
  ~$100M impact; Caesars paid. Arrests through 2023–2025 (multiple US/UK).

### Twitter 2020 (brief)

- Phone/social-engineering of internal "Spring" tool admins (targeted,
   scam bitcoin accounts) — the internal-tool trust problem again.

### Round 12 lessons

1. The dominant initial access is **the human layer**: helpdesk, MFA prompt,
   session cookie, insider — not a CVE.
2. Session-token theft defeats MFA; device/session binding is the fix.
3. Small crews (5–10 people, teenagers) cause nine-figure losses; cost of
   attack ≈ phone bill + stolen cookies.
4. Arrests correlate with identity slips (SIM contracts, marketplace handles,
   taunting), not with defense products.

**Integration**: adds an "identity attack surface" section to reports
(helpdesk verification, MFA fatigue, token binding, SIM-swap) as remediation
items; capability catalog gains vishing/SE *knowledge as defensive checks*
only; BYOVD + LOTL entries already covered by Rounds 5/6 (cross-linked);
Scattered Spider's B2B-market pattern = E1.5 strategy diversity input.

---

## Round 13 — Synthesis: Cross-Group Taxonomy, OPSEC Failures, Raphael Map

### A. Cross-group technique taxonomy (by phase)

| Phase | Hacktivist (R10) | Nation-state (R11) | Cybercrime (R12) | Common core |
|---|---|---|---|---|
| Initial access | SQLi, CMS/reseller trust-chain | Supply chain, edge 0-day, password spray | Vishing, SIM swap, token/cookie theft, insiders | **trust & identity over perimeter** |
| Execution | Havij/SQLMap/LOIC | Signed implants, build injection | LOLBins, allowlisted RMM, no custom malware | low-noise, allowlist-shaped |
| Persistence | deface pages, dumps | SAML certs, OWA rules, device regs | session cookies, GPO, shims | survives password reset |
| C2/evasion | proxies (weak) | DGA-encoding, FNV hash blocklists, country-matched VPN, dormancy | BYOVD, LOTL, buy-vs-build infra | mimic legitimate traffic |
| Discovery/exfil | SQLi dumps | mailbox export, 100TB theft | source-code sweeps, screenshots | read in place, exfil quietly |
| Impact | DDoS, deface | wipers (Stuxnet/Destover) | ransomware facade, ATM cash-out | **out of Raphael scope (§5)** — recognition only |

Key finding: **rows 1–4 converge across all three groups.** The differences
are budget and patience, not fundamentals. That is what makes a single
agent model covering all three realistic.

### B. OPSEC-failure taxonomy (how they got caught)

| Failure | Case | What broke |
|---|---|---|
| Identity reuse | LulzSec | handles/payment trails/IRC logs → Sabu flip → crew |
| Mass tooling metadata | Anonymous (PayPal14) | LOIC logs, IRC server logs, credit cards |
| Money movement | FIN7, Carbanak mastermind | marketplace ops, laundering, phones |
| Taunting/publicity | Lapsus$, Twitter hackers | public Telegram, interviews, badge photos |
| Insider cash | SEA phone-phishers, telecom insiders | money trails to identifiable humans |
| Stolen-tool fingerprints | Lazarus | password/code reuse → attribution clusters |
| Victim-side reporting | APT29 | only found by endpoint review after Microsoft review — *their* OPSEC was near-perfect |

Pattern: **state actors fail at collection/infra pivots; everyone else fails
at identity and money.** For Raphael the translation is: receipts + declared
scope + rate ceilings are our *structural* OPSEC — the system never holds
identities or funds (§5 removes the failure modes that end prosecutions).

### C. Raphael integration map

1. **Planner difficulty ladder (S7)**: tier by group archetype —
   hacktivist-grade (single web-app + SQLi class, cf. osmania) → cybercrime-
   grade (identity surface + lateral) → APT-grade (supply chain, dormancy,
   victim-conditional logic) as *scenario depth in E1.5 eval*, never as
   real-world capability drift.
2. **Capability catalog additions (knowledge, not action)**: third-party
   trust-surface recon (DNS/registrar/CMS/widget), identity-attack defense
   checks (MFA fatigue, session binding, helpdesk verification), edge-device
   inventory items — all report-side recommendations.
3. **E1.5 strategy diversity**: cross-group taxonomy above is the candidate
   strategy-feature space (entry-vector × persistence × evasion classes) —
   the external verifier scores strategies drawn from this distribution.
4. **E3 blue fixtures**: SUNBURST-style DGA/encoding patterns, fake-SSO
   domains (`victimname-okta.com` shape), push-fatigue traffic as detection
   exercises.
5. **Metrics**: per-engagement entry-vector coverage vs. this taxonomy
   (TA0001–TA0011 map), reported as a difficulty-weighted histogram.
6. **§5 exclusions stand**: impact-phase techniques (ransomware, cash-out,
   wipers, extortion, DDoS-against-uninvited) remain recognition/defense
   content only; the 621-test suite, INV-1 and guardrails unchanged.

---

# 2025-2026 Currency Addendum (Rounds 14-17)

Added 2026-09-30 per operator request for recency. Same scope rules (§5)
apply; impact-stage events appear as defender-side recognition only.

## Round 14 — Hacktivism 2025-2026

### NoName057(16) ecosystem (the current major)

- **Structure**: Telegram-native recruitment since Mar 2022; DDoSia tool
  (GitHub-hosted, contributor rewards); by 2024 merged ops with **Cyber Army
  of Russia Reborn (CARR)**; spawned **Z-Pentest** (Sep 2024 — CARR+NoName
  members, pivots to OT intrusion + hack-and-leak, e.g. HMI defacement video
  Apr 2025) and **Sector16** (Jan 2025, novice). CISA/NCSC joint advisory
  **AA25-343A (Dec 2025)**: these groups exploit internet-open **VNC** on
  critical infrastructure with unsophisticated TTPs — scan open VNC
  [T1595.002], rent VPS for password brute-force [T1583.003], simultaneous
  DDoS as cover for SCADA intrusion; routinely overstate impact.
- **#OpUK 2026 (Jan 5-9)**: NoName057 + ServerKillers DDoS'd UK MoD, ~20
  councils, National Rail, Port of Felixstowe, G4S, banks; pro-Palestinian
  **DarkStorm** joined with UK airports. Claims "verified" via CheckHost
  screenshots; motive tied to £8B frozen-Russian-assets→Ukraine story and
  Raven/Gravehawk air-defense transfers.
- **Operation Eastwood (15 Jul 2025)**: Europol/Eurojust, 12 countries —
  100+ servers seized, 24 searches, 7 warrants, 3 arrests (FR/ES/PL);
  coordinators named as Mikhail Burlakov + Maxim Lupin (Russia), ~4,000
  supporters' malware, botnet of hundreds of servers.
- **Deterrence failure (key data point)**: attack commands 8 months pre-op
  = 56,231 → 8 months post-op = 61,666; ~1,530 claimed successes
  Oct 2025-Mar 2026 (~300/month). Post-Eastwood the group **gamified**
  participation: "patriotic online game" with crypto rewards via Telegram
  (Vot Tak/RKS.Global investigation, 2026). Germany retaliated-on for the
  crackdown.

### Others

- **Handala** (Iran-linked): shift from defacement/claim-ware to destructive
  action — the Mar 2026 **Stryker** incident: weaponized Microsoft Intune
  remote-wipe across the Fortune-500 medtech's Microsoft estate (disclosed
  2026-03-11; 79 offices; >200,000 systems wiped), attributed by Beazley to
  Handala's destructive branch. First big case of "legit admin API as wiper".
- Momentum check: CISA AA25-343A + NCSC December-2025 advisory confirm
  pro-Russia DDoS vs UK/local government continues at ~monthly cadence with
  low but nonzero success.

### Round 14 lessons

1. DDoS-as-a-message is now **gamified infrastructure** (crypto pay, Telegram
   funnels) — cheap, durable, and post-takedown antifragile (arrests raised
   volume).
2. The interesting escalation is hacktivist crews moving from DDoS to
   **opportunistic OT/VNC intrusion** — low skill, high consequence.
3. Legitimate MDM/remote-admin tooling (Intune) is now a wiper channel —
   defender-side inventory item.

**Integration**: DoS recognition stays in reports (our rate ceilings +
authorization make DoS a non-issue operationally); VNC/OT exposure checks
join Tier A recon as *report findings*; Intune/remote-admin abuse added to
defense checklist. No operational change to §5 posture.

## Round 15 — Nation-State 2025-2026

### China

- **Salt Typhoon** (Earth Estries/UNC2286, "Operator Panda"): scale revealed
  — **200+ US organizations, 80 countries** (Reuters Feb 2026); telco core
  access undetected "in some of the best-defended systems in the world"
  (CrowdStrike); 2026 expansion into non-telco (Azerbaijan oil/gas, DeedRAT
  re-deployment attempts Dec 2025-Feb 2026, Bitdefender); NZ NCSC Apr 2026:
  covert SOHO-router networks at scale.
- **UNC3886**: Singapore CSA Feb 2026 — **all four major Singapore telcos**
  breached in one months-long campaign using zero-days + rootkits for
  persistence in network devices.
- **F5 (Oct 2025)**: long-term intrusion into product-development
  environments; BIG-IP source code + **undisclosed vulnerabilities** stolen —
  a stockpile event.
- Trend Micro H1 2026: China ops fold AI into recon/lateral movement;
  ADINT (harvesting device/location data from ad auctions, no malware);
  C2 increasingly on trusted cloud, developer tunnels, blockchain, paste
  sites.

### Russia

- **Midnight Blizzard / Storm-2945 "CaptiveCrunch"** (Aug 2026, Microsoft):
  manipulate **captive-portal DNS/HTTP** (hotels, conference centers) +
  SOHO-router DNS redirects → adversary-in-the-middle harvesting M365
  credentials of traveling employees (finance, legal, healthcare, energy);
  overlaps APT28's FrostArmada pattern.
- **APT28 "Operation Neusploit"** (Jan 2026): multi-stage backdoor chain
  across Central/Eastern Europe; Pawn Storm opened 2026 with an Office
  zero-day (Trend Micro).
- **Sandworm**: new wipers; struck a **Polish energy company** (NATO CNI,
  ESET Q4'25-Q1'26) — the first Russian-aligned destructive hit on CNI
  outside Ukraine in that window.

### DPRK

- **Lazarus** evolution: fake-job lures vs European **drone manufacturers**
  (Oct 2025, RAT); Operation DreamJob continues; **Operation
  DangerousPassword** → compromise of the **axios npm package**
  (100M+ weekly downloads) — a mainstream npm supply-chain foothold
  (ESET Q4'25-Q1'26); Andariel/TigerRAT re-emergence (nuclear/hydrogen-
  adjacent engineering targets).
- **TraderTraitor moneyline**: Apr 2026 DPRK-linked exploit of a major
  crypto exchange — **~$293M**, largest DeFi theft of 2026 (LayerZero/
  KelpDAO rsETH configuration).

### Iran

- **Handala** Stryker wipe (see R14) — destructive via Intune.
- **Earth Vetala** scanning newly disclosed Ivanti vulns within days;
  Iran-aligned actors tampering with **US fuel-tank gauges** (OT, Trend Micro
  H1 2026); EPMM CVEs actively exploited by state-affiliates (Rapid7).

### Round 15 lessons

1. Network devices/edge (VNC, routers, captive portals, MDM) remain the
   persistence substrate across all three states.
2. Supply chain has moved from "vendor software" to **npm packages, OAuth
   apps, and SaaS admin APIs**.
3. AI is now an operational teammate for state actors (recon/lateral
   movement handed to agents) — Trend Micro's headline finding H1 2026.

**Integration**: edge/SaaS inventory items into Tier A recon; npm/OAuth
exposure checks into supply-chain checklist (extends Round 9); captive-
portal AiM and DNS-redirect patterns become E3 blue fixtures; F5-style
"stolen vulnerability stockpile" justifies EPSS/n-day urgency (Round 7).

## Round 16 — Cybercrime 2025-2026

### Scattered Spider — peak year and arrests

- **2025 campaign rotation**: UK retailers (M&S — £300M profit hit; Co-op;
  Harrods), then US (Aflac — 22.65M notified; Hawaiian Airlines, WestJet,
  UNFI — Whole-Foods-shelf shortages), insurance; branded collabs
  ("Scattered LAPSUS$ Hunters" — Qantas ~5M via Salesforce third-party,
  Oct 2025).
- **TTP update (CISA/FBI/AU/CA joint advisory Jul 2025)**: helpdesk
  targeting, RMM tools, Snowflake access abuse, fake social personas for
  new accounts, MEGA/S3 exfil, ESXi encryption, **RattyRAT + DragonForce**
  (RaaS-as-consumer); FBI advisory 2025-07-29: push-bombing + SIM-swap
  canonical.
- **Enforcement wave**: NCA Jul 2025 (4 arrested, 17-20yo); Sep 2025 —
  Thalha Jubair (19: **120+ attacks, $115M ransom, 95 years exposure**),
  Owen Flowers (18: TfL + US healthcare), Vegas juvenile surrender
  (MGM/Caesars $100M); Jun 2026 — defendants plead guilty day-1 of trial.
  Group announced "retirement" (Sep 2025) yet continued in finance.
- **Diffusion effect**: Mandiant saw zero post-arrest intrusions attributed
  to the group — but **the playbook spread** (Google: other crews adopted
  vishing/helpdesk/ESXi TTPs; email-bombing + IT-impersonation +1,450%
  with 72% intrusion ratio, eSentire 2026).

### ShinyHunters — the OAuth supply-chain year

- Chain: mid-2025 **vishing as Salesforce IT support** → victims authorize
  malicious OAuth apps (UNC6040) → separate branch: Salesloft GitHub
  foothold (Mar 2025) → AWS → **Drift OAuth secrets** → Aug 8-18 2025
  mass REST-API export across **700+ Salesforce orgs** (Cloudflare, Palo
  Alto, Proofpoint, PagerDuty, Tanium, Google Workspace via Drift Email) —
  GTIG **UNC6395**; targeted AWS AKIA keys, passwords, Snowflake tokens.
- Claim: **1.5B records / 760 companies** (Account/Contact/Case tables);
  extortion site ~990M; Salesforce refused to pay (Oct 2025); FBI took the
  leak site down. Springboard: stolen Case data mined for secrets to pivot.
- Continuation: Gainsight apps; **Klue (Jun 11-12 2026)** — 4-year-old
  dormant test credential → token harvesting → 195 customer orgs;
  **Experience Cloud guest-profile misconfig campaign (Mar 7 2026)** —
  mass-scan of public sites, misconfigured guest permissions, then
  vishing/extortion against the stolen base (FINRA alert). Also: TransUnion
  4.5M (Jul 2025), Crunchbase 2M (Jan 2026), Telus 700TB (Mar 2026),
  NAIC credit-rating data (Jun 2026), NVIDIA partner GFN.am (May 2026),
  Stellantis (SaaS integration). CSIS: ShinyHunters tied to **>half of
  confirmed mega-breaches through May 2026**.
- Brand note: "Scattered Lapsus$ Hunters" merger narrative; claimed
  "going dark" then resumed — treat retirement claims as noise.

### Ransomware/extortion landscape (recognition data)

- **Volume**: record **1,000 leak-site victims Jan 2026**, 986/30d Feb 2026
  (Ransom-DB); 53 concurrent groups; US ~47-49%. Q3'25: 85 groups,
  ~535 victims/mo (Check Point).
- **0APT** surged to #1 (144-185 claims) but Bitdefender flags mass false
  claims — claim inflation is now a phenomenon itself.
- **Cl0p resurgence**: CVE-2025-61882 **Oracle E-Business Suite zero-day**
  (exploited months pre-disclosure) — Harvard, Washington Post, Logitech,
  Allianz UK, Envoy Air/American Airlines, NHS (unconfirmed).
- Steady core: **Qilin**, **Akira** (VPN/SonicWall→Nutanix AHV; ~$244M
  claimed; CISA "imminent threat to critical infrastructure" Nov 2025),
  INC, Play, DragonForce, Medusa; **LockBit 5.0** return (post-Cronos
  plateau, not decline — Secureworks: affiliates scattered, some moved to
  **pure extortion to avoid ransomware charges**).
- **Craft shift**: ransomware now ships **embedded BYOVD drivers** by
  default (Bitdefender Mar 2026) — defense-evasion and execution fused;
  BEC vendor-impersonation was the #1 DFIR category Q1 2026 (Beazley).

### Round 16 lessons

1. The dominant 2025-26 initial-access currencies: **vishing → OAuth
   authorization**, stolen session/refresh tokens, misconfigured SaaS
   guest profiles — zero CVEs required.
2. Arrests work locally and diffuse globally: crews die, playbooks don't;
   claim inflation + "retirement" theatre pollute attribution.
3. Supply-chain = GitHub secrets → cloud → downstream OAuth tokens — a
   single trusted integration cascades 10x (Obsidian).

**Integration**: SaaS/OAuth/trust-surface inventory becomes a first-class
Tier A recon section (extends R13-C.2); identity-defense report items
(MFA binding, helpdesk verification, OAuth app consent governance) get
concrete 2025-26 case citations; EPSS/n-day loop (Round 7) gains the
Oracle-EBS precedent; BYOVD already covered (Round 5) — now default
criminal tradecraft, worth a detection note in reports.

## Round 17 — Synthesis 2025-2026: The AI-Orchestration Inflection

### What changed vs. R13

| Axis | Classic (R10-13) | 2025-2026 (R14-16) |
|---|---|---|
| Initial access | phishing, SQLi, edge 0-days | **OAuth consent + vishing + SaaS misconfig**; edge rootkits retained by states |
| Trust chain | registrar/CMS/vendor | **npm packages, SaaS admin APIs, MDM (Intune as wiper), captive portals** |
| Hacktivism | LOIC hivemind | gamified crypto-bounty DDoS + opportunistic VNC/OT intrusion |
| Enforcement | arrests broke crews | arrests **raise volume** (Eastwood) and **diffuse playbooks** (Spider) |
| Automation | human-driven | **AI executing 80-90% of operations** (GTG-1002) |
| Impact recognition | NotPetya-class | Intune-wipe, claim-inflation noise, BYOVD-by-default |

### The AI-orchestration cases (highest relevance to Raphael)

- **GTG-1002 (Anthropic, disclosed 2025-11-13)**: Chinese state-sponsored
  operation ran **Claude Code as autonomous pentest orchestrators** —
  ~30 targets (tech, finance, chemical, gov); AI performed **80-90% of
  tactical operations**; humans at only 4-6 decision points; thousands of
  requests/second ("physically impossible" for humans); recon → vuln
  discovery → exploit → lateral movement → credential harvest → exfil,
  with AI-written post-op documentation feeding the next stage. Success
  "in a small number of cases"; **hallucinated credentials/results were the
  main operational obstacle** — validation remains the bottleneck.
- **GTG-2002 "vibe hacking" (Aug 2025)**: coding agents executing data-
  extortion intrusions against 17+ orgs (gov, healthcare, EMS, religious).
- **Scale measurement (Anthropic, Mar 2025-Mar 2026)**: 832 banned accounts
  mapped to ATT&CK — 67.3% used AI for malware writing; 6.5% for lateral
  movement; AI use shifted **deeper into the kill chain** (account
  discovery +8.9%, initial-access phishing -8.6%); **MITRE ATT&CK does not
  capture orchestration/decision autonomy** — the differentiator is the
  scaffolding around the model, not technique count.
- Policy echo: US Senate (Hassan-Ernst) letter to ONCD, Dec 2025.

### OPSEC-failure update (2025-26)

| Failure | Case | Broke on |
|---|---|---|
| Ransom payment trails | Jubair (Scattered Spider) | crypto tracing, $115M, 95-yr exposure |
| Named coordinators | NoName057 (Burlakov, Lupin) | server payments + botnet ops |
| Retire/return theatre | ShinyHunters | kept operating under same brand |
| Juvenile identity slips | Vegas/UK teens | handles, iMessage, Discord/Telegram |
| Staying *inside* the law | Salesforce (Oct 2025) | refused to pay; FBI took leak site — defender-side "OPSEC" won |

Same conclusion as R13-B, updated: **identity + money remains the arrest
path**; states remain hard to catch because they hold no money in-view.

### Raphael integration map (delta over R13-C)

1. **INV-1 / receipts / gates are now industry-justified**: GTG-1002 shows
   exactly the failure mode Raphael's architecture is built to prevent —
   an autonomous agent operating on a target set without external verdicts.
   E1.5 (external, non-self-certifying evaluation) is the direct structural
   countermeasure; cite GTG-1002/2002 in the blueprint.
2. **Validation-first planner**: hallucination was the attacker's own
   bottleneck → our planner must require receipt-backed verification of
   every claimed finding (already the receipt model; promote from design
   nicety to core requirement).
3. **Tier A recon gains a SaaS/OAuth/trust-chain section** (Drift/Gainsight/
   Klue/Experience-Cloud pattern: inventory third-party integrations, OAuth
   app consent, guest-profile permissions).
4. **Metrics**: add AI-era dimensions — entry-vector histogram vs this
   round's taxonomy, plus "claim inflation" noise filtering in E3 fixtures.
5. **§5 exclusions unchanged** — everything above is reported/defensive
   content; Raphael's scope remains operator-declared targets, receipts,
   rate ceilings, no impact-phase playbooks.

### Sources added for Rounds 14-17 (websearch 2026-09-30)

- CISA AA25-343A + NCSC Dec-2025 advisory (NoName057/CARR/Z-Pentest/
  Sector16); Eurojust/Europol Operation Eastwood releases; Moscow Times +
  Vot Tak/RKS.Global gamification investigation; CYJAX #OpUK 2026;
  Guardian May-2025 UK council DDoS.
- CRN "10 Major Cyberattacks 2025/2026"; CSIS Significant Cyber Incidents;
  Homeland CISA Cyber Threat Snapshot (F5, Scattered Spider 2025);
  SecurityWeek (CaptiveCrunch/Storm-2945, Salt Typhoon Azerbaijan, Chinese
  APTs May-2026); Microsoft/ReliaQuest CaptiveCrunch; ESET APT Report
  Q4'25-Q1'26 (axios, DreamJob, Sandworm/Poland); Trend Micro H1 2026 APT
  roundup; Bitdefender salt/AKIRA; LayerZero KelpDAO $293M.
- CISA/FBI/ACSC/CCCS Scattered Spider joint advisory (Jul 2025) + FBI
  2025-07-29 PSA; NCA arrest releases; SecurityWeek/ComputerWeekly/CyberDaily
  arrests + guilty pleas; Guardian M&S £300M.
- BleepingComputer/Google GTIG/FBI/Salesforce/CRN (Salesloft-Drift,
  UNC6395, 1.5B claim); FINRA Experience Cloud alert; CSA research note
  (Salesloft→Gainsight→Klue chain); CSIS/ShinyHunters mega-breach counts;
  Obsidian Stellantis.
- Ransom-DB Jan/Feb 2026 landscape; Bitdefender US 2026 insights (0APT
  false claims, BYOVD-by-default); Check Point Q3'25 fragmentation;
  CISA/FBI Akira advisory (Nov 2025); Computer Weekly LockBit-Cronos
  retrospective; Beazley Q1 2026 (BEC, Handala/Stryker); eSentire 2026
  (email-bombing +1,450%).
- Anthropic GTG-1002 (Nov 2025) + GTG-2002 (Aug 2025) + ATT&CK-mapping
  research (2026); Senate Hassan-Ernst letter (Dec 2025).

---

### Sources (representative, via websearch 2026-09-30)

- Anonymous/OpPayback/LOIC: DoJ 2010–2013 press releases, Ars Technica
  "PayPal 14" and HBGary coverage, Wired LulzSec series, Wikipedia op logs.
- SEA: NY Times 2013 DNS-hijack report, Mandiant SEA dossier, CrowdStrike
  SEA/AP-style writeups, The Onion/Harvard defacement archives.
- APT29: FireEye/Mandiant SUNBURST IOCs + "Highly Evasive Attacker Targets
  SolarWinds", MSFT NOBELIUM/CVE-2023-33367 notes, Volexity UNC3524,
  Microsoft DTI Midnight Blizzard.
- APT28: Kaspersky Sofacy, Mandiant APT28 trends, CISA/MSFT 2023–2026
  FATURL/GTSEBF26 reports, SentinelOne/Secureworks profiles.
- Equation/Shadow Brokers: Kaspersky Equation Group whitepaper (2015),
  ShadowBrokers FUZZBUNCH dump analyses (2017), Cisco Talos EternalBlue
  advisories, Kaspersky "WannaCry and the Non-Existent 'Kill Switch'".
- Lazarus: AlienVault 45-malware report, Kaspersky 2016 SWIFT report,
  Bangladesh Bank commission report, Treasury FATCA/OFAC designations
  (GRCT), CISA #StopRansomware Lazarus advisory (2023).
- Carbanak/FIN7: Kaspersky "The great bank robbery" (2015), Group-IB FIN7
  reports, DOJ indictments (2018–2021).
- NotPetya: Cisco Talos, ESET NotPetya paper, Maersk/Mondelez disclosures.
- Lapsus$: MSFT DEV-0537 advisory (2022), Google TAG, CISA/NSA advisory,
  UK NCA arrests 2022.
- Scattered Spider: CISA AA23-320A, Mandiant UNC3944, MGM/Caesars SEC
  8-K disclosures, 23B2/UK NCA arrests 2025.
- Twitter 2020: DOJ indictment Sept 2020, Twitter blog post-mortem.
