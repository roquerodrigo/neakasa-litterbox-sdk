"""Dump the last 30 days of per-day litter-box statistics.

Picks the first device on the account (override with
``NEAKASA_DEVICE_NAME`` in ``.env`` for multi-device accounts). Run with::

    uv run python examples/get_toilet_statistics.py
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
    month_ago = end - 30 * 86400

    try:
        client, _ = await authenticate()
        device_name = await pick_device_name(client)
        stats = await client.get_toilet_statistics(
            device_name,
            start_time=month_ago,
            end_time=end,
            zone_seconds=-10800,  # America/Sao_Paulo; switch to 0 for UTC
        )
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1

    print(f"Last 30 days on {device_name} — {len(stats)} day(s):")
    for s in stats:
        print(
            f"  {s.date}  visits={s.num:>2}  "
            f"total_time={s.toilet_total_second:>4}s  "
            f"avg_weight={s.weight_avg:.2f} {s.unit}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
