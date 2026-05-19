"""A cat registered against a Neakasa M1 litter box."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from ..utils._json import get_float, get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


class CatGender(IntEnum):
    """Gender values used by the Neakasa cat profile.

    The app surfaces ``1`` and ``2``; ``0`` is reserved for "not set".
    """

    UNKNOWN = 0
    MALE = 1
    FEMALE = 2

    @classmethod
    def from_int(cls, value: int) -> CatGender:
        """Return the matching enum member, defaulting to ``UNKNOWN``."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class Cat:
    """One cat profile from ``GET /api/catbox/cat/list``."""

    id: int
    name: str
    weight: float
    unit: str
    avatar: str
    birthday: str
    variety: int
    gender: CatGender
    sterilization: int
    enabled: int
    path: str

    @property
    def is_sterilized(self) -> bool:
        """``True`` when ``sterilization`` is the documented 'yes' value (``1``)."""
        return self.sterilization == 1

    @property
    def is_enabled(self) -> bool:
        """``True`` when this cat profile is currently active on the device."""
        return self.enabled == 1

    @classmethod
    def from_json(cls, raw: JsonObject) -> Cat:
        """Build a ``Cat`` from one element of the response array."""
        return cls(
            id=get_int(raw, "id"),
            name=get_str(raw, "name"),
            weight=get_float(raw, "weight"),
            unit=get_str(raw, "unit"),
            avatar=get_str(raw, "avatar"),
            birthday=get_str(raw, "birthday"),
            variety=get_int(raw, "variety", default=-1),
            gender=CatGender.from_int(get_int(raw, "gender")),
            sterilization=get_int(raw, "sterilization"),
            enabled=get_int(raw, "enabled"),
            path=get_str(raw, "path"),
        )

    @staticmethod
    def list_from_response(data: JsonValue) -> list[Cat]:
        """Parse the top-level array returned by the cat-list endpoint."""
        if not isinstance(data, Sequence) or isinstance(data, str):
            return []
        return [Cat.from_json(item) for item in data if isinstance(item, Mapping)]
