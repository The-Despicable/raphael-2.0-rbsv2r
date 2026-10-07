"""exec/capabilities/ — broker-gated capabilities (INV-1).

Capabilities that invoke process/network primitives live here, per the
CONV-3 constructor-gating pattern established by
``orchestrator/exec/safe_capability.py``. Every capability requires a
bound CapabilityBroker and per-target ``record_authorization`` before it
will touch the world.
"""
