"""API key authentication with scope-based access control."""
import hashlib
import logging
import os
import secrets
import time
from fastapi import Header, HTTPException
from typing import Optional

logger = logging.getLogger("orchestrator.auth")

API_KEYS: dict[str, dict] = {}

SCOPES = {
    "admin": [
        "engagements:rw", "engagements:r",
        "agents:rw", "agents:r",
        "findings:rw", "findings:r",
        "config:rw", "config:r",
        "logs:rw", "logs:r",
        "agent:execute", "agent:read",
        "tools:read", "tools:execute",
        "sessions:rw", "sessions:r",
    ],
    "operator": [
        "engagements:rw", "engagements:r",
        "agents:r",
        "findings:rw",
        "config:r",
        "agent:execute", "agent:read",
        "tools:read", "tools:execute",
        "sessions:rw", "sessions:r",
    ],
    "viewer": [
        "engagements:r",
        "findings:r",
        "agent:read",
        "tools:read",
        "sessions:r",
    ],
    "agent": [
        "agents:rw",
        "findings:w",
        "agent:execute",
    ],
}


# Whitelist of scopes allowed to be appended via env var extra scopes
EXTRA_SCOPE_WHITELIST = {
    "engagements:rw", "engagements:r",
    "agents:rw", "agents:r",
    "findings:rw", "findings:r",
    "config:rw", "config:r",
    "logs:rw", "logs:r",
    "agent:execute", "agent:read",
    "tools:read", "tools:execute",
    "sessions:rw", "sessions:r",
}


def load_keys():
    """Load API keys from environment variables.
    
    Expected format:
        RAPHAEL_KEY_<name>=<role>[,<extra_scope>...]|<api_key>
    
    Example:
        RAPHAEL_KEY_admin=admin,agent:execute|my-secret-key-here
    """
    for var, val in os.environ.items():
        if var.startswith("RAPHAEL_KEY_"):
            try:
                parts = val.split("|", 1)
                if len(parts) != 2:
                    continue
                scopes_str, key = parts
                kh = hashlib.sha256(key.encode()).hexdigest()
                scope_list = scopes_str.split(",")
                role = scope_list[0] if scope_list[0] in SCOPES else "viewer"
                resolved_scopes = list(SCOPES.get(role, []))
                for s in scope_list[1:]:
                    if s in EXTRA_SCOPE_WHITELIST:
                        resolved_scopes.append(s)
                API_KEYS[kh] = {
                    "name": var,
                    "scopes": list(set(resolved_scopes)),
                    "created": time.time(),
                }
            except Exception:
                continue

    legacy_key = os.getenv("API_KEY", "")
    if legacy_key:
        kh = hashlib.sha256(legacy_key.encode()).hexdigest()
        if kh not in API_KEYS:
            API_KEYS[kh] = {
                "name": "API_KEY_legacy",
                "scopes": SCOPES.get("admin", []),
                "created": time.time(),
            }


def require_scope(*scopes: str):
    """FastAPI dependency that requires the given scopes."""
    async def dependency(authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        key = authorization[7:]
        kh = hashlib.sha256(key.encode()).hexdigest()
        if kh not in API_KEYS:
            raise HTTPException(status_code=401, detail="Unknown API key")
        entry = API_KEYS[kh]
        for needed in scopes:
            if needed not in entry["scopes"]:
                raise HTTPException(status_code=403, detail=f"Scope '{needed}' required")
        return entry
    return dependency


def generate_key(role: str = "operator") -> tuple[str, str]:
    """Generate a new API key for a given role. Returns (raw_key, formatted_string)."""
    key = secrets.token_hex(32)
    kh = hashlib.sha256(key.encode()).hexdigest()
    API_KEYS[kh] = {
        "name": f"key_{role}_{int(time.time())}",
        "scopes": SCOPES.get(role, SCOPES["viewer"]),
        "created": time.time(),
    }
    return key, f"{role}|{','.join(API_KEYS[kh]['scopes'])}|{key}"


class WeldNotAuthorized(Exception):
    """Fail-closed denial for AM-4 welded paths (v4.1 AM-4 / ADR-012).

    Raised when a welded legacy execution site is invoked without a valid
    Broker-issued authorization. The message carries the WELD_SET path id and
    the weld ticket. Callers must NOT catch-and-continue past this exception;
    HTTP handlers map it to 403 via require_broker_mediation.
    """


def enforce_broker_mediation(
    *,
    target: str,
    action_type: str,
    capability: str,
    method: str,
    impact_estimate: float,
    argv: tuple = (),
    broker=None,
    path_id: str = "",
    weld_ticket: str = "WELD-AM4",
):
    """AM-4 weld gate: propose to the canonical Broker PDP and enforce.

    Builds the canonical broker via the bootstrap-v0/Scope-v0 factory when no
    broker is supplied, proposes the action with the caller's exact dimensions,
    and returns the receipt iff the decision is AUTHORIZED. Any other outcome
    (DENIED, error, missing broker) raises WeldNotAuthorized (fail-closed).

    This is the single shared enforcement point for all AM-4 welds (ADR-012
    weld semantics: seam fixed ON = permanently routed through Broker/PEP).
    No bypass flag, no unsafe mode. Imports are lazy so importing this module
    never pulls the brain/runtime graph at import time.
    """
    from orchestrator.runtime.policy import make_broker_from_bootstrap
    from orchestrator.hardening.action_receipt import ActionProposalStatus

    if broker is None:
        broker = make_broker_from_bootstrap()
    receipt = broker.propose_action(
        target=target,
        action_type=action_type,
        capability=capability,
        method=method,
        impact_estimate=impact_estimate,
        authorized_argv=tuple(argv),
    )
    if receipt.status is not ActionProposalStatus.AUTHORIZED:
        raise WeldNotAuthorized(
            f"AM-4 welded path denied by Broker "
            f"(path={path_id or 'unknown'} ticket={weld_ticket} "
            f"action={action_type} capability={capability} status={receipt.status}): "
            f"legacy unbrokered execution is removed; all execution must go "
            f"through the broker-gated capability."
        )
    return receipt


def require_broker_mediation(
    *,
    target: str,
    action_type: str,
    capability: str,
    method: str,
    impact_estimate: float,
    argv: tuple = (),
    path_id: str = "",
    weld_ticket: str = "WELD-AM4",
):
    """FastAPI dependency: AM-4 broker mediation with 403 fail-closed mapping."""
    async def dependency():
        try:
            return enforce_broker_mediation(
                target=target,
                action_type=action_type,
                capability=capability,
                method=method,
                impact_estimate=impact_estimate,
                argv=tuple(argv),
                path_id=path_id,
                weld_ticket=weld_ticket,
            )
        except WeldNotAuthorized as exc:
            raise HTTPException(status_code=403, detail=str(exc))
    return dependency
