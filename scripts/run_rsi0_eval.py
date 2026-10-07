#!/usr/bin/env python3
"""run_rsi0_eval.py — RSI-0 offline group-relative strategy evaluation.

Runs the three candidate ExplorationPolicies (C0 canonical, C1 reversed,
C2 single-retry) across the three controlled scenario families (S1 nominal
live lab, S2 HTTP-transport fault, S3 constrained 2/min budget), scores every
episode with the hardened objective evaluator, and writes:

  evidence/rsi0/<run_id>/manifest.json            — per-run records
  evidence/rsi0/<run_id>/evaluation_report.json   — regenerated from manifest
  evidence/rsi0/<run_id>/evaluation_report.md     — human-readable comparison

Evaluation-only: no promotion, no production-policy mutation, no provider
calls. Ranking is a declared lexicographic rule; deterministic scenarios are
reported exactly without statistical claims.
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from orchestrator.rsi.exploration_policy import ExplorationPolicy  # noqa: E402
from orchestrator.rsi import strategy_eval as SE  # noqa: E402


def candidate_policies() -> list:
    common = dict(version=1, status="experimental", created_by="rsi0-eval",
                  parent_version=0)
    c0 = ExplorationPolicy(
        policy_id="rsi0-c0-canonical", motivation="incumbent deterministic order",
        parameters={"order": ["A", "B"], "retry": {"action": "A", "at_most": 0}},
        **common)
    c1 = ExplorationPolicy(
        policy_id="rsi0-c1-reverse", motivation="reversed ordering variant",
        parameters={"order": ["B", "A"], "retry": {"action": "A", "at_most": 0}},
        **common)
    c2 = ExplorationPolicy(
        policy_id="rsi0-c2-retry-a", motivation="canonical order + one bounded A retry",
        parameters={"order": ["A", "B"], "retry": {"action": "A", "at_most": 1}},
        **common)
    for p in (c0, c1, c2):
        p.validate()
    return [c0, c1, c2]


def main() -> int:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = REPO / "evidence" / "rsi0"
    run_dir = base / stamp
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = base / f"{stamp}_{suffix}"
    run_dir.mkdir(parents=True)
    print(f"[rsi0] run directory: {run_dir}")

    policies = candidate_policies()
    manifest = {
        "experiment": "RSI-0 offline group-relative strategy evaluation",
        "run_id": run_dir.name,
        "generated_at": time.time(),
        "policy_cap": 5,
        "candidates": {p.policy_id: p.to_dict() for p in policies},
        "scenarios": {k: v["description"] for k, v in SE.SCENARIOS.items()},
        "runs": [],
    }

    for scenario in ("S1_nominal", "S2_http_fault", "S3_budget"):
        for policy in policies:
            try:
                record = SE.run_candidate(policy, scenario, run_dir)
            except Exception as exc:  # noqa: BLE001 — record and continue
                record = {"candidate": policy.policy_id, "scenario": scenario,
                          "content_hash": policy.content_hash(),
                          "verified_completion": False, "evidence_complete": False,
                          "hard_violations": [], "denials": 0, "steps_executed": 0,
                          "unscorable": f"runner error: {type(exc).__name__}: {exc}"[:200],
                          "termination": "", "wall_seconds": 0.0,
                          "objective_verdicts": {}, "run_dir": ""}
            manifest["runs"].append(record)
            print(f"[rsi0] {policy.policy_id:18s} {scenario:14s} "
                  f"completion={record['verified_completion']!s:5s} "
                  f"steps={record['steps_executed']} denials={record['denials']} "
                  f"violations={len(record['hard_violations'])}")

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    report = SE.build_report(manifest)
    (run_dir / "evaluation_report.json").write_text(json.dumps(report, indent=1))

    lines = [
        "# RSI-0 EVALUATION REPORT (group-relative strategy evaluation)",
        f"run: {run_dir.name}  generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        "Ranking rule: " + report["ranking_rule"],
        "Limits: " + report["limits"],
        "",
        "| candidate | scenario | verified | steps | denials | violations | termination |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in manifest["runs"]:
        lines.append(f"| {r['candidate']} | {r['scenario']} | {r['verified_completion']} "
                     f"| {r['steps_executed']} | {r['denials']} | "
                     f"{len(r['hard_violations'])} | {r['termination'][:80]} |")
    lines += ["", "## Per-candidate aggregates", ""]
    for cid, agg in report["candidates"].items():
        lines.append(f"- **{cid}**: runs={agg['runs']} verified={agg['verified_completion']} "
                     f"evidence_complete={agg['evidence_complete']} denials={agg['denials']} "
                     f"steps_total={agg['steps_total']} violations={agg['hard_violations']}")
    lines += ["", "## Ranking (eligible runs, declared rule)", ""]
    for cid, scen in report["ranking"]:
        lines.append(f"- {cid} / {scen}")
    if report["excluded"]:
        lines += ["", "## Excluded runs", ""]
        lines += [f"- {e}" for e in report["excluded"]]
    lines += ["", "Interpretation guardrail: deterministic scenarios — these are exact "
              "observed outcomes, not statistical estimates; no promotion decision is "
              "authorized or implied (holdout absent, no lineage machinery)."]
    (run_dir / "evaluation_report.md").write_text("\n".join(lines) + "\n")
    print(f"[rsi0] manifest + report written under {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
