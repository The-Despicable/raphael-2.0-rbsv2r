"""outcomes.py — PROPOSED three-layer outcome split for action results.

Why this exists
---------------
The only structured outcome type in the tree today is
``ActionProposalStatus`` (src/orchestrator/hardening/action_receipt.py:28),
a single flat enum whose members mix three unrelated semantic levels:

* authorization  — DENIED
* execution       — NOT_STARTED, STARTED, FINISHED-by-``SUCCEEDED``/``FAILED``
* semantic truth — nothing

and whose terminal member is literally ``SUCCEEDED``
(src/orchestrator/hardening/action_receipt.py:34). The receipt that
carries it also stores the semantic result as free text:
``result: str = ""`` (src/orchestrator/hardening/action_receipt.py:103),
and expresses impact as an uninterpreted string
``impact_estimate: str = ""`` (src/orchestrator/hardening/action_receipt.py:82).
That is the defect this module addresses: a caller that reads a receipt
can mechanically learn that a process ran, but cannot mechanically learn
whether the thing it cared about is true — and ``SUCCEEDED`` invites
exactly that conflation.

The three layers below are therefore *not* alternatives at one semantic
level, and are not collapsed into one enum:

``ExecutionStatus``    — only asks whether the process was run.
                         Writer: the broker/executor adapter, and nobody else.
``PredicateAssessment``— asks what is true about declared predicates.
                         Writer: a registered verifier, and nobody else.
``GoalProgress``       — asks whether the goal moved.
                         Writer: the controller, and nobody else.

This module is a contract proposal. It is not imported by
src/orchestrator/runtime/stages.py or src/orchestrator/runtime/loop.py
and changes no current behaviour.

Negative results and coverage
-----------------------------
A negative result without a declared coverage contract is
``PredicateAssessment.UNKNOWN``, never ``REFUTED``.

Refutation is a claim about the world ("the port is closed"). A negative
observation with no declared coverage is a claim about the *observation
procedure* ("my probe saw nothing"), and those are different claims.
``NO_COVERAGE_UNKNOWN`` names that case explicitly so callers cannot
silently promote a blind spot into a refutation.

Note the parallel with the defeater vocabulary already in the tree:
``DefeaterOutcome`` (src/orchestrator/brain/defeater_types.py:34) already
separates ``INCONCLUSIVE`` from ``TRIGGERED`` for the same reason.

Failure classes
---------------
``failure_class`` is a free string on purpose, mirroring the mechanical,
never-reclassified class constants already used by the transport layer
(FAILURE_CLASS_RATE_LIMIT, FAILURE_CLASS_SERVER, FAILURE_CLASS_TIMEOUT,
FAILURE_CLASS_CONNECTION, FAILURE_CLASS_CLIENT and ``RETRYABLE_CLASSES`` at
src/arena/llm_transport.py:56-68). The outcome layer records the class
verbatim; it does not interpret it and does not own the retry decision.

Schema version: 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Sentinel recorded in ``ActionOutcome.notes`` (and by convention in
# ``evidence_ids`` provenance) when a predicate came back negative purely
# because no coverage contract was declared for it.
NO_COVERAGE_UNKNOWN = "no_coverage_unknown"


class ExecutionStatus(str, Enum):
    """Did the process run? Writer: broker/executor adapter only.

    Establishes only that the process was or was not run. It never says
    anything about the predicates the action was meant to establish.

    """

    DENIED = "denied"                        # never dispatched, by policy
    NOT_STARTED = "not_started"              # dispatchable, but not dispatched
    FINISHED = "finished"                    # process exited (any exit code)
    TIMEOUT = "timeout"                      # process killed on deadline
    TRANSPORT_ERROR = "transport_error"      # never reached the target at all
    UNKNOWN_EXECUTION = "unknown_execution"  # we cannot tell; do not guess


class PredicateAssessment(str, Enum):
    """What is true about one declared predicate? Writer: a registered verifier.

    Always carries evidence references; an assessment with no evidence is
    ``UNKNOWN``, not ``ESTABLISHED`` and not ``REFUTED``.
    """

    ESTABLISHED = "established"
    REFUTED = "refuted"
    UNKNOWN = "unknown"
    DISPUTED = "disputed"  # two verifiers disagree; unresolved


class GoalProgress(str, Enum):
    """Did the goal move? Writer: the controller only."""

    COMPLETE = "complete"                        # every required predicate established
    PARTIAL = "partial"                          # some required predicate established
    NO_VERIFIED_PROGRESS = "no_verified_progress"  # nothing established, goal may still hold
    BLOCKED = "blocked"                          # goal cannot be advanced under current scope


@dataclass(frozen=True)
class PredicateResult:
    """One verifier's assessment of one declared predicate."""

    predicate_id: str
    assessment: PredicateAssessment
    evidence_ids: tuple = ()   # provenance; MUST be non-empty for ESTABLISHED/REFUTED
    assessed_by: str = ""      # registered verifier id
    assessed_at: float = field(default_factory=time.time)
    detail: str = ""


