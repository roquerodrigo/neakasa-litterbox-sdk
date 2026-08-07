"""Async MQTT transport for the Aliyun mobile-channel push stream.

Wraps ``aiomqtt`` so the SDK can talk to the broker from inside an
existing event loop (Home Assistant, asyncio scripts, ...). The
network loop is the same asyncio loop the caller is already on — no
threads.

Exposes a small surface the status-stream layer builds on:
:meth:`connect` / :meth:`disconnect` for lifecycle, :meth:`subscribe`
to register a topic, :meth:`publish` to send a payload, and
:meth:`bind_account` for the request/reply roundtrip on
``/app/up/account/bind``. Incoming messages flow into the caller's
``on_message`` coroutine via a background dispatcher task started by
:meth:`connect`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import ssl
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeAlias

import aiomqtt

from .._status_codes import ENVELOPE_SUCCESS_CODE
from ..exceptions import ApiError, TransportError
from ..utils._json import get_int, get_str, loads
from .broker_ca import BROKER_ROOT_CA_PATH

if TYPE_CHECKING:
    from ..utils._json import JsonObject
    from .mqtt_auth import MqttCredentials

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.aliyun.mqtt")

OnMessage: TypeAlias = Callable[[str, bytes], Awaitable[None]]
OnConnectionLost: TypeAlias = Callable[[Exception], None]


class MqttTransport:
    """Manage a single ``aiomqtt`` session against the Aliyun mobile channel."""

    def __init__(
        self,
        credentials: MqttCredentials,
        on_message: OnMessage,
        *,
        keepalive: int = 60,
        ca_certs: str | None = None,
        tls_context: ssl.SSLContext | None = None,
        on_connection_lost: OnConnectionLost | None = None,
    ) -> None:
        self._credentials = credentials
        self._on_message = on_message
        self._on_connection_lost = on_connection_lost
        self._keepalive = keepalive
        # ``ca_certs`` replaces the system trust store; the bundled
        # broker root is added on top either way. ``tls_context``
        # short-circuits both — caller hands in a fully-built
        # :class:`ssl.SSLContext`.
        self._ca_certs = ca_certs
        # Building the context calls ``load_default_certs`` /
        # ``load_verify_locations`` synchronously (file I/O) — defer it
        # to :meth:`connect` so we can run it in an executor and avoid
        # blocking the caller's event loop.
        self._tls_context: ssl.SSLContext | None = tls_context
        self._client: aiomqtt.Client | None = None
        self._dispatch_task: asyncio.Task[None] | None = None
        self._pending_replies: dict[str, asyncio.Future[JsonObject]] = {}

    def _build_tls_context(self) -> ssl.SSLContext:
        """Build the verifying SSL context off-thread (blocking file I/O)."""
        context = ssl.create_default_context(cafile=self._ca_certs)
        context.load_verify_locations(cafile=str(BROKER_ROOT_CA_PATH))
        return context

    @property
    def topic_prefix(self) -> str:
        """``/sys/<productKey>/<deviceName>`` — caller-visible namespace."""
        return f"/sys/{self._credentials.product_key}/{self._credentials.device_name}"

    async def connect(self) -> None:
        """Open the TCP+TLS connection and start the message dispatcher."""
        if self._client is not None:
            return
        if self._tls_context is None:
            loop = asyncio.get_running_loop()
            self._tls_context = await loop.run_in_executor(None, self._build_tls_context)
        client = aiomqtt.Client(
            hostname=self._credentials.host,
            port=self._credentials.port,
            identifier=self._credentials.client_id,
            username=self._credentials.username,
            password=self._credentials.password,
            tls_context=self._tls_context,
            keepalive=self._keepalive,
            clean_session=True,
        )
        await client.__aenter__()
        self._client = client
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        log.info("MQTT connected to %s", self._credentials.host)

    async def disconnect(self) -> None:
        """Tear down the session and stop the dispatcher. Idempotent."""
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._dispatch_task
            self._dispatch_task = None
        if self._client is not None:
            with contextlib.suppress(aiomqtt.MqttError):
                await self._client.__aexit__(None, None, None)
            self._client = None
        log.info("MQTT disconnected from %s", self._credentials.host)

    async def subscribe(self, topic: str, qos: int = 0) -> None:
        """Subscribe to ``topic`` (may be a wildcard pattern)."""
        await self._require_client().subscribe(topic, qos=qos)

    async def publish(self, topic: str, payload: bytes, *, qos: int = 0) -> None:
        """Publish ``payload`` to ``topic`` (fire-and-forget at QoS 0)."""
        await self._require_client().publish(topic, payload=payload, qos=qos)

    async def bind_account(
        self,
        iot_token: str,
        *,
        timeout: float = 10.0,  # noqa: ASYNC109 - public API surface; enforced via asyncio.wait_for
    ) -> None:
        """Associate this MQTT session with the user identified by ``iot_token``.

        Publishes ``/app/up/account/bind`` and waits for the matching
        ``bind_reply`` on the down-stream namespace. Without this step
        the broker keeps the session anonymous and the cloud-side
        fanout won't route the user's devices' property pushes here.
        Raises on a non-200 reply code.
        """
        request_id = uuid.uuid4().hex
        body = json.dumps(
            {
                "id": request_id,
                "system": {"version": "1.0", "time": str(int(time.time() * 1000))},
                "request": {"clientId": self._credentials.username},
                "params": {"iotToken": iot_token},
            }
        ).encode("utf-8")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[JsonObject] = loop.create_future()
        self._pending_replies[request_id] = future
        try:
            await self.publish(f"{self.topic_prefix}/app/up/account/bind", body, qos=1)
            reply = await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError as exc:
            raise TransportError(
                f"Failed to bind account: no reply within {timeout}s",
            ) from exc
        finally:
            self._pending_replies.pop(request_id, None)
        code = get_int(reply, "code", default=-1)
        if code != ENVELOPE_SUCCESS_CODE:
            raise ApiError(
                f"Failed to bind account: server returned code {code}",
                code=code,
                server_message=get_str(reply, "message") or None,
            )

    def _require_client(self) -> aiomqtt.Client:
        if self._client is None:
            raise TransportError("Failed to use MQTT: not connected, call connect() first")
        return self._client

    async def _dispatch_loop(self) -> None:
        """Pull messages from aiomqtt and route them to handlers."""
        client = self._require_client()
        try:
            async for message in client.messages:
                topic = str(message.topic)
                raw = message.payload
                payload = raw if isinstance(raw, bytes) else bytes(raw)
                log.debug("MQTT message on %s (%d bytes)", topic, len(payload))
                if self._pending_replies and self._try_dispatch_reply(payload):
                    continue
                try:
                    await self._on_message(topic, payload)
                except Exception:
                    log.exception("MQTT on_message handler raised")
        except asyncio.CancelledError:
            raise
        except aiomqtt.MqttError as exc:
            log.warning("MQTT dispatcher exited: %s", exc)
            self._signal_connection_lost(exc)
        else:
            log.warning("MQTT dispatcher exited: message stream ended")
            self._signal_connection_lost(
                TransportError("Failed to keep MQTT session: message stream ended"),
            )

    def _signal_connection_lost(self, exc: Exception) -> None:
        """Tell the owner the session died so consumers stop waiting silently."""
        if self._on_connection_lost is not None:
            self._on_connection_lost(exc)

    def _try_dispatch_reply(self, payload: bytes) -> bool:
        """Return ``True`` if ``payload`` resolved a pending request-id wait."""
        try:
            body = loads(payload)
        except ValueError:
            return False
        request_id = body.get("id")
        if not isinstance(request_id, str):
            return False
        future = self._pending_replies.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(body)
        return True
