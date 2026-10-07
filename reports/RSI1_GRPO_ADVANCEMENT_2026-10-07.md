# RAPHAEL — RSI-1 AND GRPO ADVANCEMENT REPORT — 2026-10-07

**Task**: RSI-1 — implement the verified-experience learning substrate, audit GRPO
feasibility, and select the earliest defensible improvement path. Branch
`offensive-restore`, HEAD `e6a8c707e` (unchanged). Nothing committed; no provider
calls; no credential access; protected evidence byte-identical (final check below).

---

## 1. Preflight and preservation

- Branch/HEAD/worktree preserved throughout; stashes untouched (9).
- Gate 0 re-verified first: all 40 D2 remediation tests pass; the hardened
  objective evaluator (`stages.py::_verify_objective_action`,
  `exec/artifact_verify.py`) and the policy step-cap (`max_episode_steps: 5`)
  are active. Suite before this task: 758/758.
- Training-environment inventory (local inspection only): torch 2.14.1+cu130
  **CPU-only in this environment** (CUDA driver 12080 too old for the cu130
  build — `torch.cuda.is_available()` is False); transformers 5.18.0 present;
  `trl`/`peft` **not installed**; the only locally cached model is a **GGUF**
  inference-format file (not trainable weights); no model weights, no training
  checkpoints, no optimizer/reference infrastructure, no training API access.

## 2. RSI implementation inventory (before this task)

| Component | State before RSI-1 |
|---|---|
| Runtime/Broker/PEP, evidence store, hardened objective evaluator | VERIFIED (Gate 0 PASS) |
| ExplorationPolicy v0 (identity, hash, restricted parameters) | VERIFIED (RSI-0) |
| `ExperienceNode`, experience ingestion | MISSING |
| `ImprovementHypothesis` + falsification records | MISSING |
| Policy lifecycle (`evaluated`/`accepted-for-review`/`rejected`), lineage fields | MISSING |
| Experiment snapshots / read-only replay | MISSING |
| Promotion/rollback, holdout, external evaluator | MISSING/BLOCKED (operator gates) |

## 3. Track A — RSI learning substrate (implemented this task)

**A.1 ExperienceNode** — `src/orchestrator/rsi/experience.py`
- Canonical fields per v4.2 §15.2 (identity, mission/episode, policy id/version/
  content-hash, action/decision refs, **verified** evidence refs, outcome,
  terminal reason, steps/denials/hard-violations, wall time, parent links,
  schema version), deterministic canonical serialization, SHA-256 content hash,
  `from_dict` identity enforcement, `__post_init__` validation.
- Distinction preserved: an ExperienceNode references EvidenceRecord identities;
  it never duplicates their payloads and an `objective_met` node **requires**
  evidence refs.
- `ExperienceLog`: append-only ledger; idempotent duplicates; content conflicts
  refused; disk round-trip verified.

**A.2 Trusted ingestion** — `ingest_episode(store, run_record, episode_id, roots)`
- Re-derives the outcome from the **persisted store through the canonical
  verifier** (`stages._verify_objective_action`) — the run record's own claims
  are not trusted.
- Fabricated `ok` records (nothing executed) downgrade to `objective_not_met`;
  cross-episode records (foreign `mission_id`) cannot satisfy the objective;
  genuinely failed episodes ingest honestly as `failed`.
- Duplicates are idempotent (same content ⇒ same experience id); historical
  evidence is never mutated; rejections carry reasons.

**A.3 ImprovementHypothesis** — `src/orchestrator/rsi/hypothesis.py`
- Problem, causal claim, **experience-backed** evidence refs, permitted
  dimensions (v0 evolvable surface = `candidate_order`, `bounded_retry` only —
  anything else is refused at construction), expected effect, **mandatory
  falsification condition**, confounders, status lifecycle
  (`proposed→under_evaluation→supported|rejected|inconclusive`), content hash.
- `FalsifiableEvaluation.verdict()` is a mechanical rule: violations ⇒ rejected
  (never compensable); candidate verified-rate > baseline ⇒ supported; tie ⇒
  rejected; exclusions dominating ⇒ inconclusive.

**A.4 ExplorationPolicy lifecycle** — `exploration_policy.py` extended without
breaking v0 identity: statuses `experimental → evaluated → accepted-for-review |
rejected` (deliberately **no `active`/`promoted` status**), optional lineage
fields (`parent_policy_hash`, `hypothesis_id`, `experiment_id`,
`change_description`) that are identity-bearing only when set. Verified: the
RSI-0 C0 policy hash is unchanged (`6fae82c2…`, matches the RSI-0 manifest).

**A.5 Learning/deployment separation** — nothing in the new modules writes
policies, touches the Broker/PEP, or mutates the Student; ingestion is
append-only to a separate experience ledger.

## 4. Track B — snapshots and falsifiable comparison

**B.1** `src/orchestrator/rsi/snapshot.py`: `ExperimentSnapshot` binds
experiment id, candidate hashes, persisted-store paths, scenario descriptions,
evaluator version, manifest digest, and parent experience ids into one
content-hashed record; `verify_snapshot()` performs **read-only replay** — it
re-derives objective outcomes from the persisted stores via the canonical
evaluator, labels every result `replay: true`, and flags fabricated records as
unverified (tested).
**B.2/B.3** `FalsifiableEvaluation` (above) records the pre-declared criterion
and its mechanical verdict; the holdout remains absent, so generalization and
promotion claims stay **blocked** (unchanged).

