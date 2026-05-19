"""Log in to the Neakasa REST API (with disk-cached session) and print the result.

Run with::

    uv run python examples/login.py
"""

from __future__ import annotations

import asyncio
import sys

from _session import authenticate, configure_logging


async def main() -> int:
    configure_logging()
    _, result = await authenticate()

    fresh_or_cached = "cached" if result.age_seconds() > 1 else "fresh"
    print(f"Authenticated ({fresh_or_cached}, age={result.age_seconds():.0f}s)")
    print(f"  user_id               = {result.user_id}")
    print(f"  user_name             = {result.user_info.user_name}")
    print(f"  ali_user_id           = {result.user_info.ali_user_id}")
    print(f"  ali_auth_token (len)  = {len(result.user_info.ali_authentication_token)}")
    print(f"  user_token (len)      = {len(result.user_token)}")
    print(f"  aes_key (len)         = {len(result.aes_key)}")
    print(f"  aes_iv (len)          = {len(result.aes_iv)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
