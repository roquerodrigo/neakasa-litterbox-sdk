"""One row of the litter-box activity history."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from ..utils._json import get_float, get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


class RecordType(IntEnum):
    """Classification of a row returned by ``catbox/record``.

    Observed shapes — ``1`` always carries a ``kg`` weight and a
    ``cat_id``, ``2`` always carries ``weight=20`` with empty ``unit``.
    """

    CAT_VISIT = 1
    CLEAN_CYCLE = 2
    OTHER = 3

    @classmethod
    def from_int(cls, value: int) -> RecordType:
        """Return the matching enum member, defaulting to ``OTHER``."""
        try:
            return cls(value)
        except ValueError:
            return cls.OTHER


@dataclass(frozen=True, slots=True)
class ToiletRecord:
    """One entry of the litter-box activity log.

    Field semantics confirmed live for ``record_type ∈ {1, 2}``:

    - **CAT_VISIT (1)** — ``weight`` is the cat's weight in ``kg`` and
      ``cat_id`` references :class:`Cat` (``0`` when the device didn't
      recognise which cat triggered the event).
    - **CLEAN_CYCLE (2)** — ``weight`` is the cycle's duration-ish
      counter (``20`` in every sample) and ``unit`` is empty. The
      ``start_time``/``end_time`` pair is the only reliable time data.
    - **OTHER (3)** — empty ``weight``/``unit``; semantics not yet known.

    ``way`` is preserved on the wire but its meaning hasn't been pinned
    down; leaving it on the dataclass for downstream experimentation.
    """

    record_id: int
    record_type: RecordType
    cat_id: int
    start_time: int
    end_time: int
    weight: float
    unit: str
    way: int

    @property
    def duration_seconds(self) -> int:
        """Convenience: ``end_time - start_time``."""
        return self.end_time - self.start_time

    @classmethod
    def from_json(cls, raw: JsonObject) -> ToiletRecord:
        """Build a ``ToiletRecord`` from one element of ``record_list``."""
        return cls(
            record_id=get_int(raw, "record_id"),
            record_type=RecordType.from_int(get_int(raw, "type")),
            cat_id=get_int(raw, "cat_id"),
            start_time=get_int(raw, "start_time"),
            end_time=get_int(raw, "end_time"),
            weight=get_float(raw, "weight"),
            unit=get_str(raw, "unit"),
            way=get_int(raw, "way"),
        )

    @staticmethod
    def list_from_response(data: JsonValue) -> list[ToiletRecord]:
        """Unwrap ``{"record_list": [...]}`` into a typed list."""
        if not isinstance(data, Mapping):
            return []
        records = data.get("record_list")
        if not isinstance(records, Sequence) or isinstance(records, str):
            return []
        return [ToiletRecord.from_json(item) for item in records if isinstance(item, Mapping)]
