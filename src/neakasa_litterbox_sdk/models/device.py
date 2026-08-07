"""A device registered on the user's Neakasa account."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils._json import get_int, get_str
from .device_role import DeviceRole

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class Device:
    """A Neakasa device the user owns or has been shared with.

    ``device_name`` is the identifier accepted by the history endpoints
    (:meth:`NeakasaClient.list_cats`, ``get_toilet_records``,
    ``get_toilet_statistics``). ``role`` says whether the authenticated
    user paired the device themselves (:attr:`DeviceRole.OWNER`) or
    accepted a share invite from somebody else (:attr:`DeviceRole.SHARED`).
    """

    iot_id: str
    product_key: str
    product_name: str
    device_name: str
    category_key: str
    category_name: str
    net_type: str
    role: DeviceRole
    status: int
    bind_time: int

    @classmethod
    def from_json(cls, raw: JsonObject) -> Device:
        """Build a ``Device`` from one element of the response array."""
        return cls(
            iot_id=get_str(raw, "iotId"),
            product_key=get_str(raw, "productKey"),
            product_name=get_str(raw, "productName"),
            device_name=get_str(raw, "deviceName"),
            category_key=get_str(raw, "categoryKey"),
            category_name=get_str(raw, "categoryName"),
            net_type=get_str(raw, "netType"),
            role=DeviceRole.OWNER if get_int(raw, "owned") == 1 else DeviceRole.SHARED,
            status=get_int(raw, "status"),
            bind_time=get_int(raw, "bindTime"),
        )

    @staticmethod
    def list_from_response(response: JsonObject) -> list[Device]:
        """Extract the device list from a ``list_devices`` response."""
        items: JsonValue = response.get("data")
        if not isinstance(items, Sequence) or isinstance(items, str):
            return []
        return [Device.from_json(entry) for entry in items if isinstance(entry, Mapping)]
