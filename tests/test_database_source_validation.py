import json
from pathlib import Path

from marcus_cad.database_index import DatabaseObjectIndex
from marcus_cad.system import MarcusSystem


ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_target_resolution_sources_validate():
    system = MarcusSystem(ROOT)
    result = system.parse(TARGET)
    report = system.database_index.validate_resolution(
        result.resolved_ids,
        result.resolved_sources,
    )
    assert report["valid"] is True
    assert report["checked_source_count"] == len(result.resolved_ids)
    assert report["missing_files"] == []
    assert report["id_mismatches"] == []


def test_resolution_validation_rejects_wrong_source_file():
    system = MarcusSystem(ROOT)
    result = system.parse(TARGET)
    sources = dict(result.resolved_sources)
    sources["motions"] = "database/defense/COV-4-READ.json"
    report = system.database_index.validate_resolution(result.resolved_ids, sources)
    assert report["valid"] is False
    assert report["id_mismatches"] == ["motions"]


def test_draw_persists_database_resolution_validation(tmp_path):
    MarcusSystem(ROOT).draw(TARGET, tmp_path)
    report = json.loads(
        (tmp_path / "database_resolution_validation.json").read_text()
    )
    assert report["valid"] is True
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "database_resolution_validation" in manifest["outputs"]
