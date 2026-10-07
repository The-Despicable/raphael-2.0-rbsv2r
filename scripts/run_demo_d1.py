#!/usr/bin/env python3
"""run_demo_d1.py — deterministic M2/D1 demonstration driver (no LLM).

Runs the same governed action three times through the canonical
Runtime → Broker → PEP → exec boundary:

  1. POSITIVE           — bounded D1 policy (engagement-d1-v1): the request is
                          authorized (decision_id), executed for real against
                          the local DVWA container, and bound into a receipt +
                          persisted evidence (artifact digest verified).
  2. RESTRICTIVE CONTROL— decision source swapped to bootstrap-v0: the same
                          request is DENIED; no process is spawned.
  3. KILL SWITCH        — the documented one-step revert (decision source →
                          bootstrap-v0): same denial, no process spawned.

Process-spawn proof for the denial phases: subprocess.run is instrumented
(spy) for the whole driver; the spy counter must not advance during any
denial phase, and the per-phase capability's invocation counter must stay 0.

All transcript/evidence artifacts land under
evidence/demo/d1/<timestamp>/ (never overwriting a prior run).
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
    D1Policy,
    make_broker_from_bootstrap,
    make_broker_from_policy,
    PolicyLoadError,
)
from orchestrator.runtime.loop import RaphaelRuntime  # noqa: E402
from orchestrator.runtime.organs import OrganBundle  # noqa: E402
from orchestrator.runtime.scope import ScopeV0  # noqa: E402
from orchestrator.runtime.types import MissionContext  # noqa: E402
from orchestrator.exec.capabilities.d1_lab_probe import (  # noqa: E402
    D1LabProbeCapability,
)
from orchestrator.exec.evidence_store import EvidenceStore  # noqa: E402
from orchestrator.runtime.evidence_v1 import EvidenceRecord  # noqa: E402

MISSION_ID = "d1-governed-action"
ACTION_TYPE = "recon_service_probe"
CAPABILITY = "exec.d1_lab_probe"
TARGET = "dvwa"
CANDIDATE = {
    "action_id": "ACT-D1-PROBE-0001",
    "action_type": ACTION_TYPE,
    "target": TARGET,
    "capability": CAPABILITY,
    "method": "nmap",
    "impact_estimate": 2.0,
    "args": {"probe": "nmap_service", "bounded": True},
    "rationale": "D1 bounded service probe of the declared lab identity",
}


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
    """Counts real subprocess spawns inside this process."""

    def __init__(self):
        self.count = 0
        self._orig = subprocess.run

    def arm(self):
        spy = self

        def counting(*a, **kw):
            spy.count += 1
            return spy._orig(*a, **kw)

        subprocess.run = counting

    @property
    def count_now(self):
        return self.count


def build_positive(transcript: Path):
    store = EvidenceStore(transcript / "evidence_store.jsonl")
    policy = D1Policy()  # fail-closed load; carries artifact sha256
    broker = make_broker_from_policy()
    capability = D1LabProbeCapability(
        broker=broker, artifacts_dir=transcript / "artifacts"
    )
    runtime = RaphaelRuntime(broker=broker, capability=capability, organs=OrganBundle(evidence_store=store))
    scope = ScopeV0(
        mission_id=MISSION_ID,
        targets=(TARGET,),
        allowed_action_types=(ACTION_TYPE,),
        allowed_capabilities=(CAPABILITY,),
        max_impact=2.0,
    )
    mission = MissionContext(
        mission_id=MISSION_ID,
        name="D1 Governed Action",
        objectives=["confirm the local DVWA HTTP service via one governed probe"],
        constraints={
            "halt": {"max_iterations": 1, "action_cap": 1, "require_scope": True},
            "candidates": {"0": [dict(CANDIDATE)]},
            "default_target": TARGET,
        },
        scope=scope,
    )
    return policy, store, capability, runtime, mission, scope


def run_phase(runtime, mission, label, episode_outputs):
    traces, termination = runtime.run_episode(mission, episode_outputs=episode_outputs)
    return traces, termination


def execute_positive(transcript: Path, store, spy: SubprocessSpy) -> dict:
    policy, store, capability, runtime, mission, scope = build_positive(transcript)
    episode_outputs: list = []
    before = spy.count_now
    traces, termination = run_phase(runtime, mission, "positive", episode_outputs)
    spawns_during = spy.count_now - before

    if termination.terminated and termination.final_stage != "replan":
        raise AssertionError(
            f"positive phase terminated early at '{termination.final_stage}': {termination.reason}"
        )
    out = episode_outputs[0]
    decision = out["broker"]["decision"]
    broker_receipt = out["broker"]["receipt"]
    event = out["pep"]["event"]
    evidence_receipt = out["receipt"]["receipt"]

    if decision.decision != "allow":
        raise AssertionError(f"positive phase denied: {decision.reason}")
    if event.decision_id != decision.decision_id:
        raise AssertionError("PEP event is not linked to the broker decision_id")
    if evidence_receipt.decision_id != decision.decision_id:
        raise AssertionError("EvidenceReceipt is not linked to the broker decision_id")
    if evidence_receipt.broker_receipt_id != broker_receipt.action_id:
        raise AssertionError("EvidenceReceipt does not reference the broker receipt action_id")
    pep_output = event.output or {}
    if not pep_output.get("service_confirmed"):
        raise AssertionError("probe did not confirm the expected HTTP service on dvwa")

    # Artifact integrity: the recorded sha256 must match the stored bytes.
    relpath = pep_output["artifact_relpath"]
    artifact_file = transcript / relpath
    import hashlib
    digest = hashlib.sha256(artifact_file.read_bytes()).hexdigest()
    if digest != pep_output["artifact_sha256"]:
        raise AssertionError("artifact digest mismatch: stored bytes are not the recorded artifact")

    # Persist the artifact evidence record, parented on the execution record
    # the canonical receipt stage appended (execution -> artifact provenance).
    execution_identity = ""
    for line in (transcript / "evidence_store.jsonl").read_text().splitlines():
        rec = json.loads(line)["record"]
        if rec["kind"] == "execution_result":
            execution_identity = rec["identity"]
            break
    if not execution_identity:
        raise AssertionError("no persisted execution_result evidence record found")
    artifact_record = EvidenceRecord.artifact(
        mission_id=MISSION_ID,
        producer="scripts.run_demo_d1",
        relpath=relpath,
        size_bytes=pep_output["artifact_size_bytes"],
        sha256=pep_output["artifact_sha256"],
        execution_ref=execution_identity,
        parents=(execution_identity,),
    )
    store.append(artifact_record)

    return {
        "phase": "positive",
        "policy": {"name": policy.name, "version": policy.version, "sha256": policy.sha256},
        "decision_id": decision.decision_id,
        "decision": decision.decision,
        "action_id": broker_receipt.action_id,
        "target_identity": pep_output["target_identity"],
        "result_status": str(broker_receipt.status),
        "service_confirmed": pep_output["service_confirmed"],
        "probe_argv": pep_output["probe_argv"],
        "receipt_ref": {
            "event_id": event.event_id,
            "broker_receipt_id": broker_receipt.action_id,
            "decision_id": decision.decision_id,
            "evidence_receipt_id": evidence_receipt.event_id,
            "artifact_refs": list(evidence_receipt.artifact_refs or ()),
        },
        "artifact": {
            "relpath": relpath,
            "sha256": pep_output["artifact_sha256"],
            "size_bytes": pep_output["artifact_size_bytes"],
            "digest_verified": True,
            "execution_evidence_identity": execution_identity,
        },
        "subprocess_spawns_during_phase": spawns_during,
        "stage_trace": traces[0].entries if hasattr(traces[0], "entries") else str(traces[0]),
    }


def run_denial_phase(runtime, mission, store, label, spy: SubprocessSpy) -> dict:
    capability = runtime._capability
    episode_outputs: list = []
    before_spy = spy.count_now
    before_invocations = capability.invocation_count
    traces, termination = run_phase(runtime, mission, label, episode_outputs)
    out = episode_outputs[0] if episode_outputs else {}
    stage_failure = termination.final_stage
    if stage_failure != "broker":
        raise AssertionError(
            f"{label}: expected denial at the broker stage, terminated at '{stage_failure}'"
        )
    if "pep" in out:
        raise AssertionError(f"{label}: PEP stage ran despite denial")
    decision = (out.get("broker") or {}).get("decision")
    spawned = spy.count_now - before_spy
    if spawned != 0:
        raise AssertionError(f"{label}: {spawned} process spawn(s) during a DENIED action")
    if capability.invocation_count != before_invocations:
        raise AssertionError(f"{label}: capability invoked despite denial")
    return {
        "phase": label,
        "terminated_at": termination.final_stage,
        "reason": termination.reason,
        "decision": decision.decision if decision else "deny",
        "decision_id": decision.decision_id if decision else "",
        "deny_reason": decision.reason if decision else termination.reason,
        "pep_ran": False,
        "process_spawns": 0,
        "capability_invocations": capability.invocation_count,
    }


def main() -> int:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = REPO / "evidence" / "demo" / "d1"
    transcript = base / stamp
    suffix = 0
    while transcript.exists():
        suffix += 1
        transcript = base / f"{stamp}_{suffix}"
    transcript.mkdir(parents=True)
    print(f"[d1] transcript: {transcript}")

    spy = SubprocessSpy()
    spy.arm()
    report = {"mission_id": MISSION_ID, "generated_at": time.time(), "phases": []}

    # 1. positive — the governed action really runs
    positive = execute_positive(transcript, None, spy)
    report["phases"].append(positive)
    print(f"[d1] POSITIVE  decision_id={positive['decision_id']} "
          f"action_id={positive['action_id']} status={positive['result_status']} "
          f"service_confirmed={positive['service_confirmed']} "
          f"artifact_sha256={positive['artifact']['sha256'][:16]}…")

    store_path = transcript / "evidence_store.jsonl"

    # 2. restrictive control — bootstrap-v0 denies the same request
    store = EvidenceStore(store_path)
    broker_r = make_broker_from_bootstrap()
    cap_r = D1LabProbeCapability(broker=broker_r, artifacts_dir=transcript / "artifacts")
    scope_r = ScopeV0(
        mission_id=MISSION_ID, targets=(TARGET,),
        allowed_action_types=(ACTION_TYPE,), allowed_capabilities=(CAPABILITY,),
        max_impact=2.0,
    )
    mission_r = MissionContext(
        mission_id=MISSION_ID, name="D1 Governed Action (restrictive control)",
        objectives=["same request under the restrictive policy"],
        constraints={"halt": {"max_iterations": 1, "action_cap": 1, "require_scope": True},
                     "candidates": {"0": [dict(CANDIDATE)]}, "default_target": TARGET},
        scope=scope_r,
    )
    runtime_r = RaphaelRuntime(broker=broker_r, capability=cap_r,
                               organs=OrganBundle(evidence_store=store))
    restrictive = run_denial_phase(runtime_r, mission_r, store, "restrictive_control", spy)
    report["phases"].append(restrictive)
    print(f"[d1] RESTRICTIVE denied at '{restrictive['terminated_at']}' "
          f"reason='{restrictive['deny_reason'][:80]}' spawns=0")

    # 3. kill switch — the documented swap of the decision source
    store = EvidenceStore(store_path)
    broker_k = make_broker_from_bootstrap()
    cap_k = D1LabProbeCapability(broker=broker_k, artifacts_dir=transcript / "artifacts")
    runtime_k = RaphaelRuntime(broker=broker_k, capability=cap_k,
                               organs=OrganBundle(evidence_store=store))
    kill = run_denial_phase(runtime_k, mission_r, store, "kill_switch", spy)
    kill["kill_switch_note"] = (
        "decision source swapped to policies/bootstrap-v0.json "
        "(the documented one-file revert); same request, DENIED, no process spawned"
    )
    report["phases"].append(kill)
    print(f"[d1] KILL-SWITCH denied at '{kill['terminated_at']}' spawns=0")

    # 4. wrong target — same capability, a target outside the lab identity
    store = EvidenceStore(store_path)
    broker_w = make_broker_from_policy()
    cap_w = D1LabProbeCapability(broker=broker_w, artifacts_dir=transcript / "artifacts")
    wrong = dict(CANDIDATE, action_id="ACT-D1-PROBE-0002", target="example.invalid")
    mission_w = MissionContext(
        mission_id=MISSION_ID, name="D1 wrong-target control",
        objectives=["same capability against a non-lab target must deny"],
        constraints={"halt": {"max_iterations": 1, "action_cap": 1, "require_scope": True},
                     "candidates": {"0": [wrong]}, "default_target": TARGET},
        scope=ScopeV0(mission_id=MISSION_ID, targets=(TARGET,),
                      allowed_action_types=(ACTION_TYPE,),
                      allowed_capabilities=(CAPABILITY,), max_impact=2.0),
    )
    runtime_w = RaphaelRuntime(broker=broker_w, capability=cap_w,
                               organs=OrganBundle(evidence_store=store))
    wrong_target = run_denial_phase(runtime_w, mission_w, store, "wrong_target", spy)
    report["phases"].append(wrong_target)
    print(f"[d1] WRONG-TARGET denied: '{wrong_target['deny_reason'][:80]}'")

    report["no_process_spawned_in_any_denial_phase"] = all(
        p.get("process_spawns", 0) == 0 for p in report["phases"] if p["phase"] != "positive"
    )
    report["subprocess_spies_total"] = spy.count_now
    report["uuid_marker"] = uuid.uuid4().hex

    (transcript / "transcript.json").write_text(json.dumps(_jsonable(report), indent=2))
    lines = [
        "# D1 GOVERNED ACTION TRANSCRIPT",
        f"mission: {MISSION_ID}    generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        "## positive",
        f"policy: {positive['policy']['name']} v{positive['policy']['version']} sha256={positive['policy']['sha256'][:16]}…",
        f"broker decision : {positive['decision']} (decision_id={positive['decision_id']})",
        f"action_id       : {positive['action_id']}",
        f"target identity : {json.dumps(positive['target_identity'], sort_keys=True)}",
        f"probe argv      : {' '.join(positive['probe_argv'])}",
        f"result status   : {positive['result_status']}  service_confirmed={positive['service_confirmed']}",
        f"receipt         : event={positive['receipt_ref']['event_id']} broker_receipt={positive['receipt_ref']['broker_receipt_id']} evidence_receipt={positive['receipt_ref']['evidence_receipt_id']}",
        f"artifact        : {positive['artifact']['relpath']} sha256={positive['artifact']['sha256']} (digest verified)",
        f"evidence store  : {store_path} (execution_result + artifact records)",
        "",
        "## restrictive control (bootstrap-v0)",
        f"terminated at: {restrictive['terminated_at']}  decision={restrictive['decision']}  reason={restrictive['deny_reason']}",
        f"process spawns: {restrictive['process_spawns']}  capability invocations: {restrictive['capability_invocations']}",
        "",
        "## kill switch (decision source swapped to bootstrap-v0)",
        f"terminated at: {kill['terminated_at']}  decision={kill['decision']}",
        f"process spawns: {kill['process_spawns']}  capability invocations: {kill['capability_invocations']}",
        "",
        "## wrong-target control",
        f"terminated at: {wrong_target['terminated_at']}  reason={wrong_target['deny_reason']}",
        "",
        "every denial phase spawned zero processes and invoked the capability zero times.",
    ]
    (transcript / "transcript.md").write_text("\n".join(lines) + "\n")
    print(f"[d1] evidence written under {transcript}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (PolicyLoadError, AssertionError, Exception) as exc:
        print(f"[d1] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
