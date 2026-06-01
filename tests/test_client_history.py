"""History endpoints, the authenticated GET path, and session guards."""

from __future__ import annotations

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


def _device(device_name: str = "PB01", role: DeviceRole = DeviceRole.OWNER) -> Device:
    return Device(
        iot_id="iot-1",
        product_key="pk",
        product_name="Neakasa M1",
        device_name=device_name,
        category_key="ck",
        category_name="Litter Box",
        net_type="WIFI",
        role=role,
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


def _client(monkeypatch: pytest.MonkeyPatch, role: DeviceRole = DeviceRole.OWNER) -> NeakasaClient:
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    client._device_index = {"PB01": _device(role=role)}
    return client


async def test_get_toilet_records_signs_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    get_mock = AsyncMock(return_value={"record_list": [{"id": 1, "type": 1}]})
    monkeypatch.setattr(client, "_authenticated_get", get_mock)

    records = await client.get_toilet_records("PB01", 100, 200)

    assert len(records) == 1
    path, params = get_mock.await_args.args
    assert path == "/catbox/record"
    assert params["device_name"] == "PB01"
    assert params["bind_status"] == str(DeviceRole.OWNER.value)
    assert params["start_time"] == "100"
    assert params["end_time"] == "200"


async def test_get_toilet_statistics_passes_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, role=DeviceRole.SHARED)
    get_mock = AsyncMock(return_value=[{"date": "2026-05-31", "count": 3}])
    monkeypatch.setattr(client, "_authenticated_get", get_mock)

    stats = await client.get_toilet_statistics("PB01", 100, 200, zone_seconds=-10800)

    assert len(stats) == 1
    _, params = get_mock.await_args.args
    assert params["zone"] == "-10800"
    assert params["bind_status"] == str(DeviceRole.SHARED.value)


async def test_list_cats_parses_array(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    monkeypatch.setattr(
        client,
        "_authenticated_get",
        AsyncMock(return_value=[{"id": 1, "name": "Mini"}]),
    )

    cats = await client.list_cats("PB01")

    assert [c.name for c in cats] == ["Mini"]


async def test_authenticated_get_stamps_user_id_and_unwraps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_authenticated_get`` signs the request, injects user_id, and unwraps the envelope."""
    client = _client(monkeypatch)
    transport_mock = AsyncMock(return_value={"code": 0, "data": {"hello": "world"}})
    monkeypatch.setattr(client._transport, "authenticated_get", transport_mock)

    data = await client._authenticated_get(
        "/catbox/cat/list", {"device_name": "PB01"}, context="list cats"
    )

    assert data == {"hello": "world"}
    url, params = transport_mock.await_args.args
    assert url.endswith("/catbox/cat/list")
    assert params["user_id"] == "400068852"
    # The session-derived signing material is wired through.
    assert "encrypted_user_id" in transport_mock.await_args.kwargs
    assert "session_token" in transport_mock.await_args.kwargs


def test_require_session_raises_before_login() -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    with pytest.raises(NeakasaError, match="not authenticated"):
        client._require_session()


def test_require_iot_session_raises_without_token() -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result().with_iot_token("")
    with pytest.raises(NeakasaError, match="IoT session not established"):
        client._require_iot_session()


def test_require_iot_session_returns_token() -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    assert client._require_iot_session() == "iot-token"


def test_watch_status_requires_login() -> None:
    client = NeakasaClient(email="user@example.com", password="pw")
    with pytest.raises(NeakasaError, match="not authenticated"):
        client.watch_status()


def test_watch_status_returns_stream() -> None:
    from neakasa_litterbox_sdk import StatusStream

    client = NeakasaClient(email="user@example.com", password="pw")
    client._login_result = _login_result()
    stream = client.watch_status(tls_insecure=True)
    assert isinstance(stream, StatusStream)
