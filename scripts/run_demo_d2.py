#!/usr/bin/env python3
"""run_demo_d2.py — deterministic D2 bounded-episode demonstration (no LLM).

One governed two-action episode through the canonical
Runtime → Broker → PEP → exec boundary, followed by negative controls:

  POSITIVE             — D2 policy (engagement-d2-v1): Action A (governed D1
                         nmap probe) then Action B (fixed in-container HTTP GET
                         of http://dvwa/); objective terminates on persisted
                         evidence for both probes.
  KILL SWITCH          — decision source swapped to bootstrap-v0: every step
                         denied; zero process spawns; denial receipts persisted.
  WRONG TARGET         — same capability against a non-lab identity: denied.

All receipts (attempts, denials, failures, executions) are persisted to the
timestamped evidence store; transcripts never overwrite a prior run.
"""
import dataclasses
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from orchestrator.runtime.policy import (  # noqa: E402
    D2_POLICY_PATH,
    D1Policy,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
from orchestrator.runtime.loop import RaphaelRuntime  # noqa: E402
from orchestrator.runtime.organs import OrganBundle  # noqa: E402
from orchestrator.runtime.scope import ScopeV0  # noqa: E402
from orchestrator.runtime.types import MissionContext  # noqa: E402
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability  # noqa: E402
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability  # noqa: E402
from orchestrator.exec.evidence_store import EvidenceStore  # noqa: E402

MISSION_ID = "d2-bounded-episode"
ACTION_A, ACTION_B = "recon_service_probe", "lab_http_probe"
CAP_A, CAP_B = "exec.d1_lab_probe", "exec.http_probe"
TARGET = "dvwa"
A_ID, B_ID = "ACT-D2-PROBE-0001", "ACT-D2-HTTP-0002"


def _jsonable(obj):
    if dataclasses.is_dataclass(obj):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


class SubprocessSpy:
    def __init__(self):
        self.count = 0
        self._orig = subprocess.run

    def arm(self):
        spy = self

        def counting(*a, **kw):
            spy.count += 1
            return spy._orig(*a, **kw)

        subprocess.run = counting


def cand(action_id, action_type, capability, target=TARGET):
    return {"action_id": action_id, "action_type": action_type, "target": target,
            "capability": capability,
            "method": "nmap" if capability == CAP_A else "curl",
            "impact_estimate": 2.0, "args": {"bounded": True},
            "rationale": "D2 bounded action (operator-approved scope)"}


def d2_scope():
    return ScopeV0(mission_id=MISSION_ID, targets=(TARGET,),
                   allowed_action_types=(ACTION_A, ACTION_B),
                   allowed_capabilities=(CAP_A, CAP_B), max_impact=2.0)


def d2_mission(max_iterations):
    return MissionContext(
        mission_id=MISSION_ID, name="D2 bounded episode",
        objectives=["governed two-probe reconnaissance of the local DVWA lab"],
        constraints={
            "halt": {"max_iterations": max_iterations, "action_cap": 1,
                     "require_scope": True},
            "candidates": {"0": [cand(A_ID, ACTION_A, CAP_A)],
                           "1": [cand(B_ID, ACTION_B, CAP_B)]},
            "default_target": TARGET,
            "objective": {"requires_evidence": [A_ID, B_ID]},
        },
        scope=d2_scope())


def build(transcript, broker):
    store = EvidenceStore(transcript / "evidence_store.jsonl")
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=transcript / "artifacts")
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=transcript / "artifacts")
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A: cap_a, CAP_B: cap_b})
    return store, {"CAP_A": cap_a, "CAP_B": cap_b}, runtime


def store_rows(transcript):
    rows = []
    for line in (transcript / "evidence_store.jsonl").read_text().splitlines():
        rec = json.loads(line)["record"]
        row = {"kind": rec["kind"], "identity": rec["identity"]}
        row.update(rec["payload"])
        rows.append(row)
    return rows


