"""observation.py — PROPOSED typed observation contract.

Why this exists
---------------
An assessment cannot qualify as evidence without knowing *where it came from*
and *how long it holds*. Both are already modelled in the tree and neither is
reachable from a receipt:

* ``TrustLevel`` (src/orchestrator/brain/trust.py:43) already distinguishes
  seven provenance channels — including ``TARGET_CONTROLLED`` and
  ``MODEL_INFERENCE`` — but ``WorldModel`` imports it (src/orchestrator/brain/world.py:42)
  and never reads it. Today every observation is implicitly a tool reading.
* ``Entity.first_seen``/``last_seen`` (src/orchestrator/brain/world.py:116-117)
  and ``Relationship.expires_at`` (src/orchestrator/brain/world.py:157) exist,
  but nothing decays and nothing invalidates a stale claim on new evidence.

So the two properties an assessment needs — provenance and validity — have no
carrier. This module supplies one.

Two rules this type enforces
----------------------------
1. **Provenance is a channel, not a label.** ``provenance_channel`` is a
   ``TrustLevel`` value. An observation whose channel is ``MODEL_INFERENCE`` is
   a *proposal about* an observation, not evidence, and must not satisfy a
   predicate on its own.
2. **Absence is not refutation.** ``coverage_contract_ref`` is required before
   any consumer may treat "nothing was seen" as evidence that something is not
   the case. With no coverage contract the correct assessment is ``UNKNOWN``.

Identity
--------
``subject_ref`` must be a *canonical, namespace-qualified* identity, not a
bare value. See ``identity.make_process_identifier``; a bare ``pid`` is not
unique across hosts, which is why ``create_process`` at
src/orchestrator/brain/world.py:1271 cannot be trusted as an identity source.

Schema version: 1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from orchestrator.brain.trust import TrustLevel

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Observation:
    """A typed, provenance-bearing reading. Not yet a belief.

    An observation records what a reading *said*. Whether it is true is the
    business of a verifier (``PredicateAssessment``), and whether it changes
    anything is the business of the belief store (``IntegrationEffect``).
    """

    schema_version: int = SCHEMA_VERSION
    observation_id: str = ""

    # Binding
    execution_id: str = ""       # ties to ExecutionIdentity, never a raw receipt id
    subject_ref: str = ""        # canonical, namespace-qualified identity

    # Content
    predicate: str = ""
    value: str = ""

    # Provenance and validity
    provenance_channel: str = ""        # a TrustLevel value; see _validate_channel
    observed_at: float = field(default_factory=time.time)
    validity_interval: tuple = ()      # (not_before, not_after); () means not expired
    extractor_version: str = ""        # the parser that produced this, for invalidation

    # Sources
    source_artifact_ref: str = ""      # raw output is referenced, never inlined
    coverage_contract_ref: str = ""    # required before any negative conclusion

    def _validate_channel(self) -> None:
        if not self.provenance_channel:
            raise ValueError("Observation requires an explicit provenance_channel")
        try:
            TrustLevel(self.provenance_channel)
        except ValueError as exc:
            raise ValueError(
                f"provenance_channel {self.provenance_channel!r} is not a TrustLevel; "
                "expected one of: "
                + ", ".join(sorted(m.value for m in TrustLevel))
            ) from exc

    def _validate_validity(self) -> None:
        if not self.validity_interval:
            return
        if len(self.validity_interval) != 2:
            raise ValueError(
                "validity_interval must be (not_before, not_after) or empty"
            )
        not_before, not_after = self.validity_interval
        if not_before > not_after:
            raise ValueError("validity_interval is inverted: not_before > not_after")

    def __post_init__(self) -> None:
        self._validate_channel()
        self._validate_validity()

    # ── provenance helpers ───────────────────────────────────────────

    def is_model_inference(self) -> bool:
        """True when this is a claim about the world, not a reading of it."""
        return self.provenance_channel == TrustLevel.MODEL_INFERENCE.value

    def is_target_controlled(self) -> bool:
        """True when the value came from the target, so it is untrusted input."""
        return self.provenance_channel == TrustLevel.TARGET_CONTROLLED.value

    def qualifies_as_evidence(self) -> bool:
        """May this observation support an ESTABLISHED/REFUTED assessment?

        Model inference never qualifies on its own: it is a proposal that needs
        corroboration or a validated contract. Everything else does, provided it
        carries an extractor version we can invalidate against.
        """
        if self.is_model_inference():
            return False
        return bool(self.extractor_version)

    def supports_negative_conclusion(self) -> bool:
        """May a consumer treat this as evidence that something is NOT the case?

        Only with a declared coverage contract. Per the module docstring: a
        negative reading with no coverage is a claim about the observation
        procedure, not about the world.
        """
        return bool(self.coverage_contract_ref)

    def is_expired(self, now: float | None = None) -> bool:
        """Whether the validity window has closed. Empty window ⇒ never expired."""
        if not self.validity_interval:
            return False
        _, not_after = self.validity_interval
        return (time.time() if now is None else now) > not_after

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "execution_id": self.execution_id,
            "subject_ref": self.subject_ref,
            "predicate": self.predicate,
            "value": self.value,
            "provenance_channel": self.provenance_channel,
            "observed_at": self.observed_at,
            "validity_interval": list(self.validity_interval),
            "extractor_version": self.extractor_version,
            "source_artifact_ref": self.source_artifact_ref,
            "coverage_contract_ref": self.coverage_contract_ref,
        }
