"""Verify ``_unwrap_envelope`` picks the right exception class for each code."""

from __future__ import annotations

import pytest

from neakasa_litterbox_sdk import (
    ApiError,
    AuthenticationError,
    InvalidCredentialsError,
    SessionExpiredError,
)
from neakasa_litterbox_sdk.client import _unwrap_envelope


def _envelope(code: int) -> dict[str, object]:
    return {
        "request_id": "test",
        "code": code,
        "message": "test error",
        "data": None,
    }


def test_zero_code_returns_data() -> None:
    envelope = {"code": 0, "data": {"hello": "world"}}
    assert _unwrap_envelope(envelope, context="probe") == {"hello": "world"}


@pytest.mark.parametrize("code", [1007, 3026, 3027])
def test_session_expired_codes_dispatch_to_session_expired_error(code: int) -> None:
    with pytest.raises(SessionExpiredError) as exc_info:
        _unwrap_envelope(_envelope(code), context="probe", auth=True)
    assert exc_info.value.code == code
    assert isinstance(exc_info.value, AuthenticationError)


@pytest.mark.parametrize("code", [10060, 10061, 10192])
def test_invalid_credentials_codes_dispatch_to_invalid_credentials_error(code: int) -> None:
    with pytest.raises(InvalidCredentialsError) as exc_info:
        _unwrap_envelope(_envelope(code), context="probe", auth=True)
    assert exc_info.value.code == code
    assert isinstance(exc_info.value, AuthenticationError)


def test_unknown_auth_code_falls_back_to_authentication_error() -> None:
    with pytest.raises(AuthenticationError) as exc_info:
        _unwrap_envelope(_envelope(10050), context="probe", auth=True)
    assert exc_info.value.code == 10050
    assert not isinstance(exc_info.value, SessionExpiredError)
    assert not isinstance(exc_info.value, InvalidCredentialsError)


def test_non_auth_context_uses_plain_api_error() -> None:
    with pytest.raises(ApiError) as exc_info:
        _unwrap_envelope(_envelope(1007), context="probe", auth=False)
    assert exc_info.value.code == 1007
    assert not isinstance(exc_info.value, AuthenticationError)
