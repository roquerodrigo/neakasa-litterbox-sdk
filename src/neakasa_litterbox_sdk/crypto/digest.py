"""Hashing and HMAC helpers used by the Neakasa auth flow.

The pre-login signature scheme is::

    sign = base64( HMAC-SHA256(app_secret, app_key + timestamp) ).upper()

and passwords are double-MD5 hashed before being sent::

    password = md5(md5(plaintext))
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def hmac_sha256_sign(app_key: str, app_secret: str, timestamp: str) -> str:
    """Compute the pre-login ``sign`` header for Neakasa REST requests."""
    mac = hmac.new(
        app_secret.encode("utf-8"), (app_key + timestamp).encode("utf-8"), hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode("ascii").upper()


def md5_hex(value: str | bytes) -> str:
    """Hex MD5 of ``value`` (lowercase)."""
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def md5_double_hex(plaintext: str) -> str:
    """``md5(md5(plaintext))`` as a lowercase hex string — Neakasa password format."""
    return md5_hex(md5_hex(plaintext))
