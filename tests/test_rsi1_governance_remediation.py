"""test_rsi1_governance_remediation.py — RSI-1 governance remediation (2026-10-07).

Fix A — authoritative execution provenance. The objective evaluator resolves
every claimed ``decision_id`` against the authoritative Broker receipt store of
the Runtime's own Broker. Producer labels, decision strings, well-formed
digests, and internal consistency of the evidence ledger are never sufficient.
Missing authority fails closed.

Fix B — non-bypassable D2 five-step maximum. The ceiling is a property of the
approved D2 engagement, recognised STRUCTURALLY (canonical engagement id, the
canonical capability/action vocabulary, the validated lab contract), so neither
a renamed policy artifact nor a hand-constructed ``BrokerPolicy`` with a
zero/six/64/missing cap can escape it. The ceiling is consumed inside the PEP
stage, so the bound is on governed steps that actually reach the capability
boundary — not on loop bookkeeping and not on the rate limiter.

Hermetic: every store, artifact, and policy copy lives under ``tmp_path``;
injected runners and inspectors mean no docker, no subprocess, no network.
Historical evidence is untouched.
"""
import hashlib
import json
from pathlib import Path

import pytest

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
from orchestrator.exec.evidence_store import EvidenceStore
from orchestrator.rsi import snapshot as rsi_snapshot
from orchestrator.rsi.experience import ExperienceLog, ingest_episode
from orchestrator.rsi.hypothesis import FalsifiableEvaluation
from orchestrator.rsi.snapshot import ExperimentSnapshot
from orchestrator.runtime import stages as stages_mod
from orchestrator.runtime.evidence_v1 import EvidenceRecord
from orchestrator.runtime.loop import RaphaelRuntime
from orchestrator.runtime.organs import OrganBundle
from orchestrator.runtime.policy import (
    D2_POLICY_PATH,
    D1Policy,
    PolicyLoadError,
    make_broker_from_bootstrap,
    make_broker_from_policy,
)
from orchestrator.runtime.scope import ScopeV0
from orchestrator.runtime.stages import STAGE_HANDLERS
from orchestrator.runtime.types import MissionContext, RuntimeContext

MISSION = "d2-bounded-episode"
A_ID = "ACT-D2-PROBE-0001"
B_ID = "ACT-D2-HTTP-0002"
CAP_A = "exec.d1_lab_probe"
CAP_B = "exec.http_probe"
EVIDENCE_V1 = EvidenceRecord

FAKE_NMAP = ("Starting Nmap 7.99\nNmap scan report for dvwa (172.19.0.4)\n"
             "PORT   STATE SERVICE\n80/tcp open  http\n")
# DVWA answers the fixed in-container GET with 302 and is NOT followed: a
# governed request that really executed must still produce valid evidence.
FAKE_CURL = ("<html>login redirect</html>\n302|text/html|28|0.01|http://dvwa/login.php\n")


def _runner_a(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_NMAP, ""
    return P()


def _runner_b(argv, timeout):
    class P:
        returncode, stdout, stderr = 0, FAKE_CURL, ""
    return P()


def _inspector(container):
    net = "raphael-m1_raphael-net"
    images = {"dvwa": "vulnerables/web-dvwa:stable",
              "kali-tools": "raphael/kali-tools:latest"}
    if container not in images:
        raise AssertionError(f"unexpected container {container}")
    return {"State": {"Running": True},
            "Config": {"Image": images[container]},
            "NetworkSettings": {"Networks": {net: {"IPAddress": "172.19.0.4"}}}}


def _cand(action_id, action_type, capability, method):
    return {"action_id": action_id, "action_type": action_type, "target": "dvwa",
            "capability": capability, "method": method, "impact_estimate": 2.0,
            "args": {"bounded": True}, "rationale": "remediation test"}


def _d2_scope():
    return ScopeV0(mission_id=MISSION, targets=("dvwa",),
                   allowed_action_types=("recon_service_probe", "lab_http_probe"),
                   allowed_capabilities=(CAP_A, CAP_B), max_impact=2.0)


def build_runtime(tmp_path, broker, runner_map=None, store=None):
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    if store is None:
        store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    cap_a = D1LabProbeCapability(
        broker=broker, artifacts_dir=tmp_path / "artifacts",
        runner=(runner_map or {}).get(CAP_A, _runner_a), inspector=_inspector)
    cap_b = LabHttpProbeCapability(
        broker=broker, artifacts_dir=tmp_path / "artifacts",
        runner=(runner_map or {}).get(CAP_B, _runner_b), inspector=_inspector)
    runtime = RaphaelRuntime(broker=broker, capability=cap_a,
                             organs=OrganBundle(evidence_store=store),
                             capability_registry={CAP_A: cap_a, CAP_B: cap_b})
    return runtime, store, {CAP_A: cap_a, CAP_B: cap_b}


# Retained under its historical name for readability at the call sites.
def SV_build_runtime(broker, tmp_path, runner_map=None):
    runtime, _store, caps = build_runtime(tmp_path, broker, runner_map)
    return runtime, caps


def d2_mission(candidates_by_iter, required, max_iterations=5):
    return MissionContext(
        mission_id=MISSION, name="D2 bounded episode", objectives=["governed probe"],
        scope=_d2_scope(),
        constraints={"halt": {"max_iterations": max_iterations, "action_cap": 1,
                              "require_scope": True},
                     "candidates": candidates_by_iter, "default_target": "dvwa",
                     "objective": {"requires_evidence": list(required)}})


def hermetic_episode(tmp_path, runner_map=None):
    """Run the genuine approved two-action D2 episode.

    Returns ``(store, broker, termination, caps)`` so a test can verify outcomes
    against the SAME authoritative receipt store the episode actually used — the
    only authority Fix A recognises.
    """
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, store, caps = build_runtime(tmp_path, broker, runner_map)
    mission = d2_mission({"0": [_cand(A_ID, "recon_service_probe", CAP_A, "nmap")],
                          "1": [_cand(B_ID, "lab_http_probe", CAP_B, "curl")]},
                         required=[A_ID, B_ID])
    _traces, termination = runtime.run_episode(mission)
    return store, broker, termination, caps


def evaluate(store, required=(A_ID, B_ID), broker_authority=None, roots=None,
             mission=MISSION):
    ctx = {"view": {"mission_id": mission,
                    "objective": {"requires_evidence": list(required)}},
           "evidence_store": store, "organs": None,
           "capability_registry": {CAP_A: None, CAP_B: None},
           "capability": None, "broker_authority": broker_authority,
           "artifact_roots": roots or ()}
    return STAGE_HANDLERS["replan"](ctx).output


def _rows(store):
    return [{**{"kind": r.kind.value}, **dict(r.payload)} for r in store.records()]


def _append_forged_chain(store, root, action_ids, digest, decision_ids, relpath,
                         mission=MISSION, size=None):
    """Fabricate an internally consistent execution+artifact chain."""
    payload = b"0123456789"
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "artifacts" / Path(relpath).name).write_bytes(payload)
    for aid, did in zip(action_ids, decision_ids):
        exec_rec = EVIDENCE_V1.execution_result(
            mission_id=mission, producer="runtime.receipt", action_id=aid,
            status="ok", decision="allow", stdout="fabricated",
            artifacts=(relpath,), decision_id=did)
        store.append(exec_rec)
        store.append(EVIDENCE_V1.artifact(
            mission_id=mission, producer="runtime.receipt", relpath=relpath,
            size_bytes=len(payload) if size is None else size,
            sha256=digest, execution_ref=exec_rec.identity,
            parents=(exec_rec.identity,)))
    return digest


