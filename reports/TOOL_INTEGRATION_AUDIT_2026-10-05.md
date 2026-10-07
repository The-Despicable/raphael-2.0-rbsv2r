# MASTER TOOL & CAPABILITY INTEGRATION AUDIT — 2026-10-05

**Scope**: audit-only. No tools installed or executed against any target, no
integrations implemented, no source/policy/docker changes, no commits, no
external requests. The only files created are this report and
`reports/tool_integration_inventory_2026-10-05.json` (counts in this document
are generated from that JSON and reconcile exactly).

---

## 1. Baseline (verified, not assumed)

| Item | Observed |
|---|---|
| Branch / HEAD | `offensive-restore` / `e6a8c707e` (matches all prior reports) |
| Worktree | 70 modified/untracked entries (M0→M2.1 + reports/); all preserved |
| Python | `.venv` = 3.12.15 |
| Lab | dvwa + kali-tools + dvwa-db running, loopback-only (M2.1 hardening in place; rendered compose shows zero non-loopback published ports) |
| Active policies | `engagement-d1-v1.json` only (sha `777999a3c8d5b817…`, unchanged); `bootstrap-v0` = restrictive control/kill switch; `engagement-open-v0.json` unwired; **no D2 artifact exists** |
| D1 guarantees | `tests/test_m2_d1_governed_action.py` 23/23 pass (authorization-before-PEP, denial ⇒ zero capability invocations ⇒ zero spawns, kill-switch, CONV-3 gating, receipt/artifact binding) |
| Evidence dirs | M0 baseline manifest unchanged; 4 D1 transcripts intact |
| Sources | `BLACK_HAT_OPERATOR_BLUEPRINT.md` (88 KB, §1–§24), `references/offensive_powerups_v1.md` (13 KB, R1–9), `references/famous_group_ttps_v1.md` (37 KB, R10–17). Single copies; no authoritative-version conflict (the blueprint self-grounds via `references/BLACK_HAT_GROUNDING_v1.md`) |

D1-state claims from prior reports were re-verified against current source and
configuration (policy sha, gate tests, demo transcripts) — they hold.

## 2. Methodology

1. All three sources read in full (headings, tables, integration maps, §15
   safety classes, §20 mapping, §23 consumption model).
2. Candidate extraction: every named tool/framework, every capability family,
   every multi-tool workflow, every infrastructure component, and the
   blueprint's cognitive components (§6, §20.2, §23.2) — deduplicated by the
   rule stated in the JSON (`meterpreter→metasploit`, `feroxbuster→gobuster-class`,
   `DCSync→impacket`, `CME→netexec`); source occurrences retained.
3. Tracing: each candidate checked against actual implementation locations
   (`exec/capabilities/`, `chains/tool_registry.py`, `scanners/`,
   `brain/`, `c2/`, `agent/modules/`, `mcp-hub/`, compose services), the
   canonical execution path (`Runtime→Broker→PEP→exec`), and the environment
   (M1/M2.1 container inventory: 14/24 arsenal tools in the kali container,
   1/24 on host).
4. Classification: exactly one primary status per entry (§5 scheme A–G) plus a
   separate governance assessment. Implementation existence, registry/reachability,
   dependency availability, demonstration, and result consumption are tracked as
   **separate claims** and never collapsed into "integrated".

## 3. Headline result

Of **103 deduplicated candidates** (49 tools + 1 tool family + 8 workflows +
8 infrastructure + 38 capabilities), **5 are INTEGRATED AND VERIFIED** — and all
five are the D1 governed-action path and its immediate substrate: the D1
episode workflow, the nmap probe tool (in its bounded invocation), the
kali-tools container, the dvwa/db lab target, and the world-model/hypothesis
cognitive core. **23 entries are implemented but not integrated** (fail-closed
behind deliberately deleted execution bodies and weld gates — the restoration
backlog). **62 are documented or planned only.** **7 are blocked/unavailable**
(services defined but not running or binaries absent). The D1 boundary is the
entire operating frontier: outside one exact request, every path denies.