## 5. Track C — GRPO feasibility (evidence-backed)

| Requirement (paper §4.1.1–4.2) | RAPHAEL environment |
|---|---|
| Trainable policy with log-probabilities | **Absent** — no LM policy object, no log-prob API, no adapter |
| Model weights / training interface | **Absent** — GGUF cache only; no API training access; InferX-via-OpenCode grants nothing to RAPHAEL |
| Optimizer + reference-policy management | torch/Adam exist; nothing binds them to a RAPHAEL policy |
| Reward computation | Verified outcome rewards now derivable (Gate 0 + ingestion) — the one satisfied prerequisite |
| Infrastructure | CPU-only torch in this environment (CUDA driver too old for the cu130 wheel); no trl/peft |

**Path decision**: **Path 1 (policy-level group-relative evaluation) is the
earliest feasible and scientifically useful path** — it is implemented and
verified (RSI-0/0.1 + this task's substrate). Path 2 is **not currently
feasible** (no policy abstraction/log-probs); Path 3 (model-level GRPO) is
**BLOCKED** with concrete prerequisites: a trainable policy abstraction,
weights or a weight-hosting training substrate, token log-probabilities,
training/eval separation, and an authorized training environment.

**C.4 contained prototype — implemented and executed** (`rsi/grpo_proto.py`,
result in `/tmp` during verification, re-runnable): real GRPO mechanics on a
tiny MLP over benign abstract states — group sampling (G=8), group-relative
advantages, clipped surrogate + KL-to-frozen-reference, Adam updates. Observed
(seed 20261007, 300 episodes, ~4 s CPU): greedy mean reward **−0.88 → +1.07**
(optimal), group mean −0.35 → +1.07, stable convergence. This demonstrates the
mechanics are correctly implemented; it demonstrates nothing about RAPHAEL
capability and is labeled accordingly inside the module's output.

## 6. Test results

| Command | Result |
|---|---|
| `pytest tests/test_rsi1_learning_substrate.py -q` | **18 passed** |
| `pytest tests/test_m3_d2_remediation.py tests/test_m3_d2_bounded_execution.py tests/test_m2_d1_governed_action.py -q` | 88 passed (Gate-0/D1/D2 regression) |
| `pytest tests/ --no-header -q` (full suite) | **776 passed / 0 failed / 0 skipped** (121.6 s) |
| Protected-tree hash comparison | **identical** |

## 7. Definition of Done

| Requirement | Verdict |
|---|---|
| ExperienceNode with verifiable evidence lineage | **PASS** |
| Ingestion rejects invalid provenance; duplicates idempotent | **PASS** |
| ImprovementHypothesis with falsification criteria | **PASS** |
| Policy versioning/hash restricted to permitted parameters | **PASS** (v0 identities preserved) |
| Candidate lineage (hypothesis↔policy↔experiment↔outcome) | **PASS** (lineage fields + snapshot) |
| Snapshots preserve history; replay is side-effect-free | **PASS** (replay labels + read-only stores) |
| Evaluation without automatic promotion | **PASS** (no promotion surface exists; lifecycle has no active status) |
| D1/D2 governance and safety boundaries intact | **PASS** (88-test regression + full suite) |
| GRPO trainability inspected from the environment | **PASS** (inventory above) |
| GRPO distinguished from strategy ranking | **PASS** (prototype labeled; report language enforced) |
| Recommended path justified by observed capabilities | **PASS** (Path 1) |
| Blockers concrete for Paths 2/3 | **PASS** (listed above) |
| No training run claimed without real machinery | **PASS** (prototype explicitly scoped; LLM training absent) |

**Decision: RSI FOUNDATION READY FOR EVALUATION** + **GRPO PROTOTYPE FEASIBLE**
(contained toy scope, executed) — with model-level GRPO **BLOCKED —
PREREQUISITES IDENTIFIED**. These coexist as permitted.

## 8. Remaining gaps, risks, next milestone

- **Holdout absent** → promotion/transfer claims stay blocked (operator decision).
- **Unsigned local ledger** → evidence trust is process-based; attestation is a
  future hardening item before any real promotion milestone.
- **PEP-failure continuation** unsupported (RSI-0.1) — retry semantics remain
  qualified; a runtime-design decision is required before broadening.
- **Path 2 prerequisites**: policy abstraction exposing log-probabilities,
  training/eval split, checkpoint versioning; trl/peft absent; CUDA driver too
  old for the installed wheel (CPU training only).
- **Smallest next milestone (RSI-2 candidate)**: wire the ingestion into a
  persistent experience ledger over repeated RSI-0 scenario runs, then rank
  hypothesis-backed ExplorationPolicy candidates using FalsifiableEvaluation —
  still offline, still no promotion.

## 9. Files added/modified by this task

Added: `src/orchestrator/rsi/{experience,hypothesis,snapshot,grpo_proto}.py`,
`tests/test_rsi1_learning_substrate.py`. Modified:
`src/orchestrator/rsi/exploration_policy.py` (lifecycle + optional lineage
fields, v0 identity preserved), `src/orchestrator/rsi/experience.py` (result
carries the node). Preserved: everything else, including all RSI-0/0.1
evidence, D1/D2 files, and both policy artifacts.