@dataclass(frozen=True)
class ActionOutcome:
    """Three-layer result of one action attempt.

    INVARIANT: a finished command is not semantic success;
    ``ExecutionStatus.FINISHED`` does not imply
    ``PredicateAssessment.ESTABLISHED``. A process can exit 0 while every
    predicate it was supposed to establish comes back UNKNOWN or REFUTED,
    and that is the common case, not an edge case.

    Second invariant: a negative result carrying no declared coverage
    contract is UNKNOWN, never REFUTED (see module docstring; the case is
    named by ``NO_COVERAGE_UNKNOWN``).

    ``goal_progress`` is written by the controller alone. A verifier or an
    executor filling this field in is a contract violation.
    """

    action_id: str
    execution_status: ExecutionStatus
    predicate_assessments: tuple = ()   # tuple[PredicateResult, ...]
    goal_progress: GoalProgress = GoalProgress.NO_VERIFIED_PROGRESS
    failure_class: str = ""            # "" when this is not a failure
    evidence_ids: tuple = ()
    assessed_by: str = ""
    assessed_at: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> dict:
        """Plain-dict form. ``notes`` is preserved verbatim; no free text is
        dropped and no value is reinterpreted."""
        assessments: list[dict[str, Any]] = []
        for result in self.predicate_assessments:
            assessments.append(
                {
                    "predicate_id": result.predicate_id,
                    "assessment": result.assessment.value,
                    "evidence_ids": list(result.evidence_ids),
                    "assessed_by": result.assessed_by,
                    "assessed_at": result.assessed_at,
                    "detail": result.detail,
                }
            )
        return {
            "action_id": self.action_id,
            "execution_status": self.execution_status.value,
            "predicate_assessments": assessments,
            "goal_progress": self.goal_progress.value,
            "failure_class": self.failure_class,
            "evidence_ids": list(self.evidence_ids),
            "assessed_by": self.assessed_by,
            "assessed_at": self.assessed_at,
            "notes": self.notes,
        }

    def is_semantic_success(self) -> bool:
        """True only when at least one predicate is ESTABLISHED *and* at
        none is DISPUTED. Execution status alone never satisfies this."""
        if self.execution_status is not ExecutionStatus.FINISHED:
            return False
        if any(
            r.assessment is PredicateAssessment.DISPUTED
            for r in self.predicate_assessments
        ):
            return False
        return any(
            r.assessment is PredicateAssessment.ESTABLISHED
            for r in self.predicate_assessments
        )


# ══════════════════════════════════════════════════════════════════════
# STAGE-LEVEL FOUR-LAYER SEMANTICS (v1.1)
# ══════════════════════════════════════════════════════════════════════
#
# The three enums above describe ONE action's result. A stage does more than
# that: it runs a protocol, interprets input, mutates state, and asks a verifier
# a question. Those are four different claims with four different owners, and a
# single ``effect_status`` conflates them. Concretely, an observation can
# confirm an ALREADY-KNOWN fact (an assessment, no state delta), and a belief
# can be updated without being goal-relevant. One field cannot carry both.
#
# v1.1 retraction: an earlier draft of this module asserted
#     ESTABLISHED => state_delta_refs != []
# That is FALSE. Confirming a known fact yields qualifying evidence with an
# empty state delta. The correct invariants are enforced in StageReport below.


class StageExecution(str, Enum):
    """Did the stage's protocol run? Writer: the stage handler only."""

    COMPLETED = "completed"  # protocol ran to completion
    FAILED = "failed"        # exception, or durable write did not commit


