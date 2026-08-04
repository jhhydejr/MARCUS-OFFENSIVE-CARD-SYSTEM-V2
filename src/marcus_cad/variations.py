from __future__ import annotations

from copy import deepcopy
from typing import Any


class VariationError(ValueError):
    pass


EXACT_RELATIONAL_VARIATIONS = {"ON", "HO", "DON", "HAY", "HAZE", "HOAX"}


def _index(players: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(player["label"]): player for player in players}


def _swap_geometry(
    players: list[dict[str, Any]], first: str, second: str
) -> list[dict[str, Any]]:
    result = deepcopy(players)
    indexed = _index(result)
    if first not in indexed or second not in indexed:
        raise VariationError(f"Required players are missing: {first}, {second}")

    geometry_fields = (
        "svg_x", "svg_y", "x", "y", "los_status", "alignment",
        "landmark", "side", "split"
    )
    a = indexed[first]
    b = indexed[second]
    for field in geometry_fields:
        if field in a or field in b:
            a_value = a.get(field)
            b_value = b.get(field)
            a[field] = b_value
            b[field] = a_value
    return result


def apply_variation(
    players: list[dict[str, Any]], variation: str
) -> list[dict[str, Any]]:
    """Apply only source-supported relational rules without inventing geometry."""
    name = variation.upper().strip()
    result = deepcopy(players)
    indexed = _index(result)

    if name == "ON":
        if "Y" not in indexed:
            raise VariationError("ON requires Y")
        indexed["Y"]["los_status"] = "ON"
        return result

    if name == "HO":
        if "H" not in indexed:
            raise VariationError("HO requires H")
        indexed["H"]["los_status"] = "ON"
        return result

    if name == "DON":
        missing = [label for label in ("Y", "H") if label not in indexed]
        if missing:
            raise VariationError(f"DON requires: {', '.join(missing)}")
        indexed["Y"]["los_status"] = "ON"
        indexed["H"]["los_status"] = "ON"
        return result

    if name == "HAY":
        return _swap_geometry(result, "H", "Y")

    if name == "HAZE":
        return _swap_geometry(result, "H", "Z")

    if name == "HOAX":
        return _swap_geometry(result, "H", "X")

    raise VariationError(
        f"{name} requires approved exact geometry before executable application"
    )
