from __future__ import annotations

import json
from pathlib import Path

import pytest

from marcus_cad.resolver import ObjectRegistry, RegistryError
from marcus_cad.system import MarcusSystem

ROOT = Path(__file__).resolve().parents[1]


def load_catalog():
    return json.loads((ROOT / "database" / "master" / "catalog.json").read_text())


def test_registry_builds_from_authoritative_catalog():
    registry = ObjectRegistry(load_catalog())
    report = registry.validate()
    assert report["valid"] is True
    assert report["object_count"] == sum(
        len(records) for records in load_catalog()["objects"].values()
    )
    assert "formations" in report["categories"]


def test_registry_resolves_canonical_key_to_typed_object():
    registry = ObjectRegistry(load_catalog())
    obj = registry.require("formations", "RT")
    assert obj.object_id == "FM-RT-001"
    assert obj.category == "formations"
    assert obj.record["resolved_variants"]["11|ON"]["id"] == "FRM-11-RT-ON"


def test_registry_reverse_lookup_by_id():
    registry = ObjectRegistry(load_catalog())
    obj = registry.by_id("MOT-H-ORBIT")
    assert obj is not None
    assert obj.key == "H ORBIT"
    assert obj.category == "motions"


def test_registry_rejects_duplicate_canonical_ids():
    catalog = {
        "objects": {
            "formations": {
                "A": {"id": "DUP", "status": "CANONICAL"},
                "B": {"id": "DUP", "status": "CANONICAL"},
            }
        }
    }
    with pytest.raises(RegistryError, match="duplicate canonical id"):
        ObjectRegistry(catalog)


def test_registry_rejects_alias_conflicts():
    catalog = {
        "objects": {
            "formations": {
                "A": {"id": "A", "status": "CANONICAL", "aliases": ["X"]},
                "B": {"id": "B", "status": "CANONICAL", "aliases": ["X"]},
            }
        }
    }
    with pytest.raises(RegistryError, match="alias conflict"):
        ObjectRegistry(catalog)


def test_system_resolution_uses_registry_objects():
    system = MarcusSystem(ROOT)
    result = system.parse("LH (11) RT ON H ORBIT VS 4-2 STUD COV 4 READ")
    assert result.blockers == []
    assert result.resolved_ids == {
        "backfields": "BF-GUN-001",
        "field_locations": "LOC-LH",
        "personnel": "PER-11",
        "formations": "FM-RT-001",
        "variations": "VARIATION-ON-001",
        "motions": "MOT-H-ORBIT",
        "defensive_personnel": "DEF-PER-4-2",
        "defensive_structures": "DEF-STRUCT-STUD",
        "coverages": "COV-4-READ",
    }
