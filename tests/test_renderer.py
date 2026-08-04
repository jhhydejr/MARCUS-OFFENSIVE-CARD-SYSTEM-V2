from pathlib import Path
import xml.etree.ElementTree as ET

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def _offensive_positions(path: Path) -> dict[str, tuple[float, float]]:
    root = ET.parse(path).getroot()
    positions = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "text":
            continue
        label = (element.text or "").strip()
        if label in {"X", "LT", "LG", "C", "RG", "RT", "Y", "H", "Z", "Q", "B"} and float(element.attrib.get("y", "0")) >= 580:
            positions[label] = (float(element.attrib["x"]), float(element.attrib["y"]) - 5.0)
    return positions


def test_draw_uses_canonical_coordinates_for_svg(tmp_path):
    system = MarcusSystem(ROOT)
    call = "(11) RT ON H ORBIT"
    result = system.parse(call)
    expected = {
        ("Q" if c.player == "QB" else c.player): (c.x, c.y)
        for c in system.generate_coordinates(
            result.resolved_ids["formations"],
            personnel=result.personnel,
            variation=result.variation,
            motion=result.motion,
        )
    }
    manifest = system.draw(call, tmp_path / "card")
    assert manifest["renderer"] == "DRAWING_SCENE_DRIVEN"
    assert manifest["coordinate_count"] == 11
    assert _offensive_positions(Path(manifest["outputs"]["svg"]["path"])) == expected


def test_target_card_uses_coordinate_driven_renderer(tmp_path):
    manifest = MarcusSystem(ROOT).draw(
        "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ", tmp_path / "target"
    )
    assert manifest["renderer"] == "DRAWING_SCENE_DRIVEN"
    assert Path(manifest["outputs"]["png"]["path"]).stat().st_size > 0
    assert Path(manifest["outputs"]["pdf"]["path"]).stat().st_size > 0
