"""Status-stream lifecycle and handler dispatch.

The MQTT transport and credential derivation are mocked at the
boundary; dispatch is driven by feeding raw push payloads straight into
``_handle_message``. No network.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiomqtt
import pytest

from neakasa_litterbox_sdk import (
    DEFAULT_RECONNECT_POLICY,
    LoginResult,
    OperatingState,
    ReconnectPolicy,
    TransportError,
    UserInfo,
)
from neakasa_litterbox_sdk.status_stream import StatusStream


def _login() -> LoginResult:
    return LoginResult(
        user_id="400068852",
        user_token="utoken",
        aes_key="k",
        aes_iv="iv",
        user_info=UserInfo(
            user_id=42,
            user_name="user@example.com",
            ali_user_id=400068852,
            ali_authentication_token="ali-auth-token",
        ),
        issued_at=1_700_000_000.0,
        iot_token="iot-token",
    )


def _stream(*, reconnect: ReconnectPolicy | None = DEFAULT_RECONNECT_POLICY) -> StatusStream:
    return StatusStream(MagicMock(), _login(), reconnect=reconnect)


def _push(items: dict[str, object], *, device: str = "PB01") -> bytes:
    import json

    return json.dumps({"params": {"deviceName": device, "items": items}}).encode("utf-8")


async def test_start_connects_subscribes_binds(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream()
    transport = MagicMock()
    transport.topic_prefix = "/sys/pk/dn"
    transport.connect = AsyncMock()
    transport.subscribe = AsyncMock()
    transport.bind_account = AsyncMock()
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.status_stream.derive_mqtt_credentials",
        AsyncMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.status_stream.MqttTransport",
        MagicMock(return_value=transport),
    )

    await stream.start()

    transport.connect.assert_awaited_once()
    transport.subscribe.assert_awaited_once_with("/sys/pk/dn/app/down/#", qos=1)
    transport.bind_account.assert_awaited_once_with("iot-token")

    # Idempotent: a second start is a no-op (transport already set).
    await stream.start()
    transport.connect.assert_awaited_once()


async def test_stop_disconnects_and_is_idempotent() -> None:
    stream = _stream()
    transport = MagicMock()
    transport.disconnect = AsyncMock()
    stream._transport = transport

    await stream.stop()
    transport.disconnect.assert_awaited_once()
    assert stream._transport is None

    await stream.stop()  # already torn down
    transport.disconnect.assert_awaited_once()


async def test_run_forever_returns_after_stop() -> None:
    stream = _stream()
    transport = MagicMock()
    transport.disconnect = AsyncMock()
    stream._transport = transport
    await stream.stop()  # sets the stop event
    await stream.run_forever()  # returns immediately


def _patch_transport(monkeypatch: pytest.MonkeyPatch, transport: MagicMock) -> MagicMock:
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.status_stream.derive_mqtt_credentials",
        AsyncMock(return_value=MagicMock()),
    )
    factory = MagicMock(return_value=transport)
    monkeypatch.setattr("neakasa_litterbox_sdk.status_stream.MqttTransport", factory)
    return factory


def _transport_mock() -> MagicMock:
    transport = MagicMock()
    transport.topic_prefix = "/sys/pk/dn"
    transport.connect = AsyncMock()
    transport.subscribe = AsyncMock()
    transport.bind_account = AsyncMock()
    transport.disconnect = AsyncMock()
    return transport


async def test_start_disconnects_when_subscribe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream()
    transport = _transport_mock()
    transport.subscribe = AsyncMock(side_effect=TransportError("Failed to subscribe: boom"))
    _patch_transport(monkeypatch, transport)

    with pytest.raises(TransportError, match="subscribe"):
        await stream.start()

    transport.disconnect.assert_awaited_once()
    assert stream._transport is None


async def test_start_disconnects_when_bind_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream()
    transport = _transport_mock()
    transport.bind_account = AsyncMock(side_effect=TransportError("Failed to bind account: boom"))
    _patch_transport(monkeypatch, transport)

    with pytest.raises(TransportError, match="bind account"):
        await stream.start()

    transport.disconnect.assert_awaited_once()
    assert stream._transport is None


async def test_run_forever_raises_when_connection_lost(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream(reconnect=None)
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()

    on_connection_lost = factory.call_args.kwargs["on_connection_lost"]
    on_connection_lost(aiomqtt.MqttError("connection lost"))

    assert stream._reconnect_task is None
    with pytest.raises(TransportError, match="Failed to keep status stream alive"):
        await stream.run_forever()


async def test_run_forever_reraises_transport_error_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = _stream(reconnect=None)
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()

    original = TransportError("Failed to keep MQTT session: message stream ended")
    factory.call_args.kwargs["on_connection_lost"](original)

    with pytest.raises(TransportError) as excinfo:
        await stream.run_forever()
    assert excinfo.value is original


async def test_restart_after_connection_loss_clears_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = _stream(reconnect=None)
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()
    factory.call_args.kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))
    await stream.stop()

    await stream.start()
    await stream.stop()
    await stream.run_forever()  # returns cleanly: no stale error survives the restart


async def test_context_manager_starts_and_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = _stream()
    start_mock = AsyncMock()
    stop_mock = AsyncMock()
    monkeypatch.setattr(stream, "start", start_mock)
    monkeypatch.setattr(stream, "stop", stop_mock)
    async with stream as entered:
        assert entered is stream
    start_mock.assert_awaited_once()
    stop_mock.assert_awaited_once()


async def test_handle_message_ignores_non_property_topic() -> None:
    stream = _stream()
    captured: list[object] = []
    stream.on_change(captured.append)
    await stream._handle_message("/sys/pk/dn/app/down/event/other", _push({}))
    assert captured == []


async def test_handle_message_drops_unparsable_payload() -> None:
    stream = _stream()
    captured: list[object] = []
    stream.on_change(captured.append)
    await stream._handle_message("/sys/pk/dn/thing/properties", b"not json")
    assert captured == []


async def test_handle_message_skips_empty_changes() -> None:
    """A property push with no recognizable changes is silently dropped."""
    stream = _stream()
    captured: list[object] = []
    stream.on_change(captured.append)
    # Missing deviceName -> StatusUpdate.from_push returns None.
    import json

    await stream._handle_message(
        "/sys/pk/dn/thing/properties", json.dumps({"params": {}}).encode("utf-8")
    )
    assert captured == []


async def test_handle_message_dispatches_and_fires_on_change() -> None:
    stream = _stream()
    silent: list[tuple[str, bool]] = []
    changes: list[object] = []
    stream.on_silent_mode(lambda d, v: silent.append((d, v)))
    stream.on_change(changes.append)
    await stream._handle_message("/sys/pk/dn/thing/properties", _push({"silentMode": {"value": 1}}))
    assert silent == [("PB01", True)]
    assert len(changes) == 1


async def test_handle_message_swallows_handler_exception() -> None:
    """A raising handler is logged, not propagated, so the stream survives."""
    stream = _stream()

    def _boom(_device: str, _value: bool) -> None:
        raise RuntimeError("handler blew up")

    stream.on_silent_mode(_boom)
    # Should not raise.
    await stream._handle_message("/sys/pk/dn/thing/properties", _push({"silentMode": {"value": 1}}))


def _dispatch(stream: StatusStream, items: dict[str, object]) -> None:
    from neakasa_litterbox_sdk.models.status_update import StatusUpdate

    update = StatusUpdate.from_push({"params": {"deviceName": "PB01", "items": items}})
    assert update is not None
    stream._dispatch(update)


def test_fire_typed_bool_events() -> None:
    stream = _stream()
    sink: dict[str, object] = {}
    stream.on_silent_mode(lambda d, v: sink.__setitem__("silent", v))
    stream.on_child_lock(lambda d, v: sink.__setitem__("child", v))
    stream.on_auto_level(lambda d, v: sink.__setitem__("auto", v))
    stream.on_young_cat_mode(lambda d, v: sink.__setitem__("young", v))
    stream.on_cleaning_enabled(lambda d, v: sink.__setitem__("clean", v))
    stream.on_cat_present(lambda d, v: sink.__setitem__("cat", v))
    stream.on_needs_cleaning(lambda d, v: sink.__setitem__("needs", v))
    stream.on_bucket_full(lambda d, v: sink.__setitem__("bucket", v))
    _dispatch(
        stream,
        {
            "silentMode": {"value": 1},
            "childLockOnOff": {"value": 0},
            "autoLevel": {"value": 1},
            "youngCatMode": {"value": 1},
            "cleanCfg": {"value": {"active": 1}},
            "catLeft": {"value": {"kitten": 1, "stayTime": 9, "needClean": 1}},
            "room_of_bin": {"value": 2},
        },
    )
    assert sink == {
        "silent": True,
        "child": False,
        "auto": True,
        "young": True,
        "clean": True,
        "cat": True,
        "needs": True,
        "bucket": True,
    }


def test_fire_typed_int_str_and_state_events() -> None:
    stream = _stream()
    sink: dict[str, object] = {}
    stream.on_sand_percent(lambda d, v: sink.__setitem__("sand", v))
    stream.on_cat_stay_seconds(lambda d, v: sink.__setitem__("stay", v))
    stream.on_last_sand_added(lambda d, v: sink.__setitem__("added", v))
    stream.on_last_action(lambda d, v: sink.__setitem__("action", v))
    stream.on_operating_state(lambda d, v: sink.__setitem__("state", v))
    _dispatch(
        stream,
        {
            "Sand": {"value": {"percent": 73}},
            "catLeft": {"value": {"kitten": 0, "stayTime": 12, "needClean": 0}},
            "latestAddSandTime": {"value": "2026-05-31 10:00:00"},
            "actionLog": {"value": "cleanNow"},
            "bucketStatus": {"value": 2},
        },
    )
    assert sink["sand"] == 73
    assert sink["stay"] == 12
    assert sink["added"] == "2026-05-31 10:00:00"
    assert sink["action"] == "cleanNow"
    assert sink["state"] is OperatingState.CLEANING


def test_fire_typed_unknown_goes_to_on_unknown() -> None:
    stream = _stream()
    unknown: list[tuple[str, str, object]] = []
    stream.on_unknown(lambda d, k, v: unknown.append((d, k, v)))
    _dispatch(stream, {"Reboot": {"value": 1}})
    assert unknown == [("PB01", "Reboot", 1)]


def test_flatten_skips_non_mapping_entries() -> None:
    """An item whose entry isn't a ``{value: ...}`` mapping is ignored."""
    from neakasa_litterbox_sdk.models.status_update import StatusUpdate

    update = StatusUpdate.from_push(
        {"params": {"deviceName": "PB01", "items": {"silentMode": {"value": 1}, "junk": 5}}}
    )
    assert update is not None
    assert update.changes == {"silent_mode": True}


