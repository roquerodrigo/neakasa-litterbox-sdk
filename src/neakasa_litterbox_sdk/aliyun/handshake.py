"""Exchange the Neakasa REST ``aliAuthenticationToken`` for an Aliyun ``iotToken``.

Four-step pipeline:

1. ``POST cn-shanghai.api-iot.aliyuncs.com/living/account/region/get``
   with ``authCode = <aliAuthenticationToken>`` → returns the regional
   ``oaApiGatewayEndpoint`` and ``apiGatewayEndpoint``.
2. ``POST <oaApiGatewayEndpoint>/api/prd/connect.json`` → returns a
   ``vid`` (visitor id).
3. ``POST <oaApiGatewayEndpoint>/api/prd/loginbyoauth.json`` with
   ``authCode = <aliAuthenticationToken>`` and the ``Vid`` header →
   returns a ``sid`` (OpenAccount session id).
4. ``POST <apiGatewayEndpoint>/account/createSessionByAuthCode`` with
   ``authCode = <sid>`` → returns the final ``iotToken``.

Step 1 always hits ``cn-shanghai``; the regional split happens in the
response so the rest of the chain follows the user's region.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .._credentials import APP_KEY
from ..exceptions import ApiError, AuthenticationError, NeakasaError
from ..utils._json import JsonObject, get_object, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonValue
    from .transport import AliyunTransport

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.aliyun.handshake")

_BOOTSTRAP_HOST = "cn-shanghai.api-iot.aliyuncs.com"


async def exchange_for_iot_token(
    transport: AliyunTransport,
    ali_authentication_token: str,
    *,
    language: str = "en-US",
) -> str:
    """Run the 4-step OpenAccount handshake and return the ``iotToken``."""
    if not ali_authentication_token:
        raise NeakasaError(
            "Failed to authenticate Aliyun: aliAuthenticationToken is empty",
        )
    oa_endpoint, api_endpoint = await _get_region(transport, ali_authentication_token, language)
    vid = await _get_vid(transport, oa_endpoint)
    sid = await _get_sid(transport, oa_endpoint, vid, ali_authentication_token)
    return await _create_iot_token(transport, api_endpoint, sid, language)


async def _get_region(
    transport: AliyunTransport,
    auth_code: str,
    language: str,
) -> tuple[str, str]:
    response = await transport.call(
        "/living/account/region/get",
        api_version="1.0.2",
        host=_BOOTSTRAP_HOST,
        payload={"authCode": auth_code, "type": "THIRD_AUTHCODE"},
        language=language,
    )
    data = _expect_iot_success(response, context="get Aliyun region")
    oa = get_str(data, "oaApiGatewayEndpoint")
    api = get_str(data, "apiGatewayEndpoint")
    if not oa or not api:
        raise ApiError(
            "Failed to get Aliyun region: missing oaApiGatewayEndpoint/apiGatewayEndpoint",
            code=-1,
        )
    log.debug("Aliyun region resolved: oa=%s api=%s", oa, api)
    return oa, api


async def _get_vid(transport: AliyunTransport, oa_endpoint: str) -> str:
    body: dict[str, JsonValue] = {
        "request": {
            "context": {"appKey": APP_KEY},
            "config": {"version": 0, "lastModify": 0},
            "device": {},
        }
    }
    response = await transport.call_oa("/api/prd/connect.json", host=oa_endpoint, body=body)
    _expect_oa_success(response, context="get Aliyun vid")
    data = get_object(response, "data")
    vid = get_str(data, "vid")
    if not vid:
        raise ApiError("Failed to get Aliyun vid: missing 'vid' in response", code=-1)
    return vid


async def _get_sid(
    transport: AliyunTransport,
    oa_endpoint: str,
    vid: str,
    auth_code: str,
) -> str:
    body: dict[str, JsonValue] = {
        "loginByOauthRequest": {
            "authCode": auth_code,
            "oauthPlateform": 23,
            "oauthAppKey": APP_KEY,
            "riskControlInfo": {},
        }
    }
    response = await transport.call_oa(
        "/api/prd/loginbyoauth.json",
        host=oa_endpoint,
        body=body,
        extra_headers={"vid": vid},
    )
    _expect_oa_success(response, context="get Aliyun sid", auth=True)
    inner_data = get_object(get_object(response, "data"), "data")
    login_success = get_object(inner_data, "loginSuccessResult")
    sid = get_str(login_success, "sid")
    if not sid:
        raise AuthenticationError(
            "Failed to get Aliyun sid: missing 'sid' in response",
            code=-1,
        )
    return sid


async def _create_iot_token(
    transport: AliyunTransport,
    api_endpoint: str,
    sid: str,
    language: str,
) -> str:
    response = await transport.call(
        "/account/createSessionByAuthCode",
        api_version="1.0.4",
        host=api_endpoint,
        payload={
            "request": {
                "authCode": sid,
                "accountType": "OA_SESSION",
                "appKey": APP_KEY,
            }
        },
        language=language,
    )
    data = _expect_iot_success(response, context="create Aliyun iotToken", auth=True)
    iot_token = get_str(data, "iotToken")
    if not iot_token:
        raise AuthenticationError(
            "Failed to create Aliyun iotToken: missing 'iotToken' in response",
            code=-1,
        )
    return iot_token


def _expect_iot_success(
    envelope: JsonObject,
    *,
    context: str,
    auth: bool = False,
) -> JsonObject:
    """Aliyun IoT envelope returns ``code: 200`` on success (not 0)."""
    code = _get_code(envelope)
    message = get_str(envelope, "message")
    if code != 200:
        cls = AuthenticationError if auth else ApiError
        raise cls(
            f"Failed to {context}: server returned code {code}",
            code=code,
            server_message=message or None,
        )
    return get_object(envelope, "data")


def _expect_oa_success(
    envelope: JsonObject,
    *,
    context: str,
    auth: bool = False,
) -> None:
    """OA endpoints flag success via two nested ``"true"``/``"false"`` strings."""
    top = get_str(envelope, "success")
    if top != "true":
        cls = AuthenticationError if auth else ApiError
        err_msg = get_str(envelope, "errorMsg") or get_str(envelope, "message")
        raise cls(
            f"Failed to {context}: success={top!r}",
            code=-1,
            server_message=err_msg or None,
        )
    inner = get_object(envelope, "data")
    inner_flag = get_str(inner, "successful")
    if inner_flag != "true":
        cls = AuthenticationError if auth else ApiError
        raise cls(
            f"Failed to {context}: data.successful={inner_flag!r}",
            code=-1,
            server_message=get_str(inner, "message") or None,
        )


def _get_code(envelope: JsonObject) -> int:
    value = envelope.get("code")
    if isinstance(value, bool) or not isinstance(value, int):
        return -1
    return value
