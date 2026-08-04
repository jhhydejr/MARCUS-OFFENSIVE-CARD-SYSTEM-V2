import json
import xml.etree.ElementTree as ET
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_draw_writes_ordered_drawing_scene(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")
    path = Path(manifest["outputs"]["drawing_scene"]["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert [item["name"] for item in payload["layers"]] == [
        "field_template",
        "defense",
        "offense",
        "assignments",
        "labels_metadata",
    ]
    assert [item["order"] for item in payload["layers"]] == [10, 20, 30, 40, 50]
    assert payload["layers"][2]["object_count"] == 11
    assert len(payload["offensive_players"]) == 11
    assert manifest["renderer"] == "DRAWING_SCENE_DRIVEN"
    assert manifest["outputs"]["drawing_scene"]["sha256"] == system.sha256(path)


def test_svg_contains_drawing_scene_metadata(tmp_path):
    MarcusSystem(ROOT).draw(CALL, tmp_path / "card")
    root = ET.parse(tmp_path / "card" / "card.svg").getroot()
    scene = [
        element for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "marcus-drawing-scene"
    ]
    assert len(scene) == 1
    assert scene[0].attrib["layers"] == (
        "field_template,defense,offense,assignments,labels_metadata"
    )
