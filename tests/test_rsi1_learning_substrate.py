"""test_rsi1_learning_substrate.py — RSI-1 tests (2026-10-07).

Covers: ExperienceNode identity/validation, trusted ingestion (genuine,
fabricated, cross-episode, duplicate), ImprovementHypothesis contracts and
falsifiable verdicts, ExplorationPolicy lifecycle (v0 identity preserved,
active status refused), experiment snapshots with read-only replay, and the
contained GRPO-mechanics prototype (real parameter updates on a toy policy).
"""
import json
import tempfile
from pathlib import Path

import pytest

from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import make_broker_from_policy, D2_POLICY_PATH
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.types import MissionContext
from orchestrator.rsi.experience import (
    ExperienceError, ExperienceLog, ExperienceNode, ingest_episode,
)
from orchestrator.rsi.hypothesis import (
    FalsifiableEvaluation, HypothesisError, ImprovementHypothesis,
)
from orchestrator.rsi.exploration_policy import ExplorationPolicy
from orchestrator.rsi import snapshot as rsi_snapshot
from orchestrator.rsi import grpo_proto

MISSION = "d2-bounded-episode"
MISSION_ID = MISSION
A_ID = "ACT-D2-PROBE-0001"
B_ID = "ACT-D2-HTTP-0002"
EVIDENCE_V1 = __import__("orchestrator.runtime.evidence_v1",
                         fromlist=["EvidenceRecord"]).EvidenceRecord


