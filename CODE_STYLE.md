# Code Style Guide

Style conventions for the `neakasa-litterbox-sdk` Python SDK. Run
`uv run ruff format . && uv run ruff check . --fix && uv run mypy src` before
committing — all three must exit cleanly. `uv run pytest` follows.

**Always read this file before adding or restructuring code.**

## Language

- Code is written in **English**: file names, class names, function names,
  variable names, dictionary keys, identifier strings.
- The conversation language with the user can be Portuguese or anything else;
  what is committed to disk stays English.

## File organization

- **Source layout is `src/neakasa_litterbox_sdk/`.** Tests in `tests/`, packaging in
  `pyproject.toml`. Hatchling is the build backend.
- **One top-level class per file.** Multiple semantically related classes get
  grouped into a package directory with one class per submodule and an
  `__init__.py` re-exporting the public symbols.
  - Example: `auth/` contains `signing.py`, `transport.py`, plus
    `__init__.py`.
  - Example: `models/` contains `login_result.py`, `region.py`, `user_info.py`,
    plus `__init__.py`.
  - Example: `exceptions/` contains `api.py`, `auth.py`, `base.py`,
    `credentials.py`, `session.py`, `transport.py`, plus `__init__.py`.
  - Example: `crypto/` contains `aes.py`, `digest.py`, plus `__init__.py`.
- **Public surface goes through the package `__init__.py`.** Anything not
  re-exported there is internal — prefix with `_` if intended to stay private.
- **TypedDicts and `type` aliases do not count as "classes"** for this rule —
  they live alongside related code.
- **Helper functions** may live in the same file as the single class that
  uses them. Module-level private helpers are prefixed `_` (e.g.
  `_unwrap_envelope` in `client.py`).

## Naming

- Public classes are `CapWords`: `NeakasaClient`, `LoginResult`, `UserInfo`,
  `Region`.
- Exception classes end with `Error`: `NeakasaError`, `ApiError`,
  `AuthenticationError`, `TransportError`.
- Module names are `snake_case`. Subpackages are organized by concern
  (`auth`, `crypto`, `exceptions`, `models`, `utils`).
- Private attributes / functions are prefixed with `_`.

## Typing

**Strict typing. No `Any`, no bare collection generics.** Mypy enforces this.

Banned: `typing.Any`, `object` as a value type, bare `dict` / `list` /
`tuple` / `set`, `dict[str, Any]`.

Required:

- `@dataclass(frozen=True, slots=True)` for structured records
  (`LoginResult`, `UserInfo`, …).
- `enum.Enum` subclasses for fixed sets of values (`Region`).
- Named `TypeAlias`es for shared shapes (`JsonObject`, `JsonValue`).
- Always type return values explicitly. Never rely on type inference for
  public APIs.
- Type-hinted module-level loggers:
  `log: logging.Logger = logging.getLogger(...)`.

The SDK ships a `py.typed` marker so downstream consumers get type info.

## Imports

- Always start every module with `from __future__ import annotations` so type
  hints become lazy strings.
- Same-package relative imports (`from .module import …`) are the default.
- Move type-only imports into a `TYPE_CHECKING` block:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Mapping
      from .models import LoginResult
  ```

- `noqa` comments require a written justification inline. Never silence to
  "make ruff happy" — fix the underlying code.

## Docstrings

- Every public class, function, method (including `@property`) has a docstring.
- A single sentence is usually enough. Describe the *contract* or the *why*,
  not the obvious implementation.
- Module-level docstring at the top of every `.py` file.
- Avoid restating the type — the signature already does that.

## Comments

- Default to **no comments**. Add one only when the *why* is not obvious from
  the code: a hidden constraint, a workaround, a subtle invariant, a protocol
  reference (e.g. "AES/CBC/NoPadding — the app pads manually with NUL bytes").
- Never describe *what* the code does — well-named identifiers handle that.
- **No section dividers** like `# --- Auth helpers ---` to group related
  declarations. If a file has so many sections that you feel the need for
  visual separators, split it into multiple files instead.

## Logging

- Module-level logger:
  `log: logging.Logger = logging.getLogger("neakasa_litterbox_sdk.<area>")` (e.g.
  `"neakasa_litterbox_sdk.client"`, `"neakasa_litterbox_sdk.transport"`). Don't use `__name__`
  directly — the explicit dotted name lets users scope log levels precisely.
