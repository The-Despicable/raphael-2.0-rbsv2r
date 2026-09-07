# RAPHAEL_STATE.md — Canonical State (§14.5)

Canonical HEAD: `b676d8198df003873f52b96c83896d65593a77a2`
Current Phase: §14.5 Evidence v1 IMPLEMENTED / EVIDENCE READY (NOT accepted)

§14.3: Scope v0 — CLOSED / FROZEN (impl `85c3bc90`, Option-B `c4ff633`, records `bec5c65e`)
§14.4: Native Minimal Sandbox — IMPLEMENTED (impl `7e68b24`, records `18a7acd`)
§14.5: Evidence v1 — IMPLEMENTED / EVIDENCE READY (impl `8cd3a95`, records `b676d81`)

Full Test Floor: 357 passed / 0 failed / 0 skipped / 0 xfail
Guardrails: 30 green
Static Closure: 34 orchestrator modules / 0 Arena (B-1a instrument 1)
Loaded Closure: 53 modules / 0 Arena (B-1a instrument 2, post-episode walk)

Accepted/frozen: SHELL, SUB-10, SUB-13, SUB-14, Scope v0.

Open Riders:
- C-1: gate submissions must include the verbatim Scope 19-test transcript +
  the one-line transcription-error explanation + the 316/32 §14.3 floor line.
- §14.10 ruling: over-cap demo must use a Broker-recorded estimate; no
  Scope-side manufactured impact values.

Non-Blocking Limitations:
- RLIMIT_AS/memory caps unclaimed; no kernel network isolation (fail-closed
  UNSUPPORTED); `sandboxed_exec` planner-unreachable until MVP assembly;
  static coreutils executable allowlist; single-thread preexec assumption;
  evidence store cap 10000 (fail-closed, no rotation); artifact bytes
  referenced, never embedded.

Next Gate: §14.5 acceptance (GLM authority). Do NOT start §14.6 (§14.6 =
WorldModel minimum enforcement per canonical numbering) or later work.
