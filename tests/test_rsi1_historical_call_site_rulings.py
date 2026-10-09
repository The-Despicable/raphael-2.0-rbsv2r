"""tests/test_rsi1_historical_call_site_rulings.py — historical call-site ruling contract."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULING_FILE = REPO / "evidence" / "historical_validation_call_site_rulings.json"
REPORT_FILE = REPO / "reports" / "HISTORICAL_VALIDATION_CALL_SITE_RULING_20261009.md"


def test_ruling_file_exists():
    assert RULING_FILE.exists(), f"Historical ruling JSON missing: {RULING_FILE}"


def test_report_file_exists():
    assert REPORT_FILE.exists(), f"Historical ruling report missing: {REPORT_FILE}"


def test_all_sites_have_ruling():
    with open(RULING_FILE, encoding="utf-8") as f:
        data = json.load(f)
    sites = data.get("sites", [])
    assert len(sites) == data.get("total_sites", 23)
    for site in sites:
        assert site.get("historical_only") is True
        assert site.get("current_authority_granted_by_default") is False


def test_no_current_authority_by_default():
    with open(RULING_FILE, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("current_authority_granted_by_default") is False
    assert data.get("default_ruling") == "HISTORICAL_ONLY"
