"""Build the Aliyun JSON-RPC envelope every IoT request is wrapped in.

Envelope shape (used by ``/uc/listBindingByAccount`` and the other
Aliyun IoT POSTs)::

    {
      "a":       "<request-uuid>",
      "b":       "1.0",
      "c":       {"apiVer": "1.0.8", "language": "en-US", "iotToken": "<32-hex>"},
      "d":       {<endpoint-specific payload>},
      "id":      "<same-uuid-as-a>",
      "params":  {"$ref": "$.d"},
      "request": {"$ref": "$.c"},
      "version": "1.0"
    }

The ``$ref`` fields are JSON-pointers — Aliyun's deserializer rewrites
them to the resolved objects, so we just keep them as literals.

``iot_token`` is optional because the bootstrap call (``region/get``) runs
*before* a session exists.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from .._credentials import USER_AGENT

if TYPE_CHECKING:
    from ..utils._json import JsonValue

_REF_C: dict[str, str] = {"$ref": "$.c"}
_REF_D: dict[str, str] = {"$ref": "$.d"}


def build_envelope(
    payload: dict[str, JsonValue],
    *,
    api_version: str,
    iot_token: str | None = None,
    language: str = "en-US",
    request_id: str | None = None,
) -> tuple[str, bytes]:
    """Return ``(request_id, body)`` for an Aliyun IoT POST.

    ``payload`` is what goes under ``d`` — endpoint-specific arguments.
    ``api_version`` is the per-endpoint ``apiVer`` (e.g. ``"1.0.8"`` for
    ``/uc/listBindingByAccount``).
    """
    request_id_value = request_id if request_id is not None else str(uuid.uuid4())
    common: dict[str, JsonValue] = {"apiVer": api_version, "language": language}
    if iot_token is not None:
        common["iotToken"] = iot_token
    envelope: dict[str, JsonValue] = {
        "a": request_id_value,
        "b": "1.0",
        "c": common,
        "d": payload,
        "id": request_id_value,
        "params": _REF_D,
        "request": _REF_C,
        "version": "1.0",
    }
    body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    return request_id_value, body


__all__ = ["USER_AGENT", "build_envelope"]
