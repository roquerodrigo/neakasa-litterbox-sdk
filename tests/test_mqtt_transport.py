"""Unit tests for the MQTT transport's SSL context handling."""

from __future__ import annotations

import contextlib
import ssl
from unittest.mock import AsyncMock, MagicMock

from neakasa_litterbox_sdk.aliyun.broker_ca import BROKER_ROOT_CA_PATH
from neakasa_litterbox_sdk.aliyun.mqtt_auth import MqttCredentials
from neakasa_litterbox_sdk.aliyun.mqtt_transport import MqttTransport

_BROKER_ROOT_COMMON_NAME = "GlobalSign Root CA"


def _credentials() -> MqttCredentials:
    return MqttCredentials(
        host="broker.example.com",
        port=8883,
        client_id="cid",
        username="user",
        password="pass",
        product_key="pk",
        device_name="dn",
    )


def _subject_common_names(context: ssl.SSLContext) -> set[str]:
    return {
        value
        for cert in context.get_ca_certs()
        for rdn in cert["subject"]
        for key, value in rdn
        if key == "commonName"
    }


def test_build_tls_context_always_validates() -> None:
    transport = MqttTransport(_credentials(), AsyncMock())
    ctx = transport._build_tls_context()
    assert ctx.check_hostname is True
    assert ctx.verify_mode is ssl.CERT_REQUIRED


def test_build_tls_context_trusts_bundled_broker_root() -> None:
    transport = MqttTransport(_credentials(), AsyncMock())
    ctx = transport._build_tls_context()
    assert _BROKER_ROOT_COMMON_NAME in _subject_common_names(ctx)


def test_build_tls_context_keeps_broker_root_alongside_custom_bundle() -> None:
    # ``ca_certs`` replaces the system store, but the broker root has to
    # survive it or the handshake breaks for the caller who supplied it.
    transport = MqttTransport(_credentials(), AsyncMock(), ca_certs=str(BROKER_ROOT_CA_PATH))
    ctx = transport._build_tls_context()
    assert _subject_common_names(ctx) == {_BROKER_ROOT_COMMON_NAME}


def test_init_does_not_build_context_eagerly() -> None:
    # The whole point of the deferred-build refactor: ``__init__`` must
    # not touch ``ssl.create_default_context`` so it doesn't block the
    # caller's event loop with ``load_default_certs`` file I/O.
    transport = MqttTransport(_credentials(), AsyncMock())
    assert transport._tls_context is None


def test_init_accepts_prebuilt_context() -> None:
    prebuilt = ssl.create_default_context()
    transport = MqttTransport(_credentials(), AsyncMock(), tls_context=prebuilt)
    assert transport._tls_context is prebuilt


async def test_connect_builds_context_in_executor(monkeypatch) -> None:
    transport = MqttTransport(_credentials(), AsyncMock())
    # Short-circuit aiomqtt; we only care that ``connect`` populates
    # ``_tls_context`` via the loop's executor before reaching the
    # client.
    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.aliyun.mqtt_transport.aiomqtt.Client",
        MagicMock(return_value=fake_client),
    )
    monkeypatch.setattr(transport, "_dispatch_loop", AsyncMock(return_value=None))
    await transport.connect()
    assert isinstance(transport._tls_context, ssl.SSLContext)
    # Avoid leaving the dispatch task pending across the test boundary.
    if transport._dispatch_task is not None:
        transport._dispatch_task.cancel()
        with contextlib.suppress(BaseException):
            await transport._dispatch_task


async def test_connect_uses_prebuilt_context(monkeypatch) -> None:
    prebuilt = ssl.create_default_context()
    transport = MqttTransport(_credentials(), AsyncMock(), tls_context=prebuilt)
    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    client_factory = MagicMock(return_value=fake_client)
    monkeypatch.setattr(
        "neakasa_litterbox_sdk.aliyun.mqtt_transport.aiomqtt.Client",
        client_factory,
    )
    monkeypatch.setattr(transport, "_dispatch_loop", AsyncMock(return_value=None))
    await transport.connect()
    assert transport._tls_context is prebuilt
    assert client_factory.call_args.kwargs["tls_context"] is prebuilt
    if transport._dispatch_task is not None:
        transport._dispatch_task.cancel()
        with contextlib.suppress(BaseException):
            await transport._dispatch_task
