"""Dump the last 7 days of litter-box visit records.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Run with::

    uv run python examples/get_toilet_records.py
"""

from __future__ import annotations

import asyncio
import sys
import time

from _session import authenticate, configure_logging, pick_device_name
from neakasa_litterbox_sdk import NeakasaError


async def main() -> int:
    configure_logging()

    end = int(time.time())
    week_ago = end - 7 * 86400

    try:
        client, _ = await authenticate()
        device_name = await pick_device_name(client)
        records = await client.get_toilet_records(device_name, start_time=week_ago, end_time=end)
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Last 7 days on {device_name} — {len(records)} record(s):")
    for r in records[:50]:
        label = r.record_type.name.replace("_", " ").lower()
        cat = f"cat#{r.cat_id}" if r.cat_id else "no cat"
        weight = f"{r.weight} {r.unit}".strip()
        print(
            f"  {time.strftime('%Y-%m-%d %H:%M', time.localtime(r.start_time))}  "
            f"[{label:<11}]  {cat:<10}  {weight:<8}  "
            f"({r.duration_seconds}s)"
        )
    if len(records) > 50:
        print(f"  ... ({len(records) - 50} more)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
