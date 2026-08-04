from pathlib import Path

import pytest

from marcus_cad.system import MarcusError, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def test_coordinate_engine_loads_real_rt_on_geometry():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates("FM-RT-001")

    assert len(coordinates) == 11
    by_player = {item.player: item for item in coordinates}
    assert set(by_player) == {"X", "Y", "RT", "RG", "C", "LG", "LT", "H", "Z", "QB", "B"}
    assert by_player["C"].x == 850.0
    assert by_player["C"].y == 619.0
    assert by_player["QB"].x == 850.0
    assert by_player["QB"].y == 703.0
    assert all(item.geometry_id == "GEOM-DRW-11-RT-ON-001" for item in coordinates)
    assert all(item.drawing_id == "DRW-11-RT-ON-001" for item in coordinates)


def test_coordinate_engine_loads_motion_composite_when_requested():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates(
        "FM-RT-001", variation="ON", motion="H ORBIT"
    )

    assert len(coordinates) == 11
    assert {item.geometry_id for item in coordinates} == {
        "GEOM-DRW-11-RT-ON-H-ORBIT-001"
    }
    assert {item.drawing_id for item in coordinates} == {
        "DRW-11-RT-ON-H-ORBIT-001"
    }


def test_coordinate_engine_rejects_unknown_formation_id():
    system = MarcusSystem(ROOT)
    with pytest.raises(MarcusError, match="Unknown formation id"):
        system.generate_coordinates("FM-NOT-REAL")


def test_coordinate_engine_rejects_unstored_variant():
    system = MarcusSystem(ROOT)
    with pytest.raises(MarcusError, match="No approved geometry variant"):
        system.generate_coordinates("FM-RT-001", variation="FLEX")
