"""Calibrate the device's sand-level sensor.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). The
percent argument tells the device that the *current* physical load
corresponds to ``<percent>`` of "full" — fill the box to the marked
"full" line before running this. Run with::

    uv run python examples/calibrate_sand.py        # defaults to 100
    uv run python examples/calibrate_sand.py 80
"""

from __future__ import annotations

import asyncio
import sys

from _session import authenticate, configure_logging, pick_device_name
from neakasa_litterbox_sdk import NeakasaError


async def main() -> int:
    configure_logging()

    percent = 100
    if len(sys.argv) > 1:
        try:
            percent = int(sys.argv[1])
        except ValueError:
            print(f"Invalid percent: {sys.argv[1]!r}", file=sys.stderr)
            return 2

    try:
        client, _ = await authenticate()
        device_name = await pick_device_name(client)
        await client.calibrate_sand(device_name, percent)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Sand level calibrated to {percent}% on {device_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
