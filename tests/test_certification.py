from __future__ import annotations

import json
from pathlib import Path

from marcus_cad.certification import CertificationEngine
from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]
TARGET = "LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ"


def test_certification_engine_certifies_known_pipeline(tmp_path):
    report = CertificationEngine(MarcusSystem(ROOT), "2.0.6").run(tmp_path / "cert", [TARGET])
    assert report.status == "CERTIFIED"
    assert all(check.status == "PASS" for check in report.checks)
    assert (tmp_path / "cert" / "certification_report.json").is_file()
    assert (tmp_path / "cert" / "cards" / "01" / "card.pdf").is_file()


def test_certification_report_is_machine_readable(tmp_path):
    out = tmp_path / "cert"
    CertificationEngine(MarcusSystem(ROOT), "2.0.6").run(out, [TARGET])
    payload = json.loads((out / "certification_report.json").read_text())
    assert payload["schema"] == "marcus-cad.certification-report.v1"
    assert payload["release"] == "2.0.6"
    assert payload["status"] == "CERTIFIED"
    assert {check["name"] for check in payload["checks"]} == {
        "database", "database_health", "registry", "drawing_assets", "catalog_resolution", "pipeline", "exports", "output_integrity"
    }


def test_certification_failure_is_reported_without_guessing(tmp_path):
    report = CertificationEngine(MarcusSystem(ROOT), "2.0.6").run(
        tmp_path / "cert", ["(11) UNKNOWN FORMATION"]
    )
    assert report.status == "FAILED"
    pipeline = next(check for check in report.checks if check.name == "pipeline")
    assert pipeline.status == "FAIL"
