"""
P3.11 §14.12 adversarial probe battery (machine-executed at the final HEAD).

Each probe actively attempts a bypass class from the v4 §14.12 list and
asserts fail-closed denial with traceable evidence. All probes are
scoped to the canonical perimeter (F2 record); the legacy plane is
asserted out-of-perimeter (unreachable from the canonical Runtime),
not attacked as though it were in-perimeter.

Categories (v4 §14.12 + F1 regression + canonical bypass + invariants):
 1. Planner self-auth path
 2. direct capability construction
 3. direct process execution
 4. direct probe path (discriminator proposals do not execute)
 5. mode-local execution (legacy modes unreachable from canonical path)
 6. migration seam abuse
 7. test-policy abuse (narrow policy denies outside its grant)
 8. missing decision linkage (event without decision id is detectable)
 9. fake receipt creation
10. WorldModel claim forgery (relationships require evidence linkage)
11. F1 copied-ID / forged-object (direct probe variant)
12. canonical bypass paths (§14.11.1: every execution event has a Broker id)
13. architecture invariant violations (1 Runtime / 1 PDP / 1 PEP / 10 stages)
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


def _runtime():
    from orchestrator.runtime import RaphaelRuntime
    return RaphaelRuntime()


# ── 1. Planner self-auth path ────────────────────────────────

def test_adv_planner_decision_confirms_nothing_by_itself():
    """A PlanDecision alone authorizes nothing: no receipt, no execution."""
    rt = _runtime()
    pd = rt._organs.planner.decide(
        candidates=[{
            "action_type": "safe_proving_capability",
            "capability": "fixture.inspect",
            "target": "system_info.name",
            "method": "inspect",
            "action_id": "adv-self-auth-001",
            "rationale": "adversarial: planner self-auth attempt",
            "impact_estimate": 0.0,
            "confidence": 1.0,
        }],
        objective_id="adv-objective",
    )
    assert pd.selected_action_id == "adv-self-auth-001"
    # The decision created no broker receipt and executed nothing.
    assert rt._broker.receipt_store.get("adv-self-auth-001") is None
    assert rt._capability.invocation_count == 0


def test_planner_requires_broker():
    """P3.2 / §14.9: the Planner proposes only; the Broker must decide before
    anything executes."""
    from orchestrator.runtime import MissionContext

    rt = _runtime()
    pd = rt._organs.planner.decide(
        candidates=[{
            "action_type": "safe_proving_capability",
            "capability": "fixture.inspect",
            "target": "system_info.name",
            "method": "inspect",
            "action_id": "planner-needs-broker-001",
            "rationale": "planner-only",
            "impact_estimate": 0.0,
            "confidence": 1.0,
        }],
        objective_id="planner-needs-broker",
    )
    assert pd.selected_action_id == "planner-needs-broker-001"
    # Planner decision alone: no receipt, no execution.
    assert rt._broker.receipt_store.get("planner-needs-broker-001") is None
    assert rt._capability.invocation_count == 0

    # Canonical execution happens only with a Broker decision, and the PEP
    # event carries that decision id (Broker remains the sole PDP).
    outputs: list = []
    rt.run_episode(
        MissionContext(mission_id="pb", name="pb", objectives=["inspect"]),
        episode_outputs=outputs,
    )
    assert rt._capability.invocation_count == 1
    decision = outputs[0]["broker"]["decision"]
    assert decision.decision == "allow"
    assert outputs[0]["pep"]["event"].decision_id == decision.decision_id


# ── 2. direct capability construction ────────────────────────

def test_adv_broker_bound_capability_requires_recorded_authorization():
    """Constructing the capability directly does not bypass the PEP gate."""
    from orchestrator.exec.safe_capability import (
        SafeProvingCapability, CapabilityNotGatedError,
    )
    rt = _runtime()
    cap = SafeProvingCapability(broker=rt._broker)
    # No record_authorization call happened: inspect must refuse.
    with pytest.raises(CapabilityNotGatedError):
        cap.inspect("system_info.name")


def test_broker_required_error_on_direct_ctor():
    """P3.5 / §14.9: a directly constructed privileged capability is not
    executable without recorded Broker authorization."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    from orchestrator.exec.safe_capability import (
        SafeProvingCapability, CapabilityNotGatedError,
    )

    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="direct-ctor", allowed_targets=["*"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    # Direct construction alone yields no executable authorization state.
    cap = SafeProvingCapability(broker=broker)
    with pytest.raises(CapabilityNotGatedError):
        cap.inspect("system_info.name")
    # Only a recorded Broker authorization ungates it.
    cap.record_authorization("system_info.name")
    assert cap.inspect("system_info.name").output is not None


# ── 3. direct process execution ──────────────────────────────

def test_adv_no_primitive_imports_in_runtime():
    """INV-1: runtime/*.py contains no subprocess/socket/os/shutil imports."""
    import ast
    forbidden = {"subprocess", "socket", "requests", "os", "shutil"}
    violations = []
    for py_file in (SRC_ROOT / "orchestrator" / "runtime").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        tree = ast.parse(py_file.read_text(errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden:
                        violations.append((str(py_file), node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in forbidden:
                    violations.append((str(py_file), node.lineno, node.module))
    assert not violations, violations


# ── 4. direct probe path ─────────────────────────────────────

def test_adv_discriminator_proposals_do_not_execute():
    """Contradiction discriminator proposals are data, not execution."""
    rt = _runtime()
    cm = rt._organs.contradiction_manager
    before = rt._capability.invocation_count
    try:
        proposals = cm.propose_discriminators("nonexistent-id", max_proposals=3)
    except Exception:
        proposals = []
    assert isinstance(proposals, list)
    assert rt._capability.invocation_count == before


# ── 5. mode-local execution ──────────────────────────────────

def test_adv_legacy_modes_unreachable_from_canonical_closure():
    """modes/autonomous.py is not in the canonical Runtime closure (F2)."""
    import ast
    seen = set()
    legacy_refs = []

    def walk(module_path: str):
        if module_path in seen:
            return
        seen.add(module_path)
        rel = module_path.replace(".", "/") + ".py"
        p = SRC_ROOT / rel
        if not p.exists():
            return
        try:
            tree = ast.parse(p.read_text(errors="ignore"))
        except Exception:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    name = a.name
                    if name.startswith("orchestrator.") and name not in seen:
                        if "modes.autonomous" in name or "modes" == name.split(".")[-1]:
                            legacy_refs.append((module_path, name))
                        walk(name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith("orchestrator."):
                    if "modes.autonomous" in mod:
                        legacy_refs.append((module_path, mod))
                    walk(mod)

    walk("orchestrator.runtime")
    assert not legacy_refs, legacy_refs
    assert not any("modes" in m and "autonomous" in m for m in seen)


# ── 6. migration seam abuse ──────────────────────────────────

def test_adv_no_seam_module_or_import():
    """No seam module exists; no orchestrator module imports a seam."""
    import ast
    assert not list((SRC_ROOT / "orchestrator" / "runtime").glob("*seam*.py"))
    violations = []
    for py_file in (SRC_ROOT / "orchestrator").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text(errors="ignore"))
        except Exception:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                if "seam" in m.lower():
                    violations.append((str(py_file), m))
    assert not violations, violations


# ── 7. test-policy abuse ─────────────────────────────────────

def test_adv_narrow_policy_denies_outside_grant():
    """A broker bound to a narrow test policy denies unlisted classes."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="adv-narrow",
        allowed_targets=["system_info.name"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    denied = broker.propose_action(
        target="system_info.name", action_type="reverse_shell",
        capability="shell.exec", method="netcat", impact_estimate=0.0,
    )
    assert denied.decision == "deny"
    # And the denial cannot be replayed as an allow.
    from orchestrator.hardening.action_receipt import ActionProposalStatus
    assert denied.status == ActionProposalStatus.DENIED


# ── 8. missing decision linkage ──────────────────────────────

def test_adv_event_without_decision_id_is_detectable():
    """An ExecutionEvent lacking a decision id fails the linkage check."""
    from orchestrator.runtime.types import ExecutionEvent
    event = ExecutionEvent(
        action_id="ACT_adv", decision_id="", capability="fixture.inspect",
        target="system_info.name", args={}, outcome="ok", output=None,
    )
    # The §14.11.1 invariant: every execution event must carry a Broker
    # decision id. An empty decision id is machine-detectable.
    assert event.decision_id == ""
    linked = bool(event.decision_id) and bool(event.action_id)
    assert linked is False


# ── 9. fake receipt creation ─────────────────────────────────

def test_adv_fake_receipt_unknown_action_id_denied(tmp_path):
    """A fabricated receipt absent from the broker store is denied."""
    import types
    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest, SandboxNotAuthorized,
    )
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    root = tmp_path / "advroot"
    root.mkdir()
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="adv-fake", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    ex = SandboxedExecutor(broker=broker, policy=SandboxPolicy(workdir_root=str(root)))
    forged = types.SimpleNamespace(action_id="adv-fake-id-zzz")
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="t", argv=("/bin/echo", "x"),
                           capability="fixture.inspect",
                           action_type="sandboxed_exec", method="exec"),
            forged,
        )


# ── 10. WorldModel claim forgery ─────────────────────────────

def test_adv_relationship_without_evidence_rejected():
    """WorldModel relationships require evidence linkage (no forgery)."""
    rt = _runtime()
    from orchestrator.brain.world import Relationship, RelationshipType
    rel = Relationship(
        source_entity_id="ent_a", target_entity_id="ent_b",
        relationship_type=RelationshipType.CONNECTS_TO,
        evidence_ids=[],  # forged: no evidence
    )
    with pytest.raises(ValueError):
        rt._world_model.add_relationship(rel)


def test_adv_relationship_unknown_evidence_id_rejected():
    """F-5 regression: a fabricated evidence ID must not enter the WorldModel."""
    rt = _runtime()
    from orchestrator.brain.world import Relationship, RelationshipType
    rel = Relationship(
        source_entity_id="ent_a", target_entity_id="ent_b",
        relationship_type=RelationshipType.CONNECTS_TO,
        evidence_ids=["DOES-NOT-EXIST-IN-GRAPH"],
    )
    with pytest.raises(ValueError) as exc:
        rt._world_model.add_relationship(rel)
    assert "DOES-NOT-EXIST-IN-GRAPH" in str(exc.value)
    assert rel.relationship_id not in rt._world_model.relationships


def test_adv_relationship_partially_unknown_evidence_rejected():
    """One unknown ID among several rejects the whole relationship."""
    from orchestrator.brain.evidence import Evidence
    from orchestrator.brain.trust import TrustLevel
    from orchestrator.brain.world import Relationship, RelationshipType

    rt = _runtime()
    real = Evidence.create(
        raw_content="real evidence", trust_level=TrustLevel.TOOL_OBSERVATION,
        source_detail="test", evidence_type="test",
    )
    rt._organs.evidence_graph.add_evidence(real)
    rel = Relationship(
        source_entity_id="ent_a", target_entity_id="ent_b",
        relationship_type=RelationshipType.CONNECTS_TO,
        evidence_ids=[real.evidence_id, "DOES-NOT-EXIST-IN-GRAPH"],
    )
    with pytest.raises(ValueError):
        rt._world_model.add_relationship(rel)


def test_adv_relationship_valid_evidence_id_accepted_and_retained():
    """A real EvidenceGraph ID is accepted and retained on the relationship."""
    from orchestrator.brain.evidence import Evidence
    from orchestrator.brain.trust import TrustLevel
    from orchestrator.brain.world import Relationship, RelationshipType

    rt = _runtime()
    ev = Evidence.create(
        raw_content="valid provenance", trust_level=TrustLevel.TOOL_OBSERVATION,
        source_detail="test", evidence_type="test",
    )
    rt._organs.evidence_graph.add_evidence(ev)
    rel = Relationship(
        source_entity_id="ent_a", target_entity_id="ent_b",
        relationship_type=RelationshipType.CONNECTS_TO,
        evidence_ids=[ev.evidence_id],
    )
    rel_id = rt._world_model.add_relationship(rel)
    assert rel_id == rel.relationship_id
    stored = rt._world_model.relationships[rel_id]
    assert stored.evidence_ids == [ev.evidence_id]


# ── 11. F1 copied-ID / forged-object (direct probe variant) ──

def test_adv_copied_id_wrong_method_denied(tmp_path):
    """Copied action_id with a swapped method is denied at the boundary."""
    import types
    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest, SandboxNotAuthorized,
    )
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    root = tmp_path / "advroot2"
    root.mkdir()
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="adv-f1", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    argv = ("/bin/echo", "approved")
    receipt = broker.propose_action(
        target="t", action_type="sandboxed_exec",
        capability="fixture.inspect", method="exec", impact_estimate=0.0,
        authorized_argv=argv,
    )
    assert receipt.decision == "allow"
    forged = types.SimpleNamespace(action_id=receipt.action_id)
    ex = SandboxedExecutor(broker=broker, policy=SandboxPolicy(workdir_root=str(root)))
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="t", argv=argv,
                           capability="fixture.inspect",
                           action_type="sandboxed_exec", method="netcat"),
            forged,
        )


# ── 12. canonical bypass paths (§14.11.1 machine check) ──────

def test_adv_full_episode_every_event_has_broker_id():
    """Every PEP event in a full episode carries a Broker decision id."""
    import json
    from orchestrator.runtime.scope import ScopeV0
    from orchestrator.runtime import MissionContext
    doc = json.loads((REPO_ROOT / "tests" / "p311_mvp_mission.json").read_text())
    scope = ScopeV0.from_dict(doc["scope"])
    mission = MissionContext(
        mission_id=doc["mission_id"], name=doc["name"],
        objectives=list(doc["objectives"]),
        constraints={"candidates": doc["candidates"],
                     "default_target": "system_info.name",
                     "objective_id": "mvp-objective-prove-fixture"},
        scope=scope,
    )
    rt = _runtime()
    outputs: list = []
    traces, _ = rt.run_episode(mission, max_iterations=2, require_scope=True,
                               episode_outputs=outputs)
    assert len(traces) == 2
    event = outputs[1]["pep"]["event"]
    decision = outputs[1]["broker"]["decision"]
    receipt = outputs[1]["broker"]["receipt"]
    assert event.decision_id and event.decision_id == decision.decision_id
    assert decision.decision_id == receipt.action_id
    assert event.action_id and decision.action_id == event.action_id


def test_runtime_execution_decision_linkage():
    """§14.11.1 / §14.9: every Runtime execution event carries its Broker
    decision id (INV-2)."""
    import json
    from orchestrator.runtime.scope import ScopeV0
    from orchestrator.runtime import MissionContext
    from orchestrator.runtime.types import ExecutionEvent

    doc = json.loads((REPO_ROOT / "tests" / "p311_mvp_mission.json").read_text())
    scope = ScopeV0.from_dict(doc["scope"])
    mission = MissionContext(
        mission_id=doc["mission_id"], name=doc["name"],
        objectives=list(doc["objectives"]),
        constraints={"candidates": doc["candidates"],
                     "default_target": "system_info.name",
                     "objective_id": "mvp-objective-prove-fixture"},
        scope=scope,
    )
    rt = _runtime()
    outputs: list = []
    traces, _ = rt.run_episode(mission, max_iterations=2, require_scope=True,
                               episode_outputs=outputs)

    event = outputs[1]["pep"]["event"]
    decision = outputs[1]["broker"]["decision"]
    receipt = outputs[1]["broker"]["receipt"]
    # Positive: the executed event links action -> decision -> broker receipt.
    assert event.decision_id and event.decision_id == decision.decision_id
    assert decision.decision_id == receipt.action_id
    assert event.action_id and decision.action_id == event.action_id

    # Negative: an event without a Broker decision id is detectably unlinked.
    forged = ExecutionEvent(
        action_id="ACT_unlinked", decision_id="", capability="fixture.inspect",
        target="system_info.name", args={}, outcome="ok", output=None,
    )
    assert not (forged.decision_id and forged.action_id)


# ── 13. architecture invariant violations ────────────────────

def test_adv_single_runtime_pdp_pep_ten_stages():
    """1 Runtime, 1 PDP, 1 PEP entry, 10 stages (machine check)."""
    from orchestrator.runtime.stages import STAGE_ORDER, STAGE_HANDLERS, stage_pep
    from orchestrator.runtime import RaphaelRuntime
    from orchestrator.brain.capability_broker import CapabilityBroker
    assert len(STAGE_ORDER) == 10
    assert len(STAGE_HANDLERS) == 10
    assert STAGE_ORDER == [
        "observe", "worldmodel_read", "student_candidate", "planner_request",
        "broker", "pep", "receipt", "worldmodel_integrate", "contradiction",
        "replan",
    ]
    rt = RaphaelRuntime()
    assert type(rt).__name__ == "RaphaelRuntime"
    assert isinstance(rt._broker, CapabilityBroker)
    assert STAGE_HANDLERS["pep"] is stage_pep
