"""Session-expired authentication error."""

from __future__ import annotations

from .auth import AuthenticationError

SESSION_EXPIRED_CODES: frozenset[int] = frozenset({1007, 3026, 3027})
"""Server codes that the Android app treats as "refresh and try again"."""


class SessionExpiredError(AuthenticationError):
    """The cached session is no longer accepted; the caller must re-login."""