def test_fire_typed_without_handlers_is_noop() -> None:
    """Known events with no registered handler are dropped silently."""
    stream = _stream()
    # No handlers registered anywhere; dispatch must not raise.
    _dispatch(
        stream,
        {
            "silentMode": {"value": 1},
            "Sand": {"value": {"percent": 5}},
            "latestAddSandTime": {"value": "x"},
            "bucketStatus": {"value": 0},
            "catLeft": {"value": {"kitten": 1, "stayTime": 1, "needClean": 0}},
            "Reboot": {"value": 1},
        },
    )


def _fast_policy(max_attempts: int = 3) -> ReconnectPolicy:
    return ReconnectPolicy(max_attempts=max_attempts, initial_delay=0.0, max_delay=0.0)


async def _drain(stream: StatusStream) -> None:
    """Await the background reconnect the stream just scheduled."""
    task = stream._reconnect_task
    assert task is not None
    await task


async def test_reconnects_after_connection_loss(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = StatusStream(MagicMock(), _login(), reconnect=_fast_policy())
    first, second = _transport_mock(), _transport_mock()
    factory = _patch_transport(monkeypatch, first)
    factory.side_effect = [first, second]

    await stream.start()
    factory.call_args.kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))
    await _drain(stream)

    first.disconnect.assert_awaited_once()
    assert stream._transport is second
    assert second.bind_account.await_count == 1
    assert not stream._stop_event.is_set()


