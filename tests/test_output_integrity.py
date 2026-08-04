import json
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_draw_writes_valid_output_integrity_artifact(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")
    integrity = manifest["output_integrity"]
    assert integrity["valid"] is True
    assert "svg" in integrity["checked_outputs"]
    assert "validation" in integrity["checked_outputs"]
    artifact = Path(manifest["outputs"]["output_integrity"]["path"])
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload == integrity
    assert manifest["outputs"]["output_integrity"]["sha256"] == system.sha256(artifact)


def test_output_integrity_detects_tampered_artifact(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")
    svg = Path(manifest["outputs"]["svg"]["path"])
    svg.write_text(svg.read_text(encoding="utf-8") + "\n<!-- tampered -->\n", encoding="utf-8")
    validation = system.validate_output_integrity(manifest, tmp_path / "card")
    assert validation.valid is False
    assert validation.hash_mismatches == ["svg"]


def test_output_integrity_rejects_path_outside_card_directory(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    manifest["outputs"]["outside"] = {
        "path": str(outside),
        "sha256": system.sha256(outside),
    }
    validation = system.validate_output_integrity(manifest, tmp_path / "card")
    assert validation.valid is False
    assert validation.paths_outside_card_directory == ["outside"]
