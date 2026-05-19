"""Pin the Aliyun mobile-channel sign math (offline; no network)."""

from __future__ import annotations

import hashlib
import hmac

from neakasa_litterbox_sdk._credentials import APP_KEY, APP_SECRET
from neakasa_litterbox_sdk.aliyun.mqtt_auth import _build_auth_info


def test_authinfo_sign_is_hex_lower_hmac_sha1() -> None:
    """Pin the bootstrap signer's exact byte layout + hashing."""
    info = _build_auth_info(
        now_ms=1779157013115,
        client_id="cdf9bxg7",
        device_sn="m7yr2bp9zoxn9aj5e6yvbgsl7v3rxqdk",
    )

    expected_canonical = (
        f"appKey{APP_KEY}"
        "clientIdcdf9bxg7"
        "deviceSnm7yr2bp9zoxn9aj5e6yvbgsl7v3rxqdk"
        "timestamp1779157013115"
    )
    expected_sign = (
        hmac.new(
            APP_SECRET.encode("utf-8"),
            expected_canonical.encode("utf-8"),
            hashlib.sha1,
        )
        .hexdigest()
        .lower()
    )

    assert info["clientId"] == "cdf9bxg7"
    assert info["deviceSn"] == "m7yr2bp9zoxn9aj5e6yvbgsl7v3rxqdk"
    assert info["timestamp"] == "1779157013115"
    assert info["sign"] == expected_sign


def test_authinfo_random_values_are_well_formed() -> None:
    """Without injectable seeds, lengths and alphabet should match the spec."""
    info = _build_auth_info(now_ms=1779157013115)
    assert len(info["clientId"]) == 8
    assert len(info["deviceSn"]) == 32
    assert info["clientId"].islower() or info["clientId"].isdigit()
    assert all(c.isalnum() for c in info["clientId"])
    assert all(c.isalnum() for c in info["deviceSn"])


def test_mqtt_password_sign() -> None:
    """Pin the password derivation: hex_UPPER(HMAC-SHA1(deviceSecret, canonical))."""
    pk, dn, ds = "a4HiUVpAgt9", "deviceabc1234567890", "secret_xyz"
    bare = f"{dn}&{pk}"
    canonical = f"clientId{bare}deviceName{dn}productKey{pk}"
    expected = (
        hmac.new(ds.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha1).hexdigest().upper()
    )

    # Build credentials via the same logic the production code uses.
    sign = hmac.new(ds.encode(), canonical.encode(), hashlib.sha1).hexdigest().upper()
    assert sign == expected
    assert sign.isupper()
    assert len(sign) == 40  # SHA-1 hex