async def test_reconnect_retries_until_the_broker_comes_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = StatusStream(MagicMock(), _login(), reconnect=_fast_policy())
    first, second = _transport_mock(), _transport_mock()
    first.connect = AsyncMock()
    failing = _transport_mock()
    failing.connect = AsyncMock(side_effect=TransportError("Failed to connect: broker down"))
    factory = _patch_transport(monkeypatch, first)
    factory.side_effect = [first, failing, second]

    await stream.start()
    factory.call_args_list[0].kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))
    await _drain(stream)

    assert factory.call_count == 3
    assert stream._transport is second
    assert not stream._stop_event.is_set()


async def test_reconnect_gives_up_and_notifies_the_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = StatusStream(MagicMock(), _login(), reconnect=_fast_policy(max_attempts=2))
    live = _transport_mock()
    dead = _transport_mock()
    dead.connect = AsyncMock(side_effect=TransportError("Failed to connect: broker down"))
    factory = _patch_transport(monkeypatch, live)
    factory.side_effect = [live, dead, dead]

    await stream.start()
    factory.call_args_list[0].kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))
    await _drain(stream)

    assert factory.call_count == 3  # the initial start plus both attempts
    assert stream._transport is None
    with pytest.raises(TransportError, match="Failed to reconnect the status stream after 2"):
        await stream.run_forever()


