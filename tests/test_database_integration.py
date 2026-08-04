import json
from pathlib import Path

from marcus_cad.database_index import DatabaseObjectIndex
from marcus_cad.system import MarcusSystem


ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_database_index_links_real_football_objects():
    catalog = json.loads((ROOT / "database/master/catalog.json").read_text())
    index = DatabaseObjectIndex(ROOT)
    report = index.report(catalog)
    assert report["valid"] is True
    assert report["database_file_links"] >= 20
    assert report["catalog_object_count"] == 37
    assert index.resolve("MOT-H-ORBIT").file == "database/offense/MOT-H-ORBIT.json"
    assert index.resolve("COV-4-READ").file == "database/defense/COV-4-READ.json"


def test_target_call_records_database_sources():
    result = MarcusSystem(ROOT).parse(TARGET)
    assert result.resolved_sources == {
        "backfields": "database/offense/backfields/BF-GUN-001.json",
        "coverages": "database/defense/COV-4-READ.json",
        "defensive_personnel": "database/defense/DEF-PER-4-2.json",
        "defensive_structures": "database/defense/DEF-STRUCT-STUD.json",
        "field_locations": "database/offense/field_locations/LOC-LH.json",
        "formations": "database/offense/FRM-11-RT-ON.json",
        "motions": "database/offense/MOT-H-ORBIT.json",
        "personnel": "database/master/catalog.json",
        "variations": "database/offense/variations/VARIATION-ON-001.json",
    }


def test_draw_persists_database_resolution(tmp_path):
    system = MarcusSystem(ROOT)
    system.draw(TARGET, tmp_path)
    payload = json.loads((tmp_path / "database_resolution.json").read_text())
    assert payload["resolved_ids"]["formations"] == "FM-RT-001"
    assert payload["resolved_sources"]["motions"] == "database/offense/MOT-H-ORBIT.json"
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "database_resolution" in manifest["outputs"]
