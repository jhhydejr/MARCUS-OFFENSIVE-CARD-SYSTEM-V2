from pathlib import Path

from marcus_cad.system import AssignmentObject, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def _approved(object_id: str, players: tuple[str, ...]) -> AssignmentObject:
    return AssignmentObject(
        object_id=object_id,
        assignment_type="TEST_ONLY",
        canonical_name=object_id,
        eligible_players=players,
        status="COACH_APPROVED",
        file="tests/in-memory",
    )


def test_unknown_assignment_ids_are_blocked():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates("FM-RT-001")
    assignments = {item.player: f"ASN-{item.player}" for item in coordinates}

    report = system.validate_assignments(coordinates, assignments)

    assert report.valid is False
    assert len(report.unknown_assignment_ids) == 11
    assert {item["reason"] for item in report.blockers} == {"OBJECT_NOT_IN_DATABASE"}


def test_complete_approved_registry_mapping_is_valid():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates("FM-RT-001")
    assignments = {item.player: f"ASN-{item.player}" for item in coordinates}
    system.assignment_registry = {
        assignment_id: _approved(assignment_id, (player,))
        for player, assignment_id in assignments.items()
    }

    report = system.validate_assignments(coordinates, assignments)

    assert report.valid is True
    assert report.assigned_player_count == 11
    assert report.unknown_assignment_ids == []
    assert report.ineligible_assignments == []


def test_assignment_player_eligibility_is_enforced():
    system = MarcusSystem(ROOT)
    coordinates = system.generate_coordinates("FM-RT-001")
    assignments = {item.player: f"ASN-{item.player}" for item in coordinates}
    system.assignment_registry = {
        assignment_id: _approved(assignment_id, (player,))
        for player, assignment_id in assignments.items()
    }
    system.assignment_registry[assignments["X"]] = _approved(assignments["X"], ("Z",))

    report = system.validate_assignments(coordinates, assignments)

    assert report.valid is False
    assert report.ineligible_assignments == ["X"]
    assert {item["reason"] for item in report.blockers} == {"PLAYER_NOT_ELIGIBLE"}
