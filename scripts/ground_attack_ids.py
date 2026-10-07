#!/usr/bin/env python3
"""Re-ground ATT&CK IDs cited in repo markdown against MITRE ATT&CK matrix indexes.

Usage:
  python3 scripts/ground_attack_ids.py BLACK_HAT_OPERATOR_BLUEPRINT.md
  python3 scripts/ground_attack_ids.py --cache enterprise=INDEX.txt target.md

Default mode fetches the live enterprise, mobile, and ICS technique index pages
(https://attack.mitre.org/techniques/{enterprise,mobile,ics}/) via urllib.
With --cache NAME=FILE, the FILE (converted text of that index) is parsed
line-anchored instead: a line containing only ``T1485`` starts a technique, a
line containing only ``.001`` starts a sub-technique of the current one.
Uncached sources are still fetched live; if any required source is
unreachable and uncached, exit code 2 (source error) - results would be
incomplete and are NOT reported as ID failures.

Exit codes:
  0  every ID extracted from the target exists in some matrix
  1  at least one ID not found (grounding failure)
  2  usage or source error (matrix data incomplete)

ID extraction uses \\bT\\d{4}(\\.\\d{3})?\\b over the whole target file, so
dashed placeholders like "T08xx" are never matched (xx are not digits).
"""
import argparse
import re
import sys
import urllib.request

SOURCES = {
    "enterprise": "https://attack.mitre.org/techniques/enterprise/",
    "mobile": "https://attack.mitre.org/techniques/mobile/",
    "ics": "https://attack.mitre.org/techniques/ics/",
}

ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
HTML_TECH_RE = re.compile(r'href="[^"]*techniques/(?:[a-z]+/)?(T\d{4})(?:/(\d{3}))?/?"')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "raphael-grounding/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_html(html: str):
    parents, subs = set(), set()
    for parent, sub in HTML_TECH_RE.findall(html):
        parents.add(parent)
        if sub:
            subs.add(f"{parent}.{sub}")
    return parents, subs


def parse_text(text: str):
    parents, subs, cur = set(), set(), None
    for line in text.splitlines():
        m = re.match(r"^\s*(T\d{4})\s*$", line)
        if m:
            cur = m.group(1)
            parents.add(cur)
            continue
        m = re.match(r"^\s*(\.\d{3})\s*$", line)
        if m and cur:
            subs.add(f"{cur}{m.group(1)}")
    return parents, subs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", help="markdown file citing ATT&CK IDs")
    ap.add_argument(
        "--cache",
        action="append",
        default=[],
        metavar="NAME=FILE",
        help="use saved converted text for source NAME (enterprise/mobile/ics)",
    )
    args = ap.parse_args()

    caches = {}
    for item in args.cache:
        if "=" not in item:
            print(f"bad --cache {item!r}: expected NAME=FILE", file=sys.stderr)
            return 2
        name, path = item.split("=", 1)
        if name not in SOURCES:
            print(f"unknown cache source {name!r}; valid: {sorted(SOURCES)}", file=sys.stderr)
            return 2
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                caches[name] = fh.read()
        except OSError as exc:
            print(f"cannot read cache {path}: {exc}", file=sys.stderr)
            return 2

    try:
        with open(args.target, encoding="utf-8", errors="replace") as fh:
            corpus = set(ID_RE.findall(fh.read()))
    except OSError as exc:
        print(f"cannot read target {args.target}: {exc}", file=sys.stderr)
        return 2

    known, notes, source_error = set(), [], False
    for name, url in SOURCES.items():
        if name in caches:
            parents, subs = parse_text(caches[name])
            known |= parents | subs
            notes.append(f"{name}(cache): {len(parents)} techniques")
            continue
        try:
            parents, subs = parse_html(fetch(url))
            known |= parents | subs
            notes.append(f"{name}(live): {len(parents)} techniques, {len(subs)} subs")
        except Exception as exc:  # noqa: BLE001 - report any fetch failure as source error
            source_error = True
            notes.append(f"{name}: FETCH FAILED ({exc})")

    print(f"target: {args.target}")
    print(f"extracted IDs: {len(corpus)}")
    for note in notes:
        print(f"  source {note}")

    failures = sorted(cid for cid in corpus if cid not in known)
    if source_error:
        print("RESULT: SOURCE_ERROR (matrix data incomplete; not judging IDs)")
        return 2
    if failures:
        print(f"RESULT: {len(failures)} ID(S) NOT IN ANY MATRIX:")
        for cid in failures:
            print(f"  {cid}")
        return 1
    print("RESULT: OK - every cited ID exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
