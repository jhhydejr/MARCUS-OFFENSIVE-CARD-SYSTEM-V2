from __future__ import annotations

import json
from pathlib import Path

from marcus_cad.certification import CertificationEngine
from marcus_cad.system import MarcusSystem


ROOT = Path(__file__).resolve().parents[1]


def test_asset_inventory_classifies_all_catalog_drawings() -> None:
    system = MarcusSystem(ROOT)
    inventory = system.audit_drawing_assets()
    assert inventory.schema == "marcus-cad.drawing-asset-inventory.v1"
    assert inventory.drawing_count == len(system.catalog["drawings"])
    assert inventory.approved_count >= 1
    assert inventory.approved_reusable_count == inventory.approved_count
    assert inventory.approved_incomplete_count == 0
    assert any(not entry.approved for entry in inventory.entries)


def test_asset_inventory_preserves_incomplete_unapproved_drawings() -> None:
    system = MarcusSystem(ROOT)
    inventory = system.audit_drawing_assets()
    incomplete = [entry for entry in inventory.entries if not entry.reusable]
    assert all(not entry.approved for entry in incomplete)
    assert all(entry.missing_files or entry.invalid_paths for entry in incomplete)


def test_certification_writes_asset_inventory_report(tmp_path: Path) -> None:
    system = MarcusSystem(ROOT)
    report = CertificationEngine(system, "test").run(tmp_path)
    asset_check = next(check for check in report.checks if check.name == "drawing_assets")
    assert asset_check.status == "PASS"
    payload = json.loads((tmp_path / "drawing_asset_inventory.json").read_text(encoding="utf-8"))
    assert payload["approved_incomplete_count"] == 0
    assert payload["drawing_count"] == len(system.catalog["drawings"])
