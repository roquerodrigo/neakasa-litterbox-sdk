"""Toggle automatic litter-leveling after each clean cycle.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Pass
``off`` (default ``on``) to disable. Run with::

    uv run python examples/set_auto_level.py
    uv run python examples/set_auto_level.py off
"""

from __future__ import annotations

import asyncio
import sys

from _session import authenticate, configure_logging, pick_device_name
from neakasa_litterbox_sdk import NeakasaError


async def main() -> int:
    configure_logging()
    enabled = sys.argv[1].lower() != "off" if len(sys.argv) > 1 else True

    try:
        client, _ = await authenticate()
        device_name = await pick_device_name(client)
        await client.set_auto_level(device_name, enabled)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Auto-level {'enabled' if enabled else 'disabled'} on {device_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
