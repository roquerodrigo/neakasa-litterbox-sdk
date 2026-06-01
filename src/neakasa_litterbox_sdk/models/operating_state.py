"""Operating state of a Neakasa litter box."""

from __future__ import annotations

from enum import IntEnum


class OperatingState(IntEnum):
    """What the box is currently doing, from the ``bucketStatus`` property.

    Despite its name, ``bucketStatus`` encodes the machine's activity, not
    the waste-bin fill level — that lives in ``room_of_bin`` (surfaced as
    :attr:`DeviceStatus.bucket_full`). Codes were confirmed by correlating
    the mobile app's status label with live MQTT pushes across a full
    clean cycle: ``2`` while the app showed "cleaning", ``1`` while it
    showed "restoring", ``3`` during the auto-level pass, ``0`` at rest.
    """

    UNKNOWN = -1
    IDLE = 0
    RESTORING = 1
    CLEANING = 2
    LEVELING = 3

    @classmethod
    def from_code(cls, value: int) -> OperatingState:
        """Return the matching member, defaulting to ``UNKNOWN``."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN
