"""
policy.py — bootstrap-v0 policy loader and CapabilityBroker factory (CONV-1)

Per v4.1 AM-13.2: "define and commit a minimal named, versioned policy
artifact (bootstrap-v0) that the P2 Broker-mediated mock path and the
P2.4 safe capability authorize against."

CONV-1 (P3.0): BootstrapPolicy is RETIRED from the decision role.
The Runtime now uses the real brain CapabilityBroker as the single
canonical PDP. This module retains the bootstrap-v0 JSON loader and
provides a factory for constructing a CapabilityBroker with a
BrokerPolicy derived from bootstrap-v0 rules.

bootstrap-v0 rules (from policies/bootstrap-v0.json):
- BOOT-001: mock_capability (allow, read-only, no_subprocess)
- BOOT-002: safe_proving_capability (allow, read_only_fixture_inspection)
- BOOT-003: stage_observation (allow, no_execution)
- BOOT-004: worldmodel_read (allow, read-only)
- BOOT-005: receipt_emission (allow, decision_id_required)
- default_decision: deny

The CapabilityBroker uses its own authorization dimensions
(target, action_type, capability, method, impact_estimate, rate,
scope) per v4 §5.2. The bootstrap-v0 rules are mapped to BrokerPolicy
fields:
- allowed_action_types: from BOOT rule action_classes
- allowed_capabilities: derived from the capability used at runtime
- allowed_targets: ["*"] (all targets allowed in the walking skeleton)
- max_impact_per_action: 0.0 (read-only capabilities have zero impact)

Per GLM authorization: "BootstrapPolicy retired from the *decision
role* (loader/policy-input mechanics are the lane's; physical
deletion is P9)."
"""
import json
from pathlib import Path
from typing import Optional

from orchestrator.brain.capability_broker import (
    BrokerPolicy,
    CapabilityBroker,
)
from orchestrator.runtime.types import (
    D2_APPROVED_MAX_EPISODE_STEPS,
    D2_ENGAGEMENT_ID,
    GOVERNED_ENGAGEMENT_CONTRACTS,
    is_canonical_d2_scope,
)


def _d2_registry_ceiling() -> int:
    """The one authoritative D2 ceiling, read from the governance registry.

    RSI-1 B-1: the literal 5 is declared ONCE, in
    ``types.GOVERNED_ENGAGEMENT_CONTRACTS``. The loader validates the artifact
    against it and the Runtime enforces it at the PEP boundary, so the two can
    never drift apart and no policy artifact can restate the number.
    """
    return int(GOVERNED_ENGAGEMENT_CONTRACTS[D2_ENGAGEMENT_ID]["max_episode_steps"])


POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "bootstrap-v0.json"


