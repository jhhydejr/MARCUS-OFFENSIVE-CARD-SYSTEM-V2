from dataclasses import replace
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_coordinates_pass_structural_validation():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates(
        "FM-RT-001", variation="ON", motion="H ORBIT"
    )
    report = system.validate_coordinates(coordinates)

    assert report.valid is True
    assert report.player_count == 11
    assert report.unique_player_count == 11
    assert report.missing_players == []
    assert report.unexpected_players == []
    assert report.duplicate_positions == []
    assert report.invalid_coordinates == []
    assert report.invalid_radii == []
    assert report.geometry_ids == ["GEOM-DRW-11-RT-ON-H-ORBIT-001"]
    assert report.drawing_ids == ["DRW-11-RT-ON-H-ORBIT-001"]


def test_coordinate_validation_detects_duplicate_position():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates("FM-RT-001")
    coordinates[1] = replace(
        coordinates[1],
        x=coordinates[0].x,
        y=coordinates[0].y,
    )
    report = system.validate_coordinates(coordinates)

    assert report.valid is False
    assert report.duplicate_positions == [["X", "Y"]]


def test_draw_writes_coordinate_validation_to_outputs(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(
        "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ",
        tmp_path / "card",
    )

    assert manifest["coordinate_validation"]["valid"] is True
    validation_path = Path(manifest["outputs"]["validation"]["path"])
    payload = __import__("json").loads(validation_path.read_text(encoding="utf-8"))
    assert payload["coordinate_validation"]["valid"] is True
    assert payload["coordinate_validation"]["player_count"] == 11