def main() -> int:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = REPO / "evidence" / "demo" / "d2"
    transcript = base / stamp
    suffix = 0
    while transcript.exists():
        suffix += 1
        transcript = base / f"{stamp}_{suffix}"
    transcript.mkdir(parents=True)
    print(f"[d2] transcript: {transcript}")

    spy = SubprocessSpy()
    spy.arm()
    report = {"mission_id": MISSION_ID, "generated_at": time.time(), "phases": []}
    policy = D1Policy(D2_POLICY_PATH)

    # ── POSITIVE: the bounded two-action episode ─────────────────────────
    broker = make_broker_from_policy(D2_POLICY_PATH)
    store, caps, runtime = build(transcript, broker)
    episode_outputs = []
    traces, termination = runtime.run_episode(d2_mission(max_iterations=5),
                                              episode_outputs=episode_outputs)
    if "objective met" not in termination.reason:
        raise AssertionError(f"positive episode did not meet objective: {termination.reason}")
    pos = {"phase": "positive",
           "policy": {"name": policy.name, "version": policy.version,
                      "sha256": policy.sha256},
           "termination": termination.reason,
           "steps": []}
    for i, out in enumerate(episode_outputs):
        decision = out["broker"]["decision"]
        receipt = out["broker"]["receipt"]
        request = out["planner_request"]["request"]
        event = out["pep"]["event"]
        evidence_receipt = out["receipt"]["receipt"]
        if decision.decision != "allow":
            raise AssertionError(f"step {i} denied in positive episode")
        if event.decision_id != decision.decision_id:
            raise AssertionError("event not linked to broker decision")
        if evidence_receipt.broker_receipt_id != receipt.action_id:
            raise AssertionError("evidence receipt not linked to broker receipt")
        pep_output = event.output or {}
        step = {"step": i, "action_id": request.action_id,
                "action_type": request.action_type,
                "capability": request.capability,
                "decision_id": decision.decision_id,
                "target_identity": pep_output.get("target_identity"),
                "result_status": str(receipt.status)}
        if request.action_type == ACTION_A:
            step["service_confirmed"] = pep_output.get("service_confirmed")
        else:
            step["http_status"] = pep_output.get("http_status")
            step["redirect_url"] = pep_output.get("redirect_url")
            step["redirect_followed"] = pep_output.get("redirect_followed")
            # A 3xx with a recorded redirect_url is the EXPECTED honest
            # observation (DVWA / -> login.php); what is forbidden is
            # following it. The capability never follows (no -L, --max-redirs 0).
            if pep_output.get("redirect_followed") is not False:
                raise AssertionError("redirect_followed must be explicitly False")
            if "-L" in pep_output.get("probe_argv", []):
                raise AssertionError("redirect flag present in probe argv")
        if "artifact_sha256" in pep_output:
            import hashlib
            f = transcript / pep_output["artifact_relpath"]
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            if digest != pep_output["artifact_sha256"]:
                raise AssertionError("artifact digest mismatch")
            step["artifact"] = {"relpath": pep_output["artifact_relpath"],
                                "sha256": pep_output["artifact_sha256"],
                                "digest_verified": True}
        pos["steps"].append(step)
    report["phases"].append(pos)
    for s in pos["steps"]:
        print(f"[d2] step {s['step']}: {s['action_type']} via {s['capability']} "
              f"decision_id={s['decision_id']} status={s['result_status']} "
              f"artifact={s.get('artifact', {}).get('sha256', 'n/a')[:16]}…")
    print(f"[d2] POSITIVE termination: {termination.reason}")

    # ── KILL SWITCH: decision source swapped to bootstrap-v0 ────────────
    store = EvidenceStore(transcript / "evidence_store.jsonl")
    kill_broker = make_broker_from_bootstrap()
    _, caps_k, runtime_k = build(transcript, kill_broker)
    before = spy.count
    episode_outputs_k = []
    _, term_k = runtime_k.run_episode(d2_mission(max_iterations=2),
                                      episode_outputs=episode_outputs_k)
    outs_k = episode_outputs_k
    spawns_k = spy.count - before
    if spawns_k != 0 or any("pep" in o for o in outs_k):
        raise AssertionError("kill-switch episode executed something")
    invocations = sum(c.invocation_count for c in caps_k.values())
    kill = {"phase": "kill_switch", "terminated_at": term_k.final_stage,
            "steps_denied": len(outs_k), "process_spawns": spawns_k,
            "capability_invocations": invocations,
            "note": "decision source swapped to policies/bootstrap-v0.json"}
    report["phases"].append(kill)
    print(f"[d2] KILL-SWITCH: {len(outs_k)} steps denied, spawns={spawns_k}, "
          f"capability_invocations={invocations}")

    # ── WRONG TARGET: same capability, non-lab identity ─────────────────
    store = EvidenceStore(transcript / "evidence_store.jsonl")
    wrong_broker = make_broker_from_policy(D2_POLICY_PATH)
    _, caps_w, runtime_w = build(transcript, wrong_broker)
    wrong_mission = MissionContext(
        mission_id=MISSION_ID, name="D2 wrong-target control",
        objectives=["non-lab target must deny"],
        constraints={"halt": {"max_iterations": 1, "action_cap": 1,
                              "require_scope": True},
                     "candidates": {"0": [cand("ACT-D2-WRONG", ACTION_B, CAP_B,
                                               target="example.invalid")]},
                     "default_target": TARGET},
        scope=d2_scope())
    before = spy.count
    episode_outputs_w = []
    _, term_w = runtime_w.run_episode(wrong_mission, episode_outputs=episode_outputs_w)
    outs_w = episode_outputs_w
    spawns_w = spy.count - before
    if term_w.final_stage != "broker" or spawns_w != 0:
        raise AssertionError("wrong-target control failed to deny pre-execution")
    wrong = {"phase": "wrong_target", "terminated_at": term_w.final_stage,
             "process_spawns": spawns_w,
             "capability_invocations": sum(c.invocation_count for c in caps_w.values())}
    report["phases"].append(wrong)
    print(f"[d2] WRONG-TARGET denied at '{term_w.final_stage}', spawns={spawns_w}")

    # ── persisted receipts: every attempt accounted for ─────────────────
    rows = store_rows(transcript)
    exec_rows = [r for r in rows if r["kind"] == "execution_result"]
    denials = [r for r in exec_rows if r.get("status") == "denied"]
    successes = [r for r in exec_rows if r.get("status") in ("ok", "succeeded")]
    if len(successes) < 2:
        raise AssertionError("positive episode evidence missing from the store")
    if len(denials) < 3:  # 2 kill-switch steps + 1 wrong-target step
        raise AssertionError("denial receipts missing from the store")
    report["evidence_summary"] = {
        "execution_result_records": len(exec_rows),
        "denied_records": len(denials),
        "succeeded_records": len(successes),
        "store": str(transcript / "evidence_store.jsonl"),
    }
    report["no_process_spawned_in_any_denial_phase"] = (
        kill["process_spawns"] == 0 and wrong["process_spawns"] == 0)
    report["uuid_marker"] = uuid.uuid4().hex

    (transcript / "transcript.json").write_text(json.dumps(_jsonable(report), indent=2))
    lines = [
        "# D2 BOUNDED EPISODE TRANSCRIPT",
        f"mission: {MISSION_ID}  generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"policy: {policy.name} v{policy.version} sha256={policy.sha256[:16]}…",
        "",
        "## positive episode (2 steps, objective-terminated)",
    ]
    for s in pos["steps"]:
        lines.append(f"- step {s['step']}: {s['action_type']} ({s['capability']}) "
                     f"decision_id={s['decision_id']} status={s['result_status']} "
                     f"artifact={s.get('artifact', {}).get('sha256', '')}")
    a_step = pos["steps"][0]
    b_step = pos["steps"][1]
    lines += [
        f"- action A confirmed: {a_step.get('service_confirmed')}",
        f"- action B HTTP status: {b_step.get('http_status')} "
        f"redirect_url={b_step.get('redirect_url')} followed={b_step.get('redirect_followed')}",
        f"- termination: {pos['termination']}",
        f"- evidence store: {transcript / 'evidence_store.jsonl'} "
        f"({report['evidence_summary']['execution_result_records']} execution records)",
        "",
        "## kill switch (bootstrap-v0 decision source)",
        f"- steps denied: {kill['steps_denied']}; process spawns: {kill['process_spawns']}; "
        f"capability invocations: {kill['capability_invocations']}",
        "",
        "## wrong-target control",
        f"- terminated at: {wrong['terminated_at']}; process spawns: {wrong['process_spawns']}",
        "",
        "every denial produced a persisted receipt and zero process spawns.",
    ]
    (transcript / "transcript.md").write_text("\n".join(lines) + "\n")
    print(f"[d2] evidence written under {transcript}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[d2] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
