from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ParsedCall:
    normalized_call: str
    offense_text: str
    defense_text: str
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
    # Backward-compatible names retained while callers migrate.
    defensive_personnel: str | None
    defensive_structure: str | None
    unknown_offense_tokens: tuple[str, ...]
    unknown_defense_tokens: tuple[str, ...]
    offense_slot_order_violations: tuple[str, ...]
    defense_slot_order_violations: tuple[str, ...]


class CatalogDrivenParser:
    """Deterministic longest-match parser backed by the canonical catalog.

    Canonical call order approved by the Chief Engineer:

    Offense: personnel, backfield, formation, variation, motion, shift, protection, play, tag.
    Required slots depend on card type; the parser preserves the canonical full order.

    Defense: structure, front, game, pressure, blitz, coverage.
    Required defense slots: structure, coverage.

    Field location is parsed as card context and is not one of the numbered
    offensive-call slots.
    """

    ALIASES = {
        "DOUBLES": "DBLS",
        "COVER": "COV",
        "MIDDLE": "M",
        "LEFT HASH": "LH",
        "RIGHT HASH": "RH",
        "RIGHT": "RT",
        "LEFT": "LT",
    }

    OFFENSE_SLOT_CATEGORIES = (
        ("personnel", "personnel"),
        ("backfield", "backfields"),
        ("formation", "formations"),
        ("variation", "variations"),
        ("motion", "motions"),
        ("shift", "shifts"),
        ("protection", "protections"),
        ("play", "plays"),
        ("tag", "tags"),
    )
    DEFENSE_SLOT_CATEGORIES = (
        # Existing v2.3.0 catalog names are retained as storage categories:
        # defensive_personnel stores STRUCTURE (e.g. 4-2), and
        # defensive_structures stores FRONT (e.g. STUD).
        ("structure", "defensive_personnel"),
        ("front", "defensive_structures"),
        ("game", "defensive_games"),
        ("pressure", "defensive_pressures"),
        ("blitz", "defensive_blitzes"),
        ("coverage", "coverages"),
    )

    def __init__(self, catalog: dict[str, Any]):
        self.catalog = catalog
        self.objects = catalog.get("objects", {})

    @classmethod
    def normalize(cls, text: str) -> str:
        value = text.upper().strip()
        value = value.replace("–", "-").replace("—", "-")
        value = re.sub(r"\s+", " ", value)
        for source, target in sorted(cls.ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            value = re.sub(rf"(?<![A-Z0-9]){re.escape(source)}(?![A-Z0-9])", target, value)
        value = re.sub(r"\(\s*(\d{2})\s*\)", r"(\1)", value)
        return value

    @staticmethod
    def _contains(text: str, phrase: str) -> bool:
        return bool(re.search(rf"(?<![A-Z0-9]){re.escape(phrase)}(?![A-Z0-9])", text))

    def _longest(self, category: str, text: str) -> str | None:
        match = self._longest_with_span(category, text)
        return match[0] if match else None

    def _longest_with_span(self, category: str, text: str) -> tuple[str, int, int] | None:
        keys: Iterable[str] = self.objects.get(category, {}).keys()
        matches: list[tuple[str, int, int]] = []
        for key in keys:
            found = re.search(rf"(?<![A-Z0-9]){re.escape(key)}(?![A-Z0-9])", text)
            if found:
                matches.append((key, found.start(), found.end()))
        return max(
            matches,
            key=lambda item: (len(item[0].split()), len(item[0]), item[0]),
            default=None,
        )

    @staticmethod
    def _order_violations(
        ordered_slots: tuple[tuple[str, str], ...],
        matches: dict[str, tuple[str, int, int] | None],
    ) -> tuple[str, ...]:
        present = [
            (name, match[1])
            for name, _ in ordered_slots
            if (match := matches.get(name)) is not None
        ]
        violations: list[str] = []
        previous_name: str | None = None
        previous_start = -1
        for name, start in present:
            if start < previous_start and previous_name is not None:
                violations.append(f"{name}_before_{previous_name}")
            if start >= previous_start:
                previous_name = name
                previous_start = start
        return tuple(violations)

    @staticmethod
    def _remove_phrase(text: str, phrase: str | None) -> str:
        if not phrase:
            return text
        return re.sub(rf"(?<![A-Z0-9]){re.escape(phrase)}(?![A-Z0-9])", " ", text, count=1)

    @staticmethod
    def _residue(text: str) -> tuple[str, ...]:
        text = re.sub(r"\(\d{2}\)", " ", text)
        text = re.sub(r"[^A-Z0-9-]+", " ", text)
        return tuple(token for token in text.split() if token)

    def parse(self, call: str) -> ParsedCall:
        normalized = self.normalize(call)
        offense, separator, defense = normalized.partition(" VS ")
        defense = defense if separator else ""

        field_location = self._longest("field_locations", offense)
        personnel_match = re.search(r"\((\d{2})\)", offense)
        personnel_catalog_match = self._longest_with_span("personnel", offense)
        personnel = personnel_match.group(1) if personnel_match else (
            personnel_catalog_match[0] if personnel_catalog_match else None
        )

        offense_matches: dict[str, tuple[str, int, int] | None] = {}
        for name, category in self.OFFENSE_SLOT_CATEGORIES:
            if name == "personnel":
                if personnel_match:
                    offense_matches[name] = (
                        personnel,
                        personnel_match.start(),
                        personnel_match.end(),
                    )
                else:
                    offense_matches[name] = personnel_catalog_match
            else:
                offense_matches[name] = self._longest_with_span(category, offense)
        defense_matches = {
            name: self._longest_with_span(category, defense)
            for name, category in self.DEFENSE_SLOT_CATEGORIES
        }

        offense_slots = {
            name: (match[0] if match else None)
            for name, match in offense_matches.items()
        }
        defense_slots = {
            name: (match[0] if match else None)
            for name, match in defense_matches.items()
        }
        offense_order_violations = self._order_violations(
            self.OFFENSE_SLOT_CATEGORIES,
            offense_matches,
        )
        defense_order_violations = self._order_violations(
            self.DEFENSE_SLOT_CATEGORIES,
            defense_matches,
        )

        offense_residue = offense
        for phrase in (field_location,) + tuple(
            offense_slots[name] for name, _ in self.OFFENSE_SLOT_CATEGORIES if name != "personnel"
        ):
            offense_residue = self._remove_phrase(offense_residue, phrase)
        if personnel:
            offense_residue = re.sub(rf"\(?{re.escape(personnel)}\)?", " ", offense_residue, count=1)

        defense_residue = defense
        for name, _ in self.DEFENSE_SLOT_CATEGORIES:
            defense_residue = self._remove_phrase(defense_residue, defense_slots[name])

        return ParsedCall(
            normalized_call=normalized,
            offense_text=offense.strip(),
            defense_text=defense.strip(),
            field_location=field_location,
            personnel=offense_slots["personnel"],
            backfield=offense_slots["backfield"],
            formation=offense_slots["formation"],
            variation=offense_slots["variation"],
            motion=offense_slots["motion"],
            shift=offense_slots["shift"],
            protection=offense_slots["protection"],
            play=offense_slots["play"],
            tag=offense_slots["tag"],
            structure=defense_slots["structure"],
            front=defense_slots["front"],
            game=defense_slots["game"],
            pressure=defense_slots["pressure"],
            blitz=defense_slots["blitz"],
            coverage=defense_slots["coverage"],
            defensive_personnel=defense_slots["structure"],
            defensive_structure=defense_slots["front"],
            unknown_offense_tokens=self._residue(offense_residue),
            unknown_defense_tokens=self._residue(defense_residue),
            offense_slot_order_violations=offense_order_violations,
            defense_slot_order_violations=defense_order_violations,
        )
