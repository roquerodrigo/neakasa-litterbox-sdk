"""Per-user metadata returned by Neakasa login."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils._json import get_int, get_str

if TYPE_CHECKING:
    from ..utils._json import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class UserInfo:
    """Snapshot of the user's profile returned alongside the login response."""

    user_id: int
    user_name: str
    ali_user_id: int
    ali_authentication_token: str

    @classmethod
    def from_json(cls, raw: JsonObject) -> UserInfo:
        """Build a ``UserInfo`` from the Neakasa ``userInfo`` JSON object."""
        return cls(
            user_id=get_int(raw, "userId"),
            user_name=get_str(raw, "userName"),
            ali_user_id=get_int(raw, "aliUserId"),
            ali_authentication_token=get_str(raw, "aliAuthenticationToken"),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-safe snapshot for persistence."""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "ali_user_id": self.ali_user_id,
            "ali_authentication_token": self.ali_authentication_token,
        }

    @classmethod
    def from_dict(cls, data: JsonObject) -> UserInfo:
        """Restore a ``UserInfo`` from a previously serialized dict."""
        return cls(
            user_id=get_int(data, "user_id"),
            user_name=get_str(data, "user_name"),
            ali_user_id=get_int(data, "ali_user_id"),
            ali_authentication_token=get_str(data, "ali_authentication_token"),
        )
