Library
/
system.py


from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .parser import CatalogDrivenParser
from .resolver import ObjectRegistry
from .database_index import DatabaseObjectIndex
from .renderer import (
    DrawingSceneRenderInput,
    RenderAssignmentBinding,
    RenderCoordinate,
    RendererError,
    render_svg_from_scene,
)


class MarcusError(Exception):
    pass


@dataclass(frozen=True)
class CallGrammarValidation:
    card_type: str
    valid: bool
    offense_valid: bool
    defense_valid: bool
    offense_required_slots: list[str]
    defense_required_slots: list[str]
    missing_offense_slots: list[str]
    missing_defense_slots: list[str]
    offense_slot_order_violations: list[str]
    defense_slot_order_violations: list[str]
    offense_slots: dict[str, str | None]
    defense_slots: dict[str, str | None]


@dataclass(frozen=True)
class CallSlotStatus:
    number: int
    name: str
    required: bool
    present: bool
    value: str | None
    status: str


@dataclass(frozen=True)
class CallSlotReport:
    schema: str
    card_type: str
    offense: tuple[CallSlotStatus, ...]
    defense_present: bool
    defense: tuple[CallSlotStatus, ...]
    missing_required_offense: tuple[str, ...]
    missing_required_defense: tuple[str, ...]
    offense_order_violations: tuple[str, ...]
    defense_order_violations: tuple[str, ...]
    valid: bool


@dataclass
class Resolution:
    card_type: str
    source_call: str
    normalized_call: str
    field_location: str | None
    personnel: str | None
    backfield: str | None
    formation: str | None
    variation: str | None
    motion: str | None
    shift: str | None
    protection: str | None
    play: str | None
    tag: str | None
    structure: str | None
    front: str | None
    game: str | None
    pressure: str | None
    blitz: str | None
    coverage: str | None
    # Backward-compatible aliases.
    defensive_personnel: str | None
    defensive_structure: str | None
    call_grammar_validation: CallGrammarValidation
    resolved_ids: dict[str, str]
    resolved_sources: dict[str, str]
    blockers: list[dict[str, str]]
    renderable: bool
    drawing_id: str | None
    unknown_offense_tokens: list[str]
    unknown_defense_tokens: list[str]
    offense_slot_order_violations: list[str]
    defense_slot_order_violations: list[str]


@dataclass(frozen=True)
class AssetReuseValidation:
    valid: bool
    drawing_id: str
    catalog_status: str
    asset_directory: str
    reused_files: dict[str, str]
    source_hashes: dict[str, str]
    missing_files: list[str]
    invalid_paths: list[str]


@dataclass(frozen=True)
class DrawingAssetInventoryEntry:
    drawing_id: str
    catalog_status: str
    approved: bool
    reusable: bool
    asset_directory: str
    reused_files: dict[str, str]
    source_hashes: dict[str, str]
    missing_files: list[str]
    invalid_paths: list[str]


@dataclass(frozen=True)
class DrawingAssetInventory:
    schema: str
    drawing_count: int
    approved_count: int
    reusable_count: int
    approved_reusable_count: int
    incomplete_count: int
    approved_incomplete_count: int
    entries: tuple[DrawingAssetInventoryEntry, ...]


@dataclass(frozen=True)
class CoordinateValidation:
    valid: bool
    player_count: int
    unique_player_count: int
    expected_players: list[str]
    missing_players: list[str]
    unexpected_players: list[str]
    duplicate_positions: list[list[str]]
    invalid_coordinates: list[str]
    invalid_radii: list[str]
    geometry_ids: list[str]
    drawing_ids: list[str]


@dataclass(frozen=True)
class AssignmentValidation:
    valid: bool
    status: str
    player_count: int
    assigned_player_count: int
    missing_players: list[str]
    unexpected_players: list[str]
    invalid_assignment_ids: list[str]
    unknown_assignment_ids: list[str]
    ineligible_assignments: list[str]
    assignment_ids: dict[str, str]
    blockers: list[dict[str, str]]


@dataclass(frozen=True)
class AssignmentObject:
    object_id: str
    assignment_type: str
    canonical_name: str
    eligible_players: tuple[str, ...]
    status: str
    file: str




@dataclass(frozen=True)
class PlayerAssignment:
    player: str
    assignment_id: str | None
    assignment_type: str | None
    canonical_name: str | None
    status: str
    source_file: str | None

@dataclass(frozen=True)
class AssignmentBinding:
    player: str
    assignment_id: str
    assignment_type: str
    canonical_name: str
    source_file: str


@dataclass(frozen=True)
class PlayerCoordinate:
    player: str
    x: float
    y: float
    radius: float | None = None
    los_status: str | None = None
    geometry_id: str | None = None
    drawing_id: str | None = None


@dataclass(frozen=True)
class PlayCard:
    source_call: str
    normalized_call: str
    drawing_id: str
    resolved_ids: dict[str, str]
    coordinates: tuple[PlayerCoordinate, ...]
    coordinate_validation: CoordinateValidation
    assignment_plan: tuple[PlayerAssignment, ...]
    assignment_validation: AssignmentValidation
    assignment_bindings: tuple[AssignmentBinding, ...]
    completeness: str


@dataclass(frozen=True)
class DrawingLayer:
    name: str
    order: int
    object_count: int
    source: str


@dataclass(frozen=True)
class DrawingScene:
    drawing_id: str
    normalized_call: str
    layers: tuple[DrawingLayer, ...]
    expected_offensive_players: tuple[str, ...]
    offensive_players: tuple[PlayerCoordinate, ...]
    assignment_bindings: tuple[AssignmentBinding, ...]
    completeness: str




@dataclass(frozen=True)
class CardLayoutSection:
    name: str
    x: float
    y: float
    width: float
    height: float
    required: bool


@dataclass(frozen=True)
class CardLayout:
    layout_id: str
    status: str
    canvas_width: float
    canvas_height: float
    sections: tuple[CardLayoutSection, ...]


@dataclass(frozen=True)
class CardLayoutValidation:
    valid: bool
    layout_id: str
    expected_sections: list[str]
    actual_sections: list[str]
    missing_sections: list[str]
    duplicate_sections: list[str]
    out_of_bounds_sections: list[str]
    overlapping_sections: list[list[str]]


@dataclass(frozen=True)
class OutputIntegrityValidation:
    valid: bool
    checked_outputs: list[str]
    missing_outputs: list[str]
    missing_hashes: list[str]
    hash_mismatches: list[str]
    paths_outside_card_directory: list[str]


@dataclass(frozen=True)
class DrawingSceneValidation:
    valid: bool
    expected_layer_order: list[str]
    actual_layer_order: list[str]
    duplicate_layers: list[str]
    invalid_layer_orders: list[int]
    invalid_object_counts: list[str]
    offensive_player_count: int
    unique_offensive_player_count: int
    missing_offensive_players: list[str]
    unexpected_offensive_players: list[str]
    assignment_binding_count: int
    invalid_assignment_binding_players: list[str]



