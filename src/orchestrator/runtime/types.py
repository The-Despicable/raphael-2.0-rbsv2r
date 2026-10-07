"""
types.py — Runtime type contracts (P2.1 walking skeleton)

Per v4 §13.2: at minimum, define conceptual contracts for:
- RuntimeContext
- MissionContext
- StageResult
- ActionRequest
- PolicyDecision
- ExecutionEvent
- EvidenceReceipt
- LoopTermination

These are the data shapes the Runtime sequencer passes between stages.
They are intentionally narrow and stable. Brain organs return these;
the Runtime emits them in the DecisionTrace.

No domain logic. No policy logic. No primitives.
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List, TYPE_CHECKING
import time
import uuid

if TYPE_CHECKING:
    from orchestrator.runtime.scope import ScopeV0


# ── RSI-1 Fix B: canonical D2 engagement identity ─────────────────────────
#
# The five-step maximum for the approved D2 engagement is a PROPERTY of that
# engagement, not a value the caller supplies. Recognition therefore must not
# rest on a single caller-controlled field: a policy artifact (or a
# hand-constructed BrokerPolicy) that merely renames itself must not escape the
# bound, and one that never claims the name must still be recognised when it
# IS the approved scope.
#
# These are the canonical, structurally-verifiable facts of the approved D2
# engagement (policies/engagement-d2-v1.json). Pure data + pure functions: no
# I/O, no policy evaluation, no primitives.
D2_ENGAGEMENT_ID = "d2-bounded-episode"
D2_APPROVED_MAX_EPISODE_STEPS = 5
D2_CANONICAL_ACTION_TYPES = frozenset({"recon_service_probe", "lab_http_probe"})
D2_CANONICAL_CAPABILITIES = frozenset({"exec.d1_lab_probe", "exec.http_probe"})
D2_CANONICAL_LAB_IDENTITY = {
    "compose_project": "raphael-m1",
    "target_service": "dvwa",
    "target_image_prefix": "vulnerables/web-dvwa",
    "probe_container": "kali-tools",
    "probe_tool": "nmap",
}
# The declared policy_name prefix is retained as ONE recognition signal, never
# as the sole one (a rename must not escape the invariant, and a renamed D2
# copy must not escape it either).
D2_POLICY_NAME_PREFIX = "engagement-d2"


def lab_contract_matches_d2(lab: Any) -> bool:
    """True when a validated ``scope.lab`` block IS the approved D2 lab."""
    if not isinstance(lab, dict):
        return False
    for key, expected in D2_CANONICAL_LAB_IDENTITY.items():
        if str(lab.get(key, "")) != str(expected):
            return False
    http = lab.get("http")
    if not isinstance(http, dict):
        return False
    return (http.get("host") == D2_CANONICAL_LAB_IDENTITY["target_service"]
            and http.get("method") == "GET"
            and http.get("max_redirects") == 0)


def is_canonical_d2_scope(engagement_id: str = "", action_types: Any = (),
                          capabilities: Any = (), lab: Any = None,
                          policy_name: str = "") -> bool:
    """Recognise the approved D2 engagement from validated scope facts.

    Any ONE independent canonical signal is sufficient, so no single renamed
    or omitted field can escape recognition:

    - the canonical engagement id;
    - the full canonical capability vocabulary AND action-type vocabulary;
    - the canonical validated lab contract (target image, probe tool, fixed
      in-container HTTP destination).

    Every signal is compared against canonical constants, never against a
    caller-declared maximum.
    """
    if str(engagement_id or "") == D2_ENGAGEMENT_ID:
        return True
    try:
        acts = frozenset(str(a) for a in action_types or ())
        caps = frozenset(str(c) for c in capabilities or ())
    except TypeError:
        return False
    if D2_CANONICAL_ACTION_TYPES <= acts and D2_CANONICAL_CAPABILITIES <= caps:
        return True
    if lab_contract_matches_d2(lab):
        return True
    return str(policy_name or "").startswith(D2_POLICY_NAME_PREFIX)


def broker_policy_is_d2(policy: Any) -> bool:
    """Recognise D2 from a BrokerPolicy (the shape the Runtime holds).

    A BrokerPolicy carries no lab block, so recognition uses the remaining
    independent canonical signals: engagement id, the full capability/action
    vocabulary, and the declared name prefix.
    """
    if policy is None:
        return False
    return is_canonical_d2_scope(
        engagement_id=str(getattr(policy, "engagement_id", "") or ""),
        action_types=getattr(policy, "allowed_action_types", ()) or (),
        capabilities=getattr(policy, "allowed_capabilities", ()) or (),
        policy_name=str(getattr(policy, "policy_name", "") or ""),
    )


# ── RSI-1 B-1: canonical capability-governance registry ────────────────────
#
# ROOT CAUSE OF THE B-1 ESCAPE. The D2 ceiling was attached to POLICY IDENTITY
# (declared name, engagement id, capability/action vocabulary, lab contract).
# Every one of those is a mutable field of a JSON file or a constructor call.
# An attacker who removed or narrowed all four reclassified a still-protected
# capability as "not D2", so ``broker_policy_is_d2()`` went False, the ceiling
# became 0, and the approved DVWA nmap probe ran unbounded (6/9/12 governed
# steps in the final independent audit).
#
# THE FIX INVERTS THE DIRECTION OF TRUST. This registry — held by the Runtime
# itself, not by any policy — declares which capabilities are PROTECTED and
# which governed contract governs each. A policy artifact, a constructor
# keyword, or a request field cannot add to it, remove from it, or re-point it.
# Recognition heuristics above are still used, but they can only ever make the
# ceiling STRICTER or trigger a refusal; they can never grant an unbounded
# fallback, because "no contract recognised" is now a REFUSAL for a protected
# capability rather than an absence of a limit.

D1_ENGAGEMENT_ID = "d1-governed-action"
D1_POLICY_NAME_PREFIX = "engagement-d1"
D1_CANONICAL_CAPABILITY = "exec.d1_lab_probe"

# Protected capabilities: the approved bounded-lab execution contract. These
# may only execute under a RECOGNISED governed engagement contract.
PROTECTED_GOVERNED_CAPABILITIES = frozenset(D2_CANONICAL_CAPABILITIES)

# The single authoritative statement of every governed engagement's episode
# ceiling. Nothing else in the codebase declares "5" for D2: the loader
# validates the artifact against this table's entry, and the Runtime enforces
# this table's entry at the PEP boundary regardless of what the artifact says.
# D1 is operator-approved with NO episode ceiling; that is preserved verbatim.
GOVERNED_ENGAGEMENT_CONTRACTS = {
    D2_ENGAGEMENT_ID: {
        "max_episode_steps": D2_APPROVED_MAX_EPISODE_STEPS,
        "capabilities": PROTECTED_GOVERNED_CAPABILITIES,
    },
    D1_ENGAGEMENT_ID: {
        "max_episode_steps": 0,
        "capabilities": frozenset({D1_CANONICAL_CAPABILITY}),
    },
}


def _policy_capabilities(policy: Any) -> frozenset:
    try:
        return frozenset(str(c) for c in getattr(policy, "allowed_capabilities", ()) or ())
    except TypeError:
        return frozenset()


def policy_authorises_protected_capability(policy: Any) -> bool:
    """True when the policy would let a PROTECTED capability execute."""
    return bool(_policy_capabilities(policy) & PROTECTED_GOVERNED_CAPABILITIES)


def is_recognised_d1_scope(policy: Any) -> bool:
    """Recognise the approved D1 contract.

    D1 must stay uncapped and must not be swept into the D2 ceiling, so it is
    recognised narrowly: the canonical D1 identity (exact engagement id or the
    canonical name prefix) AND a capability surface that is exactly the single
    governed D1 probe. Anything broader is not D1 and falls through to the
    D2 recogniser or, failing that, to a refusal.
    """
    if policy is None:
        return False
    identity = (str(getattr(policy, "engagement_id", "") or "").startswith(D1_ENGAGEMENT_ID)
                or str(getattr(policy, "policy_name", "") or "").startswith(D1_POLICY_NAME_PREFIX))
    if not identity:
        return False
    caps = _policy_capabilities(policy)
    return bool(caps) and caps <= PROTECTED_GOVERNED_CAPABILITIES


@dataclass(frozen=True)
class CapabilityGovernance:
    """Resolved governance decision for one Runtime's execution boundary.

    ``contract_id`` is the canonical governed contract in force ("" = none).
    ``ceiling`` is the authoritative governed-step maximum from
    ``GOVERNED_ENGAGEMENT_CONTRACTS`` (0 = that contract declares none).
    ``refuses_protected_capability`` is the B-1 fail-closed switch: a protected
    capability may not execute at all under an unrecognised contract.
    ``contract_capabilities`` is the contract's CLOSED canonical capability set.

    RSI-1 C-1: a recognised contract must authorise BOTH the policy AND the exact
    capability OBJECT being executed. ``contract_capabilities`` carries the
    closed set so ``permits_object_identity`` can decide membership from the
    object's own canonical identity rather than from any caller-controlled name.
    """

    contract_id: str = ""
    ceiling: int = 0
    refuses_protected_capability: bool = False
    reason: str = ""
    contract_capabilities: frozenset = frozenset()

    def permits_object_identity(self, object_identity: Any) -> tuple:
        """Does this contract authorise the capability OBJECT about to execute?

        RSI-1 C-1 decisive fix. ``object_identity`` is the canonical governed
        identity of the ACTUAL dispatched object
        (``exec.capability_governance.governed_capability_identity``), never a
        registry key, request field, or policy label.

        Returns ``(permitted, reason)``. DENY-BY-DEFAULT under a recognised
        contract: a contract's capability set is closed, so anything not
        provably a member is refused. Consequently a D1 contract can never
        authorise ``exec.http_probe``, and a capability class the exec-owned
        registry does not recognise cannot be claimed as a member.
        """
        try:
            identity = frozenset(str(n) for n in (object_identity or ()))
        except TypeError:
            identity = frozenset()
        if not self.contract_id:
            # No recognised contract. A protected object is already refused by
            # rule 3; a non-protected object is governed by the policy + Broker.
            if identity:
                return False, ("§governance fail-closed: a protected capability "
                               + ", ".join(sorted(identity))
                               + " requires a recognised governed engagement contract")
            return True, "no governed contract; policy vocabulary governs this capability"
        if not identity:
            # Deny-by-default: the capability class is not a recognised governed
            # capability, so it cannot be a member of this contract's closed set.
            return False, ("§governance deny-by-default: the "
                           + self.contract_id + " contract authorises exactly "
                           + ", ".join(sorted(self.contract_capabilities))
                           + "; the dispatched capability class is not a "
                             "recognised governed capability")
        outside = identity - self.contract_capabilities
        if outside:
            return False, ("§governance fail-closed: protected capability "
                           + ", ".join(sorted(outside))
                           + " is NOT authorised by the " + self.contract_id
                           + " contract (authorised: "
                           + ", ".join(sorted(self.contract_capabilities)) + ")")
        return True, (self.contract_id + " contract authorises "
                      + ", ".join(sorted(identity)))


def resolve_capability_governance(policy: Any,
                                  extra_protected: Any = frozenset()) -> CapabilityGovernance:
    """Resolve the governed execution contract for a BrokerPolicy.

    Precedence — recognition may only ever tighten:

    1. Approved D2 contract  -> ceiling 5 from the registry.
    2. Approved D1 contract  -> ceiling 0 from the registry (D1 unchanged).
    3. Policy grants a PROTECTED capability but matches no governed contract
       -> FAIL CLOSED: the capability is refused at the PEP boundary. This is
       the B-1 fix: deleting identity metadata can no longer buy an unbounded
       fallback, it only removes authorisation.
    4. No protected capability -> legacy behaviour, the artifact's own
       declared cap (bootstrap/fixture.inspect paths are untouched).

    RSI-1 C-1: ``extra_protected`` carries the canonical governed identity
    DERIVED FROM THE CAPABILITY OBJECTS this execution would actually invoke
    (``orchestrator.exec.capability_governance.governed_capability_
    identity``), so a protected object exposed under any name — an alias, a
    re-keyed registry, or the bare default capability — triggers rule 3
    exactly as its canonical name would. ``extra_protected`` can only ever
    TRIGGER the fail-closed refusal; it can never manufacture a D1 or D2
    contract, raise a ceiling, or otherwise loosen recognition.
    """
    if broker_policy_is_d2(policy):
        spec = GOVERNED_ENGAGEMENT_CONTRACTS[D2_ENGAGEMENT_ID]
        return CapabilityGovernance(
            contract_id=D2_ENGAGEMENT_ID,
            ceiling=int(spec["max_episode_steps"]),
            refuses_protected_capability=False,
            reason="approved D2 contract in force",
            contract_capabilities=frozenset(spec["capabilities"]),
        )
    if is_recognised_d1_scope(policy):
        spec = GOVERNED_ENGAGEMENT_CONTRACTS[D1_ENGAGEMENT_ID]
        return CapabilityGovernance(
            contract_id=D1_ENGAGEMENT_ID,
            ceiling=int(spec["max_episode_steps"]),
            refuses_protected_capability=False,
            reason="approved D1 contract in force (no episode ceiling)",
            contract_capabilities=frozenset(spec["capabilities"]),
        )
    try:
        object_protected = frozenset(str(n) for n in (extra_protected or ()))
    except TypeError:
        object_protected = frozenset()
    object_protected &= PROTECTED_GOVERNED_CAPABILITIES
    policy_protected = _policy_capabilities(policy) & PROTECTED_GOVERNED_CAPABILITIES
    if policy_protected or object_protected:
        return CapabilityGovernance(
            contract_id="",
            ceiling=0,
            refuses_protected_capability=True,
            reason=("§governance fail-closed: this execution grants a protected "
                    "capability ("
                    + ", ".join(sorted(policy_protected | object_protected))
                    + ") but matches no recognised governed engagement contract; "
                      "a protected capability may not execute without one"),
        )
    try:
        declared = int(getattr(policy, "max_episode_steps", 0) or 0)
    except (TypeError, ValueError):
        declared = 0
    return CapabilityGovernance(
        contract_id="",
        ceiling=max(0, declared),
        refuses_protected_capability=False,
        reason="no protected capability; policy-declared budget applies",
    )


class BudgetResetRefused(RuntimeError):
    """An attempt to rewind an active episode's governed-step budget.

    Raised instead of silently rewinding. The active counter is bound to the
    Runtime's episode lifecycle; only a real episode boundary (which mints a
    NEW budget generation) may start a fresh allowance.
    """


class EpisodeBudgetSeal:
    """Opaque per-episode seal carried by a governed-step budget.

    Identity-compared (``is``), never value-compared, and never constructible
    by a caller who has not been handed the instance. Its purpose is to make an
    episode's budget distinguishable from any forged or stale substitute.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "<EpisodeBudgetSeal>"


