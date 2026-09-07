# P3.11 §14.10 MVP Demonstration — Evidence Package

**Starting HEAD:** `5630cd215be251b459fae5e88e8de08822454f19` (GLM-reviewed remediation HEAD)
**Implementation HEAD:** `fc83a61796c0bf78cb136f553a7d4f1f431823da`
**Branch:** `weld-sub10-evidence`
**Working tree at capture:** clean except this evidence directory (committed below)

All transcripts below were produced at the implementation HEAD unless
labeled `clean_checkout` (pristine `git worktree` at the same HEAD).

---

## 1. Repository identity

- repo: `/home/yaser/external-audits/raphael-2`
- branch: `weld-sub10-evidence`
- starting HEAD: `5630cd215` (matches GLM ruling)
- final HEAD: `fc83a617` (this package)
- interpreter: Python 3.14.4 (declared range `>=3.11,<3.13` — mismatch disclosed, same as prior rounds)
- pytest: 9.1.1

## 2. Changed files (exact)

- `src/orchestrator/runtime/stages.py` — Planner wiring, denial feedback, contradiction trigger, replan report
- `src/orchestrator/runtime/loop.py` — mission candidate threading, denial-continue, output collectors
- `tests/p311_mvp_mission.json` — the one deterministic mission fixture (NEW)
- `tests/test_p311_mvp_demonstration.py` — §14.10 chain tests (NEW, 3 tests)
- `tests/test_p311_adversarial_probes.py` — §14.12 probes (NEW, 13 tests)
- `evidence/p311_mvp/` — this package (NEW)

## 3. §14.10 demonstrated causal chain (machine-executed)

Mission `p311-mvp-001` (`tests/p311_mvp_mission.json`, scope hash
`f10f5fbd430e…` — see `p311_decision_trace.json` for the full hash):

1. **mission file** → loaded deterministically (`test_p311_mvp_mission_file_is_deterministic`)
2. **scope** → `ScopeV0.from_dict`, `require_scope=True`, covers valid / denies injected
3. **Student + Planner produce candidate/request** → Student recording mode both iterations (`candidates_proposed` > 0); real `Planner.decide()` selects `mvp-injected-001` (iter 0) then `mvp-valid-001` (iter 1)
4. **Broker authorizes valid action** → iter 1 broker allow (all five authorization dimensions)
5. **Broker denies injected out-of-scope action** → iter 0 broker deny (`Scope v0: target outside declared scope: prod.db.internal`); step terminates at broker; PEP never runs; capability invocation count stays 0
6. **PEP runs safe capability** → iter 1 PEP success, `fixture.inspect` on `system_info.name`, outcome `ok`, invocation count exactly 1
7. **receipt + artifact + provenance** → `event.decision_id == receipt.action_id == decision.decision_id`; `event.action_id == request.action_id`; `EvidenceReceipt` links event to decision
8. **WorldModel accepts evidence-backed state** → `worldmodel_integrate.integrated=True` with receipt id; exactly one `receipt:{id}` evidence in the evidence graph; `worldmodel_read.available=True`
9. **contradiction/failure triggers replan** → `contradiction.triggered=True` (`denial_failures=1`, rule `p3.11.deterministic.broker_denial_failure`); `replan.replanned=True`
10. **Student outcome recorded** → recording mode + candidate counts both iterations
11. **DecisionTrace emitted** → `p311_decision_trace.json` (19 links: mission, scope, plans, broker outcomes, PEP event, receipt ids, integration, contradiction, replan, changed decision, student outcomes)

Raw transcript: `p311_targeted_transcript.txt` (16 passed).

