"""
P4.5 artifact store tests (§15 P4.5).

Proves minimal content-addressed artifact storage over the canonical
model: deterministic identity, store/retrieve, integrity, immutability,
receipt/action traceability, deterministic serialization, fail-closed
corruption semantics, and the authority model (artifacts cannot
authorize execution).
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orchestrator.exec.artifact_store import (
    ARTIFACT_ID_PREFIX,
    ArtifactRef,
    ArtifactStore,
    ArtifactStoreError,
    StoredArtifact,
    _canonical_bytes,
)


def _store(tmp_path, **kw):
    return ArtifactStore(str(tmp_path / "artifacts"), **kw)


# ── Identity ─────────────────────────────────────────────

def test_identity_deterministic_content_addressed():
    import orchestrator.exec.artifact_store as mod
    content = b"fixture-output-bytes"
    artifact_id, digest = mod._content_id(content)
    assert artifact_id == ARTIFACT_ID_PREFIX + hashlib.sha256(content).hexdigest()
    assert artifact_id == mod._content_id(bytearray(content))[0]


def test_same_content_same_identity():
    import tempfile
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        r1 = ArtifactStore(d1).put(b"same-bytes")
        r2 = ArtifactStore(d2).put(b"same-bytes")
        assert r1 == r2
        assert r1.artifact_id.startswith(ARTIFACT_ID_PREFIX)


def test_changed_content_changed_identity(tmp_path):
    store = _store(tmp_path)
    r1 = store.put(b"bytes-v1")
    r2 = store.put(b"bytes-v2")
    assert r1.artifact_id != r2.artifact_id
    assert r1.sha256 != r2.sha256


def test_metadata_does_not_redefine_identity(tmp_path):
    store = _store(tmp_path)
    r1 = store.put(b"content", media_type="text/plain", mission_id="m1")
    r2 = store.put(b"content", media_type="application/octet-stream", mission_id="m2")
    assert r1 == r2


def test_non_bytes_rejected(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ArtifactStoreError):
        store.put("not-bytes")  # type: ignore[arg-type]


# ── Store / retrieve ─────────────────────────────────────

def test_put_returns_ref_get_returns_identical(tmp_path):
    store = _store(tmp_path)
    content = b"artifact-content-\x00\xff-binary"
    ref = store.put(content, media_type="application/octet-stream")
    assert isinstance(ref, ArtifactRef)
    assert ref.byte_len == len(content)
    stored = store.get(ref)
    assert isinstance(stored, StoredArtifact)
    assert stored.content == content
    assert stored.ref == ref
    assert stored.media_type == "application/octet-stream"


def test_get_by_bare_id_and_missing(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"lookup-me")
    assert store.get(ref.artifact_id).content == b"lookup-me"
    assert store.get(ref.artifact_id + "00") is None
    assert store.get("not-an-id") is None
    assert store.get("") is None
    assert store.get_or_raise(ref).content == b"lookup-me"
    with pytest.raises(ArtifactStoreError):
        store.get_or_raise(ref.artifact_id + "00")


# ── Integrity ────────────────────────────────────────────

def test_modified_content_fails(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"original")
    bin_path = Path(store.root) / "sha256" / ref.sha256[:2] / (ref.sha256[2:] + ".bin")
    bin_path.write_bytes(b"tampered")
    assert store.get(ref) is None
    with pytest.raises(ArtifactStoreError):
        store.get_or_raise(ref)


def test_corrupted_metadata_fails(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"original")
    meta_path = Path(store.root) / "sha256" / ref.sha256[:2] / (ref.sha256[2:] + ".json")
    meta_path.write_text("{corrupt", encoding="utf-8")
    assert store.get(ref) is None


def test_identity_mismatch_fails(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"original")
    meta_path = Path(store.root) / "sha256" / ref.sha256[:2] / (ref.sha256[2:] + ".json")
    env = json.loads(meta_path.read_text(encoding="utf-8"))
    env["artifact_id"] = ARTIFACT_ID_PREFIX + "0" * 64
    meta_path.write_text(json.dumps(env), encoding="utf-8")
    assert store.get(ref) is None


def test_missing_sidecar_fails(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"original")
    meta_path = Path(store.root) / "sha256" / ref.sha256[:2] / (ref.sha256[2:] + ".json")
    meta_path.unlink()
    assert store.get(ref) is None


# ── Immutability ─────────────────────────────────────────

def test_idempotent_reingest_same_bytes(tmp_path):
    store = _store(tmp_path)
    r1 = store.put(b"stable")
    before = sorted(p.stat().st_mtime_ns for p in Path(store.root).rglob("*") if p.is_file())
    r2 = store.put(b"stable", media_type="other", mission_id="other")
    assert r1 == r2
    assert store.count() == 1
    # Producer metadata first-write-wins (identity is content-only).
    assert store.get(r1).mission_id == ""


def test_empty_content_roundtrip(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"")
    assert store.get(ref).content == b""


# ── Traceability (receipt → artifact) ────────────────────

def test_producer_linkage_to_real_receipt(tmp_path):
    """Artifact metadata traces to the producing broker receipt/action."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    broker = CapabilityBroker(BrokerPolicy(
        engagement_id="p45-link", allowed_targets=["system_info.name"],
        allowed_action_types=["safe_proving_capability"],
        allowed_capabilities=["fixture.inspect"],
    ))
    receipt = broker.propose_action(
        target="system_info.name", action_type="safe_proving_capability",
        capability="fixture.inspect", method="inspect", impact_estimate=0.0,
        authorized_argv=("fixture",),
    )
    assert receipt.decision == "allow"
    store = _store(tmp_path)
    ref = store.put(b"produced-by-receipt", producer_receipt_id=receipt.action_id,
                    producer_action_id="ACT_p45", mission_id="p45-mission")
    stored = store.get(ref)
    assert stored.producer_receipt_id == receipt.action_id
    assert stored.producer_action_id == "ACT_p45"
    assert stored.mission_id == "p45-mission"
    # The linked receipt is the live authorized one.
    assert broker.receipt_store[receipt.action_id].decision == "allow"


