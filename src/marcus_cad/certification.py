from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .database_health import DatabaseHealthEngine
from .pipeline import PipelineController
from .system import MarcusSystem


@dataclass(frozen=True)
class CertificationCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class CertificationReport:
    schema: str
    release: str
    status: str
    checks: tuple[CertificationCheck, ...]
    tested_calls: tuple[str, ...]
    output_directory: str


class CertificationEngine:
    """Run repeatable release checks without adding football knowledge."""

    def __init__(self, system: MarcusSystem, release: str):
        self.system = system
        self.release = release

    def _database_check(self) -> CertificationCheck:
        files = sorted(self.system.root.rglob("*.json"))
        errors: list[str] = []
        for path in files:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{path.relative_to(self.system.root)}: {exc}")
        if errors:
            return CertificationCheck("database", "FAIL", "; ".join(errors))
        return CertificationCheck("database", "PASS", f"{len(files)} JSON files parsed")

    def _database_health_check(self, out_dir: Path) -> CertificationCheck:
        report = DatabaseHealthEngine(self.system.root).write_report(
            out_dir / "database_health.json"
        )
        if not report.valid:
            return CertificationCheck(
                "database_health",
                "FAIL",
                (
                    f"{report.duplicate_definition_count} duplicate definitions; "
                    f"{report.broken_reference_count} broken references; "
                    f"{report.circular_reference_count} circular references"
                ),
            )
        return CertificationCheck(
            "database_health",
            "PASS",
            (
                f"{report.canonical_object_count} canonical objects; "
                f"{report.reference_count} explicit references; "
                f"{report.orphaned_object_count} staged/orphaned objects reported"
            ),
        )

    def _registry_check(self) -> CertificationCheck:
        categories = self.system.catalog.get("objects", {})
        object_count = sum(len(records) for records in categories.values() if isinstance(records, dict))
        return CertificationCheck(
            "registry",
            "PASS",
            f"{object_count} catalog records and {len(self.system.assignment_registry)} assignment objects loaded",
        )


    def _drawing_asset_check(self, out_dir: Path) -> CertificationCheck:
        inventory = self.system.audit_drawing_assets()
        report_path = out_dir / "drawing_asset_inventory.json"
        report_path.write_text(json.dumps(asdict(inventory), indent=2), encoding="utf-8")
        approved_incomplete = [
            entry.drawing_id
            for entry in inventory.entries
            if entry.approved and not entry.reusable
        ]
        if approved_incomplete:
            return CertificationCheck(
                "drawing_assets",
                "FAIL",
                "Approved drawings with incomplete asset bundles: "
                + ", ".join(approved_incomplete),
            )
        return CertificationCheck(
            "drawing_assets",
            "PASS",
            (
                f"{inventory.approved_reusable_count}/{inventory.approved_count} "
                f"approved drawings reusable; "
                f"{inventory.incomplete_count} non-certified drawings remain incomplete"
            ),
        )

    @staticmethod
    def _read_calls(path: Path) -> list[str]:
        if not path.exists():
            return []
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def default_calls(self) -> list[str]:
        # Full release certification uses calls with approved complete drawing geometry.
        # Other catalog examples are checked separately for parse/resolve stability.
        return self._read_calls(self.system.root / "examples" / "target_call.txt")

    def _catalog_resolution_check(self) -> CertificationCheck:
        calls = self._read_calls(self.system.root / "examples" / "known_calls.txt")
        failures: list[str] = []
        for index, call in enumerate(calls, start=1):
            resolution = self.system.parse(call)
            if resolution.blockers:
                failures.append(f"{index}: {call}: {resolution.blockers}")
        return CertificationCheck(
            "catalog_resolution",
            "FAIL" if failures else "PASS",
            "; ".join(failures) if failures else f"{len(calls)} catalog calls parsed and resolved",
        )

    def run(self, out_dir: Path, calls: Iterable[str] | None = None) -> CertificationReport:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        selected_calls = list(calls) if calls is not None else self.default_calls()
        checks: list[CertificationCheck] = [
            self._database_check(),
            self._database_health_check(out_dir),
            self._registry_check(),
            self._drawing_asset_check(out_dir),
            self._catalog_resolution_check(),
        ]

        pipeline_failures: list[str] = []
        export_failures: list[str] = []
        integrity_failures: list[str] = []
        controller = PipelineController(self.system)
        for index, call in enumerate(selected_calls, start=1):
            card_dir = out_dir / "cards" / f"{index:02d}"
            result = controller.compile_play(call, card_dir)
            if not result.success:
                pipeline_failures.append(f"{index}: {call}: {result.error}")
                continue
            for filename in ("card.svg", "card.png", "card.pdf"):
                path = card_dir / filename
                if not path.is_file() or path.stat().st_size == 0:
                    export_failures.append(f"{index}: {filename}")
            manifest_path = card_dir / "manifest.json"
            if not manifest_path.exists():
                integrity_failures.append(f"{index}: manifest missing")
            else:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                validation = self.system.validate_output_integrity(manifest, card_dir)
                if not validation.valid:
                    integrity_failures.append(f"{index}: output integrity failed")

        checks.append(CertificationCheck(
            "pipeline",
            "FAIL" if pipeline_failures else "PASS",
            "; ".join(pipeline_failures) if pipeline_failures else f"{len(selected_calls)} calls compiled",
        ))
        checks.append(CertificationCheck(
            "exports",
            "FAIL" if export_failures else "PASS",
            "; ".join(export_failures) if export_failures else "SVG, PNG, and PDF exports verified",
        ))
        checks.append(CertificationCheck(
            "output_integrity",
            "FAIL" if integrity_failures else "PASS",
            "; ".join(integrity_failures) if integrity_failures else "All generated output manifests verified",
        ))

        status = "CERTIFIED" if all(check.status == "PASS" for check in checks) else "FAILED"
        report = CertificationReport(
            schema="marcus-cad.certification-report.v1",
            release=self.release,
            status=status,
            checks=tuple(checks),
            tested_calls=tuple(selected_calls),
            output_directory=str(out_dir),
        )
        report_path = out_dir / "certification_report.json"
        report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        return report
