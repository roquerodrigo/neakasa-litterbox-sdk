"""Aliyun IoT API Gateway client (signing + transport + JSON-RPC envelope).

The mobile app routes runtime device traffic (``/thing/properties/get``,
``/thing/service/invoke``, ``/uc/listBindingByAccount``, …) through the
Aliyun IoT API Gateway at ``<region>.api-iot.aliyuncs.com``. This package
implements just enough of that gateway protocol to call those endpoints
from Python.
"""

from __future__ import annotations

from .envelope import build_envelope
from .handshake import exchange_for_iot_token
from .oa_signing import build_oa_headers
from .signing import GATEWAY_HOST_US, build_aliyun_headers
from .transport import AliyunTransport

__all__ = [
    "GATEWAY_HOST_US",
    "AliyunTransport",
    "build_aliyun_headers",
    "build_envelope",
    "build_oa_headers",
    "exchange_for_iot_token",
]
