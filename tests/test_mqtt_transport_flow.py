"""MQTT transport lifecycle: bind, dispatch, reply routing, teardown.

``aiomqtt.Client`` is mocked at the boundary; no broker.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import aiomqtt
import pytest

from neakasa_litterbox_sdk.aliyun.mqtt_auth import MqttCredentials
from neakasa_litterbox_sdk.aliyun.mqtt_transport import MqttTransport
from neakasa_litterbox_sdk.exceptions import ApiError, TransportError


def _credentials() -> MqttCredentials:
    return MqttCredentials(
        host="broker.example.com",
        port=1883,
        client_id="cid",
        username="dn&pk",
        password="pass",
        product_key="pk",
        device_name="dn",
    )


def _transport() -> MqttTransport:
    return MqttTransport(_credentials(), AsyncMock())


def test_topic_prefix() -> None:
    assert _transport().topic_prefix == "/sys/pk/dn"


def test_require_client_raises_when_disconnected() -> None:
    with pytest.raises(TransportError, match="not connected"):
        _transport()._require_client()


async def test_subscribe_and_publish_delegate_to_client() -> None:
    transport = _transport()
    client = MagicMock()
    client.subscribe = AsyncMock()
    client.publish = AsyncMock()
    transport._client = client

    await transport.subscribe("topic/#", qos=1)
    await transport.publish("topic", b"payload", qos=1)

    client.subscribe.assert_awaited_once_with("topic/#", qos=1)
    client.publish.assert_awaited_once_with("topic", payload=b"payload", qos=1)


async def test_bind_account_success_resolves_on_matching_reply() -> None:
    transport = _transport()
    transport._client = MagicMock()

    published: dict[str, str] = {}

    async def _publish(topic: str, payload: bytes, *, qos: int = 0) -> None:
        body = json.loads(payload)
        published["request_id"] = body["id"]
        # Simulate the broker pushing the reply onto the pending future.
        future = transport._pending_replies[body["id"]]
        future.set_result({"id": body["id"], "code": 200})

    transport.publish = _publish  # type: ignore[assignment]

    await transport.bind_account("iot-token")
    assert published["request_id"]


async def test_bind_account_raises_on_non_200_reply() -> None:
    transport = _transport()
    transport._client = MagicMock()

    async def _publish(topic: str, payload: bytes, *, qos: int = 0) -> None:
        body = json.loads(payload)
        transport._pending_replies[body["id"]].set_result(
            {"id": body["id"], "code": 500, "message": "denied"}
        )

    transport.publish = _publish  # type: ignore[assignment]

    with pytest.raises(ApiError, match="bind account"):
        await transport.bind_account("iot-token")


async def test_bind_account_times_out() -> None:
    transport = _transport()
    transport._client = MagicMock()
    transport.publish = AsyncMock()  # never resolves the future

    with pytest.raises(TransportError, match="no reply within"):
        await transport.bind_account("iot-token", timeout=0.01)
    # The pending entry is cleaned up even on timeout.
    assert transport._pending_replies == {}


def test_try_dispatch_reply_routes_matching_id() -> None:
    transport = _transport()
    loop = asyncio.new_event_loop()
    try:
        future: asyncio.Future[object] = loop.create_future()
        transport._pending_replies["abc"] = future
        handled = transport._try_dispatch_reply(json.dumps({"id": "abc", "code": 200}).encode())
        assert handled is True
        assert future.done()
    finally:
        loop.close()


def test_try_dispatch_reply_ignores_unparsable_or_unmatched() -> None:
    transport = _transport()
    assert transport._try_dispatch_reply(b"not json") is False
    assert transport._try_dispatch_reply(json.dumps({"no_id": 1}).encode()) is False
    assert transport._try_dispatch_reply(json.dumps({"id": "unknown"}).encode()) is False


def test_try_dispatch_reply_ignores_already_done_future() -> None:
    transport = _transport()
    loop = asyncio.new_event_loop()
    try:
        future: asyncio.Future[object] = loop.create_future()
        future.set_result({})
        transport._pending_replies["done"] = future
        assert transport._try_dispatch_reply(json.dumps({"id": "done"}).encode()) is False
    finally:
        loop.close()


async def test_disconnect_cancels_task_and_exits_client() -> None:
    transport = _transport()

    async def _never() -> None:
        await asyncio.Event().wait()

    transport._dispatch_task = asyncio.create_task(_never())
    client = MagicMock()
    client.__aexit__ = AsyncMock()
    transport._client = client

    await transport.disconnect()

    assert transport._dispatch_task is None
    assert transport._client is None
    client.__aexit__.assert_awaited_once()


async def test_disconnect_is_idempotent() -> None:
    transport = _transport()
    await transport.disconnect()  # nothing connected
    assert transport._client is None


async def test_disconnect_suppresses_mqtt_error_on_exit() -> None:
    transport = _transport()
    client = MagicMock()
    client.__aexit__ = AsyncMock(side_effect=aiomqtt.MqttError("already gone"))
    transport._client = client
    await transport.disconnect()  # must not raise
    assert transport._client is None


class _FakeMessages:
    def __init__(self, messages: list[object]) -> None:
        self._messages = messages

    def __aiter__(self) -> _FakeMessages:
        self._it = iter(self._messages)
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._it)
        except StopIteration:  # pragma: no cover - generator boundary
            raise StopAsyncIteration from None


def _message(topic: str, payload: bytes) -> MagicMock:
    msg = MagicMock()
    msg.topic = topic
    msg.payload = payload
    return msg


async def test_connect_is_noop_when_already_connected() -> None:
    transport = _transport()
    sentinel = MagicMock()
    transport._client = sentinel
    await transport.connect()  # early-return: must not rebuild anything
    assert transport._client is sentinel


async def test_dispatch_loop_propagates_cancellation() -> None:
    """Cancelling the dispatcher re-raises ``CancelledError`` (clean shutdown)."""

    class _CancellingMessages:
        def __aiter__(self) -> _CancellingMessages:
            return self

        async def __anext__(self) -> object:
            raise asyncio.CancelledError

    transport = _transport()
    client = MagicMock()
    client.messages = _CancellingMessages()
    transport._client = client

    with pytest.raises(asyncio.CancelledError):
        await transport._dispatch_loop()


async def test_dispatch_loop_routes_property_message_to_handler() -> None:
    on_message = AsyncMock()
    transport = MqttTransport(_credentials(), on_message)
    client = MagicMock()
    client.messages = _FakeMessages([_message("/sys/pk/dn/thing/properties", b'{"x": 1}')])
    transport._client = client

    await transport._dispatch_loop()

    on_message.assert_awaited_once()
    args = on_message.await_args.args
    assert args[0] == "/sys/pk/dn/thing/properties"
    assert args[1] == b'{"x": 1}'


async def test_dispatch_loop_routes_reply_before_handler() -> None:
    on_message = AsyncMock()
    transport = MqttTransport(_credentials(), on_message)
    loop = asyncio.get_running_loop()
    future: asyncio.Future[object] = loop.create_future()
    transport._pending_replies["rid"] = future
    client = MagicMock()
    client.messages = _FakeMessages(
        [_message("/sys/pk/dn/app/down/account/bind_reply", b'{"id": "rid", "code": 200}')]
    )
    transport._client = client

    await transport._dispatch_loop()

    assert future.result() == {"id": "rid", "code": 200}
    on_message.assert_not_awaited()


async def test_dispatch_loop_swallows_handler_exception() -> None:
    on_message = AsyncMock(side_effect=RuntimeError("handler blew up"))
    transport = MqttTransport(_credentials(), on_message)
    client = MagicMock()
    client.messages = _FakeMessages([_message("/sys/pk/dn/thing/properties", b"{}")])
    transport._client = client

    # Must not raise despite the handler exception.
    await transport._dispatch_loop()
    on_message.assert_awaited_once()


async def test_dispatch_loop_logs_and_exits_on_mqtt_error() -> None:
    class _RaisingMessages:
        def __aiter__(self) -> _RaisingMessages:
            return self

        async def __anext__(self) -> object:
            raise aiomqtt.MqttError("connection lost")

    transport = _transport()
    client = MagicMock()
    client.messages = _RaisingMessages()
    transport._client = client

    # The MqttError is caught and the loop returns cleanly.
    await transport._dispatch_loop()


async def test_dispatch_loop_signals_connection_lost_on_mqtt_error() -> None:
    class _RaisingMessages:
        def __aiter__(self) -> _RaisingMessages:
            return self

        async def __anext__(self) -> object:
            raise aiomqtt.MqttError("connection lost")

    errors: list[Exception] = []
    transport = MqttTransport(_credentials(), AsyncMock(), on_connection_lost=errors.append)
    client = MagicMock()
    client.messages = _RaisingMessages()
    transport._client = client

    await transport._dispatch_loop()

    assert len(errors) == 1
    assert isinstance(errors[0], aiomqtt.MqttError)


async def test_dispatch_loop_signals_connection_lost_when_stream_ends() -> None:
    errors: list[Exception] = []
    transport = MqttTransport(_credentials(), AsyncMock(), on_connection_lost=errors.append)
    client = MagicMock()
    client.messages = _FakeMessages([])
    transport._client = client

    await transport._dispatch_loop()

    assert len(errors) == 1
    assert isinstance(errors[0], TransportError)


async def test_dispatch_loop_does_not_signal_on_cancellation() -> None:
    class _CancellingMessages:
        def __aiter__(self) -> _CancellingMessages:
            return self

        async def __anext__(self) -> object:
            raise asyncio.CancelledError

    errors: list[Exception] = []
    transport = MqttTransport(_credentials(), AsyncMock(), on_connection_lost=errors.append)
    client = MagicMock()
    client.messages = _CancellingMessages()
    transport._client = client

    with pytest.raises(asyncio.CancelledError):
        await transport._dispatch_loop()

    assert errors == []


async def test_dispatch_loop_converts_bytearray_payload() -> None:
    on_message = AsyncMock()
    transport = MqttTransport(_credentials(), on_message)
    client = MagicMock()
    client.messages = _FakeMessages([_message("/sys/pk/dn/thing/properties", bytearray(b"abc"))])
    transport._client = client

    await transport._dispatch_loop()
    payload = on_message.await_args.args[1]
    assert isinstance(payload, bytes)
    assert payload == b"abc"
