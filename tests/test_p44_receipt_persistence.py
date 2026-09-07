"""
P4.4 receipt persistence tests (§15 P4.4).

Proves durable local receipt storage over the canonical receipt model:
deterministic serialization, integrity (existing hash chain + envelope
mission binding), mission/action traceability, fail-closed corruption
semantics, real cross-process restart survival, and the authority
model (persisted receipts cannot authorize execution).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
from orchestrator.exec.receipt_store import (
    ReceiptStore,
    ReceiptStoreError,
    StoredReceipt,
    _canonical_bytes,
)

HELPER = REPO_ROOT / "tests" / "_p44_restart_helper.py"


def _broker():
    return CapabilityBroker(BrokerPolicy(
        engagement_id="p44-test",
        allowed_targets=["system_info.name"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))


def _allowed(broker, target="system_info.name", argv=("fixture", "system_info.name")):
    receipt = broker.propose_action(
        target=target, action_type="safe_proving_capability",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
        authorized_argv=tuple(argv),
    )
    assert receipt.decision == "allow"
    return receipt


def _store(tmp_path, **kw):
    return ReceiptStore(str(tmp_path / "receipts.jsonl"), **kw)


# ── Persistence + deterministic serialization ────────────

def test_append_and_get_roundtrip(tmp_path):
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    action_id = store.append(receipt, mission_id="m1", mission_digest="d1",
                             scope_hash="s1")
    assert action_id == receipt.action_id
    stored = store.get(action_id)
    assert isinstance(stored, StoredReceipt)
    assert stored.receipt.to_dict() == receipt.to_dict()
    assert (stored.mission_id, stored.mission_digest, stored.scope_hash) == ("m1", "d1", "s1")
    assert stored.receipt.verify_integrity()


def test_serialization_deterministic_bytes(tmp_path):
    broker = _broker()
    receipt = _allowed(broker)
    line1 = _canonical_bytes({"receipt": receipt.to_dict(), "mission_id": "m"})
    line2 = _canonical_bytes({"mission_id": "m", "receipt": receipt.to_dict()})
    assert line1 == line2  # key order irrelevant
    store = _store(tmp_path)
    store.append(receipt, mission_id="m")
    raw = (tmp_path / "receipts.jsonl").read_bytes()
    assert raw.endswith(b"\n") and raw.count(b"\n") == 1
    assert json.loads(raw.decode("utf-8"))["mission_id"] == "m"


def test_same_receipt_same_bytes_idempotent(tmp_path):
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    store.append(receipt, mission_id="m")
    before = (tmp_path / "receipts.jsonl").read_bytes()
    assert store.append(receipt, mission_id="m") == receipt.action_id
    assert (tmp_path / "receipts.jsonl").read_bytes() == before
    assert len(store) == 1


def test_f1_fields_survive_roundtrip(tmp_path):
    """All six F1 dimensions + decision identity survive serialization."""
    broker, store = _broker(), _store(tmp_path)
    argv = ("fixture", "system_info.name", "extra")
    receipt = _allowed(broker, argv=argv)
    store.append(receipt, mission_id="m")
    loaded = ReceiptStore(str(tmp_path / "receipts.jsonl")).get(receipt.action_id)
    assert loaded is not None
    assert loaded.receipt.target == "system_info.name"
    assert loaded.receipt.capability == "fixture.inspect"
    assert loaded.receipt.action_type == "safe_proving_capability"
    assert loaded.receipt.method == "inspect"
    assert tuple(loaded.receipt.authorized_argv) == tuple(argv)
    assert loaded.receipt.decision == "allow"


# ── Integrity: tamper in every F1 dimension fails ────────

def _tampered_line(tmp_path, receipt, mutate):
    store = _store(tmp_path)
    store.append(receipt, mission_id="m", mission_digest="d", scope_hash="s")
    path = tmp_path / "receipts.jsonl"
    envelope = json.loads(path.read_text(encoding="utf-8"))
    mutate(envelope)
    path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")


@pytest.mark.parametrize("field,value", [
    ("target", "evil.target"),
    ("capability", "shell.exec"),
    ("action_type", "reverse_shell"),
    ("method", "netcat"),
    ("decision", "deny"),
    ("action_id", "forged-id"),
])
def test_tampered_scalar_field_refused(tmp_path, field, value):
    broker = _broker()
    receipt = _allowed(broker)
    _tampered_line(tmp_path, receipt, lambda env: env["receipt"].__setitem__(field, value))
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(tmp_path / "receipts.jsonl"))


def test_tampered_argv_refused(tmp_path):
    broker = _broker()
    receipt = _allowed(broker)
    _tampered_line(
        tmp_path, receipt,
        lambda env: env["receipt"].__setitem__("authorized_argv", ["evil"]),
    )
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(tmp_path / "receipts.jsonl"))


def test_tampered_mission_binding_refused(tmp_path):
    """Mission masquerade (swapped mission_id) breaks the envelope binding."""
    broker = _broker()
    receipt = _allowed(broker)
    _tampered_line(tmp_path, receipt, lambda env: env.__setitem__("mission_id", "other-mission"))
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(tmp_path / "receipts.jsonl"))


def test_tampered_audit_hash_refused(tmp_path):
    broker = _broker()
    receipt = _allowed(broker)
    _tampered_line(tmp_path, receipt, lambda env: env["receipt"].__setitem__("audit_hash", "0" * 64))
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(tmp_path / "receipts.jsonl"))


# ── Corruption / fail-closed ─────────────────────────────

def test_missing_file_is_empty_store(tmp_path):
    store = ReceiptStore(str(tmp_path / "absent.jsonl"))
    assert len(store) == 0
    assert store.get("anything") is None


def test_malformed_line_refuses_whole_load(tmp_path):
    path = tmp_path / "receipts.jsonl"
    path.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(path))


def test_truncated_line_refuses_whole_load(tmp_path):
    broker = _broker()
    store = _store(tmp_path)
    store.append(_allowed(broker), mission_id="m")
    path = tmp_path / "receipts.jsonl"
    raw = path.read_bytes()
    path.write_bytes(raw[: len(raw) // 2])  # truncate mid-record
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(path))


def test_unknown_schema_refused(tmp_path):
    path = tmp_path / "receipts.jsonl"
    path.write_text(json.dumps({"schema_version": 999, "action_id": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ReceiptStoreError):
        ReceiptStore(str(path))


def test_identity_conflict_rejected(tmp_path):
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    store.append(receipt, mission_id="m")
    with pytest.raises(ReceiptStoreError):
        store.append(receipt, mission_id="other-mission")


def test_non_receipt_rejected(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ReceiptStoreError):
        store.append({"action_id": "fake"})  # type: ignore[arg-type]


def test_capacity_cap_fail_closed(tmp_path):
    store = _store(tmp_path, max_records=1)
    broker = _broker()
    store.append(_allowed(broker), mission_id="m")
    broker2 = _broker()
    with pytest.raises(ReceiptStoreError):
        store.append(_allowed(broker2, argv=("fixture", "other")), mission_id="m")


# ── Mission / action traceability ────────────────────────

def test_mission_traceability_survives(tmp_path):
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    store.append(receipt, mission_id="mission-A", mission_digest="digest-A",
                 scope_hash="scope-A")
    loaded = ReceiptStore(str(tmp_path / "receipts.jsonl")).get(receipt.action_id)
    assert (loaded.mission_id, loaded.mission_digest, loaded.scope_hash) == \
        ("mission-A", "digest-A", "scope-A")


def test_cross_mission_mismatch_detectable(tmp_path):
    """A receipt bound to mission A never matches mission B's digest."""
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    store.append(receipt, mission_id="mission-A", mission_digest="digest-A")
    loaded = ReceiptStore(str(tmp_path / "receipts.jsonl")).get(receipt.action_id)
    assert loaded.mission_digest != "digest-B"
    assert loaded.mission_id != "mission-B"


