"""Command methods, property setters, and device resolution on ``NeakasaClient``."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from neakasa_litterbox_sdk import (
    Device,
    DeviceRole,
    LoginResult,
    NeakasaClient,
    NeakasaError,
    UserInfo,
)

if TYPE_CHECKING:
    from neakasa_litterbox_sdk.utils._json import JsonValue


def _device(device_name: str = "PB01", iot_id: str = "iot-1") -> Device:
    return Device(
        iot_id=iot_id,
        product_key="pk",
        product_name="Neakasa M1",
        device_name=device_name,
        category_key="ck",
        category_name="Litter Box",
        net_type="WIFI",
        role=DeviceRole.OWNER,
        status=1,
        bind_time=0,
    )


def _login_result() -> LoginResult:
    return LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="0123456789abcdef",
        aes_iv="abcdef0123456789",
        user_info=UserInfo(
            user_id=42,
            user_name="user@example.com",
            ali_user_id=400068852,
            ali_authentication_token="ali-auth-token",
        ),
        issued_at=1_700_000_000.0,
        iot_token="iot-token",
    )


def _client(monkeypatch: pytest.MonkeyPatch) -> tuple[NeakasaClient, AsyncMock]:
    """Client with a primed session, device index, and a captured aliyun call."""
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    client._device_index = {"PB01": _device()}
    call_mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(client, "_aliyun_call_authed", call_mock)
    return client, call_mock


async def test_start_clean_invokes_clean_now_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    await client.start_clean("PB01")
    call_mock.assert_awaited_once()
    kwargs = call_mock.await_args.kwargs
    assert call_mock.await_args.args[0] == "/thing/service/invoke"
    assert kwargs["payload"] == {
        "iotId": "iot-1",
        "identifier": "cleanNow",
        "args": {"bStartClean": 1},
    }


async def test_stop_clean_sends_zero_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    await client.stop_clean("PB01")
    assert call_mock.await_args.kwargs["payload"]["args"] == {"bStartClean": 0}


async def test_start_level_invokes_sand_leveling(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    await client.start_level("PB01")
    payload = call_mock.await_args.kwargs["payload"]
    assert payload["identifier"] == "sandLeveling"
    assert payload["args"] == {"bStartLeveling": 1}


async def test_stop_level_sends_zero_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    await client.stop_level("PB01")
    assert call_mock.await_args.kwargs["payload"]["args"] == {"bStartLeveling": 0}


@pytest.mark.parametrize("enabled,expected", [(True, 1), (False, 0)])
async def test_set_auto_level(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, expected: int
) -> None:
    client, call_mock = _client(monkeypatch)
    await client.set_auto_level("PB01", enabled)
    payload = call_mock.await_args.kwargs["payload"]
    assert call_mock.await_args.args[0] == "/thing/properties/set"
    assert payload["items"] == {"autoLevel": expected}


@pytest.mark.parametrize("enabled,expected", [(True, 1), (False, 0)])
async def test_set_silent_mode(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, expected: int
) -> None:
    client, call_mock = _client(monkeypatch)
    await client.set_silent_mode("PB01", enabled)
    assert call_mock.await_args.kwargs["payload"]["items"] == {"silentMode": expected}


@pytest.mark.parametrize("enabled,expected", [(True, 1), (False, 0)])
async def test_set_child_lock(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, expected: int
) -> None:
    client, call_mock = _client(monkeypatch)
    await client.set_child_lock("PB01", enabled)
    assert call_mock.await_args.kwargs["payload"]["items"] == {"childLockOnOff": expected}


async def test_set_auto_clean_preserves_existing_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Toggling auto-clean reads back cleanType/cleanParam and flips only ``active``."""
    client, call_mock = _client(monkeypatch)
    props_mock = AsyncMock(
        return_value={"cleanCfg": {"value": {"cleanType": 2, "cleanParam": 7, "active": 0}}}
    )
    monkeypatch.setattr(client, "_get_properties", props_mock)

    await client.set_auto_clean("PB01", True)

    payload = call_mock.await_args.kwargs["payload"]
    assert payload["items"] == {"cleanCfg": {"cleanType": 2, "cleanParam": 7, "active": 1}}


async def test_set_auto_clean_disable_sets_active_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    monkeypatch.setattr(
        client,
        "_get_properties",
        AsyncMock(return_value={"cleanCfg": {"value": {"cleanType": 1, "cleanParam": 3}}}),
    )
    await client.set_auto_clean("PB01", False)
    assert call_mock.await_args.kwargs["payload"]["items"]["cleanCfg"]["active"] == 0


async def test_calibrate_sand_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    client, call_mock = _client(monkeypatch)
    await client.calibrate_sand("PB01", 50)
    payload = call_mock.await_args.kwargs["payload"]
    assert payload["identifier"] == "sandAdj"
    assert payload["args"] == {"percent": 50}


@pytest.mark.parametrize("percent", [0, 101, -1, 200])
async def test_calibrate_sand_out_of_range_raises_client_side(
    monkeypatch: pytest.MonkeyPatch, percent: int
) -> None:
    client, call_mock = _client(monkeypatch)
    with pytest.raises(NeakasaError, match=r"percent must be in 1\.\.100"):
        await client.calibrate_sand("PB01", percent)
    call_mock.assert_not_awaited()


async def test_resolve_device_refreshes_index_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """A device not in the cache triggers a single ``list_devices`` refresh."""
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()

    async def _list() -> list[Device]:
        client._device_index = {"PB99": _device("PB99", "iot-99")}
        return list(client._device_index.values())

    list_mock = AsyncMock(side_effect=_list)
    monkeypatch.setattr(client, "list_devices", list_mock)

    device = await client._resolve_device("PB99")
    assert device.iot_id == "iot-99"
    list_mock.assert_awaited_once()


async def test_resolve_device_unknown_raises_after_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A still-missing device after a refresh surfaces a clear error."""
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    monkeypatch.setattr(client, "list_devices", AsyncMock(return_value=[]))

    with pytest.raises(NeakasaError, match="is not registered on this account"):
        await client._resolve_device("PBXX")


async def test_resolve_role_returns_device_role(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client(monkeypatch)
    assert await client._resolve_role("PB01") is DeviceRole.OWNER


async def test_get_status_unwraps_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_status`` resolves the device, fetches and parses properties."""
    client, call_mock = _client(monkeypatch)
    props: dict[str, JsonValue] = {"Sand": {"value": {"percent": 80}}}
    call_mock.return_value = props

    status = await client.get_status("PB01")

    # First positional arg is the endpoint path.
    assert call_mock.await_args.args[0] == "/thing/properties/get"
    assert call_mock.await_args.kwargs["payload"] == {"iotId": "iot-1"}
    assert status.sand_percent == 80


async def test_list_devices_builds_index(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    monkeypatch.setattr(
        client,
        "_aliyun_call_authed",
        AsyncMock(
            return_value={
                "data": [
                    {"iotId": "iot-1", "deviceName": "PB01", "owned": 1},
                    {"iotId": "iot-2", "deviceName": "PB02", "owned": 0},
                ]
            }
        ),
    )

    devices = await client.list_devices()

    assert [d.device_name for d in devices] == ["PB01", "PB02"]
    assert client._device_index["PB02"].role is DeviceRole.SHARED
