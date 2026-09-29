# EFFECT_SCOPE_RULING_REQUEST.md — 001R5 bounded ruling request (no scope invented)

**To:** GLM / Lead. **From:** Muse Spark 1.3 (executor, Task 001R5).
**Status (original, 001R5):** REQUEST ONLY. No classification below is asserted; the census is unchanged
(150 files after 001R6) pending rulings. Residual families remain evidence-only in CENSUS §G.

**Status (AM-4 update): ALL THREE QUESTIONS CLOSED by GLM governance verdict
(`/home/yaser/tmp/raphael-overnight/GLM_GOVERNANCE_VERDICT.md`, 2026-09-17).
Census delta 0, WELD_SET delta 0, scanner change 0. See §4 below. No new policy
invented here; this file only records the ruling outcomes against the request.

## 1. Exact governing text on record

- INV-1 (§24): "process/network/file primitives confined to `exec/`".
- AM-7: "process/network/file primitives only importable from exec/".
- AM-13.1: "Execution primitives (process, network, file) are licensed exclusively to
  `exec/`... All other file access, by any other package, is Broker-mediated exactly
  like process or network access." Exception ONLY for exec/'s receipt/artifact/ledger writes.
- Scanner doctrine (`inv1_guard.py:36`): "file-mutation primitives".
- P3.0 gate criterion names socket/urllib as non-exhaustive examples ("such as").

## 2. Questions

**Q1 — reads.** `open()`-read / `Path.read_text` / `json.load` / `sqlite3` reads /
`shutil.which` / `tempfile`: the doctrine says *mutation*; the AM-13.1 text says "all
other file access". Does "file access" include read-only access (which would pull a
large read plane into the census), or does the mutation doctrine stand (reads stay out)?

**Q2 — `mkdir` / `makedirs`.** `Path.mkdir` / `os.mkdir` / `os.makedirs` create
filesystem state but have no governed equivalent in the scanner (unlike `rmdir`, which
mirrors governed `os.rmdir`). In-scope as creation effects, or out (no governed
equivalent)?

**Q3 — N-12 open vs closed lexicon.** The governed categories ("network primitives",
"file primitives") are open-ended: each audit pass surfaces another family
(write_text → shutil → smtplib → boto3 → asyncio streams). Directives requested —
either (i) ratify a CLOSED enumerated lexicon (then completeness is decidable and the
scanner is provably complete relative to it), or (ii) explicitly accept an
open-category allowlist with a documented residual (then completeness passes are
unreachable by construction and each cycle re-certifies relative to the current list).

## 3. What the executor did meanwhile

Nothing beyond documentation: residual families are listed evidence-only in CENSUS §G
with the exact reason each is excluded; the scanner enforces exactly the 001R2/001R4/001R5
named families; fixtures pin the semantics. No file was added to or removed from the
census on judgment — only on AST-verified lexicon hits (iam_pathfinder, fast_port_scan).

## 4. GLM rulings received (AM-4 integration; source: GLM_GOVERNANCE_VERDICT.md)

**Q1 — file READ effects: CLOSED → OUT of the governed P3.0 effect universe.**
Mutation-centric reading of INV-1/AM-13.1/L6/§5.3 + scanner doctrine
("file-mutation primitives"); read-inclusive reading would collapse the
perimeter (INV-1 35/0 would be false). Census/WELD_SET/scanner consequence: none
(reads already excluded by construction).

**Q2 — `mkdir`/`makedirs`: CLOSED → OUT of the governed destructive-file universe.**
Destructive (not creative) primitives only; no governed `os.mkdir` equivalent for
`Path.mkdir` to mirror; `mkdir` cannot destroy existing data. Consequence: none
(already excluded; CENSUS §G + in-tree `.mkdir()` calls correctly out).

**Q3 — lexicon boundary: CLOSED → OPTION C, dual-layer bounded model.**
Categories intentionally open-ended ("such as"); scanner enumeration within
categories closed and explicit; new families require explicit governance.
Consequence: none — 150-file census authoritative relative to current
enumeration; this file's §2-Q3 alternatives (i)/(ii) are superseded by option C.

Boundary preserved (governance ruling vs census vs scanner vs reachability kept
distinct): no census file added/removed, no scanner logic changed, no
classification changed by this integration.