def hermetic_episode(tmp_path):
    """Run a real governed 2-action hermetic episode; return (store, record)."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    cap_a = D1LabProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                 runner=_fake_nmap, inspector=_fake_inspector)
    cap_b = LabHttpProbeCapability(broker=broker, artifacts_dir=tmp_path / "artifacts",
                                   runner=_fake_curl, inspector=_fake_inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={"exec.d1_lab_probe": cap_a,
                                                  "exec.http_probe": cap_b})
    mission = MissionContext(
        mission_id=MISSION_ID, name="rsi1", objectives=["x"], scope=ScopeV0(
            mission_id=MISSION_ID, targets=("dvwa",),
            allowed_action_types=("recon_service_probe", "lab_http_probe"),
            allowed_capabilities=("exec.d1_lab_probe", "exec.http_probe"),
            max_impact=2.0),
        constraints={"halt": {"max_iterations": 5, "action_cap": 1,
                              "require_scope": True},
                     "candidates": {"0": [_cand(A_ID, "recon_service_probe",
                                                "exec.d1_lab_probe", "nmap")],
                                    "1": [_cand(B_ID, "lab_http_probe",
                                                "exec.http_probe", "curl")]},
                     "default_target": "dvwa",
                     "objective": {"requires_evidence": [A_ID, B_ID]}})
    episode_outputs = []
    _, termination = runtime.run_episode(mission, episode_outputs=episode_outputs)
    steps = sum(1 for o in episode_outputs if "pep" in o)
    record = {
        "mission_id": MISSION_ID, "policy_id": "d2-canonical", "policy_version": 1,
        "policy_content_hash": "", "terminal_reason": termination.reason,
        "steps_executed": steps, "denials": 0, "hard_violations": [],
        "wall_seconds": 0.0,
        "action_refs": [A_ID, B_ID],
        "decision_refs": [o["broker"]["receipt"].action_id for o in episode_outputs
                          if "broker" in o],
        "objective_requires": [A_ID, B_ID],
    }
    return store, record, termination, broker


def _cand(action_id, action_type, capability, method):
    return {"action_id": action_id, "action_type": action_type, "target": "dvwa",
            "capability": capability, "method": method, "impact_estimate": 2.0,
            "args": {"bounded": True}, "rationale": "rsi1 test"}


def _fake_nmap(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, "Nmap 7.99\n80/tcp open  http\n", ""
    return P()


def _fake_curl(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, "<html>\n302|text/html|7|0.01|http://dvwa/login.php\n", ""
    return P()


def _fake_inspector(container):
    net = "raphael-m1_raphael-net"
    if container == "dvwa":
        return {"State": {"Running": True}, "Config": {"Image": "vulnerables/web-dvwa:x"},
                "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}
    return {"State": {"Running": True}, "Config": {"Image": "raphael/kali-tools:x"},
            "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.3"}}}}


# ── ExperienceNode ───────────────────────────────────────────────────────

def test_experience_node_identity_and_validation():
    node = ExperienceNode(experience_id="exp-1", mission_id="m", episode_id="e1",
                          outcome="objective_met", evidence_refs=("ev1",))
    assert node.content_hash() == node.content_hash()
    with pytest.raises(ExperienceError):
        ExperienceNode(experience_id="exp-1", mission_id="m", episode_id="e1",
                       outcome="nonsense").validate()


def test_objective_met_requires_evidence_refs():
    with pytest.raises(ExperienceError):
        ExperienceNode(experience_id="exp-1", mission_id="m", episode_id="e1",
                       outcome="objective_met").validate()


def test_experience_hash_mismatch_rejected():
    d = ExperienceNode(experience_id="exp-1", mission_id="m", episode_id="e1",
                       outcome="failed").to_dict()
    d["outcome"] = "objective_met"  # mutate content, keep declared hash
    with pytest.raises(ExperienceError):
        ExperienceNode.from_dict(d)


def test_experience_log_idempotent_and_conflict_refusing(tmp_path):
    log = ExperienceLog(tmp_path / "exp.jsonl")
    node = ExperienceNode(experience_id="exp-1", mission_id="m", episode_id="e1",
                          outcome="failed")
    assert log.append(node) == "exp-1"
    assert log.append(node) == "exp-1"          # idempotent duplicate
    conflict = ExperienceNode(experience_id="exp-1", mission_id="m",
                              episode_id="e1", outcome="objective_met",
                              evidence_refs=("ev1",))
    with pytest.raises(ExperienceError):
        log.append(conflict)
    assert len(log.all()) == 1
    log2 = ExperienceLog(tmp_path / "exp.jsonl")
    assert log2.get("exp-1").outcome == "failed"


# ── trusted ingestion ────────────────────────────────────────────────────

def test_ingest_genuine_episode_accepted_with_resolvable_evidence(tmp_path):
    store, record, _, broker = hermetic_episode(tmp_path)
    result = ingest_episode(store, record, episode_id="ep-1",
                            evidence_roots=(tmp_path / "artifacts",),
                            broker_authority=broker)
    assert result.accepted and result.reason == "objective_met"
    node = result.node
    assert node is not None
    node.validate()
    # every evidence ref must resolve to a real persisted evidence record
    assert node.evidence_refs
    for ref in node.evidence_refs:
        assert store.get(ref) is not None
    assert set(node.evidence_refs) == {r.identity for r in store.records()
                                       if r.kind.value == "execution_result"}


def test_ingestion_records_honest_outcome_not_claimed_outcome(tmp_path):
    store, record, _, broker = hermetic_episode(tmp_path)
    result = ingest_episode(store, record, episode_id="ep-1",
                            evidence_roots=(tmp_path / "artifacts",),
                            broker_authority=broker)
    node = result.node
    assert node.outcome == "objective_met"      # derived from verified evidence
    assert set(node.evidence_refs) == {r.identity for r in store.records()
                                       if r.kind.value == "execution_result"}


def test_ingestion_downgrades_fabricated_success(tmp_path):
    """A store holding fabricated ok records (nothing executed) must NOT
    ingest as objective_met — the canonical verifier rejects them."""
    store = EvidenceStore(tmp_path / "store.jsonl")
    for aid in (A_ID, B_ID):
        store.append(EVIDENCE_V1.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=aid,
            status="ok", decision="allow"))  # fabricated: nothing executed
    record = {"mission_id": MISSION_ID, "policy_id": "x", "policy_version": 1,
              "policy_content_hash": "", "terminal_reason": "claimed success",
              "steps_executed": 2, "denials": 0, "hard_violations": [],
              "wall_seconds": 0.0, "action_refs": [A_ID, B_ID],
              "decision_refs": [], "objective_requires": [A_ID, B_ID]}
    result = ingest_episode(store, record, episode_id="ep-fake")
    assert result.accepted, "honest ingestion still records the run"
    node = result.node
    assert node.outcome in ("objective_not_met", "failed"), (
        "a fabricated success must downgrade to an honest outcome")


def test_ingestion_scopes_records_by_mission(tmp_path):
    """Cross-episode records from an unrelated mission cannot satisfy this
    run's objective — the canonical verifier is mission-scoped."""
    store = EvidenceStore(tmp_path / "store.jsonl")
    for aid in (A_ID, B_ID):
        store.append(EVIDENCE_V1.execution_result(
            mission_id="totally-unrelated-run", producer="attacker",
            action_id=aid, status="ok", decision="allow"))
    record = {"mission_id": MISSION_ID, "policy_id": "x", "policy_version": 1,
              "policy_content_hash": "", "terminal_reason": "",
              "steps_executed": 0, "denials": 0, "hard_violations": [],
              "wall_seconds": 0.0, "action_refs": [A_ID, B_ID],
              "decision_refs": [], "objective_requires": [A_ID, B_ID]}
    result = ingest_episode(store, record, episode_id="ep-x")
    assert result.accepted and result.reason != "objective_met"


