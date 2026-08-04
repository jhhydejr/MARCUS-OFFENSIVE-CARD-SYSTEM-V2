from pathlib import Path

from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def test_known_dbls_rt_is_renderable():
    result = MarcusSystem(ROOT).parse("(11) DBLS RT")
    assert result.renderable
    assert result.drawing_id == "DRW-11-DBLS-RT-001"


def test_target_call_resolves_known_tokens_and_reports_blockers():
    result = MarcusSystem(ROOT).parse("LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ")
    assert result.field_location == "LH"
    assert result.personnel == "11"
    assert result.formation == "RT"
    assert result.variation == "ON"
    assert result.motion == "H ORBIT"
    assert result.defensive_personnel == "4-2"
    assert result.defensive_structure == "STUD"
    assert result.coverage == "COV 4 READ"
    assert result.renderable
    blocker_names = {b["object"] for b in result.blockers}
    assert "formations:RT" not in blocker_names
    assert "modifiers:ON" not in blocker_names
    assert "motions:H ORBIT" not in blocker_names
    assert blocker_names == set()


def test_rt_on_exact_composite_is_renderable(tmp_path):
    system = MarcusSystem(ROOT)
    result = system.parse("(11) RT ON")
    assert result.renderable is True
    assert result.drawing_id == "DRW-11-RT-ON-001"
    manifest = system.draw("(11) RT ON", tmp_path / "rt_on")
    assert Path(manifest["outputs"]["svg"]["path"]).exists()
    assert Path(manifest["outputs"]["png"]["path"]).exists()
    assert Path(manifest["outputs"]["pdf"]["path"]).exists()


def test_target_call_has_zero_blockers():
    system = MarcusSystem(ROOT)
    result = system.parse("LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ")
    assert result.blockers == []
    assert result.renderable is True


def test_rt_on_h_orbit_is_renderable(tmp_path):
    system = MarcusSystem(ROOT)
    result = system.parse("(11) RT ON H ORBIT")
    assert result.renderable
    assert result.drawing_id == "DRW-11-RT-ON-H-ORBIT-001"
    manifest = system.draw("(11) RT ON H ORBIT", tmp_path / "orbit")
    assert Path(manifest["outputs"]["svg"]["path"]).exists()
    assert Path(manifest["outputs"]["png"]["path"]).exists()
    assert Path(manifest["outputs"]["pdf"]["path"]).exists()


def test_h_orbit_has_no_destination_h_symbol():
    import xml.etree.ElementTree as ET
    svg_path = ROOT / "artifacts" / "drawings" / "DRW-11-RT-ON-H-ORBIT-001" / "drawing.svg"
    root = ET.parse(svg_path).getroot()
    destination_h_circles = [
        e for e in root.iter()
        if e.tag.split("}")[-1] == "circle"
        and e.attrib.get("cx") == "958"
        and e.attrib.get("cy") == "727"
    ]
    destination_h_labels = [
        e for e in root.iter()
        if e.tag.split("}")[-1] == "text"
        and (e.text or "").strip() == "H"
        and e.attrib.get("x") == "958"
        and e.attrib.get("y") == "732"
    ]
    assert destination_h_circles == []
    assert destination_h_labels == []


def test_h_orbit_policy_is_object_specific():
    import json
    record = json.loads((ROOT / "database" / "offense" / "MOT-H-ORBIT.json").read_text())
    policy = record["rendering_policy"]
    assert policy["show_destination_marker"] is False
    assert policy["rule_scope"] == "H ORBIT only"


def test_h_orbit_path_starts_at_player_circle_edge():
    import json, math
    record = json.loads((ROOT / "database" / "offense" / "MOT-H-ORBIT.json").read_text())
    path = record["renderer_path"]
    cx, cy = path["player_center"]
    sx, sy = path["start"]
    assert math.isclose(math.hypot(sx - cx, sy - cy), path["player_radius"], abs_tol=1e-6)
    assert path["origin_reference"] == "PLAYER_SYMBOL_EDGE"


