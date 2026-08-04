from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class DatabaseIndexError(ValueError):
    """Raised when stored football database objects cannot be indexed safely."""


@dataclass(frozen=True)
class DatabaseObjectSource:
    object_id: str
    file: str
    id_field: str
    canonical_name: str | None
    status: str | None
    category: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "object_id": self.object_id,
            "file": self.file,
            "id_field": self.id_field,
            "canonical_name": self.canonical_name,
            "status": self.status,
            "category": self.category,
        }


@dataclass(frozen=True)
class CatalogSourceLink:
    category: str
    key: str
    object_id: str
    source_kind: str
    source_file: str | None
    source_status: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "category": self.category,
            "key": self.key,
            "object_id": self.object_id,
            "source_kind": self.source_kind,
            "source_file": self.source_file,
            "source_status": self.source_status,
        }


class DatabaseObjectIndex:
    """Index top-level canonical IDs stored in the football database.

    The index records existing data only. It does not infer aliases, create IDs,
    or promote approval status. Registry documents are scanned for references but
    object definition files are preferred when resolving an ID.
    """

    ID_FIELDS = (
        "object_id",
        "formation_id",
        "motion_id",
        "personnel_id",
        "coverage_id",
        "structure_id",
        "drawing_id",
        "geometry_id",
        "variation_id",
    )

    FILE_FIELDS = ("file", "formation_file", "motion_file")

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.database_root = self.root / "database"
        self._by_id: dict[str, list[DatabaseObjectSource]] = {}
        self._scan()

    @staticmethod
    def _category(path: Path) -> str:
        parts = path.parts
        if "defense" in parts:
            return "defense"
        if "offense" in parts:
            if "assignments" in parts:
                return "assignments"
            if "formations" in parts or path.name.startswith("FRM-"):
                return "formations"
            if "formation_geometry" in parts:
                return "formation_geometry"
            if "formation_variants" in parts:
                return "formation_variants"
            if "variations" in parts:
                return "variations"
            if "field_locations" in parts:
                return "field_locations"
            return "offense"
        if "renderer" in parts:
            return "renderer"
        return "database"

    @staticmethod
    def _is_definition(path: Path, field: str) -> bool:
        name = path.name.lower()
        if "registry" in name or path.name == "catalog.json":
            return False
        if field == "object_id":
            return True
        if field == "formation_id" and (path.name.startswith("FRM-") or "formations" in path.parts):
            return True
        return False

    def _scan(self) -> None:
        if not self.database_root.is_dir():
            raise DatabaseIndexError(f"Missing database directory: {self.database_root}")
        for path in sorted(self.database_root.rglob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise DatabaseIndexError(f"Cannot index JSON file {path}: {exc}") from exc
            if not isinstance(record, dict):
                continue
            relative = str(path.relative_to(self.root))
            for field in self.ID_FIELDS:
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                source = DatabaseObjectSource(
                    object_id=value.strip(),
                    file=relative,
                    id_field=field,
                    canonical_name=record.get("canonical_name") if isinstance(record.get("canonical_name"), str) else None,
                    status=record.get("status") if isinstance(record.get("status"), str) else None,
                    category=self._category(path),
                )
                self._by_id.setdefault(source.object_id, []).append(source)

    def occurrences(self, object_id: str) -> tuple[DatabaseObjectSource, ...]:
        return tuple(self._by_id.get(object_id, ()))

    def resolve(self, object_id: str, preferred_file: str | None = None) -> DatabaseObjectSource | None:
        items = list(self._by_id.get(object_id, ()))
        if preferred_file:
            preferred = [item for item in items if item.file == preferred_file]
            if preferred:
                return sorted(preferred, key=lambda item: (item.id_field != "object_id", item.file))[0]
        definitions = [
            item for item in items
            if self._is_definition(self.root / item.file, item.id_field)
        ]
        candidates = definitions or items
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item.id_field != "object_id", len(item.file), item.file))[0]

    @staticmethod
    def _preferred_file(record: dict[str, Any]) -> str | None:
        for field in DatabaseObjectIndex.FILE_FIELDS:
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def link_catalog(self, catalog: dict[str, Any]) -> tuple[CatalogSourceLink, ...]:
        objects = catalog.get("objects", {})
        if not isinstance(objects, dict):
            raise DatabaseIndexError("catalog.objects must be an object")
        links: list[CatalogSourceLink] = []
        for category, records in objects.items():
            if not isinstance(records, dict):
                continue
            for key, record in records.items():
                if not isinstance(record, dict):
                    continue
                object_id = record.get("id")
                if not isinstance(object_id, str) or not object_id.strip():
                    continue
                source = self.resolve(object_id, self._preferred_file(record))
                links.append(CatalogSourceLink(
                    category=str(category),
                    key=str(key),
                    object_id=object_id,
                    source_kind="DATABASE_FILE" if source else "CATALOG_INLINE",
                    source_file=source.file if source else None,
                    source_status=source.status if source else str(record.get("status", "UNDEFINED")),
                ))
        return tuple(sorted(links, key=lambda item: (item.category, item.key, item.object_id)))

    def report(self, catalog: dict[str, Any]) -> dict[str, Any]:
        links = self.link_catalog(catalog)
        database_links = [item for item in links if item.source_kind == "DATABASE_FILE"]
        inline_links = [item for item in links if item.source_kind == "CATALOG_INLINE"]
        return {
            "valid": True,
            "indexed_object_ids": len(self._by_id),
            "catalog_object_count": len(links),
            "database_file_links": len(database_links),
            "catalog_inline_links": len(inline_links),
            "links": [item.to_dict() for item in links],
        }


    def validate_resolution(
        self,
        resolved_ids: dict[str, str],
        resolved_sources: dict[str, str],
    ) -> dict[str, Any]:
        """Validate that resolved object IDs are backed by the recorded source files.

        This performs structural integrity checks only. It never changes football
        status, creates aliases, or infers missing knowledge.
        """
        categories = sorted(set(resolved_ids) | set(resolved_sources))
        missing_source_categories: list[str] = []
        missing_files: list[str] = []
        invalid_json_files: list[str] = []
        id_mismatches: list[str] = []
        paths_outside_project: list[str] = []
        checked_sources: list[dict[str, str]] = []

        catalog_path = self.root / "database/master/catalog.json"
        catalog_ids: set[str] = set()
        try:
            catalog_record = json.loads(catalog_path.read_text(encoding="utf-8"))
            objects = catalog_record.get("objects", {}) if isinstance(catalog_record, dict) else {}
            if isinstance(objects, dict):
                for records in objects.values():
                    if isinstance(records, dict):
                        for record in records.values():
                            if isinstance(record, dict):
                                value = record.get("id")
                                if isinstance(value, str):
                                    catalog_ids.add(value)
        except (OSError, json.JSONDecodeError):
            catalog_ids = set()

        for category in categories:
            object_id = resolved_ids.get(category)
            source_file = resolved_sources.get(category)
            if not object_id or not source_file:
                missing_source_categories.append(category)
                continue

            source_path = (self.root / source_file).resolve()
            try:
                source_path.relative_to(self.root)
            except ValueError:
                paths_outside_project.append(category)
                continue

            if not source_path.is_file():
                missing_files.append(source_file)
                continue

            try:
                record = json.loads(source_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                invalid_json_files.append(source_file)
                continue

            matches = False
            if source_path == catalog_path.resolve():
                matches = object_id in catalog_ids
            elif isinstance(record, dict):
                matches = any(record.get(field) == object_id for field in self.ID_FIELDS)

            if not matches:
                id_mismatches.append(category)
                continue

            checked_sources.append({
                "category": category,
                "object_id": object_id,
                "source_file": source_file,
            })

        valid = not (
            missing_source_categories
            or missing_files
            or invalid_json_files
            or id_mismatches
            or paths_outside_project
        )
        return {
            "valid": valid,
            "checked_source_count": len(checked_sources),
            "checked_sources": checked_sources,
            "missing_source_categories": missing_source_categories,
            "missing_files": sorted(set(missing_files)),
            "invalid_json_files": sorted(set(invalid_json_files)),
            "id_mismatches": id_mismatches,
            "paths_outside_project": paths_outside_project,
        }

    def all_sources(self) -> Iterable[DatabaseObjectSource]:
        for object_id in sorted(self._by_id):
            yield from sorted(self._by_id[object_id], key=lambda item: (item.file, item.id_field))
