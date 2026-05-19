"""Generate the per-request session token used by post-login Neakasa REST calls.

Plaintext layout, encrypted via AES-CBC with the session ``aesKey`` /
``aesIv``::

    "<userToken>@<millisecond_epoch>"

The base64 result rides in the ``token`` header (Scheme A) or in the
``?token=`` URL parameter (Scheme B). Each request gets a fresh stamp.
"""

from __future__ import annotations

import time

from ..crypto import aes_encrypt


def generate_session_token(
    user_token: str,
    aes_key: str,
    aes_iv: str,
    *,
    now: float | None = None,
) -> str:
    """Return ``AES-CBC(userToken@timestamp_ms, aes_key, aes_iv)`` base64.

    ``now`` is injectable so unit tests can pin the timestamp against a
    known reference value.
    """
    timestamp_ms = str(int((now if now is not None else time.time()) * 1000))
    plaintext = f"{user_token}@{timestamp_ms}"
    return aes_encrypt(plaintext, aes_key.encode("utf-8"), aes_iv.encode("utf-8"))
