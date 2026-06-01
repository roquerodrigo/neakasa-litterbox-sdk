"""The 4-step OpenAccount handshake that mints the Aliyun ``iotToken``.

The :class:`AliyunTransport` is mocked at the ``call`` / ``call_oa``
boundary with response fixtures shaped like the live gateway. No
network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk.aliyun.handshake import exchange_for_iot_token
from neakasa_litterbox_sdk.exceptions import ApiError, AuthenticationError, NeakasaError


def _region_response() -> dict[str, object]:
    return {
        "code": 200,
        "data": {
            "oaApiGatewayEndpoint": "oa.example.com",
            "apiGatewayEndpoint": "api.example.com",
        },
    }


def _vid_response() -> dict[str, object]:
    return {"success": "true", "data": {"successful": "true", "vid": "vid-123"}}


def _sid_response() -> dict[str, object]:
    return {
        "success": "true",
        "data": {
            "successful": "true",
            "data": {"loginSuccessResult": {"sid": "sid-456"}},
        },
    }


def _token_response() -> dict[str, object]:
    return {"code": 200, "data": {"iotToken": "iot-token-789"}}


def _transport(
    *, call_side: list[object] | None = None, oa_side: list[object] | None = None
) -> AsyncMock:
    transport = AsyncMock()
    if call_side is not None:
        transport.call = AsyncMock(side_effect=call_side)
    if oa_side is not None:
        transport.call_oa = AsyncMock(side_effect=oa_side)
    return transport


async def test_full_handshake_returns_iot_token() -> None:
    transport = _transport(
        call_side=[_region_response(), _token_response()],
        oa_side=[_vid_response(), _sid_response()],
    )
    token = await exchange_for_iot_token(transport, "ali-auth-token")
    assert token == "iot-token-789"
    assert transport.call.await_count == 2
    assert transport.call_oa.await_count == 2


async def test_empty_auth_token_raises_before_network() -> None:
    transport = _transport(call_side=[], oa_side=[])
    with pytest.raises(NeakasaError, match="aliAuthenticationToken is empty"):
        await exchange_for_iot_token(transport, "")
    transport.call.assert_not_awaited()


async def test_region_non_200_raises_apierror() -> None:
    transport = _transport(call_side=[{"code": 500, "message": "boom"}])
    with pytest.raises(ApiError, match="get Aliyun region"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_region_missing_endpoints_raises() -> None:
    transport = _transport(call_side=[{"code": 200, "data": {"oaApiGatewayEndpoint": ""}}])
    with pytest.raises(ApiError, match="missing oaApiGatewayEndpoint"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_vid_top_level_failure_raises() -> None:
    transport = _transport(
        call_side=[_region_response()],
        oa_side=[{"success": "false", "errorMsg": "nope"}],
    )
    with pytest.raises(ApiError, match="get Aliyun vid"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_vid_inner_failure_raises() -> None:
    transport = _transport(
        call_side=[_region_response()],
        oa_side=[{"success": "true", "data": {"successful": "false", "message": "bad"}}],
    )
    with pytest.raises(ApiError, match=r"data\.successful"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_vid_missing_value_raises() -> None:
    transport = _transport(
        call_side=[_region_response()],
        oa_side=[{"success": "true", "data": {"successful": "true"}}],
    )
    with pytest.raises(ApiError, match="missing 'vid'"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_sid_failure_raises_authentication_error() -> None:
    transport = _transport(
        call_side=[_region_response()],
        oa_side=[
            _vid_response(),
            {"success": "false", "errorMsg": "denied"},
        ],
    )
    with pytest.raises(AuthenticationError, match="get Aliyun sid"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_sid_missing_value_raises_authentication_error() -> None:
    transport = _transport(
        call_side=[_region_response()],
        oa_side=[
            _vid_response(),
            {"success": "true", "data": {"successful": "true", "data": {}}},
        ],
    )
    with pytest.raises(AuthenticationError, match="missing 'sid'"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_create_token_non_200_raises_authentication_error() -> None:
    transport = _transport(
        call_side=[_region_response(), {"code": 401, "message": "expired"}],
        oa_side=[_vid_response(), _sid_response()],
    )
    with pytest.raises(AuthenticationError, match="create Aliyun iotToken"):
        await exchange_for_iot_token(transport, "ali-auth-token")


async def test_create_token_missing_value_raises() -> None:
    transport = _transport(
        call_side=[_region_response(), {"code": 200, "data": {}}],
        oa_side=[_vid_response(), _sid_response()],
    )
    with pytest.raises(AuthenticationError, match="missing 'iotToken'"):
        await exchange_for_iot_token(transport, "ali-auth-token")


def test_get_code_rejects_bool_and_non_int() -> None:
    from neakasa_litterbox_sdk.aliyun.handshake import _get_code

    assert _get_code({"code": True}) == -1
    assert _get_code({"code": "200"}) == -1
    assert _get_code({"code": 200}) == 200
    assert _get_code({}) == -1