async def test_second_drop_does_not_stack_reconnect_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = StatusStream(MagicMock(), _login(), reconnect=_fast_policy())
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()
    on_connection_lost = factory.call_args.kwargs["on_connection_lost"]
    on_connection_lost(aiomqtt.MqttError("connection lost"))
    running = stream._reconnect_task
    on_connection_lost(aiomqtt.MqttError("connection lost again"))

    assert stream._reconnect_task is running
    await _drain(stream)


async def test_stop_cancels_a_pending_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = StatusStream(
        MagicMock(),
        _login(),
        reconnect=ReconnectPolicy(max_attempts=3, initial_delay=30.0, max_delay=30.0),
    )
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()
    factory.call_args.kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))
    task = stream._reconnect_task
    assert task is not None

    await stream.stop()

    assert task.cancelled()
    assert stream._reconnect_task is None
    await stream.run_forever()  # a deliberate stop is not a failure


async def test_drop_while_stopping_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = StatusStream(MagicMock(), _login(), reconnect=_fast_policy())
    transport = _transport_mock()
    factory = _patch_transport(monkeypatch, transport)

    await stream.start()
    await stream.stop()
    factory.call_args.kwargs["on_connection_lost"](aiomqtt.MqttError("connection lost"))

    assert stream._reconnect_task is None


def test_reconnect_policy_rejects_impossible_schedules() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        ReconnectPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="delays"):
        ReconnectPolicy(initial_delay=-1.0)
    with pytest.raises(ValueError, match="multiplier"):
        ReconnectPolicy(multiplier=0.5)


def test_reconnect_policy_backs_off_up_to_the_ceiling() -> None:
    policy = ReconnectPolicy(initial_delay=1.0, multiplier=2.0, max_delay=5.0)
    assert [policy.delay_for(attempt) for attempt in range(1, 5)] == [1.0, 2.0, 4.0, 5.0]
