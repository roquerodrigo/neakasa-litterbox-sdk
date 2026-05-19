"""One day's aggregate usage of the litter box."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils._json import get_float, get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class DailyStatistics:
    """One bucket of ``GET /api/catbox/toilet/statistics``."""

    date: str
    num: int
    weight: float
    unit: str
    toilet_total_second: int
    weight_avg: float

    @classmethod
    def from_json(cls, raw: JsonObject) -> DailyStatistics:
        """Build a ``DailyStatistics`` from one element of the response array."""
        return cls(
            date=get_str(raw, "date"),
            num=get_int(raw, "num"),
            weight=get_float(raw, "weight"),
            unit=get_str(raw, "unit"),
            toilet_total_second=get_int(raw, "toilet_total_second"),
            weight_avg=get_float(raw, "weight_avg"),
        )

    @staticmethod
    def list_from_response(data: JsonValue) -> list[DailyStatistics]:
        """Parse the top-level array returned by the statistics endpoint."""
        if not isinstance(data, Sequence) or isinstance(data, str):
            return []
        return [DailyStatistics.from_json(item) for item in data if isinstance(item, Mapping)]
