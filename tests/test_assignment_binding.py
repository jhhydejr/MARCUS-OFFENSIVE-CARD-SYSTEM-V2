import xml.etree.ElementTree as ET
from pathlib import Path

from marcus_cad.system import AssignmentObject, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def _approved(object_id: str, player: str) -> AssignmentObject:
    return AssignmentObject(
        object_id=object_id,
        assignment_type="TEST_ONLY",
        canonical_name=object_id,
        eligible_players=(player,),
        status="COACH_APPROVED",
        file="tests/in-memory",
    )


def test_binding_requires_complete_valid_assignment_map():
    system = MarcusSystem(ROOT)
    resolution = system.parse(CALL)
    coordinates = system.generate_coordinates(
        resolution.resolved_ids["formations"],
        personnel=resolution.personnel,
        variation=resolution.variation,
        motion=resolution.motion,
    )
    assert system.bind_assignments(coordinates, {}) == []

    assignments = {item.player: f"ASN-{item.player}" for item in coordinates}
    system.assignment_registry = {
        assignment_id: _approved(assignment_id, player)
        for player, assignment_id in assignments.items()
    }
    bindings = system.bind_assignments(coordinates, assignments)
    assert len(bindings) == 11
    assert [item.player for item in bindings] == [item.player for item in coordinates]


def test_draw_exports_empty_binding_file_when_assignments_are_not_approved(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path)
    binding_path = tmp_path / "assignment_bindings.json"
    assert binding_path.read_text(encoding="utf-8").strip() == "[]"
    assert manifest["assignment_bindings"] == []

    root = ET.parse(tmp_path / "card.svg").getroot()
    bindings = [element for element in root.iter() if element.tag.endswith("binding")]
    assert bindings == []
