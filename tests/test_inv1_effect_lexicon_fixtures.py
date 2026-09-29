"""001R5 scanner fixtures: positive AND negative cases for the extended lexicon.

Covers N-9 (pathlib inline/chained detection, method-form FP control) and N-8
(boto3/botocore + asyncio.open_connection/start_server, usage-gated).

001R6 additions: Redis governed-network family (usage-gated construction +
proven-receiver operations, fakeredis exclusion); import-alias canonicalization
(pathlib/boto3/asyncio/smtplib/redis aliases); inline boto3.Session().client();
module-level for-glob binding; from-import single-finding de-dup.

Conventions asserted here:
- write_text/write_bytes flag ONLY on structurally proven Path receivers;
- unlink/rename/rmdir/chmod flag ONLY on proven receivers (never bare names);
- boto3/botocore/smtplib/redis bare imports never flag alone (usage-gated);
- dotted construction/call sites (boto3.client, asyncio.open_connection, ...) flag;
- unrelated asyncio calls never flag;
- no duplicate findings per site.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from orchestrator.exec.inv1_guard import scan_source


def _prims(source: str) -> set:
    return {(v["primitive"], v["line"]) for v in scan_source(source, "fixture.py")}


def _has(source: str, primitive: str) -> bool:
    return any(v["primitive"] == primitive for v in scan_source(source, "fixture.py"))


# ── PATHLIB positive ──────────────────────────────────────────────────

def test_pathlib_inline_write_text():
    src = "from pathlib import Path\nPath('x').write_text('hi')\n"
    assert _has(src, "Path.write_text"), _prims(src)


def test_pathlib_inline_write_bytes():
    src = "from pathlib import Path\nPath('x').write_bytes(b'hi')\n"
    assert _has(src, "Path.write_text") or _has(src, "Path.write_bytes"), _prims(src)


def test_pathlib_qualified_write_text():
    src = "import pathlib\npathlib.Path('/t').write_text('hi')\n"
    assert any(p.endswith("write_text") for p, _ in _prims(src)), _prims(src)


def test_pathlib_chained_write_bytes():
    src = ("import pathlib\n"
           "(pathlib.Path('/t') / 'x').write_bytes(b'z')\n")
    assert any(p.endswith("write_bytes") for p, _ in _prims(src)), _prims(src)


def test_pathlib_bound_variable():
    src = ("from pathlib import Path\n"
           "variable_path = Path('/tmp') / 'f'\n"
           "variable_path.write_text('hi')\n")
    assert _has(src, "variable_path.write_text"), _prims(src)


# ── PATHLIB negative ──────────────────────────────────────────────────

def test_arbitrary_object_write_not_flagged():
    src = ("class Obj:\n"
           "    def write_text(self, data):\n"
           "        self.buf = data\n"
           "arbitrary_object = Obj()\n"
           "arbitrary_object.write_text('hi')\n"
           "arbitrary_object.write_bytes(b'hi')\n")
    assert _prims(src) == set(), _prims(src)


def test_unrelated_write_method_not_flagged():
    src = "import os\nlogger = None\n"
    assert _prims(src) == set(), _prims(src)


# ── METHOD-FORM positive ──────────────────────────────────────────────

def test_path_unlink_rename_rmdir():
    src = ("from pathlib import Path\n"
           "Path('/t').unlink()\n"
           "Path('/a').rename('/b')\n"
           "Path('/d').rmdir()\n")
    prims = {p for p, _ in _prims(src)}
    assert "Path.unlink" in prims and "Path.rename" in prims \
        and "Path.rmdir" in prims, prims


# ── METHOD-FORM negative ──────────────────────────────────────────────

def test_record_rename_not_flagged():
    assert _prims("record.rename('a', 'b')\n") == set()


def test_model_unlink_not_flagged():
    assert _prims("model.unlink()\n") == set()


def test_arbitrary_rmdir_not_flagged():
    assert _prims("arbitrary.rmdir()\n") == set()


def test_unbound_name_with_pathlib_import_not_flagged():
    # Even with pathlib imported, an unbound name is not proven.
    src = "import pathlib\nunknown_handle.unlink()\n"
    assert _prims(src) == set(), _prims(src)


# ── NETWORK positive ──────────────────────────────────────────────────

def test_boto3_client_construction():
    src = "import boto3\nsts = boto3.client('sts')\n"
    assert _has(src, "boto3.client"), _prims(src)


def test_boto3_session_construction():
    src = "import boto3\nsession = boto3.Session()\n"
    assert _has(src, "boto3.Session"), _prims(src)


def test_boto3_chained_session_client():
    src = "import boto3\nsession = boto3.Session()\nsession.client('s3')\n"
    prims = {p for p, _ in _prims(src)}
    assert "boto3.Session" in prims and "boto3.Session.client" in prims, prims


def test_asyncio_open_connection():
    src = ("import asyncio\n"
           "async def f():\n"
           "    await asyncio.open_connection('h', 80)\n")
    assert _has(src, "asyncio.open_connection"), _prims(src)


def test_asyncio_start_server():
    src = ("import asyncio\n"
           "async def f():\n"
           "    await asyncio.start_server(None, 'h', 80)\n")
    assert _has(src, "asyncio.start_server"), _prims(src)


def test_smtplib_construction():
    src = "import smtplib\nsrv = smtplib.SMTP('h', 25)\n"
    assert _has(src, "smtplib.SMTP"), _prims(src)


# ── NETWORK negative ──────────────────────────────────────────────────

def test_unrelated_asyncio_calls_not_flagged():
    src = ("import asyncio\n"
           "async def f():\n"
           "    await asyncio.sleep(1)\n"
           "    await asyncio.gather()\n")
    assert _prims(src) == set(), _prims(src)


def test_bare_network_imports_not_flagged():
    assert _prims("import boto3\n") == set()
    assert _prims("import smtplib\n") == set()
    assert _prims("import asyncio\n") == set()


# ── No-duplicate invariant ────────────────────────────────────────────

def test_no_duplicate_findings_per_site():
    src = ("import os\nimport subprocess\nfrom pathlib import Path\n"
            "os.unlink('/x')\n"
            "subprocess.run(['id'])\n"
            "Path('/y').write_text('z')\n")
    seen = [(v["line"], v["primitive"], v["type"])
            for v in scan_source(src, "fixture.py")]
    assert len(seen) == len(set(seen)), seen


# ── 001R6: import-alias canonicalization ───────────────────────────────

def test_pathlib_import_alias_write():
    src = "from pathlib import Path as P\nP('/t').write_text('hi')\n"
    assert _has(src, "Path.write_text"), _prims(src)


def test_pathlib_import_alias_no_false_positive():
    # Alias import alone proves nothing about other names.
    src = "from pathlib import Path as P\nother.write_text('hi')\n"
    assert _prims(src) == set(), _prims(src)


def test_boto3_import_alias_client():
    src = "import boto3 as b\nb.client('s3')\n"
    assert _has(src, "boto3.client"), _prims(src)


def test_asyncio_import_alias_open_connection():
    src = ("import asyncio as a\n"
           "async def f():\n"
           "    await a.open_connection('h', 80)\n")
    assert _has(src, "asyncio.open_connection"), _prims(src)


def test_smtplib_import_alias_construction():
    src = "import smtplib as s\ns.SMTP('h')\n"
    assert _has(src, "smtplib.SMTP"), _prims(src)


def test_redis_import_alias_from_url():
    src = "import redis.asyncio as redis\nr = redis.from_url('redis://x')\n"
    assert _has(src, "redis.from_url"), _prims(src)


def test_module_level_for_glob_binding():
    src = ("from pathlib import Path\n"
           "for f in Path('/t').glob('*.x'):\n"
           "    f.write_text('hi')\n")
    assert _has(src, "f.write_text"), _prims(src)


def test_comprehension_glob_binding():
    src = ("from pathlib import Path\n"
           "fs = [f.write_text('hi') for f in Path('/t').glob('*.x')]\n")
    assert _has(src, "f.write_text"), _prims(src)


def test_arbitrary_glob_comprehension_not_flagged():
    src = ("class Store:\n"
           "    def glob(self, pat):\n"
           "        return []\n"
           "s = Store()\n"
           "[f.write_text('hi') for f in s.glob('*')]\n")
    assert _prims(src) == set(), _prims(src)


def test_boto3_inline_session_client():
    src = "import boto3\nboto3.Session().client('s3')\n"
    prims = {p for p, _ in _prims(src)}
    assert "boto3.Session.client" in prims, prims


def test_from_import_single_finding():
    # De-dup: the import site must not emit alongside the use site.
    assert _prims("from boto3 import client\nclient('s3')\n") == \
        {("boto3.client", 2)}, _prims("from boto3 import client\nclient('s3')\n")
    assert _prims("from smtplib import SMTP\nSMTP('h')\n") == \
        {("smtplib.SMTP", 2)}, _prims("from smtplib import SMTP\nSMTP('h')\n")


def test_from_import_unused_stays_clean():
    assert _prims("from boto3 import client\n") == set()
    assert _prims("from redis import Redis\n") == set()


# ── 001R6: Redis positive ──────────────────────────────────────────────

def test_redis_from_url_construction():
    src = "import redis\nr = redis.from_url('redis://x')\n"
    assert _has(src, "redis.from_url"), _prims(src)


def test_redis_client_construction():
    src = "import redis\nc = redis.Redis(host='h')\n"
    assert _has(src, "redis.Redis"), _prims(src)


def test_redis_from_import_construction():
    src = "from redis import Redis\nc = Redis(host='h')\n"
    assert _has(src, "redis.Redis"), _prims(src)


def test_redis_receiver_operations():
    src = ("import redis\n"
           "c = redis.Redis(host='h')\n"
           "c.ping()\n"
           "c.xadd('s', {'a': 'b'})\n")
    prims = {p for p, _ in _prims(src)}
    assert "redis.ping" in prims and "redis.xadd" in prims, prims


def test_redis_self_attr_and_property():
    src = ("import redis.asyncio as redis\n"
           "class Bus:\n"
           "    async def connect(self):\n"
           "        self._r = redis.from_url('redis://x')\n"
           "    @property\n"
           "    def r(self):\n"
           "        return self._r\n"
           "    async def go(self):\n"
           "        await self._r.ping()\n"
           "        await self.r.xadd('s', {'a': 'b'})\n")
    prims = {p for p, _ in _prims(src)}
    assert "redis.ping" in prims and "redis.xadd" in prims, prims


# ── 001R6: Redis negative ──────────────────────────────────────────────

def test_bare_redis_import_clean():
    assert _prims("import redis\n") == set()
    assert _prims("import redis.asyncio as redis\n") == set()


def test_arbitrary_ping_xadd_not_flagged():
    assert _prims("cache.ping()\n") == set()
    assert _prims("stream.xadd('s', {})\n") == set()
    assert _prims("obj.get('k')\n") == set()


def test_fakeredis_not_flagged():
    src = ("import fakeredis\n"
           "c = fakeredis.FakeAsyncRedis()\n"
           "await c.ping()\n")
    assert _prims(src) == set(), _prims(src)


def test_redis_exception_attrs_not_flagged():
    src = ("import redis.asyncio as redis\n"
           "try:\n"
           "    pass\n"
           "except redis.ResponseError:\n"
           "    pass\n")
    assert _prims(src) == set(), _prims(src)