def genuine_attempt(broker, mission_action_id, mission=MISSION,
                    action_type="recon_service_probe", capability=CAP_A,
                    target="dvwa", success=True):
    """Drive the Broker through a real authorize->start->complete lifecycle.

    Returns the genuine ``decision_id`` for that attempt. This is how a test
    reaches the artifact/digest layers with authentic provenance.
    """
    receipt = broker.propose_action(
        target=target, action_type=action_type, capability=capability,
        method="nmap" if capability == CAP_A else "curl", impact_estimate=2.0,
        metadata={"mission_id": mission, "mission_action_id": mission_action_id})
    assert receipt is not None
    started = broker.start_execution(receipt)
    assert started is not None
    done = broker.complete_execution(started, success=success, result="executed")
    assert done is not None
    return receipt.action_id


# ══════════════════════════════════════════════════════════════════════════
# A1 — producer spoofing
# ══════════════════════════════════════════════════════════════════════════

def test_a1_producer_spoofing_rejected(tmp_path):
    """Fabricated runtime.receipt rows with real digests never satisfy the objective."""
    store = EvidenceStore(tmp_path / "store.jsonl")
    digest = _append_forged_chain(
        store, tmp_path, (A_ID, B_ID),
        hashlib.sha256(b"0123456789").hexdigest(),
        ("DEC-FABRICATED-0001", "DEC-FABRICATED-0002"), "artifacts/x.txt")
    out = evaluate(store)  # NO broker authority at all
    assert out.get("objective_met") is not True
    assert "no authoritative broker state" in out["reason"]
    # Same forgery WITH a broker authority that never saw those attempts.
    broker = make_broker_from_policy(D2_POLICY_PATH)
    out2 = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out2.get("objective_met") is not True


def test_a1b_forgery_fabricates_no_execution(tmp_path, monkeypatch):
    """Instrument the capability boundary: fake evidence executes nothing."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _store, caps = build_runtime(tmp_path, broker)
    reached = []
    for cap in caps.values():
        original = cap.inspect
        monkeypatch.setattr(cap, "inspect",
                            lambda t, _c=cap, _o=original: (reached.append(_c), _o(t))[1])

    forged_store = EvidenceStore(tmp_path / "forged.jsonl")
    _append_forged_chain(
        forged_store, tmp_path, (A_ID, B_ID),
        hashlib.sha256(b"0123456789").hexdigest(),
        ("DEC-FABRICATED-0001", "DEC-FABRICATED-0002"), "artifacts/x.txt")
    out = evaluate(forged_store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert reached == [], "no capability may be invoked by forged evidence"
    assert all(c.invocation_count == 0 for c in caps.values())


# ══════════════════════════════════════════════════════════════════════════
# A2 — nonexistent decision
# ══════════════════════════════════════════════════════════════════════════

def test_a2_nonexistent_decision_rejected(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID, B_ID),
                         hashlib.sha256(b"0123456789").hexdigest(),
                         ("DEC-NEVER-EXISTED-1", "DEC-NEVER-EXISTED-2"),
                         "artifacts/x.txt")
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "decision-linked record" in out["reason"]


# ══════════════════════════════════════════════════════════════════════════
# A3 — mismatched genuine decision
# ══════════════════════════════════════════════════════════════════════════

def test_a3a_decision_from_another_broker_instance_rejected(tmp_path):
    other = make_broker_from_policy(D2_POLICY_PATH)
    foreign = genuine_attempt(other, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID, B_ID),
                         hashlib.sha256(b"0123456789").hexdigest(), (foreign, "DEC-B"),
                         "artifacts/x.txt")
    broker = make_broker_from_policy(D2_POLICY_PATH)  # a DIFFERENT instance
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


def test_a3b_genuine_decision_bound_to_another_mission_rejected(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    foreign = genuine_attempt(broker, A_ID, mission="some-other-mission")
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID,), 
                         hashlib.sha256(b"0123456789").hexdigest(), (foreign,),
                         "artifacts/x.txt")
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


def test_a3c_genuine_decision_bound_to_another_action_cannot_be_borrowed(tmp_path):
    """A real SUCCEEDED attempt for B_ID may not satisfy A_ID's requirement."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    other_action_attempt = genuine_attempt(
        broker, B_ID, action_type="lab_http_probe", capability=CAP_B)
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID,),
                         hashlib.sha256(b"0123456789").hexdigest(),
                         (other_action_attempt,), "artifacts/x.txt")
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


