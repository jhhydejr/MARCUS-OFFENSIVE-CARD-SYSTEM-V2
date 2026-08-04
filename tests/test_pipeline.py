import json
from pathlib import Path

from marcus_cad.pipeline import PipelineController
from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_pipeline_compiles_target_call_end_to_end(tmp_path):
    result = PipelineController(MarcusSystem(ROOT)).compile_play(TARGET, tmp_path / "card")
    assert result.success is True
    assert [stage.status for stage in result.stages] == ["PASS"] * 10
    for name in ["card.svg", "card.png", "card.pdf", "validation.json", "manifest.json", "pipeline_report.json"]:
        assert (tmp_path / "card" / name).is_file()


def test_pipeline_report_is_hashed_in_manifest(tmp_path):
    out = tmp_path / "card"
    result = PipelineController(MarcusSystem(ROOT)).compile_play(TARGET, out)
    assert result.success
    manifest = json.loads((out / "manifest.json").read_text())
    assert "pipeline_report" in manifest["outputs"]
    assert manifest["output_integrity"]["valid"] is True
    assert "pipeline_report" in manifest["output_integrity"]["checked_outputs"]


def test_pipeline_returns_structured_failure_without_guessing(tmp_path):
    result = PipelineController(MarcusSystem(ROOT)).compile_play(
        "(11) UNKNOWN FORMATION", tmp_path / "blocked"
    )
    assert result.success is False
    assert result.error
    report = json.loads((tmp_path / "blocked" / "pipeline_report.json").read_text())
    assert report["success"] is False
    assert report["stages"][0]["status"] == "FAIL"
