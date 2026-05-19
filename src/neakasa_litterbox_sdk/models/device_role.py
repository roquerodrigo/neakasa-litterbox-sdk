"""Role the authenticated user has on a paired device."""

from __future__ import annotations

from enum import IntEnum


class DeviceRole(IntEnum):
    """The user's link to a device.

    Numeric values match the ``bind_status`` query parameter the
    Neakasa history endpoints expect — ``1`` for the account that
    originally paired the device, ``2`` for an account that later
    accepted a share invite.
    """

    OWNER = 1
    SHARED = 2
