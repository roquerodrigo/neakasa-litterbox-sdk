"""Auto-refresh of the Aliyun ``iotToken`` on 401 responses."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk.client import _unwrap_aliyun
from neakasa_litterbox_sdk.exceptions import (
    ApiError,
    SessionExpiredError,
)


def test_unwrap_aliyun_maps_401_to_session_expired() -> None:
    envelope = {"code": 401, "message": "iotToken is invalid"}
    with pytest.raises(SessionExpiredError) as exc_info:
        _unwrap_aliyun(envelope, context="list devices")
    assert exc_info.value.code == 401
    assert exc_info.value.server_message == "iotToken is invalid"


def test_unwrap_aliyun_other_errors_stay_apierror() -> None:
    envelope = {"code": 500, "message": "internal"}
    with pytest.raises(ApiError) as exc_info:
        _unwrap_aliyun(envelope, context="list devices")
    assert not isinstance(exc_info.value, SessionExpiredError)
    assert exc_info.value.code == 500


def test_unwrap_aliyun_returns_data_on_success() -> None:
    envelope = {"code": 200, "data": {"items": []}}
    assert _unwrap_aliyun(envelope, context="list devices") == {"items": []}


def _make_client(monkeypatch: pytest.MonkeyPatch):
    from neakasa_litterbox_sdk.client import NeakasaClient

    client = NeakasaClient(email="user@example.com", password="pw")
    # Pretend ``login()`` already ran — bypass the network round-trips
    # so the test focuses on the retry behavior alone.
    monkeypatch.setattr(client, "_require_iot_session", lambda: "iot-token-0")
    return client


async def test_aliyun_call_authed_refreshes_on_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client(monkeypatch)
    responses = iter(
        [
            {"code": 401, "message": "expired"},
            {"code": 200, "data": {"ok": True}},
        ]
    )
    call_mock = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(client._aliyun, "call", call_mock)
    refresh_mock = AsyncMock(return_value="iot-token-1")
    monkeypatch.setattr(client, "_authenticate_aliyun", refresh_mock)

    data = await client._aliyun_call_authed(
        "/uc/listBindingByAccount",
        api_version="1.0.8",
        payload={},
        language="en-US",
        context="list devices",
    )
    assert data == {"ok": True}
    refresh_mock.assert_awaited_once()
    assert call_mock.await_count == 2


async def test_aliyun_call_authed_propagates_second_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client(monkeypatch)
    call_mock = AsyncMock(return_value={"code": 401, "message": "expired"})
    monkeypatch.setattr(client._aliyun, "call", call_mock)
    refresh_mock = AsyncMock(return_value="iot-token-1")
    monkeypatch.setattr(client, "_authenticate_aliyun", refresh_mock)

    with pytest.raises(SessionExpiredError):
        await client._aliyun_call_authed(
            "/uc/listBindingByAccount",
            api_version="1.0.8",
            payload={},
            language="en-US",
            context="list devices",
        )
    refresh_mock.assert_awaited_once()
    assert call_mock.await_count == 2


async def test_aliyun_call_authed_passes_through_on_first_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client(monkeypatch)
    call_mock = AsyncMock(return_value={"code": 200, "data": [{"id": 1}]})
    monkeypatch.setattr(client._aliyun, "call", call_mock)
    refresh_mock = AsyncMock()
    monkeypatch.setattr(client, "_authenticate_aliyun", refresh_mock)

    data = await client._aliyun_call_authed(
        "/uc/listBindingByAccount",
        api_version="1.0.8",
        payload={},
        language="en-US",
        context="list devices",
    )
    assert data == [{"id": 1}]
    refresh_mock.assert_not_awaited()
    assert call_mock.await_count == 1
