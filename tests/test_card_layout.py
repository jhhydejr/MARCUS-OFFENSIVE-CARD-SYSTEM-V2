from dataclasses import replace
from pathlib import Path
import json

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_approved_card_layout_is_valid():
    system = MarcusSystem(ROOT)
    layout = system.load_card_layout()
    validation = system.validate_card_layout(layout)
    assert validation.valid
    assert validation.actual_sections == ["title", "diagram", "notes", "validation", "metadata"]


def test_layout_validator_rejects_overlap():
    system = MarcusSystem(ROOT)
    layout = system.load_card_layout()
    sections = list(layout.sections)
    sections[1] = replace(sections[1], y=50)
    validation = system.validate_card_layout(replace(layout, sections=tuple(sections)))
    assert not validation.valid
    assert ["diagram", "title"] in validation.overlapping_sections


def test_draw_persists_layout_contract(tmp_path):
    manifest = MarcusSystem(ROOT).draw(TARGET, tmp_path / "card")
    assert manifest["card_layout_id"] == "LAYOUT-PLAY-CARD-001"
    payload = json.loads(Path(manifest["outputs"]["card_layout"]["path"]).read_text())
    assert payload["sections"][1]["name"] == "diagram"
    assert manifest["card_layout_validation"]["valid"]
