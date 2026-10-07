# DEFECT REGISTER — raphael-2 (branch offensive-restore)

Living register for confirmed defects formally deferred out of hardening
milestones. Entries are numbered `DR-NNN`, state the cause, the impact, the
deferral decision, and the owning milestone/ticket.

---

## DR-001 — `sword.phase_2_exploit` validator interface drift

- **Discovered**: 2026-10-04 import sweep (M0 reassessment §3; class "code drift").
- **Cause**: `src/sword/phase_2_exploit.py:4` imports
  `validate_exploit_results` from `orchestrator.validation.exploit_validator`
  and calls it (line ~55) as `await validate_exploit_results(raw, self.target)` —
  i.e. an **async validator of raw scan results**. The validator module exposes
  only `validate_exploit(exploit_config: dict, target: str) -> dict` — a **sync
  validator of an exploit config** whose payload expects a `safe_checks` key.
  Signatures, sync/async shape, and input semantics all differ; there is no
  evidence the results-validator ever existed under this name.
- **Impact**: `sword.phase_2_exploit` fails to import
  (`ImportError: cannot import name 'validate_exploit_results'`). No canonical
  Runtime path imports it (Runtime import closure is Arena-free and does not
  include sword); it counts as 1 of the 19 remaining fresh-process import
  failures. It does not affect M0–M3 acceptance paths.
- **Why not fixed in M2.1**: aliasing `validate_exploit = validate_exploit_results`
  would not be behavior-preserving (wrong input semantics; sync/async mismatch;
  the sword call site awaits a coroutine). Repairing it properly means designing
  the missing results-validation semantics for an offensive module — squarely
  out of the hardening milestone's boundary ("M2.1 should not expand into a
  general repair of the offensive codebase").
- **Disposition**: **formally deferred.** Fix belongs with the sword service
  bring-up work (gap-plan M4/M6 scope) alongside the other sword wiring.
- **Owner**: implementation engineer, sword workstream ticket.

---

### Related, already-classified (not separate tickets here)

The 18 structural import failures (arena `d6c_holdout_runner` cwd-based runners
×10, `mcp-hub.*` internal naming ×3, `config` vs `configs/` ×2,
`case_store` recon-pipeline ×3) are classified in
`evidence/M0_REVIEW_REASSESSMENT_20261004.md` §3 with per-module cause and
milestone assignment (service bring-up, M4/M6). They are unchanged by M2.1.
