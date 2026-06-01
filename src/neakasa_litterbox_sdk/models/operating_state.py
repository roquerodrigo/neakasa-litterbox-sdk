"""Operating state of a Neakasa litter box."""

from __future__ import annotations

import logging
from enum import IntEnum

_LOGGER = logging.getLogger(__name__)

# Codes already warned about, so a persistent unmapped state doesn't spam
# the log on every poll/push — warn once per distinct value per process.
_warned_codes: set[int] = set()


class OperatingState(IntEnum):
    """What the box is currently doing, from the ``bucketStatus`` property.

    Despite its name, ``bucketStatus`` encodes the machine's activity, not
    the waste-bin fill level — that lives in ``room_of_bin`` (surfaced as
    :attr:`DeviceStatus.bucket_full`). Codes were confirmed by correlating
    the mobile app's status label with live MQTT pushes: ``2`` while the
    app showed "cleaning", ``1`` while "restoring", ``3`` during the
    auto-level pass, ``5`` while a cat was inside the box (the app labels
    this "Cat appears"), ``0`` at rest. (``4`` has not been observed yet;
    it falls back to ``UNKNOWN``.)
    """

    UNKNOWN = -1
    IDLE = 0
    RESTORING = 1
    CLEANING = 2
    LEVELING = 3
    CAT_APPEARS = 5

    @classmethod
    def from_code(cls, value: int) -> OperatingState:
        """Return the matching member, defaulting to ``UNKNOWN``.

        An unmapped code logs a warning once (per distinct value) so new
        device states surface instead of silently becoming ``UNKNOWN``.
        """
        try:
            return cls(value)
        except ValueError:
            if value not in _warned_codes:
                _warned_codes.add(value)
                _LOGGER.warning(
                    "Unmapped Neakasa operating-state code %s (raw bucketStatus); "
                    "treating as UNKNOWN — please report it so it can be mapped",
                    value,
                )
            return cls.UNKNOWN
