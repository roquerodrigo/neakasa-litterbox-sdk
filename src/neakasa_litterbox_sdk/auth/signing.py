"""HTTP header builder for Neakasa pre-login signed requests.

Mirrors ``HttpRequest.sentGoLangGlobalGet`` and ``sentGoLangNormalGetInJava``
from the Neakasa Android app: every pre-auth request carries ``appId``,
``sign`` and ``timestamp`` headers, plus device metadata. The signature
scheme is HMAC-SHA256 over ``app_key + timestamp``, base64-encoded and
upper-cased.
"""

from __future__ import annotations

import time

from .._credentials import APP_KEY, APP_SECRET, USER_AGENT
from ..crypto import hmac_sha256_sign


def build_signed_headers(language: str = "en") -> dict[str, str]:
    """Return the headers for an unauthenticated Neakasa REST request.

    ``request-id`` deliberately reuses the signature value, matching what
    the Android client sends.
    """
    timestamp = str(int(time.time()))
    sign = hmac_sha256_sign(APP_KEY, APP_SECRET, timestamp)
    return {
        "appId": APP_KEY,
        "sign": sign,
        "timestamp": timestamp,
        "request-id": sign,
        **_common_headers(language),
    }


def build_authenticated_headers(
    encrypted_user_id: str,
    session_token: str,
    language: str = "en",
) -> dict[str, str]:
    """Return the headers for an authenticated post-login Neakasa REST request.

    Mirrors ``HttpRequest.sentGetV2`` / ``sentPostV2`` when ``needToken=true``:
    the pre-login ``appId`` / ``sign`` pair is replaced by ``uid`` (the
    boot-key-encrypted user id) and ``token`` (the per-request session
    token). The HMAC value still rides as ``request-id`` for trace
    correlation.
    """
    timestamp = str(int(time.time()))
    sign = hmac_sha256_sign(APP_KEY, APP_SECRET, timestamp)
    return {
        "uid": encrypted_user_id,
        "token": session_token,
        "timestamp": timestamp,
        "request-id": sign,
        **_common_headers(language),
    }


def _common_headers(language: str) -> dict[str, str]:
    return {
        "version": "226",
        "versionString": "2.2.6",
        "Brand": "Generic",
        "brand": "Generic",
        "Model": "neakasa-litterbox-sdk",
        "model": "neakasa-litterbox-sdk",
        "Accept-Language": language,
        "Content-Type": "application/x-www-form-urlencoded",
        "Charset": "UTF-8",
        "Accept": "*/*",
        "User-Agent": USER_AGENT,
    }
