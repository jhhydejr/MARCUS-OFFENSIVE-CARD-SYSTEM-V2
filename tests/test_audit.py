import json
from pathlib import Path

from tools.audit_repository import audit

ROOT = Path(__file__).resolve().parents[1]


def test_repository_audit_parses_all_json():
    report = audit(ROOT)
    assert report["summary"]["json_parse_error_count"] == 0
    assert report["summary"]["json_count"] >= 125


def test_repository_audit_is_deterministic():
    first = audit(ROOT)
    second = audit(ROOT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_repository_contains_target_rendering_assets():
    report = audit(ROOT)
    assert report["summary"]["svg_count"] >= 25
    assert report["summary"]["png_count"] >= 28
