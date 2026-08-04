import json
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_numbered_call_slot_report_matches_coach_approved_grammar():
    system = MarcusSystem(ROOT)
    parsed = system.parser.parse(TARGET)
    report = system.build_call_slot_report(parsed)

    assert [(item.number, item.name) for item in report.offense] == [
        (1, "personnel"), (2, "backfield"), (3, "formation"),
        (4, "variation"), (5, "motion"), (6, "shift"),
        (7, "protection"), (8, "play"), (9, "tag"),
    ]
    assert [(item.number, item.name) for item in report.defense] == [
        (1, "structure"), (2, "front"), (3, "game"),
        (4, "pressure"), (5, "blitz"), (6, "coverage"),
    ]


def test_call_slot_report_distinguishes_missing_required_from_optional_omissions():
    system = MarcusSystem(ROOT)
    report = system.build_call_slot_report(system.parser.parse(TARGET))
    offense = {item.name: item for item in report.offense}
    defense = {item.name: item for item in report.defense}

    assert offense["play"].status == "MISSING_REQUIRED"
    assert offense["shift"].status == "OPTIONAL_OMITTED"
    assert offense["protection"].status == "OPTIONAL_OMITTED"
    assert defense["game"].status == "OPTIONAL_OMITTED"
    assert defense["coverage"].status == "PRESENT"
    assert report.missing_required_offense == ("play",)
    assert report.missing_required_defense == ()


def test_rendered_card_persists_numbered_call_slot_report(tmp_path):
    manifest = MarcusSystem(ROOT).draw(TARGET, tmp_path / "card")
    report_path = tmp_path / "card" / "call_slots.json"
    payload = json.loads(report_path.read_text())

    assert payload["schema"] == "marcus.call_slots.v1"
    assert payload["offense"][0]["number"] == 1
    assert payload["offense"][7]["name"] == "play"
    assert payload["card_type"] == "SCOUT_CARD"
    assert payload["offense"][7]["status"] == "OPTIONAL_OMITTED"
    assert manifest["outputs"]["call_slots"]["sha256"] == MarcusSystem.sha256(report_path)
