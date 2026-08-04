from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


class RegistryError(ValueError):
    """Raised when the canonical object registry is internally inconsistent."""


@dataclass(frozen=True)
class CanonicalObject:
    category: str
    key: str
    object_id: str
    status: str
    record: dict[str, Any]

    def to_reference(self) -> dict[str, str]:
        return {
            "category": self.category,
            "key": self.key,
            "id": self.object_id,
            "status": self.status,
        }


class ObjectRegistry:
    """In-memory canonical index built once from database/master/catalog.json.

    The registry never invents aliases. It indexes only canonical catalog keys and
    aliases explicitly stored on catalog records.
    """

    def __init__(self, catalog: dict[str, Any]):
        self.catalog = catalog
        self._by_category_key: dict[tuple[str, str], CanonicalObject] = {}
        self._by_id: dict[str, CanonicalObject] = {}
        self._aliases: dict[tuple[str, str], str] = {}
        self._build()

    @staticmethod
    def normalize_key(value: str) -> str:
        return " ".join(value.upper().strip().split())

    def _build(self) -> None:
        objects = self.catalog.get("objects")
        if not isinstance(objects, dict):
            raise RegistryError("catalog.objects must be an object")

        for category, records in objects.items():
            if not isinstance(records, dict):
                raise RegistryError(f"catalog.objects.{category} must be an object")
            for raw_key, record in records.items():
                if not isinstance(record, dict):
                    raise RegistryError(f"record {category}:{raw_key} must be an object")
                key = self.normalize_key(raw_key)
                object_id = record.get("id")
                if not isinstance(object_id, str) or not object_id.strip():
                    raise RegistryError(f"record {category}:{raw_key} has no canonical id")
                if (category, key) in self._by_category_key:
                    raise RegistryError(f"duplicate canonical key {category}:{key}")
                if object_id in self._by_id:
                    other = self._by_id[object_id]
                    raise RegistryError(
                        f"duplicate canonical id {object_id}: "
                        f"{other.category}:{other.key} and {category}:{key}"
                    )
                obj = CanonicalObject(
                    category=category,
                    key=key,
                    object_id=object_id,
                    status=str(record.get("status", "UNDEFINED")),
                    record=record,
                )
                self._by_category_key[(category, key)] = obj
                self._by_id[object_id] = obj
                self._register_alias(category, key, key)
                aliases = record.get("aliases", [])
                if aliases is None:
                    aliases = []
                if not isinstance(aliases, list):
                    raise RegistryError(f"aliases for {category}:{key} must be a list")
                for alias in aliases:
                    if not isinstance(alias, str) or not alias.strip():
                        raise RegistryError(f"invalid alias for {category}:{key}")
                    self._register_alias(category, self.normalize_key(alias), key)

    def _register_alias(self, category: str, alias: str, canonical_key: str) -> None:
        lookup = (category, alias)
        existing = self._aliases.get(lookup)
        if existing is not None and existing != canonical_key:
            raise RegistryError(
                f"alias conflict {category}:{alias} resolves to both "
                f"{existing} and {canonical_key}"
            )
        self._aliases[lookup] = canonical_key

    def resolve(self, category: str, key_or_alias: str | None) -> CanonicalObject | None:
        if key_or_alias is None:
            return None
        normalized = self.normalize_key(key_or_alias)
        canonical_key = self._aliases.get((category, normalized))
        if canonical_key is None:
            return None
        return self._by_category_key[(category, canonical_key)]

    def require(self, category: str, key_or_alias: str) -> CanonicalObject:
        result = self.resolve(category, key_or_alias)
        if result is None:
            raise RegistryError(f"unknown canonical object {category}:{key_or_alias}")
        return result

    def by_id(self, object_id: str) -> CanonicalObject | None:
        return self._by_id.get(object_id)

    def all(self, category: str | None = None) -> Iterable[CanonicalObject]:
        objects = self._by_category_key.values()
        if category is not None:
            objects = (obj for obj in objects if obj.category == category)
        return tuple(sorted(objects, key=lambda obj: (obj.category, obj.key, obj.object_id)))

    def validate(self) -> dict[str, Any]:
        return {
            "valid": True,
            "object_count": len(self._by_id),
            "alias_count": len(self._aliases),
            "categories": sorted({obj.category for obj in self._by_id.values()}),
        }
