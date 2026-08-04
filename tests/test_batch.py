from __future__ import annotations

import json
from pathlib import Path

import pytest

from marcus_cad.batch import BatchCall, compile_batch, load_batch_calls, load_calls
from marcus_cad.system import MarcusError, MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_load_calls_supports_text_and_json(tmp_path):
    txt = tmp_path / "calls.txt"
    txt.write_text(f"{TARGET}\n\n(11) RT ON\n", encoding="utf-8")
    assert load_calls(txt) == [TARGET, "(11) RT ON"]

    js = tmp_path / "calls.json"
    js.write_text(json.dumps({"calls": [TARGET, "(11) RT ON"]}), encoding="utf-8")
    assert load_calls(js) == [TARGET, "(11) RT ON"]


def test_load_calls_rejects_invalid_json_shape(tmp_path):
    path = tmp_path / "calls.json"
    path.write_text('{"calls": [12]}', encoding="utf-8")
    with pytest.raises(MarcusError):
        load_calls(path)


def test_batch_renders_and_isolates_blocked_call(tmp_path):
    system = MarcusSystem(ROOT)
    summary = compile_batch(system, [TARGET, "(11) UNKNOWN FORMATION"], tmp_path / "batch")
    assert summary.total == 2
    assert summary.rendered == 1
    assert summary.blocked == 1
    assert summary.all_rendered is False
    assert summary.items[0].status == "RENDERED"
    assert summary.items[1].status == "BLOCKED"
    assert (tmp_path / "batch" / "batch_summary.json").exists()
    report = json.loads((tmp_path / "batch" / "validation_report.json").read_text())
    assert report["passed"] == 1
    assert report["failed"] == 1
    assert report["failures"][0]["index"] == 2


def test_batch_output_directories_are_deterministic_and_unique(tmp_path):
    system = MarcusSystem(ROOT)
    summary = compile_batch(system, ["(11) RT ON", "(11) RT ON"], tmp_path / "batch")
    names = [item.output_directory for item in summary.items]
    assert names == ["01-11-RT-ON", "02-11-RT-ON"]
    for name in names:
        assert (tmp_path / "batch" / name / "card.svg").exists()
        assert (tmp_path / "batch" / name / "card.png").exists()
        assert (tmp_path / "batch" / name / "card.pdf").exists()
        assert (tmp_path / "batch" / name / "validation.json").exists()


def test_batch_summary_uses_relative_output_paths(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "batch"
    compile_batch(system, [TARGET], out)
    payload = json.loads((out / "batch_summary.json").read_text())
    for record in payload["items"][0]["outputs"].values():
        assert not Path(record["path"]).is_absolute()


def test_batch_uses_pipeline_controller_and_writes_pipeline_reports(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "batch"
    summary = compile_batch(system, [TARGET, "(11) UNKNOWN FORMATION"], out)
    assert summary.schema == "marcus-cad.batch-summary.v2"
    for item in summary.items:
        report = out / item.pipeline_report
        assert report.exists()
        payload = json.loads(report.read_text())
        assert payload["source_call"] == item.source_call
    assert (out / "batch_manifest.json").exists()


def test_batch_manifest_hashes_summary_validation_and_pipeline_reports(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "batch"
    compile_batch(system, [TARGET], out)
    manifest = json.loads((out / "batch_manifest.json").read_text())
    assert manifest["summary"]["sha256"] == system.sha256(out / "batch_summary.json")
    assert manifest["validation"]["sha256"] == system.sha256(out / "validation_report.json")
    item = manifest["items"][0]
    assert item["pipeline_report_sha256"] == system.sha256(out / item["pipeline_report"])


def test_batch_strict_assignment_mode_isolated_and_reported(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "batch"
    summary = compile_batch(system, [TARGET, "(11) RT ON"], out, require_assignments=True)
    assert summary.require_assignments is True
    assert summary.total == 2
    assert summary.blocked == 2
    report = json.loads((out / "validation_report.json").read_text())
    assert report["require_assignments"] is True
    assert len(report["failures"]) == 2


def test_batch_card_type_controls_required_play_slot(tmp_path):
    system = MarcusSystem(ROOT)
    scout_out = tmp_path / "scout"
    scout = compile_batch(system, [TARGET], scout_out, card_type="SCOUT_CARD")
    assert scout.card_type == "SCOUT_CARD"
    assert scout.rendered == 1
    scout_payload = json.loads((scout_out / "batch_summary.json").read_text())
    assert scout_payload["card_type"] == "SCOUT_CARD"

    play_out = tmp_path / "play"
    play = compile_batch(system, [TARGET], play_out, card_type="PLAY_CARD")
    assert play.card_type == "PLAY_CARD"
    assert play.rendered == 0
    assert play.blocked == 1
    assert {"object": "offense_slot:play", "reason": "MISSING_REQUIRED_SLOT"} in play.items[0].blockers
    play_payload = json.loads((play_out / "validation_report.json").read_text())
    assert play_payload["card_type"] == "PLAY_CARD"


def test_batch_manifest_records_card_type(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "batch"
    compile_batch(system, [TARGET], out, card_type="SCOUT_CARD")
    manifest = json.loads((out / "batch_manifest.json").read_text())
    assert manifest["schema"] == "marcus-cad.batch-manifest.v2"
    assert manifest["card_type"] == "SCOUT_CARD"


def test_load_batch_calls_supports_per_call_card_types(tmp_path):
    path = tmp_path / "mixed.json"
    path.write_text(json.dumps({
        "calls": [
            {"call": TARGET, "card_type": "SCOUT_CARD"},
            {"call": TARGET, "card_type": "PLAY_CARD"},
            "(11) RT ON",
        ]
    }), encoding="utf-8")
    calls = load_batch_calls(path)
    assert calls == [
        BatchCall(TARGET, "SCOUT_CARD"),
        BatchCall(TARGET, "PLAY_CARD"),
        BatchCall("(11) RT ON", None),
    ]
    assert load_calls(path) == [TARGET, TARGET, "(11) RT ON"]


def test_mixed_batch_applies_card_type_per_call(tmp_path):
    system = MarcusSystem(ROOT)
    out = tmp_path / "mixed"
    summary = compile_batch(
        system,
        [
            BatchCall(TARGET, "SCOUT_CARD"),
            BatchCall(TARGET, "PLAY_CARD"),
        ],
        out,
        card_type="SCOUT_CARD",
    )
    assert summary.card_type == "MIXED"
    assert summary.rendered == 1
    assert summary.blocked == 1
    assert [item.card_type for item in summary.items] == ["SCOUT_CARD", "PLAY_CARD"]
    assert summary.items[0].status == "RENDERED"
    assert {"object": "offense_slot:play", "reason": "MISSING_REQUIRED_SLOT"} in summary.items[1].blockers

    payload = json.loads((out / "batch_summary.json").read_text())
    assert payload["card_type"] == "MIXED"
    assert payload["items"][0]["card_type"] == "SCOUT_CARD"
    assert payload["items"][1]["card_type"] == "PLAY_CARD"

    manifest = json.loads((out / "batch_manifest.json").read_text())
    assert manifest["card_type"] == "MIXED"
    assert manifest["default_card_type"] == "SCOUT_CARD"
    assert [item["card_type"] for item in manifest["items"]] == ["SCOUT_CARD", "PLAY_CARD"]


def test_load_batch_calls_rejects_unknown_record_fields(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"calls": [{"call": TARGET, "type": "SCOUT_CARD"}]}), encoding="utf-8")
    with pytest.raises(MarcusError, match="unsupported fields"):
        load_batch_calls(path)