def test_h_orbit_svg_uses_edge_start():
    import xml.etree.ElementTree as ET
    svg_path = ROOT / "artifacts" / "drawings" / "DRW-11-RT-ON-H-ORBIT-001" / "drawing.svg"
    root = ET.parse(svg_path).getroot()
    motion_paths = [
        e.attrib.get("d", "")
        for e in root.iter()
        if e.tag.split("}")[-1] == "path" and "marker-end" in e.attrib
    ]
    assert any(d.startswith("M 485.843782 629.000000") for d in motion_paths)


def test_target_call_exports_all_formats(tmp_path):
    system = MarcusSystem(ROOT)
    call = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"
    result = system.parse(call)
    assert result.drawing_id == "DRW-LH-11-RT-ON-H-ORBIT-VS-4-2-STUD-COV4READ-001"
    manifest = system.draw(call, tmp_path / "target")
    assert Path(manifest["outputs"]["svg"]["path"]).exists()
    assert Path(manifest["outputs"]["png"]["path"]).exists()
    assert Path(manifest["outputs"]["pdf"]["path"]).exists()


def test_defense_records_have_source_evidence():
    import json
    for name in ["DEF-PER-4-2.json", "DEF-STRUCT-STUD.json", "COV-4-READ.json"]:
        record = json.loads((ROOT / "database" / "defense" / name).read_text())
        assert record["status"] == "SOURCE_TRACED"
        assert "source" in record


def test_expanded_title_box_and_defense_text():
    import xml.etree.ElementTree as ET
    p = ROOT / "artifacts" / "drawings" / "DRW-LH-11-RT-ON-H-ORBIT-VS-4-2-STUD-COV4READ-001" / "drawing.svg"
    r = ET.parse(p).getroot()
    boxes = [e for e in r.iter() if e.tag.split("}")[-1]=="rect" and e.attrib.get("x")=="250" and e.attrib.get("width")=="1200" and e.attrib.get("height")=="92"]
    assert len(boxes) == 1
    labels = [e for e in r.iter() if e.tag.split("}")[-1]=="text" and (e.text or "").strip() in {"E","N","T","SE","W","M","S","FS","SS","C"} and float(e.attrib.get("y","9999")) <= 548]
    assert labels
    assert all(e.attrib.get("font-size")=="26" for e in labels)
    assert all(e.attrib.get("font-weight")=="700" for e in labels)


def test_global_style_and_renderer_policy():
    import json
    style=json.loads((ROOT/"database"/"renderer"/"global_card_style.json").read_text())
    policy=json.loads((ROOT/"policies"/"renderer_first_policy.json").read_text())
    assert style["offensive_player_radius"]==19
    assert style["field_number_fill"]=="#808080"
    assert policy["status"]=="APPROVED"
    assert any("No AI-generated image" in x for x in policy["rules"])


def test_formation_registry_contains_imported_source_objects():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_registry.json").read_text())
    source_ids = {item["object_id"] for item in registry["source_imported"]}
    approved_ids = {item["object_id"] for item in registry["approved_existing"]}
    assert source_ids == {"FRM-21-RT", "FRM-12-LT-M"}
    assert {"FRM-11-TRIPS-RT-LH", "FRM-11-TREY-LT-ON-LH"}.issubset(approved_ids)


def test_imported_formation_records_are_source_traced():
    import json
    directory = ROOT / "database" / "offense" / "formations"
    expected_status = {
        "FRM-11-TRIPS-RT-LH": "COACH_APPROVED",
        "FRM-21-RT": "SOURCE_IMPORTED_NEEDS_COACH_APPROVAL",
        "FRM-11-TREY-LT-ON-LH": "COACH_APPROVED",
        "FRM-12-LT-M": "SOURCE_IMPORTED_NEEDS_COACH_APPROVAL",
    }
    for object_id, status in expected_status.items():
        record = json.loads((directory / f"{object_id}.json").read_text())
        assert record["status"] == status
        assert record["source"]["source_sha256"]
        assert record["validation"]["svg_parsed"] is True


def test_mirror_formation_registry_contains_four_variants():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_inheritance_registry.json").read_text())
    assert registry["status"] == "ACTIVE"
    assert len(registry["relationships"]) == 4