def test_duplicate_ingestion_is_idempotent(tmp_path):
    store, record, _, broker = hermetic_episode(tmp_path)
    r1 = ingest_episode(store, record, episode_id="ep-1",
                        evidence_roots=(tmp_path / "artifacts",))
    n_before = len(ExperienceLog(tmp_path / "exp.jsonl").all())
    r2 = ingest_episode(store, record, episode_id="ep-1",
                        evidence_roots=(tmp_path / "artifacts",),
                        broker_authority=broker)
    assert r1.experience_id == r2.experience_id
    assert len(ExperienceLog(tmp_path / "exp.jsonl").all()) == n_before


def test_ingestion_preserves_failed_episodes_honestly(tmp_path):
    store = EvidenceStore(tmp_path / "store.jsonl")
    store.append(EVIDENCE_V1.execution_result(
        mission_id=MISSION_ID, producer="runtime.pep", action_id=A_ID,
        status="failed", decision="allow",
        reason="nmap: connection refused (fixture)"))
    record = {"mission_id": MISSION_ID, "policy_id": "x", "policy_version": 1,
              "policy_content_hash": "", "terminal_reason": "PEP raised",
              "steps_executed": 1, "denials": 0, "hard_violations": [],
              "wall_seconds": 0.0, "action_refs": [A_ID],
              "decision_refs": [], "objective_requires": [A_ID, B_ID]}
    result = ingest_episode(store, record, episode_id="ep-f")
    assert result.accepted and result.reason == "failed"
    assert result.node.outcome == "failed"


def test_ingestion_rejects_runs_without_mission_identity():
    result = ingest_episode(store=None, run_record={"objective_requires": [A_ID]},
                            episode_id="e")
    assert not result.accepted and "mission" in result.reason


# ── ImprovementHypothesis ────────────────────────────────────────────────

def test_hypothesis_requires_falsification_condition_and_evidence():
    with pytest.raises(HypothesisError):
        ImprovementHypothesis(hypothesis_id="h1", problem="p", causal_claim="c",
                              evidence_refs=(), permitted_dimensions=("candidate_order",),
                              expected_effect="e", falsification_condition="")
    with pytest.raises(HypothesisError):
        ImprovementHypothesis(hypothesis_id="h1", problem="p", causal_claim="c",
                              evidence_refs=("exp-1",),
                              permitted_dimensions=("capability",),
                              expected_effect="e",
                              falsification_condition="whenever")


def test_hypothesis_hash_and_round_trip():
    h = ImprovementHypothesis(
        hypothesis_id="h-1",
        problem="S2 fault halts the episode at the PEP stage",
        causal_claim="ordering B before A discovers the fault one step earlier",
        evidence_refs=("exp-1",), permitted_dimensions=("candidate_order",),
        expected_effect="verified completion unchanged; steps-to-failure -1",
        falsification_condition="steps-to-failure does not decrease under "
                                "matched conditions")
    d = h.to_dict()
    assert ImprovementHypothesis.from_dict(d).content_hash() == h.content_hash()
    assert h.with_status("under_evaluation").status == "under_evaluation"


