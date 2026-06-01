"""Public API surface for the Neakasa SDK."""

from __future__ import annotations

from .client import NeakasaClient
from .exceptions import (
    ApiError,
    AuthenticationError,
    InvalidCredentialsError,
    NeakasaError,
    SessionExpiredError,
    TransportError,
)
from .models import (
    Cat,
    CatGender,
    DailyStatistics,
    Device,
    DeviceRole,
    DeviceStatus,
    LoginResult,
    OperatingState,
    RecordType,
    Region,
    StatusUpdate,
    ToiletRecord,
    UserInfo,
)
from .status_stream import StatusStream

__all__ = [
    "ApiError",
    "AuthenticationError",
    "Cat",
    "CatGender",
    "DailyStatistics",
    "Device",
    "DeviceRole",
    "DeviceStatus",
    "InvalidCredentialsError",
    "LoginResult",
    "NeakasaClient",
    "NeakasaError",
    "OperatingState",
    "RecordType",
    "Region",
    "SessionExpiredError",
    "StatusStream",
    "StatusUpdate",
    "ToiletRecord",
    "TransportError",
    "UserInfo",
]