def test_a3d_decision_for_a_prohibited_target_rejected(tmp_path):
    """A receipt whose recorded target is outside the policy never qualifies."""
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="x", policy_name="x", allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe"],
        allowed_capabilities=[CAP_A], max_impact_per_action=2.0))
    attempt = genuine_attempt(broker, A_ID, target="dvwa")
    assert broker.authoritative_success_receipt(attempt, MISSION, A_ID) is not None
    # An inconsistent stored receipt (recorded target outside the policy) is
    # refused on the target dimension, whatever its status and metadata say.
    broker.receipt_store[attempt].target = "not-an-allowed-target"
    assert broker.authoritative_success_receipt(attempt, MISSION, A_ID) is None


def test_a3e_refused_terminal_transition_does_not_crash_the_lifecycle(tmp_path):
    """A DENIED receipt cannot be completed; the broker refuses cleanly."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    denied = broker.propose_action(
        target="dvwa", action_type="exploit_execute", capability=CAP_A,
        method="nmap", impact_estimate=2.0,
        metadata={"mission_id": MISSION, "mission_action_id": A_ID})
    assert denied.status.name == "DENIED"
    assert broker.start_execution(denied) is None
    assert broker.complete_execution(denied, success=True, result="x") is None
    assert broker.authoritative_success_receipt(
        denied.action_id, MISSION, A_ID) is None


# ══════════════════════════════════════════════════════════════════════════
# A4 — fabricated complete chain
# ══════════════════════════════════════════════════════════════════════════

def test_a4_fabricated_complete_chain_rejected(tmp_path):
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID, B_ID),
                         hashlib.sha256(b"0123456789").hexdigest(),
                         tuple(f"DEC-FAB-{a}" for a in (A_ID, B_ID)), "artifacts/x.txt")
    broker = make_broker_from_policy(D2_POLICY_PATH)
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


# ══════════════════════════════════════════════════════════════════════════
# A5 — positive control
# ══════════════════════════════════════════════════════════════════════════

def test_a5_genuine_episode_still_verifies(tmp_path):
    store, broker, termination, caps = hermetic_episode(tmp_path)
    assert "objective met" in termination.reason, termination.reason
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is True, out
    # Exactly the two approved governed actions executed; nothing more.
    assert caps[CAP_A].invocation_count == 1
    assert caps[CAP_B].invocation_count == 1


def test_a5b_genuine_302_evidence_is_valid_without_following_the_redirect(tmp_path):
    """A real governed request that returns 302 and does not follow it verifies."""
    store, broker, termination, _caps = hermetic_episode(tmp_path)
    assert "objective met" in termination.reason
    http_row = [r for r in _rows(store)
                if r.get("action_id") == B_ID and r.get("kind") == "execution_result"]
    assert http_row, "the HTTP attempt must be recorded"
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out["objective_met"] is True


def test_a5c_transport_failure_is_not_a_successful_response(tmp_path):
    """A curl transport failure yields FAILED, never a successful outcome."""
    def failing(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect"
        return P()

    store, broker, termination, _caps = hermetic_episode(
        tmp_path, runner_map={CAP_B: failing})
    assert "objective met" not in termination.reason
    rows = _rows(store)
    assert any(r.get("status") == "failed" for r in rows)
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert B_ID in out["reason"]


# ══════════════════════════════════════════════════════════════════════════
# A6 — attempt isolation
# ══════════════════════════════════════════════════════════════════════════

def test_a6_success_counts_only_through_its_own_attempt(tmp_path):
    """A later successful attempt verifies; the earlier failure never counts.

    Two episodes against the SAME authoritative broker and evidence store. The
    first HTTP attempt fails; a later attempt of the same mission action
    succeeds. Each attempt carries its own broker-minted decision id, only the
    successful one resolves as an authoritative success, and the failed attempt
    is never borrowed to satisfy the objective.
    """
    def failing(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) connection refused"
        return P()

    broker = _manual_d2_broker(5)   # no rate limiter: isolate the semantics
    assert broker.rate_limiter is None
    shared_store = EvidenceStore(tmp_path / "evidence_store.jsonl")

    # Episode 1: the HTTP attempt fails.
    runtime1, store, caps = build_runtime(tmp_path, broker,
                                         runner_map={CAP_B: failing},
                                         store=shared_store)
    _traces, term1 = runtime1.run_episode(d2_mission(
        {"0": [_cand(A_ID, "recon_service_probe", CAP_A, "nmap")],
         "1": [_cand(B_ID, "lab_http_probe", CAP_B, "curl")]},
        required=[A_ID, B_ID]))
    assert "objective met" not in term1.reason
    assert caps[CAP_B].invocation_count == 1

    # Episode 2: the same mission action id is attempted again and succeeds.
    runtime2, store2, caps2 = build_runtime(tmp_path, broker, store=shared_store)
    _traces, term2 = runtime2.run_episode(d2_mission(
        {"0": [_cand(A_ID, "recon_service_probe", CAP_A, "nmap")],
         "1": [_cand(B_ID, "lab_http_probe", CAP_B, "curl")]},
        required=[A_ID, B_ID]))
    assert "objective met" in term2.reason, term2.reason

    rows = [r for r in _rows(store)
            if r.get("kind") == "execution_result" and r.get("action_id") == B_ID]
    failed = [r for r in rows if r.get("status") == "failed"]
    ok = [r for r in rows if r.get("status") == "ok"]
    assert failed, "the first HTTP attempt must be recorded as a failure"
    assert ok, "the second HTTP attempt must be recorded as a success"
    # The FAILED row carries no decision-linked success claim at all.
    assert not failed[0].get("decision_id")
    # Each attempt has its own identity, and only the successful one resolves.
    assert broker.authoritative_success_receipt(
        ok[0]["decision_id"], MISSION, B_ID) is not None


def test_a6b_failure_terminates_the_episode_without_fabricating_success(tmp_path):
    """No in-episode retry is invented, and a failure is never a success."""
    def failing(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) connection refused"
        return P()

    broker = _manual_d2_broker(5)
    runtime, store, caps = build_runtime(tmp_path, broker,
                                         runner_map={CAP_B: failing})
    _traces, term = runtime.run_episode(d2_mission(
        {"0": [_cand(A_ID, "recon_service_probe", CAP_A, "nmap")],
         "1": [_cand(B_ID, "lab_http_probe", CAP_B, "curl")],
         "2": [_cand(B_ID, "lab_http_probe", CAP_B, "curl")]},
        required=[A_ID, B_ID]))
    assert "objective met" not in term.reason
    assert term.final_stage == "pep"
    assert caps[CAP_B].invocation_count == 1, "no retry was invented"
    out = evaluate(store, broker_authority=broker, roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


def test_a6b_conflicting_outcomes_for_one_attempt_are_rejected(tmp_path):
    """Two contradicting rows sharing one decision_id make the attempt ambiguous."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = genuine_attempt(broker, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    digest = hashlib.sha256(b"bytes").hexdigest()
    exec_rec = EVIDENCE_V1.execution_result(
        mission_id=MISSION, producer="runtime.receipt", action_id=A_ID,
        status="ok", decision="allow", artifacts=("artifacts/z.txt",),
        decision_id=attempt)
    store.append(exec_rec)
    store.append(EVIDENCE_V1.execution_result(
        mission_id=MISSION, producer="runtime.pep", action_id=A_ID,
        status="failed", decision="allow", artifacts=(), decision_id=attempt))
    store.append(EVIDENCE_V1.artifact(
        mission_id=MISSION, producer="runtime.receipt", relpath="artifacts/z.txt",
        size_bytes=5, sha256=digest, execution_ref=exec_rec.identity,
        parents=(exec_rec.identity,)))
    (tmp_path / "artifacts").mkdir(exist_ok=True)
    (tmp_path / "artifacts" / "z.txt").write_bytes(b"bytes")
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "contradictory records" in out["reason"]