class MarcusSystem:
    def __init__(self, root: Path):
        self.root = root.resolve()
        with (self.root / "database/master/catalog.json").open("r", encoding="utf-8") as f:
            self.catalog: dict[str, Any] = json.load(f)
        self.parser = CatalogDrivenParser(self.catalog)
        self.registry = ObjectRegistry(self.catalog)
        self.database_index = DatabaseObjectIndex(self.root)
        self.catalog_source_links = self.database_index.link_catalog(self.catalog)
        self.assignment_registry = self._load_assignment_registry()
        grammar_path = self.root / "database/master/call_grammar.json"
        with grammar_path.open("r", encoding="utf-8") as handle:
            self.call_grammar: dict[str, Any] = json.load(handle)


    def _load_assignment_registry(self) -> dict[str, AssignmentObject]:
        """Load explicitly stored assignment objects from the project database.

        Assignment knowledge is never inferred from names or drawing lines. Only
        JSON objects stored under ``database/offense/assignments`` are indexed.
        """
        directory = self.root / "database/offense/assignments"
        if not directory.exists():
            return {}
        registry: dict[str, AssignmentObject] = {}
        for path in sorted(directory.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                record = json.load(handle)
            object_id = record.get("object_id")
            if not object_id:
                continue
            assignment_type = record.get("assignment_type")
            canonical_name = record.get("canonical_name")
            eligible = record.get("eligible_players", [])
            status = record.get("status", "UNAPPROVED")
            if not all(isinstance(value, str) and value.strip() for value in (object_id, assignment_type, canonical_name, status)):
                raise MarcusError(f"Invalid assignment object metadata: {path}")
            if not isinstance(eligible, list) or not all(isinstance(player, str) and player.strip() for player in eligible):
                raise MarcusError(f"Invalid eligible_players in assignment object: {path}")
            if object_id in registry:
                raise MarcusError(f"Duplicate assignment object id: {object_id}")
            registry[object_id] = AssignmentObject(
                object_id=object_id,
                assignment_type=assignment_type,
                canonical_name=canonical_name,
                eligible_players=tuple(eligible),
                status=status,
                file=str(path.relative_to(self.root)),
            )
        return registry

    @staticmethod
    def normalize(text: str) -> str:
        return CatalogDrivenParser.normalize(text)

    @staticmethod
    def normalize_card_type(card_type: str) -> str:
        normalized = str(card_type).strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {"FORMATION": "FORMATION_CARD", "SCOUT": "SCOUT_CARD", "PLAY": "PLAY_CARD"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"FORMATION_CARD", "SCOUT_CARD", "PLAY_CARD"}:
            raise MarcusError(f"Unsupported card type: {card_type}")
        return normalized

    def default_backfield(self) -> str | None:
        defaults = self.call_grammar.get("defaults", {})
        value = defaults.get("backfield") if isinstance(defaults, dict) else None
        return value.strip() if isinstance(value, str) and value.strip() else None

    def effective_backfield(self, parsed: Any) -> tuple[str | None, bool]:
        called = getattr(parsed, "backfield", None)
        if called:
            return called, False
        default = self.default_backfield()
        return default, bool(default)

    def validate_call_grammar(self, parsed: Any, *, card_type: str = "PLAY_CARD") -> CallGrammarValidation:
        card_type = self.normalize_card_type(card_type)
        card_config = self.call_grammar["card_types"][card_type]
        offense_required = list(card_config["offensive_required_slots"])
        defense_required = list(card_config["defensive_required_slots"])
        offense_slots = {
            "personnel": parsed.personnel,
            "backfield": self.effective_backfield(parsed)[0],
            "formation": parsed.formation,
            "variation": parsed.variation,
            "motion": parsed.motion,
            "shift": parsed.shift,
            "protection": parsed.protection,
            "play": parsed.play,
            "tag": parsed.tag,
        }
        defense_slots = {
            "structure": parsed.structure,
            "front": parsed.front,
            "game": parsed.game,
            "pressure": parsed.pressure,
            "blitz": parsed.blitz,
            "coverage": parsed.coverage,
        }
        missing_offense = [slot for slot in offense_required if not offense_slots.get(slot)]
        # A defensive call is optional as a whole. If VS is present, required
        # defensive slots are enforced.
        missing_defense = (
            [slot for slot in defense_required if not defense_slots.get(slot)]
            if parsed.defense_text else []
        )
        offense_order_violations = list(getattr(parsed, "offense_slot_order_violations", ()))
        defense_order_violations = list(getattr(parsed, "defense_slot_order_violations", ()))
        offense_valid = not missing_offense and not offense_order_violations
        defense_valid = not missing_defense and not defense_order_violations
        return CallGrammarValidation(
            card_type=card_type,
            valid=offense_valid and defense_valid,
            offense_valid=offense_valid,
            defense_valid=defense_valid,
            offense_required_slots=offense_required,
            defense_required_slots=defense_required,
            missing_offense_slots=missing_offense,
            missing_defense_slots=missing_defense,
            offense_slot_order_violations=offense_order_violations,
            defense_slot_order_violations=defense_order_violations,
            offense_slots=offense_slots,
            defense_slots=defense_slots,
        )

    def build_call_slot_report(self, parsed: Any, *, card_type: str = "PLAY_CARD") -> CallSlotReport:
        """Build the coach-approved numbered call sheet for one parsed call.

        Optional slots are reported as ``OPTIONAL_OMITTED`` rather than errors.
        Required slots are reported as ``MISSING_REQUIRED`` when absent. Defense
        is optional as a whole; its required slots apply only when ``VS`` is
        present in the call.
        """
        grammar_validation = self.validate_call_grammar(parsed, card_type=card_type)
        offense_values = grammar_validation.offense_slots
        defense_values = grammar_validation.defense_slots
        offense_required = set(grammar_validation.offense_required_slots)
        defense_required = set(grammar_validation.defense_required_slots)
        configured_names = self.call_grammar["card_types"][grammar_validation.card_type]["offensive_ordered_slots"]
        master_slots = {item["name"]: item for item in self.call_grammar["offensive_call"]["ordered_slots"]}
        ordered_offense_slots = [master_slots[name] for name in configured_names]
        default_backfield, backfield_defaulted = self.effective_backfield(parsed)

        offense = tuple(
            CallSlotStatus(
                number=index,
                name=item["name"],
                required=item["name"] in offense_required,
                present=bool(offense_values.get(item["name"])),
                value=(
                    f"{default_backfield} (DEFAULT)"
                    if item["name"] == "backfield" and backfield_defaulted
                    else offense_values.get(item["name"])
                ),
                status=(
                    "DEFAULTED"
                    if item["name"] == "backfield" and backfield_defaulted
                    else (
                        "PRESENT"
                        if offense_values.get(item["name"])
                        else ("MISSING_REQUIRED" if item["name"] in offense_required else "OPTIONAL_OMITTED")
                    )
                ),
            )
            for index, item in enumerate(
                ordered_offense_slots,
                start=1,
            )
        )
        defense_present = bool(parsed.defense_text)
        defense = tuple(
            CallSlotStatus(
                number=index,
                name=item["name"],
                required=item["name"] in defense_required,
                present=bool(defense_values.get(item["name"])),
                value=defense_values.get(item["name"]),
                status=(
                    "NOT_CALLED"
                    if not defense_present
                    else (
                        "PRESENT"
                        if defense_values.get(item["name"])
                        else ("MISSING_REQUIRED" if item["name"] in defense_required else "OPTIONAL_OMITTED")
                    )
                ),
            )
            for index, item in enumerate(
                self.call_grammar["defensive_call"]["ordered_slots"],
                start=1,
            )
        )
        return CallSlotReport(
            schema="marcus.call_slots.v1",
            card_type=grammar_validation.card_type,
            offense=offense,
            defense_present=defense_present,
            defense=defense,
            missing_required_offense=tuple(grammar_validation.missing_offense_slots),
            missing_required_defense=tuple(grammar_validation.missing_defense_slots),
            offense_order_violations=tuple(grammar_validation.offense_slot_order_violations),
            defense_order_violations=tuple(grammar_validation.defense_slot_order_violations),
            valid=grammar_validation.valid,
        )

    def parse(self, call: str, *, card_type: str = "SCOUT_CARD") -> Resolution:
        parsed = self.parser.parse(call)
        n = parsed.normalized_call
        field_location = parsed.field_location
        personnel = parsed.personnel
        backfield, backfield_defaulted = self.effective_backfield(parsed)
        formation = parsed.formation
        variation = parsed.variation
        motion = parsed.motion
        shift = parsed.shift
        protection = parsed.protection
        play = parsed.play
        tag = parsed.tag
        structure = parsed.structure
        front = parsed.front
        game = parsed.game
        pressure = parsed.pressure
        blitz = parsed.blitz
        coverage = parsed.coverage
        defensive_personnel = parsed.defensive_personnel
        defensive_structure = parsed.defensive_structure
        grammar_validation = self.validate_call_grammar(parsed, card_type=card_type)

        ids: dict[str, str] = {}
        sources: dict[str, str] = {}
        blockers: list[dict[str, str]] = []
        objects = self.catalog["objects"]

        def resolve(category: str, key: str | None, required: bool = False) -> None:
            if not key:
                if required:
                    blockers.append({"object": category, "reason": "MISSING_FROM_CALL"})
                return
            canonical = self.registry.resolve(category, key)
            if canonical is None:
                blockers.append({"object": f"{category}:{key}", "reason": "NOT_IN_DATABASE"})
                return
            record = canonical.record
            ids[category] = canonical.object_id
            source = self.database_index.resolve(canonical.object_id, self.database_index._preferred_file(record))
            sources[category] = source.file if source else "database/master/catalog.json"
            status = canonical.status
            if status not in {
                "CANONICAL",
                "RECOVERED",
                "RULE_RECOVERED",
                "COACH_APPROVED",
                "DERIVED_FROM_APPROVED_MIRROR",
            }:
                blockers.append({"object": f"{category}:{key}", "reason": status})

        resolve("field_locations", field_location)
        resolve("personnel", personnel, required=True)
        resolve("backfields", backfield)
        resolve("formations", formation, required=True)
        resolve("variations", variation)
        resolve("motions", motion)
        resolve("shifts", shift)
        resolve("protections", protection)
        resolve("plays", play)
        resolve("tags", tag)
        resolve("defensive_personnel", structure)
        resolve("defensive_structures", front)
        resolve("defensive_games", game)
        resolve("defensive_pressures", pressure)
        resolve("defensive_blitzes", blitz)
        resolve("coverages", coverage)

        # GUN is the coach-approved global default when no backfield is called.
        # Other backfields must still be explicitly approved for the formation.
        default_backfield = self.default_backfield()
        if (
            backfield
            and formation
            and "backfields" in ids
            and "formations" in ids
            and not (backfield_defaulted and backfield == default_backfield)
        ):
            formation_source = sources.get("formations")
            approved_backfield_id: str | None = None
            if formation_source and formation_source != "database/master/catalog.json":
                formation_path = self.root / formation_source
                if formation_path.is_file():
                    try:
                        formation_data = json.loads(formation_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        formation_data = {}
                    value = formation_data.get("default_backfield_id")
                    if isinstance(value, str) and value.strip():
                        approved_backfield_id = value.strip()
            if approved_backfield_id is None:
                blockers.append({
                    "object": f"backfields:{backfield}",
                    "reason": "BACKFIELD_NOT_DEFINED_FOR_FORMATION",
                })
            elif approved_backfield_id != ids["backfields"]:
                blockers.append({
                    "object": f"backfields:{backfield}",
                    "reason": "BACKFIELD_NOT_APPROVED_FOR_FORMATION",
                })

        for token in parsed.unknown_offense_tokens:
            blockers.append({"object": f"offense_token:{token}", "reason": "UNKNOWN_TOKEN"})
        for token in parsed.unknown_defense_tokens:
            blockers.append({"object": f"defense_token:{token}", "reason": "UNKNOWN_TOKEN"})
        for violation in parsed.offense_slot_order_violations:
            blockers.append({"object": f"offense_order:{violation}", "reason": "CALL_ORDER_VIOLATION"})
        for violation in parsed.defense_slot_order_violations:
            blockers.append({"object": f"defense_order:{violation}", "reason": "CALL_ORDER_VIOLATION"})
        for slot in grammar_validation.missing_offense_slots:
            blockers.append({"object": f"offense_slot:{slot}", "reason": "MISSING_REQUIRED_SLOT"})
        for slot in grammar_validation.missing_defense_slots:
            blockers.append({"object": f"defense_slot:{slot}", "reason": "MISSING_REQUIRED_SLOT"})

        drawing_id = None
        exact_call = self.catalog.get("compiled_calls", {}).get(n)
        if exact_call:
            drawing_id = exact_call.get("drawing_id")
        elif formation in self.catalog["objects"]["formations"]:
            formation_record = self.catalog["objects"]["formations"][formation]
            drawing_id = formation_record.get("drawing_id")
            variants = formation_record.get("resolved_variants", {})
            # Resolve the most specific approved stored formation bundle first.
            # Field location remains a separate call object; it is used only to
            # select a stored variant and never changes coordinates by guessing.
            parts = [personnel, field_location, variation, motion]
            candidate_keys: list[str] = []
            if all(parts):
                candidate_keys.append("|".join(parts))
            if personnel and field_location and variation:
                candidate_keys.append(f"{personnel}|{field_location}|{variation}")
            if personnel and variation and motion:
                candidate_keys.append(f"{personnel}|{variation}|{motion}")
            if personnel and field_location:
                candidate_keys.append(f"{personnel}|{field_location}")
            if personnel and variation:
                candidate_keys.append(f"{personnel}|{variation}")
            if personnel:
                candidate_keys.append(personnel)
            for key in candidate_keys:
                item = variants.get(key)
                if isinstance(item, dict) and item.get("drawing_id"):
                    drawing_id = item["drawing_id"]
                    break

            # A recognized formation may still need an approved qualifier such
            # as field location or variation before it maps to stored geometry.
            # Report the approved complete calls instead of silently returning
            # an empty drawing id.
            if drawing_id is None and not blockers and isinstance(variants, dict):
                suggestions: list[str] = []
                for variant_key, variant in variants.items():
                    if not isinstance(variant, dict) or not variant.get("drawing_id"):
                        continue
                    key_parts = [part for part in str(variant_key).split("|") if part]
                    if not key_parts:
                        continue
                    variant_personnel = key_parts[0]
                    if personnel and variant_personnel != personnel:
                        continue
                    remaining = key_parts[1:]
                    location_part = next((part for part in remaining if part in {"LH", "LM", "M", "RM", "RH"}), None)
                    other_parts = [part for part in remaining if part != location_part]
                    call_parts: list[str] = []
                    if location_part:
                        call_parts.append(location_part)
                    call_parts.append(f"({variant_personnel})")
                    call_parts.append(str(formation))
                    call_parts.extend(other_parts)
                    suggestion = " ".join(call_parts)
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
                blocker: dict[str, str] = {
                    "object": f"formation_variant:{formation}",
                    "reason": "APPROVED_GEOMETRY_REQUIRES_MORE_CALL_DETAIL",
                }
                if suggestions:
                    blocker["suggested_calls"] = "; ".join(suggestions)
                blockers.append(blocker)

        return Resolution(
            card_type=grammar_validation.card_type,
            source_call=call, normalized_call=n, field_location=field_location, personnel=personnel,
            backfield=backfield, formation=formation, variation=variation, motion=motion, shift=shift,
            protection=protection, play=play, tag=tag, structure=structure, front=front,
            game=game, pressure=pressure, blitz=blitz, coverage=coverage,
            defensive_personnel=defensive_personnel, defensive_structure=defensive_structure,
            call_grammar_validation=grammar_validation,
            resolved_ids=ids, resolved_sources=sources, blockers=blockers, renderable=bool(drawing_id) and not blockers, drawing_id=drawing_id,
            unknown_offense_tokens=list(parsed.unknown_offense_tokens),
            unknown_defense_tokens=list(parsed.unknown_defense_tokens),
            offense_slot_order_violations=list(parsed.offense_slot_order_violations),
            defense_slot_order_violations=list(parsed.defense_slot_order_violations),
        )

    @staticmethod
    def sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def validate_coordinates(
        self,
        coordinates: list[PlayerCoordinate],
        *,
        personnel: str | None = "11",
    ) -> CoordinateValidation:
        """Validate coordinate integrity without inventing football rules.

        This checks only structural requirements already implied by the stored
        geometry contract: 11 unique offensive players, finite SVG coordinates,
        positive radii when present, and one geometry/drawing source.
        """
        personnel_record = self.catalog.get("objects", {}).get("personnel", {}).get(personnel or "")
        eligible_players = (
            personnel_record.get("players", [])
            if isinstance(personnel_record, dict)
            else []
        )
        if not isinstance(eligible_players, list) or not all(
            isinstance(player, str) and player.strip() for player in eligible_players
        ):
            raise MarcusError(f"Personnel {personnel!r} has no valid player list")
        expected = {"LT", "LG", "C", "RG", "RT", "QB", *eligible_players}
        players = [item.player for item in coordinates]
        counts = {player: players.count(player) for player in set(players)}
        invalid_coordinates = sorted(
            item.player for item in coordinates
            if not math.isfinite(item.x) or not math.isfinite(item.y)
        )
        invalid_radii = sorted(
            item.player for item in coordinates
            if item.radius is not None and (not math.isfinite(item.radius) or item.radius <= 0)
        )
        by_position: dict[tuple[float, float], list[str]] = {}
        for item in coordinates:
            by_position.setdefault((item.x, item.y), []).append(item.player)
        duplicate_positions = [
            sorted(names) for names in by_position.values() if len(names) > 1
        ]
        geometry_ids = sorted({item.geometry_id for item in coordinates if item.geometry_id})
        drawing_ids = sorted({item.drawing_id for item in coordinates if item.drawing_id})
        missing = sorted(expected - set(players))
        unexpected = sorted(set(players) - expected)
        valid = (
            len(coordinates) == 11
            and len(counts) == 11
            and not missing
            and not unexpected
            and not duplicate_positions
            and not invalid_coordinates
            and not invalid_radii
            and len(geometry_ids) == 1
            and len(drawing_ids) == 1
        )
        return CoordinateValidation(
            valid=valid,
            player_count=len(coordinates),
            unique_player_count=len(counts),
            expected_players=sorted(expected),
            missing_players=missing,
            unexpected_players=unexpected,
            duplicate_positions=duplicate_positions,
            invalid_coordinates=invalid_coordinates,
            invalid_radii=invalid_radii,
            geometry_ids=geometry_ids,
            drawing_ids=drawing_ids,
        )

    def resolve_assignments(
        self,
        resolution: Resolution,
    ) -> dict[str, str]:
        """Return only explicitly stored player-to-assignment references.

        The compiler never synthesizes football assignments. A compiled call may
        provide an ``assignments`` mapping in the catalog. When it is absent,
        the result is intentionally empty and the assignment validator reports
        the play card as formation-only.
        """
        compiled = self.catalog.get("compiled_calls", {}).get(resolution.normalized_call, {})
        raw = compiled.get("assignments") if isinstance(compiled, dict) else None
        if not isinstance(raw, dict):
            return {}
        return {
            str(player): str(assignment_id)
            for player, assignment_id in raw.items()
            if isinstance(player, str) and isinstance(assignment_id, str)
        }

    def bind_assignments(
        self,
        coordinates: list[PlayerCoordinate],
        assignments: dict[str, str],
    ) -> list[AssignmentBinding]:
        """Bind validated canonical assignment objects to offensive players.

        This method never synthesizes football knowledge. It returns bindings
        only when the complete assignment map passes canonical object, approval,
        and player-eligibility validation.
        """
        validation = self.validate_assignments(coordinates, assignments)
        if not validation.valid:
            return []
        bindings: list[AssignmentBinding] = []
        for coordinate in coordinates:
            assignment_id = assignments[coordinate.player]
            obj = self.assignment_registry[assignment_id]
            bindings.append(AssignmentBinding(
                player=coordinate.player,
                assignment_id=obj.object_id,
                assignment_type=obj.assignment_type,
                canonical_name=obj.canonical_name,
                source_file=obj.file,
            ))
        return bindings

    def build_assignment_plan(
        self,
        coordinates: list[PlayerCoordinate],
        assignments: dict[str, str],
    ) -> list[PlayerAssignment]:
        """Build a deterministic 11-player plan using stored assignment objects only."""
        plan: list[PlayerAssignment] = []
        for coordinate in coordinates:
            assignment_id = assignments.get(coordinate.player)
            obj = self.assignment_registry.get(assignment_id) if assignment_id else None
            if obj is None:
                plan.append(PlayerAssignment(
                    player=coordinate.player,
                    assignment_id=assignment_id,
                    assignment_type=None,
                    canonical_name=None,
                    status="MISSING" if assignment_id is None else "UNKNOWN",
                    source_file=None,
                ))
            else:
                plan.append(PlayerAssignment(
                    player=coordinate.player,
                    assignment_id=obj.object_id,
                    assignment_type=obj.assignment_type,
                    canonical_name=obj.canonical_name,
                    status=obj.status,
                    source_file=obj.file,
                ))
        return plan

    def validate_assignments(
        self,
        coordinates: list[PlayerCoordinate],
        assignments: dict[str, str],
    ) -> AssignmentValidation:
        """Validate completeness and canonical assignment-object references."""
        expected = {coordinate.player for coordinate in coordinates}
        supplied = set(assignments)
        missing = sorted(expected - supplied)
        unexpected = sorted(supplied - expected)
        invalid_ids = sorted(
            player for player, assignment_id in assignments.items()
            if not isinstance(assignment_id, str) or not assignment_id.strip()
        )
        unknown_ids = sorted(
            player for player, assignment_id in assignments.items()
            if isinstance(assignment_id, str) and assignment_id.strip()
            and assignment_id not in self.assignment_registry
        )
        ineligible = sorted(
            player for player, assignment_id in assignments.items()
            if assignment_id in self.assignment_registry
            and self.assignment_registry[assignment_id].eligible_players
            and player not in self.assignment_registry[assignment_id].eligible_players
        )
        unapproved = sorted(
            player for player, assignment_id in assignments.items()
            if assignment_id in self.assignment_registry
            and self.assignment_registry[assignment_id].status not in {"CANONICAL", "COACH_APPROVED"}
        )
        blockers: list[dict[str, str]] = []
        if not assignments:
            blockers.append({
                "object": "offensive_assignments",
                "reason": "NO_APPROVED_ASSIGNMENT_OBJECTS_FOR_CALL",
            })
        for player in missing:
            blockers.append({"object": f"assignment:{player}", "reason": "MISSING"})
        for player in unexpected:
            blockers.append({"object": f"assignment:{player}", "reason": "UNEXPECTED_PLAYER"})
        for player in invalid_ids:
            blockers.append({"object": f"assignment:{player}", "reason": "INVALID_OBJECT_ID"})
        for player in unknown_ids:
            blockers.append({"object": f"assignment:{player}", "reason": "OBJECT_NOT_IN_DATABASE"})
        for player in ineligible:
            blockers.append({"object": f"assignment:{player}", "reason": "PLAYER_NOT_ELIGIBLE"})
        for player in unapproved:
            blockers.append({"object": f"assignment:{player}", "reason": "OBJECT_NOT_APPROVED"})
        invalid_players = set(invalid_ids) | set(unknown_ids) | set(ineligible) | set(unapproved)
        valid = not blockers and len(assignments) == len(expected)
        return AssignmentValidation(
            valid=valid,
            status="COMPLETE" if valid else "NOT_READY",
            player_count=len(expected),
            assigned_player_count=len((supplied & expected) - invalid_players),
            missing_players=missing,
            unexpected_players=unexpected,
            invalid_assignment_ids=invalid_ids,
            unknown_assignment_ids=unknown_ids,
            ineligible_assignments=sorted(set(ineligible + unapproved)),
            assignment_ids=dict(sorted(assignments.items())),
            blockers=blockers,
        )

    def compose_play_card(
        self,
        resolution: Resolution,
        coordinates: list[PlayerCoordinate],
        coordinate_validation: CoordinateValidation,
        assignment_plan: list[PlayerAssignment],
        assignment_validation: AssignmentValidation,
        assignment_bindings: list[AssignmentBinding],
    ) -> PlayCard:
        """Compose one immutable play-card object for validation and rendering."""
        if not resolution.renderable or not resolution.drawing_id:
            raise MarcusError("Cannot compose a play card from an unrenderable resolution")
        if not coordinate_validation.valid:
            raise MarcusError("Cannot compose a play card with invalid coordinates")
        coordinate_players = [item.player for item in coordinates]
        plan_players = [item.player for item in assignment_plan]
        if coordinate_players != plan_players:
            raise MarcusError("Assignment plan player order does not match coordinate order")
        binding_players = {item.player for item in assignment_bindings}
        if assignment_validation.valid and binding_players != set(coordinate_players):
            raise MarcusError("Complete assignments must bind all rendered players")
        if not assignment_validation.valid and assignment_bindings:
            raise MarcusError("Incomplete assignments cannot produce renderer bindings")
        return PlayCard(
            source_call=resolution.source_call,
            normalized_call=resolution.normalized_call,
            drawing_id=resolution.drawing_id,
            resolved_ids=dict(sorted(resolution.resolved_ids.items())),
            coordinates=tuple(coordinates),
            coordinate_validation=coordinate_validation,
            assignment_plan=tuple(assignment_plan),
            assignment_validation=assignment_validation,
            assignment_bindings=tuple(assignment_bindings),
            completeness=(
                "ASSIGNMENT_COMPLETE" if assignment_validation.valid else "FORMATION_ONLY"
            ),
        )

    def build_drawing_scene(self, play_card: PlayCard) -> DrawingScene:
        """Build one deterministic drawing scene from a validated PlayCard.

        Layer order is renderer structure, not football knowledge. Football
        geometry and assignments remain references to approved stored objects.
        """
        if not play_card.coordinate_validation.valid:
            raise MarcusError("Cannot build a drawing scene with invalid coordinates")
        if len(play_card.coordinates) != 11:
            raise MarcusError("Drawing scene requires exactly 11 offensive players")
        binding_players = {item.player for item in play_card.assignment_bindings}
        coordinate_players = {item.player for item in play_card.coordinates}
        if play_card.assignment_validation.valid and binding_players != coordinate_players:
            raise MarcusError("Complete assignment scene must bind all offensive players")
        if not play_card.assignment_validation.valid and binding_players:
            raise MarcusError("Formation-only scene cannot contain assignment bindings")

        layers = (
            DrawingLayer("field_template", 10, 1, "stored_svg_template"),
            DrawingLayer("defense", 20, 1, "stored_svg_template"),
            DrawingLayer("offense", 30, len(play_card.coordinates), "canonical_coordinates"),
            DrawingLayer(
                "assignments",
                40,
                len(play_card.assignment_bindings),
                "canonical_assignment_bindings",
            ),
            DrawingLayer("labels_metadata", 50, 1, "play_card"),
        )
        if [layer.order for layer in layers] != sorted(layer.order for layer in layers):
            raise MarcusError("Drawing scene layer order is invalid")
        return DrawingScene(
            drawing_id=play_card.drawing_id,
            normalized_call=play_card.normalized_call,
            layers=layers,
            expected_offensive_players=tuple(play_card.coordinate_validation.expected_players),
            offensive_players=play_card.coordinates,
            assignment_bindings=play_card.assignment_bindings,
            completeness=play_card.completeness,
        )

    def validate_drawing_scene(self, scene: DrawingScene) -> DrawingSceneValidation:
        """Validate the renderer scene contract without adding football rules."""
        expected_order = [
            "field_template",
            "defense",
            "offense",
            "assignments",
            "labels_metadata",
        ]
        actual_order = [layer.name for layer in scene.layers]
        duplicate_layers = sorted(
            name for name in set(actual_order) if actual_order.count(name) > 1
        )
        invalid_layer_orders = [
            layer.order
            for index, layer in enumerate(scene.layers)
            if index > 0 and layer.order <= scene.layers[index - 1].order
        ]
        invalid_object_counts = sorted(
            layer.name for layer in scene.layers if layer.object_count < 0
        )

        expected_players = set(scene.expected_offensive_players)
        players = [item.player for item in scene.offensive_players]
        binding_players = [item.player for item in scene.assignment_bindings]
        invalid_binding_players = sorted(
            player for player in binding_players if player not in expected_players
        )

        layer_counts = {layer.name: layer.object_count for layer in scene.layers}
        if layer_counts.get("offense") != len(scene.offensive_players):
            invalid_object_counts.append("offense")
        if layer_counts.get("assignments") != len(scene.assignment_bindings):
            invalid_object_counts.append("assignments")
        invalid_object_counts = sorted(set(invalid_object_counts))

        missing = sorted(expected_players - set(players))
        unexpected = sorted(set(players) - expected_players)
        valid = (
            actual_order == expected_order
            and not duplicate_layers
            and not invalid_layer_orders
            and not invalid_object_counts
            and len(players) == 11
            and len(set(players)) == 11
            and not missing
            and not unexpected
            and not invalid_binding_players
            and len(binding_players) == len(set(binding_players))
        )
        return DrawingSceneValidation(
            valid=valid,
            expected_layer_order=expected_order,
            actual_layer_order=actual_order,
            duplicate_layers=duplicate_layers,
            invalid_layer_orders=invalid_layer_orders,
            invalid_object_counts=invalid_object_counts,
            offensive_player_count=len(players),
            unique_offensive_player_count=len(set(players)),
            missing_offensive_players=missing,
            unexpected_offensive_players=unexpected,
            assignment_binding_count=len(binding_players),
            invalid_assignment_binding_players=invalid_binding_players,
        )

    def load_card_layout(self) -> CardLayout:
        path = self.root / "styles/card_layout.json"
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        sections = tuple(
            CardLayoutSection(
                name=item["name"],
                x=float(item["x"]),
                y=float(item["y"]),
                width=float(item["width"]),
                height=float(item["height"]),
                required=bool(item.get("required", True)),
            )
            for item in record.get("sections", [])
        )
        return CardLayout(
            layout_id=record["layout_id"],
            status=record["status"],
            canvas_width=float(record["canvas_width"]),
            canvas_height=float(record["canvas_height"]),
            sections=sections,
        )

    def validate_card_layout(self, layout: CardLayout) -> CardLayoutValidation:
        expected = ["title", "diagram", "notes", "validation", "metadata"]
        names = [section.name for section in layout.sections]
        missing = [name for name in expected if name not in names]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        out_of_bounds = []
        for section in layout.sections:
            if (section.x < 0 or section.y < 0 or section.width <= 0 or section.height <= 0
                    or section.x + section.width > layout.canvas_width
                    or section.y + section.height > layout.canvas_height):
                out_of_bounds.append(section.name)
        overlaps: list[list[str]] = []
        for index, first in enumerate(layout.sections):
            for second in layout.sections[index + 1:]:
                separated = (first.x + first.width <= second.x or second.x + second.width <= first.x
                             or first.y + first.height <= second.y or second.y + second.height <= first.y)
                if not separated:
                    overlaps.append(sorted([first.name, second.name]))
        valid = (layout.status == "APPROVED" and not missing and not duplicates
                 and not out_of_bounds and not overlaps and names == expected)
        return CardLayoutValidation(
            valid=valid, layout_id=layout.layout_id, expected_sections=expected,
            actual_sections=names, missing_sections=missing, duplicate_sections=duplicates,
            out_of_bounds_sections=out_of_bounds, overlapping_sections=overlaps,
        )

    def validate_output_integrity(
        self,
        manifest: dict[str, Any],
        card_directory: Path,
    ) -> OutputIntegrityValidation:
        """Verify card artifacts against their manifest without changing content."""
        outputs = manifest.get("outputs", {})
        if not isinstance(outputs, dict):
            raise MarcusError("Card manifest outputs must be an object")

        card_directory = card_directory.resolve()
        checked: list[str] = []
        missing: list[str] = []
        missing_hashes: list[str] = []
        mismatches: list[str] = []
        outside: list[str] = []

        for name, record in sorted(outputs.items()):
            if name == "output_integrity":
                continue
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                missing.append(name)
                continue
            path = Path(record["path"]).resolve()
            try:
                path.relative_to(card_directory)
            except ValueError:
                outside.append(name)
                continue
            if not path.is_file():
                missing.append(name)
                continue
            expected = record.get("sha256")
            if not isinstance(expected, str) or not expected:
                missing_hashes.append(name)
                continue
            checked.append(name)
            if self.sha256(path) != expected:
                mismatches.append(name)

        return OutputIntegrityValidation(
            valid=not (missing or missing_hashes or mismatches or outside),
            checked_outputs=checked,
            missing_outputs=missing,
            missing_hashes=missing_hashes,
            hash_mismatches=mismatches,
            paths_outside_card_directory=outside,
        )

    def audit_drawing_assets(self) -> DrawingAssetInventory:
        """Inventory every catalog drawing without silently upgrading approval.

        Approved drawings must have a complete reusable asset bundle. Drawings
        that still require coach approval remain visible as incomplete inventory
        entries, but they are not treated as certified football knowledge.
        """
        approved_statuses = {
            "CANONICAL",
            "COACH_APPROVED",
            "DERIVED_FROM_APPROVED_MIRROR",
            "SOURCE_TRACED_MOTION_COMPOSITE",
            "SOURCE_TRACED_COMPOSITE",
        }
        entries: list[DrawingAssetInventoryEntry] = []
        drawings = self.catalog.get("drawings", {})
        if not isinstance(drawings, dict):
            raise MarcusError("Catalog drawings must be an object")

        for drawing_id in sorted(drawings):
            validation = self.validate_asset_reuse(drawing_id)
            approved = validation.catalog_status in approved_statuses
            entries.append(DrawingAssetInventoryEntry(
                drawing_id=drawing_id,
                catalog_status=validation.catalog_status,
                approved=approved,
                reusable=validation.valid,
                asset_directory=validation.asset_directory,
                reused_files=validation.reused_files,
                source_hashes=validation.source_hashes,
                missing_files=validation.missing_files,
                invalid_paths=validation.invalid_paths,
            ))

        approved_entries = [entry for entry in entries if entry.approved]
        reusable_entries = [entry for entry in entries if entry.reusable]
        incomplete_entries = [entry for entry in entries if not entry.reusable]
        approved_incomplete = [
            entry for entry in entries if entry.approved and not entry.reusable
        ]
        return DrawingAssetInventory(
            schema="marcus-cad.drawing-asset-inventory.v1",
            drawing_count=len(entries),
            approved_count=len(approved_entries),
            reusable_count=len(reusable_entries),
            approved_reusable_count=sum(
                1 for entry in approved_entries if entry.reusable
            ),
            incomplete_count=len(incomplete_entries),
            approved_incomplete_count=len(approved_incomplete),
            entries=tuple(entries),
        )


    def validate_asset_reuse(self, drawing_id: str) -> AssetReuseValidation:
        """Validate and fingerprint the approved stored drawing asset bundle.

        The compiler must reuse existing drawing assets rather than recreate
        formation, motion, or defensive templates. This validation is strictly
        structural: it checks the catalog link and the four stored asset files.
        """
        drawing = self.catalog.get("drawings", {}).get(drawing_id)
        if not isinstance(drawing, dict):
            raise MarcusError(f"Drawing is not registered in the catalog: {drawing_id}")

        expected = {
            "svg": drawing.get("svg"),
            "png": drawing.get("png"),
            "metadata": f"artifacts/drawings/{drawing_id}/metadata.json",
        }
        coordinate_relative = f"artifacts/drawings/{drawing_id}/coordinates.json"
        if (self.root / coordinate_relative).is_file():
            expected["coordinates"] = coordinate_relative
        reused: dict[str, str] = {}
        hashes: dict[str, str] = {}
        missing: list[str] = []
        invalid: list[str] = []
        asset_dir = (self.root / "artifacts" / "drawings" / drawing_id).resolve()

        for name, relative in expected.items():
            if not isinstance(relative, str) or not relative.strip():
                missing.append(name)
                continue
            path = (self.root / relative).resolve()
            try:
                path.relative_to(asset_dir)
            except ValueError:
                invalid.append(name)
                continue
            reused[name] = str(path.relative_to(self.root))
            if not path.is_file():
                missing.append(name)
                continue
            hashes[name] = self.sha256(path)

        return AssetReuseValidation(
            valid=not missing and not invalid and len(hashes) == len(expected),
            drawing_id=drawing_id,
            catalog_status=str(drawing.get("status", "UNKNOWN")),
            asset_directory=str(asset_dir.relative_to(self.root)),
            reused_files=dict(sorted(reused.items())),
            source_hashes=dict(sorted(hashes.items())),
            missing_files=sorted(missing),
            invalid_paths=sorted(invalid),
        )


    def draw(
        self,
        call: str,
        out_dir: Path,
        *,
        card_type: str = "SCOUT_CARD",
        require_assignments: bool = False,
    ) -> dict[str, Any]:
        card_type = self.normalize_card_type(card_type)
        result = self.parse(call, card_type=card_type)
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "validation.json"
        report_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        parsed_call = self.parser.parse(call)
        call_slot_report = self.build_call_slot_report(parsed_call, card_type=card_type)
        call_slot_report_path = out_dir / "call_slots.json"
        call_slot_report_path.write_text(
            json.dumps(asdict(call_slot_report), indent=2),
            encoding="utf-8",
        )
        database_resolution_path = out_dir / "database_resolution.json"
        database_resolution_path.write_text(
            json.dumps({
                "resolved_ids": result.resolved_ids,
                "resolved_sources": result.resolved_sources,
                "catalog_integration": self.database_index.report(self.catalog),
            }, indent=2),
            encoding="utf-8",
        )
        database_resolution_validation = self.database_index.validate_resolution(
            result.resolved_ids,
            result.resolved_sources,
        )
        database_resolution_validation_path = out_dir / "database_resolution_validation.json"
        database_resolution_validation_path.write_text(
            json.dumps(database_resolution_validation, indent=2),
            encoding="utf-8",
        )
        if not database_resolution_validation["valid"]:
            raise MarcusError(
                "Database resolution source validation failed: "
                + json.dumps(database_resolution_validation, sort_keys=True)
            )

        if not result.renderable or not result.drawing_id:
            raise MarcusError(
                "Call is not renderable from approved stored geometry. "
                f"See {report_path} for exact blockers."
            )

        drawing = self.catalog["drawings"][result.drawing_id]
        asset_reuse_validation = self.validate_asset_reuse(result.drawing_id)
        if not asset_reuse_validation.valid:
            raise MarcusError(
                "Approved drawing asset reuse validation failed: "
                + json.dumps(asdict(asset_reuse_validation), sort_keys=True)
            )
        asset_reuse_path = out_dir / "asset_reuse.json"
        asset_reuse_path.write_text(
            json.dumps(asdict(asset_reuse_validation), indent=2),
            encoding="utf-8",
        )
        svg_src = self.root / drawing["svg"]
        png_src = self.root / drawing["png"]
        svg_out = out_dir / "card.svg"
        png_out = out_dir / "card.png"
        formation_id = result.resolved_ids.get("formations")
        if not formation_id:
            raise MarcusError("Renderable call has no canonical formation id")
        try:
            coordinates = self.generate_coordinates(
                formation_id,
                personnel=result.personnel,
                field_location=result.field_location,
                variation=result.variation,
                motion=result.motion,
            )
            coordinate_validation = self.validate_coordinates(coordinates, personnel=result.personnel)
            if not coordinate_validation.valid:
                raise MarcusError(
                    "Canonical coordinate validation failed: "
                    + json.dumps(asdict(coordinate_validation), sort_keys=True)
                )
            assignments = self.resolve_assignments(result)
            assignment_plan = self.build_assignment_plan(coordinates, assignments)
            assignment_validation = self.validate_assignments(coordinates, assignments)
            assignment_bindings = self.bind_assignments(coordinates, assignments)
            play_card = self.compose_play_card(
                result,
                coordinates,
                coordinate_validation,
                assignment_plan,
                assignment_validation,
                assignment_bindings,
            )
            drawing_scene = self.build_drawing_scene(play_card)
            drawing_scene_validation = self.validate_drawing_scene(drawing_scene)
            if not drawing_scene_validation.valid:
                raise MarcusError(
                    "Drawing scene validation failed: "
                    + json.dumps(asdict(drawing_scene_validation), sort_keys=True)
                )
            card_layout = self.load_card_layout()
            card_layout_validation = self.validate_card_layout(card_layout)
            if not card_layout_validation.valid:
                raise MarcusError(
                    "Card layout validation failed: "
                    + json.dumps(asdict(card_layout_validation), sort_keys=True)
                )
            render_svg_from_scene(
                svg_src,
                svg_out,
                DrawingSceneRenderInput(
                    drawing_id=drawing_scene.drawing_id,
                    normalized_call=drawing_scene.normalized_call,
                    layer_order=tuple(layer.name for layer in drawing_scene.layers),
                    layout_id=card_layout.layout_id,
                    layout_sections=tuple(section.name for section in card_layout.sections),
                    coordinates=tuple(
                        RenderCoordinate(c.player, c.x, c.y, c.radius)
                        for c in drawing_scene.offensive_players
                    ),
                    assignment_bindings={
                        item.player: RenderAssignmentBinding(
                            player=item.player,
                            assignment_id=item.assignment_id,
                            assignment_type=item.assignment_type,
                            canonical_name=item.canonical_name,
                        )
                        for item in drawing_scene.assignment_bindings
                    },
                ),
            )
        except RendererError as exc:
            raise MarcusError(f"Coordinate-driven SVG render failed: {exc}") from exc

        try:
            import cairosvg
            cairosvg.svg2png(url=str(svg_out), write_to=str(png_out))
            pdf_out = out_dir / "card.pdf"
            cairosvg.svg2pdf(url=str(svg_out), write_to=str(pdf_out))
        except Exception as exc:
            raise MarcusError(f"SVG created, but PNG/PDF export failed: {exc}") from exc

        validation_payload = asdict(result)
        validation_payload["call_slot_report"] = asdict(call_slot_report)
        validation_payload["coordinate_validation"] = asdict(coordinate_validation)
        validation_payload["assignment_validation"] = asdict(assignment_validation)
        validation_payload["assignment_plan"] = [asdict(item) for item in assignment_plan]
        validation_payload["assignment_bindings"] = [asdict(item) for item in assignment_bindings]
        validation_payload["drawing_scene_validation"] = asdict(drawing_scene_validation)
        validation_payload["card_layout_validation"] = asdict(card_layout_validation)
        validation_payload["asset_reuse_validation"] = asdict(asset_reuse_validation)
        report_path.write_text(json.dumps(validation_payload, indent=2), encoding="utf-8")

        if require_assignments and not assignment_validation.valid:
            raise MarcusError(
                "Approved assignment validation failed. "
                f"See {report_path} for exact blockers."
            )

        assignment_bindings_path = out_dir / "assignment_bindings.json"
        assignment_bindings_path.write_text(
            json.dumps([asdict(item) for item in assignment_bindings], indent=2),
            encoding="utf-8",
        )

        assignment_plan_path = out_dir / "assignment_plan.json"
        assignment_plan_path.write_text(
            json.dumps([asdict(item) for item in assignment_plan], indent=2),
            encoding="utf-8",
        )

        play_card_path = out_dir / "play_card.json"
        play_card_path.write_text(
            json.dumps(asdict(play_card), indent=2),
            encoding="utf-8",
        )

        drawing_scene_path = out_dir / "drawing_scene.json"
        drawing_scene_path.write_text(
            json.dumps(asdict(drawing_scene), indent=2),
            encoding="utf-8",
        )

        drawing_scene_validation_path = out_dir / "drawing_scene_validation.json"
        drawing_scene_validation_path.write_text(
            json.dumps(asdict(drawing_scene_validation), indent=2),
            encoding="utf-8",
        )

        card_layout_path = out_dir / "card_layout.json"
        card_layout_path.write_text(json.dumps(asdict(card_layout), indent=2), encoding="utf-8")
        card_layout_validation_path = out_dir / "card_layout_validation.json"
        card_layout_validation_path.write_text(
            json.dumps(asdict(card_layout_validation), indent=2), encoding="utf-8"
        )

        manifest = {
            "card_type": card_type,
            "source_call": call,
            "drawing_id": result.drawing_id,
            "call_slot_report": asdict(call_slot_report),
            "renderer": "DRAWING_SCENE_DRIVEN",
            "asset_reuse": asdict(asset_reuse_validation),
            "drawing_scene_layers": [asdict(layer) for layer in drawing_scene.layers],
            "drawing_scene_validation": asdict(drawing_scene_validation),
            "card_layout_id": card_layout.layout_id,
            "card_layout_validation": asdict(card_layout_validation),
            "coordinate_count": len(coordinates),
            "coordinate_validation": asdict(coordinate_validation),
            "assignment_validation": asdict(assignment_validation),
            "assignment_plan": [asdict(item) for item in assignment_plan],
            "assignment_bindings": [asdict(item) for item in assignment_bindings],
            "card_completeness": play_card.completeness,
            "outputs": {
                "asset_reuse": {"path": str(asset_reuse_path), "sha256": self.sha256(asset_reuse_path)},
                "call_slots": {"path": str(call_slot_report_path), "sha256": self.sha256(call_slot_report_path)},
                "svg": {"path": str(svg_out), "sha256": self.sha256(svg_out)},
                "png": {"path": str(png_out), "sha256": self.sha256(png_out)},
                "pdf": {"path": str(pdf_out), "sha256": self.sha256(pdf_out)},
                "validation": {"path": str(report_path), "sha256": self.sha256(report_path)},
                "database_resolution": {"path": str(database_resolution_path), "sha256": self.sha256(database_resolution_path)},
                "database_resolution_validation": {
                    "path": str(database_resolution_validation_path),
                    "sha256": self.sha256(database_resolution_validation_path),
                },
                "assignment_plan": {"path": str(assignment_plan_path), "sha256": self.sha256(assignment_plan_path)},
                "assignment_bindings": {"path": str(assignment_bindings_path), "sha256": self.sha256(assignment_bindings_path)},
                "play_card": {"path": str(play_card_path), "sha256": self.sha256(play_card_path)},
                "drawing_scene": {"path": str(drawing_scene_path), "sha256": self.sha256(drawing_scene_path)},
                "drawing_scene_validation": {
                    "path": str(drawing_scene_validation_path),
                    "sha256": self.sha256(drawing_scene_validation_path),
                },
                "card_layout": {"path": str(card_layout_path), "sha256": self.sha256(card_layout_path)},
                "card_layout_validation": {
                    "path": str(card_layout_validation_path),
                    "sha256": self.sha256(card_layout_validation_path),
                },
            },
        }
        output_integrity = self.validate_output_integrity(manifest, out_dir)
        if not output_integrity.valid:
            raise MarcusError(
                "Card output integrity validation failed: "
                + json.dumps(asdict(output_integrity), sort_keys=True)
            )
        output_integrity_path = out_dir / "output_integrity.json"
        output_integrity_path.write_text(
            json.dumps(asdict(output_integrity), indent=2),
            encoding="utf-8",
        )
        manifest["output_integrity"] = asdict(output_integrity)
        manifest["outputs"]["output_integrity"] = {
            "path": str(output_integrity_path),
            "sha256": self.sha256(output_integrity_path),
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def compile_report(self, call: str, output: Path) -> Resolution:
        result = self.parse(call)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        return result


    def _load_geometry_index(self) -> dict[str, dict[str, Any]]:
        registry_path = self.root / "database/offense/formation_geometry_registry.json"
        with registry_path.open("r", encoding="utf-8") as f:
            registry = json.load(f)
        index: dict[str, dict[str, Any]] = {}
        for item in registry.get("geometry_objects", []):
            drawing_id = item.get("drawing_id")
            file_path = item.get("file")
            if not isinstance(drawing_id, str) or not isinstance(file_path, str):
                continue
            if drawing_id in index:
                raise MarcusError(f"Duplicate geometry for drawing {drawing_id}")
            index[drawing_id] = item
        return index

    def _drawing_for_coordinates(
        self,
        formation_id: str,
        *,
        personnel: str | None = "11",
        field_location: str | None = None,
        variation: str | None = None,
        motion: str | None = None,
    ) -> str:
        formation = self.registry.by_id(formation_id)
        if formation is None or formation.category != "formations":
            raise MarcusError(f"Unknown formation id: {formation_id}")

        variants = formation.record.get("resolved_variants", {})
        if not isinstance(variants, dict):
            raise MarcusError(f"Formation {formation_id} has invalid resolved_variants")

        if variation or motion:
            candidate_keys: list[str] = []
            with_location = [part for part in (personnel, field_location, variation, motion) if part]
            without_location = [part for part in (personnel, variation, motion) if part]
            for parts in (with_location, without_location):
                key = "|".join(parts)
                if key and key not in candidate_keys:
                    candidate_keys.append(key)
            for variant_key in candidate_keys:
                variant = variants.get(variant_key)
                if isinstance(variant, dict) and isinstance(variant.get("drawing_id"), str):
                    return variant["drawing_id"]
            raise MarcusError(
                f"No approved geometry variant for {formation_id}: "
                + ", ".join(candidate_keys)
            )

        # Canonical formation records may directly identify their approved base
        # drawing. Prefer that explicit link for a bare formation call before
        # consulting optional variant relationships.
        direct_drawing_id = formation.record.get("drawing_id")
        if isinstance(direct_drawing_id, str) and direct_drawing_id:
            return direct_drawing_id

        # Otherwise, a bare formation ID resolves to its base, non-motion variant.
        # This is deterministic and uses only explicitly stored variant relationships.
        candidates: list[tuple[str, str]] = []
        for key, variant in variants.items():
            if not isinstance(key, str) or not isinstance(variant, dict):
                continue
            parts = key.split("|")
            if personnel and (not parts or parts[0] != personnel):
                continue
            if len(parts) > 2:  # motion/composite variant, not base geometry
                continue
            drawing_id = variant.get("drawing_id")
            if isinstance(drawing_id, str):
                candidates.append((key, drawing_id))
        if len(candidates) != 1:
            choices = ", ".join(key for key, _ in sorted(candidates)) or "none"
            raise MarcusError(
                f"Formation {formation_id} does not have one unambiguous base geometry; "
                f"candidates: {choices}"
            )
        return candidates[0][1]

    @staticmethod
    def _field_location_anchors(svg_path: Path) -> dict[str, float]:
        """Read exact location anchors from approved field SVG landmarks."""
        tree = ET.parse(svg_path)
        root = tree.getroot()
        view_box = root.attrib.get("viewBox", "").split()
        if len(view_box) == 4:
            width = float(view_box[2])
        elif "width" in root.attrib:
            width = float(root.attrib["width"])
        else:
            raise MarcusError(f"SVG has no usable width: {svg_path}")
        center = width / 2.0
        clusters: dict[float, int] = {}
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] != "line":
                continue
            if not {"x1", "x2", "y1", "y2"}.issubset(element.attrib):
                continue
            x1 = float(element.attrib["x1"]); x2 = float(element.attrib["x2"])
            y1 = float(element.attrib["y1"]); y2 = float(element.attrib["y2"])
            length = abs(x2 - x1)
            if abs(y2 - y1) > 0.01 or not (8.0 <= length <= 30.0):
                continue
            x_center = round((x1 + x2) / 2.0, 3)
            if not (width * 0.20 < x_center < width * 0.80):
                continue
            clusters[x_center] = clusters.get(x_center, 0) + 1
        repeated = sorted(x for x, count in clusters.items() if count >= 5)
        left = [x for x in repeated if x < center]
        right = [x for x in repeated if x > center]
        if not left or not right:
            raise MarcusError(f"Could not resolve hash landmarks from {svg_path}")
        left_hash = max(left); right_hash = min(right)
        return {
            "LH": left_hash,
            "LM": (left_hash + center) / 2.0,
            "M": center,
            "RM": (center + right_hash) / 2.0,
            "RH": right_hash,
        }

    def generate_coordinates(
        self,
        formation_id: str,
        *,
        personnel: str | None = "11",
        field_location: str | None = None,
        variation: str | None = None,
        motion: str | None = None,
    ) -> list[PlayerCoordinate]:
        """Load approved player coordinates from canonical formation geometry.

        No coordinates are synthesized. The formation ID is resolved through the
        canonical catalog, then linked to a stored drawing and geometry object.
        """
        drawing_id = self._drawing_for_coordinates(
            formation_id, personnel=personnel, field_location=field_location,
            variation=variation, motion=motion
        )
        geometry_item = self._load_geometry_index().get(drawing_id)
        if geometry_item is None:
            raise MarcusError(f"No stored geometry object for drawing {drawing_id}")
        geometry_path = self.root / geometry_item["file"]
        with geometry_path.open("r", encoding="utf-8") as f:
            geometry = json.load(f)

        players = geometry.get("players")
        if not isinstance(players, list):
            raise MarcusError(f"Geometry {geometry_item.get('geometry_id')} has no players list")
        if geometry.get("player_count") != len(players):
            raise MarcusError(
                f"Geometry {geometry_item.get('geometry_id')} player_count mismatch"
            )
        if len(players) != 11:
            raise MarcusError(
                f"Geometry {geometry_item.get('geometry_id')} is not a complete 11-player formation"
            )

        coordinates: list[PlayerCoordinate] = []
        seen: set[str] = set()
        geometry_id = str(geometry.get("object_id") or geometry_item.get("geometry_id"))
        for record in players:
            if not isinstance(record, dict):
                raise MarcusError(f"Geometry {geometry_id} contains an invalid player record")
            raw_label = record.get("label")
            x = record.get("svg_x")
            y = record.get("svg_y")
            if not isinstance(raw_label, str) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise MarcusError(f"Geometry {geometry_id} contains incomplete coordinates")
            player = "QB" if raw_label == "Q" else raw_label
            if player in seen:
                raise MarcusError(f"Geometry {geometry_id} duplicates player {player}")
            seen.add(player)
            radius = record.get("radius", record.get("radius_or_half_size"))
            coordinates.append(
                PlayerCoordinate(
                    player=player,
                    x=float(x),
                    y=float(y),
                    radius=float(radius) if isinstance(radius, (int, float)) else None,
                    los_status=str(record["los_status"]) if record.get("los_status") is not None else None,
                    geometry_id=geometry_id,
                    drawing_id=drawing_id,
                )
            )

        if field_location:
            svg_reference = geometry.get("source_svg") or geometry_item.get("source_svg")
            svg_path = self.root / str(svg_reference or "")
            if not svg_path.is_file():
                raise MarcusError(f"Stored field SVG not found for location placement: {svg_path}")
            anchors = self._field_location_anchors(svg_path)
            if field_location not in anchors:
                raise MarcusError(f"Unsupported field location: {field_location}")
            center_player = next((item for item in coordinates if item.player == "C"), None)
            if center_player is None:
                raise MarcusError(f"Geometry {geometry_id} has no Center for field-location placement")
            dx = anchors[field_location] - center_player.x
            coordinates = [
                PlayerCoordinate(
                    player=item.player,
                    x=item.x + dx,
                    y=item.y,
                    radius=item.radius,
                    los_status=item.los_status,
                    geometry_id=item.geometry_id,
                    drawing_id=item.drawing_id,
                )
                for item in coordinates
            ]
        return coordinates
