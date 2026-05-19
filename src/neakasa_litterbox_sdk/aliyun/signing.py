"""Aliyun Cloud API Gateway request signing (HMAC-SHA1).

Every request to ``api-iot.aliyuncs.com`` carries the following
headers::

    POST https://us-east-1.api-iot.aliyuncs.com/<path>?x-ca-request-id=<uuid>
    x-ca-key:                32715650
    x-ca-signature-method:   HmacSHA1
    x-ca-timestamp:          <epoch-ms>
    x-ca-nonce:              <uuid>
    x-ca-signature:          <base64(HMAC-SHA1(appSecret, stringToSign))>
    x-ca-signature-headers:  x-ca-nonce,x-ca-timestamp,x-ca-key,x-ca-signature-method
    content-md5:             <base64(md5(body))>
    content-type:            application/octet-stream; charset=utf-8
    accept:                  application/json; charset=utf-8
    ca_version:              1
    date:                    <RFC1123>

The string-to-sign follows the Aliyun API Gateway spec — the four
``x-ca-*`` headers are appended in **alphabetical** order, regardless of
how they appear in ``x-ca-signature-headers``. (The cn-shanghai gateway
echoes the expected canonical string in the ``X-Ca-Error-Message`` header
on signature mismatch; we use that order here.) ::

    <METHOD>\\n
    <accept>\\n
    <content-md5>\\n
    <content-type>\\n
    <date>\\n
    x-ca-key:<key>\\n
    x-ca-nonce:<nonce>\\n
    x-ca-signature-method:HmacSHA1\\n
    x-ca-timestamp:<ts>\\n
    <path-with-query>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from email.utils import formatdate

from .._credentials import APP_KEY, APP_SECRET, USER_AGENT

GATEWAY_HOST_US: str = "us-east-1.api-iot.aliyuncs.com"

_ACCEPT = "application/json; charset=utf-8"
_CONTENT_TYPE = "application/octet-stream; charset=utf-8"
_SIGNATURE_METHOD = "HmacSHA1"
_SIGNATURE_HEADERS = "x-ca-nonce,x-ca-timestamp,x-ca-key,x-ca-signature-method"


def build_aliyun_headers(
    method: str,
    path_with_query: str,
    body: bytes,
    *,
    now_ms: int | None = None,
    nonce: str | None = None,
    date: str | None = None,
) -> dict[str, str]:
    """Compute every header required by an Aliyun IoT API Gateway POST.

    ``now_ms``, ``nonce`` and ``date`` are injectable so unit tests can pin
    the signature against known fixtures.
    """
    timestamp_ms = str(now_ms if now_ms is not None else int(time.time() * 1000))
    nonce_value = nonce if nonce is not None else str(uuid.uuid4())
    date_value = date if date is not None else formatdate(usegmt=True)
    content_md5 = base64.b64encode(hashlib.md5(body).digest()).decode("ascii")

    string_to_sign = "\n".join(
        [
            method,
            _ACCEPT,
            content_md5,
            _CONTENT_TYPE,
            date_value,
            f"x-ca-key:{APP_KEY}",
            f"x-ca-nonce:{nonce_value}",
            f"x-ca-signature-method:{_SIGNATURE_METHOD}",
            f"x-ca-timestamp:{timestamp_ms}",
            path_with_query,
        ]
    )
    signature = base64.b64encode(
        hmac.new(APP_SECRET.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")

    return {
        "date": date_value,
        "x-ca-signature": signature,
        "x-ca-nonce": nonce_value,
        "x-ca-key": APP_KEY,
        "ca_version": "1",
        "accept": _ACCEPT,
        "content-md5": content_md5,
        "x-ca-timestamp": timestamp_ms,
        "x-ca-signature-headers": _SIGNATURE_HEADERS,
        "content-type": _CONTENT_TYPE,
        "x-ca-signature-method": _SIGNATURE_METHOD,
        "user-agent": USER_AGENT,
    }
