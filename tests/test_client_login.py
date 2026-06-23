"""``NeakasaClient.login`` flows: fresh, cached resume, and identity contract."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from neakasa_litterbox_sdk import LoginResult, NeakasaClient, Region, UserInfo

if TYPE_CHECKING:
    import pytest


def _user_info(*, ali_token: str = "ali-auth-token") -> UserInfo:
    return UserInfo(
        user_id=42,
        user_name="user@example.com",
        ali_user_id=400068852,
        ali_authentication_token=ali_token,
    )


def _login_result(*, iot_token: str = "") -> LoginResult:
    return LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        user_info=_user_info(),
        issued_at=1_700_000_000.0,
        iot_token=iot_token,
    )


def _client() -> NeakasaClient:
    return NeakasaClient(email="user@example.com", password="pw", region=Region.US)


async def test_login_fresh_runs_rest_then_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    """No cache: a REST login then the Aliyun handshake both run, in order."""
    client = _client()
    calls: list[str] = []

    async def _rest() -> None:
        calls.append("rest")
        client._login_result = _login_result()

    async def _aliyun() -> str:
        calls.append("aliyun")
        client._login_result = _login_result(iot_token="iot-token")
        return "iot-token"

    monkeypatch.setattr(client, "_login_rest", _rest)
    monkeypatch.setattr(client, "_authenticate_aliyun", _aliyun)

    result = await client.login()

    assert calls == ["rest", "aliyun"]
    assert result.iot_token == "iot-token"
    assert client.is_authenticated


async def test_login_cached_with_iot_token_mints_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete cached session resumes with no network and returns the same object."""
    client = _client()
    rest_mock = AsyncMock()
    aliyun_mock = AsyncMock()
    monkeypatch.setattr(client, "_login_rest", rest_mock)
    monkeypatch.setattr(client, "_authenticate_aliyun", aliyun_mock)

    cached = _login_result(iot_token="cached-iot-token")
    result = await client.login(cached=cached)

    # Identity contract: nothing minted -> the very object passed in.
    assert result is cached
    rest_mock.assert_not_awaited()
    aliyun_mock.assert_not_awaited()


async def test_login_cached_with_iot_token_restores_cached_aliyun_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client()
    monkeypatch.setattr(client, "_login_rest", AsyncMock())
    monkeypatch.setattr(client, "_authenticate_aliyun", AsyncMock())

    cached = _login_result(iot_token="cached-iot-token").with_iot_session(
        "cached-iot-token",
        "eu-central-1.api-iot.aliyuncs.com",
    )
    result = await client.login(cached=cached)

    assert result is cached
    assert client._aliyun_host == "eu-central-1.api-iot.aliyuncs.com"


async def test_login_cached_without_iot_token_only_handshakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cached REST session missing the IoT token mints only the IoT session."""
    client = _client()
    rest_mock = AsyncMock()
    monkeypatch.setattr(client, "_login_rest", rest_mock)

    cached = _login_result(iot_token="")

    async def _aliyun() -> str:
        client._login_result = cached.with_iot_token("fresh-iot-token")
        return "fresh-iot-token"

    monkeypatch.setattr(client, "_authenticate_aliyun", _aliyun)

    result = await client.login(cached=cached)

    rest_mock.assert_not_awaited()
    # Something was minted -> a fresh instance, not the cached one.
    assert result is not cached
    assert result.iot_token == "fresh-iot-token"


def test_region_property() -> None:
    assert _client().region is Region.US


def test_login_result_property_starts_none() -> None:
    client = _client()
    assert client.login_result is None
    assert client.is_authenticated is False
