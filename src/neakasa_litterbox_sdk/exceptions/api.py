"""API-shape failures (non-zero `code` in JHResult envelope)."""

from __future__ import annotations

from .base import NeakasaError


class ApiError(NeakasaError):
    """Server returned a JHResult with a non-zero ``code`` field."""

    def __init__(self, message: str, code: int, server_message: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.server_message = server_message
