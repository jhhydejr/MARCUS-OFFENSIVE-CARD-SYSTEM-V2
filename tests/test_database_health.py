import json
from pathlib import Path

from marcus_cad.database_health import DatabaseHealthEngine

ROOT = Path(__file__).resolve().parents[1]


def test_database_health_report_is_valid_and_deterministic():
    engine = DatabaseHealthEngine(ROOT)
    first = engine.audit()
    second = engine.audit()
    assert first.valid is True
    assert first.json_file_count >= 75
    assert first.canonical_object_count >= 60
    assert first.duplicate_definition_count == 0
    assert first.broken_reference_count == 0
    assert first.circular_reference_count == 0
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)


def test_database_health_writes_machine_readable_report(tmp_path):
    output = tmp_path / "database_health.json"
    report = DatabaseHealthEngine(ROOT).write_report(output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "marcus-cad.database-health.v1"
    assert payload["valid"] == report.valid
    assert payload["orphaned_object_count"] == len(payload["orphaned_objects"])


def test_database_health_detects_broken_explicit_reference(tmp_path):
    database = tmp_path / "database" / "offense"
    database.mkdir(parents=True)
    (database / "A.json").write_text(json.dumps({
        "object_id": "OBJ-A",
        "object_type": "test",
        "member_object_ids": ["OBJ-MISSING"],
    }), encoding="utf-8")
    report = DatabaseHealthEngine(tmp_path).audit()
    assert report.valid is False
    assert report.broken_reference_count == 1
    assert report.broken_references[0]["target_id"] == "OBJ-MISSING"
