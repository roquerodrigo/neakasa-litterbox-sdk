"""Minimal HTTP transport for Neakasa REST endpoints.

Async-only: uses ``aiohttp`` so the whole SDK can run inside Home
Assistant's event loop without thread hops. The Neakasa REST API
expects GET requests for both pre-auth and post-auth flows (yes, even
login is a GET). Three query-encoding styles are implemented here:

- :meth:`signed_get` — standard ``?k1=v1&k2=v2`` form, pre-auth headers.
- :meth:`signed_get_data_envelope` — single ``?data=<URL-encoded JSON>``
  param containing the full parameter object (login and most
  ``withoutToken=true`` endpoints).
- :meth:`authenticated_get` — post-auth "Scheme A": plain ``?k=v``
  query string, with ``uid`` and ``token`` headers replacing
  ``appId`` / ``sign``.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import TYPE_CHECKING

import aiohttp

from ..exceptions import TransportError
from ..utils._json import loads
from .signing import build_authenticated_headers, build_signed_headers

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..utils._json import JsonObject

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.auth.transport")


class HttpTransport:
    """Issue signed GET requests against the Neakasa REST API."""

    def __init__(
        self,
        timeout: float = 10.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owns_session = session is None

    async def close(self) -> None:
        """Close the underlying ``aiohttp.ClientSession`` if we created it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def signed_get(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        language: str = "en",
    ) -> JsonObject:
        """Issue a signed GET request with classic query parameters."""
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        return await self._do_get(full_url, url, build_signed_headers(language=language))

    async def signed_get_data_envelope(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        language: str = "en",
    ) -> JsonObject:
        """Issue a signed GET that wraps the params as ``?data=<JSON>``."""
        data_param = urllib.parse.quote(json.dumps(params, separators=(",", ":")), safe="")
        full_url = f"{url}?data={data_param}"
        return await self._do_get(full_url, url, build_signed_headers(language=language))

    async def authenticated_get(
        self,
        url: str,
        params: Mapping[str, str],
        *,
        encrypted_user_id: str,
        session_token: str,
        language: str = "en",
    ) -> JsonObject:
        """Scheme A: plain query params + ``uid`` / ``token`` headers."""
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = build_authenticated_headers(encrypted_user_id, session_token, language=language)
        return await self._do_get(full_url, url, headers)

    async def _do_get(
        self,
        full_url: str,
        base_url: str,
        headers: Mapping[str, str],
    ) -> JsonObject:
        log.debug("GET %s", base_url)
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        try:
            async with self._session.get(full_url, headers=dict(headers)) as resp:
                body = await resp.read()
                if resp.status >= 400:
                    raise TransportError(
                        f"Failed to GET {base_url}: HTTP {resp.status}",
                        status_code=resp.status,
                    )
        # ``ClientTimeout`` surfaces as the builtin ``TimeoutError``, which is
        # not an ``aiohttp.ClientError`` — without it a slow cloud escapes the
        # SDK's exception hierarchy entirely.
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise TransportError(f"Failed to GET {base_url}: {exc}") from exc
        log.debug("Response body: %s", body[:2048])
        return loads(body)
