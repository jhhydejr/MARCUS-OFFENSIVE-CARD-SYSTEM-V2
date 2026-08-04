import json
from pathlib import Path

import pytest

from marcus_cad.system import MarcusError, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_target_call_reports_missing_approved_assignments():
    system = MarcusSystem(ROOT)
    resolution = system.parse(CALL)
    coordinates = system.generate_coordinates(
        resolution.resolved_ids["formations"],
        personnel=resolution.personnel,
        variation=resolution.variation,
        motion=resolution.motion,
    )
    assignments = system.resolve_assignments(resolution)
    report = system.validate_assignments(coordinates, assignments)

    assert assignments == {}
    assert report.valid is False
    assert report.status == "NOT_READY"
    assert report.assigned_player_count == 0
    assert set(report.missing_players) == {item.player for item in coordinates}
    assert report.blockers[0]["reason"] == "NO_APPROVED_ASSIGNMENT_OBJECTS_FOR_CALL"


def test_draw_persists_assignment_readiness_without_inventing_data(tmp_path):
    system = MarcusSystem(ROOT)
    manifest = system.draw(CALL, tmp_path / "card")

    assert manifest["card_completeness"] == "FORMATION_ONLY"
    assert manifest["assignment_validation"]["valid"] is False
    validation = json.loads(
        Path(manifest["outputs"]["validation"]["path"]).read_text(encoding="utf-8")
    )
    assert validation["assignment_validation"]["status"] == "NOT_READY"


def test_strict_assignment_mode_blocks_export_completion(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "strict-card"

    with pytest.raises(MarcusError, match="Approved assignment validation failed"):
        system.draw(CALL, out, require_assignments=True)

    payload = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    assert payload["assignment_validation"]["valid"] is False
