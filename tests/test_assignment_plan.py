from pathlib import Path
import json

from marcus_cad.system import MarcusSystem


ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_assignment_plan_has_one_entry_per_coordinate():
    system = MarcusSystem(ROOT)
    resolution = system.parse(CALL)
    coords = system.generate_coordinates(
        resolution.resolved_ids["formations"],
        personnel=resolution.personnel,
        variation=resolution.variation,
        motion=resolution.motion,
    )
    plan = system.build_assignment_plan(coords, {})
    assert len(plan) == 11
    assert [item.player for item in plan] == [item.player for item in coords]
    assert all(item.status == "MISSING" for item in plan)


def test_draw_writes_assignment_plan(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path)
    path = tmp_path / "assignment_plan.json"
    assert path.exists()
    payload = json.loads(path.read_text())
    assert len(payload) == 11
    assert manifest["outputs"]["assignment_plan"]["sha256"]
    assert manifest["card_completeness"] == "FORMATION_ONLY"
