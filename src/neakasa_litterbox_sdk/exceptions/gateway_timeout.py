"""Cloud gateway timeout error."""

from __future__ import annotations

from .api import ApiError

GATEWAY_TIMEOUT_CODES: frozenset[int] = frozenset({20056})
"""Aliyun IoT gateway codes that mean a backend service did not answer in time.

- ``20056`` — ``gateway.hsf.invoke.timeout`` (backend service timeout)
"""


class GatewayTimeoutError(ApiError):
    """The cloud gateway gave up waiting for its backend; retrying later usually works."""
