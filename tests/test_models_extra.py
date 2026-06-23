"""Round-trips and edge cases for the model dataclasses and JSON helpers."""

from __future__ import annotations

import pytest

from neakasa_litterbox_sdk import Device, DeviceStatus, LoginResult, RecordType, UserInfo
from neakasa_litterbox_sdk.crypto import aes_encrypt_with_boot_key
from neakasa_litterbox_sdk.models.login_result import _parse_login_token
from neakasa_litterbox_sdk.utils._json import (
    get_float,
    get_int,
    get_object,
    get_str,
    loads,
)


def test_user_info_round_trips_through_dict() -> None:
    original = UserInfo(
        user_id=42,
        user_name="user@example.com",
        ali_user_id=400068852,
        ali_authentication_token="ali-auth-token",
    )
    restored = UserInfo.from_dict(original.to_dict())
    assert restored == original


def test_login_result_round_trips_through_dict() -> None:
    original = LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="key",
        aes_iv="iv",
        user_info=UserInfo(1, "u", 2, "tok"),
        issued_at=1_700_000_000.0,
        iot_token="iot",
    )
    restored = LoginResult.from_dict(original.to_dict())
    assert restored == original


def test_login_result_round_trips_non_default_iot_host() -> None:
    """A regional ``iot_host`` survives the dict round-trip unchanged."""
    original = LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="key",
        aes_iv="iv",
        user_info=UserInfo(1, "u", 2, "tok"),
        issued_at=1_700_000_000.0,
        iot_token="iot",
        iot_host="eu-central-1.api-iot.aliyuncs.com",
    )
    restored = LoginResult.from_dict(original.to_dict())
    assert restored == original
    assert restored.iot_host == "eu-central-1.api-iot.aliyuncs.com"


def test_login_result_from_dict_defaults_iot_host_for_legacy_cache() -> None:
    """Caches serialized before ``iot_host`` existed fall back to the US host."""
    legacy = {
        "user_id": "1",
        "user_token": "t",
        "aes_key": "k",
        "aes_iv": "iv",
        "user_info": UserInfo(1, "u", 2, "tok").to_dict(),
        "issued_at": 1_000.0,
        "iot_token": "iot",
    }
    restored = LoginResult.from_dict(legacy)
    assert restored.iot_host == "us-east-1.api-iot.aliyuncs.com"


def test_login_result_age_seconds() -> None:
    result = LoginResult(
        user_id="1",
        user_token="t",
        aes_key="k",
        aes_iv="iv",
        user_info=UserInfo(1, "u", 2, "tok"),
        issued_at=1_000.0,
    )
    assert result.age_seconds(now=1_250.0) == 250.0


def test_parse_login_token_empty_returns_blanks() -> None:
    assert _parse_login_token("") == ("", "", "", "")


def test_parse_login_token_decrypts_and_splits() -> None:
    """A boot-key-encrypted ``a@b@c@d`` decrypts back to its four parts."""
    cipher = aes_encrypt_with_boot_key("tok@uid@key@iv")
    assert _parse_login_token(cipher) == ("tok", "uid", "key", "iv")


def test_parse_login_token_pads_short_token() -> None:
    cipher = aes_encrypt_with_boot_key("tok@uid")
    assert _parse_login_token(cipher) == ("tok", "uid", "", "")


def test_login_result_from_json_prefers_ali_user_id() -> None:
    """When ``aliUserId`` is set, it overrides the token-embedded user id."""
    cipher = aes_encrypt_with_boot_key("tok@embedded@key@iv")
    result = LoginResult.from_json(
        {
            "loginToken": cipher,
            "userInfo": {"aliUserId": 999, "userName": "u"},
        }
    )
    assert result.user_id == "999"
    assert result.user_token == "tok"


def test_login_result_from_json_falls_back_to_embedded_user_id() -> None:
    cipher = aes_encrypt_with_boot_key("tok@embedded@key@iv")
    result = LoginResult.from_json({"loginToken": cipher, "userInfo": {}})
    assert result.user_id == "embedded"


def test_device_list_from_response_ignores_non_array() -> None:
    assert Device.list_from_response({"data": "not-a-list"}) == []
    assert Device.list_from_response({}) == []


def test_device_list_from_response_skips_non_mapping_entries() -> None:
    devices = Device.list_from_response({"data": [{"deviceName": "PB01"}, "junk", 5]})
    assert [d.device_name for d in devices] == ["PB01"]


def test_record_type_unknown_falls_back_to_other() -> None:
    assert RecordType.from_int(99) is RecordType.OTHER
    assert RecordType.from_int(1) is RecordType.CAT_VISIT


def test_device_status_property_int_coerces_numeric_string() -> None:
    """A property whose ``value`` is a numeric string is coerced to int."""
    status = DeviceStatus.from_response({"room_of_bin": {"value": "1"}})
    assert status.bucket_full is True


def test_device_status_property_int_non_numeric_string_falls_back_to_zero() -> None:
    """A non-numeric string ``value`` falls back to ``0`` rather than raising."""
    status = DeviceStatus.from_response({"room_of_bin": {"value": "nope"}})
    assert status.bucket_full is False


def test_loads_rejects_non_object_top_level() -> None:
    with pytest.raises(ValueError, match="top level is not an object"):
        loads(b"[1, 2, 3]")


def test_get_str_default_on_wrong_type() -> None:
    assert get_str({"k": 5}, "k") == ""
    assert get_str({"k": "v"}, "k") == "v"
    assert get_str({}, "k", default="d") == "d"


def test_get_int_coerces_and_falls_back() -> None:
    assert get_int({"k": True}, "k") == 1
    assert get_int({"k": 7}, "k") == 7
    assert get_int({"k": "9"}, "k") == 9
    assert get_int({"k": "nope"}, "k", default=-1) == -1
    assert get_int({"k": 1.5}, "k", default=3) == 3


def test_get_float_coerces_and_falls_back() -> None:
    assert get_float({"k": True}, "k") == 1.0
    assert get_float({"k": 2}, "k") == 2.0
    assert get_float({"k": "3.5"}, "k") == 3.5
    assert get_float({"k": "bad"}, "k", default=9.0) == 9.0
    assert get_float({"k": None}, "k", default=4.0) == 4.0


def test_get_object_returns_empty_on_non_mapping() -> None:
    assert get_object({"k": [1]}, "k") == {}
    assert get_object({"k": {"x": 1}}, "k") == {"x": 1}
