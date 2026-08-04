from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .pipeline import PipelineController
from .system import MarcusError, MarcusSystem


@dataclass(frozen=True)
class BatchCall:
    """One batch request.

    ``card_type`` is optional so TXT files and legacy JSON string arrays continue
    to inherit the batch default. JSON object records may override it per call.
    """

    call: str
    card_type: str | None = None


@dataclass(frozen=True)
class BatchItem:
    index: int
    source_call: str
    normalized_call: str
    card_type: str
    output_directory: str
    status: str
    renderable: bool
    drawing_id: str | None
    blockers: list[dict[str, str]]
    outputs: dict[str, Any] | None
    pipeline_report: str


@dataclass(frozen=True)
class BatchSummary:
    schema: str
    total: int
    rendered: int
    blocked: int
    all_rendered: bool
    card_type: str
    require_assignments: bool
    items: list[BatchItem]


def _load_json_batch_item(item: object, index: int) -> BatchCall:
    if isinstance(item, str):
        value = item.strip()
        if not value:
            raise MarcusError(f"Batch JSON call {index} must not be empty.")
        return BatchCall(value)

    if not isinstance(item, dict):
        raise MarcusError(
            f'Batch JSON call {index} must be a string or an object with "call" and optional "card_type".'
        )
    unknown = set(item) - {"call", "card_type"}
    if unknown:
        raise MarcusError(
            f"Batch JSON call {index} contains unsupported fields: {', '.join(sorted(unknown))}."
        )
    call = item.get("call")
    card_type = item.get("card_type")
    if not isinstance(call, str) or not call.strip():
        raise MarcusError(f'Batch JSON call {index} requires a non-empty string "call".')
    if card_type is not None and not isinstance(card_type, str):
        raise MarcusError(f'Batch JSON call {index} "card_type" must be a string.')
    return BatchCall(call.strip(), card_type.strip() if isinstance(card_type, str) else None)