- Use **lazy `%`-formatting**, never f-strings:

  ```python
  log.debug("Login response: token=%s", token[:8] + "…")  # ✓ truncated secret
  log.debug(f"Login response: token={token}")             # ✗ leaks full token
  ```

- Levels:
  - `debug` — request/response counts, handshake steps, truncated bodies.
  - `info` — successful login, region selection.
  - `warning` — recoverable failures (single retry, fallback path).
  - `error` / `exception` — unrecoverable. `exception` inside `except` blocks
    captures the traceback.
- Never log raw `password`, the decrypted `userToken` / `aesKey` / `aesIv`,
  or the unredacted `aliAuthenticationToken`. The encrypted `loginToken`
  on the wire is fine (decryption requires the boot key embedded in the SDK).

## Error messages

- Format: `"Failed to <verb> <object>: <cause>"`. Keep them short and
  grep-able.
- Custom exceptions form a hierarchy: `NeakasaError` is the root. `ApiError`
  (non-zero `code` in the JHResult envelope), `AuthenticationError` (login /
  token failure, subclass of `ApiError`) with the narrower
  `SessionExpiredError` and `InvalidCredentialsError`, and `TransportError`
  (HTTP / network failure). Wrap raw `OSError` / `aiohttp` / `aiomqtt`
  errors at the transport boundary so callers only catch this hierarchy.
- Pre-validate inputs before opening a socket so user-facing errors point at
  the bad input, not a downstream traceback.

## Public API surface

- Anything imported in the package `__init__.py` is the public contract:
  `NeakasaClient`, `StatusStream`, the models (`LoginResult`, `UserInfo`,
  `Device`, `DeviceRole`, `DeviceStatus`, `StatusUpdate`, `OperatingState`,
  `Cat`, `CatGender`, `ToiletRecord`, `RecordType`, `DailyStatistics`,
  `Region`) and the exception hierarchy (`NeakasaError`, `ApiError`,
  `AuthenticationError`, `SessionExpiredError`, `InvalidCredentialsError`,
  `TransportError`). Renaming or removing those symbols is a
  `BREAKING CHANGE:`.
- Internal modules can change shape freely as long as the public re-exports
  keep working.

## Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/),
in **English**:

| Type | Meaning | Bump |
|---|---|---|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `perf` | Performance improvement | patch |
| `deps` | Dependency bump | patch |
| `docs` | Documentation only | none |
| `refactor` | Refactor without behavior change | none |
| `test` | Test-only change | none |
| `ci` | CI / tooling change | none |
| `chore` | Anything else (rarely) | none |

- Subject line: imperative mood, lowercase, no trailing period.
- Use scopes when useful: `feat(auth): add Aliyun IoT session refresh`.
- A `BREAKING CHANGE:` footer (or `!` after type) bumps the major version.

## Packaging

- Build backend: `hatchling`. Wheel and sdist contain `src/neakasa_litterbox_sdk`.
- `requires-python = ">=3.11"`. Don't bump this without a `BREAKING CHANGE:`
  footer.
- Public dependencies: keep them minimal and use `>=` lower bounds, not pins.
  Currently `aiohttp>=3.13.5`, `aiomqtt>=2.5.1`, and `cryptography>=44.0`
  (AES-CBC).
- The `[dependency-groups] dev` group carries test-only deps;
  `[dependency-groups] lint` carries ruff + mypy.
- A `py.typed` marker ships in the wheel so consumers see type info.

## Testing

- Tests live in `tests/`. `uv run pytest` runs the suite. Aim for high
  coverage on auth/crypto/transport layers since they're the byte-level
  surface most likely to regress silently.
- The suite is fully offline — transports are mocked at the boundary and
  unit tests use byte-level fixtures. Live exercising against the Neakasa
  cloud happens through the scripts in `examples/`, which read real
  credentials from `.env` (never committed).

## Linting and verification

- Ruff configuration in `pyproject.toml` under `[tool.ruff]`.
- Mypy configuration in `pyproject.toml` under `[tool.mypy]` (strict).
- After every change run the three-step lint pipeline + `pytest`. Both
  gates mirror CI:

  ```bash
  uv run ruff format . && uv run ruff check . --fix && uv run mypy src
  uv run pytest
  ```
