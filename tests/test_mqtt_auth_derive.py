"""``derive_mqtt_credentials``: bootstrap REST + credential assembly."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk.aliyun.mqtt_auth import derive_mqtt_credentials
from neakasa_litterbox_sdk.exceptions import ApiError


def _transport(response: dict[str, object]) -> AsyncMock:
    transport = AsyncMock()
    transport.call = AsyncMock(return_value=response)
    return transport


async def test_derive_assembles_client_id_username_password() -> None:
    triple = {"productKey": "pk1", "deviceName": "dn1", "deviceSecret": "secret"}
    transport = _transport({"code": 200, "data": triple})

    creds = await derive_mqtt_credentials(transport)

    assert creds.username == "dn1&pk1"
    assert creds.client_id == "dn1&pk1|securemode=2,signmethod=hmacsha1,ext=1|"
    assert creds.host == "pk1.iot-as-mqtt.us-east-1.aliyuncs.com"
    assert creds.port == 1883
    assert creds.product_key == "pk1"
    assert creds.device_name == "dn1"

    expected = (
        hmac.new(
            b"secret",
            b"clientIddn1&pk1deviceNamedn1productKeypk1",
            hashlib.sha1,
        )
        .hexdigest()
        .upper()
    )
    assert creds.password == expected


async def test_derive_defaults_to_us_gateway() -> None:
    triple = {"productKey": "pk1", "deviceName": "dn1", "deviceSecret": "secret"}
    transport = _transport({"code": 200, "data": triple})

    await derive_mqtt_credentials(transport)

    # No gateway threaded through -> bootstrap REST still hits us-east-1.
    assert transport.call.await_args.kwargs["host"] == "us-east-1.api-iot.aliyuncs.com"


async def test_derive_follows_regional_gateway() -> None:
    triple = {"productKey": "pk1", "deviceName": "dn1", "deviceSecret": "secret"}
    transport = _transport({"code": 200, "data": triple})

    creds = await derive_mqtt_credentials(
        transport, gateway_host="eu-central-1.api-iot.aliyuncs.com"
    )

    # MQTT broker and bootstrap REST must follow the account's region, not
    # the hardcoded us-east-1 (otherwise bind_account is rejected, code 2043).
    assert creds.host == "pk1.iot-as-mqtt.eu-central-1.aliyuncs.com"
    assert transport.call.await_args.kwargs["host"] == "eu-central-1.api-iot.aliyuncs.com"


async def test_derive_raises_on_non_200_code() -> None:
    transport = _transport({"code": 403, "message": "denied"})
    with pytest.raises(ApiError, match="bootstrap MQTT credentials"):
        await derive_mqtt_credentials(transport)


async def test_derive_raises_when_data_not_object() -> None:
    transport = _transport({"code": 200, "data": "oops"})
    with pytest.raises(ApiError, match="'data' is not an object"):
        await derive_mqtt_credentials(transport)


async def test_derive_raises_on_empty_triple_fields() -> None:
    transport = _transport(
        {"code": 200, "data": {"productKey": "pk", "deviceName": "", "deviceSecret": "s"}}
    )
    with pytest.raises(ApiError, match="empty productKey/deviceName/deviceSecret"):
        await derive_mqtt_credentials(transport)