class InputDisposition(str, Enum):
    """Was the input interpretable? Writer: the reducer/adapter only.

    ABSENT and UNSUPPORTED are the two members that must never produce a
    predicate assessment: there is nothing to assess.
    """

    SUPPORTED_PARSED = "supported_parsed"        # adapter understood it
    SUPPORTED_PARSE_FAILED = "supported_parse_failed"  # known shape, content unparseable
    UNSUPPORTED = "unsupported"                  # no adapter for this shape
    ABSENT = "absent"                            # nothing to interpret at all


class IntegrationEffect(str, Enum):
    """Did belief state change? Writer: the world-model writer only.

    Deliberately NOT named "effect": NO_EFFECT was withdrawn because it does
    not say what failed to change.
    """

    BELIEFS_UPDATED = "beliefs_updated"
    NO_BELIEF_UPDATE = "no_belief_update"
    INTEGRATION_FAILED = "integration_failed"


@dataclass(frozen=True)
class StageReport:
    """A stage's outcome across four distinct semantic layers.

    Invariants enforced at construction (see __post_init__):

        BELIEFS_UPDATED            => state_delta_refs is non-empty
        INPUT_DISPOSITION in (ABSENT, UNSUPPORTED)
                                   => predicate_assessments is empty
        INTEGRATION_FAILED         => no ESTABLISHED assessment may be emitted

    Explicitly NOT enforced, and deliberately so:

        STAGE_COMPLETED does NOT imply predicate_established. That is the whole
        point of the split, and asserting it here would re-collapse the layers.
    """

    stage_name: str = ""
    execution_status: StageExecution = StageExecution.COMPLETED
    input_disposition: InputDisposition = InputDisposition.ABSENT
    integration_effect: IntegrationEffect = IntegrationEffect.NO_BELIEF_UPDATE

    produced_artifact_refs: tuple = ()
    state_delta_refs: tuple = ()
    predicate_assessments: tuple = ()   # tuple[PredicateResult, ...]
    limitations: tuple = ()
    reported_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.integration_effect is IntegrationEffect.BELIEFS_UPDATED:
            if not self.state_delta_refs:
                raise ValueError(
                    "BELIEFS_UPDATED requires at least one state_delta_ref; "
                    "a belief changed, so there must be a record of what changed"
                )
        if self.input_disposition in (
            InputDisposition.ABSENT,
            InputDisposition.UNSUPPORTED,
        ):
            if self.predicate_assessments:
                raise ValueError(
                    f"{self.input_disposition.value} input cannot yield a "
                    "predicate assessment; there is nothing to assess"
                )
        if self.execution_status is StageExecution.FAILED:
            if any(
                r.assessment is PredicateAssessment.ESTABLISHED
                for r in self.predicate_assessments
            ):
                raise ValueError(
                    "a FAILED stage cannot emit an ESTABLISHED assessment"
                )

    def is_semantic_success(self) -> bool:
        """Strict: a stage succeeded AND established something verifiable.

        Note this is deliberately narrower than "the stage ran". Use
        ``established_predicates`` to inspect the assessment layer directly.
        """
        return (
            self.execution_status is StageExecution.COMPLETED
            and bool(self.predicate_assessments)
            and any(
                r.assessment is PredicateAssessment.ESTABLISHED
                for r in self.predicate_assessments
            )
        )

    def established_predicates(self) -> tuple:
        return tuple(
            r.predicate_id
            for r in self.predicate_assessments
            if r.assessment is PredicateAssessment.ESTABLISHED
        )

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "execution_status": self.execution_status.value,
            "input_disposition": self.input_disposition.value,
            "integration_effect": self.integration_effect.value,
            "produced_artifact_refs": list(self.produced_artifact_refs),
            "state_delta_refs": list(self.state_delta_refs),
            "predicate_assessments": [
                {
                    "predicate_id": r.predicate_id,
                    "assessment": r.assessment.value,
                    "evidence_ids": list(r.evidence_ids),
                    "assessed_by": r.assessed_by,
                }
                for r in self.predicate_assessments
            ],
            "limitations": list(self.limitations),
            "reported_at": self.reported_at,
        }
