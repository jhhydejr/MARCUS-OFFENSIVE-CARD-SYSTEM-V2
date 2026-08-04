from pathlib import Path

from marcus_cad.system import MarcusSystem


ROOT = Path(__file__).resolve().parents[1]
CALL = "(11) DBLS LT H STAR VS ODD COV 4"


def test_scout_call_terms_are_parsed_as_longest_approved_phrases():
    result = MarcusSystem(ROOT).parse(CALL, card_type="SCOUT_CARD")

    assert result.personnel == "11"
    assert result.formation == "DBLS LT"
    assert result.motion == "H STAR"
    assert result.structure == "ODD"
    assert result.coverage == "COV 4"
    assert result.unknown_offense_tokens == []
    assert result.unknown_defense_tokens == []
    assert result.call_grammar_validation.valid is True


def test_scout_call_reports_missing_geometry_instead_of_unknown_tokens():
    result = MarcusSystem(ROOT).parse(CALL, card_type="SCOUT_CARD")

    reasons = {(item["object"], item["reason"]) for item in result.blockers}
    assert ("motions:H STAR", "TOKEN_RECOGNIZED_GEOMETRY_NOT_CANONICAL") in reasons
    assert ("defensive_personnel:ODD", "TOKEN_RECOGNIZED_GEOMETRY_NOT_CANONICAL") in reasons
    assert ("coverages:COV 4", "TOKEN_RECOGNIZED_GEOMETRY_NOT_CANONICAL") in reasons
    assert not any(reason == "UNKNOWN_TOKEN" for _, reason in reasons)
    assert result.renderable is False
