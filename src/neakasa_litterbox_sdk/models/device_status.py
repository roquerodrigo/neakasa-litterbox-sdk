"""Live property readback for a Neakasa device."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils._json import get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    """Snapshot of the runtime state the mobile app's home screen shows.

    Fields are populated from ``/thing/properties/get`` — each property
    on the wire is wrapped as ``{"time": ..., "value": ...}``; this
    dataclass flattens the values that map to user-facing UI controls.
    Properties not modeled here (network diagnostics, firmware version,
    debug flags, …) round-trip through :meth:`from_response`'s raw
    input if a consumer needs them.

    "Last cleaned at" is not on this readback — query
    :meth:`NeakasaClient.get_toilet_records` and filter by
    ``record_type == RecordType.CLEAN_CYCLE`` instead.
    """

    sand_percent: int
    cat_present: bool
    cat_stay_seconds: int
    needs_cleaning: bool
    bucket_full: bool
    last_sand_added: str
    cleaning_enabled: bool
    auto_level: bool
    silent_mode: bool
    child_lock: bool
    young_cat_mode: bool
    last_action: str
    wifi_name: str
    wifi_rssi: int
    ip_address: str
    mac_address: str
    firmware_version: str
    hardware_version: str
    updated_at: int

    @classmethod
    def from_response(cls, raw: JsonObject) -> DeviceStatus:
        """Build a :class:`DeviceStatus` from the gateway ``data`` map."""
        sand = _property_object(raw, "Sand")
        cat_left = _property_object(raw, "catLeft")
        clean_cfg = _property_object(raw, "cleanCfg")
        network = _property_object(raw, "NetWorkStatus")
        version = _property_object(raw, "DeviceVer")
        return cls(
            sand_percent=get_int(sand, "percent"),
            cat_present=get_int(cat_left, "kitten") == 1,
            cat_stay_seconds=get_int(cat_left, "stayTime"),
            needs_cleaning=get_int(cat_left, "needClean") == 1,
            # The M1 signals a full waste bin via ``room_of_bin`` (1 = full,
            # 0 = empty), confirmed by diffing the cloud snapshot full↔empty.
            # ``bucketStatus`` stays 0 on this model and never reflected it.
            bucket_full=_property_int(raw, "room_of_bin") != 0,
            last_sand_added=_property_str(raw, "latestAddSandTime"),
            cleaning_enabled=get_int(clean_cfg, "active") == 1,
            auto_level=_property_int(raw, "autoLevel") == 1,
            silent_mode=_property_int(raw, "silentMode") == 1,
            child_lock=_property_int(raw, "childLockOnOff") == 1,
            young_cat_mode=_property_int(raw, "youngCatMode") == 1,
            last_action=_property_str(raw, "actionLog"),
            wifi_name=get_str(network, "WiFi_Name"),
            wifi_rssi=get_int(network, "WiFi_RSSI"),
            ip_address=get_str(network, "IP_Addr"),
            mac_address=get_str(network, "MAC_Addr"),
            firmware_version=get_str(version, "FW_Version"),
            hardware_version=get_str(version, "HW_Version"),
            updated_at=_property_int(raw, "timestamp"),
        )


def _property_value(raw: JsonObject, key: str) -> JsonValue:
    """Return ``raw[key]["value"]`` as a ``JsonValue``, or ``None`` if absent."""
    entry = raw.get(key)
    if not isinstance(entry, Mapping):
        return None
    return entry.get("value")


def _property_object(raw: JsonObject, key: str) -> JsonObject:
    """Return ``raw[key]["value"]`` narrowed to a JSON object (``{}`` if absent)."""
    value = _property_value(raw, key)
    return value if isinstance(value, Mapping) else {}


def _property_int(raw: JsonObject, key: str) -> int:
    """Return ``raw[key]["value"]`` narrowed to int (``0`` if absent or non-numeric)."""
    value = _property_value(raw, key)
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            return int(value) if isinstance(value, str) else 0
        except ValueError:
            return 0
    return value


def _property_str(raw: JsonObject, key: str) -> str:
    """Return ``raw[key]["value"]`` narrowed to str (``""`` if absent)."""
    value = _property_value(raw, key)
    return value if isinstance(value, str) else ""
