#!/usr/bin/env python3
# Consistency check: README.md limitations table vs docs/LIMITATIONS.md.
#
# docs/LIMITATIONS.md is the CANONICAL register. This script fails if the README
# table drifts from it: missing IDs, extra IDs, duplicate IDs, reordered rows,
# mismatched titles, or mismatched severities. It never edits either file.
#
# Exit: 0 = consistent, 1 = drift detected.
import io
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CANONICAL = REPO / "docs" / "LIMITATIONS.md"
README = REPO / "README.md"

# Trailing "(Added 2026-08-04)" / "(Added 2026-08-08, SENTINEL D1/D1-B)" notes
# are provenance markers, not part of the limitation title.
_ADDED = re.compile(r"\s*\(Added[^)]*\)\s*$")
_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    text = _ADDED.sub("", text)
    return _WS.sub(" ", text).strip().casefold()


def parse_canonical(path: Path) -> list:
    """Ordered list of (L-ID, {title, severity}) in document order.

    Severity is None when the canonical entry declares none. The order is kept
    so canonical duplicates and canonical row order can be validated.
    """
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    current = None
    for line in lines:
        heading = re.match(r"^##\s+(L-\d{3}):\s*(.+?)\s*$", line)
        if heading:
            current = heading.group(1)
            rows.append((current, {"title": heading.group(2), "severity": None}))
            continue
        if current is None:
            continue
        # Accept both "**Severity**: X" and "**Severity: X**" spellings.
        sev = re.match(r"^\*\*Severity(?:\*\*)?:?\s*([^:*]+?)\*{0,2}\s*$", line)
        if sev:
            rows[-1][1]["severity"] = sev.group(1).strip()
    return rows


def parse_readme(path: Path) -> list:
    """Ordered list of (L-ID, {title, severity}) from the README table.

    The sequence is preserved verbatim so duplicate rows and row reordering are
    detectable; duplicates are never collapsed here.
    """
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh.read().split("\n"):
            row = re.match(r"^\|\s*(L-\d{3})\s*\|([^|]*)\|([^|]*)\|", line)
            if row:
                rows.append((row.group(1),
                             {"title": row.group(2).strip(),
                              "severity": row.group(3).strip()}))
    return rows


def first_wins(rows: list) -> dict:
    """Map L-ID -> entry, keeping the FIRST occurrence.

    A later duplicate must not silently replace the entry it duplicates.
    """
    out = {}
    for lid, entry in rows:
        out.setdefault(lid, entry)
    return out


def find_duplicates(rows: list) -> list:
    """Return [(L-ID, [1-based row numbers...])] for every repeated ID."""
    positions = {}
    for idx, (lid, _) in enumerate(rows, 1):
        positions.setdefault(lid, []).append(idx)
    return [(lid, idxs) for lid, idxs in positions.items() if len(idxs) > 1]


def main() -> int:
    for path in (CANONICAL, README):
        if not path.exists():
            print(f"FAIL: missing {path}")
            return 1

    canon_rows = parse_canonical(CANONICAL)
    readme_rows = parse_readme(README)
    canon = first_wins(canon_rows)
    readme = first_wins(readme_rows)
    canon_order = [lid for lid, _ in canon_rows]
    readme_order = [lid for lid, _ in readme_rows]
    problems = []

    if not canon_rows:
        problems.append("canonical register parsed empty")
    if not readme_rows:
        problems.append("README limitations table not found or parsed empty")

    # Duplicates: reported for both sides, never silently collapsed.
    for lid, positions in find_duplicates(canon_rows):
        problems.append(
            f"docs/LIMITATIONS.md declares {lid} more than once "
            f"(headings at lines/rows {', '.join(str(p) for p in positions)})")
    for lid, positions in find_duplicates(readme_rows):
        problems.append(
            f"{lid}: duplicated in the README limitations table "
            f"(table rows {', '.join(str(p) for p in positions)})")

    for lid in sorted(set(canon) - set(readme)):
        problems.append(f"{lid}: present in docs/LIMITATIONS.md, missing from README table")
    for lid in sorted(set(readme) - set(canon)):
        problems.append(f"{lid}: present in README table, absent from docs/LIMITATIONS.md")

    # Ordering: compared only once both sides hold the same set of IDs, so a
    # missing/extra row is reported once rather than as a cascade of positions.
    if sorted(canon_order) == sorted(readme_order) and canon_order != readme_order:
        for i, (exp, obs) in enumerate(zip(canon_order, readme_order)):
            if exp != obs:
                problems.append(
                    f"row order mismatch at position {i + 1}: "
                    f"expected {exp} (canonical order), README has {obs}")
                break
        else:
            problems.append("row order mismatch: README order differs from docs/LIMITATIONS.md")

    for lid in sorted(set(canon) & set(readme)):
        c, r = canon[lid], readme[lid]
        if norm(c["title"]) != norm(r["title"]):
            problems.append(
                f"{lid}: title mismatch\n"
                f"      canonical: {c['title']!r}\n"
                f"      README    : {r['title']!r}")
        csev = norm(c["severity"]) if c["severity"] else None
        rsev = norm(r["severity"])
        if csev is None:
            if not (rsev.startswith("\u2014") or rsev.startswith("-")):
                problems.append(
                    f"{lid}: canonical declares no severity; README says {r['severity']!r}")
        elif rsev != csev:
            problems.append(
                f"{lid}: severity mismatch \u2014 canonical {c['severity']!r} vs README {r['severity']!r}")

    if problems:
        print(f"FAIL: README limitations table disagrees with docs/LIMITATIONS.md "
              f"({len(problems)} problem(s))")
        for p in problems:
            print("  -", p)
        print("\ndocs/LIMITATIONS.md is canonical. Fix the README table; "
              "do not edit the canonical register to match the README.")
        return 1

    print(f"OK: README limitations table matches docs/LIMITATIONS.md "
          f"({len(canon_rows)} entries, {canon_order[0]}..{canon_order[-1]}, order verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())