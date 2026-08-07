"""Real-time status push stream consumers can attach to.

Wraps the MQTT plumbing in a context manager: enter opens the session
and binds the user; exit tears it down. Consumers register typed
callbacks for the events they care about — one per property — plus an
optional fallback for raw passthrough and a "fired on every update"
catchall.

A dropped connection is re-established in the background following the
stream's :class:`ReconnectPolicy`; only once that schedule is exhausted
does the failure reach the consumer.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Self

from .aliyun.mqtt_auth import derive_mqtt_credentials
from .aliyun.mqtt_transport import MqttTransport
from .exceptions import TransportError
from .models import OperatingState, StatusUpdate
from .reconnect_policy import DEFAULT_RECONNECT_POLICY
from .utils._json import JsonValue, loads

if TYPE_CHECKING:
    import ssl
    from types import TracebackType

    from .aliyun.transport import AliyunTransport
    from .models import LoginResult
    from .reconnect_policy import ReconnectPolicy

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.status_stream")

type OnBoolEvent = Callable[[str, bool], None]
type OnIntEvent = Callable[[str, int], None]
type OnStrEvent = Callable[[str, str], None]
type OnOperatingStateEvent = Callable[[str, OperatingState], None]
type OnUnknownEvent = Callable[[str, str, JsonValue], None]
type OnAnyEvent = Callable[[StatusUpdate], None]


class StatusStream:
    """Live property-change stream for the user's Neakasa devices.

    Built by :meth:`NeakasaClient.watch_status`. Designed as an async
    context manager — register handlers up-front or inside the
    ``async with``:

    .. code-block:: python

        async with client.watch_status() as stream:
            stream.on_silent_mode(handler_silent)
            stream.on_sand_percent(handler_sand)
            stream.on_unknown(handler_unknown)
            await stream.run_forever()

    Each ``on_<event>`` registers a handler for one property — the
    callback runs every time that property changes on any device the
    user owns or has been shared. Unhandled known events are dropped;
    properties the SDK doesn't recognise (new server-side fields, raw
    diagnostics like ``Reboot`` / ``NetWorkStatus``) go to
    :meth:`on_unknown` if registered. :meth:`on_change` fires for
    *every* update with the full :class:`StatusUpdate` regardless.

    Handlers run on the same asyncio event loop the caller is using;
    keep them non-blocking and dispatch heavy work via
    ``asyncio.create_task`` if needed.

    ``reconnect`` selects what happens when the broker drops the
    session: the default policy retries in the background with an
    exponential backoff and only reports the failure once its attempts
    run out. Pass ``reconnect=None`` to have the very first drop reach
    :meth:`run_forever` immediately — the right choice for consumers
    that already supervise the stream themselves.
    """

    def __init__(
        self,
        aliyun: AliyunTransport,
        login: LoginResult,
        *,
        ca_certs: str | None = None,
        tls_context: ssl.SSLContext | None = None,
        reconnect: ReconnectPolicy | None = DEFAULT_RECONNECT_POLICY,
    ) -> None:
        self._aliyun = aliyun
        self._login = login
        self._ca_certs = ca_certs
        self._tls_context = tls_context
        self._reconnect_policy = reconnect
        self._transport: MqttTransport | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._stopping = False
        self._stop_event = asyncio.Event()
        self._connection_error: Exception | None = None
        self._on_silent_mode: OnBoolEvent | None = None
        self._on_child_lock: OnBoolEvent | None = None
        self._on_auto_level: OnBoolEvent | None = None
        self._on_young_cat_mode: OnBoolEvent | None = None
        self._on_cleaning_enabled: OnBoolEvent | None = None
        self._on_cat_present: OnBoolEvent | None = None
        self._on_needs_cleaning: OnBoolEvent | None = None
        self._on_bucket_full: OnBoolEvent | None = None
        self._on_operating_state: OnOperatingStateEvent | None = None
        self._on_sand_percent: OnIntEvent | None = None
        self._on_cat_stay_seconds: OnIntEvent | None = None
        self._on_last_sand_added: OnStrEvent | None = None
        self._on_last_action: OnStrEvent | None = None
        self._on_unknown: OnUnknownEvent | None = None
        self._on_change: OnAnyEvent | None = None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        await self.stop()

    async def start(self) -> None:
        """Open the MQTT session, subscribe, and bind to the user's account.

        If subscribing or binding fails, the freshly opened connection is
        torn down before the error propagates — nothing leaks.
        """
        if self._transport is not None:
            return
        self._stopping = False
        self._transport = await self._open_transport()
        self._connection_error = None
        self._stop_event.clear()
        log.info("Status stream live for %s", self._login.user_info.user_name)

    async def stop(self) -> None:
        """Tear down the MQTT session and any pending reconnect. Idempotent."""
        if self._transport is None and self._reconnect_task is None:
            return
        self._stopping = True
        await self._cancel_reconnect()
        transport, self._transport = self._transport, None
        if transport is not None:
            await transport.disconnect()
        self._stop_event.set()
        log.info("Status stream stopped")

    async def run_forever(self) -> None:
        """Block the caller until :meth:`stop` is called or the task is cancelled.

        Raises :class:`TransportError` if the MQTT connection drops and
        the stream's :class:`ReconnectPolicy` cannot bring it back, so
        consumers can rebuild the stream instead of blocking forever.
        """
        await self._stop_event.wait()
        error = self._connection_error
        if error is None:
            return
        if isinstance(error, TransportError):
            raise error
        raise TransportError(f"Failed to keep status stream alive: {error}") from error

    async def _open_transport(self) -> MqttTransport:
        """Connect, subscribe, and bind — tearing the session down on failure."""
        credentials = await derive_mqtt_credentials(self._aliyun, gateway_host=self._login.iot_host)
        transport = MqttTransport(
            credentials,
            on_message=self._handle_message,
            ca_certs=self._ca_certs,
            tls_context=self._tls_context,
            on_connection_lost=self._handle_connection_lost,
        )
        await transport.connect()
        try:
            await transport.subscribe(f"{transport.topic_prefix}/app/down/#", qos=1)
            await transport.bind_account(self._login.iot_token)
        except BaseException:
            await transport.disconnect()
            raise
        return transport

    def _handle_connection_lost(self, exc: Exception) -> None:
        """Retry the session in the background, or report the drop right away."""
        log.warning("Status stream connection lost: %s", exc)
        if self._reconnect_policy is None or self._stopping:
            self._report_failure(exc)
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect(self._reconnect_policy, exc))

    async def _reconnect(self, policy: ReconnectPolicy, cause: Exception) -> None:
        """Rebuild the session on a backoff, reporting the drop if it never comes back."""
        dead, self._transport = self._transport, None
        if dead is not None:
            await dead.disconnect()
        for attempt in range(1, policy.max_attempts + 1):
            await asyncio.sleep(policy.delay_for(attempt))
            try:
                self._transport = await self._open_transport()
            except Exception as exc:
                cause = exc
                log.warning(
                    "Status stream reconnect attempt %d/%d failed: %s",
                    attempt,
                    policy.max_attempts,
                    exc,
                )
                continue
            log.info("Status stream reconnected after %d attempt(s)", attempt)
            return
        self._report_failure(
            TransportError(
                f"Failed to reconnect the status stream after "
                f"{policy.max_attempts} attempts: {cause}",
            ),
        )

    async def _cancel_reconnect(self) -> None:
        """Stop an in-flight reconnect and wait for it to unwind."""
        task, self._reconnect_task = self._reconnect_task, None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def _report_failure(self, exc: Exception) -> None:
        """Hand the failure to the consumer and release :meth:`run_forever` waiters."""
        self._connection_error = exc
        self._stop_event.set()

    def on_silent_mode(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, enabled)`` handler for silent-mode toggles."""
        self._on_silent_mode = fn

    def on_child_lock(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, enabled)`` handler for child-lock toggles."""
        self._on_child_lock = fn

    def on_auto_level(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, enabled)`` handler for auto-level toggles."""
        self._on_auto_level = fn

    def on_young_cat_mode(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, enabled)`` handler for kitten-mode toggles."""
        self._on_young_cat_mode = fn

    def on_cleaning_enabled(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, enabled)`` handler for scheduled-cleaning toggles."""
        self._on_cleaning_enabled = fn

    def on_cat_present(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, present)`` handler for cats entering or leaving."""
        self._on_cat_present = fn

    def on_needs_cleaning(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, needs_cleaning)`` handler for pending-clean flags."""
        self._on_needs_cleaning = fn

    def on_bucket_full(self, fn: OnBoolEvent) -> None:
        """Register a ``(device_name, full)`` handler for waste-bin status flips."""
        self._on_bucket_full = fn

    def on_operating_state(self, fn: OnOperatingStateEvent) -> None:
        """Register a ``(device_name, state)`` handler for activity changes.

        ``state`` is an :class:`OperatingState` (idle / cleaning /
        restoring / leveling / cat_appears); unrecognised codes arrive as
        :attr:`OperatingState.UNKNOWN`.
        """
        self._on_operating_state = fn

    def on_sand_percent(self, fn: OnIntEvent) -> None:
        """Register a ``(device_name, percent_0_to_100)`` handler for litter-level updates."""
        self._on_sand_percent = fn

    def on_cat_stay_seconds(self, fn: OnIntEvent) -> None:
        """Register a ``(device_name, seconds)`` handler fired while a cat is present."""
        self._on_cat_stay_seconds = fn

    def on_last_sand_added(self, fn: OnStrEvent) -> None:
        """Register a ``(device_name, "YYYY-MM-DD HH:MM:SS")`` handler for refills."""
        self._on_last_sand_added = fn

    def on_last_action(self, fn: OnStrEvent) -> None:
        """Register a ``(device_name, action)`` handler for device-reported actions."""
        self._on_last_action = fn

    def on_unknown(self, fn: OnUnknownEvent) -> None:
        """Register a ``(device_name, raw_key, raw_value)`` handler for unmapped properties.

        Useful for surfacing new server-side fields the SDK doesn't yet
        translate — see :class:`StatusUpdate` for the passthrough rules.
        """
        self._on_unknown = fn

    def on_change(self, fn: OnAnyEvent) -> None:
        """Register a handler receiving the whole :class:`StatusUpdate` on every push.

        Runs after the per-event handlers; useful as a catchall when you
        need access to ``device_name`` plus every field in a single
        callback.
        """
        self._on_change = fn

    async def _handle_message(self, topic: str, payload: bytes) -> None:
        if "/thing/properties" not in topic:
            log.debug("Non-property push on %s: %s", topic, payload[:200])
            return
        try:
            body = loads(payload)
        except ValueError:
            log.warning("Dropping unparsable push on %s", topic)
            return
        update = StatusUpdate.from_push(body)
        if update is None or not update.changes:
            return
        try:
            self._dispatch(update)
        except Exception:
            log.exception("Status-stream handler raised")

    def _dispatch(self, update: StatusUpdate) -> None:
        """Route ``update`` to every registered handler."""
        device_name = update.device_name
        for key, value in update.changes.items():
            self._fire_typed(device_name, key, value)
        if self._on_change is not None:
            self._on_change(update)

    def _fire_typed(self, device_name: str, key: str, value: JsonValue) -> None:
        """Dispatch a single ``(key, value)`` to its typed handler, or to on_unknown."""
        if key == "silent_mode" and isinstance(value, bool):
            if self._on_silent_mode is not None:
                self._on_silent_mode(device_name, value)
            return
        if key == "child_lock" and isinstance(value, bool):
            if self._on_child_lock is not None:
                self._on_child_lock(device_name, value)
            return
        if key == "auto_level" and isinstance(value, bool):
            if self._on_auto_level is not None:
                self._on_auto_level(device_name, value)
            return
        if key == "young_cat_mode" and isinstance(value, bool):
            if self._on_young_cat_mode is not None:
                self._on_young_cat_mode(device_name, value)
            return
        if key == "cleaning_enabled" and isinstance(value, bool):
            if self._on_cleaning_enabled is not None:
                self._on_cleaning_enabled(device_name, value)
            return
        if key == "cat_present" and isinstance(value, bool):
            if self._on_cat_present is not None:
                self._on_cat_present(device_name, value)
            return
        if key == "needs_cleaning" and isinstance(value, bool):
            if self._on_needs_cleaning is not None:
                self._on_needs_cleaning(device_name, value)
            return
        if key == "bucket_full" and isinstance(value, bool):
            if self._on_bucket_full is not None:
                self._on_bucket_full(device_name, value)
            return
        if key == "operating_state" and isinstance(value, OperatingState):
            if self._on_operating_state is not None:
                self._on_operating_state(device_name, value)
            return
        if key == "sand_percent" and isinstance(value, int) and not isinstance(value, bool):
            if self._on_sand_percent is not None:
                self._on_sand_percent(device_name, value)
            return
        if key == "cat_stay_seconds" and isinstance(value, int) and not isinstance(value, bool):
            if self._on_cat_stay_seconds is not None:
                self._on_cat_stay_seconds(device_name, value)
            return
        if key == "last_sand_added" and isinstance(value, str):
            if self._on_last_sand_added is not None:
                self._on_last_sand_added(device_name, value)
            return
        if key == "last_action" and isinstance(value, str):
            if self._on_last_action is not None:
                self._on_last_action(device_name, value)
            return
        if self._on_unknown is not None:
            self._on_unknown(device_name, key, value)
