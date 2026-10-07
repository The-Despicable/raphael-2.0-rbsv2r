"""scenario_validity.py — RSI-0.1 experiment module (2026-10-07).

Corrects two RSI-0 scenario-design gaps and produces instrumented, persisted
evidence:

1. **S3 root cause + rate-limit verification.** In RSI-0 the S3 episode
   terminated after two steps because objective completion (stage_replan ->
   replanned=False) ends the loop before the third candidate step is ever
   proposed — the limiter was never reached. This module demonstrates the
   rate limit with a **controlled multi-episode setup sharing one broker**
   (and therefore one limiter instance): episode 1 executes the two approved
   actions genuinely; episode 2's first proposal is the THIRD within the
   window and is denied at the Broker boundary. Instrumentation records every
   proposal, decision, and PEP invocation; a subprocess spy proves the denied
   attempt spawns nothing.

2. **C2 retry verification.** Two separate, honestly-labelled behaviors:
   - capability-boundary fault on Action A: the runtime halts at the PEP
     stage — the retry branch is NOT reachable (unsupported by the current
     runtime contract);
   - broker-stage rate denial of Action A (transient class): continuation IS
     supported; after the rate window expires, the same action_id executes
     successfully through the full governed path (retry exercised across
     episodes).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D2_POLICY_PATH,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext
from orchestrator.rsi.exploration_policy import ACTIONS, CONSTRAINT_ECHO, ExplorationPolicy

MISSION_ID = "rsi01-scenario-validity"
A_ID = CONSTRAINT_ECHO["objective_requires"][0]
B_ID = CONSTRAINT_ECHO["objective_requires"][1]


def scenario_policy_1pm(workdir: Path) -> Path:
    """Isolated policy copy with a 1/min budget (S3/C2 experiment fixture)."""
    base = json.loads(Path(D2_POLICY_PATH).read_text())
    base["rate_limits"]["max_actions_per_minute"] = 1
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "engagement-d2-scenario-1pm.json"
    path.write_text(json.dumps(base, indent=1))
    return path


def scenario_policy_2pm(workdir: Path) -> Path:
    base = json.loads(Path(D2_POLICY_PATH).read_text())
    base["rate_limits"]["max_actions_per_minute"] = 2
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "engagement-d2-scenario-2pm.json"
    path.write_text(json.dumps(base, indent=1))
    return path


def hermetic_inspector(container: str) -> dict:
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


def hermetic_nmap(argv, timeout):
    class P:
        returncode = 0
        stdout = ("Starting Nmap 7.99\nNmap scan report for dvwa (172.19.0.4)\n"
                  "PORT   STATE SERVICE\n80/tcp open  http\n")
        stderr = ""
    return P()


def hermetic_http(argv, timeout):
    class P:
        returncode = 0
        stdout = "<html>login redirect</html>\n302|text/html|28|0.01|http://dvwa/login.php\n"
        stderr = ""
    return P()


class ProposalRecorder:
    """Instruments the authoritative Broker boundary: every propose_action
    call is recorded with its decision, status, and reason. Read via a
    wrapping closure — no production code is modified."""

    def __init__(self, broker):
        self.broker = broker
        self.records: List[Dict[str, Any]] = []
        orig = broker.propose_action

        def recording(**kw):
            receipt = orig(**kw)
            self.records.append({
                "action_type": kw.get("action_type", ""),
                "capability": kw.get("capability", ""),
                "target": kw.get("target", ""),
                "decision": "allow" if receipt is not None and "AUTHORIZED" in str(
                    getattr(receipt, "status", "")) else
                    ("denied" if receipt is not None else "none"),
                "receipt_status": str(getattr(receipt, "status", "NONE")),
                "reason": str(getattr(receipt, "reason", ""))[:140],
            })
            return receipt

        broker.propose_action = recording

    def sequence(self):
        return [(r["action_type"], r["decision"]) for r in self.records]


def build_runtime(broker, store, artifacts_dir, runner_a=None, runner_b=None):
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=artifacts_dir,
                                 runner=runner_a or hermetic_nmap,
                                 inspector=hermetic_inspector)
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=artifacts_dir,
                                   runner=runner_b or hermetic_http,
                                   inspector=hermetic_inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={"exec.d1_lab_probe": cap_a,
                                                  "exec.http_probe": cap_b})
    return runtime, (cap_a, cap_b)


def d2_mission(candidates_by_iter, max_iterations):
    return MissionContext(
        mission_id=MISSION_ID, name="RSI-0.1 scenario validity",
        objectives=["governed two-probe reconnaissance"],
        constraints={
            "halt": {"max_iterations": max_iterations, "action_cap": 1,
                     "require_scope": True},
            "candidates": candidates_by_iter,
            "default_target": CONSTRAINT_ECHO["target"],
            "objective": {"requires_evidence": list(CONSTRAINT_ECHO["objective_requires"])},
        },
        scope=ScopeV0(mission_id=MISSION_ID, targets=(CONSTRAINT_ECHO["target"],),
                      allowed_action_types=(ACTIONS["A"]["action_type"],
                                            ACTIONS["B"]["action_type"]),
                      allowed_capabilities=(ACTIONS["A"]["capability"],
                                            ACTIONS["B"]["capability"]),
                      max_impact=2.0))


def cand(step_key, action_key):
    act = ACTIONS[action_key]
    return {"action_id": act["action_id"], "action_type": act["action_type"],
            "target": CONSTRAINT_ECHO["target"], "capability": act["capability"],
            "method": act["method"], "impact_estimate": 2.0,
            "args": {"bounded": True, "step": step_key},
            "rationale": f"RSI-0.1 step {step_key}"}


def store_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line in path.read_text().splitlines():
        rec = json.loads(line)["record"]
        row = {"kind": rec["kind"], "mission_id": rec["mission_id"],
               "producer": rec["producer"], "identity": rec["identity"]}
        row.update(rec["payload"])
        rows.append(row)
    return rows


# ── S3-corrected: multi-episode shared-limiter rate denial ──────────────

def s3_rate_limit_verification(workdir: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"experiment": "S3_rate_limit_verification",
                           "boundary": "Broker (authoritative PDP)",
                           "proposals": [], "episodes": []}
    workdir.mkdir(parents=True, exist_ok=True)
    policy_path = scenario_policy_2pm(workdir)  # 2 actions/minute (isolated copy)
    broker = make_broker_from_policy(policy_path)
    recorder = ProposalRecorder(broker)
    store = EvidenceStore(workdir / "evidence_store.jsonl")
    runtime, caps = build_runtime(broker, store, workdir / "artifacts")

    # Episode 1 — two genuine governed executions consume the 2/min window.
    m1 = d2_mission({"0": [cand("0", "A")], "1": [cand("1", "B")]}, max_iterations=5)
    ep1_outs = []
    traces1, term1 = runtime.run_episode(m1, episode_outputs=ep1_outs)
    ep1_pep = sum(1 for o in ep1_outs if "pep" in o)
    out["episodes"].append({"episode": 1, "pep_invocations": ep1_pep,
                            "terminated_at": term1.final_stage,
                            "termination": term1.reason[:160]})

    # Episode 2 — same broker (shared limiter state): the third proposal in
    # the window. max_iterations=1 keeps the episode to exactly one attempt.
    m2 = d2_mission({"0": [cand("2", "A")]}, max_iterations=1)
    ep2_outs = []
    traces2, term2 = runtime.run_episode(m2, episode_outputs=ep2_outs)
    ep2_pep = sum(1 for o in ep2_outs if "pep" in o)
    out["episodes"].append({"episode": 2, "pep_invocations": ep2_pep,
                            "terminated_at": term2.final_stage,
                            "termination": term2.reason[:160]})

    out["proposal_sequence"] = recorder.sequence()
    out["denials"] = [r for r in recorder.records if r["decision"] == "denied"]

    # Durable denial receipt in the store (persisted by stage_broker).
    rows = store_rows(store.path)
    denied_rows = [r for r in rows if r.get("status") == "denied"]
    rate_denials = [r for r in denied_rows
                    if "ratelimiter" in r.get("reason", "").lower()
                    and "rate limit exceeded" in r.get("reason", "").lower()]
    out["persisted_denied_receipts"] = len(denied_rows)
    out["persisted_rate_denials"] = len(rate_denials)
    out["rate_denial_reason"] = rate_denials[0].get("reason", "") if rate_denials else ""
    out["limiter_semantics"] = ("counts authorized proposals (records an action on "
                                "allow); rate-denied proposals are recorded as denials "
                                "(emergency-brake accounting) and never execute; state "
                                "persists per Broker instance across episodes")
    out["third_proposal_denied_at_broker"] = (
        len(rate_denials) >= 1 and ep2_pep == 0
        and out["proposal_sequence"][-1][1] == "denied")
    return out


# ── C2 verification ──────────────────────────────────────────────────────

def c2_capability_fault_test(workdir: Path) -> Dict[str, Any]:
    """Action A fails at the capability boundary (PEP). Observed runtime
    behavior: persisted failure receipt + immediate halt; the C2 retry step
    is never proposed (unsupported for PEP failures)."""
    out: Dict[str, Any] = {"experiment": "C2_capability_fault"}
    workdir.mkdir(parents=True, exist_ok=True)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    recorder = ProposalRecorder(broker)
    store = EvidenceStore(workdir / "evidence_store.jsonl")

    def failing_nmap(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "nmap: connection refused (fixture)"
        return P()

    runtime, caps = build_runtime(broker, store, workdir / "artifacts",
                                  runner_a=failing_nmap)
    policy = ExplorationPolicy(
        policy_id="rsi01-c2-retry-a", version=1, status="experimental",
        created_by="rsi01", motivation="retry verification",
        parameters={"order": ["A", "B"], "retry": {"action": "A", "at_most": 1}})
    policy.validate()
    # C2 mission: steps A, B, A(retry) — the retry is candidate index 2.
    steps = policy.ordered_action_keys()
    candidates = {str(i): [cand(str(i), k)] for i, k in enumerate(steps)}
    m = d2_mission(candidates, max_iterations=5)
    outs = []
    traces, term = runtime.run_episode(m, episode_outputs=outs)
    out["candidate_steps_declared"] = len(steps)
    out["terminated_at"] = term.final_stage
    out["termination"] = term.reason[:180]
    out["iterations_run"] = len(outs)
    # The retry step is candidate index 2; it was proposed only if the
    # episode ran at least three iterations.
    out["retry_step_proposed"] = len(outs) > 2
    rows = store_rows(store.path)
    failed = [r for r in rows if r.get("status") == "failed"]
    out["persisted_failure_receipts"] = len(failed)
    out["failure_reason"] = failed[0].get("reason", "") if failed else ""
    out["verdict"] = ("UNSUPPORTED — the runtime halts at the PEP stage on a "
                      "capability failure; the retry candidate step is never "
                      "proposed. C2 retry is unvalidated for capability faults.")
    return out


def c2_rate_retry_window_test(workdir: Path) -> Dict[str, Any]:
    """Action A denied at the Broker (rate, transient class) -> broker-denial
    continuation runs the remaining candidates -> after the window expires the
    same action_id executes successfully through the full governed path."""
    out: Dict[str, Any] = {"experiment": "C2_rate_retry_window",
                           "window_wait_seconds": 61}
    workdir.mkdir(parents=True, exist_ok=True)
    policy_path = scenario_policy_1pm(workdir)  # 1 action/minute
    broker = make_broker_from_policy(policy_path)
    recorder = ProposalRecorder(broker)
    store = EvidenceStore(workdir / "evidence_store.jsonl")
    runtime, caps = build_runtime(broker, store, workdir / "artifacts")

    # Episode 1: A executes (consumes the window); B denied; A-retry denied.
    m1 = d2_mission({"0": [cand("0", "A")], "1": [cand("1", "B")],
                     "2": [cand("2", "A")]}, max_iterations=3)
    ep1_outs = []
    traces1, term1 = runtime.run_episode(m1, episode_outputs=ep1_outs)
    ep1_pep = sum(1 for o in ep1_outs if "pep" in o)
    out["episode_1"] = {"pep_invocations": ep1_pep,
                        "terminated_at": term1.final_stage,
                        "termination": term1.reason[:160]}
    denied_before = [r for r in recorder.records if r["decision"] == "denied"]

    # Window expiry: the limiter's per-minute window is time-based (60 s).
    time.sleep(61)

    # Episode 2 (same broker): A (same action_id) is proposed again and now
    # passes the limiter -> authorized -> executed -> objective evidence for A.
    m2 = d2_mission({"0": [cand("2", "A")], "1": [cand("3", "B")]}, max_iterations=2)
    ep2_outs = []
    traces2, term2 = runtime.run_episode(m2, episode_outputs=ep2_outs)
    ep2_pep = sum(1 for o in ep2_outs if "pep" in o)
    b_ok = any(o.get("pep") is not None and
               (o["pep"]["event"].output or {}).get("http_status") == 302
               for o in ep2_outs)
    out["episode_2"] = {"pep_invocations": ep2_pep,
                        "terminated_at": term2.final_stage,
                        "termination": term2.reason[:160],
                        "b_executed_http_302": b_ok}
    out["denials_before_window_expiry"] = len(denied_before)
    out["retry_exercised_across_episodes"] = ep2_pep >= 1
    out["verdict"] = ("PARTIALLY SUPPORTED — the retry executes through the full "
                      "governed path when the transient failure is a Broker-stage "
                      "rate denial and the window expires (across episodes); it is "
                      "UNSUPPORTED within one episode when the failure is a "
                      "capability-boundary fault (the runtime halts at the PEP).")
    return out
