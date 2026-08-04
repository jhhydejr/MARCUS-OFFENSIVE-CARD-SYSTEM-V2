import json
from pathlib import Path

import pytest

from marcus_cad.system import MarcusError, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
SCOUT_CALL = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_scout_card_does_not_require_offensive_play_slot():
    system = MarcusSystem(ROOT)
    parsed = system.parser.parse(SCOUT_CALL)
    validation = system.validate_call_grammar(parsed, card_type="SCOUT_CARD")
    report = system.build_call_slot_report(parsed, card_type="SCOUT_CARD")

    assert validation.valid
    assert validation.card_type == "SCOUT_CARD"
    assert validation.missing_offense_slots == []
    assert report.card_type == "SCOUT_CARD"
    assert report.offense[7].name == "play"
    assert report.offense[7].required is False
    assert report.offense[7].status == "OPTIONAL_OMITTED"


def test_play_card_requires_offensive_play_slot():
    system = MarcusSystem(ROOT)
    parsed = system.parser.parse(SCOUT_CALL)
    validation = system.validate_call_grammar(parsed, card_type="PLAY_CARD")
    report = system.build_call_slot_report(parsed, card_type="PLAY_CARD")

    assert not validation.valid
    assert validation.missing_offense_slots == ["play"]
    assert report.card_type == "PLAY_CARD"
    assert report.offense[7].required is True
    assert report.offense[7].status == "MISSING_REQUIRED"


def test_scout_card_renders_but_play_card_blocks_without_slot_7(tmp_path):
    system = MarcusSystem(ROOT)
    scout = system.draw(SCOUT_CALL, tmp_path / "scout", card_type="SCOUT_CARD")
    payload = json.loads((tmp_path / "scout" / "call_slots.json").read_text())
    assert scout["outputs"]["call_slots"]["sha256"] == system.sha256(tmp_path / "scout" / "call_slots.json")
    assert payload["card_type"] == "SCOUT_CARD"

    with pytest.raises(MarcusError):
        system.draw(SCOUT_CALL, tmp_path / "play", card_type="PLAY_CARD")
    validation = json.loads((tmp_path / "play" / "validation.json").read_text())
    assert {"object": "offense_slot:play", "reason": "MISSING_REQUIRED_SLOT"} in validation["blockers"]
