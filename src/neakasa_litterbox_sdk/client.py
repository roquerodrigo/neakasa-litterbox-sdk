"""High-level client for the Neakasa REST API."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .aliyun.handshake import exchange_for_iot_token
from .aliyun.transport import AliyunTransport
from .auth.session_token import generate_session_token
from .auth.transport import HttpTransport
from .crypto import aes_encrypt_with_boot_key, md5_double_hex
from .exceptions import (
    ApiError,
    AuthenticationError,
    InvalidCredentialsError,
    NeakasaError,
    SessionExpiredError,
)
from .exceptions.credentials import INVALID_CREDENTIALS_CODES
from .exceptions.session import SESSION_EXPIRED_CODES
from .models import (
    Cat,
    DailyStatistics,
    Device,
    DeviceRole,
    DeviceStatus,
    LoginResult,
    Region,
    ToiletRecord,
)
from .status_stream import StatusStream
from .utils._json import get_int, get_str

if TYPE_CHECKING:
    import ssl
    from types import TracebackType

    from .utils._json import JsonObject, JsonValue

log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.client")

_PRODUCT_ID = "a123nCqsrQm3vEbt"
_AREA_CODE = "1"


class NeakasaClient:
    """Synchronous client wrapping the Neakasa REST API.

    The client never logs in implicitly. The caller drives the session
    lifecycle:

    1. Construct ``NeakasaClient(email, password)``.
    2. Call :meth:`login` — pass ``cached=<previous LoginResult>`` to
       resume a stored session (idempotent), or omit it to issue a
       fresh login (e.g. after a :class:`SessionExpiredError`).
    3. Persist ``result.to_dict()`` whenever ``result is not cached``
       (i.e. anything was minted). The SDK has no visibility into
       whatever cache the integration uses.
    """

    def __init__(
        self,
        email: str,
        password: str,
        region: Region = Region.US,
        timeout: float = 10.0,
        language: str = "en",
    ) -> None:
        self._email = email
        self._password = password
        self._region = region
        self._language = language
        self._transport = HttpTransport(timeout=timeout)
        self._aliyun = AliyunTransport(timeout=timeout)
        self._login_result: LoginResult | None = None
        self._device_index: dict[str, Device] = {}

    @property
    def region(self) -> Region:
        """The cloud region this client targets."""
        return self._region

    @property
    def is_authenticated(self) -> bool:
        """``True`` while a login result (fresh or cached) is held in memory."""
        return self._login_result is not None

    @property
    def login_result(self) -> LoginResult | None:
        """The active login result, or ``None`` before ``login()``."""
        return self._login_result

    async def __aenter__(self) -> NeakasaClient:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP sessions. Idempotent."""
        await self._transport.close()
        await self._aliyun.close()

    async def login(self, *, cached: LoginResult | None = None) -> LoginResult:
        """Establish a usable session and return the resulting credentials.

        Pass ``cached=`` with a previously persisted :class:`LoginResult`
        to resume that session idempotently — only the missing pieces
        (REST login, IoT session bootstrap) are minted. Returns the same
        object passed in when nothing needed minting; a fresh instance
        otherwise.

        Omit ``cached=`` (the default) to force a fresh login. Use this
        on first run and after a :class:`SessionExpiredError` propagates.

        Persist ``result.to_dict()`` whenever ``result is not cached`` —
        that identity check distinguishes "minted something" from
        "nothing changed".
        """
        self._login_result = cached
        if self._login_result is None:
            await self._login_rest()
        if not self._require_session().iot_token:
            await self._authenticate_aliyun()
        return self._require_session()

    async def _login_rest(self) -> LoginResult:
        """Issue a fresh REST login and store the new ``LoginResult``."""
        envelope = await self._transport.signed_get_data_envelope(
            self._region.login_url,
            self._build_login_params(),
            language=self._language,
        )
        login_data = _expect_object(
            _unwrap_envelope(envelope, context="login", auth=True),
            context="login",
        )
        result = LoginResult.from_json(login_data)
        self._login_result = result
        log.info("Logged in as %s (region=%s)", self._email, self._region.name)
        return result

    async def get_toilet_records(
        self,
        device_name: str,
        start_time: int,
        end_time: int,
    ) -> list[ToiletRecord]:
        """Fetch the user's litter-box visit history.

        Time bounds are unix seconds. The server filters by the caller's
        role on ``device_name`` (owner vs shared); the SDK resolves that
        role from the device list and the caller doesn't need to think
        about it.
        """
        data = await self._authenticated_get(
            "/catbox/record",
            {
                "device_name": device_name,
                "bind_status": str((await self._resolve_role(device_name)).value),
                "start_time": str(start_time),
                "end_time": str(end_time),
            },
            context="get toilet records",
        )
        return ToiletRecord.list_from_response(data)

    async def get_toilet_statistics(
        self,
        device_name: str,
        start_time: int,
        end_time: int,
        *,
        zone_seconds: int = 0,
    ) -> list[DailyStatistics]:
        """Fetch per-day litter-box statistics.

        Returns one bucket per day with at least one cat visit.
        ``zone_seconds`` is the user's offset from UTC in seconds (e.g.
        ``-10800`` for ``America/Sao_Paulo``); pass ``0`` for UTC if you
        don't need per-day bucketing aligned to a specific timezone.
        """
        data = await self._authenticated_get(
            "/catbox/toilet/statistics",
            {
                "device_name": device_name,
                "bind_status": str((await self._resolve_role(device_name)).value),
                "start_time": str(start_time),
                "end_time": str(end_time),
                "zone": str(zone_seconds),
            },
            context="get toilet statistics",
        )
        return DailyStatistics.list_from_response(data)

    async def list_cats(self, device_name: str) -> list[Cat]:
        """List the cats registered against ``device_name``.

        The returned ``Cat.id`` matches the ``cat_id`` field on
        :class:`ToiletRecord`.
        """
        data = await self._authenticated_get(
            "/catbox/cat/list",
            {
                "device_name": device_name,
                "bind_status": str((await self._resolve_role(device_name)).value),
            },
            context="list cats",
        )
        return Cat.list_from_response(data)

    async def _authenticated_get(
        self,
        path: str,
        params: dict[str, str],
        *,
        context: str,
    ) -> JsonValue:
        """Issue a session-signed GET and return the unwrapped ``data`` payload.

        Stamps the active session's ``user_id`` onto ``params``, signs
        the request with the per-call AES-derived token, and raises on
        the server's ``code != 0``.
        """
        session = self._require_session()
        envelope = await self._transport.authenticated_get(
            f"{self._region.web_url}{path}",
            {**params, "user_id": session.user_id},
            encrypted_user_id=aes_encrypt_with_boot_key(session.user_id),
            session_token=generate_session_token(
                session.user_token, session.aes_key, session.aes_iv
            ),
            language=self._language,
        )
        return _unwrap_envelope(envelope, context=context, auth=True)

    async def _aliyun_call_authed(
        self,
        path: str,
        *,
        api_version: str,
        payload: dict[str, JsonValue],
        language: str,
        context: str,
    ) -> JsonValue:
        """Call an Aliyun endpoint and unwrap; refresh the token once on 401.

        Aliyun's ``iotToken`` expires periodically without notice. When
        the gateway answers 401 we re-run :meth:`_authenticate_aliyun`
        (which uses the REST session that's still valid) and replay the
        request once. A second 401 surfaces ``SessionExpiredError`` to
        the caller — at that point the REST session itself is gone and
        the caller needs to ``login()`` from scratch.
        """
        for attempt in range(2):
            response = await self._aliyun.call(
                path,
                api_version=api_version,
                iot_token=self._require_iot_session(),
                payload=payload,
                language=language,
            )
            try:
                return _unwrap_aliyun(response, context=context)
            except SessionExpiredError:
                if attempt == 0:
                    log.info("Aliyun session expired on %s; refreshing iotToken", context)
                    await self._refresh_iot_session()
                    continue
                raise
        # Unreachable — the loop body either returns, raises, or continues
        # exactly once (attempt 0 -> continue, attempt 1 -> return/raise).
        raise NeakasaError("Internal: aliyun retry loop exhausted")  # pragma: no cover

    def _require_session(self) -> LoginResult:
        """Return the active :class:`LoginResult` or raise if none is held."""
        if self._login_result is None:
            raise NeakasaError(
                "Failed to call endpoint: not authenticated, call login(cached=...) first",
            )
        return self._login_result

    async def list_devices(self) -> list[Device]:
        """List the Neakasa devices registered on the user's account.

        Returns one :class:`Device` per pairing, identical to the mobile
        app's device list. The returned ``Device.device_name`` is the
        identifier the history endpoints expect.
        """
        data = _expect_object(
            await self._aliyun_call_authed(
                "/uc/listBindingByAccount",
                api_version="1.0.8",
                payload={},
                language=f"{self._language}-US",
                context="list devices",
            ),
            context="list devices",
        )
        devices = Device.list_from_response(data)
        self._device_index = {d.device_name: d for d in devices}
        return devices

    async def get_status(self, device_name: str) -> DeviceStatus:
        """Fetch the live property snapshot for ``device_name``.

        Mirrors the data the mobile app's home screen polls: sand level,
        cat presence, cleaning config, mode switches. Always issues a
        network request — the SDK does not cache property readbacks
        because they're inherently time-sensitive.
        """
        return DeviceStatus.from_response(await self._get_properties(device_name))

    def watch_status(
        self,
        *,
        ca_certs: str | None = None,
        tls_insecure: bool = False,
        tls_context: ssl.SSLContext | None = None,
    ) -> StatusStream:
        """Open a live status stream against the user's account.

        Returns a :class:`StatusStream` ready for handler registration.
        Use as an async context manager so the underlying MQTT
        connection tears down cleanly::

            async with client.watch_status() as stream:
                stream.on_silent_mode(handler_silent)
                stream.on_sand_percent(handler_sand)
                stream.on_unknown(handler_unknown)
                await stream.run_forever()

        Handlers fire on the same asyncio loop the caller is running;
        keep them non-blocking and use ``asyncio.create_task`` for
        anything that needs to run alongside the dispatcher.

        ``ca_certs`` lets you point at a CA bundle the broker's chain
        validates against (the Aliyun broker still chains to the legacy
        GlobalSign Root CA dropped by recent ``certifi`` releases).
        ``tls_insecure=True`` skips hostname/cert validation entirely
        for environments where that's acceptable. ``tls_context`` hands
        in a fully-built :class:`ssl.SSLContext` and bypasses both —
        useful for callers (e.g. Home Assistant) that already manage a
        shared, pre-warmed context off the event loop.

        Requires that :meth:`login` has been called first.
        """
        session = self._require_session()
        return StatusStream(
            self._aliyun,
            session,
            ca_certs=ca_certs,
            tls_insecure=tls_insecure,
            tls_context=tls_context,
        )

    async def _get_properties(self, device_name: str) -> JsonObject:
        """Return the raw ``data`` map from ``/thing/properties/get``."""
        device = await self._resolve_device(device_name)
        return _expect_object(
            await self._aliyun_call_authed(
                "/thing/properties/get",
                api_version="1.0.4",
                payload={"iotId": device.iot_id},
                language=f"{self._language}-US",
                context="get device status",
            ),
            context="get device status",
        )

    async def start_clean(self, device_name: str) -> None:
        """Start a cleaning cycle — the mobile app's "Clean Now" button.

        Returns once the device gateway has acknowledged the command;
        physical motion runs asynchronously.
        """
        await self._invoke_service(
            device_name,
            identifier="cleanNow",
            args={"bStartClean": 1},
            context="start clean",
        )

    async def stop_clean(self, device_name: str) -> None:
        """Cancel a running cleaning cycle."""
        await self._invoke_service(
            device_name,
            identifier="cleanNow",
            args={"bStartClean": 0},
            context="stop clean",
        )

    async def start_level(self, device_name: str) -> None:
        """Start a litter-leveling pass — the mobile app's "Smooth" button.

        Drives the leveling motor to redistribute litter evenly across
        the floor.
        """
        await self._invoke_service(
            device_name,
            identifier="sandLeveling",
            args={"bStartLeveling": 1},
            context="start level",
        )

    async def stop_level(self, device_name: str) -> None:
        """Cancel a running leveling pass."""
        await self._invoke_service(
            device_name,
            identifier="sandLeveling",
            args={"bStartLeveling": 0},
            context="stop level",
        )

    async def set_auto_clean(self, device_name: str, enabled: bool) -> None:
        """Toggle scheduled auto-cleaning on the device.

        Preserves the existing ``cleanType`` / ``cleanParam`` (mode +
        interval) by reading them back first; only the ``active`` flag
        flips. Use the official app to configure those values for now —
        the SDK doesn't expose them as inputs.
        """
        properties = await self._get_properties(device_name)
        clean_cfg = _expect_object(
            properties.get("cleanCfg", {}),
            context="set auto clean",
        )
        value = _expect_object(clean_cfg.get("value", {}), context="set auto clean")
        new_cfg: dict[str, int] = {
            "cleanType": get_int(value, "cleanType"),
            "cleanParam": get_int(value, "cleanParam"),
            "active": 1 if enabled else 0,
        }
        await self._set_property(device_name, "cleanCfg", new_cfg, context="set auto clean")

    async def set_auto_level(self, device_name: str, enabled: bool) -> None:
        """Toggle automatic litter-leveling after each clean cycle."""
        await self._set_property(
            device_name, "autoLevel", 1 if enabled else 0, context="set auto level"
        )

    async def set_silent_mode(self, device_name: str, enabled: bool) -> None:
        """Toggle the device's silent mode (suppresses motor / status sounds)."""
        await self._set_property(
            device_name, "silentMode", 1 if enabled else 0, context="set silent mode"
        )

    async def set_child_lock(self, device_name: str, enabled: bool) -> None:
        """Toggle the device's child lock (ignores manual button presses while on)."""
        await self._set_property(
            device_name,
            "childLockOnOff",
            1 if enabled else 0,
            context="set child lock",
        )

    async def calibrate_sand(self, device_name: str, percent: int) -> None:
        """Calibrate the device's sand-level sensor to ``percent`` (1-100).

        Tells the device that the current physical litter load corresponds
        to ``percent`` of "full" — the mobile app's "Calibrate" flow
        drives this from a slider after the user fills the box to a
        marked level. The value lands on the ``Sand.percent`` property
        readback. Range mirrors the device's TSL schema (``min=1``,
        ``max=100``); out-of-range values get a clear client-side error
        instead of a generic ``6306`` from the gateway.
        """
        if not 1 <= percent <= 100:
            raise NeakasaError(
                f"Failed to calibrate sand: percent must be in 1..100, got {percent}",
            )
        await self._invoke_service(
            device_name,
            identifier="sandAdj",
            args={"percent": percent},
            context="calibrate sand",
        )

    async def _invoke_service(
        self,
        device_name: str,
        *,
        identifier: str,
        args: dict[str, int],
        context: str,
    ) -> None:
        """POST one ``/thing/service/invoke`` and raise on an envelope error."""
        device = await self._resolve_device(device_name)
        await self._aliyun_call_authed(
            "/thing/service/invoke",
            api_version="1.0.5",
            payload={"iotId": device.iot_id, "identifier": identifier, "args": args},
            language=f"{self._language}-US",
            context=context,
        )

    async def _set_property(
        self,
        device_name: str,
        key: str,
        value: int | dict[str, int],
        *,
        context: str,
    ) -> None:
        """POST one ``/thing/properties/set`` and raise on an envelope error."""
        device = await self._resolve_device(device_name)
        await self._aliyun_call_authed(
            "/thing/properties/set",
            api_version="1.0.5",
            payload={"iotId": device.iot_id, "items": {key: value}},
            language=f"{self._language}-US",
            context=context,
        )

    async def _resolve_role(self, device_name: str) -> DeviceRole:
        """Return the caller's :class:`DeviceRole` for ``device_name``."""
        return (await self._resolve_device(device_name)).role

    async def _resolve_device(self, device_name: str) -> Device:
        """Return the cached :class:`Device`, refreshing the index on a miss."""
        if device_name not in self._device_index:
            await self.list_devices()
        if device_name not in self._device_index:
            raise NeakasaError(
                f"Failed to resolve device: '{device_name}' is not registered on this account",
            )
        return self._device_index[device_name]

    async def _refresh_iot_session(self) -> None:
        """Re-establish the IoT session, falling back to a full REST re-login.

        First tries the 4-step Aliyun handshake with the existing
        ``aliAuthenticationToken``. If that token has also expired (or the
        Aliyun API is transiently unavailable), issues a fresh REST login
        to mint a new ``aliAuthenticationToken`` and retries the handshake.
        """
        try:
            await self._authenticate_aliyun()
        except (ApiError, AuthenticationError, NeakasaError):
            log.info("Aliyun handshake failed, attempting full re-login")
            await self._login_rest()
            await self._authenticate_aliyun()

    async def _authenticate_aliyun(self) -> str:
        """Exchange the REST session for an Aliyun IoT session and return the new token.

        Runs the 4-step OpenAccount handshake (region/get → connect.json
        → loginbyoauth.json → createSessionByAuthCode) and stores the
        resulting ``iotToken`` on :attr:`login_result`. :meth:`login`
        calls this lazily when no IoT token is cached.
        """
        session = self._require_session()
        iot_token = await exchange_for_iot_token(
            self._aliyun,
            session.user_info.ali_authentication_token,
            language=f"{self._language}-US",
        )
        self._login_result = session.with_iot_token(iot_token)
        log.debug("IoT session established for %s", self._email)
        return iot_token

    def _require_iot_session(self) -> str:
        """Return the cached ``iotToken`` or raise if the IoT session is missing."""
        session = self._require_session()
        if not session.iot_token:
            raise NeakasaError(
                "Failed to call endpoint: IoT session not established, call login() first",
            )
        return session.iot_token

    def _build_login_params(self) -> dict[str, str]:
        """Return the form parameters expected by the REST login endpoint."""
        return {
            "areaCode": _AREA_CODE,
            "productId": _PRODUCT_ID,
            "userName": self._email,
            "phone": "",
            "email": self._email,
            "password": md5_double_hex(self._password),
            "userAppVersion": "2.2.6",
            "deviceNumber": "neakasa-litterbox-sdk",
            "deviceToken": "neakasa-litterbox-sdk",
            "deviceType": "2",
            "devSysVer": "neakasa-litterbox-sdk/0.1.0",
        }