def test_falsifiable_verdict_mapping():
    def ev(cvr, bvr, hard=0, excl=0):
        return FalsifiableEvaluation(hypothesis_id="h", experiment_id="e",
                                     criterion="c", hard_violations=hard,
                                     exclusions=excl,
                                     candidate_verified_rate=cvr,
                                     baseline_verified_rate=bvr)
    assert ev(1.0, 1.0).verdict() == "rejected"  # tie: no improvement
    assert ev(0.9, 0.5).verdict() == "supported"
    assert ev(0.9, 0.5, hard=1).verdict() == "rejected"   # never compensable
    assert ev(0.2, 0.5, excl=3).verdict() == "inconclusive"  # exclusions dominate


# ── ExplorationPolicy lifecycle ──────────────────────────────────────────

def test_policy_lifecycle_and_v0_identity_preserved():
    manifest = json.loads((Path(__file__).resolve().parent.parent
                           / "evidence" / "rsi0" / "20261006T194851Z"
                           / "manifest.json").read_text())
    c0_hash = manifest["candidates"]["rsi0-c0-canonical"]["content_hash"]
    p = ExplorationPolicy(
        policy_id="rsi0-c0-canonical", version=1, status="experimental",
        created_by="rsi0-eval", motivation="incumbent deterministic order",
        parameters={"order": ["A", "B"], "retry": {"action": "A", "at_most": 0}})
    assert p.content_hash() == c0_hash, "v0 policy identity must be preserved"
    evolved = ExplorationPolicy(**{**p.canonical_dict(), "status": "evaluated",
                                   "experiment_id": "rsi0-20261006T194851Z",
                                   "hypothesis_id": "h-order",
                                   "parent_policy_hash": p.content_hash()})
    evolved.validate()
    assert evolved.status == "evaluated"
    from orchestrator.rsi.exploration_policy import ExplorationPolicyError
    with pytest.raises(ExplorationPolicyError):
        ExplorationPolicy(**{**p.canonical_dict(), "status": "active"}).validate()


# ── experiment snapshot + read-only replay ──────────────────────────────

def test_snapshot_and_replay_derive_from_persisted_stores(tmp_path):
    store, record, _, broker = hermetic_episode(tmp_path)
    manifest = {"run_id": "rsi1-test",
                "candidates": {"d2-canonical": {"content_hash": "x"}},
                "scenarios": {"S1": "nominal"}}
    snap = rsi_snapshot.ExperimentSnapshot.from_manifest(manifest, tmp_path)
    replay = rsi_snapshot.verify_snapshot(snap, tmp_path, broker_authority=broker)
    assert replay["replay_only"] is True
    run = replay["runs"][0]
    assert sorted(run["verified_actions"]) == sorted([A_ID, B_ID])
    assert run["unverified_actions"] == []
    assert snap.content_hash() == rsi_snapshot.ExperimentSnapshot.from_dict(
        snap.to_dict()).content_hash()


def test_snapshot_replay_flags_fabricated_records(tmp_path):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    for aid in (A_ID, B_ID):
        store.append(EVIDENCE_V1.execution_result(
            mission_id=MISSION_ID, producer="runtime.receipt", action_id=aid,
            status="ok", decision="allow"))  # fabricated: nothing executed
    manifest = {"run_id": "rsi1-fake", "candidates": {"c": {"content_hash": "x"}},
                "scenarios": {"S": "s"}}
    snap = rsi_snapshot.ExperimentSnapshot.from_manifest(manifest, tmp_path)
    replay = rsi_snapshot.verify_snapshot(snap, tmp_path)
    run = replay["runs"][0]
    assert run["unverified_actions"], "fabricated records must not verify"
    assert not run["verified_actions"]


# ── GRPO-mechanics prototype ────────────────────────────────────────────

def test_grpo_prototype_learns_on_the_toy_task(monkeypatch):
    monkeypatch.setattr(grpo_proto, "EPISODES", 80)
    tmp = Path(tempfile.mkdtemp())
    res = grpo_proto.run_prototype(tmp)
    assert res["trained_greedy_mean_reward"] > res["initial_greedy_mean_reward"]
    assert (tmp / "grpo_prototype_result.json").is_file()
    assert any("not language-model training" in label.lower()
               for label in res["honesty_labels"])
