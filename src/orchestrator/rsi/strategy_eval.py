"""strategy_eval.py — RSI-0 deterministic candidate runner, scorer, reporter.

Runs bounded D2 episodes for candidate ExplorationPolicies across controlled
scenarios, scores persisted evidence with the hardened objective evaluator,
and emits a regenerable manifest + evaluation report. Evaluation-only: no
promotion, no policy mutation, no provider calls.

Scenarios:
  S1 nominal      — live lab, real governed probes (docker required).
  S2 http_fault   — hermetic; the HTTP capability's runner deterministically
                    fails with connection-refused (rc 7).
  S3 budget       — hermetic; a scenario-local policy artifact caps the rate
                    at 2/min so the third authorized-shape attempt (C2's
                    retry) is rate-denied. The production policy file is
                    never modified; the scenario writes its own copy into the
                    run's temporary directory.

Ranking rule (declared, lexicographic, no invented weights):
  1. hard-violation count ascending (0 required for a score)
  2. verified objective completion descending
  3. evidence-complete descending
  4. steps used ascending
  5. policy_id ascending (deterministic tie-break)
Unscorable episodes (ambiguous verification) are excluded from ranking and
reported with reasons.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D1Policy, D2_POLICY_PATH, make_broker_from_bootstrap, make_broker_from_policy)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext
from orchestrator.rsi.exploration_policy import (
    ACTIONS,
    CONSTRAINT_ECHO,
    ExplorationPolicy,
)

MISSION_ID = "rsi0-strategy-eval"


# ── scenario fixtures ────────────────────────────────────────────────────

def _live_runner(argv, timeout):
    return subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout)


def _http_refused_runner(argv, timeout):
    """S2 fixture: deterministic connection-refused at the HTTP boundary."""
    class P:
        returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect to dvwa port 80"
    return P()


def _hermetic_nmap_runner(argv, timeout):
    class P:
        returncode = 0
        stdout = ("Starting Nmap 7.99\nNmap scan report for dvwa (172.19.0.4)\n"
                  "PORT   STATE SERVICE\n80/tcp open  http\n")
        stderr = ""
    return P()


def _hermetic_http_runner(argv, timeout):
    class P:
        returncode = 0
        stdout = ("<html>login redirect</html>\n"
                  "302|text/html|28|0.01|http://dvwa/login.php\n")
        stderr = ""
    return P()


def fake_inspector(container: str) -> dict:
    net = "raphael-m1_raphael-net"
    if container == "dvwa":
        return {"State": {"Running": True},
                "Config": {"Image": "vulnerables/web-dvwa:latest"},
                "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}
    if container == "kali-tools":
        return {"State": {"Running": True},
                "Config": {"Image": "raphael/kali-tools:latest"},
                "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.3"}}}}
    raise AssertionError(f"unexpected container {container}")


SCENARIOS: Dict[str, Dict[str, Any]] = {
    "S1_nominal": {
        "description": "Live lab; both approved probes execute for real.",
        "hermetic": False,
        "runners": {"http": _live_runner},
        "policy_path": None,          # production D2 policy (6/min)
    },
    "S2_http_fault": {
        "description": "Hermetic; HTTP capability deterministically refused (rc 7).",
        "hermetic": True,
        "runners": {D1LabProbeCapability: _hermetic_nmap_runner,
                    "http": _http_refused_runner},
        "policy_path": None,
    },
    "S3_budget": {
        "description": "Hermetic; scenario-local policy caps actions at 2/min "
                       "(C2's third authorized-shape attempt is rate-denied).",
        "hermetic": True,
        "runners": {D1LabProbeCapability: _hermetic_nmap_runner,
                    "http": _hermetic_http_runner},
        "policy_path": "scenario",    # written per-run with 2/min
    },
}


def _scenario_policy(scenario: str, workdir: Path) -> Path:
    """S3: scenario-local policy copy with a 2/min budget (isolated fixture).

    The production policy artifact is never modified; the scenario writes its
    own copy into the run directory and the loader consumes that path."""
    from orchestrator.runtime.policy import D2_POLICY_PATH
    base = json.loads(Path(D2_POLICY_PATH).read_text())
    base["rate_limits"]["max_actions_per_minute"] = 2
    path = workdir / f"engagement-d2-{scenario.lower()}.json"
    path.write_text(json.dumps(base, indent=1))
    return path


# ── candidate runner ─────────────────────────────────────────────────────

def build_mission(policy: ExplorationPolicy, max_iterations: int = 5) -> MissionContext:
    """Mission built FROM the candidate policy: step order, retry, and the
    objective contract come from the policy + constraint echo. Scope, halt
    semantics, and the objective ids come from the approved D2 contract."""
    steps = policy.ordered_action_keys()
    candidates = {}
    for i, key in enumerate(steps):
        act = ACTIONS[key]
        # A retry re-uses the same mission action_id: the objective evaluator
        # groups attempts by decision_id, so a later attempt is judged on its
        # own records (attempt isolation is already the proven contract).
        candidates[str(i)] = [{
            "action_id": act["action_id"], "action_type": act["action_type"],
            "target": CONSTRAINT_ECHO["target"], "capability": act["capability"],
            "method": act["method"], "impact_estimate": 2.0,
            "args": {"bounded": True, "candidate": policy.policy_id,
                     "step": i, "retry": i >= len(policy.parameters["order"])},
            "rationale": f"RSI-0 candidate {policy.policy_id} step {i}",
        }]
    return MissionContext(
        mission_id=MISSION_ID, name=f"RSI-0 {policy.policy_id}",
        objectives=["governed two-probe reconnaissance of the local DVWA lab"],
        constraints={
            "halt": {"max_iterations": max_iterations, "action_cap": 1,
                     "require_scope": True},
            "candidates": candidates, "default_target": CONSTRAINT_ECHO["target"],
            "objective": {"requires_evidence":
                          list(CONSTRAINT_ECHO["objective_requires"])},
        },
        scope=ScopeV0(mission_id=MISSION_ID, targets=(CONSTRAINT_ECHO["target"],),
                      allowed_action_types=tuple({a["action_type"] for a in ACTIONS.values()}),
                      allowed_capabilities=tuple({a["capability"] for a in ACTIONS.values()}),
                      max_impact=2.0))


def run_candidate(policy: ExplorationPolicy, scenario: str,
                  out_dir: Path, broker: Optional[Any] = None) -> Dict[str, Any]:
    """Run one candidate under one scenario through the canonical path."""
    sc = SCENARIOS[scenario]
    run_dir = out_dir / f"{policy.policy_id}_{scenario}"
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    store = EvidenceStore(run_dir / "evidence_store.jsonl")

    # The broker is EXPLICITLY bound to the operator-approved D2 artifact;
    # the scenario may override with its own isolated policy copy (S3).
    policy_path = D2_POLICY_PATH
    if sc["policy_path"] == "scenario":
        policy_path = _scenario_policy(scenario, run_dir)
    broker = make_broker_from_policy(policy_path)

    runner_a = sc["runners"].get(D1LabProbeCapability) if sc["hermetic"] else _live_runner
    runner_b = sc["runners"].get("http") if sc["hermetic"] else _live_runner
    inspector = fake_inspector if sc["hermetic"] else _live_inspector
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=run_dir / "artifacts",
                                 runner=runner_a, inspector=inspector)
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=run_dir / "artifacts",
                                   runner=runner_b, inspector=inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A_KEY: cap_a, CAP_B_KEY: cap_b})
    mission = build_mission(policy, max_iterations=CONSTRAINT_ECHO["max_episode_steps"])

    t0 = time.time()
    episode_outputs: list = []
    traces, termination = runtime.run_episode(mission, episode_outputs=episode_outputs)
    wall = time.time() - t0
    return _score(policy, scenario, run_dir, store, episode_outputs, termination, wall,
                  broker_authority=broker)


CAP_A_KEY = "exec.d1_lab_probe"
CAP_B_KEY = "exec.http_probe"


def _live_inspector(container: str) -> dict:
    import subprocess as _sp
    proc = _sp.run(["docker", "inspect", container], capture_output=True,
                   text=True, timeout=20)
    if proc.returncode != 0:
        raise RuntimeError(f"docker inspect {container} failed")
    return json.loads(proc.stdout)[0]


def _score(policy, scenario, run_dir, store, episode_outputs, termination, wall,
           broker_authority=None) -> Dict[str, Any]:
    from orchestrator.runtime.stages import _verify_objective_action
    view = {"mission_id": MISSION_ID}
    rows = []
    hard_violations = []
    steps_executed = 0
    denials = 0
    for i, out in enumerate(episode_outputs):
        broker_out = out.get("broker") or {}
        decision = (broker_out.get("decision") or None)
        has_pep = "pep" in out
        if decision is not None and decision.decision == "allow" and has_pep:
            steps_executed += 1
        if decision is not None and decision.decision != "allow":
            denials += 1
            if has_pep:
                hard_violations.append(f"step {i}: PEP ran after denial")
        # unauthorized-action check: an allowed action must be within the
        # approved D2 vocabulary (the policy is loaded from the artifact).
        if decision is not None and decision.decision == "allow":
            req = (out.get("planner_request") or {}).get("request")
            act = req.action_type if req is not None else ""
            if act not in {a["action_type"] for a in ACTIONS.values()}:
                hard_violations.append(f"step {i}: unauthorized action type {act!r}")
    objective = _verify_objective_action  # noqa: F841 (documented use below)
    verdicts = {}
    for rid in CONSTRAINT_ECHO["objective_requires"]:
        verdicts[rid] = _verify_objective_action(store, view, rid,
                                                 (run_dir / "artifacts",),
                                                 broker_authority=broker_authority)
    verified_completion = all(v["ok"] for v in verdicts.values())
    evidence_complete = verified_completion and not hard_violations
    return {
        "candidate": policy.policy_id, "scenario": scenario,
        "content_hash": policy.content_hash(),
        "termination": termination.reason,
        "steps_executed": steps_executed, "denials": denials,
        "wall_seconds": round(wall, 3),
        "objective_verdicts": {k: {"ok": v["ok"], "reason": v["reason"][:160]}
                               for k, v in verdicts.items()},
        "verified_completion": verified_completion,
        "evidence_complete": evidence_complete,
        "hard_violations": hard_violations,
        "unscorable": None,
        "run_dir": str(run_dir),
    }


# ── ranking + report (regenerable from the manifest alone) ──────────────

def rank(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Declared lexicographic rule; unscorable/hard-violating runs excluded."""
    eligible = [r for r in runs if not r["hard_violations"] and not r["unscorable"]]
    excluded = [r for r in runs if r not in eligible]
    ordered = sorted(eligible, key=lambda r: (
        0 if r["verified_completion"] else 1,
        0 if r["evidence_complete"] else 1,
        r["steps_executed"], r["candidate"], r["scenario"]))
    # pairs are emitted as lists so JSON round-trips are identity-preserving
    return [[r["candidate"], r["scenario"]] for r in ordered] + \
           [[r["candidate"], r["scenario"]] for r in excluded]


