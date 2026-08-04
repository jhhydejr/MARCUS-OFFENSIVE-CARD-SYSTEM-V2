from pathlib import Path
import json
import pytest

from marcus_cad.system import MarcusError, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_draw_writes_composed_play_card(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(TARGET, tmp_path / "card")
    play_card_path = Path(manifest["outputs"]["play_card"]["path"])
    assert play_card_path.exists()
    payload = json.loads(play_card_path.read_text(encoding="utf-8"))
    assert payload["source_call"] == TARGET
    assert payload["drawing_id"] == "DRW-LH-11-RT-ON-H-ORBIT-VS-4-2-STUD-COV4READ-001"
    assert len(payload["coordinates"]) == 11
    assert len(payload["assignment_plan"]) == 11
    assert payload["completeness"] == manifest["card_completeness"]
    assert manifest["outputs"]["play_card"]["sha256"] == system.sha256(play_card_path)


def test_composer_rejects_unrenderable_resolution():
    system = MarcusSystem(ROOT)
    resolution = system.parse("(11) UNKNOWN FORMATION")
    with pytest.raises(MarcusError, match="unrenderable"):
        system.compose_play_card(
            resolution,
            [],
            system.validate_coordinates([]),
            [],
            system.validate_assignments([], {}),
            [],
        )
