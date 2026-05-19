"""AES-CBC helpers used by the Neakasa REST auth flow.

Two cipher modes coexist:

- **Boot key/IV** (``3J74PRUE5TKPJP32`` / ``QB8GC2X6WK39FF93``) — fixed
  SDK-wide constants. Used by :func:`decrypt_login_token` to unwrap the
  ``loginToken`` from the login response, and by
  :func:`aes_encrypt_with_boot_key` to encrypt fields like ``userId``
  that get passed on subsequent requests.
- **Session key/IV** — different per login; comes out of the
  ``loginToken``'s plaintext (``aesKey`` / ``aesIv`` fields).
  :func:`aes_encrypt` takes them as parameters and is used by the
  session-token generator.

The cipher is ``AES/CBC/NoPadding`` throughout — the plaintext is
padded manually with NUL bytes (``\\x00``) up to the next 16-byte
boundary before encryption, then stripped after decryption.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_BOOT_KEY = b"3J74PRUE5TKPJP32"
_BOOT_IV = b"QB8GC2X6WK39FF93"
_BLOCK_SIZE = 16


def decrypt_login_token(token: str) -> str:
    """Decrypt the base64 ``loginToken`` from the Neakasa login response."""
    ciphertext = base64.b64decode(token.replace(" ", "+"))
    cipher = Cipher(algorithms.AES(_BOOT_KEY), modes.CBC(_BOOT_IV))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext.rstrip(b"\x00").decode("utf-8")


def aes_encrypt(plaintext: str, key: bytes, iv: bytes) -> str:
    """AES-CBC NoPadding encrypt ``plaintext`` with ``key`` / ``iv``, returning base64."""
    data = plaintext.encode("utf-8")
    pad_len = (_BLOCK_SIZE - len(data) % _BLOCK_SIZE) % _BLOCK_SIZE
    padded = data + b"\x00" * pad_len
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")


def aes_encrypt_with_boot_key(plaintext: str) -> str:
    """Convenience wrapper using the hardcoded boot key/IV.

    Used to encrypt the ``userId`` field that goes inside the
    ``?data=<JSON>`` payload of post-login GETs and the ``uid`` header
    of Scheme-A authenticated calls.
    """
    return aes_encrypt(plaintext, _BOOT_KEY, _BOOT_IV)