## 4. Master integration matrix

The full matrix (all 15 fields per entry: ID, candidate, entry type, sources
with section references, intended function, RAPHAEL implementation with
file:line, execution path, environment status, integration status, governance
status, evidence, dependencies, remaining gap, safe treatment, confidence) is
the machine-readable deliverable `reports/tool_integration_inventory_2026-10-05.json`.
Representative rows:

| ID | Candidate | Type | Integration | Governance | Key evidence | Remaining gap |
|---|---|---|---|---|---|---|
| T-01 | nmap | TOOL | **B — integrated, partially verified** | VERIFIED | `exec/capabilities/d1_lab_probe.py` live-verified ×4 (nmap `80/tcp open`, digest-verified artifact); `chains/tool_registry.py:101` executor gated W-01 | broader nmap usage has no authorized path |
| T-02 | sqlmap | TOOL | C | N/A | `tool_registry.py:184` gated; binary in container 1.10.9 | deleted body (by design) |
| T-08 | nuclei | TOOL | C | N/A | `scanners/nuclei_scanner.py` gated; v3.11.0 in container; **templates absent** | templates + authorized dispatch |
| T-18 | bloodhound | TOOL | C | N/A | `tool_registry.py:238` gated; binary in container; **neo4j not running** | authorized dispatch + neo4j |
| T-19 | netexec | TOOL | C | N/A | `tool_registry.py:344` gated; **binary absent** | install + dispatch |
| T-22 | sliver | TOOL | **F — blocked** | N/A | `c2/sliver_backend.py` W-08 stub; service not running | bring-up + restoration decision |
| T-36 | mimikatz-class | TOOL | D | N/A | source §15 mandates fixture treatment | fixture design only |
| T-41 | caldera | TOOL | D | N/A | not installed | emulation platform |
| W-08 | governed D1 episode | WORKFLOW | **A — integrated and verified** | VERIFIED | 4 demo transcripts; 23 tests; kill-switch + denial phases | multi-step generalization (D2, pending authorization) |
| I-01 | kali-tools container | INFRASTRUCTURE | **A** | VERIFIED | running; 14/24 tools; serves D1 | 10 tools absent |
| I-03 | neo4j | INFRASTRUCTURE | **F — blocked** | N/A | compose-defined, not running | start + consumer integration |
| F-09 | Persistence family | CAPABILITY | C | N/A | `agent/modules/` code intact (`exfil.py`, `credtheft.py`, …) but **unreachable** (W-14-gated dispatch); source model class: fixture-only | unreachable by design; fixture design per §15 |
| K-01 | World model with provenance | CAPABILITY | **A** | VERIFIED | `brain/world.py` (schema_version, provenance relationships), canonical stages, suite-tested | graph-search depth |
| K-04 | Capability-selection function | CAPABILITY | B | PARTIALLY VERIFIED | `brain/action.py` `Planner.decide` scores candidates; authorization is a hard constraint at the Broker | info-gain / detection-risk weights (§20.2) not implemented |
| K-10 | Capability→simulation split (§15) | CAPABILITY | B | PARTIALLY VERIFIED | deleted bodies + weld gates + D1 denials demonstrate the split structurally | §15 fixture/simulation instances (design only) |

## 5. Capability-layer assessment (separate from tools)

**Implemented and verified natively (A):** versioned world model with
provenance (`brain/world.py`); hypothesis engine with retained
negative knowledge (`brain/hypothesis.py`, `brain/contradiction.py`).

**Implemented, partially verified (B):** capability selection (planner scores
candidates with authorization as a hard constraint — but §20.2's
information-gain/detection-risk/cost terms are absent); failure classification
(PERSISTENT/TEMPORARY denial classes with planner suppression — verified in
`decide()`); the §15 capability→simulation split (structurally demonstrated by
deleted bodies, weld gates, and live broker denials — but the §15
fixture/simulation instances themselves are design-only).

