"""Print the live status of the user's litter box.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Run with::

    uv run python examples/get_status.py
"""

from __future__ import annotations

import asyncio
import sys

from _session import authenticate, configure_logging, pick_device_name
from neakasa_litterbox_sdk import NeakasaError


async def main() -> int:
    configure_logging()

    try:
        client, _ = await authenticate()
        device_name = await pick_device_name(client)
        status = await client.get_status(device_name)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Status of {device_name}:")
    print(f"  sand_percent     = {status.sand_percent}%")
    print(f"  cat_present      = {status.cat_present}")
    print(f"  cat_stay_seconds = {status.cat_stay_seconds}s")
    print(f"  needs_cleaning   = {status.needs_cleaning}")
    print(f"  bucket_full      = {status.bucket_full}")
    print(f"  last_sand_added  = {status.last_sand_added!r}")
    print(f"  last_action      = {status.last_action!r}")
    print(f"  cleaning_enabled = {status.cleaning_enabled}")
    print(f"  auto_level       = {status.auto_level}")
    print(f"  silent_mode      = {status.silent_mode}")
    print(f"  child_lock       = {status.child_lock}")
    print(f"  young_cat_mode   = {status.young_cat_mode}")
    print(f"  wifi             = {status.wifi_name!r}  rssi={status.wifi_rssi}dBm")
    print(f"  ip / mac         = {status.ip_address} / {status.mac_address}")
    print(f"  firmware / hw    = {status.firmware_version} / {status.hardware_version}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
