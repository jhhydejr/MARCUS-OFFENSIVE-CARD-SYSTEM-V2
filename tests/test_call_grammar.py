import json
from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def test_call_grammar_file_records_coach_approved_slot_order():
    grammar = json.loads((ROOT / "database/master/call_grammar.json").read_text())
    assert grammar["status"] == "COACH_APPROVED"
    assert [item["name"] for item in grammar["offensive_call"]["ordered_slots"]] == [
        "personnel", "backfield", "formation", "variation", "motion", "shift",
        "protection", "play", "tag",
    ]
    assert grammar["offensive_call"]["required_slots"] == ["personnel", "formation", "play"]
    assert [item["name"] for item in grammar["defensive_call"]["ordered_slots"]] == [
        "structure", "front", "game", "pressure", "blitz", "coverage",
    ]
    assert grammar["defensive_call"]["required_slots"] == ["structure", "coverage"]


def test_target_call_maps_defense_to_structure_front_and_coverage():
    result = MarcusSystem(ROOT).parse("LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ")
    assert result.structure == "4-2"
    assert result.front == "STUD"
    assert result.coverage == "COV 4 READ"
    assert result.game is None
    assert result.pressure is None
    assert result.blitz is None


def test_target_call_reports_missing_required_offensive_play_without_inventing_it():
    result = MarcusSystem(ROOT).parse("LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ", card_type="PLAY_CARD")
    validation = result.call_grammar_validation
    assert validation.valid is False
    assert validation.missing_offense_slots == ["play"]
    assert validation.missing_defense_slots == []
    assert validation.offense_slots["play"] is None


def test_optional_slots_may_be_absent():
    system = MarcusSystem(ROOT)
    # Inject a test-only play object into the in-memory catalog, then rebuild the
    # system parser/registry through a temporary project copy is unnecessary for
    # grammar validation itself; the validation contract accepts a parsed-like object.
    parsed = type("Parsed", (), {
        "personnel": "11", "formation": "RT", "variation": None,
        "motion": None, "shift": None, "protection": None,
        "play": "TEST PLAY", "tag": None, "structure": None,
        "front": None, "game": None, "pressure": None, "blitz": None,
        "coverage": None, "defense_text": "",
    })()
    validation = system.validate_call_grammar(parsed)
    assert validation.valid is True
    assert validation.missing_offense_slots == []
    assert validation.missing_defense_slots == []


def test_defense_required_slots_apply_when_vs_is_present():
    system = MarcusSystem(ROOT)
    parsed = type("Parsed", (), {
        "personnel": "11", "formation": "RT", "variation": None,
        "motion": None, "shift": None, "protection": None,
        "play": "TEST PLAY", "tag": None, "structure": "4-2",
        "front": None, "game": None, "pressure": None, "blitz": None,
        "coverage": None, "defense_text": "4-2",
    })()
    validation = system.validate_call_grammar(parsed)
    assert validation.valid is False
    assert validation.missing_defense_slots == ["coverage"]


def test_canonical_slot_order_has_no_order_violations():
    result = MarcusSystem(ROOT).parse(
        "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"
    )
    assert result.offense_slot_order_violations == []
    assert result.defense_slot_order_violations == []


def test_offensive_slots_out_of_order_are_blocked():
    result = MarcusSystem(ROOT).parse(
        "LH (11) RT H ORBIT ON VS 4-2 STUD COV 4 READ"
    )
    assert result.call_grammar_validation.offense_valid is False
    assert result.offense_slot_order_violations == ["motion_before_variation"]
    assert {
        "object": "offense_order:motion_before_variation",
        "reason": "CALL_ORDER_VIOLATION",
    } in result.blockers


def test_defensive_slots_out_of_order_are_blocked():
    result = MarcusSystem(ROOT).parse(
        "LH (11) RT ON H ORBIT VS COV 4 READ 4-2 STUD"
    )
    assert result.call_grammar_validation.defense_valid is False
    assert result.defense_slot_order_violations == ["coverage_before_front"]
    assert {
        "object": "defense_order:coverage_before_front",
        "reason": "CALL_ORDER_VIOLATION",
    } in result.blockers
