from __future__ import annotations

import re
from typing import Optional

from app.models.question import UserAnswer

_WEIGHT_UNIT_ALIASES = {
    "kg": {"kg", "kgs", "kilogram", "kilograms"},
    "lb": {"lb", "lbs", "pound", "pounds"},
    "oz": {"oz", "ounce", "ounces"},
    "stone": {"stone", "stones", "st"},
}

_HEIGHT_UNIT_ALIASES = {
    "cm": {"cm", "centimeter", "centimeters"},
    "m": {"m", "meter", "meters"},
    "ft": {"ft", "foot", "feet"},
    "in": {"in", "inch", "inches"},
}

_NUMERIC_REGEX = re.compile(r"-?\d+(?:\.\d+)?")


def parse_numeric_value(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    match = _NUMERIC_REGEX.search(raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_unit(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    normalized = raw.strip().lower()
    return normalized or None


def _map_unit(value: Optional[str], mapping: dict[str, set[str]]) -> Optional[str]:
    if not value:
        return None
    for canonical, aliases in mapping.items():
        if value == canonical or value in aliases:
            return canonical
    return None


def resolve_weight_unit(answer: UserAnswer) -> Optional[str]:
    for selection in answer.selected_options or []:
        if not selection.option:
            continue
        for source in (selection.option.value, selection.option.option_text):
            normalized = normalize_unit(source)
            resolved = _map_unit(normalized, _WEIGHT_UNIT_ALIASES)
            if resolved:
                return resolved
    return None


def resolve_height_unit(answer: UserAnswer) -> Optional[str]:
    for selection in answer.selected_options or []:
        if not selection.option:
            continue
        for source in (selection.option.value, selection.option.option_text):
            normalized = normalize_unit(source)
            resolved = _map_unit(normalized, _HEIGHT_UNIT_ALIASES)
            if resolved:
                return resolved
    return None


def convert_weight_to_kg(value: float, unit: Optional[str]) -> Optional[float]:
    if value < 0:
        return None
    if unit == "lb":
        return value * 0.45359237
    if unit == "oz":
        return value * 0.0283495
    if unit == "stone":
        return value * 6.35029318
    return value


def convert_height_to_m(value: float, unit: Optional[str]) -> Optional[float]:
    if value < 0:
        return None
    if unit == "cm":
        return value / 100
    if unit == "ft":
        return value * 0.3048
    if unit == "in":
        return value * 0.0254
    return value


def weight_kg_from_answer(answer: UserAnswer) -> Optional[float]:
    raw_value = parse_numeric_value(answer.answer_text)
    if raw_value is None:
        return None
    unit = resolve_weight_unit(answer)
    return convert_weight_to_kg(raw_value, unit)
