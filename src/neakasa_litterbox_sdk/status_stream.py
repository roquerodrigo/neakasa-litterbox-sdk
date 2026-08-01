"""Real-time status push stream consumers can attach to.

Wraps the MQTT plumbing in a context manager: enter opens the session
and binds the user; exit tears it down. Consumers register typed
callbacks for the events they care about — one per property — plus an
optional fallback for raw passthrough and a "fired on every update"
catchall.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias

from .aliyun.mqtt_auth import derive_mqtt_credentials
from .aliyun.mqtt_transport import MqttTransport
from .models import OperatingState, StatusUpdate
from .utils._json import JsonValue, loads

if TYPE_CHECKING:
    import ssl
    from types import TracebackType

    from .aliyun.transport import AliyunTransport
    from .models import LoginResult

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.status_stream")

OnBoolEvent: TypeAlias = Callable[[str, bool], None]
OnIntEvent: TypeAlias = Callable[[str, int], None]
OnStrEvent: TypeAlias = Callable[[str, str], None]
OnOperatingStateEvent: TypeAlias = Callable[[str, OperatingState], None]
OnUnknownEvent: TypeAlias = Callable[[str, str, JsonValue], None]
OnAnyEvent: TypeAlias = Callable[[StatusUpdate], None]


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
    """

    def __init__(
        self,
        aliyun: AliyunTransport,
        login: LoginResult,
        *,
        ca_certs: str | None = None,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        self._aliyun = aliyun
        self._login = login
        self._ca_certs = ca_certs
        self._tls_context = tls_context
        self._transport: MqttTransport | None = None
        self._stop_event = asyncio.Event()
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

    async def __aenter__(self) -> StatusStream:
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
        """Open the MQTT session, subscribe, and bind to the user's account."""
        if self._transport is not None:
            return
        credentials = await derive_mqtt_credentials(self._aliyun, gateway_host=self._login.iot_host)
        transport = MqttTransport(
            credentials,
            on_message=self._handle_message,
            ca_certs=self._ca_certs,
            tls_context=self._tls_context,
        )
        await transport.connect()
        await transport.subscribe(f"{transport.topic_prefix}/app/down/#", qos=1)
        await transport.bind_account(self._login.iot_token)
        self._transport = transport
        self._stop_event.clear()
        log.info("Status stream live for %s", self._login.user_info.user_name)

    async def stop(self) -> None:
        """Tear down the MQTT session. Idempotent."""
        if self._transport is None:
            return
        await self._transport.disconnect()
        self._transport = None
        self._stop_event.set()
        log.info("Status stream stopped")

    async def run_forever(self) -> None:
        """Block the caller until :meth:`stop` is called or the task is cancelled."""
        await self._stop_event.wait()

    def on_silent_mode(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, enabled)`` whenever silent mode toggles."""
        self._on_silent_mode = fn

    def on_child_lock(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, enabled)`` whenever the child lock toggles."""
        self._on_child_lock = fn

    def on_auto_level(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, enabled)`` whenever auto-level toggles."""
        self._on_auto_level = fn

    def on_young_cat_mode(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, enabled)`` whenever kitten mode toggles."""
        self._on_young_cat_mode = fn

    def on_cleaning_enabled(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, enabled)`` whenever scheduled cleaning toggles."""
        self._on_cleaning_enabled = fn

    def on_cat_present(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, present)`` whenever a cat enters or leaves."""
        self._on_cat_present = fn

    def on_needs_cleaning(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, needs_cleaning)`` when the device flags one."""
        self._on_needs_cleaning = fn

    def on_bucket_full(self, fn: OnBoolEvent) -> None:
        """Fires with ``(device_name, full)`` when the waste bin status flips."""
        self._on_bucket_full = fn

    def on_operating_state(self, fn: OnOperatingStateEvent) -> None:
        """Fires with ``(device_name, state)`` when the box changes activity.

        ``state`` is an :class:`OperatingState` (idle / cleaning /
        restoring / leveling / cat_appears); unrecognised codes arrive as
        :attr:`OperatingState.UNKNOWN`.
        """
        self._on_operating_state = fn

    def on_sand_percent(self, fn: OnIntEvent) -> None:
        """Fires with ``(device_name, percent_0_to_100)`` on each litter-level update."""
        self._on_sand_percent = fn

    def on_cat_stay_seconds(self, fn: OnIntEvent) -> None:
        """Fires with ``(device_name, seconds)`` while a cat is present."""
        self._on_cat_stay_seconds = fn

    def on_last_sand_added(self, fn: OnStrEvent) -> None:
        """Fires with ``(device_name, "YYYY-MM-DD HH:MM:SS")`` on each refill."""
        self._on_last_sand_added = fn

    def on_last_action(self, fn: OnStrEvent) -> None:
        """Fires with ``(device_name, action)`` for each device-reported action string."""
        self._on_last_action = fn

    def on_unknown(self, fn: OnUnknownEvent) -> None:
        """Fires with ``(device_name, raw_key, raw_value)`` for any unmapped property.

        Useful for surfacing new server-side fields the SDK doesn't yet
        translate — see :class:`StatusUpdate` for the passthrough rules.
        """
        self._on_unknown = fn

    def on_change(self, fn: OnAnyEvent) -> None:
        """Fires with the whole :class:`StatusUpdate` for every push.

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
