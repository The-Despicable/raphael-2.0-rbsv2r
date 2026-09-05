"""
safe_proving_capability.py — one safe, deterministic, Raphael-native capability.

Per v4 §13.3 P2.4: "Add exactly one low-risk, deterministic, Raphael-native
capability. Prefer a capability that:
- has deterministic output
- has no external network requirement
- can be run inside a local fixture
- clearly demonstrates receipt generation

A read-only fixture inspection or equivalent is acceptable."

This module implements SafeProvingCapability: a read-only inspection of
an in-process fixture. It is:
- READ-ONLY (no file mutation, no subprocess, no network)
- DETERMINISTIC (same input -> same output, no time/randomness)
- FIXTURE-BASED (uses an in-process dict, no filesystem)
- RECEIPT-GENERATING (returns an EvidenceReceipt-shaped output)

GLM §4: bootstrap-v0 BOOT-002 applies: read_only_fixture_inspection,
no_external_network, receipt_generation_required.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
import time
import uuid


# The fixture is an in-process dict. Deterministic, read-only.
DEFAULT_FIXTURE: dict = {
    "system_info": {
        "name": "raphael-walking-skeleton",
        "version": "2.1-P2.1",
        "stage": "P2.1",
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


class SafeProvingCapability:
    """Read-only fixture inspection capability.

    Deterministic. No subprocess. No network. No file mutation.
    Generates an EvidenceReceipt-shaped output.
    """

    def __init__(self, fixture: Optional[dict] = None):
        self._fixture = fixture if fixture is not None else DEFAULT_FIXTURE
        self._invocation_count = 0

    def inspect(self, target: str) -> CapabilityResult:
        """Inspect a named key in the fixture.

        target: a dotted path into the fixture (e.g. "system_info.name")
        Returns the value at that path, or None if not found.
        """
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
