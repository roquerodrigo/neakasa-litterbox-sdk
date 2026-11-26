"""Descriptions of the network failures the transports wrap."""

from __future__ import annotations

import aiohttp
import pytest

from neakasa_litterbox_sdk.utils._errors import describe_cause


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (aiohttp.ClientError("network down"), "network down"),
        (TimeoutError(), "request timed out"),
        (
            TimeoutError("Timeout on reading data from socket"),
            "Timeout on reading data from socket",
        ),
        (aiohttp.ServerDisconnectedError(""), "ServerDisconnectedError"),
        (aiohttp.ClientPayloadError(), "ClientPayloadError"),
    ],
)
def test_describe_cause(error: BaseException, expected: str) -> None:
    assert describe_cause(error) == expected
