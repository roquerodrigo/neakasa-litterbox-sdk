"""Round-trip + fixture tests for the post-login AES + token helpers."""

from __future__ import annotations

from neakasa_litterbox_sdk.auth.session_token import generate_session_token
from neakasa_litterbox_sdk.crypto import aes_encrypt, aes_encrypt_with_boot_key, decrypt_login_token


def test_boot_key_encrypt_decrypt_roundtrip() -> None:
    """``aes_encrypt_with_boot_key`` and ``decrypt_login_token`` use the same key/IV."""
    plaintext = "400115938"
    cipher = aes_encrypt_with_boot_key(plaintext)
    # decrypt_login_token strips trailing NULs we added during NUL-padding encrypt
    assert decrypt_login_token(cipher) == plaintext


def test_aes_encrypt_pads_with_nul_to_block_size() -> None:
    """Encrypting a 9-char string yields exactly one 16-byte AES block (24 b64 chars)."""
    cipher = aes_encrypt_with_boot_key("400115938")
    # 1 block = 16 bytes ciphertext = 24 base64 chars including padding
    assert len(cipher) == 24
    assert cipher.endswith("==")


def test_aes_encrypt_with_custom_key_roundtrip() -> None:
    """Custom (session) key/IV mode produces a value decryptable by the same pair."""
    key = b"0123456789abcdef"
    iv = b"abcdef0123456789"
    cipher = aes_encrypt("hello world", key, iv)
    # Decrypt using the same mode the Android app uses (boot key path also handles this shape)
    # We use the public decrypt helper by swapping to a small helper below:
    import base64

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = decryptor.update(base64.b64decode(cipher)) + decryptor.finalize()
    assert plain.rstrip(b"\x00").decode("utf-8") == "hello world"


def test_session_token_pins_against_known_inputs() -> None:
    """Same inputs (timestamp + keys + user_token) must produce the same token."""
    token1 = generate_session_token(
        user_token="cafef00d" * 4,
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        now=1700000000.5,  # 1700000000500 ms
    )
    token2 = generate_session_token(
        user_token="cafef00d" * 4,
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        now=1700000000.5,
    )
    assert token1 == token2
    # Different timestamp → different token
    token3 = generate_session_token(
        user_token="cafef00d" * 4,
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        now=1700000001.0,
    )
    assert token3 != token1
