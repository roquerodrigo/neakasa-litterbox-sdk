"""Invalid-credentials authentication error."""

from __future__ import annotations

from .auth import AuthenticationError

INVALID_CREDENTIALS_CODES: frozenset[int] = frozenset({10060, 10061, 10192})
"""Server codes that mean the user or password is wrong.

- ``10060`` — user does not exist
- ``10061`` — wrong account or password
- ``10192`` — password incorrect (alternate path)
"""


class InvalidCredentialsError(AuthenticationError):
    """The email or password the SDK presented was rejected by the server."""
