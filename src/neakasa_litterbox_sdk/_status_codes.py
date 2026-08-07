"""Status codes both backends answer with, named once for every caller."""

from __future__ import annotations

ENVELOPE_SUCCESS_CODE: int = 200
"""``code`` a JHResult / Aliyun envelope carries when the call succeeded."""

HTTP_ERROR_STATUS: int = 400
"""First HTTP status the transports treat as a failed request."""