def _unwrap_envelope(envelope: JsonObject, *, context: str, auth: bool = False) -> JsonValue:
    """Unwrap the GoLang-server envelope, raising on non-zero ``code``.

    Returns the raw ``data`` field which depending on the endpoint can be a
    JSON object, an array, ``null``, or a primitive. Callers narrow the
    shape they expect.
    """
    code = get_int(envelope, "code", default=-1)
    message = get_str(envelope, "message") or get_str(envelope, "msg")
    if code != 0:
        error_cls = _error_class_for(code) if auth else ApiError
        raise error_cls(
            f"Failed to {context}: server returned code {code}",
            code=code,
            server_message=message or None,
        )
    return envelope.get("data")


# The Aliyun mobile-channel API Gateway uses HTTP-style codes
# (200 = OK), with 401 specifically meaning the ``iotToken`` is no
# longer accepted. Surface that as :class:`SessionExpiredError` so
# callers (and :meth:`NeakasaClient._aliyun_call_authed`) can react
# with a token refresh instead of treating it as a generic failure.
_ALIYUN_SESSION_EXPIRED_CODES: frozenset[int] = frozenset({401})


def _unwrap_aliyun(envelope: JsonObject, *, context: str) -> JsonValue:
    """Unwrap an Aliyun IoT API Gateway envelope (success is ``code == 200``)."""
    code = get_int(envelope, "code", default=-1)
    message = get_str(envelope, "message")
    if code != 200:
        error_cls: type[ApiError] = (
            SessionExpiredError if code in _ALIYUN_SESSION_EXPIRED_CODES else ApiError
        )
        raise error_cls(
            f"Failed to {context}: server returned code {code}",
            code=code,
            server_message=message or None,
        )
    return envelope.get("data")


def _error_class_for(code: int) -> type[ApiError]:
    """Pick the most specific exception subclass for an auth-shaped ``code``."""
    if code in SESSION_EXPIRED_CODES:
        return SessionExpiredError
    if code in INVALID_CREDENTIALS_CODES:
        return InvalidCredentialsError
    return AuthenticationError


def _expect_object(value: JsonValue, *, context: str) -> JsonObject:
    """Narrow a ``JsonValue`` to a JSON object or raise on a shape mismatch."""
    if isinstance(value, Mapping):
        return value
    raise ApiError(
        f"Failed to {context}: expected object in response, got {type(value).__name__}",
        code=-1,
    )
