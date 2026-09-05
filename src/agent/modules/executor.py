
# --- P1 DEPRECATION MARKER (per v4 section 12.2 P1.2) ---
# SUB-12: UNREACHABLE_FROM_CANONICAL (P0 inventory).
# See evidence/phases/P0/02_execution_inventory/subprocess_sites.md.
# Disposition: deprecate; verify zero canonical references; delete at P9.1.
# No canonical Runtime path reaches this site (v4 INV-5/INV-6).
# Do not import from canonical code (v4 INV-11).
# -------------------------------------------------------

import subprocess, asyncio

class Executor:
    @staticmethod
    async def run(command: str, timeout: int = 30) -> dict:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.PIPE,
                stderr=asyncio.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "code": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"error": "timeout"}
        except Exception as e:
            return {"error": str(e)}