def load_batch_calls(path: Path) -> list[BatchCall]:
    """Load batch requests.

    TXT inputs contain one call per non-comment line and inherit the CLI/default
    card type. JSON inputs accept legacy string arrays plus object records:

    ``{"call": "...", "card_type": "SCOUT_CARD"}``
    """
    if not path.exists():
        raise MarcusError(f"Batch input does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MarcusError(f"Invalid batch JSON: {exc}") from exc
        if isinstance(payload, dict):
            payload = payload.get("calls")
        if not isinstance(payload, list):
            raise MarcusError('Batch JSON must be an array or an object with a "calls" array.')
        calls = [_load_json_batch_item(item, index) for index, item in enumerate(payload, start=1)]
    else:
        calls = [
            BatchCall(value)
            for line in path.read_text(encoding="utf-8").splitlines()
            if (value := line.strip()) and not value.startswith("#")
        ]

    if not calls:
        raise MarcusError("Batch input contains no non-empty play calls.")
    return calls


def load_calls(path: Path) -> list[str]:
    """Backward-compatible loader returning only call strings."""
    return [item.call for item in load_batch_calls(path)]


def _slug(normalized_call: str, max_length: int = 72) -> str:
    value = re.sub(r"[^A-Z0-9]+", "-", normalized_call.upper()).strip("-")
    return (value or "CALL")[:max_length].rstrip("-")


def _relative_outputs(manifest: dict[str, Any] | None, out_root: Path) -> dict[str, Any] | None:
    if not manifest:
        return None
    outputs: dict[str, Any] = {}
    for key, value in manifest.get("outputs", {}).items():
        item = dict(value)
        if "path" in item:
            item["path"] = str(Path(item["path"]).resolve().relative_to(out_root.resolve()))
        outputs[key] = item
    return outputs


def _normalize_request(item: str | BatchCall, index: int) -> BatchCall:
    if isinstance(item, BatchCall):
        request = item
    elif isinstance(item, str):
        request = BatchCall(item)
    else:
        raise MarcusError(f"Batch call {index} must be a string or BatchCall.")
    if not request.call.strip():
        raise MarcusError(f"Batch call {index} must be a non-empty string.")
    return BatchCall(request.call.strip(), request.card_type)


def compile_batch(
    system: MarcusSystem,
    calls: Sequence[str | BatchCall] | Iterable[str | BatchCall],
    out_root: Path,
    *,
    card_type: str = "SCOUT_CARD",
    require_assignments: bool = False,
) -> BatchSummary:
    """Compile every call through the same end-to-end pipeline.

    The ``card_type`` argument is the batch default. A JSON/object ``BatchCall``
    may override it for one item, allowing scout cards and play cards in the
    same batch without weakening either card type's required-slot rules.
    """
    requests = [_normalize_request(item, index) for index, item in enumerate(calls, start=1)]
    default_card_type = system.normalize_card_type(card_type)
    if not requests:
        raise MarcusError("Batch contains no play calls.")

    out_root = out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    items: list[BatchItem] = []
    controller = PipelineController(system)

    for index, request in enumerate(requests, start=1):
        item_card_type = system.normalize_card_type(request.card_type or default_card_type)
        call = request.call
        resolution = system.parse(call, card_type=item_card_type)
        item_name = f"{index:02d}-{_slug(resolution.normalized_call)}"
        item_dir = out_root / item_name
        item_dir.mkdir(parents=True, exist_ok=True)

        result = controller.compile_play(
            call,
            item_dir,
            card_type=item_card_type,
            require_assignments=require_assignments,
        )
        manifest_path = item_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
        status = "RENDERED" if result.success else "BLOCKED"
        blockers = list(resolution.blockers)
        if result.error and not blockers:
            blockers.append({"object": "pipeline", "reason": result.error})

        items.append(BatchItem(
            index=index,
            source_call=call,
            normalized_call=resolution.normalized_call,
            card_type=item_card_type,
            output_directory=item_name,
            status=status,
            renderable=result.success,
            drawing_id=resolution.drawing_id,
            blockers=blockers,
            outputs=_relative_outputs(manifest, out_root),
            pipeline_report=str(Path(item_name) / "pipeline_report.json"),
        ))

    rendered = sum(item.status == "RENDERED" for item in items)
    item_card_types = {item.card_type for item in items}
    summary_card_type = next(iter(item_card_types)) if len(item_card_types) == 1 else "MIXED"
    summary = BatchSummary(
        schema="marcus-cad.batch-summary.v2",
        total=len(items),
        rendered=rendered,
        blocked=len(items) - rendered,
        all_rendered=rendered == len(items),
        card_type=summary_card_type,
        require_assignments=require_assignments,
        items=items,
    )
    payload = asdict(summary)
    summary_path = out_root / "batch_summary.json"
    validation_path = out_root / "validation_report.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    validation_path.write_text(json.dumps({
        "schema": "marcus-cad.validation-report.v2",
        "total": summary.total,
        "passed": summary.rendered,
        "failed": summary.blocked,
        "card_type": summary.card_type,
        "default_card_type": default_card_type,
        "require_assignments": require_assignments,
        "failures": [
            {
                "index": item.index,
                "call": item.source_call,
                "card_type": item.card_type,
                "output_directory": item.output_directory,
                "pipeline_report": item.pipeline_report,
                "blockers": item.blockers,
            }
            for item in items if item.status == "BLOCKED"
        ],
    }, indent=2), encoding="utf-8")

    batch_manifest = {
        "schema": "marcus-cad.batch-manifest.v2",
        "card_type": summary.card_type,
        "default_card_type": default_card_type,
        "summary": {"path": "batch_summary.json", "sha256": system.sha256(summary_path)},
        "validation": {"path": "validation_report.json", "sha256": system.sha256(validation_path)},
        "items": [
            {
                "index": item.index,
                "card_type": item.card_type,
                "status": item.status,
                "output_directory": item.output_directory,
                "pipeline_report": item.pipeline_report,
                "pipeline_report_sha256": system.sha256(out_root / item.pipeline_report),
            }
            for item in items
        ],
    }
    (out_root / "batch_manifest.json").write_text(json.dumps(batch_manifest, indent=2), encoding="utf-8")
    return summary
