from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DatabaseHealthReport:
    schema: str
    valid: bool
    json_file_count: int
    canonical_object_count: int
    reference_count: int
    duplicate_definition_count: int
    broken_reference_count: int
    orphaned_object_count: int
    circular_reference_count: int
    parse_errors: tuple[dict[str, str], ...]
    duplicate_definitions: tuple[dict[str, Any], ...]
    broken_references: tuple[dict[str, str], ...]
    orphaned_objects: tuple[dict[str, str], ...]
    circular_references: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DatabaseHealthEngine:
    """Audit stored football knowledge without inventing or changing it.

    Only explicit stored identifier fields are considered. Orphaned objects are
    reported for review but do not make the database invalid because some
    approved objects may intentionally be staged before use.
    """

    DEFINITION_FIELDS = (
        "object_id",
        "formation_id",
        "motion_id",
        "personnel_id",
        "coverage_id",
        "structure_id",
        "drawing_id",
        "geometry_id",
        "variation_id",
        "registry_id",
    )

    REFERENCE_FIELDS = {
        "member_object_id",
        "member_object_ids",
        "mirror_of_object_id",
        "formation_object_id",
        "source_object_id",
        "parent_object_id",
        "depends_on_object_id",
        "dependency_object_ids",
    }

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.database_root = self.root / "database"

    @staticmethod
    def _is_definition_file(path: Path, field: str) -> bool:
        lowered = path.name.lower()
        if "registry" in lowered or path.name == "catalog.json":
            return False
        if field == "object_id":
            return True
        if field == "formation_id":
            return path.name.startswith("FRM-") or "formations" in path.parts
        if field == "motion_id":
            return path.name.startswith("MOT-")
        if field in {"personnel_id", "coverage_id", "structure_id", "variation_id"}:
            return True
        return False

    @staticmethod
    def _values(value: Any) -> Iterable[str]:
        if isinstance(value, str) and value.strip():
            yield value.strip()
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    yield item.strip()

    def _walk_references(
        self,
        value: Any,
        source_id: str | None,
        source_file: str,
        path: str = "$",
    ) -> Iterable[dict[str, str]]:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in self.REFERENCE_FIELDS:
                    for target in self._values(child):
                        yield {
                            "source_id": source_id or "",
                            "target_id": target,
                            "field": key,
                            "file": source_file,
                            "path": child_path,
                        }
                yield from self._walk_references(child, source_id, source_file, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from self._walk_references(child, source_id, source_file, f"{path}[{index}]")

    @staticmethod
    def _find_cycles(graph: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
        cycles: set[tuple[str, ...]] = set()
        active: list[str] = []
        active_set: set[str] = set()
        complete: set[str] = set()

        def canonicalize(nodes: list[str]) -> tuple[str, ...]:
            ring = nodes[:-1]
            rotations = [tuple(ring[i:] + ring[:i]) for i in range(len(ring))]
            smallest = min(rotations)
            return smallest + (smallest[0],)

        def visit(node: str) -> None:
            if node in complete:
                return
            active.append(node)
            active_set.add(node)
            for target in sorted(graph.get(node, ())):
                if target in active_set:
                    index = active.index(target)
                    cycles.add(canonicalize(active[index:] + [target]))
                elif target not in complete:
                    visit(target)
            active.pop()
            active_set.remove(node)
            complete.add(node)

        for node in sorted(graph):
            visit(node)
        return tuple(sorted(cycles))

    def audit(self) -> DatabaseHealthReport:
        if not self.database_root.is_dir():
            raise FileNotFoundError(f"Missing database directory: {self.database_root}")

        json_files = sorted(self.database_root.rglob("*.json"))
        parse_errors: list[dict[str, str]] = []
        records: list[tuple[Path, dict[str, Any]]] = []
        definitions: dict[str, list[dict[str, str]]] = {}
        all_identifiers: set[str] = set()

        for file_path in json_files:
            relative = str(file_path.relative_to(self.root))
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                parse_errors.append({"file": relative, "error": str(exc)})
                continue
            if not isinstance(payload, dict):
                continue
            records.append((file_path, payload))
            for field in self.DEFINITION_FIELDS:
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                identifier = value.strip()
                all_identifiers.add(identifier)
                if self._is_definition_file(file_path, field):
                    definitions.setdefault(identifier, []).append({
                        "file": relative,
                        "field": field,
                    })

        # Catalog IDs are legitimate stored targets even when defined inline.
        catalog_path = self.database_root / "master" / "catalog.json"
        if catalog_path.is_file():
            try:
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                objects = catalog.get("objects", {}) if isinstance(catalog, dict) else {}
                if isinstance(objects, dict):
                    for category_records in objects.values():
                        if isinstance(category_records, dict):
                            for record in category_records.values():
                                if isinstance(record, dict) and isinstance(record.get("id"), str):
                                    all_identifiers.add(record["id"].strip())
            except (OSError, json.JSONDecodeError):
                pass

        references: list[dict[str, str]] = []
        for file_path, payload in records:
            relative = str(file_path.relative_to(self.root))
            source_id = next(
                (
                    payload.get(field).strip()
                    for field in self.DEFINITION_FIELDS
                    if isinstance(payload.get(field), str) and payload.get(field).strip()
                ),
                None,
            )
            references.extend(self._walk_references(payload, source_id, relative))

        duplicates = tuple(
            {
                "object_id": object_id,
                "definitions": sorted(items, key=lambda item: (item["file"], item["field"])),
            }
            for object_id, items in sorted(definitions.items())
            if len(items) > 1
        )

        broken = tuple(
            reference
            for reference in sorted(
                references,
                key=lambda item: (item["file"], item["path"], item["target_id"]),
            )
            if reference["target_id"] not in all_identifiers
        )

        incoming = {reference["target_id"] for reference in references}
        catalog_ids = set()
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            objects = catalog.get("objects", {}) if isinstance(catalog, dict) else {}
            if isinstance(objects, dict):
                for category_records in objects.values():
                    if isinstance(category_records, dict):
                        for record in category_records.values():
                            if isinstance(record, dict) and isinstance(record.get("id"), str):
                                catalog_ids.add(record["id"].strip())
        except (OSError, json.JSONDecodeError):
            pass

        orphaned = tuple(
            {
                "object_id": object_id,
                "file": items[0]["file"],
                "field": items[0]["field"],
            }
            for object_id, items in sorted(definitions.items())
            if object_id not in incoming and object_id not in catalog_ids
        )

        graph: dict[str, set[str]] = {}
        canonical_ids = set(definitions)
        for reference in references:
            source = reference["source_id"]
            target = reference["target_id"]
            if source in canonical_ids and target in canonical_ids:
                graph.setdefault(source, set()).add(target)
        cycles = self._find_cycles(graph)

        valid = not (parse_errors or duplicates or broken or cycles)
        return DatabaseHealthReport(
            schema="marcus-cad.database-health.v1",
            valid=valid,
            json_file_count=len(json_files),
            canonical_object_count=len(definitions),
            reference_count=len(references),
            duplicate_definition_count=len(duplicates),
            broken_reference_count=len(broken),
            orphaned_object_count=len(orphaned),
            circular_reference_count=len(cycles),
            parse_errors=tuple(parse_errors),
            duplicate_definitions=duplicates,
            broken_references=broken,
            orphaned_objects=orphaned,
            circular_references=cycles,
        )

    def write_report(self, output_path: Path) -> DatabaseHealthReport:
        report = self.audit()
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report
