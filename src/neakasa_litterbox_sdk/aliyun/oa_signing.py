"""Aliyun OpenAccount gateway signing (HmacSHA256 over form-encoded body).

The OpenAccount endpoints (``/api/prd/connect.json``,
``loginbyoauth.json``) do not use the IoT envelope. They take a
form-encoded body and sign with a slightly different canonical string
than :func:`aliyun.signing.build_aliyun_headers`::

    POST\\n
    <accept>\\n
    \\n
    <content-type>\\n
    <date>\\n
    x-ca-key:<key>\\n
    x-ca-nonce:<nonce>\\n
    x-ca-signature-method:HmacSHA256\\n
    x-ca-timestamp:<epoch-sec>\\n
    <path>?<body unescaped>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from email.utils import formatdate

from .._credentials import APP_KEY, APP_SECRET, USER_AGENT

_ACCEPT = "application/json"
_CONTENT_TYPE = "application/x-www-form-urlencoded"
_SIGNATURE_METHOD = "HmacSHA256"
_SIGNATURE_HEADERS = "x-ca-nonce,x-ca-timestamp,x-ca-key,x-ca-signature-method"


def build_oa_headers(
    method: str,
    path: str,
    signing_body: str,
    *,
    now_sec: int | None = None,
    nonce: str | None = None,
    date: str | None = None,
) -> dict[str, str]:
    """Compute headers for an Aliyun OpenAccount POST.

    ``signing_body`` is the body in its canonical, *un-URL-encoded* form
    (``k=<raw json>&k2=<raw json>``). The wire body is the URL-encoded
    counterpart and is sent by the transport — only the signer cares about
    the canonical form.

    ``now_sec`` / ``nonce`` / ``date`` are injectable for fixture pinning.
    """
    timestamp_sec = str(now_sec if now_sec is not None else int(time.time()))
    nonce_value = nonce if nonce is not None else str(uuid.uuid4())
    date_value = date if date is not None else formatdate(usegmt=True)

    string_to_sign = "\n".join(
        [
            method,
            _ACCEPT,
            "",  # content-md5 not used on OA
            _CONTENT_TYPE,
            date_value,
            f"x-ca-key:{APP_KEY}",
            f"x-ca-nonce:{nonce_value}",
            f"x-ca-signature-method:{_SIGNATURE_METHOD}",
            f"x-ca-timestamp:{timestamp_sec}",
            f"{path}?{signing_body}",
        ]
    )
    signature = base64.b64encode(
        hmac.new(
            APP_SECRET.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
    ).decode("ascii")

    return {
        "accept": _ACCEPT,
        "content-type": _CONTENT_TYPE,
        "date": date_value,
        "x-ca-key": APP_KEY,
        "x-ca-nonce": nonce_value,
        "x-ca-signature": signature,
        "x-ca-signature-headers": _SIGNATURE_HEADERS,
        "x-ca-signature-method": _SIGNATURE_METHOD,
        "x-ca-timestamp": timestamp_sec,
        "user-agent": USER_AGENT,
    }