def test_mirrored_coordinate_sets_preserve_y_and_negate_about_axis():
    import json
    pairs = [
        ("DRW-11-TRIPS-RT-LH-001", "DRW-11-TRIPS-LT-RH-001"),
        ("DRW-21-RT-001", "DRW-21-LT-001"),
        ("DRW-LH-11-TREY-LT-ON-001", "DRW-RH-11-TREY-RT-ON-001"),
        ("DRW-M-12-LT-001", "DRW-M-12-RT-001"),
    ]
    for source_id, target_id in pairs:
        source = json.loads((ROOT / "artifacts" / "drawings" / source_id / "coordinates.json").read_text())
        target = json.loads((ROOT / "artifacts" / "drawings" / target_id / "coordinates.json").read_text())
        source_by_label = {p["label"]: p for p in source["players"]}
        target_by_label = {p["label"]: p for p in target["players"]}
        assert source_by_label.keys() == target_by_label.keys()
        for label, p in source_by_label.items():
            q = target_by_label[label]
            assert abs(q["svg_x"] - (1700.0 - p["svg_x"])) < 1e-6
            assert abs(q["svg_y"] - p["svg_y"]) < 1e-6


def test_formation_layer_registry_is_active():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_layer_registry.json").read_text())
    assert registry["status"] == "ACTIVE"
    assert registry["resolution_order"][:5] == [
        "personnel", "formation_family", "direction", "field_location", "variation"
    ]


def test_formation_family_objects_exist_and_have_members():
    import json
    directory = ROOT / "database" / "offense" / "formation_families"
    for family_id in ["FMF-DBLS-001", "FMF-RT-001", "FMF-TRIPS-001", "FMF-TREY-001"]:
        record = json.loads((directory / f"{family_id}.json").read_text())
        assert record["object_type"] == "formation_family"
        assert record["status"] == "ACTIVE"
        assert record["member_object_ids"]


def test_formation_variants_reference_reusable_layers():
    import json
    directory = ROOT / "database" / "offense" / "formation_variants"
    files = list(directory.glob("VAR-*.json"))
    assert len(files) >= 8
    for path in files:
        record = json.loads(path.read_text())
        assert record["formation_family_id"]
        assert "field_location_id" in record
        assert "variation_ids" in record


def test_variation_registry_uses_supplied_playbook_list():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "variation_registry.json").read_text())
    assert registry["terminology"]["canonical_term"] == "variation"
    assert registry["variation_order"] == [
        "ON", "HO", "DON", "OPEN", "WIDE", "HUG", "HAY",
        "HAZE", "HOAX", "SNUG", "FLEX", "SQUEEZE", "HIDE"
    ]


def test_every_variation_has_one_noninvented_object():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "variation_registry.json").read_text())
    for name, item in registry["variations"].items():
        record = json.loads((ROOT / item["file"]).read_text())
        assert record["canonical_name"] == name
        assert record["object_type"] == "formation_variation"
        assert record["geometry"]["status"] == "NOT_INVENTED"


def test_formation_layers_and_variants_use_variation_term():
    import json
    layer = json.loads((ROOT / "database" / "offense" / "formation_layer_registry.json").read_text())
    assert "variation" in layer["resolution_order"]
    assert "modifier" not in layer["resolution_order"]
    for path in (ROOT / "database" / "offense" / "formation_variants").glob("VAR-*.json"):
        record = json.loads(path.read_text())
        assert "variation_ids" in record
        assert "modifier_ids" not in record


def test_parser_uses_variation_terminology():
    system = MarcusSystem(ROOT)
    result = system.parse("(11) RT ON")
    assert result.variation == "ON"
    assert result.resolved_ids["variations"] == "VARIATION-ON-001"


