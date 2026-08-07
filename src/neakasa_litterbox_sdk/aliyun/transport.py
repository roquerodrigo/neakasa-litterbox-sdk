"""POST envelopes against the Aliyun IoT API Gateway and OpenAccount."""

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import TYPE_CHECKING

import aiohttp

from .._status_codes import HTTP_ERROR_STATUS
from ..exceptions import TransportError
from ..utils._json import loads
from .envelope import build_envelope
from .oa_signing import build_oa_headers
from .signing import GATEWAY_HOST_US, build_aliyun_headers

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.aliyun.transport")


class AliyunTransport:
    """Issue signed POSTs against Aliyun IoT API Gateway and OpenAccount."""

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

    async def call(
        self,
        path: str,
        *,
        api_version: str,
        host: str = GATEWAY_HOST_US,
        iot_token: str | None = None,
        payload: dict[str, JsonValue],
        language: str = "en-US",
    ) -> JsonObject:
        """Send a standard IoT-envelope POST (the ``c/d/params/request`` JSON-RPC shape)."""
        request_id, body = build_envelope(
            payload,
            api_version=api_version,
            iot_token=iot_token,
            language=language,
        )
        path_with_query = f"{path}?x-ca-request-id={urllib.parse.quote(request_id)}"
        url = f"https://{host}{path_with_query}"
        headers = build_aliyun_headers("POST", path_with_query, body)
        log.debug("POST %s%s (request-id=%s)", host, path, request_id)
        return await self._do_post(url, path, body, headers)

    async def call_oa(
        self,
        path: str,
        *,
        host: str,
        body: dict[str, JsonValue],
        extra_headers: dict[str, str] | None = None,
    ) -> JsonObject:
        """OpenAccount-style POST: form-encoded body, HmacSHA256 signature.

        Used by the ``connect.json`` / ``loginbyoauth.json`` steps of the
        OpenAccount handshake — different signing scheme from
        :meth:`call`, so it lives in its own method.
        """
        encoded_body = _encode_oa_body(body, url_encoded=True)
        signing_body = _encode_oa_body(body, url_encoded=False)
        wire = encoded_body.encode("utf-8")
        headers = build_oa_headers("POST", path, signing_body)
        if extra_headers:
            headers.update(extra_headers)
        url = f"https://{host}{path}"
        log.debug("POST %s%s (oa)", host, path)
        return await self._do_post(url, path, wire, headers)

    async def _do_post(
        self,
        url: str,
        path: str,
        body: bytes,
        headers: dict[str, str],
    ) -> JsonObject:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        try:
            async with self._session.post(url, data=body, headers=headers) as resp:
                raw = await resp.read()
                if resp.status >= HTTP_ERROR_STATUS:
                    detail = raw[:512].decode("utf-8", errors="replace")
                    log.debug("HTTP %s on %s: body=%s", resp.status, path, detail)
                    raise TransportError(
                        f"Failed to POST {path}: HTTP {resp.status}: {detail}",
                        status_code=resp.status,
                    )
        # ``ClientTimeout`` surfaces as the builtin ``TimeoutError``, which is
        # not an ``aiohttp.ClientError`` — without it a slow cloud escapes the
        # SDK's exception hierarchy entirely.
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise TransportError(f"Failed to POST {path}: {exc}") from exc
        log.debug("Response body: %s", raw[:2048])
        return loads(raw)


def _encode_oa_body(body: dict[str, JsonValue], *, url_encoded: bool) -> str:
    """Serialise the OA body as ``k1=<json>&k2=<json>``.

    The wire form URL-encodes the JSON values; the canonical string-to-sign
    keeps them raw. ``url_encoded`` flips between the two.
    """
    parts: list[str] = []
    for key, value in body.items():
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        if url_encoded:
            encoded = urllib.parse.quote_plus(encoded)
        parts.append(f"{key}={encoded}")
    return "&".join(parts)
