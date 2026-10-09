"""RSI-1 measurement integrity, holdout authority, and promotion-eligibility.

DESIGN RULE (authority, not trust)
==================================
Nothing in this module believes a caller's assertion. Every fact that can
influence a promotion-eligibility classification is either

  (a) DERIVED here from bytes on disk whose digest is PINNED IN THIS FILE, or
  (b) an explicitly ABSENT/absent value, which resolves to BLOCKED / REFUSE.

A caller cannot construct a string, a boolean, or a dataclass that makes this
module believe a holdout, an evaluator identity, a statistical condition, or a
promotion prerequisite has been satisfied.

The former design let ``classify_promotion_eligibility(record, config, adequacy,
independent_holdout=True)`` return ``PROMOTION_ELIGIBLE`` from ordinary public
API arguments alone. That parameter no longer exists. Classification now takes
only a decision record plus a gate config, and derives every gate from
:func:`build_authority`, which reads a committed, digest-pinned anchor.

HONEST BLOCKERS (deliberate, not defects)
=========================================
* The canonical protected holdout ``evaluations/campaign/rbs_v4_holdout.jsonl``
  is ABSENT. ``verify_holdout`` therefore reports ``MISSING``. Nothing here
  substitutes, reconstructs, or approximates it.
* The authoritative roadmap defines NO numeric statistical requirement for RSI
  promotion. Adequacy therefore reports ``UNSPECIFIED_THRESHOLD`` and can never
  reach ``ADEQUATE``.
* No authoritative evidence index exists for the roadmap s19.5 GLM-contract
  artefacts (replay, safety, retention, transfer, stability, budget), so those
  gates are ``BLOCKED``. ``PROMOTION_ELIGIBLE`` is therefore unreachable in this
  repository today. That is the correct state, not a bug.

Promotion itself is NOT implemented and NOT authorised. Every state here is a
REPORT.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_VERSION = 2

# ══════════════════════════════════════════════════════════════════════════
# 0. Shared vocabulary
# ══════════════════════════════════════════════════════════════════════════

STATUS_PASS = "PASS"
STATUS_BLOCKED = "BLOCKED"
STATUS_REFUSE = "REFUSE"
STATUS_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

STATE_INDEPENDENT_HOLDOUT = "INDEPENDENT_HOLDOUT"
STATE_LOCAL_REPLAY = "LOCAL_REPLAY"
STATE_UNVERIFIABLE_INPUTS = "UNVERIFIABLE_INPUTS"
STATE_STATISTICALLY_INADEQUATE = "STATISTICALLY_INADEQUATE"
STATE_PROMOTION_ELIGIBLE = "PROMOTION_ELIGIBLE"
EVALUATION_STATES = (
    STATE_UNVERIFIABLE_INPUTS,
    STATE_LOCAL_REPLAY,
    STATE_STATISTICALLY_INADEQUATE,
    STATE_INDEPENDENT_HOLDOUT,
    STATE_PROMOTION_ELIGIBLE,
)

# Holdout verification statuses. There is intentionally no "close enough" path
# into HOLDOUT_VERIFIED.
HOLDOUT_VERIFIED = "VERIFIED"
HOLDOUT_MISSING = "MISSING"
HOLDOUT_UNREADABLE = "UNREADABLE"
HOLDOUT_INVALID_ENCODING = "INVALID_ENCODING"
HOLDOUT_MALFORMED = "MALFORMED"
HOLDOUT_EMPTY = "EMPTY"
HOLDOUT_DUPLICATE_ROWS = "DUPLICATE_ROWS"
HOLDOUT_SCHEMA_INVALID = "SCHEMA_INVALID"
HOLDOUT_ROW_COUNT_MISMATCH = "ROW_COUNT_MISMATCH"
HOLDOUT_DIGEST_MISMATCH = "DIGEST_MISMATCH"
HOLDOUT_CAMPAIGN_MISMATCH = "CAMPAIGN_MISMATCH"
HOLDOUT_UNEXPECTED_PATH = "UNEXPECTED_PATH"
HOLDOUT_ANCHOR_MISSING = "ANCHOR_MISSING"
HOLDOUT_ANCHOR_TAMPERED = "ANCHOR_TAMPERED"
HOLDOUT_ANCHOR_MALFORMED = "ANCHOR_MALFORMED"

HOLDOUT_FAILURE_STATUSES = (
    HOLDOUT_MISSING, HOLDOUT_UNREADABLE, HOLDOUT_INVALID_ENCODING, HOLDOUT_MALFORMED,
    HOLDOUT_EMPTY, HOLDOUT_DUPLICATE_ROWS, HOLDOUT_SCHEMA_INVALID,
    HOLDOUT_ROW_COUNT_MISMATCH, HOLDOUT_DIGEST_MISMATCH, HOLDOUT_CAMPAIGN_MISMATCH,
    HOLDOUT_UNEXPECTED_PATH, HOLDOUT_ANCHOR_MISSING, HOLDOUT_ANCHOR_TAMPERED,
    HOLDOUT_ANCHOR_MALFORMED,
)

HOLDOUT_NEVER_SUBSTITUTED = "no substitution is ever performed"

ADEQUATE = "ADEQUATE"
INADEQUATE = "INADEQUATE"
UNSPECIFIED_THRESHOLD = "UNSPECIFIED_THRESHOLD"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
INVALID_EVIDENCE = "INVALID_EVIDENCE"


class EvaluationGateError(ValueError):
    """Raised for programmer errors (bad API usage), never for invalid DATA.

    Invalid evaluation data never raises: it resolves to an explicit status.
    """


# ══════════════════════════════════════════════════════════════════════════
# 1. Authoritative anchors — pinned digests, not caller arguments
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AnchorSet:
    """The committed, digest-pinned facts this module is allowed to believe.

    ``holdout_anchor_file`` / ``holdout_anchor_sha256`` pin a manifest that
    itself declares the canonical holdout's path, SHA-256, and row count. The
    expected holdout SHA therefore originates OUTSIDE the evaluated dataset and
    OUTSIDE every verification argument.

    ``evidence_index_file``/``evidence_index_sha256`` would pin an index of the
    roadmap s19.5 GLM-contract artefacts. It is ``None`` because no such index
    has been established; that absence is why the replay/safety/retention/
    transfer/stability/budget gates are BLOCKED today.
    """
    holdout_anchor_file: str
    holdout_anchor_sha256: str
    holdout_required_row_keys: Tuple[str, ...] = ("run_id",)
    evidence_index_file: Optional[str] = None
    evidence_index_sha256: Optional[str] = None
    #: Source-pinned location of the ADOPTED evaluation-configuration registry.
    #: Both remain ``None`` in this repository: no production evaluation
    #: configuration has been adopted, so ``resolve_config_adoption`` reports
    #: ``UNADOPTED_CONFIG``. This is the correct production state, not a gap to
    #: be filled by inventing a registry.
    adopted_config_registry_file: Optional[str] = None
    adopted_config_registry_sha256: Optional[str] = None

    def evidence_index_adopted(self) -> bool:
        return bool(self.evidence_index_file and self.evidence_index_sha256)

    def config_registry_adopted(self) -> bool:
        return bool(self.adopted_config_registry_file
                    and self.adopted_config_registry_sha256)

    def anchor_identity(self) -> Dict[str, Any]:
        """FULL anchor identity, bound into :attr:`EvaluatorIdentity.anchors_digest`.

        The previous implementation recorded only whether an evidence index was
        adopted, not which one, so two different pinned index identities produced
        the same evaluator identity. The full identity of every anchor is now
        bound, which is what makes "same evaluator code + different adopted
        config" distinguishable from "same evaluator code + same adopted config".
        """
        return {
            "adopted_config_registry_file": self.adopted_config_registry_file,
            "adopted_config_registry_sha256": self.adopted_config_registry_sha256,
            "evidence_index_file": self.evidence_index_file,
            "evidence_index_sha256": self.evidence_index_sha256,
            "holdout_anchor_file": self.holdout_anchor_file,
            "holdout_anchor_sha256": self.holdout_anchor_sha256,
            "holdout_required_row_keys": list(self.holdout_required_row_keys),
        }


#: Pinned to the bytes of evaluations/campaign/rbs_v4_reproducibility_manifest.json
#: as committed in this repository. Editing the manifest does not change what
#: this module expects: the manifest is rejected as TAMPERED.
AUTHORITATIVE_ANCHORS = AnchorSet(
    holdout_anchor_file="evaluations/campaign/rbs_v4_reproducibility_manifest.json",
    holdout_anchor_sha256=(
        "c26ed773ba57d43d53e150acb90db8299aa565f9ea7b2646a7820aa2c9775757"),
)

#: Repository root. Tests override this module attribute to point at a
#: synthetic fixture repository; production code has no such injection point,
#: because no function here accepts a root/anchors parameter.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _is_hex_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


# ══════════════════════════════════════════════════════════════════════════
# 2. Evaluator identity — content-addressed over the real modules
# ══════════════════════════════════════════════════════════════════════════

EVALUATOR_COMPONENT_MODULES: Tuple[str, ...] = (
    "src/orchestrator/rsi/evaluation_gate.py",
    "src/orchestrator/rsi/snapshot.py",
    "src/orchestrator/rsi/strategy_eval.py",
    "src/orchestrator/rsi/scenario_validity.py",
    "src/orchestrator/runtime/stages.py",
    "src/orchestrator/runtime/types.py",
    "src/orchestrator/exec/capability_governance.py",
    "src/orchestrator/brain/action.py",
    "src/arena/ablation.py",
    # NOTE: "src/arena/manifests.py" was previously listed here. It has never
    # existed in any commit on any branch (verified with `git log --all` and
    # `git rev-list --all --objects`), so the entry made identity.complete
    # permanently False and every real decision record REFUSE. It was removed
    # rather than replaced or satisfied: a directory of JSON specs is not an
    # evaluator module, and `src/arena/d6_manifest.py` is NOT a substitute
    # merely because its name resembles it. Do not re-add a component without
    # dependency tracing that shows it materially affects evaluation semantics.
)

PLACEHOLDER_EVALUATOR_IDENTITIES = ("id", "0" * 64, "unknown", "none", "n/a", "")


@dataclass(frozen=True)
class EvaluatorIdentity:
    """Content hash of every module and config that defines this evaluator.

    Because the pinned anchor digests above live inside
    ``evaluation_gate.py`` — a hashed component — changing the expected holdout
    SHA necessarily changes this identity.
    """
    component_digests: Mapping[str, str]
    gate_config_digest: str
    missing_components: Tuple[str, ...] = ()
    anchors_digest: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def identity(self) -> str:
        return _sha256_bytes(_stable({
            "anchors": self.anchors_digest,
            "components": dict(sorted(self.component_digests.items())),
            "gate_config_digest": self.gate_config_digest,
            "schema_version": self.schema_version,
        }).encode())

    @property
    def complete(self) -> bool:
        """False when any hashed component could not be read."""
        return not self.missing_components

    @classmethod
    def compute_current(cls, config: "GateConfig",
                        anchors: Optional[AnchorSet] = None) -> "EvaluatorIdentity":
        """The ONLY authoritative evaluator identity for this exact config."""
        anchors = anchors or AUTHORITATIVE_ANCHORS
        digests: Dict[str, str] = {}
        missing: List[str] = []
        for rel in EVALUATOR_COMPONENT_MODULES:
            target = _REPO_ROOT / rel
            try:
                digests[rel] = _sha256_file(target)
            except OSError:
                missing.append(rel)
        return cls(component_digests=digests, gate_config_digest=config.config_digest,
                   missing_components=tuple(missing),
                   anchors_digest=_sha256_bytes(_stable(anchors.anchor_identity()).encode()))

    @staticmethod
    def is_placeholder(identity: str) -> bool:
        """Refuse obvious placeholders before any digest comparison."""
        if not isinstance(identity, str) or not identity:
            return True
        if identity.strip().lower() in PLACEHOLDER_EVALUATOR_IDENTITIES:
            return True
        return not _is_hex_sha256(identity)

    def to_dict(self) -> Dict[str, Any]:
        return {"anchors_digest": self.anchors_digest,
                "component_digests": dict(sorted(self.component_digests.items())),
                "complete": self.complete, "gate_config_digest": self.gate_config_digest,
                "identity": self.identity,
                "missing_components": list(self.missing_components),
                "schema_version": self.schema_version}


# ══════════════════════════════════════════════════════════════════════════
# 2b. Configuration adoption — experimental config != adopted authority
# ══════════════════════════════════════════════════════════════════════════
#
# A caller-created GateConfig is a perfectly valid RESEARCH configuration. It
# becomes promotion-authoritative only when an INDEPENDENTLY resolved,
# source-pinned adoption registry says so. Nothing the caller supplies can
# stand in for adoption: not a boolean, an adoption id, a registry path, or a
# registry digest.

ADOPTION_ADOPTED = "ADOPTED"
ADOPTION_UNADOPTED = "UNADOPTED_CONFIG"
ADOPTION_REGISTRY_UNAVAILABLE = "CONFIG_REGISTRY_UNAVAILABLE"
ADOPTION_REGISTRY_TAMPERED = "CONFIG_REGISTRY_TAMPERED"
ADOPTION_REGISTRY_MALFORMED = "CONFIG_REGISTRY_MALFORMED"
ADOPTION_STALE = "STALE_ADOPTION"
ADOPTION_BINDING_MISMATCH = "CONFIG_BINDING_MISMATCH"

ADOPTION_FAILURE_STATUSES = (
    ADOPTION_UNADOPTED, ADOPTION_REGISTRY_UNAVAILABLE, ADOPTION_REGISTRY_TAMPERED,
    ADOPTION_REGISTRY_MALFORMED, ADOPTION_STALE, ADOPTION_BINDING_MISMATCH,
)

#: Registry entry lifecycle. Only ACTIVE confers authority; the others stay
#: readable for history but are never authoritative.
ADOPTION_ACTIVE = "ACTIVE"
ADOPTION_SUPERSEDED = "SUPERSEDED"
ADOPTION_REVOKED = "REVOKED"
ADOPTION_ENTRY_STATUSES = (ADOPTION_ACTIVE, ADOPTION_SUPERSEDED, ADOPTION_REVOKED)

ADOPTION_REGISTRY_SCHEMA_VERSION = 1
_ADOPTION_ENTRY_KEYS = frozenset({
    "adoption_id", "campaign_id", "version", "status", "config_digest", "config"})

#: Roadmap s18.3 P7.10 promotion-lock controls. A config that disables one of
#: these may still be used experimentally, but it can never be adopted as a
#: promotion-authoritative configuration, so toggling a flag cannot manufacture
#: authority.
PROMOTION_REQUIREMENTS = (
    "require_independent_holdout",
    "require_parent_lineage",
    "require_replay_integrity",
    "require_safety_pass",
    "require_rollback_target",
    "require_glm_contract",
)

#: Bounded read for a pinned anchor. A resource bound, not a statistical
#: threshold.
_MAX_PINNED_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class ConfigAdoption:
    """Result of resolving whether ``config`` is an ADOPTED authority.

    ``status == ADOPTION_ADOPTED`` is the only value that confers promotion
    authority, and it is reachable only from pinned, digest-verified registry
    bytes. Every other status is an explicit fail-closed outcome.
    """
    status: str
    adoption_id: str = ""
    campaign_id: str = ""
    version: Optional[int] = None
    config_digest: str = ""
    registry_digest: str = ""
    detail: str = ""

    @property
    def adopted(self) -> bool:
        return self.status == ADOPTION_ADOPTED

    def to_dict(self) -> Dict[str, Any]:
        return {"adoption_id": self.adoption_id, "campaign_id": self.campaign_id,
                "config_digest": self.config_digest, "detail": self.detail,
                "registry_digest": self.registry_digest, "status": self.status,
                "version": self.version}


def _read_pinned_json(relpath: str, expected_sha256: str) -> Any:
    """Read a repository-relative pinned JSON anchor, verifying its digest.

    No basename searching, no sibling substitution, no absolute paths, and no
    escape from the repository root: the pinned path is the ONLY path consulted.
    """
    if not isinstance(relpath, str) or not relpath:
        raise EvaluationGateError("pinned anchor path is missing")
    if not _is_hex_sha256(expected_sha256):
        raise EvaluationGateError("pinned anchor digest is malformed")
    root = _REPO_ROOT.resolve()
    declared = Path(relpath)
    if declared.is_absolute():
        raise EvaluationGateError("pinned anchor path must be repository-relative")
    target = (root / declared).resolve()
    if root != target and root not in target.parents:
        raise EvaluationGateError("pinned anchor path escapes the repository")
    if not target.is_file():
        raise FileNotFoundError(relpath)
    size = target.stat().st_size
    if size > _MAX_PINNED_BYTES:
        raise EvaluationGateError("pinned anchor exceeds the bounded-read limit")
    raw = target.read_bytes()
    if _sha256_bytes(raw) != expected_sha256:
        raise EvaluationGateError("pinned anchor digest mismatch")

    def unique_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise EvaluationGateError(f"duplicate JSON key in pinned anchor: {key!r}")
            result[key] = value
        return result

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def resolve_config_adoption(config: GateConfig,
                            anchors: Optional[AnchorSet] = None) -> ConfigAdoption:
    """Resolve whether ``config`` is an independently adopted authority.

    Fail-closed at every step. No caller-supplied adoption value is consulted.
    """
    anchors = anchors or AUTHORITATIVE_ANCHORS
    path = anchors.adopted_config_registry_file
    digest = anchors.adopted_config_registry_sha256

    # No registry has been adopted by this repository revision.
    if path is None or digest is None:
        return ConfigAdoption(
            status=ADOPTION_UNADOPTED,
            detail=("no evaluation-configuration adoption registry is pinned by "
                    "this repository revision; a caller-created GateConfig is a "
                    "valid EXPERIMENTAL configuration but is not promotion-authoritative"))

    try:
        payload = _read_pinned_json(path, digest)
    except FileNotFoundError:
        return ConfigAdoption(status=ADOPTION_REGISTRY_UNAVAILABLE,
                              detail=f"pinned adoption registry is absent: {path}")
    except EvaluationGateError as exc:
        text = str(exc)
        # Digest/shape/path failures from _read_pinned_json are tampering or
        # malformed CONTENT; a JSON syntax error is likewise malformed content,
        # not an unavailable file.
        status = (ADOPTION_REGISTRY_MALFORMED
                  if "duplicate JSON key" in text else ADOPTION_REGISTRY_TAMPERED)
        return ConfigAdoption(status=status, detail=text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # The bytes were pinned and digest-verified, so undecodable content is a
        # malformed registry rather than an unavailable one.
        return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED, detail=str(exc))
    except OSError as exc:
        return ConfigAdoption(status=ADOPTION_REGISTRY_UNAVAILABLE, detail=str(exc))

    if not isinstance(payload, dict) or set(payload) != {"schema_version", "entries"}:
        return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                              detail="registry must contain exactly schema_version and entries")
    version = payload["schema_version"]
    if type(version) is not int or version != ADOPTION_REGISTRY_SCHEMA_VERSION:
        return ConfigAdoption(
            status=ADOPTION_REGISTRY_MALFORMED,
            detail=f"registry schema_version must be the int "
                   f"{ADOPTION_REGISTRY_SCHEMA_VERSION}")
    entries = payload["entries"]
    if not isinstance(entries, list):
        return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                              detail="registry entries must be a list")

    seen_keys = set()
    active: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ADOPTION_ENTRY_KEYS:
            return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                                  detail="entry keys do not match the required schema")
        for name in ("adoption_id", "campaign_id"):
            if not isinstance(entry[name], str) or not entry[name]:
                return ConfigAdoption(
                    status=ADOPTION_REGISTRY_MALFORMED,
                    detail=f"entry {name} must be a non-empty string")
        if type(entry["version"]) is not int or entry["version"] < 1:
            return ConfigAdoption(
                status=ADOPTION_REGISTRY_MALFORMED,
                detail="entry version must be a positive non-boolean integer")
        if entry["status"] not in ADOPTION_ENTRY_STATUSES:
            return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                                  detail=f"entry status must be one of "
                                         f"{list(ADOPTION_ENTRY_STATUSES)}")
        if not _is_hex_sha256(entry["config_digest"]):
            return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                                  detail="entry config_digest is not a SHA-256")
        if not isinstance(entry["config"], dict):
            return ConfigAdoption(status=ADOPTION_REGISTRY_MALFORMED,
                                  detail="entry config must be an object")

        key = (entry["campaign_id"], entry["version"])
        if key in seen_keys:
            return ConfigAdoption(
                status=ADOPTION_REGISTRY_MALFORMED,
                detail=f"duplicate campaign/version entry: {key}")
        seen_keys.add(key)

        if entry["status"] == ADOPTION_ACTIVE:
            campaign = entry["campaign_id"]
            if campaign in active:
                return ConfigAdoption(
                    status=ADOPTION_REGISTRY_MALFORMED,
                    detail=f"more than one ACTIVE adoption for campaign {campaign!r}")
            active[campaign] = entry

    entry = active.get(config.campaign_id)
    if entry is None:
        return ConfigAdoption(status=ADOPTION_UNADOPTED,
                              detail=f"no ACTIVE adoption for campaign "
                                     f"{config.campaign_id!r}",
                              campaign_id=config.campaign_id)

    # Exact canonical payload AND digest must both match.
    if (entry["config_digest"] != config.config_digest
            or _stable(entry["config"]) != _stable(config.to_dict())):
        return ConfigAdoption(
            status=ADOPTION_BINDING_MISMATCH,
            campaign_id=config.campaign_id,
            detail="supplied config does not match the adopted canonical payload")

    disabled = [name for name in PROMOTION_REQUIREMENTS
                if getattr(config, name) is not True]
    if disabled:
        return ConfigAdoption(
            status=ADOPTION_BINDING_MISMATCH, campaign_id=config.campaign_id,
            detail=f"adopted config disables promotion-lock requirement(s) {disabled}; "
                   "toggling a requirement flag cannot manufacture authority")

    return ConfigAdoption(
        status=ADOPTION_ADOPTED, adoption_id=entry["adoption_id"],
        campaign_id=entry["campaign_id"], version=entry["version"],
        config_digest=config.config_digest, registry_digest=digest)


# ══════════════════════════════════════════════════════════════════════════
# 2c. Policy identity — derive-and-verify, never record-supplied trust
# ══════════════════════════════════════════════════════════════════════════
#
# C1/C2 finding: ``EvaluationDecisionRecord.baseline_policy_hash`` and
# ``candidate_policy_hash`` are caller-supplied strings. The runtime policy
# loader computes a SHA-256 over the artifact at load time, but nothing bound
# the record's hash to that loaded artifact, so the record hash was an
# ASSERTED identity — usable for lineage bookkeeping, never proof of content.
#
# Mechanism below: the artifact CONTENT is hashed here (the caller supplies
# bytes, never a digest), and the derived digest is compared against the
# record. A derived-vs-declared mismatch is a detected fabrication and refuses
# unconditionally. Absence of a derived binding is BLOCKED only when the gate
# config requires policy identity (``require_policy_identity``); otherwise the
# historical asserted-hash behavior is preserved unchanged. Whether adopted
# production configurations must set that flag is an operator governance
# decision (PROPOSED, not silently adopted by this mechanism).

POLICY_IDENTITY_VERIFIED = "POLICY_IDENTITY_VERIFIED"
POLICY_IDENTITY_MISMATCH = "POLICY_IDENTITY_MISMATCH"
POLICY_IDENTITY_ASSERTED = "POLICY_IDENTITY_ASSERTED"
POLICY_IDENTITY_MISSING = "POLICY_IDENTITY_MISSING"

POLICY_IDENTITY_ROLES = ("baseline", "candidate")


@dataclass(frozen=True)
class PolicyIdentity:
    """A policy identity observation derived by THIS module.

    ``content_sha256`` is either computed here from the artifact's actual
    bytes (``derived=True``) or an explicitly asserted, non-authoritative
    echo of a record-supplied value (``derived=False``, via
    :func:`asserted_policy_identity`). Only ``derived=True`` can turn the
    policy-identity gate PASS; an asserted identity can never verify.
    """
    role: str
    policy_id: str
    content_sha256: str
    origin: str = ""
    derived: bool = True

    def __post_init__(self) -> None:
        if self.role not in POLICY_IDENTITY_ROLES:
            raise EvaluationGateError(
                f"policy identity role must be one of {POLICY_IDENTITY_ROLES}, "
                f"got {self.role!r}")
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise EvaluationGateError("policy_id must be a non-empty string")
        if not _is_hex_sha256(self.content_sha256):
            raise EvaluationGateError(
                f"content_sha256 must be a 64-char lowercase hex SHA-256, got "
                f"{self.content_sha256!r}")
        if type(self.derived) is not bool:
            raise EvaluationGateError("derived must be a bool")


def derive_policy_identity(role: str, policy_id: str, content: bytes,
                           origin: str = "") -> PolicyIdentity:
    """Derive the identity of a policy artifact from its actual bytes.

    The caller supplies the artifact CONTENT (never a digest); the SHA-256 is
    computed here, inside the authority module. ``origin`` is recorded
    verbatim for audit readability and is not an authority.
    """
    if not isinstance(content, (bytes, bytearray)):
        raise EvaluationGateError(
            f"policy content must be bytes to hash (got {type(content).__name__}); "
            "accepting a caller-computed digest would re-create the C1/C2 gap")
    return PolicyIdentity(role=role, policy_id=policy_id,
                          content_sha256=_sha256_bytes(bytes(content)),
                          origin=origin, derived=True)


def asserted_policy_identity(role: str, policy_id: str, claimed_sha256: str,
                             origin: str = "") -> PolicyIdentity:
    """Record a caller-supplied policy hash as ASSERTED (non-authoritative).

    Adopting asserted identities downstream is an explicit operator decision
    with recorded consequences; this constructor exists so that mode cannot be
    mistaken for verification — ``derived=False`` can never turn the
    policy-identity gate green.
    """
    if not _is_hex_sha256(claimed_sha256):
        raise EvaluationGateError(
            f"claimed_sha256 must be a 64-char lowercase hex SHA-256, got "
            f"{claimed_sha256!r}")
    return PolicyIdentity(role=role, policy_id=policy_id,
                          content_sha256=claimed_sha256, origin=origin,
                          derived=False)


def verify_policy_identity(record: "EvaluationDecisionRecord",
                           identities: Tuple[PolicyIdentity, ...],
                           *, require_binding: bool = False
                           ) -> List[Tuple[str, str, str]]:
    """Compare a record's policy hashes against identity observations.

    Returns ``(gate_name, status, detail)`` triples for the
    ``policy_identity_baseline`` / ``policy_identity_candidate`` gates.

    Rules (fail-closed precedence):

    * a DERIVED identity that matches the record hash     -> PASS
    * a DERIVED identity that contradicts the record hash -> REFUSE
      (unconditionally, regardless of ``require_binding``: a derived-vs-declared
      mismatch is a detected fabrication, the same class as any other
      record-vs-authority contradiction)
    * no identity supplied, or only an ASSERTED one       -> BLOCKED when
      ``require_binding`` is True, no gate otherwise (historical behavior)
    * an empty record hash                                -> BLOCKED
      (POLICY_IDENTITY_MISSING) when ``require_binding`` is True
    """
    gates: List[Tuple[str, str, str]] = []
    by_role = {}
    for item in identities:
        if not isinstance(item, PolicyIdentity):
            raise EvaluationGateError(
                f"policy identities must be PolicyIdentity instances, got "
                f"{type(item).__name__}")
        if item.role in by_role:
            raise EvaluationGateError(
                f"duplicate policy identity for role {item.role!r}; one "
                "observation per role, ambiguity is not verification")
        by_role[item.role] = item

    for role in POLICY_IDENTITY_ROLES:
        gate_name = f"policy_identity_{role}"
        record_hash = getattr(record, f"{role}_policy_hash")
        identity = by_role.get(role)
        if identity is not None and identity.derived:
            if record_hash == identity.content_sha256:
                gates.append((gate_name, STATUS_PASS,
                              f"{POLICY_IDENTITY_VERIFIED}: record hash matches "
                              f"the digest derived from artifact content "
                              f"(policy_id={identity.policy_id!r})"))
            else:
                gates.append((gate_name, STATUS_REFUSE,
                              f"{POLICY_IDENTITY_MISMATCH}: record declares "
                              f"{record_hash!r} but the artifact supplied for "
                              f"verification hashes to {identity.content_sha256!r} "
                              f"(policy_id={identity.policy_id!r}); declared "
                              "policy identity is a fabrication"))
            continue
        if not require_binding:
            # Asserted mode without an adopted requirement: historical
            # behavior, no new gate. The hash remains a claim.
            continue
        if not record_hash:
            gates.append((gate_name, STATUS_BLOCKED,
                          f"{POLICY_IDENTITY_MISSING}: record declares no "
                          f"{role} policy hash"))
        elif identity is None:
            gates.append((gate_name, STATUS_BLOCKED,
                          f"{POLICY_IDENTITY_ASSERTED}: record-supplied hash is "
                          f"asserted, not verified — no artifact content was "
                          f"supplied for derivation"))
        else:
            gates.append((gate_name, STATUS_BLOCKED,
                              f"{POLICY_IDENTITY_ASSERTED}: identity for "
                              f"{identity.policy_id!r} is an asserted echo "
                              f"(derived=False) and cannot verify the record hash"))
    return gates


# ══════════════════════════════════════════════════════════════════════════
# 2d. Campaign-scoped POLICY MANIFEST — the trusted re-derivation source
# ══════════════════════════════════════════════════════════════════════════
#
# Operator ruling 2026-10-09: exploration-policy artifacts must be committed and
# digest-pinned for campaigns seeking authoritative results, bound to trusted
# configuration/adoption state, WITHOUT per-campaign anchors in AnchorSet and
# WITHOUT a second independent authority source.
#
# TRUST CHAIN (each link verified before the next is used):
#
#   AnchorSet.adopted_config_registry_sha256   (pinned IN THIS FILE)
#     -> adoption registry bytes               (_read_pinned_json, digest-verified)
#     -> registry entry config_digest          (== config.config_digest)
#     -> config.policy_manifest_file/_sha256   (fields of config.to_dict())
#     -> manifest bytes                        (_read_pinned_json, digest-verified)
#     -> manifest entry artifact path + sha256 (exact bytes, digest-verified)
#     -> PolicyIdentity(role, policy_id, sha256(bytes), derived=True)
#
# Adoption is the ONLY way in: resolve_policy_identities() refuses to read a
# manifest unless resolve_config_adoption(config) reports ADOPTED. That is what
# makes this a projection of the existing authority rather than a parallel one.
#
# NOTHING here reads an identity from a ledger record, from the record's own
# declared hash, or from any caller. The record's declared hash is only ever
# COMPARED against the derived identity, and a disagreement refuses.

POLICY_MANIFEST_SCHEMA_VERSION = 1
POLICY_MANIFEST_KEYS = frozenset({"schema_version", "campaign_id",
                                  "source_revision", "policies"})
POLICY_MANIFEST_ENTRY_KEYS = frozenset({"role", "policy_id", "artifact",
                                        "sha256", "policy_schema_version"})

POLICY_MANIFEST_VERIFIED = "POLICY_MANIFEST_VERIFIED"
POLICY_MANIFEST_UNPINNED = "POLICY_MANIFEST_UNPINNED"
POLICY_MANIFEST_CONFIG_NOT_ADOPTED = "POLICY_MANIFEST_CONFIG_NOT_ADOPTED"
POLICY_MANIFEST_ABSENT = "POLICY_MANIFEST_ABSENT"
POLICY_MANIFEST_TAMPERED = "POLICY_MANIFEST_TAMPERED"
POLICY_MANIFEST_MALFORMED = "POLICY_MANIFEST_MALFORMED"
POLICY_MANIFEST_CAMPAIGN_MISMATCH = "POLICY_MANIFEST_CAMPAIGN_MISMATCH"
POLICY_MANIFEST_ROLE_INVALID = "POLICY_MANIFEST_ROLE_INVALID"
POLICY_ARTIFACT_ABSENT = "POLICY_ARTIFACT_ABSENT"
POLICY_ARTIFACT_TAMPERED = "POLICY_ARTIFACT_TAMPERED"
POLICY_ARTIFACT_UNPARSABLE = "POLICY_ARTIFACT_UNPARSABLE"

#: Every one of these is fail-closed: none of them can produce an identity.
POLICY_MANIFEST_FAILURE_STATUSES = (
    POLICY_MANIFEST_UNPINNED, POLICY_MANIFEST_CONFIG_NOT_ADOPTED,
    POLICY_MANIFEST_ABSENT, POLICY_MANIFEST_TAMPERED, POLICY_MANIFEST_MALFORMED,
    POLICY_MANIFEST_CAMPAIGN_MISMATCH, POLICY_MANIFEST_ROLE_INVALID,
    POLICY_ARTIFACT_ABSENT, POLICY_ARTIFACT_TAMPERED,
    POLICY_ARTIFACT_UNPARSABLE,
)


@dataclass(frozen=True)
class PolicyManifestResolution:
    """Outcome of resolving policy identities from the trusted manifest.

    ``status == POLICY_MANIFEST_VERIFIED`` is the ONLY value that carries
    ``identities``, and it is reachable only when the config is independently
    ADOPTED and every manifest and artifact digest verified. Every other status
    is an explicit fail-closed outcome with an empty ``identities`` tuple.
    """
    status: str
    identities: Tuple[PolicyIdentity, ...] = ()
    manifest_file: str = ""
    manifest_sha256: str = ""
    campaign_id: str = ""
    source_revision: str = ""
    artifact_digests: Mapping[str, str] = field(default_factory=dict)
    detail: str = ""

    @property
    def verified(self) -> bool:
        return self.status == POLICY_MANIFEST_VERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {"artifact_digests": dict(sorted(self.artifact_digests.items())),
                "campaign_id": self.campaign_id, "detail": self.detail,
                "identities": [
                    {"content_sha256": i.content_sha256, "derived": i.derived,
                     "origin": i.origin, "policy_id": i.policy_id, "role": i.role}
                    for i in self.identities],
                "manifest_file": self.manifest_file,
                "manifest_sha256": self.manifest_sha256,
                "source_revision": self.source_revision, "status": self.status}


def _read_pinned_artifact_bytes(relpath: str, expected_sha256: str) -> bytes:
    """Read exact artifact bytes, repository-relative, digest-verified.

    Deliberately a BYTE read, not a JSON read: the identity is the digest of the
    committed bytes, so re-serialising the parsed object would prove nothing
    about what was actually committed. Same containment rules as
    :func:`_read_pinned_json` — no absolute paths, no basename searching, no
    sibling substitution, no escape from the repository root, bounded size.
    """
    if not isinstance(relpath, str) or not relpath:
        raise EvaluationGateError("pinned artifact path is missing")
    if not _is_hex_sha256(expected_sha256):
        raise EvaluationGateError("pinned artifact digest is malformed")
    root = _REPO_ROOT.resolve()
    declared = Path(relpath)
    if declared.is_absolute():
        raise EvaluationGateError("pinned artifact path must be repository-relative")
    target = (root / declared).resolve()
    if root != target and root not in target.parents:
        raise EvaluationGateError("pinned artifact path escapes the repository")
    if not target.is_file():
        raise FileNotFoundError(relpath)
    if target.stat().st_size > _MAX_PINNED_BYTES:
        raise EvaluationGateError("pinned artifact exceeds the bounded-read limit")
    raw = target.read_bytes()
    if _sha256_bytes(raw) != expected_sha256:
        raise EvaluationGateError("pinned artifact digest mismatch")
    return raw


def resolve_policy_identities(config: GateConfig,
                             anchors: Optional[AnchorSet] = None
                             ) -> PolicyManifestResolution:
    """Resolve policy identities from TRUSTED artifacts for ``config``.

    This is the only path by which a strict-mode record can regain current
    authority after a restart. It is deliberately not parameterised by a record,
    a ledger, a policy path, or an expected digest: every input it consults is
    either the adopted config (already digest-verified against pinned registry
    bytes) or content inside the digest-verified manifest it names.

    Fail-closed at every step. Absence of a manifest binding, absence of
    adoption, or any digest disagreement yields an explicit status and an EMPTY
    identities tuple — never a fallback to caller-supplied identity.
    """
    anchors = anchors or AUTHORITATIVE_ANCHORS

    if not config.policy_manifest_file or not config.policy_manifest_sha256:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_UNPINNED, campaign_id=config.campaign_id,
            detail=("this configuration pins no campaign policy manifest; strict "
                    "policy identity cannot be re-derived and cannot fall back "
                    "to caller-supplied identity"))

    # THE gate. Adoption is what makes config.policy_manifest_sha256 trusted
    # rather than caller-chosen, so it is checked before the manifest is read.
    adoption = resolve_config_adoption(config, anchors)
    if not adoption.adopted:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_CONFIG_NOT_ADOPTED,
            campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=(f"policy manifest resolution requires an independently "
                    f"adopted configuration; adoption is {adoption.status}: "
                    f"{adoption.detail}"))

    try:
        payload = _read_pinned_json(config.policy_manifest_file,
                                    config.policy_manifest_sha256)
    except FileNotFoundError:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_ABSENT, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=f"pinned policy manifest is absent: "
                   f"{config.policy_manifest_file}")
    except EvaluationGateError as exc:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_TAMPERED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file, detail=str(exc))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file, detail=str(exc))
    except OSError as exc:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_ABSENT, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file, detail=str(exc))

    if not isinstance(payload, dict) or set(payload) != set(POLICY_MANIFEST_KEYS):
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=f"policy manifest must contain exactly "
                   f"{sorted(POLICY_MANIFEST_KEYS)}")
    version = payload["schema_version"]
    if type(version) is not int or version != POLICY_MANIFEST_SCHEMA_VERSION:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=f"policy manifest schema_version must be the int "
                   f"{POLICY_MANIFEST_SCHEMA_VERSION}, got {version!r}")

    # Campaign binding. A manifest pinned for another campaign is not evidence
    # for this one, however well-formed it is.
    manifest_campaign = payload["campaign_id"]
    if not isinstance(manifest_campaign, str) or not manifest_campaign:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail="policy manifest campaign_id must be a non-empty string")
    if manifest_campaign != config.campaign_id:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_CAMPAIGN_MISMATCH,
            campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=(f"policy manifest is pinned for campaign "
                    f"{manifest_campaign!r} but the adopted configuration is "
                    f"campaign {config.campaign_id!r}"))

    source_revision = payload["source_revision"]
    if not isinstance(source_revision, str) or not source_revision.strip():
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail="policy manifest source_revision must be a non-empty string")

    entries = payload["policies"]
    if not isinstance(entries, list) or not entries:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail="policy manifest policies must be a non-empty list")

    # Exactly one entry per role, both roles required. A missing or duplicated
    # role is malformed, not "unverified": ambiguity is not partial evidence.
    by_role: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != set(POLICY_MANIFEST_ENTRY_KEYS):
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail=f"policy manifest entry keys do not match the required "
                       f"schema {sorted(POLICY_MANIFEST_ENTRY_KEYS)}")
        role = entry["role"]
        if role not in POLICY_IDENTITY_ROLES:
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_ROLE_INVALID, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail=f"policy manifest entry role must be one of "
                       f"{list(POLICY_IDENTITY_ROLES)}, got {role!r}")
        if role in by_role:
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_ROLE_INVALID, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail=f"policy manifest declares role {role!r} more than once; "
                       "one authorized artifact per role is required")
        if not isinstance(entry["policy_id"], str) or not entry["policy_id"]:
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail="policy manifest entry policy_id must be a non-empty string")
        if not _is_hex_sha256(entry["sha256"]):
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail=f"policy manifest entry sha256 for role {role!r} is not a "
                       f"SHA-256")
        policy_version = entry["policy_schema_version"]
        if type(policy_version) is not int or policy_version < 1:
            return PolicyManifestResolution(
                status=POLICY_MANIFEST_MALFORMED, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                detail=f"policy manifest entry policy_schema_version for role "
                       f"{role!r} must be a positive non-boolean integer")
        by_role[role] = entry
    missing = [r for r in POLICY_IDENTITY_ROLES if r not in by_role]
    if missing:
        return PolicyManifestResolution(
            status=POLICY_MANIFEST_ROLE_INVALID, campaign_id=config.campaign_id,
            manifest_file=config.policy_manifest_file,
            detail=f"policy manifest is missing required role(s) {missing}")

    identities: List[PolicyIdentity] = []
    digests: Dict[str, str] = {}
    for role in POLICY_IDENTITY_ROLES:
        entry = by_role[role]
        try:
            raw = _read_pinned_artifact_bytes(entry["artifact"], entry["sha256"])
        except FileNotFoundError:
            return PolicyManifestResolution(
                status=POLICY_ARTIFACT_ABSENT, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"pinned policy artifact for role {role!r} is absent: "
                       f"{entry['artifact']}")
        except EvaluationGateError as exc:
            status = (POLICY_ARTIFACT_UNPARSABLE
                      if "escapes the repository" in str(exc)
                      else POLICY_ARTIFACT_TAMPERED)
            return PolicyManifestResolution(
                status=status, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"policy artifact for role {role!r}: {exc}")
        except OSError as exc:
            return PolicyManifestResolution(
                status=POLICY_ARTIFACT_ABSENT, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"policy artifact for role {role!r}: {exc}")

        # The artifact must be parseable policy content, and must agree with its
        # OWN declared identity. This catches a manifest that pins well-formed
        # bytes which are not the policy they claim to be.
        declared = None
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                declared = parsed.get("content_hash")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return PolicyManifestResolution(
                status=POLICY_ARTIFACT_UNPARSABLE, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"policy artifact for role {role!r} is not valid JSON: {exc}")
        if not isinstance(parsed, dict) or parsed.get("policy_id") != entry["policy_id"]:
            return PolicyManifestResolution(
                status=POLICY_ARTIFACT_UNPARSABLE, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"policy artifact for role {role!r} declares policy_id "
                       f"{parsed.get('policy_id') if isinstance(parsed, dict) else None!r} "
                       f"but the manifest pins {entry['policy_id']!r}")
        if declared is not None and declared != _sha256_bytes(raw):
            return PolicyManifestResolution(
                status=POLICY_ARTIFACT_UNPARSABLE, campaign_id=config.campaign_id,
                manifest_file=config.policy_manifest_file,
                source_revision=source_revision, artifact_digests=dict(digests),
                detail=f"policy artifact for role {role!r} declares content_hash "
                       f"{declared!r} which is not the digest of its own committed "
                       "bytes; the artifact does not describe itself")

        identities.append(derive_policy_identity(
            role, entry["policy_id"], raw,
            origin=f"{config.policy_manifest_file}#{role}"))
        digests[role] = entry["sha256"]

    return PolicyManifestResolution(
        status=POLICY_MANIFEST_VERIFIED, identities=tuple(identities),
        manifest_file=config.policy_manifest_file,
        manifest_sha256=config.policy_manifest_sha256,
        campaign_id=config.campaign_id, source_revision=source_revision,
        artifact_digests=digests,
        detail=(f"policy identities derived from pinned artifacts of campaign "
                f"{config.campaign_id!r} at source revision "
                f"{source_revision!r}"))


def trusted_policy_identities(config: GateConfig,
                              anchors: Optional[AnchorSet] = None
                              ) -> PolicyManifestResolution:
    """Alias kept for call-site readability. Same function, no extra authority."""
    return resolve_policy_identities(config, anchors)


def effective_policy_identities(
            config: GateConfig,
            supplied: Tuple[PolicyIdentity, ...]
            ) -> Tuple[PolicyIdentity, ...]:
    """Choose the identity observations classification will actually judge on.

    Precedence, and the reason for it:

    1. A TRUSTED manifest resolution (adopted config -> pinned manifest ->
       digest-verified artifact bytes) is authoritative when it verifies. Caller
       input cannot override it, and a caller-derived identity that CONTRADICTS
       it is refused outright, because two derivations from trusted bytes
       disagreeing is a contradiction, not a preference.
    2. Otherwise the caller's DERIVED identities are used, exactly as before.
       This is what lets an in-process admission verify content the caller
       genuinely holds, and it is why the existing caller-supplied path stays
       meaningful rather than being deleted.
    3. Asserted identities never satisfy a strict gate from either path.

    Note what this is NOT: a public pass-through. The trusted path is resolved
    from the config, so a restarted process re-derives strict records with no
    caller involvement at all. It also never reads an identity out of the ledger
    or out of the record's declared hash.
    """
    if not config.require_policy_identity:
        return supplied
    resolution = resolve_policy_identities(config)
    if not resolution.verified:
        return supplied        # fail closed downstream: BLOCKED, never PASS
    trusted_by_role = {i.role: i for i in resolution.identities}
    for item in supplied:
        if not isinstance(item, PolicyIdentity):
            raise EvaluationGateError(
                f"policy identities must be PolicyIdentity instances, got "
                f"{type(item).__name__}")
        if item.derived and item.role in trusted_by_role:
            trusted = trusted_by_role[item.role]
            if item.content_sha256 != trusted.content_sha256:
                raise EvaluationGateError(
                    f"policy identity for role {item.role!r} supplied by the "
                    f"caller ({item.content_sha256!r}) contradicts the digest "
                    f"independently derived from the pinned trusted artifact "
                    f"({trusted.content_sha256!r}, policy_id="
                    f"{trusted.policy_id!r}); a contradiction between two "
                    "derivations is refused, never resolved in favour of "
                    "the caller")
    return resolution.identities


# ══════════════════════════════════════════════════════════════════════════
# 3. Gate configuration
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GateConfig:
    """Which promotion-lock conditions apply, and any ADOPTED thresholds.

    Every ``require_*`` flag defaults to True so a caller cannot relax the
    roadmap s18.3 P7.10 promotion lock by omitting a requirement.
    """
    config_id: str
    campaign_id: str
    require_independent_holdout: bool = True
    require_parent_lineage: bool = True
    require_replay_integrity: bool = True
    require_safety_pass: bool = True
    require_rollback_target: bool = True
    require_glm_contract: bool = True
    min_runs_per_arm: Optional[int] = None
    min_effect_size: Optional[float] = None
    significance_level: Optional[float] = None
    max_exclusion_fraction: Optional[float] = None
    #: C1/C2 remediation. When True, decision records must carry a DERIVED
    #: policy identity (artifact content hashed by this module) matching their
    #: declared baseline/candidate policy hashes; an asserted-only hash is
    #: BLOCKED. Defaults to False so experimental classification keeps the
    #: historical behavior; whether adopted production configurations must set
    #: it True is an operator governance decision (PROPOSED, see
    #: evidence/GOVERNANCE_DECISIONS_20261009.jsonl). A derived-vs-declared
    #: MISMATCH refuses unconditionally even when this flag is False.
    require_policy_identity: bool = False
    #: Campaign-scoped POLICY MANIFEST binding (operator ruling 2026-10-09).
    #: When non-empty, strict re-derivation resolves policy identities from this
    #: manifest instead of from any caller. Both fields are part of
    #: ``config_digest`` and of ``to_dict()``, so an ADOPTED registry entry
    #: transitively pins them: adoption pins the config, the config pins the
    #: manifest, the manifest pins the artifact bytes. That is why no
    #: per-campaign policy anchor is added to :class:`AnchorSet` and why this is
    #: not a second authority source — it is reached THROUGH adoption.
    #:
    #: Empty by default. A config that requires policy identity WITHOUT this
    #: binding cannot be re-derived after restart and stays BLOCKED, which is the
    #: correct fail-closed outcome rather than a silent fallback to caller input.
    policy_manifest_file: str = ""
    policy_manifest_sha256: str = ""

    def __post_init__(self) -> None:
        for name in ("min_runs_per_arm", "min_effect_size", "significance_level",
                     "max_exclusion_fraction"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EvaluationGateError(f"{name} must be numeric or None, got {value!r}")
            if not math.isfinite(float(value)):
                raise EvaluationGateError(f"{name} must be finite, got {value!r}")
        # Requirement flags must be genuine booleans. Accepting 1 / "true" would
        # let a truthy non-bool smuggle authority-flag state past the promotion
        # lock, so this is an explicit type requirement, not coercion.
        for name in PROMOTION_REQUIREMENTS + ("require_policy_identity",):
            if type(getattr(self, name)) is not bool:
                raise EvaluationGateError(
                    f"{name} must be a bool, got "
                    f"{type(getattr(self, name)).__name__}")
        # The policy-manifest binding is a PATH/DIGEST PAIR. A half-configured
        # binding is refused rather than silently treated as absent, because a
        # digest without a path (or the reverse) cannot be resolved and would
        # otherwise degrade to the same BLOCKED state with no explanation.
        for name in ("policy_manifest_file", "policy_manifest_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise EvaluationGateError(f"{name} must be a string, got {value!r}")
        if bool(self.policy_manifest_file) != bool(self.policy_manifest_sha256):
            raise EvaluationGateError(
                "policy_manifest_file and policy_manifest_sha256 must be set "
                "together or both empty; a partial policy-manifest binding "
                f"got file={self.policy_manifest_file!r} "
                f"sha256={self.policy_manifest_sha256!r}")
        if self.policy_manifest_sha256 and not _is_hex_sha256(
                self.policy_manifest_sha256):
            raise EvaluationGateError(
                "policy_manifest_sha256 must be a 64-char lowercase hex "
                f"SHA-256, got {self.policy_manifest_sha256!r}")

    @property
    def config_digest(self) -> str:
        return _sha256_bytes(_stable({
            "campaign_id": self.campaign_id,
            "config_id": self.config_id,
            "max_exclusion_fraction": self.max_exclusion_fraction,
            "min_effect_size": self.min_effect_size,
            "min_runs_per_arm": self.min_runs_per_arm,
            "policy_manifest_file": self.policy_manifest_file,
            "policy_manifest_sha256": self.policy_manifest_sha256,
            "require_glm_contract": self.require_glm_contract,
            "require_independent_holdout": self.require_independent_holdout,
            "require_parent_lineage": self.require_parent_lineage,
            "require_policy_identity": self.require_policy_identity,
            "require_replay_integrity": self.require_replay_integrity,
            "require_rollback_target": self.require_rollback_target,
            "require_safety_pass": self.require_safety_pass,
            "schema_version": SCHEMA_VERSION,
            "significance_level": self.significance_level,
        }).encode())

    def to_dict(self) -> Dict[str, Any]:
        payload = {"campaign_id": self.campaign_id, "config_id": self.config_id,
                   "config_digest": self.config_digest,
                   "max_exclusion_fraction": self.max_exclusion_fraction,
                   "min_effect_size": self.min_effect_size,
                   "min_runs_per_arm": self.min_runs_per_arm,
                   "policy_manifest_file": self.policy_manifest_file,
                   "policy_manifest_sha256": self.policy_manifest_sha256,
                   "require_glm_contract": self.require_glm_contract,
                   "require_independent_holdout": self.require_independent_holdout,
                   "require_parent_lineage": self.require_parent_lineage,
                   "require_policy_identity": self.require_policy_identity,
                   "require_replay_integrity": self.require_replay_integrity,
                   "require_rollback_target": self.require_rollback_target,
                   "require_safety_pass": self.require_safety_pass,
                   "schema_version": SCHEMA_VERSION,
                   "significance_level": self.significance_level}
        return payload


# ══════════════════════════════════════════════════════════════════════════
# 4. Authoritative holdout anchor (anchor-derived, never caller-derived)
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class HoldoutDeclaration:
    """The canonical protected holdout, as declared by a PINNED anchor.

    Classification never accepts this as an input. It is produced only by
    :func:`load_authoritative_declaration`, which reads a manifest whose own
    SHA-256 is pinned in :data:`AUTHORITATIVE_ANCHORS`. A caller cannot supply a
    different expected SHA and have a dataset prove itself against it.
    """
    holdout_id: str
    campaign_id: str
    path: str
    sha256: str
    row_count: int = 0
    required_row_keys: Tuple[str, ...] = ()
    anchor_file: str = ""
    anchor_sha256: str = ""
    anchor_verified: bool = False

    def resolve(self) -> Path:
        """Resolve the canonical path INSIDE the repo root. No searching."""
        candidate = (_REPO_ROOT / self.path).resolve()
        root = _REPO_ROOT.resolve()
        if candidate != root and root not in candidate.parents:
            raise EvaluationGateError(
                f"declared holdout path escapes the repository root: {self.path!r}")
        return candidate

    def to_dict(self) -> Dict[str, Any]:
        return {"anchor_file": self.anchor_file, "anchor_sha256": self.anchor_sha256,
                "anchor_verified": self.anchor_verified, "campaign_id": self.campaign_id,
                "holdout_id": self.holdout_id, "path": self.path,
                "required_row_keys": list(self.required_row_keys),
                "row_count": self.row_count, "sha256": self.sha256}


@dataclass(frozen=True)
class AuthoritativeAnchor:
    """Result of loading the pinned anchor."""
    status: str
    declaration: Optional[HoldoutDeclaration] = None
    detail: str = ""

    @property
    def loaded(self) -> bool:
        return self.status == "LOADED"


def load_authoritative_anchor(
        anchors: Optional[AnchorSet] = None) -> AuthoritativeAnchor:
    """Load the pinned anchor and derive the canonical holdout declaration.

    Fails closed. The manifest's digest is checked against the digest PINNED IN
    THIS MODULE, so editing the manifest cannot redirect the evaluator to an
    attacker-supplied dataset.
    """
    anchors = anchors or AUTHORITATIVE_ANCHORS
    anchor_path = _REPO_ROOT / anchors.holdout_anchor_file
    if not anchor_path.is_file():
        return AuthoritativeAnchor(
            status=HOLDOUT_ANCHOR_MISSING,
            detail=f"authoritative holdout anchor is absent: {anchors.holdout_anchor_file}")
    try:
        measured = _sha256_file(anchor_path)
    except OSError as exc:
        return AuthoritativeAnchor(status=HOLDOUT_ANCHOR_MISSING, detail=str(exc))
    if measured != anchors.holdout_anchor_sha256:
        return AuthoritativeAnchor(
            status=HOLDOUT_ANCHOR_TAMPERED,
            detail=(f"authoritative holdout anchor digest differs from the pinned digest; "
                    f"measured={measured} pinned={anchors.holdout_anchor_sha256}. The "
                    f"evaluator will not trust an anchor it cannot verify."))
    try:
        payload = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        return AuthoritativeAnchor(status=HOLDOUT_ANCHOR_MALFORMED, detail=str(exc))
    dataset = payload.get("dataset")
    if not isinstance(dataset, dict):
        return AuthoritativeAnchor(status=HOLDOUT_ANCHOR_MALFORMED,
                                   detail="anchor has no dataset object")
    path = dataset.get("file")
    sha256 = dataset.get("sha256")
    rows = dataset.get("total_rows")
    if not isinstance(path, str) or not path or not _is_hex_sha256(sha256):
        return AuthoritativeAnchor(
            status=HOLDOUT_ANCHOR_MALFORMED,
            detail="anchor dataset.file / dataset.sha256 missing or malformed")
    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
        return AuthoritativeAnchor(status=HOLDOUT_ANCHOR_MALFORMED,
                                   detail="anchor dataset.total_rows missing or invalid")
    declaration = HoldoutDeclaration(
        holdout_id=str(payload.get("campaign") or path),
        campaign_id=str(payload.get("campaign") or ""),
        path=path, sha256=sha256, row_count=rows,
        required_row_keys=anchors.holdout_required_row_keys,
        anchor_file=anchors.holdout_anchor_file,
        anchor_sha256=anchors.holdout_anchor_sha256, anchor_verified=True)
    return AuthoritativeAnchor(status="LOADED", declaration=declaration)


# ══════════════════════════════════════════════════════════════════════════
# 5. Fail-closed holdout verification
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class HoldoutVerification:
    """Verification outcome. No ``PASS``-on-absence path; no substitution."""
    holdout_id: str
    status: str
    detail: str = ""
    measured_sha256: str = ""
    measured_rows: int = 0
    expected_sha256: str = ""
    substitution_performed: bool = False   # ALWAYS False, structurally

    @property
    def verified(self) -> bool:
        return self.status == HOLDOUT_VERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {"detail": self.detail, "expected_sha256": self.expected_sha256,
                "holdout_id": self.holdout_id, "measured_rows": self.measured_rows,
                "measured_sha256": self.measured_sha256, "status": self.status,
                "substitution_note": HOLDOUT_NEVER_SUBSTITUTED,
                "substitution_performed": self.substitution_performed}


def verify_holdout(declaration: HoldoutDeclaration) -> HoldoutVerification:
    """Verify a pinned canonical holdout. Returns a status; never raises.

    There is NO ``search_paths`` parameter. The declared path is resolved
    exactly, inside the repository root, and a sibling/basename match is never
    substituted. ``MISSING`` stays ``MISSING``.

    Every expected invalid-input condition yields an explicit status:
    missing, unreadable, invalid UTF-8, malformed JSONL, empty, duplicate rows,
    schema mismatch, row-count mismatch, digest mismatch, campaign mismatch,
    unexpected path.
    """
    holdout_id = declaration.holdout_id
    try:
        target = declaration.resolve()
    except EvaluationGateError as exc:
        return HoldoutVerification(holdout_id=holdout_id, status=HOLDOUT_UNEXPECTED_PATH,
                                   detail=str(exc))
    if not target.is_file():
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_MISSING,
            expected_sha256=declaration.sha256,
            detail=(f"canonical protected holdout is absent at the anchored path "
                    f"'{declaration.path}'; {HOLDOUT_NEVER_SUBSTITUTED}"))
    try:
        raw = target.read_bytes()
    except OSError as exc:
        return HoldoutVerification(holdout_id=holdout_id, status=HOLDOUT_UNREADABLE,
                                   detail=str(exc))
    measured = _sha256_bytes(raw)

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_INVALID_ENCODING, detail=str(exc),
            measured_sha256=measured, expected_sha256=declaration.sha256)

    rows: List[Any] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            return HoldoutVerification(
                holdout_id=holdout_id, status=HOLDOUT_MALFORMED,
                detail=f"line {lineno} is not valid JSON: {exc}",
                measured_sha256=measured, expected_sha256=declaration.sha256)

    if measured != declaration.sha256:
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_DIGEST_MISMATCH,
            detail="measured digest differs from the anchored digest",
            measured_sha256=measured, measured_rows=len(rows),
            expected_sha256=declaration.sha256)

    if not rows:
        return HoldoutVerification(holdout_id=holdout_id, status=HOLDOUT_EMPTY,
                                   detail="holdout file contains no rows",
                                   measured_sha256=measured,
                                   expected_sha256=declaration.sha256)

    non_objects = sum(1 for r in rows if not isinstance(r, dict))
    if non_objects:
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_SCHEMA_INVALID,
            detail=f"{non_objects} row(s) are not JSON objects",
            measured_sha256=measured, measured_rows=len(rows),
            expected_sha256=declaration.sha256)

    missing_keys = sorted({k for k in declaration.required_row_keys
                           for r in rows if k not in r})
    if missing_keys:
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_SCHEMA_INVALID,
            detail=f"rows missing anchored required keys: {missing_keys}",
            measured_sha256=measured, measured_rows=len(rows),
            expected_sha256=declaration.sha256)

    seen: Dict[str, int] = {}
    for index, r in enumerate(rows):
        key = _stable(r)
        if key in seen:
            return HoldoutVerification(
                holdout_id=holdout_id, status=HOLDOUT_DUPLICATE_ROWS,
                detail=(f"row {index} duplicates row {seen[key]}; the anchored "
                        f"dataset is append-only one-run-per-line"),
                measured_sha256=measured, measured_rows=len(rows),
                expected_sha256=declaration.sha256)
        seen[key] = index

    if declaration.row_count and len(rows) != declaration.row_count:
        return HoldoutVerification(
            holdout_id=holdout_id, status=HOLDOUT_ROW_COUNT_MISMATCH,
            detail=f"row count {len(rows)} != anchored {declaration.row_count}",
            measured_sha256=measured, measured_rows=len(rows),
            expected_sha256=declaration.sha256)

    if declaration.campaign_id:
        present = {str(r.get("campaign", "")) for r in rows}
        present.discard("")
        if present and not present <= {declaration.campaign_id}:
            return HoldoutVerification(
                holdout_id=holdout_id, status=HOLDOUT_CAMPAIGN_MISMATCH,
                detail=(f"rows carry campaign(s) {sorted(present)} which do not match "
                        f"the anchored campaign '{declaration.campaign_id}'"),
                measured_sha256=measured, measured_rows=len(rows),
                expected_sha256=declaration.sha256)

    return HoldoutVerification(
        holdout_id=holdout_id, status=HOLDOUT_VERIFIED,
        detail="presence, encoding, digest, schema, uniqueness, row count and campaign verified",
        measured_sha256=measured, measured_rows=len(rows),
        expected_sha256=declaration.sha256)


def verify_authoritative_holdout() -> HoldoutVerification:
    """Verify the ANCHORED holdout. The only holdout path classification trusts."""
    anchor = load_authoritative_anchor()
    if not anchor.loaded or anchor.declaration is None:
        return HoldoutVerification(holdout_id="unknown", status=anchor.status,
                                   detail=anchor.detail)
    return verify_holdout(anchor.declaration)


# ══════════════════════════════════════════════════════════════════════════
# 6. Statistical adequacy — fails closed, never invents a standard
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SampleEvidence:
    """Raw observed counts, validated on construction.

    ``bool`` is rejected because ``isinstance(True, int)`` is True in Python and
    ``True`` is not a sample size. Floats are rejected unless integral, and
    NaN / +-inf are rejected before any comparison, because Python's comparison
    semantics silently make ``nan < x`` False and would let NaN pass a minimum.
    """
    runs_candidate: int
    runs_baseline: int
    exclusions: int
    effect: Optional[float]

    @staticmethod
    def _require_count(name: str, value: Any) -> int:
        if value is None:
            return INVALID_EVIDENCE  # type: ignore[return-value]
        if isinstance(value, bool):
            raise EvaluationGateError(f"{name} must be an integer, got bool {value!r}")
        if isinstance(value, float):
            if not math.isfinite(value):
                raise EvaluationGateError(f"{name} must be finite, got {value!r}")
            if not value.is_integer():
                raise EvaluationGateError(f"{name} must be a whole number, got {value!r}")
            value = int(value)
        if not isinstance(value, int):
            raise EvaluationGateError(f"{name} must be an integer, got {type(value).__name__}")
        if value < 0:
            raise EvaluationGateError(f"{name} must be non-negative, got {value!r}")
        return value

    @classmethod
    def validate(cls, *, runs_candidate: Any, runs_baseline: Any,
                 exclusions: Any = 0, effect: Any = None) -> Optional["SampleEvidence"]:
        """Return the evidence, or ``None`` when any count is unusable.

        Uses an explicit allowlist rather than Python comparison behaviour so
        NaN, infinities, negatives, fractional values, ``None`` and wrong types
        are all rejected identically.
        """
        if isinstance(effect, bool):
            return None
        if effect is not None:
            if not isinstance(effect, (int, float)):
                return None
            if not math.isfinite(float(effect)):
                return None
        try:
            cand = cls._require_count("runs_candidate", runs_candidate)
            base = cls._require_count("runs_baseline", runs_baseline)
            excl = cls._require_count("exclusions", exclusions)
        except EvaluationGateError:
            return None
        if cand is INVALID_EVIDENCE or base is INVALID_EVIDENCE or excl is INVALID_EVIDENCE:
            return None
        return cls(runs_candidate=cand, runs_baseline=base, exclusions=excl,
                   effect=None if effect is None else float(effect))

    def to_dict(self) -> Dict[str, Any]:
        return {"effect": self.effect, "exclusions": self.exclusions,
                "runs_baseline": self.runs_baseline,
                "runs_candidate": self.runs_candidate}


@dataclass(frozen=True)
class AdequacyReport:
    """Observed evidence plus an EXPLICIT, derived threshold status."""
    observed_runs_candidate: int
    observed_runs_baseline: int
    observed_exclusions: int
    observed_effect: Optional[float]
    min_runs_per_arm: Optional[int]
    min_effect_size: Optional[float]
    significance_level: Optional[float]
    status: str
    detail: str = ""

    @property
    def adequate(self) -> bool:
        return self.status == ADEQUATE

    @property
    def refusing(self) -> bool:
        return self.status in (INVALID_EVIDENCE, NOT_IMPLEMENTED)

    def to_dict(self) -> Dict[str, Any]:
        return {"adequate": self.adequate, "detail": self.detail,
                "min_effect_size": self.min_effect_size,
                "min_runs_per_arm": self.min_runs_per_arm,
                "observed_effect": self.observed_effect,
                "observed_exclusions": self.observed_exclusions,
                "observed_runs_baseline": self.observed_runs_baseline,
                "observed_runs_candidate": self.observed_runs_candidate,
                "significance_level": self.significance_level, "status": self.status}


def assess_statistical_adequacy(*, runs_candidate: Any, runs_baseline: Any,
                                exclusions: Any = 0, effect: Any = None,
                                config: GateConfig) -> AdequacyReport:
    """Report statistical adequacy WITHOUT inventing a threshold.

    ``UNSPECIFIED_THRESHOLD``  no authoritative numeric requirement exists.
                                Can never be ``ADEQUATE``.
    ``NOT_IMPLEMENTED``        an ADOPTED requirement this module cannot
                                actually evaluate (e.g. a significance level,
                                which needs per-run observations). Reporting
                                ADEQUATE here is forbidden.
    ``INADEQUATE``             every evaluable adopted threshold was checked and
                                one was not met.
    ``INVALID_EVIDENCE``       the observed counts themselves are unusable.
    """
    def _report(status: str, detail: str, sample: Optional[SampleEvidence]
                ) -> AdequacyReport:
        return AdequacyReport(
            observed_runs_candidate=0 if sample is None else sample.runs_candidate,
            observed_runs_baseline=0 if sample is None else sample.runs_baseline,
            observed_exclusions=0 if sample is None else sample.exclusions,
            observed_effect=None if sample is None else sample.effect,
            min_runs_per_arm=config.min_runs_per_arm,
            min_effect_size=config.min_effect_size,
            significance_level=config.significance_level, status=status, detail=detail)

    sample = SampleEvidence.validate(runs_candidate=runs_candidate,
                                     runs_baseline=runs_baseline,
                                     exclusions=exclusions, effect=effect)
    if sample is None:
        return _report(INVALID_EVIDENCE,
                       "observed counts are unusable (NaN, infinite, negative, "
                       "fractional, boolean, None or wrong type); adequacy is refused "
                       "rather than compared", None)

    adopted = [config.min_runs_per_arm, config.min_effect_size,
               config.significance_level, config.max_exclusion_fraction]
    if all(t is None for t in adopted):
        return _report(UNSPECIFIED_THRESHOLD,
                       "the authoritative roadmap (v4.2_RSI) defines NO numeric "
                       "statistical requirement for RSI promotion; no minimum run "
                       "count, effect size or significance level is adopted, so "
                       "adequacy is UNSPECIFIED and promotion eligibility stays "
                       "BLOCKED rather than guessing a number", sample)

    if config.significance_level is not None:
        # Adopting alpha obliges us to evaluate it. We hold aggregate counts
        # only, so we CANNOT. Silently ignoring the adopted level is forbidden.
        return _report(NOT_IMPLEMENTED,
                       f"an adopted significance_level={config.significance_level} "
                       "requires per-run observations to evaluate; this module holds "
                       "aggregate counts only and will not report adequacy on an "
                       "unenforced threshold", sample)

    if config.min_runs_per_arm is not None:
        if (sample.runs_candidate < config.min_runs_per_arm
                or sample.runs_baseline < config.min_runs_per_arm):
            return _report(INADEQUATE, "observed run count below the adopted minimum "
                           "per arm", sample)
    if config.min_effect_size is not None:
        if sample.effect is None or abs(sample.effect) < config.min_effect_size:
            return _report(INADEQUATE, "observed effect below the adopted minimum "
                           "effect size", sample)
    if config.max_exclusion_fraction is not None:
        total = sample.runs_candidate + sample.runs_baseline
        if total and (sample.exclusions / total) > config.max_exclusion_fraction:
            return _report(INADEQUATE, "exclusion fraction above the adopted maximum",
                           sample)
    return _report(ADEQUATE, "every evaluable explicitly adopted threshold is met; no "
                   "threshold is inferred by this module", sample)


# ══════════════════════════════════════════════════════════════════════════
# 7. Evidence index — roadmap s19.5 GLM-contract artefacts
# ══════════════════════════════════════════════════════════════════════════

#: Roadmap s19.5 "report at minimum" list. Every entry must resolve to a
#: verified artefact under an adopted anchor before it can be anything but
#: BLOCKED.
GLM_CONTRACT_ITEMS: Tuple[str, ...] = (
    "protected_holdout_results",
    "budget_resource_accounting",
    "retention_result",
    "transfer_result",
    "stability_result",
    "rollback_availability",
)

ATTESTATION_KINDS: Tuple[str, ...] = (
    "replay_evaluation", "safety_report", "resource_budget",
    "retention_result", "transfer_result", "stability_result",
    "protocol_preregistration", "frozen_metrics", "reviewer_authority",
)

EVIDENCE_INDEX_MISSING = "NO_AUTHORITATIVE_INDEX"
EVIDENCE_INDEX_TAMPERED = "INDEX_TAMPERED"
EVIDENCE_ITEM_MISSING = "ARTEFACT_MISSING"
EVIDENCE_ITEM_DIGEST_MISMATCH = "ARTEFACT_DIGEST_MISMATCH"
EVIDENCE_ITEM_VERIFIED = "ARTEFACT_VERIFIED"


@dataclass(frozen=True)
class EvidenceItem:
    """One GLM-contract artefact resolved against the pinned evidence index."""
    kind: str
    path: str
    expected_sha256: str
    status: str
    detail: str = ""

    @property
    def verified(self) -> bool:
        return self.status == EVIDENCE_ITEM_VERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {"detail": self.detail, "expected_sha256": self.expected_sha256,
                "kind": self.kind, "path": self.path, "status": self.status}


@dataclass(frozen=True)
class EvidenceIndex:
    """The set of GLM-contract artefacts, resolved from a PINNED index.

    Today ``status`` is :data:`EVIDENCE_INDEX_MISSING` because no index has
    been established. Every item is therefore BLOCKED — which is precisely why
    ``PROMOTION_ELIGIBLE`` is unreachable.
    """
    status: str
    items: Mapping[str, EvidenceItem]
    index_file: str = ""
    detail: str = ""

    def item(self, kind: str) -> EvidenceItem:
        return self.items.get(kind, EvidenceItem(
            kind=kind, path="", expected_sha256="", status=self.status,
            detail=self.detail or "no authoritative index is adopted"))

    def to_dict(self) -> Dict[str, Any]:
        return {"detail": self.detail, "index_file": self.index_file,
                "items": {k: v.to_dict() for k, v in sorted(self.items.items())},
                "status": self.status}


def load_evidence_index(anchors: Optional[AnchorSet] = None) -> EvidenceIndex:
    """Resolve every GLM-contract artefact against the PINNED index.

    There is no caller-supplied expected digest anywhere in this path, so a
    caller cannot point the evaluator at a file it likes and declare it verified.
    """
    anchors = anchors or AUTHORITATIVE_ANCHORS
    if not anchors.evidence_index_adopted():
        return EvidenceIndex(
            status=EVIDENCE_INDEX_MISSING, items={},
            detail=("no authoritative evidence index has been adopted for the "
                    "roadmap s19.5 GLM-contract artefacts, so each is BLOCKED; a "
                    "declared reference on a decision record is a claim, not "
                    "evidence"))
    index_path = _REPO_ROOT / str(anchors.evidence_index_file)
    if not index_path.is_file():
        return EvidenceIndex(status=EVIDENCE_INDEX_MISSING, items={},
                             index_file=str(anchors.evidence_index_file),
                             detail="declared evidence index file is absent")
    measured = _sha256_file(index_path)
    if measured != anchors.evidence_index_sha256:
        return EvidenceIndex(status=EVIDENCE_INDEX_TAMPERED, items={},
                             index_file=str(anchors.evidence_index_file),
                             detail="evidence index digest differs from the pinned digest")
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        return EvidenceIndex(status=EVIDENCE_INDEX_TAMPERED, items={},
                             index_file=str(anchors.evidence_index_file), detail=str(exc))
    declared = payload.get("artefacts")
    items: Dict[str, EvidenceItem] = {}
    for kind in ATTESTATION_KINDS:
        entry = declared.get(kind) if isinstance(declared, dict) else None
        if not isinstance(entry, dict) or not _is_hex_sha256(entry.get("sha256")):
            items[kind] = EvidenceItem(kind=kind, path="", expected_sha256="",
                                       status=EVIDENCE_ITEM_MISSING,
                                       detail="index declares no verifiable artefact")
            continue
        rel = entry.get("file")
        target = _REPO_ROOT / str(rel)
        if not isinstance(rel, str) or not target.is_file():
            items[kind] = EvidenceItem(kind=kind, path=str(rel),
                                       expected_sha256=entry["sha256"],
                                       status=EVIDENCE_ITEM_MISSING,
                                       detail="declared artefact file is absent")
            continue
        try:
            artefact = _sha256_file(target)
        except OSError as exc:
            items[kind] = EvidenceItem(kind=kind, path=str(rel),
                                       expected_sha256=entry["sha256"],
                                       status=EVIDENCE_ITEM_MISSING, detail=str(exc))
            continue
        if artefact != entry["sha256"]:
            items[kind] = EvidenceItem(
                kind=kind, path=str(rel), expected_sha256=entry["sha256"],
                status=EVIDENCE_ITEM_DIGEST_MISMATCH,
                detail="artefact digest differs from the indexed digest")
            continue
        items[kind] = EvidenceItem(kind=kind, path=str(rel),
                                   expected_sha256=entry["sha256"],
                                   status=EVIDENCE_ITEM_VERIFIED,
                                   detail="artefact digest verified against the pinned index")
    return EvidenceIndex(status="LOADED", items=items,
                         index_file=str(anchors.evidence_index_file),
                         detail="evidence index loaded and verified against pinned digest")


# ══════════════════════════════════════════════════════════════════════════
# 8. Evaluation authority — everything classification is allowed to believe
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class EvaluationAuthority:
    """The complete, derived fact set for one classification.

    Constructed only by :func:`build_authority`. Classification consumes this,
    never a caller's claim about any of its fields.
    """
    config: GateConfig
    evaluator_identity: EvaluatorIdentity
    holdout: HoldoutVerification
    anchor_status: str
    adequacy: AdequacyReport
    evidence: EvidenceIndex
    #: INDEPENDENTLY RESOLVED adoption status. Never caller-supplied.
    config_adoption: "ConfigAdoption" = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, Any]:
        return {"adequacy": self.adequacy.to_dict(),
                "anchor_status": self.anchor_status,
                "config_adoption": (self.config_adoption.to_dict()
                                    if self.config_adoption is not None else None),
                "config_digest": self.config.config_digest,
                "evaluator_identity": self.evaluator_identity.to_dict(),
                "evidence_index": self.evidence.to_dict(),
                "holdout": self.holdout.to_dict()}


def build_authority(config: GateConfig,
                    *, runs_candidate: Any = None, runs_baseline: Any = None,
                    exclusions: Any = 0, effect: Any = None) -> EvaluationAuthority:
    """Derive the authoritative fact set for ``config``.

    Deliberately accepts NO evaluator identity, NO holdout declaration, NO
    holdout path, NO holdout digest, NO root, and NO boolean standing in for
    verification. Everything it reports is computed here from pinned bytes.
    """
    identity = EvaluatorIdentity.compute_current(config)
    anchor = load_authoritative_anchor()
    if anchor.loaded and anchor.declaration is not None:
        holdout = verify_holdout(anchor.declaration)
    else:
        holdout = HoldoutVerification(holdout_id="unknown", status=anchor.status,
                                      detail=anchor.detail)
    evidence = load_evidence_index()
    # Adoption is resolved INTERNALLY from pinned anchors. This function takes
    # no adoption boolean, adoption id, registry path, or registry digest, so a
    # caller cannot assert authority into existence.
    adoption = resolve_config_adoption(config)
    adequacy = assess_statistical_adequacy(
        runs_candidate=0 if runs_candidate is None else runs_candidate,
        runs_baseline=0 if runs_baseline is None else runs_baseline,
        exclusions=exclusions, effect=effect, config=config)
    return EvaluationAuthority(config=config, evaluator_identity=identity,
                               holdout=holdout, anchor_status=anchor.status,
                               adequacy=adequacy, evidence=evidence,
                               config_adoption=adoption)


# ══════════════════════════════════════════════════════════════════════════
# 9. Immutable evaluation decision record (roadmap s18.3 P7.7 / s19.5)
# ══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class EvaluationDecisionRecord:
    """Canonical immutable record of ONE evaluation decision.

    Fields that would previously have carried authority now carry CLAIMS. The
    record's own content hash proves internal consistency and nothing more: a
    record is not authoritative because it hashes correctly.
    """
    decision_id: str
    campaign_id: str
    evaluator_identity: str
    evaluator_label: str
    gate_config_digest: str
    inputs_digest: str
    holdout_id: str
    holdout_status: str
    holdout_sha256: str
    holdout_row_count: int = 0
    holdout_evaluation_refs: Tuple[str, ...] = ()
    replay_evaluation_refs: Tuple[str, ...] = ()
    metrics: Tuple[Tuple[str, Any], ...] = ()
    gate_outcomes: Tuple[Tuple[str, str], ...] = ()
    selection_history_refs: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    parent_lineage: Tuple[str, ...] = ()
    rollback_target: str = ""
    baseline_policy_hash: str = ""
    candidate_policy_hash: str = ""
    protocol_id: str = ""
    metrics_frozen_digest: str = ""
    reviewer_authority: str = ""
    runs_candidate: int = 0
    runs_baseline: int = 0
    exclusions: int = 0
    effect: Optional[float] = None
    replay_evidence_complete: bool = False
    safety_passed: bool = False
    final_state: str = ""
    schema_version: int = SCHEMA_VERSION
    _content_hash: str = field(default="", repr=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_policy_hash": self.baseline_policy_hash,
            "campaign_id": self.campaign_id,
            "candidate_policy_hash": self.candidate_policy_hash,
            "content_hash": self._content_hash,
            "decision_id": self.decision_id,
            "effect": self.effect,
            "evaluator_identity": self.evaluator_identity,
            "evaluator_label": self.evaluator_label,
            "evidence_refs": list(self.evidence_refs),
            "exclusions": self.exclusions,
            "final_state": self.final_state,
            "gate_config_digest": self.gate_config_digest,
            "gate_outcomes": [list(g) for g in self.gate_outcomes],
            "holdout_evaluation_refs": list(self.holdout_evaluation_refs),
            "holdout_id": self.holdout_id,
            "holdout_row_count": self.holdout_row_count,
            "holdout_sha256": self.holdout_sha256,
            "holdout_status": self.holdout_status,
            "inputs_digest": self.inputs_digest,
            "metrics": [list(m) for m in self.metrics],
            "metrics_frozen_digest": self.metrics_frozen_digest,
            "parent_lineage": list(self.parent_lineage),
            "protocol_id": self.protocol_id,
            "replay_evaluation_refs": list(self.replay_evaluation_refs),
            "replay_evidence_complete": self.replay_evidence_complete,
            "reviewer_authority": self.reviewer_authority,
            "rollback_target": self.rollback_target,
            "runs_baseline": self.runs_baseline,
            "runs_candidate": self.runs_candidate,
            "safety_passed": self.safety_passed,
            "schema_version": self.schema_version,
            "selection_history_refs": list(self.selection_history_refs),
        }

    def content_hash(self) -> str:
        """Digest of every substantive field, including ``schema_version``.

        The digest deliberately excludes itself (see :meth:`_hash_payload`), so
        it is well defined, and includes the schema version so a schema change
        invalidates every previously minted record.
        """
        payload = self.to_dict()
        payload.pop("content_hash", None)
        return _sha256_bytes(_stable(payload).encode())

    def is_intact(self) -> bool:
        """True when no field changed after minting.

        The dataclass is frozen, but ``object.__setattr__`` can still mutate it.
        Admission re-checks this so a record altered in-process is refused rather
        than trusted because it once hashed correctly.
        """
        return self._content_hash == self.content_hash()

    def __post_init__(self) -> None:
        computed = self.content_hash()
        if not _is_hex_sha256(computed):
            raise EvaluationGateError("content hash could not be computed")
        if self._content_hash and self._content_hash != computed:
            raise EvaluationGateError(
                "decision record content_hash mismatch — a field was altered after "
                "the record was minted")
        object.__setattr__(self, "_content_hash", computed)

    @classmethod
    def mint(cls, **kwargs: Any) -> "EvaluationDecisionRecord":
        """Mint a record. ``_content_hash`` is never caller-supplied."""
        kwargs.pop("_content_hash", None)
        return cls(**kwargs)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationDecisionRecord":
        data = dict(payload)
        declared = data.pop("content_hash", "") or ""
        for key in ("holdout_evaluation_refs", "replay_evaluation_refs",
                    "selection_history_refs", "evidence_refs", "parent_lineage"):
            if key in data and data[key] is not None:
                data[key] = tuple(data[key])
        for key in ("metrics", "gate_outcomes"):
            if key in data and data[key] is not None:
                data[key] = tuple(tuple(x) for x in data[key])
        known = {f for f in cls.__dataclass_fields__ if f != "_content_hash"}
        unknown = set(data) - known
        if unknown:
            raise EvaluationGateError(f"unknown decision record fields: {sorted(unknown)}")
        missing = {"decision_id", "campaign_id", "evaluator_identity", "evaluator_label",
                   "gate_config_digest", "inputs_digest", "holdout_id", "holdout_status",
                   "holdout_sha256"} - set(data)
        if missing:
            raise EvaluationGateError(f"incomplete decision record: {sorted(missing)}")
        if not declared:
            raise EvaluationGateError(
                "decision record carries no content_hash; an unsigned record is not "
                "admissible")
        if not _is_hex_sha256(declared):
            raise EvaluationGateError(f"malformed content_hash: {declared!r}")
        return cls(_content_hash=declared, **data)


@dataclass(frozen=True)
class EligibilityAssessment:
    """Mechanical classification of one decision record into the five states."""
    state: str
    reasons: Tuple[str, ...]
    gates: Tuple[Tuple[str, str], ...]

    def to_dict(self) -> Dict[str, Any]:
        return {"gates": [list(g) for g in self.gates], "reasons": list(self.reasons),
                "state": self.state}

    def gate(self, name: str) -> str:
        for key, value in self.gates:
            if key == name:
                return value
        return STATUS_NOT_IMPLEMENTED

    def hard_failures(self) -> Tuple[str, ...]:
        return tuple(n for n, s in self.gates if s == STATUS_REFUSE)

    def blocked_gates(self) -> Tuple[str, ...]:
        return tuple(n for n, s in self.gates if s == STATUS_BLOCKED)


# ══════════════════════════════════════════════════════════════════════════
# 10. Classification — no caller authority anywhere on this path
# ══════════════════════════════════════════════════════════════════════════


def classify_promotion_eligibility(
        record: EvaluationDecisionRecord,
        config: GateConfig,
        *,
        blocking_conditions: Tuple[str, ...] = (),
        policy_identities: Tuple[PolicyIdentity, ...] = (),
) -> EligibilityAssessment:
    """Classify a decision record. Reports; never promotes.

    The signature is the remediation: there is no ``independent_holdout``
    boolean, no caller-supplied ``AdequacyReport``, no caller-supplied
    evaluator identity, and no caller-supplied gate digest. Every gate below is
    DERIVED by :func:`build_authority` and then COMPARED against the record.

    ``policy_identities`` carries observations produced by
    :func:`derive_policy_identity` — artifact CONTENT hashed inside this
    module — never caller-computed digests. See section 2c.

    Fail-closed precedence:

    1. a REFUSE gate (identity/config/holdout fabrication, invalid evidence)
                                                   -> ``UNVERIFIABLE_INPUTS``
    2. the decision is a replay/local selection with no holdout evaluation
                                                   -> ``LOCAL_REPLAY``
    3. the anchored holdout is not VERIFIED      -> ``UNVERIFIABLE_INPUTS``
    4. statistical adequacy not ADEQUATE         -> ``STATISTICALLY_INADEQUATE``
    5. verified holdout + adequate, open gates   -> ``INDEPENDENT_HOLDOUT``
    6. every gate PASS                           -> ``PROMOTION_ELIGIBLE``
    """
    gates: List[Tuple[str, str]] = []
    reasons: List[str] = []

    authority = build_authority(
        config, runs_candidate=record.runs_candidate, runs_baseline=record.runs_baseline,
        exclusions=record.exclusions, effect=record.effect)
    return _classify_with_authority(record, config, authority,
                                    blocking_conditions=blocking_conditions,
                                    policy_identities=policy_identities)


def _classify_with_authority(record: EvaluationDecisionRecord, config: GateConfig,
                             authority: EvaluationAuthority, *,
                             blocking_conditions: Tuple[str, ...] = (),
                             policy_identities: Tuple[PolicyIdentity, ...] = ()
                             ) -> EligibilityAssessment:
    """Classify a record against ONE already-derived authority observation.

    INTERNAL. There is deliberately no caller-supplied ``authority`` parameter on
    :func:`classify_promotion_eligibility`: authority is always derived here or
    by the ledger, never asserted. Splitting the body out is what lets the
    ledger derive authority exactly ONCE per admission and reuse that single
    observation for the state, gate and evaluation-input checks, instead of
    re-reading pinned anchors three times and risking a mid-admission change.
    """
    gates: List[Tuple[str, str]] = []
    reasons: List[str] = []

    identity = authority.evaluator_identity
    holdout = authority.holdout
    evidence = authority.evidence

    for condition in blocking_conditions:
        gates.append((f"blocking_condition:{condition}", STATUS_BLOCKED))
        reasons.append(f"open blocking condition reported by the evaluator: {condition}")

    # ── A. evaluator identity, derived and compared ────────────────────────
    if not identity.complete:
        gates.append(("evaluator_identity_current", STATUS_REFUSE))
        reasons.append("authoritative evaluator identity is incomplete; components "
                       f"unreadable: {list(identity.missing_components)}")
    elif EvaluatorIdentity.is_placeholder(record.evaluator_identity):
        gates.append(("evaluator_identity_current", STATUS_REFUSE))
        reasons.append(f"decision record carries a placeholder/non-digest evaluator "
                       f"identity {record.evaluator_identity!r}; presence of a string "
                       "is not authority")
    elif record.evaluator_identity != identity.identity:
        gates.append(("evaluator_identity_current", STATUS_REFUSE))
        stale = ("stale or foreign" if _is_hex_sha256(record.evaluator_identity)
                 else "malformed")
        reasons.append(f"{stale} evaluator identity on the decision record does not "
                       f"match the authoritative identity derived from the current "
                       f"evaluator modules for this config")
    else:
        gates.append(("evaluator_identity_current", STATUS_PASS))

    # ── B0. configuration adoption, INTERNALLY resolved ────────────────────
    # A caller-created config that is internally self-consistent, whose digest
    # matches, and whose evaluator identity matches is still NOT authoritative.
    # Only an independently resolved, source-pinned adoption registry confers
    # authority. Experimental use of the same config is unaffected.
    adoption = authority.config_adoption
    adopted = adoption is not None and adoption.adopted
    gates.append(("configuration_adopted", STATUS_PASS if adopted else STATUS_REFUSE))
    # The resolved status is always reported, adopted or not, so the precise
    # adoption condition is observable rather than inferable.
    gates.append(("configuration_adoption_status",
                  adoption.status if adoption is not None else ADOPTION_UNADOPTED))
    if not adopted:
        reasons.append(f"configuration adoption: "
                       f"{adoption.status if adoption is not None else ADOPTION_UNADOPTED}: "
                       f"{adoption.detail if adoption is not None else 'not resolved'}")

    # ── B. gate config identity, derived and compared ──────────────────────
    if record.gate_config_digest != config.config_digest:
        gates.append(("gate_config_matches", STATUS_REFUSE))
        reasons.append("decision record gate_config_digest does not match the digest of "
                       "the gate configuration actually used to classify it")
    else:
        gates.append(("gate_config_matches", STATUS_PASS))

    # ── C. campaign binding ────────────────────────────────────────────────
    if record.campaign_id != config.campaign_id:
        gates.append(("campaign_binding", STATUS_REFUSE))
        reasons.append(f"decision record campaign {record.campaign_id!r} does not match "
                       f"gate config campaign {config.campaign_id!r}")
    else:
        gates.append(("campaign_binding", STATUS_PASS))

    # ── C2. policy identity binding (C1/C2 remediation) ────────────────────
    # The record's baseline/candidate policy hashes are caller-supplied
    # strings. They verify only against a DERIVED identity (artifact content
    # hashed in this module). A derived-vs-declared mismatch refuses
    # unconditionally; a missing/asserted-only binding is BLOCKED when the
    # config requires policy identity, and emits no gate otherwise
    # (historical asserted-hash behavior, preserved for experimental use).
    for pi_gate, pi_status, pi_detail in verify_policy_identity(
            record, effective_policy_identities(config, policy_identities),
            require_binding=config.require_policy_identity):
        gates.append((pi_gate, pi_status))
        if pi_status != STATUS_PASS:
            reasons.append(f"{pi_gate}: {pi_detail}")

    # ── D. holdout anchor and verification, both derived ───────────────────
    gates.append(("holdout_anchor", STATUS_PASS if authority.anchor_status == "LOADED"
                  else STATUS_REFUSE))
    if authority.anchor_status != "LOADED":
        reasons.append(f"authoritative holdout anchor is {authority.anchor_status}: "
                       f"{holdout.detail}")

    holdout_status = holdout.status
    gates.append(("holdout_verification",
                  STATUS_PASS if holdout.verified else STATUS_BLOCKED))
    if not holdout.verified:
        reasons.append(f"anchored protected holdout verification is {holdout_status}: "
                       f"{holdout.detail}; {HOLDOUT_NEVER_SUBSTITUTED}")

    # The record's holdout fields are CLAIMS. They must agree with the derived
    # facts, and any disagreement is a detected fabrication.
    claims_holdout = bool(record.holdout_evaluation_refs)
    if claims_holdout:
        if record.holdout_status != holdout_status:
            gates.append(("record_holdout_consistent", STATUS_REFUSE))
            reasons.append(
                f"decision record asserts holdout_status={record.holdout_status!r} but "
                f"the evaluator's own verification of the anchored holdout returned "
                f"{holdout_status!r}; the asserted status is ignored and the "
                f"fabrication is refused")
        anchor_decl = load_authoritative_anchor().declaration
        if anchor_decl is not None:
            if (record.holdout_sha256 != anchor_decl.sha256
                    or record.holdout_id != anchor_decl.holdout_id
                    or record.holdout_row_count != anchor_decl.row_count):
                gates.append(("holdout_identity_anchored", STATUS_REFUSE))
                reasons.append("decision record holdout identity does not match the "
                               "committed anchor; a dataset may not prove itself "
                               "against a caller-supplied digest")
            else:
                gates.append(("holdout_identity_anchored", STATUS_PASS))
        else:
            gates.append(("holdout_identity_anchored", STATUS_REFUSE))
    else:
        gates.append(("record_holdout_consistent", STATUS_NOT_IMPLEMENTED))
        gates.append(("holdout_identity_anchored", STATUS_NOT_IMPLEMENTED))

    # ── E. independent holdout, DERIVED (never a caller boolean) ────────────
    if config.require_independent_holdout:
        gates.append(("independent_holdout",
                      STATUS_PASS if (holdout.verified and claims_holdout)
                      else STATUS_BLOCKED))

    # ── F. statistical adequacy, DERIVED from validated counts ──────────────
    adequacy = authority.adequacy
    adequacy_gate = (STATUS_REFUSE if adequacy.refusing
                     else STATUS_PASS if adequacy.status == ADEQUATE
                     else STATUS_BLOCKED)
    gates.append(("statistical_adequacy", adequacy_gate))
    if adequacy_gate != STATUS_PASS:
        reasons.append(f"statistical adequacy is {adequacy.status}: {adequacy.detail}")

    # ── G. evidence-derived s19.5 GLM-contract gates ───────────────────────
    def _artefact_gate(gate_name: str, kind: str, declared_refs: Sequence[str]) -> None:
        item = evidence.item(kind)
        if item.verified:
            gates.append((gate_name, STATUS_PASS))
            return
        detail = (f"declared {len(declared_refs)} reference(s)" if declared_refs
                  else "no reference declared")
        gates.append((gate_name, STATUS_BLOCKED))
        reasons.append(f"{gate_name}: {item.status} ({item.detail}); {detail}. A "
                       f"declared reference is a claim, not verified evidence")

    def _declared_and_verified(gate_name: str, kind: str, declared: str) -> None:
        """Declaration is NECESSARY but never SUFFICIENT.

        A roadmap s19.5 pre-registration item passes only when the record names
        it AND a pinned-index artefact verifies it. A free-text identifier on
        the record can therefore never turn this gate green.
        """
        item = evidence.item(kind)
        if not declared:
            gates.append((gate_name, STATUS_BLOCKED))
            reasons.append(f"{gate_name}: not declared (roadmap s19.5 GLM contract)")
            return
        if item.verified:
            gates.append((gate_name, STATUS_PASS))
            return
        gates.append((gate_name, STATUS_BLOCKED))
        reasons.append(f"{gate_name}: declared as {declared!r} but the artefact is "
                       f"{item.status} ({item.detail}); a declared identifier is not "
                       f"verified evidence")

    if config.require_replay_integrity:
        _artefact_gate("replay_evidence_complete", "replay_evaluation",
                       record.replay_evaluation_refs)
    if config.require_safety_pass:
        _artefact_gate("safety", "safety_report", record.evidence_refs)
    if config.require_glm_contract:
        _artefact_gate("resource_budget", "resource_budget", ())
        _artefact_gate("retention_result", "retention_result", ())
        _artefact_gate("transfer_result", "transfer_result", ())
        _artefact_gate("stability_result", "stability_result", ())
        _declared_and_verified("protocol_preregistered", "protocol_preregistration",
                               record.protocol_id)
        _declared_and_verified("metrics_frozen", "frozen_metrics",
                               record.metrics_frozen_digest)
        _declared_and_verified("reviewer_authority", "reviewer_authority",
                               record.reviewer_authority)

    # ── H. structural promotion-lock conditions (P7.10) ────────────────────
    if config.require_parent_lineage:
        ok = bool(record.parent_lineage) and bool(record.candidate_policy_hash)
        gates.append(("parent_lineage", STATUS_PASS if ok else STATUS_REFUSE))
        if not ok:
            reasons.append("candidate has no parent lineage / policy hash (P7.10)")
    if config.require_rollback_target:
        ok = bool(record.rollback_target)
        gates.append(("rollback_target", STATUS_PASS if ok else STATUS_REFUSE))
        if not ok:
            reasons.append("no rollback target recorded (P7.10)")

    refused = [n for n, s in gates if s == STATUS_REFUSE]
    blocked = [n for n, s in gates if s == STATUS_BLOCKED]

    if refused:
        return EligibilityAssessment(STATE_UNVERIFIABLE_INPUTS, tuple(reasons),
                                     tuple(gates))

    if not claims_holdout:
        reasons.append("no verified independent holdout: replay/local selection can "
                       "prove only a historical property (roadmap L25, P8.9); "
                       "transfer and stability claims are not established")
        return EligibilityAssessment(STATE_LOCAL_REPLAY, tuple(reasons), tuple(gates))

    if not holdout.verified:
        return EligibilityAssessment(STATE_UNVERIFIABLE_INPUTS, tuple(reasons),
                                     tuple(gates))

    if adequacy.status != ADEQUATE:
        return EligibilityAssessment(STATE_STATISTICALLY_INADEQUATE, tuple(reasons),
                                     tuple(gates))

    if blocked:
        # A verified protected holdout was evaluated, but open conditions remain.
        # Deliberately distinct from PROMOTION_ELIGIBLE.
        return EligibilityAssessment(STATE_INDEPENDENT_HOLDOUT, tuple(reasons),
                                     tuple(gates))

    return EligibilityAssessment(STATE_PROMOTION_ELIGIBLE, tuple(reasons), tuple(gates))


# ══════════════════════════════════════════════════════════════════════════
# 11. Reproducibility + hardened append-only decision ledger
# ══════════════════════════════════════════════════════════════════════════


def inputs_digest(campaign_id: str, holdout: HoldoutVerification,
                  config: GateConfig, identity: EvaluatorIdentity,
                  selection_history_refs: Tuple[str, ...] = ()) -> str:
    """Digest the IMMUTABLE INPUT set of an evaluation.

    Inputs and outputs stay separated, so identical inputs always yield the same
    digest and therefore the same gate semantics on replay.
    """
    return _sha256_bytes(_stable({
        "campaign_id": campaign_id,
        "evaluator_identity": identity.identity,
        "gate_config_digest": config.config_digest,
        "holdout_id": holdout.holdout_id,
        "holdout_sha256": holdout.measured_sha256,
        "holdout_status": holdout.status,
        "schema_version": SCHEMA_VERSION,
        "selection_history_refs": list(selection_history_refs),
    }).encode())


def derive_evaluation_inputs_digest(record: EvaluationDecisionRecord,
                                   authority: EvaluationAuthority) -> str:
    """Digest of the EVALUATION INPUTS alone.

    This is deliberately NOT record identity. ``decision_id`` names the
    decision record, not the experiment, so it is EXCLUDED: binding it here
    would let two otherwise identical evaluations of the same inputs look like
    two different experiments, which would silently defeat the same-input
    lineage guard in :meth:`DecisionLedger._check_lineage`.

    Bound here: campaign identity, baseline and candidate policy hashes, the
    DERIVED evaluator identity and gate-config digest, the DERIVED holdout
    identity/status, the DERIVED statistical-adequacy status, configuration
    adoption identity, and the frozen selection-history references.

    Record-supplied aggregate VALUES never enter this digest: a numeric
    assertion must not be able to masquerade as a different measured
    experiment. Those are removed from the authoritative path in the
    measurement-containment phase.
    """
    return _sha256_bytes(_stable({
        "baseline_policy_hash": record.baseline_policy_hash,
        "campaign_id": record.campaign_id,
        "candidate_policy_hash": record.candidate_policy_hash,
        "config_adoption_id": ("" if authority.config_adoption is None
                               else authority.config_adoption.adoption_id),
        "config_adoption_status": (ADOPTION_UNADOPTED
                                   if authority.config_adoption is None
                                   else authority.config_adoption.status),
        "config_adoption_version": (None if authority.config_adoption is None
                                    else authority.config_adoption.version),
        "config_registry_digest": ("" if authority.config_adoption is None
                                   else authority.config_adoption.registry_digest),
        "evaluator_identity": authority.evaluator_identity.identity,
        "gate_config_digest": authority.config.config_digest,
        "holdout_id": authority.holdout.holdout_id,
        "holdout_measured_sha256": authority.holdout.measured_sha256,
        "holdout_status": authority.holdout.status,
        "schema_version": SCHEMA_VERSION,
        "selection_history_refs": list(record.selection_history_refs),
        "statistical_adequacy_status": authority.adequacy.status,
    }).encode())


class DecisionLedger:
    """Append-only decision ledger with ADMISSION verified against authority.

