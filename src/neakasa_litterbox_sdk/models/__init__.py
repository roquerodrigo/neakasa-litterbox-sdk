"""Public data classes returned by SDK methods."""

from __future__ import annotations

from .cat import Cat, CatGender
from .daily_statistics import DailyStatistics
from .device import Device
from .device_role import DeviceRole
from .device_status import DeviceStatus
from .login_result import LoginResult
from .operating_state import OperatingState
from .region import Region
from .status_update import StatusUpdate
from .toilet_record import RecordType, ToiletRecord
from .user_info import UserInfo

__all__ = [
    "Cat",
    "CatGender",
    "DailyStatistics",
    "Device",
    "DeviceRole",
    "DeviceStatus",
    "LoginResult",
    "OperatingState",
    "RecordType",
    "Region",
    "StatusUpdate",
    "ToiletRecord",
    "UserInfo",
]
