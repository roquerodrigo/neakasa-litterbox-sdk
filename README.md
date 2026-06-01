# neakasa-litterbox-sdk

[![CI](https://github.com/roquerodrigo/neakasa-litterbox-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/neakasa-litterbox-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/neakasa-litterbox-sdk)](https://pypi.org/project/neakasa-litterbox-sdk/)

Async Python SDK for the **Neakasa M1** self-cleaning cat litter box.

> ⚠️ **Unofficial.** This project is not affiliated with, endorsed by,
> or supported by Neakasa or its parent company. It targets the
> publicly-reachable Neakasa cloud API and the Aliyun IoT gateway
> their mobile app uses. The vendor can change either side at any time
> and break this SDK without notice.

## Status

**Alpha** — usable but not yet stable.

| Area | State |
|---|---|
| Email/password login + persisted sessions | ✅ |
| Device list, history (cats, toilet records, daily statistics) | ✅ |
| Live device status (sand level, cat presence, mode flags) | ✅ |
| Device commands (clean, level, calibrate, toggles) | ✅ |
| Real-time MQTT push (`watch_status`) | ✅ |
| Async-native API (`aiohttp` + `aiomqtt`) | ✅ |
| Public API stability | ❌ breaking changes still happen across `0.x` releases |
| Multi-device user accounts | ⚠️ untested — designed for it, but only validated against single-device setups |
| Regions other than US | ⚠️ EU/AP endpoints declared, only US is exercised live |

See [`CHANGELOG.md`](./CHANGELOG.md) for breaking changes between
releases.

## Install

```bash
pip install neakasa-litterbox-sdk
```

Or, with [uv](https://docs.astral.sh/uv/):

```bash
uv add neakasa-litterbox-sdk
```

Requires Python 3.11+.

## Quick start

```python
import asyncio
from neakasa_litterbox_sdk import NeakasaClient, Region


async def main() -> None:
    async with NeakasaClient(email="you@example.com", password="…", region=Region.US) as client:
        await client.login()
        for device in await client.list_devices():
            print(device.product_name, device.device_name, device.role.name.lower())
            for cat in await client.list_cats(device.device_name):
                print(" ", cat.name, cat.weight, cat.unit)


asyncio.run(main())
```

## API

The package re-exports everything below from ``neakasa_litterbox_sdk``;
deeper import paths are internal and may change. **The whole SDK is
asyncio-native** — every I/O method is a coroutine and the client
doubles as an async context manager that closes its underlying HTTP
sessions on exit.

### `NeakasaClient`

The single entry point. Holds session state in memory. Use as an async
context manager so the underlying ``aiohttp`` sessions tear down
cleanly.

```python
NeakasaClient(
    email: str,
    password: str,
    region: Region = Region.US,
    timeout: float = 10.0,
    language: str = "en",
)
```

All I/O methods are coroutines (prefix every call with `await`).

| Method | Signature | Purpose |
|---|---|---|
| `login` | `async (*, cached: LoginResult \| None = None) -> LoginResult` | Establish a session. With `cached=` resumes the stored one idempotently; without it forces a fresh login. |
| `list_devices` | `async () -> list[Device]` | Devices on the account (mobile-app "device picker"). |
| `get_status` | `async (device_name: str) -> DeviceStatus` | Live property snapshot — sand level, cat presence, mode switches. |
| `list_cats` | `async (device_name: str) -> list[Cat]` | Cat profiles registered against a device. |
| `get_toilet_records` | `async (device_name: str, start_time: int, end_time: int) -> list[ToiletRecord]` | Visit history (unix-second bounds). |
| `get_toilet_statistics` | `async (device_name: str, start_time: int, end_time: int, *, zone_seconds: int = 0) -> list[DailyStatistics]` | Per-day aggregates. `zone_seconds` is the UTC offset for bucket alignment (e.g. `-10800` for `America/Sao_Paulo`). |
| `start_clean` / `stop_clean` | `async (device_name: str) -> None` | Run / cancel a cleaning cycle — mobile app's "Clean Now". |
| `start_level` / `stop_level` | `async (device_name: str) -> None` | Run / cancel the leveling motor — redistributes litter evenly. |
| `calibrate_sand` | `async (device_name: str, percent: int) -> None` | Tell the device the current physical load is `percent` (1–100) of "full". |
| `set_auto_clean` | `async (device_name: str, enabled: bool) -> None` | Toggle scheduled auto-cleaning. Preserves the device's existing mode/interval. |
| `set_auto_level` | `async (device_name: str, enabled: bool) -> None` | Toggle automatic litter-leveling after each clean cycle. |
| `set_silent_mode` | `async (device_name: str, enabled: bool) -> None` | Suppress motor / status sounds while on. |
| `set_child_lock` | `async (device_name: str, enabled: bool) -> None` | Ignore manual button presses while on. |
| `watch_status` | `(*, ca_certs=None, tls_insecure=False) -> StatusStream` | Build a live MQTT push stream — use as an `async with` context manager and register per-event handlers on the returned stream. |
| `close` | `async () -> None` | Close the underlying HTTP sessions. Idempotent; `async with client` also does this on exit. |

| Property | Type | |
|---|---|---|
| `region` | `Region` | The cloud region this client targets. |
| `is_authenticated` | `bool` | True once `login()` has succeeded. |
| `login_result` | `LoginResult \| None` | The active session, or `None`. |

### Models

All dataclasses are `frozen=True, slots=True`.

**`Device`** — one entry of `list_devices()`.

| Field | Type | Notes |
|---|---|---|
| `iot_id` | `str` | Stable per pairing. |
| `product_key` | `str` | |
| `product_name` | `str` | e.g. `Neakasa_M1`. |
| `device_name` | `str` | Identifier the history endpoints accept. |
| `category_key` / `category_name` | `str` | |
| `net_type` | `str` | |
| `role` | `DeviceRole` | `OWNER` or `SHARED`. |
| `status` | `int` | |
| `bind_time` | `int` | Unix seconds. |

**`Cat`** — one entry of `list_cats()`.

| Field | Type | Notes |
|---|---|---|
| `id` | `int` | Matches `ToiletRecord.cat_id`. |
| `name` | `str` | |
| `weight` / `unit` | `float`, `str` | |
| `avatar` / `birthday` / `path` | `str` | |
| `variety` | `int` | Breed code; `-1` if not set. |
| `gender` | `CatGender` | `UNKNOWN` / `MALE` / `FEMALE`. |
| `sterilization` / `enabled` | `int` | Raw flags. |

Properties: `is_sterilized: bool`, `is_enabled: bool`.

**`ToiletRecord`** — one entry of `get_toilet_records()`.

| Field | Type | Notes |
|---|---|---|
| `record_id` | `int` | |
| `record_type` | `RecordType` | `CAT_VISIT` / `CLEAN_CYCLE` / `OTHER`. |
| `cat_id` | `int` | `0` when no cat was matched. |
| `start_time` / `end_time` | `int` | Unix seconds. |
| `weight` / `unit` | `float`, `str` | For `CAT_VISIT`, the cat's measured weight. |
| `way` | `int` | Preserved from the wire; semantics not yet pinned down. |

Property: `duration_seconds: int`.

**`StatusUpdate`** — one push delivered by `watch_status()`.

| Field | Type | Notes |
|---|---|---|
| `device_name` | `str` | Same identifier the history endpoints accept. |
| `changes` | `dict[str, JsonValue]` | Only the fields that changed. Known keys are snake_case (matching `DeviceStatus`); unknown ones pass through under the original camelCase name with the raw value. |
| `received_at` | `float` | Client-side `time.time()` when the push arrived. |

**`StatusStream`** — returned by `watch_status()`. Register one handler
per event type; each is fire-and-forget (no return):

| Handler | Signature | Fires on |
|---|---|---|
| `on_silent_mode` / `on_child_lock` / `on_auto_level` / `on_young_cat_mode` / `on_cleaning_enabled` / `on_cat_present` / `on_needs_cleaning` / `on_bucket_full` | `(device_name: str, value: bool) -> None` | The corresponding `DeviceStatus` bool flipping. |
| `on_sand_percent` / `on_cat_stay_seconds` | `(device_name: str, value: int) -> None` | The corresponding int changing. |
| `on_last_sand_added` / `on_last_action` | `(device_name: str, value: str) -> None` | The string-typed property updating. |
| `on_operating_state` | `(device_name: str, value: OperatingState) -> None` | The box changes activity (idle / cleaning / restoring / leveling / cat_appears). |
| `on_unknown` | `(device_name: str, raw_key: str, raw_value: JsonValue) -> None` | A property the SDK doesn't yet model (raw passthrough). |
| `on_change` | `(update: StatusUpdate) -> None` | Every push, after the per-event handlers — catchall. |

Handlers run on the same asyncio loop as the rest of the SDK; keep
them non-blocking and offload heavy work via ``asyncio.create_task``.
Use the stream as ``async with client.watch_status() as stream:`` and
``await stream.run_forever()`` to block until cancellation.

**`DeviceStatus`** — return value of `get_status()`.

| Field | Type | Notes |
|---|---|---|
| `sand_percent` | `int` | Litter level, 0–100. |
| `cat_present` | `bool` | A cat is currently in the box. |
| `cat_stay_seconds` | `int` | How long the cat has been there. |
| `needs_cleaning` | `bool` | Device flagged a pending clean. |
| `bucket_full` | `bool` | Waste bin needs emptying. |
| `operating_state` | `OperatingState` | Activity: idle / cleaning / restoring / leveling / cat_appears (cat inside). |
| `last_sand_added` | `str` | Server-formatted `"YYYY-MM-DD HH:MM:SS"`. |
| `last_action` | `str` | Device-reported description of its last action. |
| `cleaning_enabled` / `auto_level` / `silent_mode` / `child_lock` / `young_cat_mode` | `bool` | Mode switches. |
| `wifi_name` / `ip_address` / `mac_address` | `str` | Network diagnostics. |
| `wifi_rssi` | `int` | Signal strength in dBm (negative). |
| `firmware_version` / `hardware_version` | `str` | Reported by the device. |
| `updated_at` | `int` | Snapshot timestamp (epoch ms). |

`get_status()` does not cache — every call hits the device gateway.
"Last cleaned at" is not on this readback; query `get_toilet_records()`
and filter by `record_type == RecordType.CLEAN_CYCLE`.

**`DailyStatistics`** — one entry of `get_toilet_statistics()`.

| Field | Type | |
|---|---|---|
| `date` | `str` | `YYYY-MM-DD`. |
| `num` | `int` | Visits in the bucket. |
| `weight` / `unit` | `float`, `str` | |
| `toilet_total_second` | `int` | Total occupied seconds. |
| `weight_avg` | `float` | Average cat weight. |

**`LoginResult`** — the session blob.

Treat it as opaque; persist via `to_dict()`/`from_dict()` and pass to
`client.login(cached=...)` on the next run.

| Method | Signature | |
|---|---|---|
| `to_dict` | `() -> dict[str, JsonValue]` | JSON-safe snapshot. |
| `from_dict` | `(data: dict) -> LoginResult` | Classmethod; restore. |
| `age_seconds` | `(now: float \| None = None) -> float` | Seconds since `issued_at`. |

Exposes `user_info: UserInfo` for diagnostics (`user_id`, `user_name`,
`ali_user_id`). Other fields are session-internal.

**`Region`** — enum with `US` (default), `EU`, `AP`. Mainland China
is out of scope.

**`DeviceRole`** — `IntEnum`: `OWNER = 1`, `SHARED = 2`. The numeric
values match the server's per-call role filter so the SDK can pass
them through without conversion.

**`CatGender`** — `IntEnum`: `UNKNOWN = 0`, `MALE = 1`, `FEMALE = 2`.

**`RecordType`** — `IntEnum`: `CAT_VISIT = 1`, `CLEAN_CYCLE = 2`, `OTHER = 3`.

### Exceptions

```
NeakasaError
├── ApiError                    (non-zero envelope code)
│   └── AuthenticationError
│       ├── SessionExpiredError      (codes 1007 / 3026 / 3027)
│       └── InvalidCredentialsError  (codes 10060 / 10061 / 10192)
└── TransportError              (HTTP / network failure)
```

Catch the narrowest class that fits;  `AuthenticationError` is the
catch-all for "auth went wrong".

## Caching the session

The server does not advertise an expiry; the official app uses the
token until an auth-failure code comes back, then re-logs in. The SDK
exposes the issue timestamp so consumers can persist `LoginResult` and
reuse it across runs:

```python
import asyncio, json
from pathlib import Path
from neakasa_litterbox_sdk import LoginResult, NeakasaClient


async def run() -> None:
    cache = Path(".neakasa-session.json")
    stored = LoginResult.from_dict(json.loads(cache.read_text())) if cache.exists() else None

    async with NeakasaClient(email="…", password="…") as client:
        result = await client.login(cached=stored)
        if result is not stored:
            cache.write_text(json.dumps(result.to_dict()))


asyncio.run(run())
```

`result is not cached` cleanly distinguishes "minted something" from
"nothing changed". The SDK does **not** recheck staleness — the caller
decides their TTL policy and skips `cached=` whenever they want a
refresh.

## Handling token expiry

The SDK does not refresh the session automatically. On
`SessionExpiredError` the caller should:

1. Call `client.login()` (no `cached=`) for a fresh `LoginResult`.
2. Persist that result.
3. Retry the original call.

```python
from neakasa_litterbox_sdk import SessionExpiredError


async def call_and_persist(client, cache):
    try:
        return await client.list_devices()
    except SessionExpiredError:
        result = await client.login()
        cache.write_text(json.dumps(result.to_dict()))
        return await client.list_devices()
```

`InvalidCredentialsError` and bare `AuthenticationError` propagate
without retry — they signal a hard failure (wrong password, account
locked, …) that re-login cannot fix.

## Contributing

Read [`CODE_STYLE.md`](./CODE_STYLE.md) before adding or restructuring
code — it's the single source of truth for layout, naming, typing,
logging, error messages, and commit conventions. The high-level
pointer for agents lives in [`CLAUDE.md`](./CLAUDE.md).

## Architecture

The SDK speaks to two backends under the hood (the Neakasa REST cloud
and an Aliyun IoT API Gateway used for device-list and command paths),
but consumers only see the high-level surface above — `login()`
handles the multi-step bootstrap and `LoginResult` carries whatever
credentials need to round-trip.

## License

[MIT](./LICENSE).
