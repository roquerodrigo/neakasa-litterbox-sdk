"""Start the leveling motor on the user's litter box.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Run with::

    uv run python examples/start_level.py
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
        await client.start_level(device_name)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Leveling pass started on {device_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
