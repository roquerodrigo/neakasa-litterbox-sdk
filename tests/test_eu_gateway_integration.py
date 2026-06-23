"""End-to-end regional-gateway routing through the real client + transport.

Unlike the unit tests that mock ``AliyunTransport.call`` directly, this
exercises the full ``NeakasaClient`` -> ``AliyunTransport`` -> aiohttp stack,
mocking only the HTTP boundary. It proves the regional ``apiGatewayEndpoint``
resolved during the handshake actually reaches the request URL of a subsequent
device call -- the exact path that regressed for EU devices
(ha-neakasa-litterbox#36): the iotToken was minted on the EU gateway but
``/uc/listBindingByAccount`` was replayed against the hardcoded US gateway.
"""

from __future__ import annotations

import json

from neakasa_litterbox_sdk import LoginResult, NeakasaClient, Region, UserInfo

_EU_HOST = "eu-central-1.api-iot.aliyuncs.com"
_EU_OA_HOST = "oa-eu.example.com"
_BOOTSTRAP_HOST = "cn-shanghai.api-iot.aliyuncs.com"
_US_HOST = "us-east-1.api-iot.aliyuncs.com"


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.status = 200
        self._body = json.dumps(payload).encode("utf-8")

    async def read(self) -> bytes:
        return self._body

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _RecordingSession:
    """aiohttp stand-in: replays queued responses and records every POST URL."""

    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.urls: list[str] = []

    def post(self, url: str, data: bytes, headers: dict[str, str]) -> _FakeResponse:
        self.urls.append(url)
        return _FakeResponse(self._responses.pop(0))

    async def close(self) -> None:
        return None


def _rest_session() -> LoginResult:
    """A REST login that's complete except for the (not-yet-minted) IoT token."""
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
    )


def _handshake_responses() -> list[dict[str, object]]:
    """The 5 POSTs: region -> vid -> sid -> iotToken -> listBindingByAccount."""
    return [
        # /living/account/region/get -> resolves the EU regional endpoints
        {
            "code": 200,
            "data": {"oaApiGatewayEndpoint": _EU_OA_HOST, "apiGatewayEndpoint": _EU_HOST},
        },
        # connect.json -> vid
        {"success": "true", "data": {"successful": "true", "vid": "vid-123"}},
        # loginbyoauth.json -> sid
        {
            "success": "true",
            "data": {"successful": "true", "data": {"loginSuccessResult": {"sid": "sid-456"}}},
        },
        # createSessionByAuthCode -> iotToken
        {"code": 200, "data": {"iotToken": "iot-token-789"}},
        # listBindingByAccount -> empty device list
        {"code": 200, "data": {"data": []}},
    ]


async def test_eu_device_call_routes_through_regional_gateway() -> None:
    client = NeakasaClient(email="user@example.com", password="pw", region=Region.EU)
    session = _RecordingSession(_handshake_responses())
    # Inject the fake HTTP session into the real AliyunTransport.
    client._aliyun._session = session  # type: ignore[assignment]
    client._aliyun._owns_session = False

    # Seed a REST session so login() skips _login_rest and runs only the
    # Aliyun handshake, then make a real device call.
    await client.login(cached=_rest_session())
    devices = await client.list_devices()

    assert devices == []
    assert client._aliyun_host == _EU_HOST

    region_url, _vid_url, _sid_url, token_url, list_url = session.urls
    # Bootstrap discovery always starts at the cn-shanghai gateway.
    assert region_url.startswith(f"https://{_BOOTSTRAP_HOST}/living/account/region/get")
    # Token mint already used the regional host (correct before the fix too).
    assert token_url.startswith(f"https://{_EU_HOST}/account/createSessionByAuthCode")
    # The fix: the device call must hit the regional gateway, not us-east-1.
    assert list_url.startswith(f"https://{_EU_HOST}/uc/listBindingByAccount")
    assert _US_HOST not in list_url
