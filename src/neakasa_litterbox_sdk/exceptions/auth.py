"""Authentication-specific failures."""

from __future__ import annotations

from .api import ApiError


class AuthenticationError(ApiError):
    """Login or session refresh failed."""
