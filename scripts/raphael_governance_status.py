#!/usr/bin/env python3
"""raphael_governance_status.py — read-only governance status surface (G1).

Purpose
-------
Makes the governance ledger observable: how many decisions exist, what state
each is in, what is actually in force, and what could not be authorised. This
exists because the independent audit classified the registry as ``DORMANT`` — no
production consumer, so nothing could see what the ledger says.

It is **observational only**. Running it authorises nothing, enforces nothing,
and changes nothing. All parsing and authority checking is delegated to
:func:`orchestrator.rsi.governance_registry_io.load_ledger` and the canonical
registry; this script contains no ledger logic of its own.

Usage
-----
    PYTHONPATH=src .venv/bin/python scripts/raphael_governance_status.py
    PYTHONPATH=src .venv/bin/python scripts/raphael_governance_status.py --repo-root .
    PYTHONPATH=src .venv/bin/python scripts/raphael_governance_status.py --json

Exit codes
----------
    0  governance state was observed successfully
    1  a required artifact was missing, unreadable, or invalid  (fail-closed)
    2  usage error

``0`` means "read successfully" — it does **not** mean "authority granted".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from orchestrator.rsi.governance_registry_io import (  # noqa: E402
    AUTHENTICATION_LIMITATION,
    OBSERVATION_DISCLAIMER,
    GovernanceLoadError,
    GovernanceSnapshot,
    load_ledger,
)

#: The decision whose legacy weld-perimeter component requires an independent
#: GLM architecture ruling that does not exist in this repository.
GD_03 = "GD-2026-10-11-03"

EXIT_OK = 0
EXIT_ARTIFACT_FAILURE = 1
EXIT_USAGE = 2


def _build_report(snapshot: GovernanceSnapshot) -> dict:
    counts = snapshot.status_counts()
    return {
        "loaded": True,
        "repo_root": str(snapshot.repo_root),
        "sources": {
            "ledger": str(snapshot.ledger_path),
            "delegation_record": (
                str(snapshot.delegation_path)
                if snapshot.delegation_path else None),
            "trusted_issuer_store": (
                str(snapshot.trust_store_path)
                if snapshot.trust_store_path else None),
        },
        "record_count": snapshot.record_count,
        "current_status_counts": counts,
        "historical_adoption_events": len(snapshot.historical_adoption_events),
        "historical_adoption_event_ids": sorted(
            r.decision_id for r in snapshot.historical_adoption_events),
        "effective_authority_count": snapshot.effective_authority_count,
        "effective_authority_ids": sorted(
            r.decision_id for r in snapshot.effective_authoritative),
        "unverified_authority_count": len(snapshot.unverified_authority),
        "unverified_authority": [
            {"decision_id": d, "status": s, "reason": r}
            for d, s, r in snapshot.unverified_authority],
        "authority_problem_count": len(snapshot.authority_problems),
        "authority_problems": dict(sorted(snapshot.authority_problems.items())),
        "trusted_issuer_count": len(snapshot.trusted_issuers),
        "trusted_issuer_store_empty": snapshot.trust_store_is_empty,
        "gd_03_status": snapshot.status_of(GD_03),
        "notes": list(snapshot.notes),
        "authentication_limitation": AUTHENTICATION_LIMITATION,
        "disclaimer": OBSERVATION_DISCLAIMER,
    }


def _print_text(report: dict) -> None:
    counts = report["current_status_counts"]
    print("RAPHAEL GOVERNANCE STATUS (read-only, observational)")
    print("=" * 62)
    print(f"  repo root                 : {report['repo_root']}")
    print(f"  ledger                    : {report['sources']['ledger']}")
    print(f"  delegation record         : "
          f"{report['sources']['delegation_record'] or '(absent)'}")
    print(f"  trusted-issuer store      : "
          f"{report['sources']['trusted_issuer_store'] or '(absent)'}")
    print()
    print("  DECISION LEDGER")
    print(f"    total records           : {report['record_count']}")
    for status in sorted(counts):
        print(f"    current {status:<14}: {counts[status]}")
    print(f"    historical adoptions    : "
          f"{report['historical_adoption_events']} "
          f"(preserved events, not current authority)")
    if report["historical_adoption_event_ids"]:
        print(f"      ids                   : "
              f"{', '.join(report['historical_adoption_event_ids'])}")
    print()
    print("  AUTHORITY (contextual, not structural)")
    print(f"    effective authority     : {report['effective_authority_count']}")
    if report["effective_authority_ids"]:
        print(f"      ids                   : "
              f"{', '.join(report['effective_authority_ids'])}")
    print(f"    unverified records     : {report['unverified_authority_count']}")
    for item in report["unverified_authority"]:
        print(f"      {item['decision_id']} [{item['status']}]: "
              f"{_shorten(item['reason'])}")
    print(f"    authority problems      : {report['authority_problem_count']}")
    for decision_id, reason in report["authority_problems"].items():
        print(f"      {decision_id}: {_shorten(reason)}")
    print()
    print("  TRUST / AUTHENTICATION")
    print(f"    trusted issuers         : {report['trusted_issuer_count']}")
    print(f"    store empty             : {report['trusted_issuer_store_empty']}")
    print()
    print("  GATED DECISION")
    print(f"    {GD_03}            : {report['gd_03_status'] or '(absent)'}")
    print()
    print("  LIMITATIONS")
    for line in _wrap(report["authentication_limitation"], 60):
        print(f"    {line}")
    print()
    print("  NOTES")
    for note in report["notes"] or ["    (none)"]:
        for i, line in enumerate(_wrap(note, 60)):
            print(f"    {line}" if i == 0 else f"    {line}")
    print()
    for line in _wrap(report["disclaimer"], 60):
        print(f"  {line}")


def _wrap(text: str, width: int) -> list:
    import textwrap
    return textwrap.wrap(text, width=width) or [""]


def _shorten(text: str, limit: int = 88) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Raphael governance status (G1). Observational "
                    "only: this authorises nothing and changes nothing.")
    parser.add_argument(
        "--repo-root", default=str(REPO_ROOT),
        help="repository root to read governance state from "
             "(default: this script's repository)")
    parser.add_argument(
        "--json", action="store_true",
        help="emit the report as JSON instead of text")
    args = parser.parse_args(argv)

    try:
        snapshot = load_ledger(args.repo_root)
    except GovernanceLoadError as exc:
        # Fail closed and say so. Never substitute an empty registry, and never
        # report zero authority when the truth is "could not be read".
        target = f" [{exc.path}]" if exc.path else ""
        message = f"GOVERNANCE LOAD FAILED{target}: {exc}"
        if args.json:
            json.dump(
                {"loaded": False, "error": str(exc),
                 "path": str(exc.path) if exc.path else None,
                 "note": "fail-closed: governance state could not be read. "
                         "This is NOT the same as 'no authority'; do not "
                         "treat it as such.",
                 "disclaimer": OBSERVATION_DISCLAIMER},
                sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        else:
            print(message, file=sys.stderr)
            print("  fail-closed: governance state could not be read.", file=sys.stderr)
            print("  This is NOT the same as 'no authority'. Do not treat it "
                  "as such.", file=sys.stderr)
        return EXIT_ARTIFACT_FAILURE

    report = _build_report(snapshot)
    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_text(report)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())