**Documented/planned (D):** attack-path graph with dead-end detection (§8) —
relationships exist in the world model but no path-search; campaign-grade
durable state with resume (§9) — content-addressed stores exist, no campaign
object; defender model/OPSEC state (§11–12) — nothing; measurable taxonomy
registry (§4) — nothing runtime-side (this audit's inventory is the first);
external hard-zero-gated evaluation (§22 E1.5) — designed, not built.

**Family coverage:** of the blueprint's 28 capability families, 2 have a live
(though narrow) governed implementation (Reconnaissance, Attack-surface
discovery — both via the D1 probe), 9 have gated implementations that would
activate only through deliberate restoration decisions, and 17 are
documentation-only. Per the sources' own model classes, 15 families are
designated fixture/simulation (initial access, credential access, persistence,
lateral movement, C2-lab, identity, cloud, SaaS, edge, web/API, OT/ICS, mobile,
social engineering, impact, supply chain) — RAPHAEL currently represents these
as **fail-closed gates + analytical knowledge, not fixtures**: the source's
mandated safe equivalents (canary-credential fixtures, ICS digital twins,
fixture fleets, consenting-user simulations) do not exist yet. That is the
single largest structured gap between the blueprint and the repository.

## 6. Safety-classification audit (blueprint §15)

All nine §15 high-consequence classes (disruption/DDoS, destructive action,
ransomware-like behavior, bulk credential theft, mass phishing, kernel/driver
evasion, destructive OT, mass exploitation, botnet operation) are
**non-operational in RAPHAEL today**: no execution capability exists for any of
them; the closest artifacts are fail-closed stubs (`mhddos-service` body
deleted, not running) and analytical research documents. The structural split
(K-10) is demonstrated by denial evidence. **No §15 class is represented as a
fixture or simulator yet** — the blueprint's required "safe functional
equivalents" are unbuilt (design-only). This is a compliance *pass* with a
coverage *gap*: understanding is documented, simulation is not built, execution
is (correctly) absent.

## 7. Quantitative summary (denominators explicit)

All counts derive from `reports/tool_integration_inventory_2026-10-05.json`
(103 entries; status legend A–G per task §5).

**Tools (48 single-tool entries + 1 tool family = 49):**
INTEGRATED AND VERIFIED **0** · INTEGRATED BUT PARTIALLY VERIFIED **1** (nmap —
one verified bounded invocation route) · IMPLEMENTED BUT NOT INTEGRATED **14**
(gated executors/wrappers with container-present binaries) · DOCUMENTED OR
PLANNED ONLY **31** · BLOCKED OR UNAVAILABLE **2** (sliver, subfinder — path
exists, dependency absent) · ABSENT 0 · UNDETERMINED 0.

**Capability families (28):** INTEGRATED BUT PARTIALLY VERIFIED **2**
(Reconnaissance, Attack-surface discovery — via the D1 probe) · IMPLEMENTED BUT
NOT INTEGRATED **9** · DOCUMENTED OR PLANNED ONLY **17**.

**Cognitive components (10):** INTEGRATED AND VERIFIED **2** (world model,
hypothesis engine) · INTEGRATED BUT PARTIALLY VERIFIED **3** · DOCUMENTED **5**.

**Workflows (8):** INTEGRATED AND VERIFIED **1** (the governed D1 episode) ·
DOCUMENTED **7**.

**Infrastructure (8):** INTEGRATED AND VERIFIED **2** (kali container, dvwa/db)
· BLOCKED **5** (neo4j, mcp-hub, sliver, service fleet, tor) · DOCUMENTED **1**
(threat feeds).

**Totals (103):** A=5 · B=6 · C=23 · D=62 · F=7 · E=0 · G=0.
**Governance:** VERIFIED 6 · PARTIALLY VERIFIED 5 · NOT APPLICABLE 92 · NOT
VERIFIED 0.

**Interpretation guardrails (per task §9):** no single "percentage complete" is
meaningful. The honest summary: RAPHAEL has **one** verified end-to-end
governed workflow; a reasoning core (world model, hypotheses, contradictions,
failure memory) that is real and tested; a large fail-closed implementation
shelf (23 entries) awaiting deliberate restoration decisions; and a long
documented tail. Tool-installation coverage (14/24 container tools) is a
*dependency* statistic, not a capability-coverage statistic — most installed
tools have no governed invocation path.

## 8. Findings

1. **Operational end-to-end workflows (evidence-backed): exactly one** — the
   governed D1 nmap probe episode, verified four times with full
   receipt/evidence/kill-switch/denial proof.
2. **Installed but not connected:** 13 of the 14 container-present arsenal
   tools (all but nmap) have no authorized invocation path.
3. **Implemented but unreachable:** the fail-closed shelf — 6 tool_registry
   executors, 6 scanner wrappers, `kali_tools_client`, `sandbox.run_code`, the
   c2 family stubs, and the intact `agent/modules/` bodies (persistence/exfil
   code present, dispatch W-14-gated).
4. **Native equivalents without the named tool:** the reasoning core — world
   model, hypotheses/contradictions, denial-feedback failure memory — are real
   code; the blueprint's §20.2 selection function is partially implemented
   (authorization-as-hard-constraint is real at the Broker; info-gain weights
   are not).
5. **Documented/planned only:** 62 entries, including the entire
   fixture/simulation layer the blueprint mandates for §15 classes, and all
   multi-tool workflows.
6. **Dependency/environment blockers:** neo4j, mcp-hub (broken imports),
   sliver, tor-proxy, 10 absent container tools, missing nuclei-templates.
7. **Dispatch/authorization/evidence paths:** intact on the D1 path (verified);
   every other path terminates at a deliberate gate — no broken-by-accident
   paths were found beyond the known defect register (DR-001 sword drift, 18
   structural import failures — unchanged).
8. **Deduplication:** 6 alias groups folded (documented in the JSON
   `dedup_rule`).
9. **Missing proof preventing stronger classifications:** the general tool
   executors are one *authorized decision source* away from integration — but
   no evidence exists that any of them has ever executed in this repository, so
   none can be classified above C.
10. **Source-vs-roadmap conflicts:** none material. The blueprint's §23
    consumption model (directly transferable / adaptable / research-only) is
    consistent with the roadmap's phased restoration; the blueprint's §15
    "never autonomously operational" classes align with the current
    fail-closed state. One nuance: the blueprint's environment note says 0/24
    tools on "the current build host" (2026-10-01) — now 1/24 host, 14/24
    container (M1 brought the lab up); the blueprint note is stale but was
    written before M1.

## 9. Prioritized backlog (planning artifact only — not started)

| # | Item | Source ref | Current state | Area | Dependencies | Governance/evidence condition | Minimum verification | Priority | Blocks |
|---|---|---|---|---|---|---|---|---|---|
| B-1 | Rate-limiter wiring (broker) | blueprint §20.2 budgets; D2 design | component exists, unbound | `brain/rate_limiter.py` + runtime broker construction | none | limits must be policy-driven; denial receipts on breach | policy 6/min → 7th action denied with receipt | **P0** | D2 contract item |
| B-2 | D2 bounded episode (per approved contract) | entry-gate §7 proposal; D2 design freeze | design-only | runtime driver + policy artifact d2-v1 | B-1; operator authorization | every action broker+scope decided; denial/kill-switch proof per run | 2-action episode transcript with per-step receipts | **P0** | M3/D2 |
| B-3 | Action-B HTTP probe capability | D2 design freeze §2 | design-only | `exec/capabilities/` | lab running; identity check | fixed endpoint bound to verified identity; no content capture | metadata+digest artifact, redirect not followed | **P0** | M3/D2 |
| B-4 | nuclei-templates install | PW R2/R7; T-08 | templates ABSENT | kali container | none | allowlisted template set | template run through gated scanner (post-authorization) | P1 | W-02 |
| B-5 | Missing container tools (subfinder/puredns/alterx/netexec/chisel/searchsploit) | blueprint §5; PW R2 | binaries absent | Dockerfile | none | install inventory evidence only | `env_inventory.sh` delta | P1 | W-01 chain, W-05 |
| B-6 | neo4j bring-up + consumer decision | PW R3; T-18 | defined, not running; world model does not consume it | compose + brain | lab running | world-model consumption must stay canonical (no second graph authority) | service healthy + explicit non-consumption note OR integration design | P1 | W-04 |
| B-7 | mcp-hub naming repair + service start | M1 import sweep | imports broken | `src/mcp-hub` | none | wrappers must route through broker like any capability | import sweep delta | P2 | subfinder/gobuster paths |
| B-8 | §20.2 selection weights (info-gain, detection-risk) | blueprint §20.2 | planner scores without them | `brain/action.py` | K-01/K-02 | scoring stays advisory; broker remains sole PDP | scored-vs-selected diff on a deterministic episode | P2 | F-tier reasoning depth |
| B-9 | Attack-path graph search (§8) | blueprint §8 | relationships only | `brain/world.py` or new module | K-01 | path proposals are candidates, never actions | path enumerated on fixture graph | P2 | C-tier reasoning |
| B-10 | §15 fixture/simulation layer (canary creds, fixture fleet, digital twin) | blueprint §15 | absent by design | new fixtures | none | fixtures produce receipts; never operational | fixture behavior documented + receipted | P2 | source-mandated safe equivalents |
| B-11 | Campaign durable state + resume (§9) | blueprint §9 | stores exist, no campaign object | runtime | evidence store | resume preserves evidence integrity | interruption-resume test | P3 | F-tier |
| B-12 | External evaluation harness (E1.5) | blueprint §22; FG R17 | designed only | evaluation | defined scenario suite | verdicts external to the system | held-out scenario verdict record | P3 | evaluation claims |
| B-13 | Defender model / OPSEC state (§11–12) | blueprint §11–12 | absent | brain | B-8 | blueprint-class reasoning only | design review | P3 | E/F-tier |
| B-14 | W-01 body restoration + general executor authorization | roadmap F2 | deleted by design (all 10 bodies) | `chains/tool_registry.py` | operator decision per body | per-body authorization policy + probes; D1-style governance | harmless-exec probe through restored sink with receipt | **operator-gated** | roadmap F2/F3 |

## 10. Limitations

- Import/executable presence was verified for the kali container via the M1/M2.1
  inventory (not re-run against a live container in this audit — the inventory
  is recent and the container image is unchanged since).
- "NONE FOUND" statements are scoped to the inspected locations (src/,
  compose, scripts/, references/); they are not universal absence claims.
- The blueprint's behavioral descriptions were taken as requirements sources at
  face value; their ATT&CK grounding was previously validated
  (`references/BLACK_HAT_GROUNDING_v1.md`, 119/119) and not re-validated here.
- Test execution was performed (suite + D1 tests) — established safe: the suite
  is hermetic, no external activity, protected-tree hashes verified identical.
- 0 candidates UNDETERMINED; every entry carries a confidence rating (48 high,
  5 medium) with reasons in the JSON.

## 11. Deliverable reconciliation

`reports/tool_integration_inventory_2026-10-05.json`: 103 entries — tools 48,
tool family 1, workflows 8, infrastructure 8, capabilities 38. Status totals
A5 / B6 / C23 / D62 / F7 / E0 / G0; governance VERIFIED 6 / PARTIALLY VERIFIED
5 / NOT APPLICABLE 92. Every count in this report is generated from that file.
