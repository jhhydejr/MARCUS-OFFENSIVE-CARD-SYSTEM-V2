import xml.etree.ElementTree as ET
from pathlib import Path

from marcus_cad.system import AssignmentObject, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_renderer_attaches_canonical_assignment_metadata(monkeypatch, tmp_path):
    system = MarcusSystem(ROOT)
    resolution = system.parse(CALL)
    coordinates = system.generate_coordinates(
        resolution.resolved_ids["formations"],
        personnel=resolution.personnel,
        variation=resolution.variation,
        motion=resolution.motion,
    )
    assignments = {item.player: f"ASN-{item.player}" for item in coordinates}
    system.assignment_registry = {
        assignment_id: AssignmentObject(
            object_id=assignment_id,
            assignment_type="TEST_ONLY",
            canonical_name=f"Assignment for {player}",
            eligible_players=(player,),
            status="COACH_APPROVED",
            file="tests/in-memory",
        )
        for player, assignment_id in assignments.items()
    }
    monkeypatch.setattr(system, "resolve_assignments", lambda _: assignments)

    manifest = system.draw(CALL, tmp_path)
    assert manifest["card_completeness"] == "ASSIGNMENT_COMPLETE"

    root = ET.parse(tmp_path / "card.svg").getroot()
    offensive = [
        element for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
        and element.attrib.get("data-player")
    ]
    assert len(offensive) == 11
    assert {element.attrib["data-assignment-id"] for element in offensive} == set(assignments.values())
    assert all(element.attrib["data-assignment-type"] == "TEST_ONLY" for element in offensive)


def test_renderer_leaves_assignment_attributes_absent_when_not_approved(tmp_path):
    MarcusSystem(ROOT).draw(CALL, tmp_path)
    root = ET.parse(tmp_path / "card.svg").getroot()
    offensive = [
        element for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
        and element.attrib.get("data-player")
    ]
    assert len(offensive) == 11
    assert all("data-assignment-id" not in element.attrib for element in offensive)
