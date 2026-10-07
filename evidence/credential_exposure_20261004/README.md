# Credential exposure record & rotation checklist — 2026-10-04 (M0-C)

## Scope

Full-format NVIDIA API-key literals (`nvapi-…`) in the repository working
tree, found by the 2026-10-04 E2E audit and re-scanned fresh during M0.
Values are NOT reproduced anywhere in this record; each key is identified by
the first 8 hex chars of its SHA-256 (fingerprint) and length only.

## Inventory (working tree, BEFORE M0-C cleanup)

| Fingerprint (sha256[:8]) | Length | Sites (file:line at audit time) |
|---|---|---|
| `58356654` | 70 | `src/orchestrator/nvidia_provider.py:42` (env default), `scripts/rbs_v2r_probe_120b.py:14`, `scripts/rbs_v2r_canary_phase3_B.py:22` |
| `06323f90` | 70 | `forge/wire_llm_service.py:40`, `forge/probe_nvidia.py:16`, `forge/apply_d13_blocks.py:14,18,45`, `forge/apply_d13_fixes.py:122`, `src/arena/manifests/D6C_HOLDOUT_MANIFEST.json:171`, `evaluations/campaign/PROVIDER_GATE_report.md:119` |
| `c5fdb929` | 70 | `forge/prelaunch_verify2.py:26` |
| `94652146` | 70 | `forge/prelaunch_verify2.py:27` |
| `d98e6170` | 34 | `forge/verify_d13_patch.py:27` |

Partial key fragments (prefix + ≤7 chars, redacted as well):
`forge/prelaunch_inspect.py:69`, `evaluations/campaign/L028_OPTIONA_SENTINEL_REPORT.md:35`.
An example-config occurrence in `cli/.env.example:316` held a real key and was
replaced with the placeholder `nvapi-REPLACE_ME`.

## M0-C cleanup (working tree) — DONE 2026-10-04

- `src/orchestrator/nvidia_provider.py` — embedded default removed from
  `os.getenv("NVIDIA_API_KEY", …)`; env is now the only source.
- `scripts/rbs_v2r_probe_120b.py`, `scripts/rbs_v2r_canary_phase3_B.py`,
  `forge/wire_llm_service.py`, `forge/probe_nvidia.py` — literals replaced by
  `os.environ.get("NVIDIA_API_KEY", "")` (+ `import os` where missing).
- `forge/prelaunch_verify2.py` — `sentinel_keys` now read from the loaded
  `.env` (`NVIDIA_API_KEY_A/B`) instead of embedded literals; the checker's
  reporting behavior is preserved.
- `forge/apply_d13_blocks.py`, `forge/apply_d13_fixes.py`,
  `forge/verify_d13_patch.py`, `forge/prelaunch_inspect.py` — one-shot
  remediation-era scripts: embedded literals (and the short fragments) replaced
  by the marker `REDACTED-M0-C-20261004`. Their "was the key removed?" search
  semantics now apply to the marker, not to the original literal.
- `src/arena/manifests/D6C_HOLDOUT_MANIFEST.json` — value redacted
  (`REDACTED-M0-C-20261004`), JSON validity re-verified. NOTE: this is a
  tracked evidence artifact; its pre-M0 content (including the key) remains in
  git history.
- `evaluations/campaign/PROVIDER_GATE_report.md`,
  `evaluations/campaign/L028_OPTIONA_SENTINEL_REPORT.md` — literals/fragments
  redacted inline.
- Post-cleanup scan: zero `nvapi-` full-format literals and zero fragments in
  the working tree.

## Historical Git objects — NOT remediated (out of M0 scope)

`git grep nvapi- HEAD` confirms the same literals in committed history
(incl. `cli/.env.example`, `forge/apply_d13_*`, reports, manifests). The keys
must be considered COMPROMISED regardless of the working-tree cleanup. History
rewrite (filter-repo/BFG) requires explicit operator authorization and is not
performed in M0.

## Operator rotation checklist (external actions — REQUIRED, not yet confirmed)

1. Log in to the NVIDIA NGC / build.nvidia.com account(s) that issued the five
   keys above.
2. Revoke/roll every key matching the fingerprints (treat all five as
   compromised; `d98e6170` is a malformed/short variant — revoke its issuer
   key too if it is a truncation).
3. Issue replacement key(s) and store them ONLY in the environment
   (`.env`, which is git-ignored) — never in source, manifests, or reports.
4. Validate replacements with a minimal authenticated call from a machine that
   does not echo the key (e.g. `scripts/validate_env.py` after M1 provisioning,
   or a single models-list request) — do NOT use any repo script that embeds or
   prints keys.
5. Record the rotation date and the new fingerprints (sha256[:8]) in the
   security log; confirm in the M1 review so the M0 security gate can close.
6. Optional, on operator authorization only: purge the literals from git
   history (git filter-repo) and force-protect any shared remotes.

Rotation status as of this report: **PENDING — provider-side action required**.
Working-tree cleanup alone does NOT constitute rotation.
