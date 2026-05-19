"""One property-change push delivered by the live status stream."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class StatusUpdate:
    """One property-change push from the Neakasa cloud.

    The cloud forwards each property write the device makes as a single
    MQTT message. This dataclass is the parsed, consumer-facing shape:
    ``device_name`` identifies the affected device (same value the
    history endpoints accept) and ``changes`` is a flat dict of only the
    fields that actually changed.

    Known top-level properties are translated to the same snake_case
    keys :class:`DeviceStatus` uses (``silentMode`` → ``silent_mode``,
    ``catLeft.kitten`` → ``cat_present``, …). Unrecognized properties
    pass through under their **original** camelCase key with the raw
    value the device sent, so a new server-side field never gets
    silently dropped — the consumer can read it and choose how to
    handle it.
    """

    device_name: str
    changes: dict[str, JsonValue] = field(default_factory=dict)
    received_at: float = field(default_factory=time.time)

    @classmethod
    def from_push(cls, body: JsonObject) -> StatusUpdate | None:
        """Build a :class:`StatusUpdate` from a raw push envelope.

        Returns ``None`` if the payload is missing the device id or the
        ``items`` map (which indicates this isn't a property change at
        all and the caller should skip it).
        """
        params = body.get("params")
        if not isinstance(params, Mapping):
            return None
        device_name = params.get("deviceName")
        if not isinstance(device_name, str):
            return None
        items = params.get("items")
        if not isinstance(items, Mapping):
            return None
        return cls(device_name=device_name, changes=_flatten_changes(items))


def _flatten_changes(items: JsonObject) -> dict[str, JsonValue]:
    """Translate raw push items to the snake_case keys :class:`DeviceStatus` uses."""
    out: dict[str, JsonValue] = {}
    for key, entry in items.items():
        if not isinstance(entry, Mapping):
            continue
        value = entry.get("value")
        if key == "silentMode":
            out["silent_mode"] = value == 1
        elif key == "childLockOnOff":
            out["child_lock"] = value == 1
        elif key == "autoLevel":
            out["auto_level"] = value == 1
        elif key == "youngCatMode":
            out["young_cat_mode"] = value == 1
        elif key == "bucketStatus":
            out["bucket_full"] = value != 0
        elif key == "latestAddSandTime" and isinstance(value, str):
            out["last_sand_added"] = value
        elif key == "actionLog" and isinstance(value, str):
            out["last_action"] = value
        elif key == "Sand" and isinstance(value, Mapping):
            percent = value.get("percent")
            if isinstance(percent, int):
                out["sand_percent"] = percent
        elif key == "catLeft" and isinstance(value, Mapping):
            out["cat_present"] = value.get("kitten") == 1
            stay = value.get("stayTime")
            if isinstance(stay, int):
                out["cat_stay_seconds"] = stay
            out["needs_cleaning"] = value.get("needClean") == 1
        elif key == "cleanCfg" and isinstance(value, Mapping):
            out["cleaning_enabled"] = value.get("active") == 1
        else:
            # Pass unmapped properties through verbatim. Keeps new
            # server-side fields visible without requiring an SDK
            # release; consumers can read them under the same camelCase
            # name the wire uses.
            out[key] = value
    return out
