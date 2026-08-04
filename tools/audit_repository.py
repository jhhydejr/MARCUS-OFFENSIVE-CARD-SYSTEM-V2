from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

ID_KEYS = {
    "id", "object_id", "drawing_id", "formation_id", "motion_id", "coverage_id",
    "personnel_id", "structure_id", "family_id", "variation_id", "field_location_id",
}
REFERENCE_SUFFIXES = ("_id", "_ids")


@dataclass(frozen=True)
class JsonFileAudit:
    path: str
    sha256: str
    top_level_type: str
    object_ids: tuple[str, ...]
    parse_error: str | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def walk(value: Any, key: str | None = None) -> Iterable[tuple[str | None, Any]]:
    yield key, value
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from walk(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child, key)


def audit(root: Path) -> dict[str, Any]:
    files = sorted(p for p in root.rglob("*") if p.is_file() and ".pytest_cache" not in p.parts and "__pycache__" not in p.parts)
    json_files = [p for p in files if p.suffix.lower() == ".json"]
    parsed: dict[Path, Any] = {}
    json_audits: list[JsonFileAudit] = []
    parse_errors: list[dict[str, str]] = []
    id_locations: defaultdict[str, list[str]] = defaultdict(list)

    for path in json_files:
        rel = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            parsed[path] = data
            ids: set[str] = set()
            if isinstance(data, dict):
                for key in ID_KEYS:
                    value = data.get(key)
                    if isinstance(value, str) and value:
                        ids.add(value)
            for object_id in sorted(ids):
                id_locations[object_id].append(rel)
            json_audits.append(JsonFileAudit(rel, sha256(path), type(data).__name__, tuple(sorted(ids))))
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            parse_errors.append({"path": rel, "error": message})
            json_audits.append(JsonFileAudit(rel, sha256(path), "invalid", tuple(), message))

    known_ids = set(id_locations)
    references: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    for path, data in parsed.items():
        rel = path.relative_to(root).as_posix()
        for key, value in walk(data):
            if not key or (key not in ID_KEYS and not key.endswith(REFERENCE_SUFFIXES)):
                continue
            for candidate in strings(value):
                if not candidate or candidate in known_ids:
                    if candidate:
                        references.append({"source": rel, "field": key, "target": candidate})
                    continue
                # Only flag values that look like canonical IDs; ordinary labels are not references.
                if "-" in candidate and candidate.upper() == candidate and " " not in candidate:
                    unresolved.append({"source": rel, "field": key, "target": candidate})

    duplicate_ids = {object_id: locations for object_id, locations in sorted(id_locations.items()) if len(locations) > 1}
    extension_counts = Counter((p.suffix.lower() or "<none>") for p in files)
    object_type_counts = Counter()
    status_counts = Counter()
    for data in parsed.values():
        if isinstance(data, dict):
            if isinstance(data.get("object_type"), str):
                object_type_counts[data["object_type"]] += 1
            if isinstance(data.get("status"), str):
                status_counts[data["status"]] += 1

    return {
        "audit_format": "marcus_repository_audit",
        "audit_version": 1,
        "root": root.name,
        "summary": {
            "file_count": len(files),
            "json_count": len(json_files),
            "svg_count": extension_counts.get(".svg", 0),
            "png_count": extension_counts.get(".png", 0),
            "pdf_count": extension_counts.get(".pdf", 0),
            "python_count": extension_counts.get(".py", 0),
            "canonical_id_count": len(known_ids),
            "json_parse_error_count": len(parse_errors),
            "duplicate_id_count": len(duplicate_ids),
            "unresolved_reference_count": len(unresolved),
        },
        "extension_counts": dict(sorted(extension_counts.items())),
        "object_type_counts": dict(sorted(object_type_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "duplicate_ids": duplicate_ids,
        "unresolved_references": unresolved,
        "json_parse_errors": parse_errors,
        "json_files": [asdict(item) for item in json_audits],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Marcus Offensive CAD repository deterministically.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output", default="reports/repository_audit.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    report = audit(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 1 if report["summary"]["json_parse_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
