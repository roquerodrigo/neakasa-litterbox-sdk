"""Transport-layer failures (HTTP, network)."""

from __future__ import annotations

from .base import NeakasaError


class TransportError(NeakasaError):
    """HTTP or network failure while talking to a Neakasa server."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
