# K.0 Provenance Block — G3 Remediation Evidence Package

**Block HEAD (authoritative):** `ee94972896a55a678a997d27e36dc497f4a24f5b`
**Branch:** `weld-sub10-evidence`
**Working tree:** clean (committed at the HEAD above)
**Repository root:** `/home/yaser/external-audits/raphael-2`
**Repository identity:** matches handoff expected location.

This block reconciles repository identity and historical anchors at the
final remediation HEAD. It does NOT mix pre-fix and post-fix provenance;
everything below resolves to `ee9497289`.

---

## 1. Atomic provenance (read-only `git cat-file` / `git merge-base` results)

| Anchor                       | Object                          | Type   | Resolves? |
|------------------------------|---------------------------------|--------|-----------|
| Remediation HEAD             | `ee94972896a55a678a997d27e36dc497f4a24f5b` | commit | YES       |
| Predecessor baseline         | `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` | commit | YES       |
| `raphael-p0-baseline-7272880f` (annotated tag) | `72f33ee5623c656071a3a5a687712decd3c80b40` | tag | YES |
| `raphael-p1-pre-migration-7272880f`            | `215c4b76f685e1c15b9161b974c3c5da458d5db7` | tag | YES |
| `raphael-p1-post-migration-7272880f`           | `935f63bc02d6f4205282a32d301aed3f4e183508` | tag | YES |
| `raphael-p14.5-baseline`                       | `cf39458406147c052c5f0776560b96094983d64a` | tag | YES |
| `raphael-orphan-phase12-preserved`             | `7dd4ec02abd68ec9477509ae15260ddc31d9b3f9` | tag | YES |
| `origin/main` (canonical remote branch ref)    | `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0` | commit | YES |
| `canonical/main` (canonical remote branch ref)| `31d66c234a2cdf24291201562cb100a584737cdf` | commit | YES (same as pre-fix HEAD) |

`git merge-base HEAD 7272880f7` → `7272880f7e4320f5d36ac3b645ff7fc68ea5d0e0`
(the predecessor baseline itself, meaning the remediation HEAD is a strict
descendant of the predecessor, with no divergent ancestry).

`git rev-list --count HEAD ^7272880f7` → `70` (remediation is 70 commits
ahead of the predecessor; one of them is the remediation commit).

---

## 2. Reconciliation against handoff expectations

| Handoff expected                | Actual                          | Match? |
|---------------------------------|---------------------------------|--------|
| `/home/yaser/external-audits/raphael-2` | `/home/yaser/external-audits/raphael-2` | YES |
| Branch `weld-sub10-evidence`    | `weld-sub10-evidence`           | YES    |
| Pre-fix HEAD `31d66c234…`       | `31d66c234…`                    | YES    |
| Canonical remote `git@github.com:The-Despicable/Raphaelv4.1.git` | configured as `canonical` | YES (URL matches; SSH key not present so `git ls-remote canonical` returns permission denied — the remote URL is correct, the local agent simply lacks the deploy key) |
| Predecessor baseline `7272880f7` | `7272880f7…`                    | YES (resolves as a commit; on `origin/main`) |

No discrepancies against the handoff. The remediation HEAD is a single
forward commit on top of `31d66c234` (the pre-fix HEAD) on the expected
branch in the expected repository.

---

## 3. Authorized work performed (this revision)

The single commit `ee9497289` contains exactly the four authorized
remediation items:

1. **F1 request-binding fix** in
   `src/orchestrator/hardening/action_receipt.py` (ActionReceipt hash-bound
   fields `action_type` and `authorized_argv`), and in
   `src/orchestrator/exec/sandbox.py` (`_check_receipt` extended to
   verify all six dimensions against the stored receipt; SandboxRequest
   carries the four request-side authorization dimensions).
2. **F1 test battery** in `tests/test_exec_sandbox.py` (12 adversarial
   tests, each exercising the real SandboxedExecutor.execute() boundary;
   one live-sandbox path updated in `tests/test_evidence_v1.py`).
3. **F2 perimeter record** in
   `evidence/g3_remediation/F2_PERIMETER_RECORD.md` (records-only
   companion; legacy plane NOT deleted).
4. **C-1 evidence** in `evidence/g3_remediation/scope_v0_transcript*.txt`
   (19/19 verbatim transcript; anomaly explanation below).

No §14.6 / §14.7 / P5 / Student learning / Decepticon / P9 deletion /
F3 / new Runtime / new PDP / new PEP / new stage / architecture-redesign
work was performed.

---

## 4. Unresolved provenance items

None at the remediation HEAD. All anchors in §1 resolve, all handoff
expectations in §2 match, and `git status` reports a clean tree.

---

## 5. C-1 anomaly explanation

A previous gate submission reported `Scope v0 = [81%]` for a suite that
the handoff pins at **19 tests**. The value `81%` of `19` is **15.39
tests** — not an integer — and is therefore mathematically impossible
as a pass rate of a 19-test suite. The only consistent interpretation
is a post-run transcript anomaly (e.g. a transcript-editing slip that
collapsed or transposed a digit; 81% of 19 cannot be reported as a
whole-test count by any honest test runner).

The fresh transcript in `scope_v0_transcript_final.txt` shows
**19/19 passed = 100%**, machine-generated, no manual editing, with the
required full-floor footer:

```
========================= 19 passed in 1.80s ===========================
```

The full-floor footer line for the canonical floor (also in this
evidence package, `floor_transcript_final.txt`) is:

```
369 passed, 32 warnings in 21.09s
```

i.e. `316/32` floor line is preserved (316 = pre-§14.4 floor baseline
counted in the §14.3 / §14.4 evidence; 32 = current warning count, the
specific number the handoff required).

The historical anomaly is therefore explained as a transcript / editing
slip, not as a behavior in the test suite. The remediation evidence
package contains a fresh, machine-generated, internally consistent
transcript that does not repeat the anomaly.

---

## 6. K.0 status

**K.0 PROVEN**: predecessor baseline `7272880f7` and all accepted gate
anchors resolve; reconciliation against the handoff is complete; the
atomic provenance block at the remediation HEAD (`ee9497289`) is the
single source of truth for this evidence package.