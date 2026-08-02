"""Transport-boundary behavior for the REST HttpTransport.

aiohttp is mocked at the ``ClientSession`` boundary — no real sockets.
Covers success decoding, the ``status >= 400`` path, ``ClientError``
wrapping into :class:`TransportError`, and session ownership/lifecycle.
"""

from __future__ import annotations

import aiohttp
import pytest

from neakasa_litterbox_sdk.auth.transport import HttpTransport
from neakasa_litterbox_sdk.exceptions import TransportError


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    async def read(self) -> bytes:
        return self._body

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeSession:
    """Minimal stand-in for ``aiohttp.ClientSession``."""

    def __init__(
        self, response: _FakeResponse | None = None, raise_exc: Exception | None = None
    ) -> None:
        self._response = response
        self._raise_exc = raise_exc
        self.closed = False
        self.last_get: tuple[str, dict[str, str]] | None = None

    def get(self, url: str, headers: dict[str, str]) -> _FakeResponse:
        self.last_get = (url, headers)
        if self._raise_exc is not None:
            raise self._raise_exc
        assert self._response is not None
        return self._response

    async def close(self) -> None:
        self.closed = True


async def test_signed_get_decodes_json_object() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"code": 0, "data": {"x": 1}}'))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    result = await transport.signed_get("https://host/api", {"a": "b"})
    assert result == {"code": 0, "data": {"x": 1}}
    assert session.last_get is not None
    assert session.last_get[0] == "https://host/api?a=b"


async def test_signed_get_data_envelope_wraps_params() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"code": 0}'))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    await transport.signed_get("https://host/api", {})  # warm
    await transport.signed_get_data_envelope("https://host/login", {"email": "a@b.c"})
    assert session.last_get is not None
    assert session.last_get[0].startswith("https://host/login?data=")


async def test_authenticated_get_sets_uid_and_token_headers() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"code": 0}'))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    await transport.authenticated_get(
        "https://host/api/x",
        {"user_id": "1"},
        encrypted_user_id="enc",
        session_token="tok",
    )
    assert session.last_get is not None
    headers = session.last_get[1]
    assert headers["uid"] == "enc"
    assert headers["token"] == "tok"


async def test_http_error_status_raises_transport_error() -> None:
    session = _FakeSession(_FakeResponse(503, b"upstream down"))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError) as exc_info:
        await transport.signed_get("https://host/api", {})
    assert exc_info.value.status_code == 503


async def test_client_error_is_wrapped() -> None:
    session = _FakeSession(raise_exc=aiohttp.ClientError("boom"))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError, match="Failed to GET"):
        await transport.signed_get("https://host/api", {})


async def test_timeout_is_wrapped() -> None:
    # aiohttp raises the builtin TimeoutError on ``ClientTimeout``; it is not
    # a ClientError, so it has to be caught explicitly or it escapes the SDK.
    session = _FakeSession(raise_exc=TimeoutError)
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError, match="Failed to GET"):
        await transport.signed_get("https://host/api", {})


async def test_close_closes_owned_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the transport created the session, ``close`` shuts it down."""
    transport = HttpTransport()
    created = _FakeSession(_FakeResponse(200, b"{}"))
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.auth.transport.aiohttp.ClientSession",
        lambda timeout: created,
    )
    await transport.signed_get("https://host/api", {})  # lazily creates the session
    assert transport._session is created
    await transport.close()
    assert created.closed is True
    assert transport._session is None


async def test_close_does_not_close_injected_session() -> None:
    """An externally provided session is the caller's to close, not ours."""
    session = _FakeSession(_FakeResponse(200, b"{}"))
    transport = HttpTransport(session=session)  # type: ignore[arg-type]
    await transport.close()
    assert session.closed is False


async def test_close_is_idempotent_when_never_used() -> None:
    transport = HttpTransport()
    await transport.close()  # no session was ever created
    assert transport._session is None
