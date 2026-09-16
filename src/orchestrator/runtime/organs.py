"""
organs.py — Canonical organ wiring (G3-EN-5)

Per v4 section 13.3 P2.2: "Wire minimal handlers for: observation,
WorldModel read, Student candidate generation in recording mode,
Planner request generation, Broker call, PEP invocation, receipt
emission, minimal WorldModel integration, minimal contradiction/
failure trigger, replan."

G3-EN-5: wire Planner, WorldModel (read + integrate), Student
(recording mode), and minimal contradiction/failure trigger onto
the single canonical Runtime path.

The organs are instantiated from the brain modules. The Runtime
holds a reference to each organ and calls them in the stage handlers.

Constraints:
- One Runtime, no second orchestrator
- No new stages (existing 10 stages, modified in-place)
- CapabilityBroker remains the single PDP
- PEP remains under exec/
- INV-2 decision linkage preserved
- Fail-closed preserved
- Arena-free Runtime closure
- Student recording-only (no learning, no promotion)
- No P5 falsification semantics
"""
from typing import Any, Optional

from orchestrator.brain.evidence import EvidenceGraph
from orchestrator.brain.world import WorldModel
from orchestrator.brain.hypothesis import HypothesisManager
from orchestrator.brain.contradiction import ContradictionManager
from orchestrator.brain.action import Planner
from orchestrator.brain.candidate_generators.student_generator import (
    StudentCandidateGenerator,
)


class OrganBundle:
    """Bundle of Head-2 organs wired onto the canonical Runtime path.

    Per G3-EN-5: one bundle per Runtime. Organs are instantiated
    with minimal interconnections suitable for the P3.0 walking
    skeleton. Full organ depth is P4 work.
    """

    def __init__(self, evidence_store: Optional[Any] = None):
        # EvidenceGraph is the substrate that WorldModel, Contradiction,
        # and Hypothesis all share.
        self.evidence_graph = EvidenceGraph()
        # §14.5 Evidence v1 durable store (exec/-owned). Optional: when
        # None the canonical path runs without persistence (legacy).
        # Evidence records only; it never authorizes.
        self.evidence_store = evidence_store
        # WorldModel: read + integrate target.
        self.world_model = WorldModel(evidence_graph=self.evidence_graph)
        # HypothesisManager: stores hypotheses (needed by Planner and
        # Contradiction).
        self.hypothesis_manager = HypothesisManager(
            evidence_graph=self.evidence_graph,
            world_model=self.world_model,
        )
        # ContradictionManager: detects CONTRADICTS relationships.
        # Wired with evidence_graph, hypothesis_manager, world_model.
        self.contradiction_manager = ContradictionManager(
            evidence_graph=self.evidence_graph,
            hypothesis_manager=self.hypothesis_manager,
            world_model=self.world_model,
        )
        # Student: recording-only candidate generation. No learning,
        # no promotion, no P5 semantics.
        self.student = StudentCandidateGenerator()
        # Planner: produces PlanDecision from candidates. Wired with
        # the world, evidence, hypothesis, contradiction managers.
        # For the walking skeleton, the Planner's decide() is called
        # with a deterministic candidate set (the safe-proving request).
        from orchestrator.brain.action import ActionRegistry
        self.action_registry = ActionRegistry()
        self.planner = Planner(
            world=self.world_model,
            evidence_graph=self.evidence_graph,
            hypothesis_manager=self.hypothesis_manager,
            contradiction_manager=self.contradiction_manager,
            action_registry=self.action_registry,
            chain_synthesizer=None,
        )

    def record_observation(self, view: dict) -> None:
        """Record an observation into the evidence graph (for WorldModel)."""
        # Walking skeleton: record the view keys as evidence.
        from orchestrator.brain.evidence import Evidence
        from orchestrator.brain.trust import TrustLevel
        for key in view.get("view_keys", []):
            ev = Evidence(
                trust_level=TrustLevel.TOOL_OBSERVATION,
                source_detail="runtime.observe",
                raw_content=f"observed:{key}",
                description=f"runtime observed key {key}",
            )
            self.evidence_graph.add_evidence(ev)

    def record_integration(self, receipt_id: str) -> None:
        """Record a receipt into the evidence graph (for WorldModel)."""
        from orchestrator.brain.evidence import Evidence
        from orchestrator.brain.trust import TrustLevel
        ev = Evidence(
            trust_level=TrustLevel.TOOL_OBSERVATION,
            source_detail="runtime.receipt",
            raw_content=f"receipt:{receipt_id}",
            description=f"runtime integrated receipt {receipt_id}",
        )
        self.evidence_graph.add_evidence(ev)