# ── Authority: persisted receipts cannot authorize ──────

def test_persisted_receipt_cannot_authorize(tmp_path):
    """Disk state never enters the live Broker store; execution refused."""
    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest, SandboxNotAuthorized,
    )
    broker, store = _broker(), _store(tmp_path)
    receipt = _allowed(broker)
    store.append(receipt, mission_id="m")
    # Fresh broker knows nothing: the durable copy grants no authority.
    fresh = CapabilityBroker(BrokerPolicy(
        engagement_id="fresh", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    loaded = ReceiptStore(str(tmp_path / "receipts.jsonl")).get(receipt.action_id)
    ex = SandboxedExecutor(broker=fresh,
                           policy=SandboxPolicy(workdir_root=str(tmp_path)))
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="system_info.name", argv=("fixture", "x"),
                           capability="fixture.inspect",
                           action_type="sandboxed_exec", method="exec"),
            loaded.receipt,
        )


# ── Restart survival (real OS-process boundary) ──────────

def test_receipts_survive_process_restart(tmp_path):
    """Process A persists; process B (fresh interpreter) loads + verifies."""
    import os
    store_path = str(tmp_path / "restart.jsonl")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    written = subprocess.run(
        [sys.executable, str(HELPER), store_path, "write"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
        timeout=60,
    )
    assert written.returncode == 0, written.stderr
    write_ids = json.loads(written.stdout)["ids"]
    assert len(write_ids) == 2

    read = subprocess.run(
        [sys.executable, str(HELPER), store_path, "read"],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
        timeout=60,
    )
    assert read.returncode == 0, read.stderr
    records = json.loads(read.stdout)["records"]
    assert [r["action_id"] for r in records] == sorted(write_ids)
    by_id = {r["action_id"]: r for r in records}
    assert by_id[write_ids[0]]["decision"] == "allow"
    assert by_id[write_ids[1]]["decision"] == "deny"
    for r in records:
        assert r["mission_id"] == "p44-restart-mission"
        assert r["mission_digest"] == "digest-p44-restart"
        assert r["scope_hash"] == "scopehash-p44"
        assert r["capability"] == "fixture.inspect"
        assert r["action_type"] == "safe_proving_capability"
        assert r["method"] == "inspect"
