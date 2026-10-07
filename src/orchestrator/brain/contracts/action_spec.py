"""action_spec.py — PROPOSED declarative ActionSpec contract.

Why this exists
---------------
``Action`` today (src/orchestrator/brain/action.py:149) carries
``required_capabilities: list[str]`` (src/orchestrator/brain/action.py:187)
and free-form ``tags: list[str]`` (src/orchestrator/brain/action.py:192)
as its only declaration of what context it needs. Nothing declares the
*context projection* the action reads, so a cache of prior outcomes keyed
on "same action, same target" silently conflates attempts that ran against
genuinely different world state. That is the defect this module addresses:
retry and cache decisions are only correct when the key covers the
declared inputs, and there is currently no place to declare them.

The same class also pins the other gap: the receipt carries impact as a
bare string, ``impact_estimate: str = ""`` (src/orchestrator/hardening/action_receipt.py:82),
so two specs that differ in blast radius are not mechanically
distinguishable. ``impact_class`` and ``required_scope_predicates`` give
the planner a typed, checkable declaration to bind the receipt against.

``semantic_version_key`` exists so that any change in *meaning* — spec
version, declared dependencies, required scope predicates — changes the
key, while cosmetic changes do not. Bump ``spec_version`` when semantics
change; the key is derived, never hand-written.

This module is a contract proposal. Nothing in the runtime stage graph
imports it.

Schema version: 1
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum


class RetryDisposition(str, Enum):
    """What may be done about a failed attempt of this spec."""

    NEVER = "never"  # failure is terminal for this spec
    DEFER = "defer"  # retry later on a schedule, not now
    RETRY = "retry"  # immediate re-dispatch is admissible
    RETRY_IF_STATE_CHANGED = "retry_if_state_changed"  # only if declared dependencies moved


@dataclass(frozen=True)
class PredicateRef:
    """A reference to a declared predicate — not an assertion about it.

    Names a subject kind, a predicate, and a value kind. The predicate's
    truth is always supplied elsewhere by a registered verifier; this type
    only states that the predicate is *declared*.
    """

    subject_kind: str   # e.g. "service", "entity", "observation"
    predicate: str      # e.g. "listens_on", "resolved_to"
    value_kind: str = ""  # "" when the predicate is existential


@dataclass(frozen=True)
class ParameterSpec:
    """One declared input of an action."""

    name: str
    type_hint: str = "str"
    required: bool = True
    semantic_normalizer: str = ""  # id of a normalizer; "" means identity
    is_secret: bool = False       # True ⇒ value stored as an opaque ref, never in any key


@dataclass(frozen=True)
class ActionSpec:
    """Immutable, versioned declaration of one action."""

    spec_id: str
    spec_version: int = 1
    action_type: str = ""
    description: str = ""

    parameters: tuple = ()  # tuple[ParameterSpec, ...]
    causal_preconditions: tuple = ()  # tuple[PredicateRef, ...]
    expected_effects: tuple = ()  # tuple[PredicateRef, ...]

    # The declared context projection this action depends on. These names
    # are hashed into the failure-cache key (see identity.failure_key), so
    # an action whose behaviour changes with them MUST list them here.
    declared_dependencies: tuple = ()  # tuple[str, ...]

    verifier_id: str = ""  # registered verifier that may assess this spec's predicates
    retry_policy: RetryDisposition = RetryDisposition.RETRY_IF_STATE_CHANGED
    impact_class: str = ""  # e.g. "read_only", "mutating_local", "mutating_remote"
    required_scope_predicates: tuple = ()  # tuple[PredicateRef, ...]

    @property
    def semantic_version_key(self) -> str:
        """Stable string for cache keying.

        Covers spec identity, spec version, the declared dependency
        projection, the required scope predicates, the verifier id, the
        retry policy, the impact class, and the *names* (never values) of
        the declared parameters. Parameter values are deliberately absent:
        they belong to the attempt context, not to the spec.
        """
        payload = {
            "spec_id": self.spec_id,
            "spec_version": self.spec_version,
            "action_type": self.action_type,
            "declared_dependencies": list(self.declared_dependencies),
            "required_scope_predicates": [
                [p.subject_kind, p.predicate, p.value_kind]
                for p in self.required_scope_predicates
            ],
            "causal_preconditions": [
                [p.subject_kind, p.predicate, p.value_kind]
                for p in self.causal_preconditions
            ],
            "expected_effects": [
                [p.subject_kind, p.predicate, p.value_kind]
                for p in self.expected_effects
            ],
            "verifier_id": self.verifier_id,
            "retry_policy": self.retry_policy.value,
            "impact_class": self.impact_class,
            "parameter_names": [
                {"name": p.name, "required": p.required, "secret": p.is_secret}
                for p in self.parameters
            ],
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "spec_id": self.spec_id,
            "spec_version": self.spec_version,
            "action_type": self.action_type,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type_hint": p.type_hint,
                    "required": p.required,
                    "semantic_normalizer": p.semantic_normalizer,
                    "is_secret": p.is_secret,
                }
                for p in self.parameters
            ],
            "causal_preconditions": [
                {"subject_kind": p.subject_kind, "predicate": p.predicate, "value_kind": p.value_kind}
                for p in self.causal_preconditions
            ],
            "expected_effects": [
                {"subject_kind": p.subject_kind, "predicate": p.predicate, "value_kind": p.value_kind}
                for p in self.expected_effects
            ],
            "declared_dependencies": list(self.declared_dependencies),
            "verifier_id": self.verifier_id,
            "retry_policy": self.retry_policy.value,
            "impact_class": self.impact_class,
            "required_scope_predicates": [
                {"subject_kind": p.subject_kind, "predicate": p.predicate, "value_kind": p.value_kind}
                for p in self.required_scope_predicates
            ],
            "semantic_version_key": self.semantic_version_key,
        }