def build_report(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Regenerate the evaluation report from the manifest (no re-runs)."""
    runs = manifest["runs"]
    per_candidate: Dict[str, Dict[str, Any]] = {}
    for r in runs:
        c = per_candidate.setdefault(r["candidate"], {
            "runs": 0, "verified_completion": 0, "evidence_complete": 0,
            "hard_violations": 0, "unscorable": 0, "denials": 0,
            "steps_total": 0, "scenarios": {}})
        c["runs"] += 1
        c["verified_completion"] += int(r["verified_completion"])
        c["evidence_complete"] += int(r["evidence_complete"])
        c["hard_violations"] += len(r["hard_violations"])
        c["unscorable"] += int(r["unscorable"] is not None)
        c["denials"] += r["denials"]
        c["steps_total"] += r["steps_executed"]
        c["scenarios"][r["scenario"]] = {
            "verified_completion": r["verified_completion"],
            "steps_executed": r["steps_executed"],
            "termination": r["termination"][:160]}
    ranking = rank(runs)
    return {
        "experiment": manifest["experiment"],
        "candidates": {k: {kk: vv for kk, vv in v.items() if kk != "scenarios"}
                       for k, v in sorted(per_candidate.items())},
        "per_scenario": {k: v["scenarios"] for k, v in sorted(per_candidate.items())},
        "ranking": [list(pair) for pair in ranking],
        "excluded": [r["run_dir"] for r in runs if r["hard_violations"] or r["unscorable"]],
        "ranking_rule": "lexicographic: verified_completion desc, evidence_complete desc, "
                        "steps asc, policy_id asc; hard violations and unscorable runs excluded",
        "limits": "deterministic scenarios; no statistical confidence claims; "
                  "holdout-based generalization and promotion are out of scope (absent holdout)",
    }
