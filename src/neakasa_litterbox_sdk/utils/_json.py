"""Typed JSON aliases and safe accessors for Neakasa responses."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | Sequence[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]


def loads(payload: bytes | str) -> JsonObject:
    """Parse a JSON object response, rejecting non-object top levels."""
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("Failed to parse JSON: top level is not an object")
    return cast("JsonObject", parsed)


def get_str(data: JsonObject, key: str, default: str = "") -> str:
    """Return ``data[key]`` if it is a string, else ``default``."""
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def get_int(data: JsonObject, key: str, default: int = 0) -> int:
    """Return ``data[key]`` coerced to int, falling back to ``default``."""
    value = data.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def get_float(data: JsonObject, key: str, default: float = 0.0) -> float:
    """Return ``data[key]`` coerced to float, falling back to ``default``."""
    value = data.get(key, default)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def get_object(data: JsonObject, key: str) -> JsonObject:
    """Return ``data[key]`` as a JSON object, or an empty mapping."""
    value = data.get(key)
    return value if isinstance(value, Mapping) else {}