## 4. §14.11 failure criteria mapping

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | Every Runtime execution event has a Broker decision id | `test_adv_full_episode_every_event_has_broker_id` + demo linkage assertions | PROVEN |
| 2 | Direct execution cannot bypass Broker | `test_adv_no_primitive_imports_in_runtime`, `test_p2_guardrail_no_production_bypass` (30 green), F1 battery (12 green) | PROVEN |
| 3 | WorldModel accepts no execution-derived claim without evidence linkage | `test_adv_relationship_without_evidence_rejected` + receipt-evidence assertion in demo | PROVEN |
| 4 | Replan changes the next decision | demo: denied triple `(safe_proving_capability, prod.db.internal, fixture.inspect)` → allowed triple `(safe_proving_capability, system_info.name, fixture.inspect)`; `replan.replanned=True` with both triples | PROVEN |
| 5 | Demonstration reproduces from a clean checkout | pristine `git worktree` at `fc83a617`: 16/16 targeted green, 385 floor green, closure 34/0 + 53/0 — identical to working repo | PROVEN |
| 6 | No second canonical loop reachable | `test_adv_single_runtime_pdp_pep_ten_stages` + single-runtime guardrail | PROVEN |
| 7 | No migration seam ungates the canonical Runtime | `test_adv_no_seam_module_or_import` + `test_p2_guardrail_runtime_no_seam` | PROVEN |
| 8 | Safe capability produces evidence through PEP | demo PEP→receipt→evidence linkage + `test_execution_action_linkage_live_sandbox` | PROVEN |

## 5. §14.12 adversarial categories

| Category | Probe | Status |
|----------|-------|--------|
| Planner self-auth path | `test_adv_planner_decision_confirms_nothing_by_itself` | PROVEN (denied by design) |
| direct capability construction | `test_adv_broker_bound_capability_requires_recorded_authorization` | PROVEN (denied) |
| direct process execution | `test_adv_no_primitive_imports_in_runtime` | PROVEN (absent) |
| direct probe path | `test_adv_discriminator_proposals_do_not_execute` | PROVEN (no execution) |
| mode-local execution | `test_adv_legacy_modes_unreachable_from_canonical_closure` | PROVEN (out-of-perimeter) |
| migration seam abuse | `test_adv_no_seam_module_or_import` | PROVEN (absent) |
| test-policy abuse | `test_adv_narrow_policy_denies_outside_grant` | PROVEN (denied) |
| missing decision linkage | `test_adv_event_without_decision_id_is_detectable` | PROVEN (detectable) |
| fake receipt creation | `test_adv_fake_receipt_unknown_action_id_denied` | PROVEN (denied) |
| WorldModel claim forgery | `test_adv_relationship_without_evidence_rejected` | PROVEN (rejected) |
| F1 copied-ID / forged-object | `test_adv_copied_id_wrong_method_denied` (+ F1 battery 12/12) | PROVEN (denied) |
| canonical bypass paths | `test_adv_full_episode_every_event_has_broker_id` | PROVEN (linked) |
| architecture invariants | `test_adv_single_runtime_pdp_pep_ten_stages` | PROVEN (1/1/1/10) |

Raw transcript: `p311_targeted_transcript.txt` (13/13 probes green).

## 6. Verification

- targeted (demo + probes): 16 passed — `p311_targeted_transcript.txt`
- guardrails: 30 passed — `p311_guardrails_transcript.txt`
- scope: 19 passed — `p311_scope_transcript.txt`
- full floor: **385 passed / 0 failed / 0 skipped / 0 xfail / 33 warnings** — `p311_floor_transcript.txt` (369 baseline + 16 new; +1 warning is the same pre-existing `SyntaxWarning: "\-"` class from `src/orchestrator/capabilities/interactive_shell/capability.py:141, compiled by the new AST-scanning probe — pre-existing repo content, confirmed in clean worktree)
- static closure: 34 orchestrator / 0 arena — `p311_closure_transcript.txt`
- loaded closure: 53 / 0 arena — same file
- clean-checkout reproduction: 16/16 targeted + 385 floor + 34/0 + 53/0 in pristine worktree — `p311_clean_checkout_floor.txt`, `p311_clean_checkout_closure.txt`

## 7. Status language

- §14.10: PROVEN (demonstration machine-executed; NOT ACCEPTED — acceptance is a GLM ruling)
- §14.11: 8/8 PROVEN (criterion 5 via clean worktree; NOT ACCEPTED pending GLM)
- §14.12: 13/13 PROVEN (NOT ACCEPTED pending GLM)
- G3: NOT ACCEPTED (no GLM acceptance ruling has occurred)
- PROVEN ≠ ACCEPTED throughout.
