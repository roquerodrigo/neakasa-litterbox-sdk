"""Public exception hierarchy.

Hierarchy::

    NeakasaError
    ├── ApiError                       (non-zero ``code`` in the JHResult envelope)
    │   └── AuthenticationError        (auth/login failure — anything code-mapped here)
    │       ├── SessionExpiredError    (codes 1007 / 3026 / 3027)
    │       └── InvalidCredentialsError (codes 10060 / 10061 / 10192)
    └── TransportError                 (HTTP / network failure)

Catch the most specific class you can handle; ``AuthenticationError`` is the
right catch-all for "auth went wrong, anything else propagates".
"""

from __future__ import annotations

from .api import ApiError
from .auth import AuthenticationError
from .base import NeakasaError
from .credentials import INVALID_CREDENTIALS_CODES, InvalidCredentialsError
from .session import SESSION_EXPIRED_CODES, SessionExpiredError
from .transport import TransportError

__all__ = [
    "INVALID_CREDENTIALS_CODES",
    "SESSION_EXPIRED_CODES",
    "ApiError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "NeakasaError",
    "SessionExpiredError",
    "TransportError",
]
