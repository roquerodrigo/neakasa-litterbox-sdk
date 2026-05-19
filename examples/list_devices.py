"""List the Neakasa devices registered on the user's account.

``authenticate()`` handles the full session lifecycle: restore cache,
log in if needed, and persist any rotation. Run with::

    uv run python examples/list_devices.py
"""

from __future__ import annotations

import asyncio
import sys

from _session import authenticate, configure_logging
from neakasa_litterbox_sdk import NeakasaError


async def main() -> int:
    configure_logging()

    try:
        client, _ = await authenticate()
        devices = await client.list_devices()
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    if not devices:
        print("No devices on this account.")
        return 0

    print(f"Found {len(devices)} device(s):")
    for index, device in enumerate(devices, start=1):
        print(f"  #{index} {device.product_name} ({device.category_name})")
        print(f"     iot_id      = {device.iot_id}")
        print(f"     device_name = {device.device_name}")
        print(f"     product_key = {device.product_key}")
        print(f"     role        = {device.role.name.lower()}")
        print(f"     status      = {device.status}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
