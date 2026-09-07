"""P4.4 restart-boundary helper (run in a FRESH OS process, never imported).

Usage:
    python _p44_restart_helper.py <store_path> write  -> prints JSON {ids: [...]}
    python _p44_restart_helper.py <store_path> read   -> prints JSON {records: [...]}

`write` authorizes two receipts through a real CapabilityBroker and
persists them with mission bindings, then exits. `read` loads the
durable store in a new process, verifies integrity, and prints the
recovered fields. The P4.4 test runs these as two separate
subprocesses to prove a real restart boundary.
"""
import json
import sys

sys.path.insert(0, "src")

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.receipt_store import ReceiptStore


def _broker():
    return CapabilityBroker(BrokerPolicy(
        engagement_id="p44-restart",
        allowed_targets=["system_info.name"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))


def do_write(store_path: str) -> dict:
    broker = _broker()
    argv = ("fixture", "system_info.name")
    r1 = broker.propose_action(
        target="system_info.name", action_type="safe_proving_capability",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
        authorized_argv=argv,
    )
    assert r1.decision == "allow", r1.reason
    r2 = broker.propose_action(
        target="elsewhere", action_type="safe_proving_capability",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
        authorized_argv=argv,
    )
    assert r2.decision == "deny"
    store = ReceiptStore(store_path)
    store.append(r1, mission_id="p44-restart-mission",
                 mission_digest="digest-p44-restart",
                 scope_hash="scopehash-p44")
    store.append(r2, mission_id="p44-restart-mission",
                 mission_digest="digest-p44-restart",
                 scope_hash="scopehash-p44")
    return {"ids": [r1.action_id, r2.action_id]}


def do_read(store_path: str) -> dict:
    store = ReceiptStore(store_path)
    out = []
    for action_id, stored in sorted(store._index.items()):
        r = stored.receipt
        assert r.verify_integrity(), action_id
        out.append({
            "action_id": r.action_id,
            "status": r.status.value,
            "decision": r.decision,
            "target": r.target,
            "capability": r.capability,
            "action_type": r.action_type,
            "method": r.method,
            "authorized_argv": list(r.authorized_argv),
            "mission_id": stored.mission_id,
            "mission_digest": stored.mission_digest,
            "scope_hash": stored.scope_hash,
        })
    return {"records": out}


if __name__ == "__main__":
    store_path, mode = sys.argv[1], sys.argv[2]
    if mode == "write":
        print(json.dumps(do_write(store_path), sort_keys=True))
    elif mode == "read":
        print(json.dumps(do_read(store_path), sort_keys=True))
    else:
        raise SystemExit(f"unknown mode {mode!r}")
