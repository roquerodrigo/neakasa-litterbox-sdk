"""SDK-level credentials.

Identical for every install — they identify the SDK to both the Neakasa
REST cloud (HMAC-SHA256 signing in ``auth/signing.py``) and the Aliyun
IoT API Gateway (HMAC-SHA1 signing in ``aliyun/signing.py``). The values
live in this single private module so both signers stay in sync.

These are not personal secrets, but treat them like other hardcoded API
keys: don't log them, don't expose them in error messages.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def _sdk_version() -> str:
    try:
        return version("neakasa-litterbox-sdk")
    except PackageNotFoundError:
        return "0.0.0"


APP_KEY = "32715650"
APP_SECRET = "698ee0ef531c3df2ddded87563643860"
USER_AGENT = f"neakasa-litterbox-sdk/{_sdk_version()}"
