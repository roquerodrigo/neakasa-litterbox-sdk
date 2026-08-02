"""Transport-boundary behavior for the Aliyun POST transport.

aiohttp is mocked at the ``ClientSession`` boundary. Covers the IoT
envelope POST, the OpenAccount form POST, the ``status >= 400`` path,
``ClientError`` wrapping, and session ownership.
"""

from __future__ import annotations

import aiohttp
import pytest

from neakasa_litterbox_sdk.aliyun.transport import AliyunTransport, _encode_oa_body
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
    def __init__(
        self, response: _FakeResponse | None = None, raise_exc: Exception | None = None
    ) -> None:
        self._response = response
        self._raise_exc = raise_exc
        self.closed = False
        self.last_post: tuple[str, bytes, dict[str, str]] | None = None

    def post(self, url: str, data: bytes, headers: dict[str, str]) -> _FakeResponse:
        self.last_post = (url, data, headers)
        if self._raise_exc is not None:
            raise self._raise_exc
        assert self._response is not None
        return self._response

    async def close(self) -> None:
        self.closed = True


async def test_call_posts_iot_envelope() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"code": 200, "data": {"ok": true}}'))
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    result = await transport.call(
        "/uc/listBindingByAccount",
        api_version="1.0.8",
        iot_token="tok",
        payload={},
    )
    assert result == {"code": 200, "data": {"ok": True}}
    assert session.last_post is not None
    url, body, headers = session.last_post
    assert "x-ca-request-id=" in url
    assert b'"apiVer":"1.0.8"' in body
    assert headers["x-ca-key"]


async def test_call_oa_form_encodes_and_signs() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"success": "true"}'))
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    await transport.call_oa(
        "/api/prd/connect.json",
        host="oa.example.com",
        body={"request": {"context": {"appKey": "k"}}},
        extra_headers={"vid": "v1"},
    )
    assert session.last_post is not None
    url, body, headers = session.last_post
    assert url == "https://oa.example.com/api/prd/connect.json"
    assert headers["vid"] == "v1"
    assert body.startswith(b"request=")


async def test_post_error_status_raises_transport_error() -> None:
    session = _FakeSession(_FakeResponse(500, b"internal error"))
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError) as exc_info:
        await transport.call("/x", api_version="1.0", payload={})
    assert exc_info.value.status_code == 500
    assert "internal error" in str(exc_info.value)


async def test_post_client_error_is_wrapped() -> None:
    session = _FakeSession(raise_exc=aiohttp.ClientError("network down"))
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError, match="Failed to POST"):
        await transport.call("/x", api_version="1.0", payload={})


async def test_post_timeout_is_wrapped() -> None:
    # aiohttp raises the builtin TimeoutError on ``ClientTimeout``; it is not
    # a ClientError, so it has to be caught explicitly or it escapes the SDK.
    session = _FakeSession(raise_exc=TimeoutError)
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    with pytest.raises(TransportError, match="Failed to POST"):
        await transport.call("/x", api_version="1.0", payload={})


async def test_close_closes_owned_session(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = AliyunTransport()
    created = _FakeSession(_FakeResponse(200, b'{"code": 200}'))
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.aliyun.transport.aiohttp.ClientSession",
        lambda timeout: created,
    )
    await transport.call("/x", api_version="1.0", payload={})
    assert transport._session is created
    await transport.close()
    assert created.closed is True
    assert transport._session is None


async def test_close_does_not_close_injected_session() -> None:
    session = _FakeSession(_FakeResponse(200, b'{"code": 200}'))
    transport = AliyunTransport(session=session)  # type: ignore[arg-type]
    await transport.close()
    assert session.closed is False


def test_encode_oa_body_url_encoded_vs_canonical() -> None:
    body = {"a": {"b": "c d"}}
    canonical = _encode_oa_body(body, url_encoded=False)
    encoded = _encode_oa_body(body, url_encoded=True)
    assert canonical == 'a={"b":"c d"}'
    assert encoded == "a=%7B%22b%22%3A%22c+d%22%7D"
