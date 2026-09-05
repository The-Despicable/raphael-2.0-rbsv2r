# --- P1 DEPRECATION MARKER (per v4 section 12.2 P1.2) ---
# DEPRECATED: AdaptiveBrain (31-line counter stub).
# v4 P1.2: AdaptiveBrain is a deprecation target.
# v4 INV-11: deprecated modules not imported by canonical code.
# Removed from brain/__init__.py re-export closure (RC-A).
# Direct consumers must import from orchestrator.brain.adaptive_brain explicitly.
# P9 owns physical deletion (after zero-reference proof).
# See evidence/phases/G2_RC/RC-A for disposition.
# -------------------------------------------------------
import time
import logging

logger = logging.getLogger("adaptive_brain")

_analytics = {
    "total_engagements": 0,
    "successful_phases": 0,
    "failed_phases": 0,
    "phases_completed": 0,
    "total_findings": 0,
    "start_time": time.time(),
    "targets_seen": set(),
    "phase_counts": {},
}


def get_analytics() -> dict:
    return {
        "total_engagements": _analytics["total_engagements"],
        "successful_phases": _analytics["successful_phases"],
        "failed_phases": _analytics["failed_phases"],
        "phases_completed": _analytics["phases_completed"],
        "total_findings": _analytics["total_findings"],
        "uptime_seconds": round(time.time() - _analytics["start_time"], 2),
        "targets_seen": len(_analytics["targets_seen"]),
        "phase_counts": dict(_analytics["phase_counts"]),
        "success_rate": round(
            _analytics["successful_phases"] / max(_analytics["phases_completed"], 1), 4
        ),
    }
