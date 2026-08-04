import json
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_rt_on_approved_asset_bundle_is_reusable():
    validation = MarcusSystem(ROOT).validate_asset_reuse("DRW-11-RT-ON-001")
    assert validation.valid is True
    assert validation.reused_files == {
        "coordinates": "artifacts/drawings/DRW-11-RT-ON-001/coordinates.json",
        "metadata": "artifacts/drawings/DRW-11-RT-ON-001/metadata.json",
        "png": "artifacts/drawings/DRW-11-RT-ON-001/preview.png",
        "svg": "artifacts/drawings/DRW-11-RT-ON-001/drawing.svg",
    }
    assert set(validation.source_hashes) == {"coordinates", "metadata", "png", "svg"}


def test_target_compile_records_exact_approved_asset_reuse(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(TARGET, tmp_path)
    payload = json.loads((tmp_path / "asset_reuse.json").read_text())
    assert payload["valid"] is True
    assert payload["drawing_id"] == "DRW-LH-11-RT-ON-H-ORBIT-VS-4-2-STUD-COV4READ-001"
    assert manifest["asset_reuse"]["drawing_id"] == payload["drawing_id"]
    assert "asset_reuse" in manifest["outputs"]


def test_asset_reuse_detects_missing_stored_file(tmp_path):
    # Use a copied project so the approved repository is not changed.
    import shutil
    project = tmp_path / "project"
    shutil.copytree(ROOT, project)
    missing = project / "artifacts/drawings/DRW-11-RT-ON-001/drawing.svg"
    missing.unlink()
    validation = MarcusSystem(project).validate_asset_reuse("DRW-11-RT-ON-001")
    assert validation.valid is False
    assert validation.missing_files == ["svg"]
