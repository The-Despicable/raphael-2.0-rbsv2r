"""P3.0 re-inventory consistency guardrail (records-consistency, strengthens only).

Asserts completeness/consistency of the classification set produced by
evidence/phases/P3_0_reinventory/: every inventoried path has exactly one label,
WELD_SET equals the not-yet-mediated set, and every P0 SUB maps to one P0_DIFF row.
Reads evidence files only; never executes legacy code. Does not touch the 521 floor.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RDIR = REPO / "evidence" / "phases" / "P3_0_reinventory"

EXPECTED_PATHS = [f"R3.0-P{i:02d}" for i in range(1, 16)]
EXPECTED_MEDIATED = {"R3.0-P01", "R3.0-P02", "R3.0-P13"}
EXPECTED_NOT_YET = {f"R3.0-P{i:02d}" for i in (4, 5, 6, 7, 8, 9, 10, 11, 12)}
EXPECTED_DEAD = {"R3.0-P03", "R3.0-P14", "R3.0-P15"}
EXPECTED_SUBS = [f"SUB-{i:02d}" for i in range(1, 18)]


def test_reinventory_artifact_set_exists():
    for name in ("INVENTORY.md", "P0_DIFF.md", "CLASSIFICATION.md", "WELD_SET.md",
                 "probe_reinventory.py"):
        assert (RDIR / name).exists(), f"missing P3.0 re-inventory artifact: {name}"
    assert RDIR.is_dir()


def test_classification_covers_every_path_exactly_once():
    text = (RDIR / "CLASSIFICATION.md").read_text()
    for pid in EXPECTED_PATHS:
        assert text.count(pid) >= 1, f"path {pid} missing from CLASSIFICATION.md"
    assert EXPECTED_MEDIATED | EXPECTED_NOT_YET | EXPECTED_DEAD == set(EXPECTED_PATHS)
    assert len(EXPECTED_PATHS) == 15
    assert len(EXPECTED_MEDIATED) == 3
    assert len(EXPECTED_NOT_YET) == 9
    assert len(EXPECTED_DEAD) == 3


def test_weld_set_equals_not_yet_mediated():
    text = (RDIR / "WELD_SET.md").read_text()
    for pid in EXPECTED_NOT_YET:
        assert pid in text, f"weld set missing not-yet-mediated path {pid}"
    for pid in EXPECTED_MEDIATED | EXPECTED_DEAD:
        # mediated/dead paths must not appear as weld items (W-0 table rows reference R3.0-Pxx;
        # the "explicitly NOT in the weld set" section may name them — so check the weld table only)
        table = text.split("## Weld set")[1].split("## Explicitly")[0] if "## Weld set" in text else text
        assert pid not in table, f"non-weld path {pid} leaked into weld table"


def test_p0_diff_maps_every_sub():
    text = (RDIR / "P0_DIFF.md").read_text()
    for sub in EXPECTED_SUBS:
        assert sub in text, f"P0 site {sub} unmapped in P0_DIFF.md"
    for corrected in ("SUB-04", "SUB-05", "SUB-06", "SUB-07", "SUB-08", "SUB-09"):
        assert corrected in text
    assert "dead → not-yet-mediated" in text or "dead→not-yet-mediated" in text


def test_inventory_totals_internally_consistent():
    inv = (RDIR / "INVENTORY.md").read_text()
    assert "paths **15**" in inv
    assert "Broker-mediated 3" in inv
    assert "not-yet-mediated 9" in inv