# ── Deterministic serialization ──────────────────────────

def test_ref_serialization_stable_and_strict(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"stable-ref")
    d1 = ref.to_dict()
    d2 = json.loads(json.dumps(d1, sort_keys=True))
    assert ArtifactRef.from_dict(d2) == ref
    assert _canonical_bytes({"b": 1, "a": 2}) == _canonical_bytes({"a": 2, "b": 1})
    # Verbatim preservation: byte_len stays int, never coerced.
    assert isinstance(ArtifactRef.from_dict(d1).byte_len, int)
    with pytest.raises(ArtifactStoreError):
        ArtifactRef.from_dict({**d1, "extra": 1})
    with pytest.raises(ArtifactStoreError):
        ArtifactRef.from_dict({"artifact_id": "nope", "byte_len": 0, "sha256": "0" * 64})
    with pytest.raises(ArtifactStoreError):
        ArtifactRef.from_dict("not-a-mapping")  # type: ignore[arg-type]


def test_metadata_bytes_stable(tmp_path):
    store = _store(tmp_path)
    store.put(b"stable-meta", media_type="text/plain", mission_id="m")
    import glob
    metas = glob.glob(str(tmp_path / "artifacts" / "sha256" / "*" / "*.json"))
    assert len(metas) == 1
    raw = Path(metas[0]).read_bytes()
    assert raw == _canonical_bytes(json.loads(raw.decode("utf-8")))


# ── Corruption / failure semantics ───────────────────────

def test_unknown_schema_refused(tmp_path):
    store = _store(tmp_path)
    ref = store.put(b"v")
    meta_path = Path(store.root) / "sha256" / ref.sha256[:2] / (ref.sha256[2:] + ".json")
    env = json.loads(meta_path.read_text(encoding="utf-8"))
    env["schema_version"] = 999
    meta_path.write_text(json.dumps(env), encoding="utf-8")
    assert store.get(ref) is None


def test_oversize_rejected(tmp_path):
    store = _store(tmp_path, max_bytes=8)
    with pytest.raises(ArtifactStoreError):
        store.put(b"nine-bytes")


def test_capacity_cap_fail_closed(tmp_path):
    store = _store(tmp_path, max_artifacts=1)
    store.put(b"one")
    with pytest.raises(ArtifactStoreError):
        store.put(b"two")


def test_missing_root_is_empty(tmp_path):
    store = ArtifactStore(str(tmp_path / "absent"))
    assert store.count() == 0


# ── Authority: artifacts cannot authorize ────────────────

def test_artifactref_has_no_authority():
    assert not hasattr(ArtifactRef, "authorize")
    assert not hasattr(ArtifactRef, "execute")
    import inspect
    src = inspect.getsource(ArtifactRef) + inspect.getsource(StoredArtifact)
    # Type-name tokens: docstring prose ("authorizes nothing") is correct
    # documentation, not authority. Authority is established by
    # definitions/calls, checked below.
    for token in ("CapabilityBroker", "receipt_store", "Sandbox", "Popen",
                  "subprocess"):
        assert token not in src, token
    for stmt in ("def authorize", "def execute(", "def decide(", "def propose",
                 "self.decision", "if self."):
        assert stmt not in src, stmt
    assert not hasattr(ArtifactRef, "decide")
    assert not hasattr(ArtifactRef, "propose_action")


def test_loaded_artifact_cannot_authorize(tmp_path):
    """A stored artifact grants no execution authority at any boundary."""
    from orchestrator.brain.capability_broker import BrokerPolicy, CapabilityBroker
    from orchestrator.exec.sandbox import (
        SandboxedExecutor, SandboxPolicy, SandboxRequest, SandboxNotAuthorized,
    )
    store = _store(tmp_path)
    ref = store.put(b"echo-approved", producer_receipt_id="whatever",
                    producer_action_id="ACT_x", mission_id="m")
    loaded = store.get_or_raise(ref)
    fresh = CapabilityBroker(BrokerPolicy(
        engagement_id="fresh", allowed_targets=["*"],
        allowed_action_types=["sandboxed_exec"],
        allowed_capabilities=["fixture.inspect"],
    ))
    import types
    forged = types.SimpleNamespace(action_id="not-authorized-here")
    ex = SandboxedExecutor(broker=fresh,
                           policy=SandboxPolicy(workdir_root=str(tmp_path)))
    with pytest.raises(SandboxNotAuthorized):
        ex.execute(
            SandboxRequest(target="t", argv=(loaded.content.decode(),),
                           capability="fixture.inspect",
                           action_type="sandboxed_exec", method="exec"),
            forged,
        )
    # The artifact bytes themselves authorize nothing at the broker either.
    assert fresh.receipt_store.get("not-authorized-here") is None
