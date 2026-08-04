from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


class RendererError(Exception):
    pass


@dataclass(frozen=True)
class RenderCoordinate:
    player: str
    x: float
    y: float
    radius: float | None = None


@dataclass(frozen=True)
class RenderAssignmentBinding:
    player: str
    assignment_id: str
    assignment_type: str
    canonical_name: str


@dataclass(frozen=True)
class DrawingSceneRenderInput:
    drawing_id: str
    normalized_call: str
    layer_order: tuple[str, ...]
    layout_id: str
    layout_sections: tuple[str, ...]
    coordinates: tuple[RenderCoordinate, ...]
    assignment_bindings: Mapping[str, RenderAssignmentBinding]


_LABEL_TO_SVG = {"QB": "Q"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def render_svg_from_scene(
    template: Path,
    output: Path,
    scene: DrawingSceneRenderInput,
) -> None:
    """Render a complete drawing scene through the canonical layer contract."""
    required = ("field_template", "defense", "offense", "assignments", "labels_metadata")
    if scene.layer_order != required:
        raise RendererError(
            f"Invalid drawing scene layer order: {scene.layer_order!r}"
        )
    required_sections = ("title", "diagram", "notes", "validation", "metadata")
    if scene.layout_sections != required_sections:
        raise RendererError(f"Invalid card layout sections: {scene.layout_sections!r}")
    if not scene.layout_id:
        raise RendererError("Drawing scene requires a card layout id")
    if len(scene.coordinates) != 11:
        raise RendererError("Drawing scene must contain exactly 11 offensive coordinates")
    render_svg_from_coordinates(
        template,
        output,
        scene.coordinates,
        assignment_bindings=scene.assignment_bindings,
    )

    tree = ET.parse(output)
    root = tree.getroot()
    metadata = next((element for element in root if _local(element.tag) == "metadata"), None)
    if metadata is None:
        metadata = ET.Element("metadata")
        root.insert(0, metadata)
    ET.SubElement(
        metadata,
        "marcus-drawing-scene",
        {
            "drawing_id": scene.drawing_id,
            "normalized_call": scene.normalized_call,
            "layers": ",".join(scene.layer_order),
            "layout_id": scene.layout_id,
            "layout_sections": ",".join(scene.layout_sections),
        },
    )
    tree.write(output, encoding="unicode", xml_declaration=True)


def render_svg_from_coordinates(
    template: Path,
    output: Path,
    coordinates: Iterable[RenderCoordinate],
    *,
    assignment_bindings: Mapping[str, RenderAssignmentBinding] | None = None,
) -> None:
    """Render the offensive player layer from approved coordinate objects.

    The stored SVG remains the card/defense/motion template. Offensive player
    circles and labels are repositioned from canonical geometry at render time.
    """
    tree = ET.parse(template)
    root = tree.getroot()
    circles = [element for element in root.iter() if _local(element.tag) == "circle"]
    rectangles = [element for element in root.iter() if _local(element.tag) == "rect"]
    texts = [element for element in root.iter() if _local(element.tag) == "text"]

    used_circles: set[int] = set()
    used_rectangles: set[int] = set()
    for coordinate in coordinates:
        label = _LABEL_TO_SVG.get(coordinate.player, coordinate.player)
        accepted_labels = {label, coordinate.player}
        candidates = [
            element for element in texts
            if (element.text or "").strip() in accepted_labels
            and "x" in element.attrib and "y" in element.attrib
            and float(element.attrib.get("y", "0")) >= 580
        ]
        if len(candidates) != 1:
            raise RendererError(f"Expected one offensive SVG label for {label}; found {len(candidates)}")
        text = candidates[0]
        old_x = float(text.attrib["x"])
        old_y = float(text.attrib["y"]) - 5.0

        shape: ET.Element | None = None
        shape_kind: str | None = None

        # The Center is canonically drawn as a square in stored formation SVGs;
        # all other offensive players use circles. Reuse the stored symbol type
        # instead of converting or inventing geometry.
        if coordinate.player == "C":
            ranked_rectangles: list[tuple[float, int, ET.Element]] = []
            for index, rectangle in enumerate(rectangles):
                if index in used_rectangles:
                    continue
                required = {"x", "y", "width", "height"}
                if not required.issubset(rectangle.attrib):
                    continue
                width = float(rectangle.attrib["width"])
                height = float(rectangle.attrib["height"])
                if width > 100 or height > 100:
                    continue
                center_x = float(rectangle.attrib["x"]) + width / 2.0
                center_y = float(rectangle.attrib["y"]) + height / 2.0
                distance = abs(center_x - old_x) + abs(center_y - old_y)
                ranked_rectangles.append((distance, index, rectangle))
            if ranked_rectangles:
                distance, index, shape = min(ranked_rectangles, key=lambda item: item[0])
                if distance <= 2.0:
                    used_rectangles.add(index)
                    shape_kind = "rect"
                else:
                    shape = None

        if shape is None:
            ranked_circles: list[tuple[float, int, ET.Element]] = []
            for index, circle in enumerate(circles):
                if index in used_circles or "cx" not in circle.attrib or "cy" not in circle.attrib:
                    continue
                distance = abs(float(circle.attrib["cx"]) - old_x) + abs(float(circle.attrib["cy"]) - old_y)
                ranked_circles.append((distance, index, circle))
            if not ranked_circles:
                raise RendererError(f"No SVG player symbol available for {label}")
            distance, index, shape = min(ranked_circles, key=lambda item: item[0])
            if distance > 2.0:
                raise RendererError(f"SVG player-symbol/label mismatch for {label}")
            used_circles.add(index)
            shape_kind = "circle"

        x = f"{coordinate.x:.6f}".rstrip("0").rstrip(".")
        y = f"{coordinate.y:.6f}".rstrip("0").rstrip(".")
        if shape_kind == "circle":
            shape.attrib["cx"] = x
            shape.attrib["cy"] = y
            if coordinate.radius is not None:
                shape.attrib["r"] = f"{coordinate.radius:.6f}".rstrip("0").rstrip(".")
        else:
            half_size = coordinate.radius if coordinate.radius is not None else 20.0
            size = 2.0 * half_size
            shape.attrib["x"] = f"{coordinate.x - half_size:.6f}".rstrip("0").rstrip(".")
            shape.attrib["y"] = f"{coordinate.y - half_size:.6f}".rstrip("0").rstrip(".")
            shape.attrib["width"] = f"{size:.6f}".rstrip("0").rstrip(".")
            shape.attrib["height"] = f"{size:.6f}".rstrip("0").rstrip(".")

        text.attrib["x"] = x
        text.attrib["y"] = f"{coordinate.y + 5.0:.6f}".rstrip("0").rstrip(".")
        text.attrib["data-player"] = coordinate.player
        shape.attrib["data-player"] = coordinate.player

        binding = (assignment_bindings or {}).get(coordinate.player)
        if binding is not None:
            attributes = {
                "data-assignment-id": binding.assignment_id,
                "data-assignment-type": binding.assignment_type,
                "data-assignment-name": binding.canonical_name,
            }
            text.attrib.update(attributes)
            shape.attrib.update(attributes)


    # Persist canonical player-to-assignment bindings in SVG metadata. The
    # renderer does not draw assignment geometry until approved drawing rules
    # exist, but downstream exporters and validators receive the exact bound
    # object IDs through the SVG master.
    metadata = next((element for element in root if _local(element.tag) == "metadata"), None)
    if metadata is None:
        metadata = ET.Element("metadata")
        root.insert(0, metadata)
    binding_parent = ET.SubElement(metadata, "marcus-assignment-bindings")
    for player, binding in sorted((assignment_bindings or {}).items()):
        ET.SubElement(
            binding_parent,
            "binding",
            {
                "player": player,
                "assignment_id": binding.assignment_id,
                "assignment_type": binding.assignment_type,
                "canonical_name": binding.canonical_name,
            },
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="unicode", xml_declaration=True)
