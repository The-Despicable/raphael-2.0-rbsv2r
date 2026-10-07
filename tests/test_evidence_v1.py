"""
§14.5 Evidence v1 tests: typed records, deterministic identity, strict
serialization, bounded persistence, provenance linkage, and control-plane
boundaries. Evidence records; it never authorizes, executes, or believes.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.runtime.evidence_v1 import (
    EVIDENCE_VERSION,
    EvidenceError,
    EvidenceKind,
    EvidenceRecord,
)
from orchestrator.exec.evidence_store import EvidenceStore


def _obs(**overrides):
    base = dict(mission_id="m", producer="sandbox.exec", content="saw x")
    base.update(overrides)
    return EvidenceRecord.observation(**base)


# ── 1-2. classes construct; malformed rejected ────────────────────

def test_all_five_classes_construct():
    obs = _obs()
    ass = EvidenceRecord.assertion(
        mission_id="m", producer="planner", claim="x is y", claimant="planner")
    exe = EvidenceRecord.execution_result(
        mission_id="m", producer="sandbox.exec", action_id="act_1", status="success")
    art = EvidenceRecord.artifact(
        mission_id="m", producer="sandbox.exec", relpath="out.txt",
        size_bytes=3, sha256="a" * 64)
    fnd = EvidenceRecord.finding(
        mission_id="m", producer="analyst", statement="x holds",
        derived_from=(obs.identity,))
    kinds = {r.kind for r in (obs, ass, exe, art, fnd)}
    assert kinds == set(EvidenceKind)
    for record in (obs, ass, exe, art, fnd):
        assert record.identity.startswith("ev1_")
        assert record.version == EVIDENCE_VERSION


def test_malformed_evidence_rejected():
    with pytest.raises(EvidenceError):
        EvidenceRecord.observation(mission_id="", producer="p", content="x")
    with pytest.raises(EvidenceError):
        EvidenceRecord.observation(mission_id="m", producer="p", content="x" * 9000)
    with pytest.raises(EvidenceError):
        EvidenceRecord.assertion(mission_id="m", producer="p", claim="c",
                                 claimant="x", parents=("a",) * 9)
    with pytest.raises(EvidenceError):
        EvidenceRecord.finding(mission_id="m", producer="p",
                               statement="s", derived_from=())
    with pytest.raises(EvidenceError):
        EvidenceRecord.artifact(mission_id="m", producer="p",
                                relpath="/etc/hostname", size_bytes=1,
                                sha256="b" * 64)
    with pytest.raises(EvidenceError):
        EvidenceRecord.artifact(mission_id="m", producer="p", relpath="a.txt",
                                size_bytes=-1, sha256="b" * 64)


# ── 3-6. version, determinism, round-trip ─────────────────────────

def test_version_enforced():
    record = _obs()
    bad = dict(record.to_dict())
    bad["version"] = 999
    with pytest.raises(EvidenceError):
        EvidenceRecord.from_dict(bad)


def test_deterministic_identity_and_serialization():
    first = EvidenceRecord.observation(
        mission_id="m", producer="p", content="same", observed_at=1000.0)
    second = EvidenceRecord.observation(
        mission_id="m", producer="p", content="same", observed_at=2000.0)
    # observed_at is provenance, not identity: equivalents share identity.
    assert first.identity == second.identity
    assert first.to_dict() != second.to_dict()  # timestamps differ in form
    clone = EvidenceRecord.from_dict(first.to_dict())
    assert clone == first
    assert clone.identity == first.identity
    other = _obs(content="different")
    assert other.identity != first.identity


def test_serialization_stable_bytes():
    import json

    record = _obs()
    once = json.dumps(record.to_dict(), sort_keys=True)
    twice = json.dumps(EvidenceRecord.from_dict(record.to_dict()).to_dict(),
                       sort_keys=True)
    assert once == twice


# ── 7-8. unknown / missing fields ─────────────────────────────────

def test_unknown_fields_rejected():
    bad = dict(_obs().to_dict())
    bad["authorization"] = "allow"
    with pytest.raises(EvidenceError):
        EvidenceRecord.from_dict(bad)


def test_missing_required_fields_rejected():
    bad = dict(_obs().to_dict())
    del bad["payload"]
    with pytest.raises(EvidenceError):
        EvidenceRecord.from_dict(bad)
    with pytest.raises(EvidenceError):
        EvidenceRecord.from_dict({"kind": "observation"})


# ── 9-11. provenance, action, artifact linkage ────────────────────

def test_provenance_preserved():
    record = EvidenceRecord.observation(
        mission_id="mission-7", producer="sensor.x", content="c",
        target="10.0.0.1", source="fixture.inspect", observed_at=1234.0)
    clone = EvidenceRecord.from_dict(record.to_dict())
    assert clone.mission_id == "mission-7"
    assert clone.producer == "sensor.x"
    assert clone.observed_at == 1234.0
    assert dict(clone.payload)["target"] == "10.0.0.1"


def test_execution_action_linkage_live_sandbox():
    """Real SandboxResult -> ExecutionResult record preserves outcome."""
    import tempfile

    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest)
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker)

    root = tempfile.mkdtemp()
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="e", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"]))
    receipt = broker.propose_action(
        target="t", action_type="sandboxed_exec",
        capability="fixture.inspect", method="exec", impact_estimate=0.0,
        # §14.6 F1: thread the argv the live sandbox will execute.
        authorized_argv=("/bin/echo", "linked"),
    )
    assert receipt.decision == "allow"
    executor = SandboxedExecutor(
        broker=broker, policy=SandboxPolicy(workdir_root=root))
    outcome = executor.execute(
        SandboxRequest(
            target="t", argv=("/bin/echo", "linked"),
            # §14.6 F1: thread the four request-side authorization dimensions.
            capability="fixture.inspect",
            action_type="sandboxed_exec",
            method="exec",
        ),
        receipt,
    )
    record = EvidenceRecord.execution_result_from_sandbox(
        mission_id="m", action_id=receipt.action_id, sandbox_result=outcome,
        decision=receipt.decision, policy_version="bootstrap-v0")
    payload = dict(record.payload)
    assert payload["action_id"] == receipt.action_id
    assert payload["status"] == "success"
    assert "linked" in payload["stdout"]
    assert payload["decision"] == "allow"
    assert payload["policy_version"] == "bootstrap-v0"


def test_artifact_linkage_references_not_reads(tmp_path):
    """Artifact records reference bytes passed in; evidence reads no host files."""
    import hashlib

    content = b"artifact-bytes"
    fake = type("R", (), {"artifacts": {"out.bin": content}})()
    records = EvidenceRecord.artifact_records_from_sandbox(
        mission_id="m", sandbox_result=fake, execution_ref="act_9")
    assert len(records) == 1
    payload = dict(records[0].payload)
    assert payload["relpath"] == "out.bin"
    assert payload["size_bytes"] == len(content)
    assert payload["sha256"] == hashlib.sha256(content).hexdigest()
    assert payload["execution_ref"] == "act_9"


# ── 12-16. bounds, duplicates, refs, cycles ───────────────────────

def test_bounded_record_size():
    with pytest.raises(EvidenceError):
        EvidenceRecord.execution_result(
            mission_id="m", producer="p", action_id="a", status="success",
            stdout="y" * 70000)


def test_duplicate_identical_idempotent(tmp_path):
    store = EvidenceStore(str(tmp_path / "ev.jsonl"))
    record = _obs()
    assert store.append(record) == record.identity
    assert store.append(record) == record.identity
    assert len(store) == 1


def test_duplicate_conflict_rejected(tmp_path):
    store = EvidenceStore(str(tmp_path / "ev.jsonl"))
    record = _obs()
    store.append(record)
    tampered = dict(record.to_dict())
    tampered_payload = dict(tampered["payload"])
    tampered_payload["content"] = "different content, same envelope id"
    tampered["payload"] = tampered_payload
    # Same envelope identity, different content: hand-crafted conflict.
    with pytest.raises(EvidenceError):
        store.append(EvidenceRecord.from_dict(tampered))


def test_invalid_reference_rejected(tmp_path):
    store = EvidenceStore(str(tmp_path / "ev.jsonl"))
    orphan = EvidenceRecord.finding(
        mission_id="m", producer="p", statement="s",
        derived_from=("ev1_" + "0" * 64,))
    with pytest.raises(EvidenceError):
        store.append(orphan)


# ── 17-18. persistence, corruption ────────────────────────────────

def test_persistence_and_retrieval(tmp_path):
    path = str(tmp_path / "ev.jsonl")
    store = EvidenceStore(path)
    first = _obs()
    child = EvidenceRecord.finding(
        mission_id="m", producer="p", statement="holds",
        derived_from=(first.identity,))
    store.append(first)
    store.append(child)
    reopened = EvidenceStore(path)
    assert len(reopened) == 2
    assert reopened.get(child.identity) == child
    assert reopened.get("ev1_" + "f" * 64) is None


def test_corrupt_record_fails_closed(tmp_path):
    path = tmp_path / "ev.jsonl"
    path.write_text('{"identity": "ev1_x", "record": {"kind": "nope"}}\n')
    with pytest.raises(EvidenceError):
        EvidenceStore(str(path))
    path.write_text('not json at all\n')
    with pytest.raises(EvidenceError):
        EvidenceStore(str(path))


# ── 19. evidence cannot authorize ─────────────────────────────────

def test_evidence_cannot_authorize_execution(tmp_path):
    """A v1 record presented as a receipt is denied by the existing path."""
    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest)
    from orchestrator.brain.capability_broker import (
        BrokerPolicy, CapabilityBroker)

    broker = CapabilityBroker(BrokerPolicy(engagement_id="e"))
    executor = SandboxedExecutor(
        broker=broker, policy=SandboxPolicy(workdir_root=str(tmp_path)))
    from orchestrator.exec.sandbox import SandboxNotAuthorized

    with pytest.raises(SandboxNotAuthorized):
        executor.execute(
            SandboxRequest(target="t", argv=("/bin/echo", "x")),
            _obs(),  # evidence record: no action_id in broker store
        )
    # Records expose no authorization verbs at all.
    for verb in ("authorize", "allow", "approve", "grant", "permit", "execute"):
        assert not hasattr(EvidenceRecord, verb), verb


# ── 20-23. boundaries: scope/sandbox unchanged, no stage/PDP/arena ──

def test_scope_sandbox_behavior_unchanged():
    """§14.3/§14.4 behavior intact after adding evidence substrate."""
    from orchestrator.runtime import RaphaelRuntime, MissionContext
    from orchestrator.runtime.scope import ScopeV0

    scope = ScopeV0(mission_id="m", targets=("system_info.name",),
                    allowed_action_types=("safe_proving_capability",),
                    allowed_capabilities=("fixture.inspect",))
    _, term = RaphaelRuntime().run_episode(
        MissionContext(mission_id="m", name="m", objectives=["i"], scope=scope))
    assert term.final_stage == "replan"
    _, term = RaphaelRuntime().run_episode(
        MissionContext(mission_id="m", name="m", objectives=["i"]),
        require_scope=True)
    assert term.final_stage == "scope"


def test_no_new_stage_no_new_pdp():
    from orchestrator.runtime.stages import STAGE_ORDER

    assert len(STAGE_ORDER) == 10
    assert STAGE_ORDER[4] == "broker" and STAGE_ORDER[5] == "pep"


def test_no_arena_in_evidence_surface():
    """Evidence modules stay stdlib-only at top level (closure-safe).

    Only module-level imports affect the Runtime closure; the single
    function-level brain import inside to_legacy_evidence() runs solely
    when explicitly exporting to the canonical graph.
    """
    import ast

    for rel in ("runtime/evidence_v1.py",):
        tree = ast.parse((SRC_ROOT / "orchestrator" / rel).read_text())
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        assert "arena" not in imported
        assert "orchestrator" not in imported, sorted(imported)




def test_worldmodel_untouched_by_finding():
    """Creating Findings mutates no beliefs: WorldModel entity count stable."""
    from orchestrator.brain.world import WorldModel
    from orchestrator.brain.evidence import EvidenceGraph

    world = WorldModel(EvidenceGraph())
    before = len(world.entities)
    obs = _obs()
    EvidenceRecord.finding(mission_id="m", producer="p", statement="s",
                           derived_from=(obs.identity,))
    assert len(world.entities) == before


def test_legacy_graph_integration_no_second_graph():
    """v1 exports into the canonical EvidenceGraph via existing add_evidence."""
    from orchestrator.brain.evidence import EvidenceGraph
    from orchestrator.brain.trust import TrustLevel

    graph = EvidenceGraph()
    legacy = _obs().to_legacy_evidence()
    evidence_id = graph.add_evidence(legacy)
    fetched = graph.get_evidence(evidence_id)
    assert fetched.evidence_type == "v1:observation"
    assert fetched.trust_level == TrustLevel.TOOL_OBSERVATION
    # Student producers keep their label with no trust elevation.
    student = EvidenceRecord.observation(
        mission_id="m", producer="student.candidate", content="c")
    assert (student.to_legacy_evidence().trust_level
            == TrustLevel.MODEL_INFERENCE)


def test_artifact_ref_count_bounded():
    """More than MAX_ARTIFACT_REFS references rejected (boundedness)."""
    from orchestrator.runtime.evidence_v1 import MAX_ARTIFACT_REFS

    with pytest.raises(EvidenceError):
        EvidenceRecord.execution_result(
            mission_id="m", producer="p", action_id="a", status="success",
            artifacts=tuple(f"f{i}.txt" for i in range(MAX_ARTIFACT_REFS + 1)))


# ── 24. Canonical Runtime integration (producer -> store -> consumer) ──

def _scoped_mission(mission_id="ev1-integration"):
    from orchestrator.runtime import MissionContext
    from orchestrator.runtime.scope import ScopeV0

    scope = ScopeV0(
        mission_id=mission_id, targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",), max_impact=0.0,
    )
    return MissionContext(
        mission_id=mission_id, name=mission_id, objectives=["inspect"],
        scope=scope,
    )


def _candidate_mission(mission_id, action_id):
    from orchestrator.runtime import MissionContext
    from orchestrator.runtime.scope import ScopeV0

    scope = ScopeV0(
        mission_id=mission_id, targets=("system_info.name",),
        allowed_action_types=("safe_proving_capability",),
        allowed_capabilities=("fixture.inspect",), max_impact=0.0,
    )
    candidate = {
        "action_id": action_id,
        "action_type": "safe_proving_capability",
        "target": "system_info.name",
        "capability": "fixture.inspect",
        "method": "inspect",
        "args": {"read_only": True},
        "rationale": "ev1 integration",
        "confidence": 1.0,
        "impact_estimate": 0.0,
    }
    return MissionContext(
        mission_id=mission_id, name=mission_id, objectives=["inspect"],
        constraints={"candidates": {"0": [candidate]},
                     "default_target": "system_info.name",
                     "objective_id": "ev1-objective"},
        scope=scope,
    )


def test_canonical_episode_produces_and_persists_evidence_v1(tmp_path):
    """A real canonical episode persists an execution_result and links it."""
    from orchestrator.runtime import RaphaelRuntime

    store = EvidenceStore(str(tmp_path / "evidence_v1.jsonl"))
    rt = RaphaelRuntime(evidence_store=store)
    outputs: list = []
    traces, term = rt.run_episode(
        _scoped_mission(), require_scope=True, episode_outputs=outputs)

    assert term.final_stage == "replan"  # canonical Runtime still runs
    receipt_out = outputs[0]["receipt"]
    evidence_id = receipt_out["evidence_v1_id"]
    assert evidence_id.startswith("ev1_")

    record = store.get(evidence_id)
    assert record is not None
    assert record.kind == EvidenceKind.EXECUTION_RESULT
    event = outputs[0]["pep"]["event"]
    assert dict(record.payload)["action_id"] == event.action_id
    # The canonical receipt links to the durable record.
    assert receipt_out["receipt"].evidence_v1_ids == (evidence_id,)

    # Durable + readable back from disk by a consumer.
    reopened = EvidenceStore(str(tmp_path / "evidence_v1.jsonl"))
    assert reopened.get(evidence_id) == record


def test_canonical_episode_without_store_is_unchanged():
    """No store bound: the canonical path runs with no persistence."""
    from orchestrator.runtime import RaphaelRuntime

    outputs: list = []
    rt = RaphaelRuntime()
    traces, term = rt.run_episode(
        _scoped_mission("ev1-no-store"), require_scope=True,
        episode_outputs=outputs)
    assert term.final_stage == "replan"
    assert outputs[0]["receipt"]["evidence_v1_id"] == ""
    assert outputs[0]["receipt"]["receipt"].evidence_v1_ids == ()


def test_evidence_v1_replay_is_idempotent(tmp_path):
    """Re-ingesting the same decision does not duplicate evidence."""
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.runtime.evidence_v1 import EvidenceRecord

    store = EvidenceStore(str(tmp_path / "evidence_v1.jsonl"))
    rt = RaphaelRuntime(evidence_store=store)
    rt.run_episode(
        _candidate_mission("ev1-replay", "ev1-fixed-001"), require_scope=True)
    # The default capability collects no artifact, so this episode persists
    # only its execution_result.
    records = store.records()
    assert {r.kind.value for r in records} == {"execution_result"}
    persisted = records[0]

    # Re-ingesting the identical record is idempotent (same content-addressed
    # identity, no duplicate row).
    assert store.append(EvidenceRecord.from_dict(persisted.to_dict())) == persisted.identity
    assert len(store) == 1

    # A fresh episode mints a NEW authorization (new decision_id), so it is a
    # genuinely distinct attempt and is recorded as such — the two records are
    # never conflated.
    rt.run_episode(
        _candidate_mission("ev1-replay", "ev1-fixed-001"), require_scope=True)
    assert len(store) == 2
    decision_ids = {dict(r.payload)["decision_id"] for r in store.records()}
    assert len(decision_ids) == 2


def test_evidence_v1_malformed_or_failing_store_fails_closed():
    """Evidence production failure fails closed (and does not authorize)."""
    from orchestrator.runtime import RaphaelRuntime

    class _BrokenStore:
        def get(self, identity):
            raise EvidenceError("corrupt evidence store")

        def append(self, record):
            raise EvidenceError("corrupt evidence store")

    outputs: list = []
    rt = RaphaelRuntime(evidence_store=_BrokenStore())
    traces, term = rt.run_episode(
        _scoped_mission("ev1-broken"), require_scope=True,
        episode_outputs=outputs)
    assert term.final_stage == "receipt"
    assert "Evidence v1 fail-closed" in term.reason
    # PEP had already run, but the broken evidence never authorized it:
    # the broker decision is the sole authorization (recorded at broker stage).
    assert outputs[0]["broker"]["decision"].decision == "allow"
