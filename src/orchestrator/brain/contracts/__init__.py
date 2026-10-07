"""contracts/ — PROPOSED brain subsystem contracts.

These types are a specification layer, not a wired implementation. Nothing
in ``src/orchestrator/runtime/stages.py`` or
``src/orchestrator/runtime/loop.py`` imports this package, and importing
it changes no current behaviour. They exist so the missing brain
subsystems — outcomes, action specification, identity, goals — can be
written against a fixed contract rather than against whichever
single-enum shape happened to be in place.

The four problems they address, each cited at the module that names it:

* ``outcomes`` — a finished command is not semantic success. The existing
  flat ``ActionProposalStatus`` (src/orchestrator/hardening/action_receipt.py:28)
  has a terminal member ``SUCCEEDED`` and a free-text ``result`` field
  (src/orchestrator/hardening/action_receipt.py:103), so semantic truth is
  unrecoverable from a receipt.
* ``action_spec`` — no declared context projection, so failure-cache keys
  cannot be correct. ``Action`` lists capabilities
  (src/orchestrator/brain/action.py:187) and tags
  (src/orchestrator/brain/action.py:192) but not what it depends on.
* ``identity`` — ``f"pid:{pid}"`` (src/orchestrator/brain/world.py:1271) is
  not unique across hosts, and a fresh ``action_id`` per proposal
  (src/orchestrator/brain/action.py:157) cannot distinguish a retry of the
  same intended operation from a new operation.
* ``goal`` — no goal type with an evidence-gated completion rule; an LLM
  assertion of "done" is currently indistinguishable from a verified fact.

Schema version: 1
"""

from __future__ import annotations

from orchestrator.brain.contracts.action_spec import (
    ActionSpec,
    ParameterSpec,
    PredicateRef,
    RetryDisposition,
)
from orchestrator.brain.contracts.goal import (
    Goal,
    GoalEvaluation,
    GoalPredicate,
    GoalStatus,
)
from orchestrator.brain.contracts.identity import (
    ActionKey,
    AttemptContext,
    ExecutionIdentity,
    FailureRecord,
    failure_key,
    make_process_identifier,
)
from orchestrator.brain.contracts.outcomes import (
    NO_COVERAGE_UNKNOWN,
    ActionOutcome,
    ExecutionStatus,
    GoalProgress,
    PredicateAssessment,
    PredicateResult,
    StageExecution,
    InputDisposition,
    IntegrationEffect,
    StageReport,
)
from orchestrator.brain.contracts.observation import Observation



__all__ = [
    # outcomes
    "ExecutionStatus",
    "PredicateAssessment",
    "GoalProgress",
    "PredicateResult",
    "ActionOutcome",
    "NO_COVERAGE_UNKNOWN",
    # outcomes — stage-level four-layer split (v1.1)
    "StageExecution",
    "InputDisposition",
    "IntegrationEffect",
    "StageReport",
    # observation (v1.1)
    "Observation",
    # action_spec
    "ActionSpec",
    "ParameterSpec",
    "RetryDisposition",
    "PredicateRef",
    # identity
    "AttemptContext",
    "ActionKey",
    "ExecutionIdentity",
    "FailureRecord",
    "failure_key",
    "make_process_identifier",
    # goal
    "GoalPredicate",
    "Goal",
    "GoalStatus",
    "GoalEvaluation",
]
