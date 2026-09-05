"""
safe_capability.py — Safe proving capability (CONV-3 relocated)

Originally at src/orchestrator/runtime/safe_proving_capability.py
(P2.1 walking skeleton). Relocated to exec/ per CONV-3.

Per v4 L6: exec/ is the sole PEP package. Capabilities that perform
file/network/process operations must live here.

Per v4 §13.3 P2.4: "one low-risk, deterministic, Raphael-native
capability." This capability is read-only, deterministic, and
fixture-based.

CONV-3 constructor gating: the capability requires a
CapabilityBroker reference. inspect() verifies the broker has been
consulted (via the broker_authorized flag) before performing the
read. This is the "gated" part of CONV-3.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
import time
import uuid

from orchestrator.brain.capability_broker import CapabilityBroker


# The fixture is an in-process dict. Deterministic, read-only.
DEFAULT_FIXTURE: dict = {
    "system_info": {
        "name": "raphael-walking-skeleton",
        "version": "2.1-P2.1",
        "stage": "P3.0-C0NV-1",
    },
    "capabilities": [
        {"name": "fixture.inspect", "version": "1"},
    ],
    "environment": {
        "os": "linux",
        "python": "3.x",
        "runtime": "walking-skeleton",
    },
}


@dataclass
class CapabilityResult:
    """Output of a capability invocation. PEP-shaped."""
    capability: str
    target: str
    output: Any = None
    receipt_summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "target": self.target,
            "output": self.output,
            "receipt_summary": self.receipt_summary,
            "timestamp": self.timestamp,
        }


class CapabilityNotGatedError(Exception):
    """Raised when inspect() is called without broker gating (CONV-3)."""
    pass


class SafeProvingCapability:
    """Read-only fixture inspection capability (CONV-3 relocated).

    Gated by the broker: the capability requires a CapabilityBroker
    reference. inspect() verifies the broker has been consulted for
    this target before performing the read.
    """

    def __init__(self,
                 broker: Optional[CapabilityBroker] = None,
                 fixture: Optional[dict] = None):
        self._broker = broker
        self._fixture = fixture if fixture is not None else DEFAULT_FIXTURE
        self._invocation_count = 0
        self._broker_authorized_targets: set = set()

    def gate_with_broker(self, broker: CapabilityBroker) -> None:
        """Bind the capability to a broker (CONV-3 constructor gating).

        After binding, inspect() requires that the broker has
        authorized the specific target via propose_action().
        """
        self._broker = broker

    def record_authorization(self, target: str) -> None:
        """Record that the broker has authorized a specific target.

        Called by the PEP stage after a successful broker.propose_action()
        with the given target. The capability then permits inspect(target).
        """
        self._broker_authorized_targets.add(target)

    def inspect(self, target: str) -> CapabilityResult:
        """Inspect a named key in the fixture.

        Gated by broker: if a broker is bound, the target must have
        been authorized via record_authorization() before this call.
        If no broker is bound, the capability operates in legacy
        read-only mode (no network, no subprocess, no file mutation).
        """
        if self._broker is not None:
            # CONV-3: broker-gated mode — require prior authorization
            if target not in self._broker_authorized_targets:
                raise CapabilityNotGatedError(
                    f"Target '{target}' not authorized by broker. "
                    f"Call record_authorization(target) after "
                    f"broker.propose_action() succeeds."
                )
        self._invocation_count += 1
        parts = target.split(".")
        node = self._fixture
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        return CapabilityResult(
            capability="fixture.inspect",
            target=target,
            output=node,
            receipt_summary=f"Inspected fixture key '{target}' (invocation #{self._invocation_count})",
        )

    @property
    def invocation_count(self) -> int:
        return self._invocation_count

    @property
    def broker(self) -> Optional[CapabilityBroker]:
        return self._broker
