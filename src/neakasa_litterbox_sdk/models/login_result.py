"""Result of a successful login to the Neakasa REST API."""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..crypto import decrypt_login_token
from ..utils._json import get_float, get_object, get_str
from .user_info import UserInfo

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


_DEFAULT_IOT_HOST = "us-east-1.api-iot.aliyuncs.com"


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Everything the SDK needs to keep talking to Neakasa after login.

    The server does not advertise an expiry — the official app treats
    the session as valid until an auth-failure code (1007 / 3026 / 3027)
    comes back and only then re-logs in. Consumers caching this result
    across runs should follow the same lazy strategy, or invalidate
    after a self-chosen TTL using ``issued_at`` plus ``time.time()``.

    Treat :meth:`to_dict` / :meth:`from_dict` as an opaque round-trip;
    individual fields are an internal contract subject to change.
    """

    user_id: str
    user_token: str
    aes_key: str
    aes_iv: str
    user_info: UserInfo
    issued_at: float
    iot_token: str = ""
    iot_host: str = _DEFAULT_IOT_HOST

    def with_iot_token(self, iot_token: str) -> LoginResult:
        """Return a copy with ``iot_token`` set (the dataclass is frozen)."""
        return dataclasses.replace(self, iot_token=iot_token)

    def with_iot_session(self, iot_token: str, iot_host: str) -> LoginResult:
        """Return a copy with both ``iot_token`` and ``iot_host`` updated."""
        return dataclasses.replace(self, iot_token=iot_token, iot_host=iot_host)

    @classmethod
    def from_json(cls, raw: JsonObject) -> LoginResult:
        """Build a ``LoginResult`` from the ``data`` object of the login response.

        The ``loginToken`` field is AES-CBC encrypted and decodes to
        ``<userToken>@<userId>@<aesKey>@<aesIv>``. After parsing, the
        Android app overrides ``userId`` with ``userInfo.aliUserId``.
        ``issued_at`` is stamped at parse time so consumers can age-check
        cached sessions.
        """
        user_info = UserInfo.from_json(get_object(raw, "userInfo"))
        token, _embedded_user_id, aes_key, aes_iv = _parse_login_token(get_str(raw, "loginToken"))
        user_id = str(user_info.ali_user_id) if user_info.ali_user_id else _embedded_user_id
        return cls(
            user_id=user_id,
            user_token=token,
            aes_key=aes_key,
            aes_iv=aes_iv,
            user_info=user_info,
            issued_at=time.time(),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-safe snapshot for persisting between runs."""
        return {
            "user_id": self.user_id,
            "user_token": self.user_token,
            "aes_key": self.aes_key,
            "aes_iv": self.aes_iv,
            "user_info": self.user_info.to_dict(),
            "issued_at": self.issued_at,
            "iot_token": self.iot_token,
            "iot_host": self.iot_host,
        }

    @classmethod
    def from_dict(cls, data: JsonObject) -> LoginResult:
        """Restore a ``LoginResult`` from a previously serialized dict."""
        return cls(
            user_id=get_str(data, "user_id"),
            user_token=get_str(data, "user_token"),
            aes_key=get_str(data, "aes_key"),
            aes_iv=get_str(data, "aes_iv"),
            user_info=UserInfo.from_dict(get_object(data, "user_info")),
            issued_at=get_float(data, "issued_at"),
            iot_token=get_str(data, "iot_token"),
            iot_host=get_str(data, "iot_host", default=_DEFAULT_IOT_HOST),
        )

    def age_seconds(self, now: float | None = None) -> float:
        """Seconds elapsed since the result was issued."""
        return (now if now is not None else time.time()) - self.issued_at


def _parse_login_token(token: str) -> tuple[str, str, str, str]:
    """Decrypt ``token`` and split into ``(user_token, user_id, aes_key, aes_iv)``."""
    if not token:
        return "", "", "", ""
    parts = decrypt_login_token(token).split("@")
    padded = parts + [""] * (4 - len(parts))
    return padded[0], padded[1], padded[2], padded[3]