# ══════════════════════════════════════════════════════════════════════════
# A7 — denial / failure / authorization-only
# ══════════════════════════════════════════════════════════════════════════

def test_a7_authorization_only_never_satisfies(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = broker.propose_action(
        target="dvwa", action_type="recon_service_probe", capability=CAP_A,
        method="nmap", impact_estimate=2.0,
        metadata={"mission_id": MISSION, "mission_action_id": A_ID})
    assert "AUTHORIZED" in str(receipt_status := attempt.status)
    assert receipt_status.name == "AUTHORIZED"
    store = EvidenceStore(tmp_path / "store.jsonl")
    out = evaluate(store, required=(A_ID,), broker_authority=broker)
    assert out.get("objective_met") is not True


def test_a7b_denied_attempt_never_satisfies(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    denied = broker.propose_action(
        target="dvwa", action_type="exploit_execute", capability=CAP_A,
        method="nmap", impact_estimate=2.0,
        metadata={"mission_id": MISSION, "mission_action_id": A_ID})
    assert denied.status.name == "DENIED"
    store = EvidenceStore(tmp_path / "store.jsonl")
    store.append(EVIDENCE_V1.execution_result(
        mission_id=MISSION, producer="runtime.broker", action_id=A_ID,
        status="denied", decision="deny", decision_id=denied.action_id))
    out = evaluate(store, required=(A_ID,), broker_authority=broker)
    assert out.get("objective_met") is not True


def test_a7c_failed_attempt_never_satisfies(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    failed = genuine_attempt(broker, A_ID, success=False)
    store = EvidenceStore(tmp_path / "store.jsonl")
    _append_forged_chain(store, tmp_path, (A_ID,),
                         hashlib.sha256(b"0123456789").hexdigest(), (failed,),
                         "artifacts/x.txt")
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True


# ══════════════════════════════════════════════════════════════════════════
# A8 — trusted ingestion
# ══════════════════════════════════════════════════════════════════════════

def test_a8_ingestion_rejects_fabricated_evidence(tmp_path):
    store = EvidenceStore(tmp_path / "store.jsonl")
    for aid in (A_ID, B_ID):
        store.append(EVIDENCE_V1.execution_result(
            mission_id=MISSION, producer="runtime.receipt", action_id=aid,
            status="ok", decision="allow", decision_id=f"DEC-FAKE-{aid}"))
    record = {"mission_id": MISSION, "policy_id": "x", "policy_version": 1,
              "policy_content_hash": "", "terminal_reason": "claimed",
              "steps_executed": 2, "denials": 0, "hard_violations": [],
              "wall_seconds": 0.0, "action_refs": [A_ID, B_ID],
              "decision_refs": [], "objective_requires": [A_ID, B_ID]}
    broker = make_broker_from_policy(D2_POLICY_PATH)
    result = ingest_episode(store, record, episode_id="ep-fake",
                            evidence_roots=(tmp_path,), broker_authority=broker)
    assert result.accepted, "the run is still recorded"
    assert result.reason != "objective_met", "fabricated success must downgrade"


def test_a8b_ingestion_genuine_with_authority(tmp_path):
    store, broker, _term, _caps = hermetic_episode(tmp_path)
    record = {"mission_id": MISSION, "policy_id": "engagement-d2-v1",
              "policy_version": 1, "policy_content_hash": "x",
              "terminal_reason": "objective met", "steps_executed": 2, "denials": 0,
              "hard_violations": [], "wall_seconds": 1.0,
              "action_refs": [A_ID, B_ID], "decision_refs": [],
              "objective_requires": [A_ID, B_ID]}
    result = ingest_episode(store, record, episode_id="ep-genuine",
                            evidence_roots=(tmp_path / "artifacts",),
                            broker_authority=broker)
    assert result.accepted and result.reason == "objective_met", result


def test_a8c_ingestion_without_authority_fails_closed(tmp_path):
    store = EvidenceStore(tmp_path / "store.jsonl")
    record = {"mission_id": MISSION, "policy_id": "x", "policy_version": 1,
              "policy_content_hash": "", "terminal_reason": "objective met",
              "steps_executed": 2, "denials": 0, "hard_violations": [],
              "wall_seconds": 0.0, "action_refs": [A_ID, B_ID],
              "decision_refs": [], "objective_requires": [A_ID, B_ID]}
    result = ingest_episode(store, record, episode_id="ep-noauth",
                            evidence_roots=(tmp_path,))
    assert result.accepted
    assert result.reason != "objective_met"


# ══════════════════════════════════════════════════════════════════════════
# A9 — replay
# ══════════════════════════════════════════════════════════════════════════

def test_a9_replay_cannot_upgrade_forged_records(tmp_path):
    store = EvidenceStore(tmp_path / "evidence_store.jsonl")
    for aid in (A_ID, B_ID):
        store.append(EVIDENCE_V1.execution_result(
            mission_id=MISSION, producer="runtime.receipt", action_id=aid,
            status="ok", decision="allow", decision_id=f"DEC-FAKE-{aid}"))
    manifest = {"run_id": "forged", "candidates": {"c": {"content_hash": "x"}},
                "scenarios": {"S": "s"}}
    snap = ExperimentSnapshot.from_manifest(manifest, tmp_path)
    broker = make_broker_from_policy(D2_POLICY_PATH)
    replay = rsi_snapshot.verify_snapshot(snap, tmp_path, broker_authority=broker)
    assert replay["replay_only"] is True
    run = replay["runs"][0]
    assert run["unverified_actions"], "forged records must not verify in replay"
    assert not run["verified_actions"]


def test_a9b_replay_of_a_genuine_run_still_verifies(tmp_path):
    store, broker, _term, _caps = hermetic_episode(tmp_path)
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    manifest = {"run_id": "genuine", "candidates": {"c": {"content_hash": "x"}},
                "scenarios": {"S": "s"}}
    snap = ExperimentSnapshot.from_manifest(manifest, tmp_path)
    replay = rsi_snapshot.verify_snapshot(snap, tmp_path, broker_authority=broker)
    run = replay["runs"][0]
    assert sorted(run["verified_actions"]) == sorted([A_ID, B_ID]), replay


# ══════════════════════════════════════════════════════════════════════════
# A10 — artifact integrity (reached with GENUINE provenance)
# ══════════════════════════════════════════════════════════════════════════

def _genuine_recorded_chain(tmp_path, store, attempt, action_id, relpath,
                            digest, size):
    """Record an execution+artifact pair bound to a genuine successful attempt."""
    exec_rec = EVIDENCE_V1.execution_result(
        mission_id=MISSION, producer="runtime.receipt", action_id=action_id,
        status="ok", decision="allow", artifacts=(relpath,), decision_id=attempt)
    store.append(exec_rec)
    store.append(EVIDENCE_V1.artifact(
        mission_id=MISSION, producer="runtime.receipt", relpath=relpath,
        size_bytes=size, sha256=digest, execution_ref=exec_rec.identity,
        parents=(exec_rec.identity,)))
    return exec_rec


def test_a10a_digest_invalid_is_rejected(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = genuine_attempt(broker, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "x.txt").write_bytes(b"genuine bytes")
    _genuine_recorded_chain(tmp_path, store, attempt, A_ID, "artifacts/x.txt",
                            "0" * 64, len(b"genuine bytes"))
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "digest mismatch" in out["reason"]


def test_a10b_size_invalid_is_rejected(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = genuine_attempt(broker, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "x.txt").write_bytes(b"genuine bytes")
    _genuine_recorded_chain(tmp_path, store, attempt, A_ID, "artifacts/x.txt",
                            hashlib.sha256(b"genuine bytes").hexdigest(), 999999)
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "size mismatch" in out["reason"]


def test_a10c_dangling_reference_is_rejected(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = genuine_attempt(broker, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    _genuine_recorded_chain(tmp_path, store, attempt, A_ID, "artifacts/never.txt",
                            "0" * 64, 1)
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "does not resolve" in out["reason"]


def test_a10d_path_escaping_reference_is_rejected(tmp_path):
    """The evidence ledger and the verifier both refuse an escaping relpath."""
    from orchestrator.exec.artifact_verify import (ArtifactVerificationError,
                                                  resolve_artifact_path)
    from orchestrator.runtime.evidence_v1 import EvidenceError
    root = tmp_path / "artifacts"
    root.mkdir(parents=True)
    (tmp_path / "outside.txt").write_bytes(b"secret")
    for ref in ("../outside.txt", "/etc/passwd", "artifacts/../../outside.txt"):
        with pytest.raises(ArtifactVerificationError):
            resolve_artifact_path(root, ref)
    # Defence at the ledger layer: an escaping ref is not even recordable.
    for ref in ("../outside.txt", "/etc/passwd"):
        with pytest.raises(EvidenceError):
            EVIDENCE_V1.execution_result(
                mission_id=MISSION, producer="runtime.receipt", action_id=A_ID,
                status="ok", decision="allow", artifacts=(ref,),
                decision_id="DEC-X")


def test_a10e_borrowed_artifact_from_another_attempt_is_rejected(tmp_path):
    """An artifact record owned by another attempt cannot satisfy this one."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    good = genuine_attempt(broker, A_ID)
    other = genuine_attempt(broker, B_ID, action_type="lab_http_probe",
                            capability=CAP_B)
    store = EvidenceStore(tmp_path / "store.jsonl")
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "shared.txt").write_bytes(b"shared bytes")
    digest = hashlib.sha256(b"shared bytes").hexdigest()
    # B's attempt owns the only artifact record for this ref...
    _genuine_recorded_chain(tmp_path, store, other, B_ID, "artifacts/shared.txt",
                            digest, 12)
    # ...A's execution record CLAIMS the same ref but links to nothing of its own.
    exec_rec = EVIDENCE_V1.execution_result(
        mission_id=MISSION, producer="runtime.receipt", action_id=A_ID,
        status="ok", decision="allow", artifacts=("artifacts/shared.txt",),
        decision_id=good)
    store.append(exec_rec)
    # A must not borrow B's artifact record.
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is not True
    assert "no linked artifact record" in out["reason"]
    # Control: B, whose own record owns it, does verify.
    out_b = evaluate(store, required=(B_ID,), broker_authority=broker,
                     roots=(tmp_path / "artifacts",))
    assert out_b.get("objective_met") is True, out_b


def test_a10f_oversized_artifact_is_rejected(tmp_path):
    from orchestrator.exec.artifact_verify import (ArtifactVerificationError,
                                                  verify_artifact)
    root = tmp_path / "artifacts"
    root.mkdir(parents=True)
    (root / "big.bin").write_bytes(b"A" * 200000)
    with pytest.raises(ArtifactVerificationError):
        verify_artifact(root, "big.bin")


def test_a10g_correct_genuine_chain_verifies(tmp_path):
    """The positive control for A10: real bytes + real attempt verifies."""
    broker = make_broker_from_policy(D2_POLICY_PATH)
    attempt = genuine_attempt(broker, A_ID)
    store = EvidenceStore(tmp_path / "store.jsonl")
    (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "artifacts" / "x.txt").write_bytes(b"genuine bytes")
    _genuine_recorded_chain(tmp_path, store, attempt, A_ID, "artifacts/x.txt",
                            hashlib.sha256(b"genuine bytes").hexdigest(),
                            len(b"genuine bytes"))
    out = evaluate(store, required=(A_ID,), broker_authority=broker,
                   roots=(tmp_path / "artifacts",))
    assert out.get("objective_met") is True, out


# ══════════════════════════════════════════════════════════════════════════
# B — non-bypassable D2 five-step maximum
# ══════════════════════════════════════════════════════════════════════════

def _budget_mission(max_it, action_type="recon_service_probe", capability=CAP_A,
                    method="nmap", scope=None):
    cons = {"halt": {"max_iterations": max_it, "action_cap": 1, "require_scope": True},
            "candidates": {str(i): [_cand(f"ACT-R{i}", action_type, capability, method)]
                           for i in range(max_it)},
            "default_target": "dvwa",
            "objective": {"requires_evidence": [f"ACT-NEVER-{i}" for i in range(max_it)]}}
    return MissionContext(
        mission_id=MISSION, name="budget", objectives=["x"],
        scope=scope if scope is not None else ScopeV0(
            mission_id=MISSION, targets=("dvwa",),
            allowed_action_types=(action_type,), allowed_capabilities=(capability,),
            max_impact=2.0),
        constraints=cons)


def _governed(broker, tmp_path, mission, runner_map=None):
    runtime, _store, caps = build_runtime(tmp_path, broker, runner_map)
    outs = []
    _traces, term = runtime.run_episode(mission, episode_outputs=outs)
    return sum(c.invocation_count for c in caps.values()), term, caps


def _policy_copy(tmp_path, name="copy.json", **overrides):
    data = json.loads(D2_POLICY_PATH.read_text())
    data.update(overrides)
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


def _manual_d2_broker(cap, *, engagement_id="d2-bounded-episode",
                      policy_name="engagement-d2-v1"):
    """BrokerPolicy built in Python — no loader, so the loader cannot help."""
    return CapabilityBroker(BrokerPolicy(
        engagement_id=engagement_id, policy_name=policy_name,
        allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe", "lab_http_probe"],
        allowed_capabilities=["exec.d1_lab_probe", "exec.http_probe"],
        max_impact_per_action=2.0, max_episode_steps=cap))


# ── B1 ─────────────────────────────────────────────────────────────────────

def test_b1_normal_policy_caller_budget_seven(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    execs, term, _caps = _governed(broker, tmp_path, _budget_mission(7))
    assert execs <= 5, execs
    assert execs == 5, "the budget must actually be spent, not merely not exceeded"
    assert term.budget_clamped is True
    assert term.effective_budget == 5
    assert term.requested_budget == 7


# ── B2/B3/B4 — tampered policy artifacts ───────────────────────────────────

@pytest.mark.parametrize("cap", [6, 64, 1, 4])
def test_b2_modified_cap_copy_is_rejected(tmp_path, cap):
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(_policy_copy(tmp_path, f"cap{cap}.json",
                                             max_episode_steps=cap))


@pytest.mark.parametrize("cap", [None, 0, -1, "5", 5.0, True, "x"])
def test_b3_missing_null_or_invalid_cap_fails_closed(tmp_path, cap):
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(_policy_copy(tmp_path, "badcap.json",
                                             max_episode_steps=cap))


def test_b3b_cap_removed_entirely_is_rejected(tmp_path):
    data = json.loads(D2_POLICY_PATH.read_text())
    data.pop("max_episode_steps")
    path = tmp_path / "nocap.json"
    path.write_text(json.dumps(data))
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(path)


@pytest.mark.parametrize("new_name", ["totally-innocent", "policy", "d2-rogue",
                                      "engagement-d2-tampered-renamed"])
def test_b4_renaming_the_artifact_does_not_escape_the_loader(tmp_path, new_name):
    """Recognition is structural: a rename is not an escape from the loader."""
    with pytest.raises(PolicyLoadError):
        make_broker_from_policy(_policy_copy(tmp_path, "renamed.json",
                                             policy_name=new_name,
                                             max_episode_steps=64))


@pytest.mark.parametrize("new_name", ["totally-innocent", "policy"])
def test_b4b_renamed_but_faithful_copy_is_still_bounded_at_runtime(tmp_path, new_name):
    broker = make_broker_from_policy(_policy_copy(
        tmp_path, "faithful.json", policy_name=new_name, engagement_id="renamed-eng"))
    execs, term, _caps = _governed(broker, tmp_path, _budget_mission(9))
    assert execs <= 5, execs
    assert term.d2_recognized is True, "renamed D2 scope must still be recognised"
    assert term.governed_step_ceiling == 5


# ── B5 ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cap", [0, 6, 64])
@pytest.mark.parametrize("engagement_id,policy_name", [
    ("d2-bounded-episode", "engagement-d2-v1"),   # honest identity
    ("renamed-engagement", "renamed-policy"),     # renamed away entirely
])
def test_b5_manual_broker_policy_cannot_bypass(tmp_path, cap, engagement_id,
                                              policy_name):
    broker = _manual_d2_broker(cap, engagement_id=engagement_id,
                               policy_name=policy_name)
    execs, term, _caps = _governed(broker, tmp_path, _budget_mission(9))
    assert execs <= 5, f"manual BrokerPolicy cap={cap} executed {execs} steps"
    assert term.d2_recognized is True
    assert term.governed_step_ceiling == 5


def test_b5b_manual_policy_without_any_d2_vocabulary_is_refused(tmp_path):
    """RSI-1 B-1: a neutral policy granting a PROTECTED capability fails CLOSED.

    This case previously executed 6 unbounded governed steps — it WAS the escape
    the final independent audit reported. Recognition can no longer be the only
    thing standing between a protected capability and an unbounded fallback:
    deleting every identity signal now removes the authorisation instead.
    """
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="other", policy_name="other", allowed_targets=["dvwa"],
        allowed_action_types=["recon_service_probe"],
        allowed_capabilities=[CAP_A], max_impact_per_action=2.0,
        max_episode_steps=64))
    runtime, _store, caps = build_runtime(tmp_path, broker)
    _traces, term = runtime.run_episode(_budget_mission(6))
    assert term.d2_recognized is False
    assert term.governed_step_ceiling == 0
    assert term.governance_refuses_protected is True
    assert term.governance_contract == ""
    assert sum(c.invocation_count for c in caps.values()) == 0


# ── B6 — alternate supported entry points ──────────────────────────────────

def test_b6_bare_step_loop_cannot_exceed_five(tmp_path, monkeypatch):
    """A caller that drives step() directly bypasses the iteration clamp."""
    broker = _manual_d2_broker(64, engagement_id="renamed", policy_name="renamed")
    runtime, _store, caps = build_runtime(tmp_path, broker)
    pep_calls, refusals = [], []
    original = stages_mod.stage_pep

    def counting_pep(ctx):
        pep_calls.append(ctx["planner_request"]["request"].action_id)
        result = original(ctx)
        if isinstance(result.output, dict) and result.output.get(
                "governed_step_budget_exhausted"):
            refusals.append(ctx["planner_request"]["request"].action_id)
        return result

    monkeypatch.setitem(stages_mod.STAGE_HANDLERS, stages_mod.STAGE_PEP, counting_pep)
    scope = ScopeV0(mission_id=MISSION, targets=("dvwa",),
                    allowed_action_types=("recon_service_probe",),
                    allowed_capabilities=(CAP_A,), max_impact=2.0)
    for i in range(30):
        view = {"mission_name": "x", "mission_id": MISSION, "iteration": i,
                "target": "dvwa", "objective_id": "o",
                "candidates": [_cand(f"ACT-{i}", "recon_service_probe", CAP_A, "nmap")]}
        runtime.step(RuntimeContext(mission_id=MISSION, objective_id="o", view=view,
                                    iteration=i, scope=scope))
    executed = sum(c.invocation_count for c in caps.values())
    assert len(pep_calls) == 30
    assert executed == 5, executed
    assert len(refusals) == 25, refusals[:3]
    assert runtime._step_budget.used == 5


def test_b6b_sequential_episodes_each_get_their_own_budget(tmp_path):
    """A NEW episode is a new budget; neither episode may exceed five."""
    broker = _manual_d2_broker(64, engagement_id="renamed", policy_name="renamed")
    assert broker.rate_limiter is None, "isolate the step ceiling from the rate limiter"
    runtime, _store, caps = build_runtime(tmp_path, broker)
    for _ in range(2):
        _traces, term = runtime.run_episode(_budget_mission(9))
        assert term.effective_budget == 5
        assert term.governed_steps_used == 5
    # 5 + 5, and never more.
    assert sum(c.invocation_count for c in caps.values()) == 10


# ── B7 — no replenishment by replan / denial / failure ─────────────────────

def test_b7_replanning_does_not_replenish(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    execs, term, _caps = _governed(broker, tmp_path, _budget_mission(5))
    assert execs == 5
    assert term.iterations == 5
    assert term.effective_budget == 5


def test_b7b_denial_loop_does_not_replenish(tmp_path):
    """Repeated broker denials inside a D2-recognised episode stay inside the cap.

    Uses the real D2 artifact with an action type the policy PROHIBITS, so the
    Broker denies every iteration: the episode can only continue via the
    denial-continuation path, and must still stop at five governed steps.
    """
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _store, caps = build_runtime(tmp_path, broker)
    mission = _budget_mission(9, action_type="shell_exec", method="/bin/sh",
                              scope=ScopeV0(mission_id=MISSION, targets=("dvwa",),
                                            allowed_action_types=("shell_exec",),
                                            allowed_capabilities=(CAP_A,),
                                            max_impact=2.0))
    outs = []
    _traces, term = runtime.run_episode(mission, episode_outputs=outs)
    assert term.d2_recognized is True
    assert len(outs) <= 5, "denial continuation may not exceed the episode budget"
    assert all("pep" not in o for o in outs)
    assert sum(c.invocation_count for c in caps.values()) == 0
    # The denials are recorded honestly as denials, never as executions.
    rows = _rows(runtime._organs.evidence_store)
    assert rows, "each attempted action must leave a durable denial record"
    assert all(r.get("decision") == "deny" for r in rows
               if r.get("kind") == "execution_result")


def test_b7c_failure_loop_does_not_replenish(tmp_path):
    def failing(argv, timeout):
        class P:
            returncode, stdout, stderr = 7, "", "curl: (7) Failed to connect"
        return P()

    broker = make_broker_from_policy(D2_POLICY_PATH)
    execs, _term, _caps = _governed(broker, tmp_path, _budget_mission(9),
                                    runner_map={CAP_A: failing, CAP_B: failing})
    assert execs <= 5, execs


def test_b7d_candidate_tail_does_not_replenish(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _store, caps = build_runtime(tmp_path, broker)
    cons = {"halt": {"max_iterations": 5, "action_cap": 1, "require_scope": True},
            "candidates": {str(i): [_cand(f"ACT-A{i}", "recon_service_probe", CAP_A, "nmap"),
                                    _cand(f"ACT-B{i}", "lab_http_probe", CAP_B, "curl")]
                           for i in range(9)},
            "default_target": "dvwa",
            "objective": {"requires_evidence": ["ACT-NEVER"]}}
    mission = MissionContext(
        mission_id=MISSION, name="tail", objectives=["x"], constraints=cons,
        scope=_d2_scope())
    runtime.run_episode(mission, max_iterations=50)
    assert sum(c.invocation_count for c in caps.values()) <= 5


# ── B8 — the sixth step cannot reach the PEP ────────────────────────────────

def test_b8_no_sixth_invocation_reaches_the_capability(tmp_path, monkeypatch):
    """No rate limiter is attached, so the step ceiling is the only gate."""
    broker = _manual_d2_broker(64, engagement_id="renamed", policy_name="renamed")
    assert broker.rate_limiter is None
    runtime, _store, caps = build_runtime(tmp_path, broker)
    succeeded = [r for r in broker.receipt_store.values()
                 if r.status.name == "SUCCEEDED"]
    _traces, term = runtime.run_episode(_budget_mission(9))
    succeeded = [r for r in broker.receipt_store.values()
                 if r.status.name == "SUCCEEDED"]
    assert len(succeeded) == 5, "at most five terminal successes may exist"
    assert sum(c.invocation_count for c in caps.values()) == 5
    assert term.governed_steps_used == 5


def test_b8b_budget_exhaustion_is_reported_honestly(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    execs, term, _caps = _governed(broker, tmp_path, _budget_mission(9))
    assert execs == 5
    # The objective was never satisfied, and the report must not claim it was.
    assert "objective met" not in term.reason
    assert "budget" in term.reason


def test_b8c_clamp_report_names_the_governing_bound(tmp_path):
    broker = _manual_d2_broker(64, engagement_id="renamed", policy_name="renamed")
    _execs, term, _caps = _governed(broker, tmp_path, _budget_mission(9))
    assert term.budget_clamped is True
    assert "canonical d2-bounded-episode invariant 5" in term.reason
    assert "policy declared 64" in term.reason


# ── B9 — D1 unchanged ──────────────────────────────────────────────────────

def test_b9_d1_artifact_is_unchanged():
    d1 = json.loads((D2_POLICY_PATH.parent / "engagement-d1-v1.json").read_text())
    assert "lab_http_probe" not in d1["allowed"]["action_types"]
    assert "exec.http_probe" not in d1["allowed"]["capabilities"]
    assert d1.get("max_episode_steps") is None
    assert D1Policy(D2_POLICY_PATH.parent / "engagement-d1-v1.json") \
        .max_episode_steps is None


def test_b9b_d1_governed_probe_still_works(tmp_path):
    broker = make_broker_from_policy(D2_POLICY_PATH)
    runtime, _store, caps = build_runtime(tmp_path, broker)
    scope = ScopeV0(mission_id="d1-regression", targets=("dvwa",),
                    allowed_action_types=("recon_service_probe",),
                    allowed_capabilities=(CAP_A,), max_impact=2.0)
    mission = MissionContext(
        mission_id="d1-regression", name="d1", objectives=["x"], scope=scope,
        constraints={"halt": {"max_iterations": 1, "action_cap": 1,
                              "require_scope": True},
                     "candidates": {"0": [_cand(A_ID, "recon_service_probe",
                                                CAP_A, "nmap")]},
                     "default_target": "dvwa"})
    outs = []
    _traces, term = runtime.run_episode(mission, episode_outputs=outs)
    assert sum(1 for o in outs if "pep" in o) == 1
    assert caps[CAP_A].invocation_count == 1


def test_b9c_canonical_d2_artifact_still_declares_five():
    policy = D1Policy(D2_POLICY_PATH)
    assert policy.max_episode_steps == 5
    assert policy.is_d2_scope is True
    assert policy.to_broker_policy().max_episode_steps == 5


# ══════════════════════════════════════════════════════════════════════════
# hypothesis + falsification (unchanged substrate)
# ══════════════════════════════════════════════════════════════════════════

def test_hypothesis_falsification_mapping():
    def ev(cvr, bvr, hard=0, excl=0):
        return FalsifiableEvaluation(hypothesis_id="h", experiment_id="e",
                                     criterion="c", hard_violations=hard,
                                     exclusions=excl, candidate_verified_rate=cvr,
                                     baseline_verified_rate=bvr)
    assert ev(1.0, 1.0).verdict() == "rejected"   # tie
    assert ev(0.9, 0.5).verdict() == "supported"
    assert ev(0.9, 0.5, hard=1).verdict() == "rejected"
    assert ev(0.2, 0.5, excl=3).verdict() == "inconclusive"