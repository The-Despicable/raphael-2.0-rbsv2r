"""capability_governance.py — exec-owned governance identity registry (RSI-1 C-1).

ROOT CAUSE OF THE C-1 ESCAPES. The B-1 governance registry protected
capabilities by NAME — the policy's declared capability vocabulary and the
Runtime's dispatch-registry keys. Both are caller-controlled: registering a
PROTECTED capability object under an innocuous alias (or as the bare default
capability) severed the name→protection link, the policy "granted" no
protected capability, the resolver fell through to the attacker's declared
budget, and the object executed unbounded (25 real spawns in the final
independent audit). Separately, ``stage_pep`` treated an ABSENT governance or
budget context as "no gate", so a hand-built stage dict executed 12 times.

THE FIX INVERTS THE DIRECTION OF TRUST AGAIN. Governance identity is bound
to the concrete capability TYPE by this exec-owned, module-level mapping —
not to any name a policy, a request, a registry key, or a class attribute
declares. Resolution is an EXACT ``type(capability)`` lookup against this
table (with an MRO walk so a subclass cannot strip protection by overriding
class attributes — inheritance can only ever KEEP a capability governed,
never un-govern it). Unknown types resolve to an empty set.

This module is exec-owned by design: the canonical protection facts live
next to the canonical capability implementations, where no Runtime caller,
policy artifact, or request field can re-point them. Resolution is pure and
side-effect free; the capability modules are imported lazily so runtime
governance code never pulls primitives in at module import time.
"""

# Exact concrete protected capability type -> canonical governed capability
# identity (the canonical names under which the governed engagement
# contracts in orchestrator.runtime.types recognise these capabilities).
# Keyed by the EXACT class object — never by name, never by attribute.
_GOVERNED_CAPABILITY_TYPES = None


def _governed_capability_types() -> dict:
    """Build (once) the exact type -> canonical identity mapping.

    The mapping is module-owned and immutable once built. Lazy import keeps
    the runtime's import of THIS module free of capability-module (and
    therefore primitive) imports at module load time.
    """
    global _GOVERNED_CAPABILITY_TYPES
    if _GOVERNED_CAPABILITY_TYPES is None:
        from orchestrator.exec.capabilities.d1_lab_probe import D1LabProbeCapability
        from orchestrator.exec.capabilities.http_probe import LabHttpProbeCapability
        _GOVERNED_CAPABILITY_TYPES = {
            D1LabProbeCapability: frozenset({"exec.d1_lab_probe"}),
            LabHttpProbeCapability: frozenset({"exec.http_probe"}),
        }
    return _GOVERNED_CAPABILITY_TYPES


def governed_capability_identity(capability) -> frozenset:
    """Canonical governed capability names for a capability OBJECT.

    - Exact concrete protected types resolve to their canonical names.
    - A subclass of a protected type INHERITS its governance (an MRO walk):
      overriding class attributes cannot strip protection; inheritance can
      only keep a capability governed, never un-govern it.
    - Unknown types resolve to an empty set (unprotected — the legacy
      bootstrap/fixture surface is untouched).

    The result is intersection-free by construction: only names present in
    this registry can ever be returned, so a tampered attribute, a renamed
    policy vocabulary, or a re-keyed dispatch registry cannot invent or
    remove protection.
    """
    if capability is None:
        return frozenset()
    concrete = type(capability)
    mapping = _governed_capability_types()
    identity = mapping.get(concrete)
    if identity is None:
        for base in concrete.__mro__[1:]:
            if base in mapping:
                identity = mapping[base]
                break
    if not identity:
        return frozenset()
    try:
        return frozenset(str(name) for name in identity)
    except TypeError:
        return frozenset()
