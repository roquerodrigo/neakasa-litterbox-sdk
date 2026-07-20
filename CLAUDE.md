# neakasa-litterbox-sdk

Python SDK for the **Neakasa M1** self-cleaning cat litter box. The Neakasa REST cloud uses an HMAC-SHA256 + AES-CBC handshake; the device backplane is Aliyun IoT. Goal: programmatic automation (Home Assistant, scripts) without depending on the official app.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read
[`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for
conventions: language, file organisation, naming, typing, imports,
docstrings, comments, logging, error messages, public API surface,
conventional commits, packaging, testing, lint workflow.

## Verification workflow

After every code change, always run lint then tests, in that order, before
declaring the task done:

```bash
uv run ruff format . && uv run ruff check . --fix && uv run mypy src
uv run pytest
```

Both gates mirror CI. Skip this only when the change literally cannot
affect lint or tests (e.g., README-only edits).

## Downstream consumer

This package is published to PyPI and consumed by the `ha-neakasa-litterbox`
Home Assistant integration (sibling repo), which pins an **exact** version
(`neakasa-litterbox-sdk==X.Y.Z`) in both its `pyproject.toml` and
`custom_components/neakasa_litterbox/manifest.json`. A new release here does
not reach the integration until that pin is bumped there.
