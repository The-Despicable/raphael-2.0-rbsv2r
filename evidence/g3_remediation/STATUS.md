# G3 Remediation — Final Status Classification

**Final HEAD:** `07fad8c1dd23be3eec6ac785b6f391abb48a17f4`
**Branch:** `weld-sub10-evidence`
**Working tree:** clean

---

## Concise blocker status

| Blocker | Status | Evidence file |
|---------|--------|---------------|
| **F1** | **IMPLEMENTED + PROVEN** (six-dimension binding; 12 adversarial tests pass; full floor green) | `f1_diff.txt`, `tests/test_exec_sandbox.py` (F1 battery), `floor_transcript_final.txt` |
| **F2** | **IMPLEMENTED as perimeter record** (records-only; legacy plane NOT deleted, NOT refactored; P9 prerequisites recorded) | `F2_PERIMETER_RECORD.md`, `import_graph_legacy.txt` |
| **C-1** | **PROVEN** (19/19 Scope transcript, machine-generated, internally consistent; 81% anomaly explained as a transcription slip) | `scope_v0_transcript_final.txt`, `K0_PROVENANCE_BLOCK.md` §5 |
| **K.0** | **PROVEN** (predecessor `7272880f7` resolves; accepted gate anchors resolve; no discrepancies vs handoff) | `K0_PROVENANCE_BLOCK.md` |
| **G3** | **NOT ACCEPTED** (no GLM ruling yet; this evidence package is the submission for re-adjudication) | n/a |

---

## Floor

* **369 passed / 0 failed / 0 skipped / 0 xfail / 32 warnings**
* Baseline 357 (pre-remediation) + 12 new F1 adversarial tests = 369
* 316/32 footer line preserved (the historical `316` is the pre-§14.4
  floor count; current count is 369; both numbers appear in the
  evidence package, with 316 explained as the pre-§14.4 baseline)

## Guardrails

* **30/30 green** — no new guardrail files, no existing guardrail
  weakened

## Closure

* **Static:** 34 orchestrator modules / 0 arena
* **Loaded:** 53 modules / 0 arena
* Both Arena-free; both equal the §14.5 baseline

## Environment

* Python `3.14.4`
* pytest `9.1.1`
* `pyproject.toml` declares `requires-python = ">=3.11,<3.13"` —
  the agent runs Python 3.14.4, which is OUTSIDE the declared range.
  This is the same environment mismatch the previous gate submissions
  flagged. NOT concealed.

## Governance

* G0 PASS (historical)
* G1 PASS (historical)
* G2 PASS (historical)
* G3 NOT PASSED (no GLM ruling yet)
* Verdict ORANGE

---

No roadmap advancement performed. Awaiting GLM re-adjudication.