Admission is no longer a content-hash self-consistency check. A record is
    admitted only when the evaluator's own derived authority agrees with it:
    current evaluator identity, matching gate config identity, and a holdout
    claim consistent with the evaluator's own verification.

    CONTAINMENT INVARIANT (the submitted record must equal the derived truth)::

        record.final_state      == assessment.state
        record.gate_outcomes    == assessment.gates
        record.inputs_digest    == derive_evaluation_inputs_digest(record, authority)

    A contradiction is REJECTED. The submitted record is never silently
    rewritten: rejecting preserves both the caller's claim and the evaluator's
    derived answer as separately observable facts.

    Two representations are kept strictly apart:

    ``historical_states()``
        the ``final_state`` strings actually STORED in the ledger. These are
        claims that were validated at admission time. They are audit material,
        never current authority.
    ``final_states(config)``
        states re-DERIVED right now against current authority. Requires a
        config; a record whose fresh derivation contradicts its stored claim is
        excluded, so forged eligibility cannot surface as current authority.

    Lineage is monotonic and ordered by INSERTION, not by lexical decision id
    (roadmap INV-21 lineage-complete, L26 parent/supersedes lineage).
    """

    def __init__(self, path: Path):
        self._path = Path(path)
        self._index: Dict[str, EvaluationDecisionRecord] = {}
        self._order: List[str] = []
        self._lineage: Dict[str, str] = {}
        if self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = EvaluationDecisionRecord.from_dict(json.loads(line))
                existing = self._index.get(record.decision_id)
                if existing is not None and existing.content_hash() != record.content_hash():
                    raise EvaluationGateError(
                        f"decision ledger conflict for '{record.decision_id}'")
                if existing is None:
                    self._order.append(record.decision_id)
                self._index[record.decision_id] = record
                if record.candidate_policy_hash:
                    self._lineage[record.candidate_policy_hash] = record.final_state

    @property
    def path(self) -> Path:
        return self._path

    def _effective_policy_identities(
            self, record: EvaluationDecisionRecord, config: GateConfig,
            supplied: Tuple[PolicyIdentity, ...]) -> Tuple[PolicyIdentity, ...]:
        """Ledger-side view of :func:`effective_policy_identities`.

        Kept as a method so the admission path reads explicitly, but it adds no
        behaviour of its own: the trusted resolution is applied inside
        :func:`_classify_with_authority`, so classification and admission cannot
        disagree about which identities govern.
        """
        return effective_policy_identities(config, supplied)

    def _derive(self, record: EvaluationDecisionRecord, config: GateConfig,
                policy_identities: Tuple[PolicyIdentity, ...] = ()
                ) -> Tuple[EvaluationAuthority, EligibilityAssessment]:
        """Derive authority ONCE and classify against that same observation.

        State, gates and the evaluation-input binding are all judged against ONE
        consistent authority object. ``_classify_with_authority`` is internal and
        takes no caller-supplied authority, so a single derivation per admission is
        guaranteed rather than merely intended.
        """
        authority = build_authority(
            config, runs_candidate=record.runs_candidate,
            runs_baseline=record.runs_baseline, exclusions=record.exclusions,
            effect=record.effect)
        return authority, _classify_with_authority(
            record, config, authority, policy_identities=policy_identities)

    def verify_admission(self, record: EvaluationDecisionRecord,
                         config: GateConfig,
                         policy_identities: Tuple[PolicyIdentity, ...] = ()
                         ) -> EligibilityAssessment:
        """Derive and validate admission. Submitted state is NOT authority.

        Raises :class:`EvaluationGateError` on any refusal gate or on a
        contradiction between the submitted authoritative fields and the freshly
        derived values. ``policy_identities`` (derived via
        :func:`derive_policy_identity`) is verified as part of admission.

        A BLOCKED policy-identity gate is additionally an ADMISSION failure when
        ``config.require_policy_identity`` is True. Classification and admission
        are deliberately different questions: classification asks what a record
        currently demonstrates (an unverified policy identity is BLOCKED, and the
        record simply cannot reach ``PROMOTION_ELIGIBLE``), while admission asks
        whether a config that has declared the binding mandatory will accept an
        unverified record into its ledger at all. Without this distinction a
        requiring config would silently accept records whose policy identity was
        never bound, which is exactly the C1/C2 gap the flag exists to close.
        """
        authority, assessment = self._derive(record, config, policy_identities)
        refused = assessment.hard_failures()
        if refused:
            raise EvaluationGateError(
                f"decision {record.decision_id!r} refused at admission by gates "
                f"{list(refused)}; derived state={assessment.state}")
        if config.require_policy_identity:
            unbound = tuple(n for n, s in assessment.gates
                            if s == STATUS_BLOCKED and n.startswith("policy_identity_"))
            if unbound:
                raise EvaluationGateError(
                    f"decision {record.decision_id!r} refused at admission by gates "
                    f"{list(unbound)}; this configuration requires a DERIVED policy "
                    "identity and no verified binding was supplied")
        if record.final_state not in EVALUATION_STATES:
            raise EvaluationGateError(
                f"final_state {record.final_state!r} is not an evaluation state; "
                f"gate statuses such as BLOCKED/REFUSE are not final states "
                f"(expected one of {list(EVALUATION_STATES)})")
        if record.final_state != assessment.state:
            raise EvaluationGateError(
                f"final_state mismatch for {record.decision_id!r}: "
                f"submitted={record.final_state!r} derived={assessment.state!r}")
        self._validate_gate_names(record.gate_outcomes, record.decision_id)
        self._validate_gate_names(assessment.gates, record.decision_id)

        # Normalise to the gate's own key/status pairs. A record round-tripped
        # through JSON carries lists rather than tuples, and key ORDER is not a
        # security property: the SET of (gate, status) pairs must match exactly,
        # so a rewritten or dropped gate is still caught. Duplicate names are
        # rejected above, BEFORE this set conversion, because a set would erase
        # them.
        submitted_gates = tuple(sorted((str(n), str(s))
                                       for n, s in record.gate_outcomes))
        derived_gates = tuple(sorted((str(n), str(s))
                                     for n, s in assessment.gates))
        if submitted_gates != derived_gates:
            missing = sorted(set(derived_gates) - set(submitted_gates))
            extra = sorted(set(submitted_gates) - set(derived_gates))
            raise EvaluationGateError(
                f"gate_outcomes mismatch for {record.decision_id!r}: "
                f"submitted={len(record.gate_outcomes)} gate(s), "
                f"derived={len(assessment.gates)}; missing={missing} extra={extra}")
        if record.inputs_digest != derive_evaluation_inputs_digest(record, authority):
            raise EvaluationGateError(
                f"inputs_digest mismatch for {record.decision_id!r}: the submitted "
                f"digest does not bind this record to the currently derived inputs")
        return assessment

    @staticmethod
    def _validate_gate_names(gates: Sequence[Tuple[str, str]], decision_id: str) -> None:
        """Reject duplicate gate NAMES before any set/dict normalisation.

        Converting to a set would silently collapse ``("safety","PASS")`` and
        ``("safety","REFUSE")`` into one entry, hiding a contradiction. Both
        shapes are refused: the same name twice, and the same name with two
        different statuses. Canonical ordering is applied only for comparison,
        after this check.
        """
        seen: Dict[str, str] = {}
        for name, status in gates:
            key = str(name)
            if key in seen:
                detail = (f"duplicate gate name {key!r} with statuses "
                          f"{seen[key]!r} and {str(status)!r}"
                          if seen[key] != str(status)
                          else f"duplicate gate name {key!r} with status {seen[key]!r}")
                raise EvaluationGateError(
                    f"gate_outcomes for {decision_id!r} contain a {detail}; gate names "
                    "must be unique or the outcome is ambiguous")
            seen[key] = str(status)

    def _check_lineage(self, record: EvaluationDecisionRecord,
                       assessment: EligibilityAssessment) -> None:
        key = record.candidate_policy_hash
        if not key:
            return
        prior_record = self._latest_for_candidate(key)
        if prior_record is None or prior_record.final_state == record.final_state:
            return
        if record.final_state != STATE_PROMOTION_ELIGIBLE:
            return
        previous = prior_record.final_state
        if not record.inputs_digest:
            raise EvaluationGateError(
                f"lineage violation: candidate {key[:12]} moves from {previous!r} to "
                f"PROMOTION_ELIGIBLE without a declared evaluation inputs_digest")
        if prior_record.inputs_digest == record.inputs_digest:
            raise EvaluationGateError(
                f"lineage violation: candidate {key[:12]} moves from {previous!r} to "
                f"PROMOTION_ELIGIBLE on the SAME evaluation inputs as the preceding "
                f"decision {prior_record.decision_id!r}. A superseding decision must "
                f"prove why the old state no longer applies via a genuinely new "
                f"evaluation (roadmap INV-21, L26).")
        if prior_record.decision_id not in record.parent_lineage:
            raise EvaluationGateError(
                f"lineage violation: superseding decision {record.decision_id!r} does "
                f"not name the superseded decision {prior_record.decision_id!r} in its "
                f"parent_lineage (roadmap INV-21)")

    def _latest_for_candidate(self, candidate_hash: str
                              ) -> Optional[EvaluationDecisionRecord]:
        """Most recently INSERTED record for a candidate (never lexical order)."""
        latest = None
        for decision_id in self._order:
            candidate = self._index.get(decision_id)
            if candidate is not None and candidate.candidate_policy_hash == candidate_hash:
                latest = candidate
        return latest

    def append(self, record: EvaluationDecisionRecord,
               config: Optional[GateConfig] = None,
               policy_identities: Tuple[PolicyIdentity, ...] = ()) -> str:
        """Append a decision record after verifying it against derived authority.

        Order is deliberate (roadmap §19.5 / P7.10 fail-closed):

        1. record type, then the required config
        2. the record must still be intact (unchanged since minting)
        3. derive authority ONCE and classify (with any policy identities)
        4. reject refusal gates
        5. reject state, gate-outcome and input-digest contradictions
        6. duplicate/content conflict handling — AFTER verification, so an
           identical stored record can never bypass fresh authority checks
        7. lineage monotonicity
        8. persist the validated record exactly as submitted
        """
        if not isinstance(record, EvaluationDecisionRecord):
            raise EvaluationGateError("DecisionLedger accepts only decision records")
        if config is None:
            raise EvaluationGateError(
                "DecisionLedger.append requires the GateConfig used to classify this "
                "record; admission is verified against derived authority, not against "
                "the record's own content hash")
        if not record.is_intact():
            raise EvaluationGateError(
                f"decision {record.decision_id!r} changed after minting; admission "
                "refuses a record whose content hash no longer matches its fields")

        assessment = self.verify_admission(record, config, policy_identities)

        existing = self._index.get(record.decision_id)
        if existing is not None:
            if existing.content_hash() == record.content_hash():
                return record.decision_id      # idempotent, but only after checks
            raise EvaluationGateError(
                f"conflicting decision record for {record.decision_id!r}; the ledger "
                "is append-only and will not rewrite history")

        self._check_lineage(record, assessment)

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(_stable(record.to_dict()) + "\n")
        self._index[record.decision_id] = record
        self._order.append(record.decision_id)
        if record.candidate_policy_hash:
            self._lineage[record.candidate_policy_hash] = record.final_state
        return record.decision_id

    def get(self, decision_id: str) -> Optional[EvaluationDecisionRecord]:
        """Audit read. Returns the STORED record; not a claim of current authority."""
        return self._index.get(decision_id)

    def all(self) -> List[EvaluationDecisionRecord]:
        """Audit read in insertion order. Not a claim of current authority."""
        return [self._index[d] for d in self._order if d in self._index]

    def insertion_order(self) -> Tuple[str, ...]:
        return tuple(self._order)

    def historical_states(self) -> Dict[str, str]:
        """The ``final_state`` strings STORED in the ledger.

        AUDIT MATERIAL ONLY. These were validated when admitted, but they are
        claims, not current authority; use :meth:`final_states` for that.
        """
        return dict(self._lineage)

    def final_states(self, config: Optional[GateConfig] = None) -> Dict[str, str]:
        """States re-DERIVED now against current authority.

        ``config`` is REQUIRED: without it there is no current authority to
        derive against. A record whose fresh derivation disagrees with its
        stored claim, or that now carries a REFUSE gate, is EXCLUDED, so a
        forged or stale eligibility string can never surface here.

        Under ``require_policy_identity`` with a pinned, adopted policy manifest,
        policy identities are re-derived from the trusted artifacts inside the
        admission step, so an honestly admitted strict-mode record IS readable
        again after a restart with no caller input. There is deliberately no
        parameter for supplying identities here: a pass-through would let a
        caller assert its way back into authority.
        """
        if config is None:
            raise EvaluationGateError(
                "final_states(config) requires the GateConfig used to classify these "
                "records; stored states are historical claims, not current authority. "
                "Use historical_states() if you explicitly want the stored strings.")
        verified: Dict[str, str] = {}
        for decision_id in self._order:
            record = self._index.get(decision_id)
            if record is None or not record.candidate_policy_hash:
                continue
            try:
                assessment = self.verify_admission(record, config)
            except EvaluationGateError:
                continue          # contradicted / refused: not current authority
            if record.final_state == assessment.state:
                verified[record.candidate_policy_hash] = assessment.state
        return verified

    def current_authority(self, decision_id: str, config: GateConfig
                          ) -> Optional[EligibilityAssessment]:
        """Freshly derived assessment for a stored record, or ``None``.

        ``None`` means the stored record is no longer current authority
        (contradicted, refused, or unverifiable) — it is still readable through
        :meth:`get` as historical material.

        Like :meth:`final_states`, this re-derives strict-mode policy identity
        from the trusted artifacts named by the adopted config. It accepts no
        caller-supplied identity.
        """
        record = self._index.get(decision_id)
        if record is None:
            return None
        try:
            return self.verify_admission(record, config)
        except EvaluationGateError:
            return None


def recompute_gate_outcomes(record: EvaluationDecisionRecord, config: GateConfig,
                            blocking_conditions: Tuple[str, ...] = (),
                            ) -> Tuple[Tuple[str, str], ...]:
    """Re-derive a record's gate semantics from derived authority.

    Pure: writes nothing, touches no ledger or evidence store. Reproducing an
    old decision therefore cannot fabricate authority either.
    """
    return classify_promotion_eligibility(
        record, config, blocking_conditions=blocking_conditions).gates