"""Pin the Aliyun API Gateway signing math."""

from __future__ import annotations

import base64
import hashlib
import hmac

from neakasa_litterbox_sdk._credentials import APP_KEY, APP_SECRET
from neakasa_litterbox_sdk.aliyun.signing import build_aliyun_headers


def test_headers_match_signature_fixture() -> None:
    """All static headers + signature math match the expected canonical form."""
    body = b'{"a":"req","b":"1.0","c":{"apiVer":"1.0.8","language":"en-US","iotToken":"tok"},"d":{},"id":"req","params":{"$ref":"$.d"},"request":{"$ref":"$.c"},"version":"1.0"}'  # noqa: E501  byte-exact fixture; line-wrapping would change the signed bytes
    headers = build_aliyun_headers(
        "POST",
        "/uc/listBindingByAccount?x-ca-request-id=fixed",
        body,
        now_ms=1779157013115,
        nonce="2b1d5870-52c2-4b91-9b2a-9c2c2f0da0b8",
        date="Tue, 19 May 2026 02:16:53 GMT",
    )

    assert headers["x-ca-key"] == APP_KEY
    assert headers["x-ca-signature-method"] == "HmacSHA1"
    assert headers["x-ca-signature-headers"] == (
        "x-ca-nonce,x-ca-timestamp,x-ca-key,x-ca-signature-method"
    )
    assert headers["accept"] == "application/json; charset=utf-8"
    assert headers["content-type"] == "application/octet-stream; charset=utf-8"
    assert headers["ca_version"] == "1"
    assert headers["x-ca-nonce"] == "2b1d5870-52c2-4b91-9b2a-9c2c2f0da0b8"
    assert headers["x-ca-timestamp"] == "1779157013115"

    expected_md5 = base64.b64encode(hashlib.md5(body, usedforsecurity=False).digest()).decode(
        "ascii"
    )
    assert headers["content-md5"] == expected_md5

    expected_string_to_sign = "\n".join(
        [
            "POST",
            "application/json; charset=utf-8",
            expected_md5,
            "application/octet-stream; charset=utf-8",
            "Tue, 19 May 2026 02:16:53 GMT",
            f"x-ca-key:{APP_KEY}",
            "x-ca-nonce:2b1d5870-52c2-4b91-9b2a-9c2c2f0da0b8",
            "x-ca-signature-method:HmacSHA1",
            "x-ca-timestamp:1779157013115",
            "/uc/listBindingByAccount?x-ca-request-id=fixed",
        ]
    )
    expected_signature = base64.b64encode(
        hmac.new(APP_SECRET.encode(), expected_string_to_sign.encode(), hashlib.sha1).digest()
    ).decode("ascii")
    assert headers["x-ca-signature"] == expected_signature


def test_empty_body_gets_md5_of_empty_string() -> None:
    headers = build_aliyun_headers(
        "POST",
        "/uc/listBindingByAccount?x-ca-request-id=fixed",
        b"",
        now_ms=0,
        nonce="n",
        date="d",
    )
    # Known MD5 of empty input
    assert headers["content-md5"] == "1B2M2Y8AsgTpgAmY7PhCfg=="
