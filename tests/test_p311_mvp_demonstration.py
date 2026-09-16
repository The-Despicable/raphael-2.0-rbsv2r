"""
P3.11 §14.10 MVP demonstration test.

Deterministic local mission through the canonical Runtime path:

mission file
  -> scope declared (ScopeV0, require_scope=True)
  -> Student + Planner produce candidate/request (recording Student;
     real Planner.decide() over mission candidates)
  -> Broker authorizes the valid action (iteration 1)
  -> Broker denies the injected out-of-scope action (iteration 0,
     scope conjunction; no execution)
  -> PEP runs the safe proving capability (iteration 1 only)
  -> receipt + artifact + provenance created
  -> WorldModel accepts evidence-backed state (receipt evidence)
  -> contradiction/failure triggers replan (denial feedback)
  -> Student outcome is recorded (recording mode, both iterations)
  -> DecisionTrace emitted (mission-level evidence)

Temporal order: iteration 0 denies the injected candidate first; the
PERSISTENT denial feedback suppresses it on iteration 1, where the
Planner selects the valid candidate. The replan stage then reports a
changed next decision. This order is what makes §14.11 criterion 4
(replan changes the next decision) observable.

No network, no Arena, no Decepticon, no Kali/C2, no offensive tools.
Safe proving capability only. Canonical perimeter only.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime import RaphaelRuntime, MissionContext
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import DecisionTrace

MISSION_FILE = REPO_ROOT / "tests" / "p311_mvp_mission.json"


def _load_mission():
    with open(MISSION_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _build_runtime_and_mission():
    doc = _load_mission()
    scope = ScopeV0.from_dict(doc["scope"])
    constraints = {
        "candidates": doc["candidates"],
        "default_target": doc["constraints"]["default_target"],
        "objective_id": doc["constraints"]["objective_id"],
    }
    mission = MissionContext(
        mission_id=doc["mission_id"],
        name=doc["name"],
        objectives=list(doc["objectives"]),
        constraints=constraints,
        scope=scope,
    )
    return RaphaelRuntime(), mission, doc, scope


def test_p311_mvp_mission_file_is_deterministic():
    """The mission fixture loads deterministically (byte-stable content)."""
    raw = MISSION_FILE.read_bytes()
    doc = json.loads(raw)
    assert doc["mission_id"] == "p311-mvp-001"
    assert doc["scope"]["mission_id"] == "p311-mvp-001"
    # Canonical re-serialization is stable (sort_keys): the file is the
    # deterministic source of truth for the demonstration.
    assert json.loads(json.dumps(doc, sort_keys=True)) == doc
    assert set(doc["candidates"].keys()) == {"0", "1"}
    assert len(doc["candidates"]["0"]) == 1
    assert len(doc["candidates"]["1"]) == 2


def test_p311_mvp_full_chain():
    """§14.10: the complete causal chain through the canonical path."""
    rt, mission, doc, scope = _build_runtime_and_mission()
    episode_outputs: list = []
    traces, termination = rt.run_episode(
        mission, max_iterations=2, require_scope=True,
        episode_outputs=episode_outputs,
    )

    # ── Episode shape: denial first, then replanned success ──
    assert len(traces) == 2, f"expected 2 iteration traces, got {len(traces)}"
    assert len(episode_outputs) == 2
    t0_entries = {e["stage"]: e for e in traces[0].entries}
    t1_entries = {e["stage"]: e for e in traces[1].entries}
    assert traces[0].mission_id == "p311-mvp-001"
    assert traces[1].mission_id == "p311-mvp-001"

    # ── Iteration 0: injected out-of-scope action reaches the Broker
    #    and is denied; nothing executes ──
    assert t0_entries["planner_request"]["success"] is True
    assert t0_entries["broker"]["success"] is False
    assert "outside declared scope" in (t0_entries["broker"]["error"] or "")
    assert "prod.db.internal" in (t0_entries["broker"]["error"] or "")
    # Denial terminates iteration 0 at the broker stage: no PEP, no
    # receipt, no integration stages ran.
    assert "pep" not in t0_entries
    assert "receipt" not in t0_entries
    out0 = episode_outputs[0]
    plan0 = out0["planner_request"]["plan_decision"]
    assert plan0.selected_action_id == "mvp-injected-001"
    # The injected candidate never executed: capability untouched.
    assert rt._capability.invocation_count == 1  # only iteration 1 executes

    # ── Denial feedback recorded (failure signal for replan) ──
    feedback = rt._organs.planner.feedback_records
    assert len(feedback) == 1
    rec = next(iter(feedback.values()))
    assert rec.action_type == "safe_proving_capability"
    assert rec.target == "prod.db.internal"
    assert rec.capability == "fixture.inspect"
    assert rec.denial_class.value == "persistent"

    # ── Iteration 1: Planner suppresses the denied triple and selects
    #    the valid candidate; Broker authorizes ──
    assert t1_entries["broker"]["success"] is True
    out1 = episode_outputs[1]
    plan1 = out1["planner_request"]["plan_decision"]
    assert plan1.selected_action_id == "mvp-valid-001"
    assert plan1.selected_action_id != plan0.selected_action_id
    req1 = out1["planner_request"]["request"]
    assert req1.action_id == "mvp-valid-001"
    assert req1.target == "system_info.name"

    # ── PEP executes the safe proving capability exactly once ──
    assert t1_entries["pep"]["success"] is True
    event = out1["pep"]["event"]
    assert event.capability == "fixture.inspect"
    assert event.target == "system_info.name"
    assert event.outcome == "ok"
    assert event.output is not None
    assert rt._capability.invocation_count == 1

    # ── Receipt / decision linkage (§14.11.1: every execution event
    #    carries a Broker decision id) ──
    decision = out1["broker"]["decision"]
    receipt_obj = out1["broker"]["receipt"]
    assert decision.decision == "allow"
    assert event.decision_id == receipt_obj.action_id == decision.decision_id
    assert event.action_id == req1.action_id
    ev_receipt = out1["receipt"]["receipt"]
    assert ev_receipt.event_id == event.event_id
    assert ev_receipt.decision_id == decision.decision_id

    # ── WorldModel accepts evidence-backed state ──
    graph = rt._organs.evidence_graph
    receipt_evidence = [
        ev for ev in graph.get_all_evidence()
        if getattr(ev, "raw_content", "") == f"receipt:{ev_receipt.receipt_id}"
    ]
    assert len(receipt_evidence) == 1
    assert out1["worldmodel_read"]["available"] is True
    assert out1["contradiction"]["triggered"] is True
    assert out1["contradiction"]["denial_failures"] == 1
    replan_out = out1["replan"]
    assert replan_out["replanned"] is True
    assert replan_out["denied_triple"] == [
        "safe_proving_capability", "prod.db.internal", "fixture.inspect",
    ]
    assert replan_out["next_triple"] == [
        "safe_proving_capability", "system_info.name", "fixture.inspect",
    ]
    assert replan_out["denied_triple"] != replan_out["next_triple"]
    assert replan_out["next_receipt_id"] == receipt_obj.action_id

    # ── Student outcome recorded (recording mode, both iterations) ──
    assert out0["student_candidate"]["mode"] == "recording"
    assert out1["student_candidate"]["mode"] == "recording"
    assert out0["student_candidate"]["candidates_proposed"] > 0
    assert out1["student_candidate"]["candidates_proposed"] > 0

    # ── Scope still enforced on the valid path ──
    assert scope.scope_hash() == ScopeV0.from_dict(doc["scope"]).scope_hash()

    # ── DecisionTrace: mission-level evidence of the full chain ──
    summary = DecisionTrace(mission_id="p311-mvp-001")
    summary.append({"link": "mission_file", "value": str(MISSION_FILE)})
    summary.append({"link": "scope_hash", "value": scope.scope_hash()})
    summary.append({"link": "iteration_0_plan", "value": plan0.selected_action_id})
    summary.append({"link": "iteration_0_broker", "value": "deny"})
    summary.append({"link": "iteration_1_plan", "value": plan1.selected_action_id})
    summary.append({"link": "iteration_1_broker", "value": "allow"})
    summary.append({"link": "pep_event", "value": event.event_id})
    summary.append({"link": "broker_receipt", "value": receipt_obj.action_id})
    summary.append({"link": "evidence_receipt", "value": ev_receipt.receipt_id})
    summary.append({"link": "replan", "value": "replanned=True"})
    summary.append({"link": "changed_decision",
                    "value": f"{replan_out['denied_triple']} -> {replan_out['next_triple']}"})
    assert summary.mission_id == "p311-mvp-001"
    assert len(summary.entries) == 11


def test_p311_mvp_denial_executes_nothing():
    """§14.11.2 (denial half): the denied request reaches no primitive."""
    rt, mission, doc, scope = _build_runtime_and_mission()
    # Single iteration with only the injected candidate: denial, no PEP.
    mission.constraints = {
        "candidates": {"0": doc["candidates"]["0"]},
        "default_target": "system_info.name",
        "objective_id": "mvp-objective-prove-fixture",
    }
    episode_outputs: list = []
    traces, termination = rt.run_episode(
        mission, max_iterations=1, require_scope=True,
        episode_outputs=episode_outputs,
    )
    assert len(traces) == 1
    assert termination.final_stage == "broker"
    assert rt._capability.invocation_count == 0
    assert "pep" not in {e["stage"] for e in traces[0].entries}


def test_replan_changes_next_decision():
    """§14.7 / §14.10 / §14.9: denial feedback changes the next decision."""
    rt, mission, doc, scope = _build_runtime_and_mission()
    outputs: list = []
    traces, term = rt.run_episode(
        mission, max_iterations=2, require_scope=True,
        episode_outputs=outputs,
    )

    plan0 = outputs[0]["planner_request"]["plan_decision"]
    plan1 = outputs[1]["planner_request"]["plan_decision"]
    # The denied proposal is suppressed; the next iteration chooses another.
    assert plan0.selected_action_id != plan1.selected_action_id
    # Iteration 0 denied by Scope before execution; iteration 1 executed.
    t0_broker = next(e for e in traces[0].entries if e["stage"] == "broker")
    assert t0_broker["success"] is False
    assert "outside declared scope" in (t0_broker["error"] or "")
    assert outputs[1]["broker"]["decision"].decision == "allow"
    assert rt._capability.invocation_count == 1
    # The replan stage reports the changed decision triple.
    replan = outputs[1]["replan"]
    assert replan["replanned"] is True
    assert replan["denied_triple"] != replan["next_triple"]
