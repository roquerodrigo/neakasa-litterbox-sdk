"""Verify the envelope unwrappers pick the right exception class for each code."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk import (
    ApiError,
    AuthenticationError,
    GatewayTimeoutError,
    InvalidCredentialsError,
    NeakasaClient,
    SessionExpiredError,
)
from neakasa_litterbox_sdk.client import _unwrap_aliyun, _unwrap_envelope


def _envelope(code: int) -> dict[str, object]:
    return {
        "request_id": "test",
        "code": code,
        "message": "test error",
        "data": None,
    }


def test_zero_code_returns_data() -> None:
    envelope = {"code": 0, "data": {"hello": "world"}}
    assert _unwrap_envelope(envelope, context="probe") == {"hello": "world"}


@pytest.mark.parametrize("code", [1007, 3026, 3027])
def test_session_expired_codes_dispatch_to_session_expired_error(code: int) -> None:
    with pytest.raises(SessionExpiredError) as exc_info:
        _unwrap_envelope(_envelope(code), context="probe", auth=True)
    assert exc_info.value.code == code
    assert isinstance(exc_info.value, AuthenticationError)


@pytest.mark.parametrize("code", [3019, 10060, 10061, 10192])
def test_invalid_credentials_codes_dispatch_to_invalid_credentials_error(code: int) -> None:
    with pytest.raises(InvalidCredentialsError) as exc_info:
        _unwrap_envelope(_envelope(code), context="probe", auth=True)
    assert exc_info.value.code == code
    assert isinstance(exc_info.value, AuthenticationError)


def test_unknown_auth_code_falls_back_to_authentication_error() -> None:
    with pytest.raises(AuthenticationError) as exc_info:
        _unwrap_envelope(_envelope(10050), context="probe", auth=True)
    assert exc_info.value.code == 10050
    assert not isinstance(exc_info.value, SessionExpiredError)
    assert not isinstance(exc_info.value, InvalidCredentialsError)


def test_non_auth_context_uses_plain_api_error() -> None:
    with pytest.raises(ApiError) as exc_info:
        _unwrap_envelope(_envelope(1007), context="probe", auth=False)
    assert exc_info.value.code == 1007
    assert not isinstance(exc_info.value, AuthenticationError)


def test_error_text_quotes_the_server_message() -> None:
    with pytest.raises(
        ApiError, match=r"^Failed to probe: server returned code 1001 \(test error\)$"
    ):
        _unwrap_envelope(_envelope(1001), context="probe")


def test_error_text_without_server_message() -> None:
    with pytest.raises(ApiError, match=r"^Failed to probe: server returned code 1001$"):
        _unwrap_envelope({"code": 1001}, context="probe")


def test_aliyun_gateway_timeout_dispatches_to_gateway_timeout_error() -> None:
    envelope = {
        "code": 20056,
        "id": "request-id",
        "localizedMsg": "\u540e\u7aef\u670d\u52a1\u8d85\u65f6",
        "message": "gateway.hsf.invoke.timeout",
    }
    with pytest.raises(GatewayTimeoutError) as exc_info:
        _unwrap_aliyun(envelope, context="get device status")
    assert exc_info.value.code == 20056
    assert exc_info.value.server_message == "gateway.hsf.invoke.timeout"
    assert str(exc_info.value) == (
        "Failed to get device status: server returned code 20056 (gateway.hsf.invoke.timeout)"
    )
    assert not isinstance(exc_info.value, AuthenticationError)


async def test_gateway_timeout_is_not_replayed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    monkeypatch.setattr(client, "_require_iot_session", lambda: "iot-token")
    call_mock = AsyncMock(return_value={"code": 20056, "message": "gateway.hsf.invoke.timeout"})
    monkeypatch.setattr(client._aliyun, "call", call_mock)
    with pytest.raises(GatewayTimeoutError):
        await client._aliyun_call_authed(
            "/thing/properties/get",
            api_version="1.0.4",
            payload={},
            language="en-US",
            context="get device status",
        )
    assert call_mock.await_count == 1
