"""Session lifecycle, REST login, Aliyun bootstrap, and envelope helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk import ApiError, LoginResult, NeakasaClient, UserInfo
from neakasa_litterbox_sdk.aliyun.handshake import AliyunSession
from neakasa_litterbox_sdk.client import _expect_object


def _login_result(*, iot_token: str = "") -> LoginResult:
    return LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        user_info=UserInfo(
            user_id=42,
            user_name="user@example.com",
            ali_user_id=400068852,
            ali_authentication_token="ali-auth-token",
        ),
        issued_at=1_700_000_000.0,
        iot_token=iot_token,
    )


async def test_close_delegates_to_both_transports(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    rest_close = AsyncMock()
    aliyun_close = AsyncMock()
    monkeypatch.setattr(client._transport, "close", rest_close)
    monkeypatch.setattr(client._aliyun, "close", aliyun_close)

    await client.close()

    rest_close.assert_awaited_once()
    aliyun_close.assert_awaited_once()


async def test_async_context_manager_closes_on_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    close_mock = AsyncMock()
    monkeypatch.setattr(client, "close", close_mock)

    async with client as entered:
        assert entered is client
    close_mock.assert_awaited_once()


async def test_login_rest_parses_and_stores(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_login_rest`` unwraps the envelope, builds a LoginResult, and stores it."""
    client = NeakasaClient(email="user@example.com", password="pw")
    envelope = {
        "code": 0,
        "data": {
            "loginToken": "",
            "userInfo": {
                "userId": 42,
                "userName": "user@example.com",
                "aliUserId": 400068852,
                "aliAuthenticationToken": "ali-auth-token",
            },
        },
    }
    monkeypatch.setattr(
        client._transport,
        "signed_get_data_envelope",
        AsyncMock(return_value=envelope),
    )

    result = await client._login_rest()

    assert result.user_id == "400068852"
    assert result.user_info.ali_authentication_token == "ali-auth-token"
    assert client.login_result is result


async def test_authenticate_aliyun_stores_iot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_authenticate_aliyun`` runs the handshake and stamps the iotToken."""
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.client.exchange_for_iot_session",
        AsyncMock(
            return_value=AliyunSession(
                iot_token="fresh-iot-token",
                api_gateway_endpoint="eu-central-1.api-iot.aliyuncs.com",
            )
        ),
    )

    token = await client._authenticate_aliyun()

    assert token == "fresh-iot-token"
    assert client.login_result is not None
    assert client.login_result.iot_token == "fresh-iot-token"
    assert client.login_result.iot_host == "eu-central-1.api-iot.aliyuncs.com"


def test_expect_object_passes_through_mapping() -> None:
    assert _expect_object({"a": 1}, context="probe") == {"a": 1}


@pytest.mark.parametrize("value", [[], "str", 5, None])
def test_expect_object_rejects_non_object(value: object) -> None:
    with pytest.raises(ApiError, match="expected object in response"):
        _expect_object(value, context="probe")  # type: ignore[arg-type]
