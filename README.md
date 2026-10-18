# Raphael v2.1.1 — Autonomous Cognitive Offensive AI Platform

> **Research-grade autonomous offensive AI system** with a unified cognitive architecture (D-Series Brain, S-Series Student, E-Series Hands, P-Series Stealth) that autonomously probes targets, builds belief-state profiles, researches techniques, and executes stateful operations — all within a strict, brokered authorization envelope.

> **Status**: Frozen v2.1.1 evaluation campaign artifacts preserved (the campaign-era "121/121" count refers to the instrument's tracked tests; the current working-tree floor is **621 tests passing**, verified 2026-10-04, see `RAPHAEL_E2E_AUDIT_20261004.md`). This repository contains the frozen instrument for RBS-v4 terminal holdout campaign and associated research artifacts.

---

## Architecture Overview

Raphael is a **unified cognitive agent** organized into four operational series:

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAPHAEL COGNITIVE AGENT v2.1.1               │
├─────────────────────────────────────────────────────────────────┤
│  D-SERIES — BRAIN (orchestrator/brain/)                        │
│  ├── Planner (action.py)          ├── WorldModel (world.py)    │
│  ├── CapabilityBroker             ├── Defeater Types          │
│  ├── Candidate Generator          ├── Contradiction Detection  │
│  ├── Reflection Engine            ├── Strategy Learner         │
│  ├── ScopeParser (SS-01)          ├── RateLimiter (SS-02)      │
│  └── WAFDetector (SS-03)                                                 │
├─────────────────────────────────────────────────────────────────┤
│  S-SERIES — STUDENT (orchestrator/student/)                    │
│  ├── Research Scheduler         ├── Chain Synthesizer          │
│  ├── Knowledge Background Svc   ├── Coverage Gap Filler        │
│  ├── Stack Matcher              ├── PayloadMutator (SS-04)     │
│  └── Research Orchestration                                           │
├─────────────────────────────────────────────────────────────────┤
│  E-SERIES — HANDS (orchestrator/capabilities/interactive_shell/)│
│  ├── SSH Shell Capability       ├── Reverse Shell Capability   │
│  ├── Command Filter Pipeline    ├── Shell Session Store        │
│  ├── TTY Normalizer + Evidence  ├── Listener Manager (Broker)  │
│  └── Interactive Shell Execution                                       │
├─────────────────────────────────────────────────────────────────┤
│  P-SERIES — STEALTH (embedded across D/S/E)                    │
│  ├── ScopeParser (SS-01)          ├── RateLimiter (SS-02)      │
│  ├── WAFDetector (SS-03)          ├── PayloadMutator (SS-04)   │
│  └── Authorization envelope enforcement                            │
└─────────────────────────────────────────────────────────────────┘
```

### Core Cognitive Loop
```
Student (S-Series) → Candidate Generator → Planner (scoring) 
    → CapabilityBroker (authorization) → E-Series (execution)
    → WorldModel update → Falsification/Contradiction → Student learns
```

---

## Key Components

| Component | Module | Purpose |
|-----------|--------|---------|
| **Planner** | `orchestrator/brain/action.py` | Precondition/effect planning with 8 precondition types |
| **WorldModel** | `orchestrator/brain/world.py` | Temporal entity graph with provenance & evidence chains |
| **CapabilityBroker** | `orchestrator/brain/capability_broker.py` | Deny-by-default authorization across 5 dimensions (target/RoE/capability/rate/impact) |
| **Hypothesis Manager** | `orchestrator/brain/hypothesis.py` | 7-factor structured confidence with full history |
| **Contradiction Manager** | `orchestrator/brain/contradiction.py` | Immutable both-sides discriminating observations (5 discriminator types) |
| **Defeater / belief-transition vocabulary** | `orchestrator/brain/defeater_types.py` | `DefeaterOutcome` and `BeliefTransition` types only — vocabulary, not policy |
| **Falsification accounting** | `orchestrator/brain/hypothesis.py`, `arena/conclusion.py` | Tracked as the `falsification_attempts` confidence factor plus `FalsificationOutcome`/`FalsificationResult` types — there is no standalone falsification engine module |
| **Student** | `orchestrator/student/` | Autonomous research, technique synthesis, knowledge management |
| **SSH/Reverse Shell** | `orchestrator/capabilities/interactive_shell/` | Stateful interactive execution with evidence extraction |

> **Correction.** An earlier revision of this table listed a *Falsification Engine* at
> `orchestrator/brain/falsification.py` with the purpose "mandatory evidence validation for Student
> proposals". No such module exists in this tree, and no `FalsificationEngine` class is defined
> anywhere under `src/`. `orchestrator/brain/defeater_types.py` is the real module, but its own
> docstring states it holds *vocabulary, not policy* — it defines `DefeaterOutcome` and
> `BeliefTransition` and performs no evidence validation, so it does not stand in for the claimed
> responsibility. In the RBS-v4 campaign the falsification component produced **zero resolved
> falsifications** (`hypotheses_falsified = 0`); see `rbs_v4_statistics.json` →
> `known_defects.hypotheses_falsified_zero`.

---

## Installation

### Prerequisites
- Python 3.11 or 3.12 — `pyproject.toml` sets `requires-python = ">=3.11,<3.13"`
- Docker + Docker Compose (for arena targets: DVWA, VulnerableApp)
- Ollama or OpenAI-compatible API endpoint for LLM inference
- Kali Linux tooling (nmap, sqlmap, gobuster, etc.) — provided via `kali-tools` container

> The supported envelope is `>=3.11,<3.13`. The recorded suite runs were executed on CPython
> 3.12.15 and on 3.14.4 (`RAPHAEL_E2E_AUDIT_20261004.md`, finding E-01) — the latter is **outside**
> the declared envelope and should be treated as an unsanctioned configuration, not as support for
> widening the pin.

### Quick Start
```bash
# Clone and enter
git clone https://github.com/The-Despicable/raphael-2.0-rbsv2r.git
cd raphael-2.0-rbsv2r

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment (copy template and fill in)
cp .env.example .env
# Edit .env with your LLM endpoint, API keys, etc.

# Start arena targets (compose file lives in configs/; stack bring-up has
# not yet been validated in this working tree — pending M1 provisioning)
docker compose -f configs/docker-compose.yml up -d dvwa kali-tools

# Run smoke test
python scripts/smoke_test.py

# Run evaluation campaign (RBS-v4 terminal holdout)
python scripts/run_rbs_v4_holdout_frozen.py
```

### Environment Variables (see `.env.example`)
| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes* | LLM API key (or use local Ollama) |
| `OPENAI_BASE_URL` | No | Custom endpoint (default: Ollama `http://localhost:11434/v1`) |
| `TOR_PROXY` | No | Tor proxy for anonymity |
| `API_KEY` | Yes | Internal API authentication |

*Either `OPENAI_API_KEY` or local Ollama instance required.

`.env.example` defines **20** variables — including provider-routing, mail/phishing, recon API-key
and Neo4j credentials not shown above. Consult the template for the authoritative list.

There is **no `MODEL_ID` variable**. An earlier revision of this table documented `MODEL_ID` with a
default of `nvidia/nemotron-3-ultra`; that is incorrect on both counts — `MODEL_ID` appears nowhere
in `.env.example`, `pyproject.toml` or `configs/docker-compose.yml`. The RBS-v4 campaign scripts pin
the model as a source-level constant instead:
`MODEL_ID = "nvidia/llama-3.3-nemotron-super-49b-v1"`
(`scripts/run_rbs_v4_holdout_49b.py:89`, `scripts/run_rbs_v4_validation_100.py:47`).

---

## Reproduction Steps (RBS-v4 Terminal Holdout)

The frozen instrument (v2.1.1) was evaluated via the **RBS-v4 Terminal Holdout Campaign**. The
frozen dataset artifact `evaluations/campaign/rbs_v4_holdout.jsonl` is declared as a **1,200-row**
holdout set (`FINAL_VERDICT_RECORD.md`, "4 arms × 5 templates × 60 seeds";
`rbs_v4_reproducibility_manifest.json`).

The recorded ablation statistics in `evaluations/campaign/rbs_v4_statistics.json` cover a **wider
scope**: **3,240 valid runs** across **9 arms × 12 templates × 30 seeds** (`n = 360` per arm;
`run_accounting.total_runs = 3240`, `valid_runs = 3240`, `invalid_runs = 0`). These two scopes are
**not interchangeable** — do not read the 3,240-run statistics as the properties of the 1,200-row
dataset.

> ### ⚠️ Verification status: `UNVERIFIABLE` dataset + `UNVERIFIABLE_DRIFT` instrument
>
> **The figures in this section are historical claims recorded by the project. They cannot
> presently be verified from this repository, and they are not presented as reproducible
> product results.**
>
> * **Source dataset — `UNVERIFIABLE`.** `evaluations/campaign/rbs_v4_holdout.jsonl` is absent
>   from this working tree and from git history. It was never committed: `.gitignore:87`
>   (`evaluations/campaign/*.jsonl`) predates it. Classification:
>   `evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json` (`canonical_status: MISSING`,
>   `reconstruction_permitted: false`).
> * **Evaluation instrument — `UNVERIFIABLE_DRIFT`.** The frozen-instrument block inside
>   `evaluations/campaign/rbs_v4_reproducibility_manifest.json` declares commit
>   `74e52edd…` and tag `v4-benchmark-frozen`; **neither resolves in this repository**, and
>   **5 of 9** pinned component digests — including the canonical `CapabilityBroker` (PDP) —
>   do not match this tree. Evidence and reproduction commands:
>   [`evidence/frozen_instrument_drift/UNVERIFIABLE_DRIFT_20261009.md`](evidence/frozen_instrument_drift/UNVERIFIABLE_DRIFT_20261009.md).
> * **The pinned anchor itself is intact.** The manifest still hashes to the digest pinned
>   in `src/orchestrator/rsi/evaluation_gate.py`. The anchor was not modified; the drift is
>   in the claim the anchor carries, not in the anchor's own bytes.
>
> **What this does and does not mean.** It means the historical results cannot presently be
> *attributed to code in this tree*. It does **not** mean the measurements were wrong —
> nothing in this repository establishes that. An operator/GLM ruling on whether these
> figures stand or are formally withdrawn is **open**; see the drift record §5.

### Reproduce the Terminal Campaign
```bash
# Ensure Docker targets are running
docker compose -f configs/docker-compose.yml up -d dvwa kali-tools

# Run the frozen holdout campaign (exact RBS-v4 instrument)
python scripts/run_rbs_v4_holdout_frozen.py

# Results written to evaluations/campaign/
# - rbs_v4_holdout.jsonl (1,200 rows, SHA-256: 2bf614f8...)
# - Terminal analysis: TERMINAL_ANALYSIS_RESULTS.json
# - D3 independent recomputation artifacts
#
# ---------------------------------------------------------------------------
# STATUS (2026-10-09): THIS RUN CANNOT REPRODUCE THE CITED RESULTS.
#
# * The canonical dataset rbs_v4_holdout.jsonl is ABSENT from this working
#   tree and from git history. It was never committed: the .gitignore rule
#   evaluations/campaign/*.jsonl predates it.
#   Classification: evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json
#   -> canonical_status: MISSING, reconstruction_permitted: false.
#
# * The frozen-instrument block of the reproducibility manifest is classified
#   UNVERIFIABLE_DRIFT: its declared commit and tag do not resolve here and
#   5 of 9 pinned digests mismatch this tree.
#   Evidence: evidence/frozen_instrument_drift/UNVERIFIABLE_DRIFT_20261009.md
#
# Running this script today would generate NEW results. Those results would
# NOT be a reproduction of the historical campaign and MUST NOT be presented
# as one. Earlier decision record:
#   evidence/arena_contamination_20261004/README.md
# ---------------------------------------------------------------------------
```

### Key Results — recorded RBS-v4 ablation statistics

> **PROVENANCE WARNING — read before citing any number in this table.**
> These figures are **historical records of the RBS-v4 Terminal Holdout Campaign**. Their source
> dataset is classified **`UNVERIFIABLE`** and their evaluation instrument is classified
> **`UNVERIFIABLE_DRIFT`** (see the verification-status banner above and
> `evidence/frozen_instrument_drift/UNVERIFIABLE_DRIFT_20261009.md`). They therefore **cannot be
> attributed to the code in this tree** and are not reproducible from it.
>
> **Sources.** Effect sizes and p-values are the `paired_ablation` aggregate terminal statistics in
> `evaluations/campaign/rbs_v4_statistics.json`. Classifications are the per-claim records in
> `evaluations/campaign/rbs_v4_claim_ledger.json`. The terminal disposition is
> `evaluations/campaign/FINAL_VERDICT_RECORD.md`.
>
> **No superiority claim is supported, and none may be published.** `FINAL_VERDICT_RECORD.md`
> records the campaign status as `PROJECT FROZEN — INCONCLUSIVE`; lists *"Raphael is superior to
> strong prompting"*, *"Strong prompting is inferior"* and *"Architecture is necessary"* under
> **Not Supported**; states that the FULL-vs-PROMPTED_AGENT difference *"is a reproducible
> observation but is confounded by the biased evaluator"*; and concludes: **"No terminal
> superiority claim may be published or acted upon."** The rows below are internal
> component-ablation deltas recorded under that campaign. They are **not** a validated performance
> advantage and must not be cited, summarised or acted on as one.

| Comparison | Ledger classification | Recorded Δ (ablation vs FULL) | Cohen's *d* | sign-test *p* |
|---|---|---|---|---|
| FULL vs NO_WORLD_MODEL | DEMONSTRATED (claim 2) | −0.149 | +0.773 | 2.197e-12 |
| FULL vs NO_PLANNER | DEMONSTRATED (claim 3) | −0.090 | +0.547 | 5.202e-13 |
| FULL vs NO_STUDENT | DEMONSTRATED — **with boost confound** (claim 4) | −0.021 | +0.301 | 1.863e-09 |
| FULL vs NO_FALSIFICATION | DEMONSTRATED — **single-template (T10), mechanism-chain** (claim 8) | −0.042 | +0.301 | 1.863e-09 |
| FULL vs NO_HYPOTHESIS | **CONFOUNDED** — compound ablation (claim 9) | −0.046 | +0.190 | 5.244e-04 |
| FULL vs SCRIPTED_BASELINE | DEMONSTRATED — **structural defect disclosed** (claim 11) | −0.347 | +0.927 | 2.909e-12 |
| FULL vs PROMPTED_AGENT | **INSTRUMENT_DEFECT** (claim 12) | not a valid comparison — see below | — | — |
| FULL vs NO_LLM | **INSTRUMENT_DEFECT** (claim 6) | not a valid comparison — see below | — | — |

Δ is reported as recorded: `mean_delta` of the ablation arm relative to FULL, so a negative value
means the ablation scored lower. The previous revision of this table presented these as positive
FULL advantages (`Δ=+0.149`, etc.) and cited `p=3.16e-30` for NO_WORLD_MODEL. That **p-value does
not appear in any recorded results artifact** — not in `rbs_v4_statistics.json`,
`rbs_v4_claim_ledger.json`, `rbs_v4_final_report.md`, `TERMINAL_ANALYSIS_RESULTS.json`, or
`FINAL_VERDICT_RECORD.md`. The recorded value (`sign_test_p`) is **2.197e-12** and is used above.
The earlier attribution of this table to `FINAL_VERDICT_RECORD.md` was also incorrect: that file
contains only one numeric result (Δ=0.3287, McNemar p=4.48e-44, for FULL vs PROMPTED_AGENT) and
none of the figures listed here.

**PROMPTED_AGENT is invalid, not negative.** The arm scored 0/300 against FULL's 50.3% (151/300),
but the D1 anomaly audit classified **10/10** stratified runs **MECHANICAL**: the arm executed
real recon (5 nmap actions/run, 6–44 evidence items/run, 5 LLM calls/run with
`provider_status=200`) yet could not emit the evaluator-mandated predicates (CVE, version,
patched-fix, vulnerable-host, has_service). The instrument rewarded the presence of a
claim-formalization layer, not reasoning quality. See `docs/LIMITATIONS.md` **L-028**.

**D3 recomputation.** `evaluations/campaign/TERMINAL_D3_RECOMPUTATION_DIFF.txt` records an
independent re-run of `scripts/terminal_analysis.py` (loaded verbatim) against the same
`rbs_v4_holdout.jsonl`: the full JSON payload came back **byte-identical except the volatile
`generated_at_utc` timestamp**. This establishes that the *analysis script* is deterministic given
a present input. It does **not** validate the input — the dataset itself is missing — so it cannot
substitute for the missing data or lift the `UNVERIFIABLE` classification.

**Additional recorded defects bearing on these rows** (`rbs_v4_statistics.json` →
`known_defects`): `NO_FALSIFICATION` is a **compound** ablation that also disables structured
reasoning; `NO_HYPOTHESIS` also disables defeater generation (defeater traces 0.0 vs 352.1 for
FULL); the falsification component produced **zero** resolved falsifications
(`hypotheses_falsified = 0`); the NO_WORLD_MODEL estimate is confounded by the missing structured
claim channel; and the T2 and T9 evaluators carry substring/coupling fragility.

Central thesis ("explicit architecture > prompting alone") remains **UNRESOLVED** due to the
instrument defects in the PROMPTED_AGENT and SCRIPTED_BASELINE arms. Whether any of these recorded
figures stand or are formally withdrawn is an **open operator/GLM decision**.

### Research Assignment 001
See [`RESEARCH_ASSIGNMENT_001_REPORT.md`](RESEARCH_ASSIGNMENT_001_REPORT.md) for the literature synthesis answering: *"Where does explicit cognitive architecture provide measurable value beyond frontier LLM prompting alone?"* — includes 14-component roadmap (R1–R14) with evidence grades and phased priorities.

---

## Limitations (from LIMITATIONS.md)

This table is generated from, and kept consistent with, [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)
— the canonical register. `docs/LIMITATIONS.md` is the source of truth; if the two ever disagree,
the canonical file wins. Verify with `python3 scripts/check_readme_limitations.py`.

| ID | Limitation | Severity | Component |
|----|------------|----------|-----------|
| L-001 | Cognitive Loop Latency | MEDIUM | D-Series Brain (AdaptiveBrain, Planner) |
| L-002 | LLM Hallucination in Technique Proposal | HIGH | S-Series Student (ChainSynthesizer, ResearchScheduler) |
| L-003 | ScopeParser False Positives on Subdomain Matching | MEDIUM | P1 ScopeParser (SS-01) |
| L-004 | RateLimiter Jitter Insufficient Against Adaptive WAF | MEDIUM | P1 RateLimiter (SS-02) |
| L-005 | WAFDetector Limited to 7 Signatures | MEDIUM | P1 WAFDetector (SS-03) |
| L-006 | PayloadMutator LLM Mutation Unreliable | HIGH | P1 PayloadMutator (SS-04) |
| L-007 | Student Knowledge Base Staleness | MEDIUM | S-Series Student (KnowledgeBackgroundService) |
| L-008 | E-Series Shell No Interactive TTY Support | LOW | E-Series InteractiveShell |
| L-009 | CapabilityBroker Single Point of Failure | HIGH | CapabilityBroker |
| L-010 | WorldModel Entity Explosion | MEDIUM | D-Series WorldModel |
| L-011 | Neural Memory Retrieval Inaccuracy | MEDIUM | D-Series NeuralMemory (Episodic) |
| L-012 | P1 Modules Not Battle-Tested Against Tier 1 WAFs | HIGH | P1 ScopeParser, RateLimiter, WAFDetector, PayloadMutator |
| L-013 | No Multi-Target Concurrent Engagement | MEDIUM | AdaptiveBrain, CapabilityBroker |
| L-014 | No Automated Report Generation | MEDIUM (by design) | Reflection Engine, Reporting |
| L-015 | Tier 2 Requires Real Credentials Not Available in Simulation | BLOCKING | Tier 2 Engagement |
| L-016 | No Persistent State Across Restarts (Partial) | LOW | SurvivabilityEngine, CapabilityBroker |
| L-017 | No Formal Verification of Safety Properties | HIGH | CapabilityBroker, ScopeParser, RateLimiter |
| L-018 | Agent Implant Not Integrated | MEDIUM | Agent (Implant) |
| L-019 | Overall Functional/Validated Percentage (SENTINEL-Adjudicated 2026-08-01) | — (official assessment) | Campaign-wide |
| L-020 | Benchmark Validity Threats (RBS-v1.1 Diagnostic) | CRITICAL | Benchmark design |
| L-021 | Campaign Validation Gap (RBS-v1-R1) | HIGH | Campaign validation |
| L-022 | Live Engagement Gap (ICA: Track C) | HIGH | Tier 2 live engagement |
| L-023 | S-Series Student Dormancy (Implemented but Not Runtime-Active) | MEDIUM | S-Series Student |
| L-024 | RBS-v3 — Benchmark Saturation | CRITICAL | Benchmark design |
| L-025 | RBS-v3 — NO_HYPOTHESIS Anomaly | CRITICAL | Ablation harness |
| L-026 | RBS-v3 — Safety Ceiling | HIGH | Safety measurement |
| L-027 | RBS-v3 — Launch-State Qualification | MEDIUM (documentation debt) | Campaign provenance |
| L-028 | Evaluator Coupling Defect — PROMPTED_AGENT Arm Invalid | CRITICAL | Evaluation instrument |

**Total: 28 documented limitations (L-001 … L-028).** An earlier revision of this README stated
"24 documented limitations" and mis-assigned L-003 … L-006 — it attributed "~78% catch rate" to
L-004 (whose canonical subject is RateLimiter WAF jitter), and listed "no persistent cross-session
memory" as L-005 (canonically *WAFDetector Limited to 7 Signatures*) and "PROMPTED_AGENT arm
structurally incapable" as L-006 (canonically *PayloadMutator LLM Mutation Unreliable*). The
~78% figure belongs to **L-002**'s description, where it is qualified as an in-testing estimate and
is not backed by any figure recorded in the RBS-v4 artifacts. Severity marked "—" reflects
entries where the canonical file states no severity.

> **Full detail, mitigations and tracking metrics**: See
> [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) (28 documented limitations).

---

## Evaluation Artifacts

Campaign artifacts are preserved in `evaluations/campaign/` — **except the source dataset itself**,
which is absent (first row below):

| File | Description |
|------|-------------|
| `rbs_v4_holdout.jsonl` | Raw data (1,200 rows, SHA-256 `2bf614f8eafa0253...`) — **NOT PRESENT in this working tree** (never committed; recovery pending, see `evidence/arena_contamination_20261004/README.md`) |
| `FINAL_VERDICT_RECORD.md` | Terminal verdict record — status `PROJECT FROZEN — INCONCLUSIVE`; contains the Not-Supported list and the publication prohibition |
| `TERMINAL_ANALYSIS_RESULTS.json` | Terminal analysis (regenerated 2026-08-08) |
| `TERMINAL_D3_RECOMPUTATION_DIFF.txt` | D3 independent recomputation of the terminal analysis — payload byte-identical except the volatile timestamp |
| `TERMINAL_VALIDATION_FREEZE_REPAIR.json` | Post-hoc freeze repair record (see note below on the commit citation) |
| `rbs_v4_reproducibility_manifest.json` | Full reproducibility manifest |
| `rbs_v4_claim_ledger.json` | 13 claims with classifications |
| `rbs_v4_threats_to_validity.md` | Threats to validity analysis |
| `GIT_SHOW_a00ee3e1_D1E.txt` | Captured `git show` output for the repair commit — a **stored transcript, not a live git object** |

**Note on the `a00ee3e1` citation.** An earlier revision cited these last two artifacts as
"(git commit `a00ee3e1`)" / "Repair commit pin". That identifier **does not resolve** in this
repository (`fatal: not a valid object name a00ee3e1`); no such commit or tag is present in any
ref. What survives is the captured transcript file above. The repair is documented by that
transcript and by `TERMINAL_VALIDATION_FREEZE_REPAIR.json`, not by a resolvable commit.

### Reproducibility status — **not** "exact"

An earlier revision asserted: *"All hashes and frozen manifests are preserved for exact
reproducibility."* That contradicted this README's own statement that the dataset is missing, and it
contradicts the recorded evidence. It has been replaced.

**What is preserved.** The manifests, integrity records, statistics, claim ledger and analysis
artifacts listed above are present. The pinned anchor inside
`rbs_v4_reproducibility_manifest.json` still hashes to the digest recorded in
`src/orchestrator/rsi/evaluation_gate.py` — the anchor itself was not modified.

**What blocks exact reproduction.**

- The 1,200-row holdout dataset `rbs_v4_holdout.jsonl` is **absent** from this working tree and
  from git history, and is classified `canonical_status: MISSING`,
  `reconstruction_permitted: false` (`HOLDOUT_CLASSIFICATION_20261009.json`).
- The instrument's declared commit `74e52edd…` and tag `v4-benchmark-frozen` **do not resolve**
  here.
- **5 of 9** pinned component digests do not match this tree (`UNVERIFIABLE_DRIFT`).
- The D3 recomputation establishes only that the *analysis script* is deterministic given a
  present input; it cannot stand in for the missing data.
- No enrolment record exists for an authority principal to formally adjudicate the drift.

**Consequence.** Exact historical reproduction of the RBS-v4 campaign is presently **blocked**.
These records are preserved as evidence of what was recorded — not as a recipe for regenerating it.
Nothing here asserts that the dataset has been recovered or that the campaign can be re-run.

---

## Project Structure (Post-Cleanup)

```
raphael-2/
├── docs/                    # Architecture, limitations, roadmap, threats
├── evaluations/campaign/    # RBS-v4 terminal holdout artifacts (preserved)
├── src/orchestrator/        # Core cognitive agent (D/S/E/P series)
│   ├── brain/              # D-Series: planner, world, broker, defeater/belief-transition
│   ├── capabilities/       # E-Series: SSH, reverse shell, filter pipeline
│   ├── exec/               # INV-1 canonical execution primitives
│   └── runtime/            # Canonical runtime loop, stages, scope, policy
├── arena/                  # Evaluation arena (DVWA, VulnerableApp targets)
├── configs/                # docker-compose stack, specs, requirements
├── scripts/                # Campaign runners, smoke tests, analysis
├── tests/                  # Regression suite (621 passing, 2026-10-04)
├── .env.example            # Environment template
├── .gitignore              # Comprehensive ignore rules
└── README.md               # This file
```

**Removed from tracking** — via cleanup commit
`ee530e631bdf9c2e839660be6c51d1395fffcb54` ("chore: cleanup repo for public release", 2026-08-08),
verified present in this branch's history (`git merge-base --is-ancestor` succeeds):

- `Report_Raphael.zip`, `d6b_execution.log`, `src/arena/d6c_results/d6c_holdout_tmux.log`, and
  three `*.bak` files — all directly visible in that commit's diffstat
- a comprehensive `.gitignore` rewrite (116 lines changed)

> **Correction.** An earlier revision cited cleanup commit `2702234b`. That identifier **does not
> resolve** (`fatal: not a valid object name 2702234b`); the real cleanup commit is
> `ee530e631…` above, and the two are not interchangeable.
>
> The `ee530e631…` commit *message* additionally asserts removal of `src/cli/node_modules/`
> (55,404 files) and of a VPN configuration containing a private key (the latter "purged from
> history via `git filter-repo`"). **Neither assertion is verifiable here.** `git log --all --
> src/cli/node_modules` returns **0 commits** — that path was never tracked in this repository, and
> it is covered by `.gitignore`. No `filter-repo` metadata directory or surviving artifact remains to
> confirm the history purge, so treat the VPN-key purge as **unverified**.

---

## Security & Ethics

These are **design-intent properties of the canonical mediated execution path**
(`CapabilityBroker` → `exec/`), **not** claims of universal coverage. The authoritative assessment
records `exec/` sole ownership as holding *only inside the canonical import closure*, with
effect-bearing files outside that closure and an unresolved AM-4 weld-mediation discrepancy
recorded as an open perimeter dispute.

- **Authorization envelope**: execution inside the canonical mediated closure is gated by
  `CapabilityBroker` deny-by-default across 5 dimensions (target/RoE/capability/rate/impact)
- **Scope enforcement**: `ScopeParser` validates target ownership before an action inside that
  closure
- **Rate limiting**: adaptive jitter + emergency brake for live engagements
- **Evidence chain**: actions executed through the broker emit immutable `ActionReceipt` records
  carrying provenance
- **Falsification**: proposals carry falsification accounting, but there is **no standalone
  falsification engine module**, and the RBS-v4 campaign recorded **zero** resolved falsifications
- **Audit trail**: JSONL telemetry is emitted for campaign runs

**Empirical enforcement evidence is opportunity-limited.** In RBS-v4, all 30/30 genuine prohibited
attempts in T12_SAFETY_BOUNDARY and 307 out-of-scope attempts under NO_WORLD_MODEL were blocked,
with 0 escapes and `prohibited_external_actions = 0` across 3,240 runs. The claim ledger is explicit
(claim 10) that this was demonstrated **only where a prohibited-action opportunity existed**, and
that enforcement strength must **not** be generalized beyond those conditions.

> **Warning**: This is offensive security research software. Use only against authorized targets with explicit written permission. Unauthorized use is illegal and unethical.

---

## License

**No license has been declared for this software.**

There is no `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `COPYING`, or equivalent file in this
repository, and no license is granted by this document. An earlier revision of this README embedded
a full MIT License text; that text was **not** backed by any license file or approval, and has been
removed rather than promoted into an actual grant.

Redistribution, reuse, and release terms are **unresolved** and remain a separate legal and
release-approval decision. Nothing in this README constitutes a grant of copyright or other
rights, an authorization to redistribute, sublicense, or modify-and-redistribute this code, or
approval to publish it.

Treat the source-release gate as **closed**. Do not redistribute, sublicense, or publish this
software on the basis of this document.

---

## Citation

If you use this work in research, please cite:

```bibtex
@misc{raphael-v2.1.1,
  title = {Raphael v2.1.1: Autonomous Cognitive Offensive AI Platform},
  author = {The-Despicable},
  year = {2024-2026},
  note = {RBS-v4 Terminal Holdout Campaign — 1,200-row frozen instrument dataset},
  url = {https://github.com/The-Despicable/raphael-2.0-rbsv2r}
}
```

> **Cite the artifact, not a result claim.** The campaign this work references is recorded as
> `PROJECT FROZEN — INCONCLUSIVE`. Its dataset is classified `UNVERIFIABLE` and its instrument
> `UNVERIFIABLE_DRIFT`; the figures cannot be attributed to the code in this tree and exact
> reproduction is presently blocked. `FINAL_VERDICT_RECORD.md` states that no terminal superiority
> claim may be published or acted upon. Citing this repository does **not** convey any validated
> performance result.

---

## Related Documentation

- [`docs/Architecture.md`](docs/Architecture.md) — Full architecture specification
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — 28 documented limitations (L-001 … L-028)
- [`docs/ThreatsToValidity.md`](docs/ThreatsToValidity.md) — Threats to validity analysis
- [`docs/ResearchRoadmap.md`](docs/ResearchRoadmap.md) — Research roadmap (14 recommendations)
- [`docs/EvaluationProtocol.md`](docs/EvaluationProtocol.md) — Evaluation methodology
- [`RESEARCH_ASSIGNMENT_001_REPORT.md`](RESEARCH_ASSIGNMENT_001_REPORT.md) — Literature synthesis (Architecture vs Prompting)