class BootstrapPolicy:
    """Loader for bootstrap-v0 JSON. CONV-1: not the decision source.

    This class is retained for the loader/policy-input mechanics
    (extracting the bootstrap-v0 JSON into a BrokerPolicy). It is
    NOT the decision source — the CapabilityBroker is.
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or POLICY_PATH
        self._data = self._load()
        self.name: str = self._data.get("policy_name", "bootstrap-v0")
        self.version: str = self._data.get("version", "0")
        self._rules = {r["action_class"]: r for r in self._data.get("rules", [])}

    def _load(self) -> dict:
        with open(self._path) as f:
            return json.load(f)

    @property
    def allowed_action_types(self) -> list:
        """Action classes that bootstrap-v0 allows (for BrokerPolicy)."""
        return [
            action_class
            for action_class, rule in self._rules.items()
            if rule.get("decision") == "allow"
        ]

    def to_broker_policy(
        self,
        engagement_id: str = "bootstrap-v0",
        allowed_capabilities: Optional[list] = None,
        allowed_targets: Optional[list] = None,
        max_impact_per_action: float = 0.0,
    ) -> BrokerPolicy:
        """Construct a BrokerPolicy from bootstrap-v0 rules.

        Args:
            engagement_id: Engagement identifier for the BrokerPolicy.
            allowed_capabilities: Capabilities to allow. If None, derived
                from the runtime capability name.
            allowed_targets: Targets to allow. If None, defaults to ["*"]
                (all targets, matching bootstrap-v0's no-scope-check).
            max_impact_per_action: Maximum impact per action (0-10 scale).
                Default 0.0 for read-only capabilities.
        """
        return BrokerPolicy(
            schema_version=1,
            engagement_id=engagement_id,
            allowed_targets=allowed_targets or ["*"],
            allowed_action_types=self.allowed_action_types,
            allowed_capabilities=allowed_capabilities or ["*"],
            max_impact_per_action=max_impact_per_action,
        )


def make_broker_from_bootstrap(
    capability_name: str = "fixture.inspect",
    engagement_id: str = "bootstrap-v0",
) -> CapabilityBroker:
    """Factory: create a CapabilityBroker from bootstrap-v0 rules.

    CONV-1: this is the single canonical PDP factory for the Runtime.
    The Runtime's stage_broker calls broker.propose_action() on the
    returned broker.
    """
    bp = BootstrapPolicy()
    broker_policy = bp.to_broker_policy(
        engagement_id=engagement_id,
        allowed_capabilities=[capability_name, "*"],
        allowed_targets=["*"],
    )
    return CapabilityBroker(broker_policy)


# ── M2-D1 (2026-10-04): bounded lab policy loader ────────────────────────────
# engagement-d1-v1 authorizes exactly one action class, one exec/ capability,
# and one lab target ("dvwa"). It is the opposite of engagement-open-v0.json
# (which remains unwired and grants nothing). Loader is strict: missing,
# malformed, stale, or unsupported values fail closed.

D1_POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "engagement-d1-v1.json"
D2_POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "engagement-d2-v1.json"

D1_SUPPORTED_SCHEMA_VERSION = 1
D1_SUPPORTED_MODE = "BOUNDED_LAB"
D2_MAX_EPISODE_STEPS_CEILING = 64
D1_REQUIRED_LAB_KEYS = (
    "compose_project",
    "target_service",
    "target_image_prefix",
    "probe_container",
    "probe_tool",
)


class PolicyLoadError(ValueError):
    """Raised when a policy artifact is missing, malformed, stale, or
    unsupported. Fail-closed: no BrokerPolicy is produced."""


def _require_str_list(value, what: str) -> tuple:
    if not isinstance(value, list) or not value:
        raise PolicyLoadError(f"engagement-d1-v1: '{what}' must be a non-empty list")
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise PolicyLoadError(f"engagement-d1-v1: '{what}' entries must be non-empty strings")
    return tuple(value)


class D1Policy:
    """Strict loader for the bounded D1 lab policy (engagement-d1-v1).

    Deterministic and auditable: the artifact's sha256 is computed at load
    time and carried on the BrokerPolicy's engagement_id context so every
    decision trace names the exact bytes that produced it.
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = Path(path) if path else D1_POLICY_PATH
        if not self._path.is_file():
            raise PolicyLoadError(
                f"engagement-d1-v1: policy file missing: {self._path}"
            )
        import hashlib
        raw = self._path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        try:
            self._data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PolicyLoadError(
                f"engagement-d1-v1: malformed policy JSON: {exc}"
            ) from None
        if not isinstance(self._data, dict):
            raise PolicyLoadError("engagement-d1-v1: policy root must be an object")
        if self._data.get("schema_version") != D1_SUPPORTED_SCHEMA_VERSION:
            raise PolicyLoadError(
                "engagement-d1-v1: unsupported schema_version "
                f"{self._data.get('schema_version')!r} (supported: {D1_SUPPORTED_SCHEMA_VERSION})"
            )
        self.name = self._data.get("policy_name")
        if not isinstance(self.name, str) or not self.name.strip():
            raise PolicyLoadError("engagement-d1-v1: 'policy_name' must be a non-empty string")
        version = self._data.get("version")
        if not isinstance(version, int) or version < 1:
            raise PolicyLoadError("engagement-d1-v1: 'version' must be a positive integer")
        self.version = version
        if self._data.get("status") != "ACTIVE":
            raise PolicyLoadError(
                f"engagement-d1-v1: policy status must be 'ACTIVE', got {self._data.get('status')!r}"
            )
        if self._data.get("mode") != D1_SUPPORTED_MODE:
            raise PolicyLoadError(
                f"engagement-d1-v1: unsupported mode {self._data.get('mode')!r} "
                f"(supported: {D1_SUPPORTED_MODE})"
            )
        allowed = self._data.get("allowed")
        if not isinstance(allowed, dict):
            raise PolicyLoadError("engagement-d1-v1: 'allowed' block missing")
        self.allowed_action_types = _require_str_list(allowed.get("action_types"), "allowed.action_types")
        self.allowed_capabilities = _require_str_list(allowed.get("capabilities"), "allowed.capabilities")
        self.allowed_targets = _require_str_list(allowed.get("targets"), "allowed.targets")
        lab = (self._data.get("scope") or {}).get("lab")
        if not isinstance(lab, dict):
            raise PolicyLoadError("engagement-d1-v1: 'scope.lab' contract missing")
        for key in D1_REQUIRED_LAB_KEYS:
            if not isinstance(lab.get(key), str) or not lab.get(key, "").strip():
                raise PolicyLoadError(f"engagement-d1-v1: 'scope.lab.{key}' must be a non-empty string")
        self.lab = dict(lab)
        # M3/D2: optional fixed-HTTP contract. When present it is validated
        # strictly — GET-only, zero redirects, bounded time/size. Absent = the
        # artifact does not authorize any HTTP action (D1 behavior unchanged).
        self.http_contract = self._validate_http_contract(lab.get("http"))
        # M3/D2 remediation: the authoritative episode-wide step maximum. When
        # the artifact declares one it is validated strictly (positive int, no
        # bool, bounded); a malformed value fails closed. Absent = the policy
        # declares no episode cap and legacy budgets are untouched (D1).
        self.max_episode_steps = self._validate_max_episode_steps(
            self._data.get("max_episode_steps")
        )
        # RSI-1 Fix B: the approved D2 engagement must declare EXACTLY the
        # operator-approved five-step maximum. Recognition is STRUCTURAL (see
        # ``runtime.types.is_canonical_d2_scope``) — canonical engagement id,
        # the full D2 capability/action vocabulary, the canonical validated lab
        # contract, or the declared name prefix. A copy that renames itself
        # away from "engagement-d2*" is still recognised from its scope facts,
        # so renaming is not an escape. A modified copy (6, 64), a missing or
        # null limit, or any other value fails closed here — the loader, not
        # the demo launcher, is the first governance gate.
        self.is_d2_scope = is_canonical_d2_scope(
            engagement_id=str(self._data.get("engagement_id", "") or ""),
            action_types=self.allowed_action_types,
            capabilities=self.allowed_capabilities,
            lab=self.lab,
            policy_name=self.name,
        )
        if self.is_d2_scope and self.max_episode_steps != _d2_registry_ceiling():
            raise PolicyLoadError(
                f"{self.name}: max_episode_steps must be exactly "
                f"{_d2_registry_ceiling()} for the approved D2 scope, "
                f"got {self.max_episode_steps!r}"
            )
        fail_closed = self._data.get("fail_closed")
        if not isinstance(fail_closed, dict) or not fail_closed or not all(
            v is True for v in fail_closed.values()
        ):
            raise PolicyLoadError(
                "engagement-d1-v1: 'fail_closed' must be present with every flag true"
            )
        prohibited = self._data.get("prohibited") or {}
        self.prohibited_action_types = _require_str_list(
            prohibited.get("action_types", []), "prohibited.action_types"
        ) if prohibited.get("action_types") else ()
        self.prohibited_capabilities = _require_str_list(
            prohibited.get("capabilities", []), "prohibited.capabilities"
        ) if prohibited.get("capabilities") else ()
        prohibited_targets = prohibited.get("targets", [])
        if prohibited_targets:
            # A wildcard prohibited target would deny the allowed target too
            # (prohibited wins in the PDP) — refuse the contradictory artifact.
            if "*" in prohibited_targets:
                raise PolicyLoadError(
                    "engagement-d1-v1: prohibited.targets '*' would deny the "
                    "allowed target as well (prohibited wins); refusing artifact"
                )
            self.prohibited_targets = _require_str_list(prohibited_targets, "prohibited.targets")
        else:
            self.prohibited_targets = ()
        rate = self._data.get("rate_limits") or {}
        impact = self._data.get("impact") or {}
        try:
            self.max_actions_per_minute = int(rate.get("max_actions_per_minute", 6))
            self.max_actions_per_hour = int(rate.get("max_actions_per_hour", 60))
            self.max_concurrent = int(rate.get("max_concurrent", 1))
            self.max_impact_per_action = float(impact.get("max_impact_per_action", 2.0))
            self.max_cumulative_impact = float(impact.get("max_cumulative_impact", 20.0))
        except (TypeError, ValueError) as exc:
            raise PolicyLoadError(
                f"engagement-d1-v1: malformed rate_limits/impact values: {exc}"
            ) from None
        if min(self.max_actions_per_minute, self.max_actions_per_hour,
               self.max_impact_per_action) <= 0:
            raise PolicyLoadError("engagement-d1-v1: rate/impact limits must be positive")

    @staticmethod
    def _validate_http_contract(spec):
        """Strict validation for the optional fixed-HTTP contract (M3/D2).

        GET only; redirects forbidden; bounded time and artifact size; the
        destination is a fixed constant (no URL substitution is representable).
        """
        if spec is None:
            return None
        if not isinstance(spec, dict):
            raise PolicyLoadError("policy http contract: must be an object")
        if spec.get("scheme") != "http":
            raise PolicyLoadError("policy http contract: scheme must be 'http'")
        if spec.get("method") != "GET":
            raise PolicyLoadError("policy http contract: method must be 'GET' (fixed)")
        if spec.get("max_redirects") != 0:
            raise PolicyLoadError("policy http contract: max_redirects must be 0 (redirects forbidden)")
        host = spec.get("host")
        if not isinstance(host, str) or not host.strip():
            raise PolicyLoadError("policy http contract: 'host' must be a non-empty string")
        path = spec.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            raise PolicyLoadError("policy http contract: 'path' must start with '/'")
        try:
            port = int(spec.get("port"))
            max_time = int(spec.get("max_time_seconds"))
            max_bytes = int(spec.get("max_artifact_bytes"))
        except (TypeError, ValueError) as exc:
            raise PolicyLoadError(f"policy http contract: malformed numeric field: {exc}") from None
        if not (1 <= port <= 65535) or max_time <= 0 or max_bytes <= 0:
            raise PolicyLoadError("policy http contract: port/time/size out of range")
        ctx = spec.get("execution_context")
        if not isinstance(ctx, str) or "in-container" not in ctx:
            raise PolicyLoadError(
                "policy http contract: execution_context must declare the in-container context"
            )
        return dict(spec)

    @staticmethod
    def _validate_max_episode_steps(value) -> Optional[int]:
        """Strict validation of the optional episode step maximum (M3/D2).

        None (absent) means the artifact declares no cap and legacy budgets
        are untouched (D1). Any present value must be a positive, bounded,
        non-bool int, else the policy fails closed.
        """
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise PolicyLoadError(
                f"engagement policy: 'max_episode_steps' must be a positive integer, got {value!r}"
            )
        if not 1 <= value <= D2_MAX_EPISODE_STEPS_CEILING:
            raise PolicyLoadError(
                f"engagement policy: 'max_episode_steps' out of range "
                f"({value}; 1..{D2_MAX_EPISODE_STEPS_CEILING})"
            )
        return value


    def to_broker_policy(self) -> BrokerPolicy:
        """Map the validated artifact onto the canonical BrokerPolicy."""
        return BrokerPolicy(
            schema_version=1,
            engagement_id=f"{self.name}@sha256:{self.sha256[:16]}",
            policy_name=self.name,
            allowed_targets=self.allowed_targets,
            prohibited_targets=self.prohibited_targets,
            allowed_action_types=self.allowed_action_types,
            prohibited_action_types=self.prohibited_action_types,
            allowed_capabilities=self.allowed_capabilities,
            prohibited_capabilities=self.prohibited_capabilities,
            max_actions_per_minute=self.max_actions_per_minute,
            max_actions_per_hour=self.max_actions_per_hour,
            max_concurrent=self.max_concurrent,
            max_impact_per_action=self.max_impact_per_action,
            max_cumulative_impact=self.max_cumulative_impact,
            high_impact_requires_approval=True,
            max_episode_steps=self.max_episode_steps or 0,
        )


def make_broker_from_policy(path: Optional[Path] = None) -> CapabilityBroker:
    """Factory: canonical PDP built from a bounded lab policy artifact.

    Fail-closed: any missing/malformed/stale value raises PolicyLoadError
    instead of producing a broker. M3/D2: the policy's rate limits are
    ENFORCED by binding the existing RateLimiter component to the returned
    broker (deterministic lab operation: jitter disabled — the per-minute
    cap and denial accounting remain active). Counting semantics: the
    limiter counts authorized proposals (actions that passed every other
    dimension); rate-denied proposals are recorded as denials (emergency-
    brake accounting) and never execute, so they cannot bypass the control.
    """
    policy = D1Policy(path)
    from orchestrator.brain.rate_limiter import RateLimiter, RateLimiterConfig
    rate_limiter = RateLimiter(RateLimiterConfig(
        max_actions_per_minute=policy.max_actions_per_minute,
        max_actions_per_hour=policy.max_actions_per_hour,
        # Deterministic bounded-lab operation: no jitter sleep. The rate CAP
        # (per-minute/per-hour) and denial accounting stay fully active.
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
    ))
    return CapabilityBroker(policy.to_broker_policy(), rate_limiter=rate_limiter)
