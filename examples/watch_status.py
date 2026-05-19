"""Stream live status changes from every device on the account.

Registers a handler per event type and blocks until Ctrl-C. Run with::

    uv run python examples/watch_status.py

The Aliyun broker's TLS chain still anchors at the legacy GlobalSign
Root CA, which recent ``certifi`` bundles drop. This example uses
``tls_insecure=True`` to skip cert validation — fine for local
experiments; in production point ``ca_certs`` at a bundle that still
carries that root.
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
        async with client.watch_status(tls_insecure=True) as stream:
            stream.on_silent_mode(lambda dn, on: print(f"[{dn}] silent_mode={on}"))
            stream.on_child_lock(lambda dn, on: print(f"[{dn}] child_lock={on}"))
            stream.on_auto_level(lambda dn, on: print(f"[{dn}] auto_level={on}"))
            stream.on_cleaning_enabled(lambda dn, on: print(f"[{dn}] auto_clean={on}"))
            stream.on_sand_percent(lambda dn, pct: print(f"[{dn}] sand_percent={pct}%"))
            stream.on_cat_present(lambda dn, p: print(f"[{dn}] cat_present={p}"))
            stream.on_needs_cleaning(lambda dn, n: print(f"[{dn}] needs_cleaning={n}"))
            stream.on_bucket_full(lambda dn, f: print(f"[{dn}] bucket_full={f}"))
            stream.on_last_action(lambda dn, a: print(f"[{dn}] last_action={a!r}"))
            stream.on_unknown(lambda dn, key, val: print(f"[{dn}] {key}={val!r}"))
            print("Listening for live status changes. Ctrl-C to stop.")
            await stream.run_forever()
    except NeakasaError as exc:
        print(f"SDK error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
