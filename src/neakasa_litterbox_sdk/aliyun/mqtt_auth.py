"""Aliyun mobile-channel MQTT credential derivation.

Two stages used to authenticate the SDK as an Aliyun mobile-channel
client:

1. **Bootstrap REST** — POST ``/app/aepauth/handle`` (apiVer 1.0.0) on
   the regional IoT API gateway with a signed ``authInfo`` block; the
   response returns a per-session ``(productKey, deviceName,
   deviceSecret)`` triple that authenticates the SDK as an Aliyun
   "device".

2. **MQTT credential derivation** — combine the triple into the
   ``(client_id, username, password)`` tuple paho-mqtt expects::

       client_id = "<dn>&<pk>|securemode=2,signmethod=hmacsha1,ext=1|"
       username  = "<dn>&<pk>"
       password  = hex_UPPER(HMAC-SHA1(deviceSecret,
                     "clientId<bare>deviceName<dn>productKey<pk>"))

Sign canonical strings concatenate **key+value** for each parameter in
alphabetical key order, no separators.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .._credentials import APP_KEY, APP_SECRET
from ..exceptions import ApiError
from ..utils._json import get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject
    from .transport import AliyunTransport

_BOOTSTRAP_PATH = "/app/aepauth/handle"
_BOOTSTRAP_API_VERSION = "1.0.0"
# The bootstrap REST and the broker host both have to be regional —
# verified live, ``api.link.aliyun.com`` (the SDK's default) returns a
# triple whose broker is in cn-shanghai and rejects bind from an
# iotToken minted in any other region. Sticking to the same region the
# rest of the SDK targets (us-east-1) keeps bind happy.
_BOOTSTRAP_HOST = "us-east-1.api-iot.aliyuncs.com"

_MQTT_HOST_TEMPLATE = "{product_key}.iot-as-mqtt.us-east-1.aliyuncs.com"
# Aliyun's mobile-channel broker speaks TLS on port 1883, not the standard
# 8883 — the SDK's ``DEFAULT_HOST`` constant pins it explicitly and the
# ``ssl://`` prefix is applied separately based on ``SECURE_MODE``.
_MQTT_PORT = 1883
_MQTT_CLIENT_ID_SUFFIX = "|securemode=2,signmethod=hmacsha1,ext=1|"


@dataclass(frozen=True, slots=True)
class MqttCredentials:
    """Everything paho-mqtt needs to open an Aliyun mobile-channel session.

    ``product_key`` / ``device_name`` are kept on the side because the
    user-scoped subscribe topics carry them in the path
    (``/sys/<product_key>/<device_name>/app/down/...``).
    """

    host: str
    port: int
    client_id: str
    username: str
    password: str
    product_key: str
    device_name: str


async def derive_mqtt_credentials(transport: AliyunTransport) -> MqttCredentials:
    """Run the bootstrap REST and return the resulting MQTT credentials."""
    triple = await _fetch_triple(transport)
    product_key = get_str(triple, "productKey")
    device_name = get_str(triple, "deviceName")
    device_secret = get_str(triple, "deviceSecret")
    if not product_key or not device_name or not device_secret:
        raise ApiError(
            "Failed to derive MQTT credentials: empty productKey/deviceName/deviceSecret",
            code=-1,
        )

    bare_client_id = f"{device_name}&{product_key}"
    password_sign_string = f"clientId{bare_client_id}deviceName{device_name}productKey{product_key}"
    password = (
        hmac.new(
            device_secret.encode("utf-8"),
            password_sign_string.encode("utf-8"),
            hashlib.sha1,
        )
        .hexdigest()
        .upper()
    )

    return MqttCredentials(
        host=_MQTT_HOST_TEMPLATE.format(product_key=product_key),
        port=_MQTT_PORT,
        client_id=f"{bare_client_id}{_MQTT_CLIENT_ID_SUFFIX}",
        username=bare_client_id,
        password=password,
        product_key=product_key,
        device_name=device_name,
    )


async def _fetch_triple(transport: AliyunTransport) -> JsonObject:
    """POST ``/app/aepauth/handle`` and return the response ``data`` map."""
    auth_info = _build_auth_info()
    response = await transport.call(
        _BOOTSTRAP_PATH,
        api_version=_BOOTSTRAP_API_VERSION,
        host=_BOOTSTRAP_HOST,
        payload={"authInfo": auth_info},
    )
    code = get_int(response, "code", default=-1)
    if code != 200:
        raise ApiError(
            f"Failed to bootstrap MQTT credentials: server returned code {code}",
            code=code,
            server_message=get_str(response, "message") or None,
        )
    data = response.get("data")
    if not isinstance(data, Mapping):
        raise ApiError(
            "Failed to bootstrap MQTT credentials: response 'data' is not an object",
            code=-1,
        )
    return data


def _build_auth_info(
    *,
    now_ms: int | None = None,
    client_id: str | None = None,
    device_sn: str | None = None,
) -> dict[str, str]:
    """Compute the inner ``authInfo`` dict (with the per-call HMAC-SHA1 sign).

    Test seam: ``now_ms`` / ``client_id`` / ``device_sn`` are injectable so
    fixtures can pin the signature against a known value.
    """
    timestamp = str(now_ms if now_ms is not None else int(time.time() * 1000))
    client_id_value = client_id if client_id is not None else _random_alphanum(8)
    device_sn_value = device_sn if device_sn is not None else _random_alphanum(32)
    sign_string = (
        f"appKey{APP_KEY}clientId{client_id_value}deviceSn{device_sn_value}timestamp{timestamp}"
    )
    sign = (
        hmac.new(
            APP_SECRET.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha1,
        )
        .hexdigest()
        .lower()
    )
    return {
        "clientId": client_id_value,
        "deviceSn": device_sn_value,
        "timestamp": timestamp,
        "sign": sign,
    }


def _random_alphanum(n: int) -> str:
    """Mirror ``C0018a.m70a`` — lowercase ASCII letters + digits, random."""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))
