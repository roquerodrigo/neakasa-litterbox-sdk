"""Pin the Aliyun OpenAccount signing scheme used by the iotToken handshake."""

from __future__ import annotations

import base64
import hashlib
import hmac

from neakasa_litterbox_sdk._credentials import APP_KEY, APP_SECRET
from neakasa_litterbox_sdk.aliyun.oa_signing import build_oa_headers
from neakasa_litterbox_sdk.aliyun.transport import _encode_oa_body


def test_oa_signing_canonical_string() -> None:
    """Headers match the do_request_raw recipe: HmacSHA256 over form-encoded body."""
    body = {"request": {"context": {"appKey": APP_KEY}}}
    signing_body = _encode_oa_body(body, url_encoded=False)
    assert signing_body == f'request={{"context":{{"appKey":"{APP_KEY}"}}}}'

    headers = build_oa_headers(
        "POST",
        "/api/prd/connect.json",
        signing_body,
        now_sec=1779157013,
        nonce="fixed-nonce",
        date="Tue, 19 May 2026 02:16:53 GMT",
    )

    assert headers["x-ca-key"] == APP_KEY
    assert headers["x-ca-signature-method"] == "HmacSHA256"
    assert headers["accept"] == "application/json"
    assert headers["content-type"] == "application/x-www-form-urlencoded"
    assert headers["x-ca-nonce"] == "fixed-nonce"
    assert headers["x-ca-timestamp"] == "1779157013"

    expected_string_to_sign = "\n".join(
        [
            "POST",
            "application/json",
            "",
            "application/x-www-form-urlencoded",
            "Tue, 19 May 2026 02:16:53 GMT",
            f"x-ca-key:{APP_KEY}",
            "x-ca-nonce:fixed-nonce",
            "x-ca-signature-method:HmacSHA256",
            "x-ca-timestamp:1779157013",
            f"/api/prd/connect.json?{signing_body}",
        ]
    )
    expected_signature = base64.b64encode(
        hmac.new(APP_SECRET.encode(), expected_string_to_sign.encode(), hashlib.sha256).digest()
    ).decode("ascii")
    assert headers["x-ca-signature"] == expected_signature


def test_oa_body_wire_form_url_encodes_json_values() -> None:
    """Wire body URL-encodes the JSON payload; the canonical form does not."""
    body: dict[str, object] = {"request": {"k": "a&b"}}
    wire = _encode_oa_body(body, url_encoded=True)
    canonical = _encode_oa_body(body, url_encoded=False)

    assert canonical == 'request={"k":"a&b"}'
    assert wire == "request=%7B%22k%22%3A%22a%26b%22%7D"
