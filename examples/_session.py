"""Shared bootstrap for the example scripts.

Loads ``.env`` from the repo root, restores a cached ``LoginResult`` from
``.neakasa-session.json`` when present and younger than ``MAX_AGE_SECONDS``,
and returns a ready-to-use authenticated client. Examples should call
``authenticate()`` once and then use only its return value — they should
not duplicate the cache or login logic.

Reads (required): ``NEAKASA_EMAIL``, ``NEAKASA_PASSWORD``.
Writes: ``.neakasa-session.json`` on every fresh login (gitignored).
"""

from __future__ import annotations

# uv-installed CPython on macOS ships without a usable CA bundle, so
# both urllib and aiohttp fail TLS verification by default. Pointing
# SSL_CERT_FILE at the certifi bundle has to happen *before* any SDK
# import triggers ssl module initialisation downstream.
import os

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from neakasa_litterbox_sdk import LoginResult, NeakasaClient, NeakasaError

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
CACHE_PATH: Path = REPO_ROOT / ".neakasa-session.json"
MAX_AGE_SECONDS: int = 20 * 60 * 60


def configure_logging(level: int = logging.INFO) -> None:
    """Default logging setup for example scripts."""
    logging.basicConfig(level=level, format="%(name)s %(levelname)s: %(message)s")


async def authenticate() -> tuple[NeakasaClient, LoginResult]:
    """Return an authenticated client + its current ``LoginResult``.

    Reuses ``.neakasa-session.json`` when the cached session is fresher
    than ``MAX_AGE_SECONDS``. Otherwise performs a fresh ``login()`` and
    rewrites the cache. Exits with status 2 if ``.env`` is missing the
    required credentials.
    """
    load_dotenv(REPO_ROOT / ".env")
    email = os.environ.get("NEAKASA_EMAIL")
    password = os.environ.get("NEAKASA_PASSWORD")
    if not email or not password:
        sys.exit("Missing NEAKASA_EMAIL or NEAKASA_PASSWORD in .env")

    cached = _load_cache()
    if cached is not None and _is_stale(cached):
        cached = None  # treat stale cache as no cache → forces fresh login

    client = NeakasaClient(email=email, password=password)
    result = await client.login(cached=cached)
    if result is not cached:
        persist_session(result)
    return client, result


async def pick_device_name(client: NeakasaClient) -> str:
    """Return ``NEAKASA_DEVICE_NAME`` if set, otherwise the first device on the account."""
    name = os.environ.get("NEAKASA_DEVICE_NAME")
    if name:
        return name
    devices = await client.list_devices()
    if not devices:
        raise NeakasaError("No devices on this account")
    return devices[0].device_name


def persist_session(result: LoginResult | None) -> None:
    """Write ``result`` to the cache file (creates ``.neakasa-session.json``)."""
    if result is None:
        return
    CACHE_PATH.write_text(json.dumps(result.to_dict(), indent=2))


def _is_stale(result: LoginResult) -> bool:
    return result.age_seconds() > MAX_AGE_SECONDS


def _load_cache() -> LoginResult | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return LoginResult.from_dict(json.loads(CACHE_PATH.read_text()))
    except OSError, ValueError:
        return None
