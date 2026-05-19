"""List the cats registered against a Neakasa device.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Run with::

    uv run python examples/list_cats.py
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
        cats = await client.list_cats(device_name)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Found {len(cats)} cat(s) on {device_name}:")
    for cat in cats:
        print(
            f"  #{cat.id} {cat.name:<10} {cat.weight} {cat.unit}  "
            f"gender={cat.gender.name.lower()}  "
            f"sterilized={'yes' if cat.is_sterilized else 'no'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
