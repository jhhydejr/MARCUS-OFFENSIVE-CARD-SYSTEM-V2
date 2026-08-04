from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .system import MarcusError, MarcusSystem


@dataclass(frozen=True)
class PipelineStage:
    name: str
    status: str
    detail: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    source_call: str
    normalized_call: str | None
    success: bool
    output_directory: str
    stages: tuple[PipelineStage, ...]
    manifest_path: str | None
    validation_path: str | None
    error: str | None


class PipelineController:
    """Single public controller for call-to-card compilation.

    The controller delegates football resolution and rendering to ``MarcusSystem``.
    It adds one stable entry point, one stage report, and one success/failure result
    without inferring or changing football knowledge.
    """

    STAGE_NAMES = (
        "parse_resolve",
        "coordinate_validation",
        "assignment_binding",
        "play_card_composition",
        "drawing_scene_validation",
        "card_layout_validation",
        "svg_render",
        "png_export",
        "pdf_export",
        "output_integrity",
    )

    def __init__(self, system: MarcusSystem):
        self.system = system

    def compile_play(
        self,
        call: str,
        out_dir: Path,
        *,
        card_type: str = "SCOUT_CARD",
        require_assignments: bool = False,
        raise_on_error: bool = False,
    ) -> PipelineResult:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "pipeline_report.json"
        manifest_path = out_dir / "manifest.json"
        validation_path = out_dir / "validation.json"

        normalized_call: str | None = None
        try:
            parsed = self.system.parse(call, card_type=card_type)
            normalized_call = parsed.normalized_call
            manifest = self.system.draw(
                call,
                out_dir,
                card_type=card_type,
                require_assignments=require_assignments,
            )
            stages = tuple(PipelineStage(name, "PASS") for name in self.STAGE_NAMES)
            result = PipelineResult(
                source_call=call,
                normalized_call=normalized_call,
                success=True,
                output_directory=str(out_dir),
                stages=stages,
                manifest_path=str(manifest_path),
                validation_path=str(validation_path),
                error=None,
            )
            report_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")

            manifest.setdefault("outputs", {})["pipeline_report"] = {
                "path": str(report_path),
                "sha256": self.system.sha256(report_path),
            }
            integrity = self.system.validate_output_integrity(manifest, out_dir)
            if not integrity.valid:
                raise MarcusError(
                    "Pipeline output integrity validation failed: "
                    + json.dumps(asdict(integrity), sort_keys=True)
                )
            integrity_path = out_dir / "output_integrity.json"
            integrity_path.write_text(json.dumps(asdict(integrity), indent=2), encoding="utf-8")
            manifest["output_integrity"] = asdict(integrity)
            manifest["outputs"]["output_integrity"] = {
                "path": str(integrity_path),
                "sha256": self.system.sha256(integrity_path),
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            return result
        except MarcusError as exc:
            stages = (PipelineStage("compile_play", "FAIL", str(exc)),)
            result = PipelineResult(
                source_call=call,
                normalized_call=normalized_call,
                success=False,
                output_directory=str(out_dir),
                stages=stages,
                manifest_path=str(manifest_path) if manifest_path.exists() else None,
                validation_path=str(validation_path) if validation_path.exists() else None,
                error=str(exc),
            )
            report_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
            if raise_on_error:
                raise
            return result
