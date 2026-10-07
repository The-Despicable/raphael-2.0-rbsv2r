"""PatchSandbox — legacy sandboxed code-execution surface (W-10 sink).

This package owns the ``orchestrator.sandbox`` namespace. A sibling
``sandbox.py`` module used to define ``PatchSandbox`` but was permanently
shadowed by this package (regular packages resolve before modules of the
same name), leaving every ``from orchestrator.sandbox import PatchSandbox``
broken. The module's definition now lives here; do NOT re-add a sibling
``orchestrator/sandbox.py`` — it would re-create the shadow.

PatchSandbox is NOT the canonical native sandbox (``orchestrator/exec/
sandbox.py``, §14.4). Its ``run_code`` is the W-10 welded sink: broker
mediation first, execution body deleted (fail-closed).
"""

import subprocess
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger("sandbox")


class PatchSandbox:
    def __init__(self) -> None:
        self.running = False

    async def validate_syntax(self, code: str) -> tuple[bool, str]:
        try:
            compile(code, "<sandbox>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    async def run_code(self, code: str, timeout: int = 30) -> dict:
        # AM-4 W-10 (R3.0-P16) WELDED under Scope v0: arbitrary-code execution
        # requires a Broker AUTHORIZED decision (fail-closed WeldNotAuthorized
        # otherwise). The legacy unconditional run branch is deleted.
        from orchestrator.auth import enforce_broker_mediation, WeldNotAuthorized
        enforce_broker_mediation(
            target="local-sandbox",
            action_type="exploit_execute",
            capability="sandbox.run_code",
            method="run_code",
            impact_estimate=9.0,
            path_id="R3.0-P16",
            weld_ticket="W-10",
        )
        # AM-4-R2: legacy arbitrary-code execution body DELETED (was
        # NamedTemporaryFile write + subprocess.run + cleanup unlink). No
        # execution path remains past the gate.
        raise WeldNotAuthorized(
            "AM-4 W-10 R3.0-P16: run_code execution branch deleted; "
            "all execution routes through the broker-gated capability."
        )


sandbox = PatchSandbox()