def test_exact_relational_variations_execute_without_invented_coordinates():
    from marcus_cad.variations import apply_variation
    players = [
        {"label": "X", "svg_x": 100, "svg_y": 500, "los_status": "ON"},
        {"label": "H", "svg_x": 300, "svg_y": 520, "los_status": "OFF"},
        {"label": "Y", "svg_x": 1100, "svg_y": 520, "los_status": "OFF"},
        {"label": "Z", "svg_x": 1500, "svg_y": 500, "los_status": "ON"},
    ]
    on = apply_variation(players, "ON")
    assert next(p for p in on if p["label"] == "Y")["los_status"] == "ON"
    ho = apply_variation(players, "HO")
    assert next(p for p in ho if p["label"] == "H")["los_status"] == "ON"
    don = apply_variation(players, "DON")
    assert next(p for p in don if p["label"] == "H")["los_status"] == "ON"
    assert next(p for p in don if p["label"] == "Y")["los_status"] == "ON"
    hay = apply_variation(players, "HAY")
    assert next(p for p in hay if p["label"] == "H")["svg_x"] == 1100
    assert next(p for p in hay if p["label"] == "Y")["svg_x"] == 300


def test_landmark_dependent_variations_remain_blocked():
    import pytest
    from marcus_cad.variations import apply_variation, VariationError
    with pytest.raises(VariationError):
        apply_variation([{"label": "H", "svg_x": 300, "svg_y": 500}], "HUG")


def test_every_variation_has_source_occurrence_metadata():
    import json
    directory = ROOT / "database" / "offense" / "variations"
    names = ["ON","HO","DON","OPEN","WIDE","HUG","HAY","HAZE","HOAX","SNUG","FLEX","SQUEEZE","HIDE"]
    for name in names:
        record = json.loads((directory / f"VARIATION-{name}-001.json").read_text())
        assert "source_occurrences" in record
        assert record["compatibility"]["status"] == "SOURCE_OBSERVED"


def test_variation_source_occurrence_registry_is_active():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "variation_source_occurrence_registry.json").read_text())
    assert registry["status"] == "ACTIVE"
    assert set(registry["variations"]) == {
        "ON","HO","DON","OPEN","WIDE","HUG","HAY","HAZE","HOAX","SNUG","FLEX","SQUEEZE","HIDE"
    }


def test_representative_variation_evidence_files_exist():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "variation_source_occurrence_registry.json").read_text())
    for name, item in registry["variations"].items():
        evidence = item["representative_evidence"]
        if evidence:
            assert (ROOT / evidence).exists()


def test_formation_geometry_registry_is_active():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_geometry_registry.json").read_text())
    assert registry["status"] == "ACTIVE"
    assert registry["summary"]["geometry_object_count"] >= 10


def test_all_geometry_objects_have_coordinates_and_source_hashes():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_geometry_registry.json").read_text())
    for item in registry["geometry_objects"]:
        record = json.loads((ROOT / item["file"]).read_text())
        assert record["source_svg_sha256"]
        assert record["players"]
        assert all("svg_x" in p and "svg_y" in p for p in record["players"])
        assert all(p["radius"] == 19 for p in record["players"])


def test_latest_source_svg_candidates_are_preserved():
    import json
    registry = json.loads((ROOT / "database" / "offense" / "formation_geometry_registry.json").read_text())
    assert registry["summary"]["source_candidate_count"] == 6
    for item in registry["source_candidates"]:
        assert (ROOT / item["file"]).exists()
        assert item["sha256"]


def test_v160_catalog_driven_alias_normalization():
    system = MarcusSystem(ROOT)
    result = system.parse("left hash ( 11 ) doubles right on h orbit vs 4-2 stud cover 4 read")
    assert result.normalized_call == "LH (11) DBLS RT ON H ORBIT VS 4-2 STUD COV 4 READ"
    assert result.field_location == "LH"
    assert result.personnel == "11"
    assert result.variation == "ON"
    assert result.motion == "H ORBIT"


def test_v160_unknown_tokens_are_explicit_blockers():
    result = MarcusSystem(ROOT).parse("(11) DBLS RT BANANA")
    assert result.renderable is False
    assert result.unknown_offense_tokens == ["BANANA"]
    assert {tuple(x.values()) for x in result.blockers} >= {("offense_token:BANANA", "UNKNOWN_TOKEN")}


def test_v160_longest_formation_match_wins():
    result = MarcusSystem(ROOT).parse("(11) DBLS RT")
    assert result.formation == "DBLS RT"
    assert result.unknown_offense_tokens == []