def _coerce_ceiling(value) -> int:
    """Coerce a ceiling to a non-negative int (malformed -> 0)."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


class GovernedStepBudget:
    """Per-episode governed-step ceiling enforced AT the PEP boundary.

    RSI-1 Fix B: the iteration clamp in the Runtime bounds how many cognitive
    iterations run, but the INVARIANT is about governed steps actually reaching
    the PEP. This counter is therefore consumed inside the PEP stage, before
    the Broker receipt is started, so the bound holds for every entry path
    (``run_episode``, a bare ``step()`` loop, or any future driver) rather than
    only for the clamp.

    ``ceiling == 0`` means the engagement declares no governed-step maximum and
    the counter is inert (D1 and bootstrap behaviour unchanged).

    RSI-1 FINAL BLOCKER — STRUCTURAL EPISODE BINDING. Within one active episode
    the counter is strictly monotonic and cannot be rewound by any caller:

    * ``__slots__`` means there is no instance ``__dict__`` to edit.
    * The counter lives in a closure cell created at construction. It is not
      stored as any attribute, so there is no ``_used``-style field to zero and
      no ``_read``/``_advance`` hook to replace — the security boundary is the
      object's own structure, not a private NAME.
    * ``__setattr__`` freezes every attribute once construction completes;
      only ``ceiling`` stays writable (the PEP repairs a tampered ceiling to the
      registry figure before consuming). ``__delattr__`` always refuses.
    * There is NO in-place reset. ``reset()`` raises ``BudgetResetRefused``.
      The legitimate episode transition is
      :meth:`next_episode`, which mints a NEW budget with a strictly greater
      ``generation``; the Runtime re-binds it to the Broker, so a stale budget
      left over from the previous episode is inert by identity.
    """

    __slots__ = ("_frozen", "_ceiling", "_generation", "_seal", "_read", "_advance")

    #: The only attribute assignable after construction.
    _WRITABLE_AFTER_INIT = frozenset({"ceiling"})

    def __init__(self, ceiling: int = 0, generation: int = 0):
        cell = {"used": 0}

        def _read() -> int:
            return int(cell["used"])

        def _advance() -> bool:
            cap = self._ceiling
            if cap <= 0:
                return True                      # contract declares no bound
            if int(cell["used"]) >= cap:
                return False                     # exhausted (fail closed)
            cell["used"] = int(cell["used"]) + 1
            return True

        object.__setattr__(self, "_frozen", False)
        object.__setattr__(self, "_read", _read)
        object.__setattr__(self, "_advance", _advance)
        object.__setattr__(self, "_seal", EpisodeBudgetSeal())
        try:
            object.__setattr__(self, "_generation", int(generation))
        except (TypeError, ValueError):
            object.__setattr__(self, "_generation", 0)
        object.__setattr__(self, "_ceiling", _coerce_ceiling(ceiling))
        object.__setattr__(self, "_frozen", True)   # freeze: see __setattr__

    # ── freeze guards ────────────────────────────────────────────────────

    def __setattr__(self, name, value):
        if name in GovernedStepBudget._WRITABLE_AFTER_INIT:
            object.__setattr__(self, "_ceiling", _coerce_ceiling(value))
            return
        if not getattr(self, "_frozen", False):
            object.__setattr__(self, name, value)   # construction only
            return
        raise AttributeError(
            f"GovernedStepBudget.{name!r} is frozen: an active episode's "
            "governed-step counter cannot be rewound or replaced by a caller")

    def __delattr__(self, name):
        raise AttributeError(
            f"GovernedStepBudget.{name!r} cannot be deleted: an active "
            "episode's governed-step counter is bound to the Runtime")

    # ── read-only surface ────────────────────────────────────────────────

    @property
    def ceiling(self) -> int:
        return self._ceiling

    @ceiling.setter
    def ceiling(self, value) -> None:
        object.__setattr__(self, "_ceiling", _coerce_ceiling(value))

    @property
    def used(self) -> int:
        """Governed steps consumed in the current episode. READ-ONLY."""
        return self._read()

    @property
    def generation(self) -> int:
        """Monotonic episode generation. Advances only via ``next_episode``."""
        return self._generation

    @property
    def seal(self) -> EpisodeBudgetSeal:
        """Opaque identity of this episode's budget (for ``is`` comparison)."""
        return self._seal

    # ── the only legitimate episode transition ───────────────────────────

    @classmethod
    def next_episode(cls, previous, ceiling: int = 0) -> "GovernedStepBudget":
        """Mint the NEXT episode's budget.

        The ONLY authorised way to obtain a fresh governed-step allowance. The
        Runtime calls this at its real episode boundary and re-binds the result
        to the Broker, so any budget object held over from a previous episode is
        stale, inert, and refused by the PEP's identity check.
        """
        prior = 0
        if previous is not None:
            try:
                prior = int(getattr(previous, "generation", 0) or 0)
            except (TypeError, ValueError):
                prior = 0
        return cls(ceiling=ceiling, generation=prior + 1)

    def reset(self) -> None:
        """REFUSED. There is no in-place reset of an active episode's budget.

        The Runtime rotates the budget by minting a new generation at the
        episode boundary (:meth:`next_episode`). A mid-episode reset must not
        rewind the counter, so this always raises and leaves the active counter
        untouched.
        """
        raise BudgetResetRefused(
            "an active episode's governed-step budget cannot be reset in place; "
            "the Runtime mints a new episode generation at the episode boundary "
            f"(current generation {self._generation}, used {self.used})")

    # ── the only counter-advancing operation ─────────────────────────────

    def try_consume(self) -> bool:
        """Consume one governed step. False = exhausted (fail closed).

        This can only ever ADVANCE the counter. There is no operation on this
        object that decreases it.
        """
        return bool(self._advance())

    def remaining(self) -> int:
        if self._ceiling <= 0:
            return -1  # unbounded
        return max(0, self._ceiling - self.used)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class RuntimeContext:
    """Immutable snapshot of the Runtime's environment at step start."""
    mission_id: str
    objective_id: str
    view: dict = field(default_factory=dict)
    iteration: int = 0
    started_at: float = field(default_factory=time.time)
    scope: Optional["ScopeV0"] = None

    @staticmethod
    def make(mission_id: str, objective_id: str, view: Optional[dict] = None) -> "RuntimeContext":
        return RuntimeContext(
            mission_id=mission_id,
            objective_id=objective_id,
            view=view or {},
        )


