import json
from dataclasses import replace
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def _scene(system: MarcusSystem):
    resolution = system.parse(CALL)
    coordinates = system.generate_coordinates(
        resolution.resolved_ids["formations"],
        personnel=resolution.personnel,
        variation=resolution.variation,
        motion=resolution.motion,
    )
    coordinate_validation = system.validate_coordinates(coordinates)
    assignments = system.resolve_assignments(resolution)
    plan = system.build_assignment_plan(coordinates, assignments)
    assignment_validation = system.validate_assignments(coordinates, assignments)
    bindings = system.bind_assignments(coordinates, assignments)
    play_card = system.compose_play_card(
        resolution,
        coordinates,
        coordinate_validation,
        plan,
        assignment_validation,
        bindings,
    )
    return system.build_drawing_scene(play_card)


def test_drawing_scene_validation_accepts_canonical_scene():
    system = MarcusSystem(ROOT)
    validation = system.validate_drawing_scene(_scene(system))
    assert validation.valid
    assert validation.offensive_player_count == 11
    assert validation.actual_layer_order == validation.expected_layer_order


def test_drawing_scene_validation_rejects_layer_count_mismatch():
    system = MarcusSystem(ROOT)
    scene = _scene(system)
    bad_layers = tuple(
        replace(layer, object_count=10) if layer.name == "offense" else layer
        for layer in scene.layers
    )
    validation = system.validate_drawing_scene(replace(scene, layers=bad_layers))
    assert not validation.valid
    assert "offense" in validation.invalid_object_counts


def test_draw_writes_scene_validation_artifact(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")
    item = manifest["outputs"]["drawing_scene_validation"]
    path = Path(item["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["valid"] is True
    assert item["sha256"] == system.sha256(path)
    assert manifest["drawing_scene_validation"]["valid"] is True
