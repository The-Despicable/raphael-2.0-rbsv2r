#!/usr/bin/env python3
"""run_rsi01_eval.py — RSI-0.1 scenario-validity experiments.

Produces evidence/rsi0_1/<run_id>/ with:
  s3_rate_limit.json     — multi-episode shared-limiter rate denial at the Broker
  c2_capability_fault.json — Action A PEP failure -> halt (retry unsupported)
  c2_rate_retry_window.json — transient rate denial -> window expiry -> governed retry
  manifest.json          — combined run record
"""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from orchestrator.rsi import scenario_validity as SV  # noqa: E402


def main() -> int:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = REPO / "evidence" / "rsi0_1"
    run_dir = base / stamp
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = base / f"{stamp}_{suffix}"
    run_dir.mkdir(parents=True)
    print(f"[rsi01] run directory: {run_dir}")

    manifest = {"experiment": "RSI-0.1 scenario validity and candidate-behavior verification",
                "run_id": run_dir.name, "generated_at": time.time()}

    print("[rsi01] 1/3 S3 rate-limit verification (2/min, shared broker, 2 episodes)")
    s3 = SV.s3_rate_limit_verification(run_dir / "s3")
    manifest["s3_rate_limit"] = s3
    (run_dir / "s3_rate_limit.json").write_text(json.dumps(s3, indent=1))
    print(f"[rsi01]    proposals={[d for d in s3['proposal_sequence']]}")
    print(f"[rsi01]    third_proposal_denied_at_broker={s3['third_proposal_denied_at_broker']} "
          f"persisted_rate_denials={s3['persisted_rate_denials']}")

    print("[rsi01] 2/3 C2 capability-fault test (Action A fails at the PEP)")
    c2a = SV.c2_capability_fault_test(run_dir / "c2_fault")
    manifest["c2_capability_fault"] = c2a
    (run_dir / "c2_capability_fault.json").write_text(json.dumps(c2a, indent=1))
    print(f"[rsi01]    halted_at='{c2a['terminated_at']}' "
          f"failure_receipts={c2a['persisted_failure_receipts']} "
          f"retry_proposed={c2a['retry_step_proposed']}")

    print("[rsi01] 3/3 C2 rate-retry window test (~61 s window expiry)")
    c2b = SV.c2_rate_retry_window_test(run_dir / "c2_window")
    manifest["c2_rate_retry_window"] = c2b
    (run_dir / "c2_rate_retry_window.json").write_text(json.dumps(c2b, indent=1))
    print(f"[rsi01]    ep1={c2b['episode_1']} ")
    print(f"[rsi01]    ep2={c2b['episode_2']}")
    print(f"[rsi01]    retry_exercised_across_episodes={c2b['retry_exercised_across_episodes']}")

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"[rsi01] manifest written: {run_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