@dataclass
class MissionContext:
    """The mission this Runtime instance is executing."""
    mission_id: str
    name: str
    objectives: List[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    scope: Optional["ScopeV0"] = None
    # P4.3 §15: optional bound first-class MissionSpec. When present
    # (populated by from_spec), the broker stage derives the
    # AuthorizationContext from this actual spec object rather than
    # the view's mission_id string. Default None preserves legacy
    # hand-built missions. Not part of equality-sensitive identity.
    spec: Any = None
    @staticmethod
    def from_spec(spec: Any, extra_constraints: Optional[dict] = None) -> "MissionContext":
        """Build a Runtime MissionContext from a first-class MissionSpec.

        P4.1 §15.1: the spec's identity/objectives/target envelope/
        constraints/scope become the runtime context. The spec's halt
        conditions ride in constraints under the reserved "halt" key so
        run_episode can consume them; per-iteration candidate sets ride
        under the reserved "candidates" key. ``extra_constraints`` adds
        ephemeral caller keys (e.g. test-declared candidates) without
        mutating the spec. Reserved keys in extra_constraints fail
        closed rather than silently overriding the spec.
        """
        from orchestrator.runtime.mission_spec import MissionSpec as _MissionSpec
        if not isinstance(spec, _MissionSpec):
            raise ValueError("MissionContext.from_spec: 'spec' must be a MissionSpec")
        merged: dict = dict(spec.constraints)
        if extra_constraints:
            if not isinstance(extra_constraints, dict):
                raise ValueError("MissionContext.from_spec: 'extra_constraints' must be a mapping")
            for reserved in ("halt", "candidates"):
                if reserved in extra_constraints:
                    raise ValueError(
                        f"MissionContext.from_spec: reserved key '{reserved}' "
                        "must come from the MissionSpec, not extra_constraints"
                    )
            merged.update(extra_constraints)
        merged["halt"] = spec.halt.to_dict()
        return MissionContext(
            mission_id=spec.mission_id,
            name=spec.name,
            objectives=list(spec.objectives),
            constraints=merged,
            scope=spec.scope,
            spec=spec,
        )

@dataclass
class StageResult:
    """Output of a single stage. The Runtime sequencer consumes this."""
    stage_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    trace_id: str = field(default_factory=lambda: _new_id("STG"))

    @staticmethod
    def make(stage_name: str, success: bool, output: Any = None,
             error: Optional[str] = None, duration_ms: float = 0.0) -> "StageResult":
        return StageResult(
            stage_name=stage_name,
            success=success,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )


@dataclass
class ActionRequest:
    """What the Planner asks the Broker to authorize."""
    action_id: str = field(default_factory=lambda: _new_id("ACT"))
    action_type: str = ""
    target: str = ""
    args: dict = field(default_factory=dict)
    rationale: str = ""
    # §14.6 F1: optional planner-side capability/method metadata threaded
    # to the broker and the PEP. Existing planners that omit these get
    # the broker-stage default ("fixture.inspect" / "inspect") via the
    # capability_name context key.
    capability: str = ""
    method: str = ""
    # Declared impact estimate (0-10) carried from the candidate/request
    # into the Broker so the Scope max_impact conjunction evaluates the
    # real value. None means "not declared": stage_broker fails closed.
    impact_estimate: Optional[float] = None

@dataclass
class PolicyDecision:
    """The Broker's allow/deny + constraints."""
    decision_id: str = field(default_factory=lambda: _new_id("PDC"))
    action_id: str = ""
    decision: str = "deny"  # "allow" | "deny"
    reason: str = ""
    constraints: dict = field(default_factory=dict)
    policy_name: str = ""
    policy_version: str = ""


@dataclass
class ExecutionEvent:
    """PEP-emitted record of a capability invocation."""
    event_id: str = field(default_factory=lambda: _new_id("EVT"))
    action_id: str = ""
    decision_id: str = ""
    capability: str = ""
    target: str = ""
    args: dict = field(default_factory=dict)
    outcome: str = ""
    output: Any = None
    timestamp: float = field(default_factory=time.time)
    def to_dict(self) -> dict:
        """Return a dictionary representation of the ExecutionEvent."""
        return {
            "event_id": self.event_id,
            "action_id": self.action_id,
            "decision_id": self.decision_id,
            "capability": self.capability,
            "target": self.target,
            "args": self.args,
            "outcome": self.outcome,
            "output": self.output,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionEvent":
        """Reconstruct an ExecutionEvent from a dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            action_id=data.get("action_id", ""),
            decision_id=data.get("decision_id", ""),
            capability=data.get("capability", ""),
            target=data.get("target", ""),
            args=data.get("args", {}),
            outcome=data.get("outcome", ""),
            output=data.get("output"),
            timestamp=data.get("timestamp", 0.0),
        )


@dataclass
class EvidenceReceipt:
    """Links an ExecutionEvent to its PolicyDecision and downstream consumers.

    P4.1 provenance depth (§15.1): the receipt additionally records the
    mission/scope identity, the authorized action dimensions (F1
    bindings, copied from the Broker's stored authorization truth —
    never re-evaluated here), and the Broker receipt id. All new fields
    default to empty so existing constructions are unchanged. Evidence
    remains non-authorizing: this object links and describes; it cannot
    permit execution.
    """
    receipt_id: str = field(default_factory=lambda: _new_id("RCP"))
    event_id: str = ""
    decision_id: str = ""
    hypothesis_id: Optional[str] = None
    summary: str = ""
    timestamp: float = field(default_factory=time.time)
    # P4.1 provenance linkage (all defaulted; populated by stage_receipt
    # from the broker-stage stored authorization + mission context).
    mission_id: str = ""
    scope_hash: str = ""
    action_type: str = ""
    target: str = ""
    capability: str = ""
    method: str = ""
    argv: tuple = ()
    broker_receipt_id: str = ""
    # §14.5 Evidence v1 durable-record identities linked to this receipt.
    evidence_v1_ids: tuple = ()
    artifact_refs: tuple = ()

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "event_id": self.event_id,
            "decision_id": self.decision_id,
            "hypothesis_id": self.hypothesis_id,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "mission_id": self.mission_id,
            "scope_hash": self.scope_hash,
            "action_type": self.action_type,
            "target": self.target,
            "capability": self.capability,
            "method": self.method,
            "argv": list(self.argv),
            "broker_receipt_id": self.broker_receipt_id,
            "evidence_v1_ids": list(self.evidence_v1_ids),
            "artifact_refs": list(self.artifact_refs),
        }


@dataclass
class LoopTermination:
    """Why and how the episode loop stopped."""
    terminated: bool = False
    reason: str = ""
    iterations: int = 0
    final_stage: str = ""
    # M3/D2 budget accounting: the caller's requested budget, the effective
    # (policy-clamped) budget, whether a clamp occurred, and the authoritative
    # policy maximum (0 = the policy declares no episode cap).
    requested_budget: int = 0
    effective_budget: int = 0
    budget_clamped: bool = False
    policy_max_episode_steps: int = 0
    # RSI-1 Fix B: which bound actually governed the episode, how many governed
    # steps reached the PEP, and whether the engagement was recognised as the
    # approved D2 scope. Reported truthfully so a clamp is never presented as
    # the policy's own cap when the independent invariant applied.
    governed_step_ceiling: int = 0
    governed_steps_used: int = 0
    d2_recognized: bool = False
    # RSI-1 B-1: which canonical governed contract governs this execution
    # ("" = none) and whether a protected capability is refused outright
    # because no recognised contract governs it.
    governance_contract: str = ""
    governance_refuses_protected: bool = False
    # RSI-1 C-1: the episode token of the governed-step budget that governed
    # this episode. It advances only at a legitimate episode boundary, so a
    # caller (or a test) can prove the budget was not rewound mid-episode.
    governance_budget_epoch: int = 0


@dataclass
class DecisionTrace:
    """Append-only trace of a Runtime episode. Stable, inspectable."""
    trace_id: str = field(default_factory=lambda: _new_id("TRC"))
    mission_id: str = ""
    entries: List[dict] = field(default_factory=list)

    def append(self, entry: dict) -> None:
        self.entries.append(entry)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "mission_id": self.mission_id,
            "entries": list(self.entries),
        }
