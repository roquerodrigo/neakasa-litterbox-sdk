"""Lock the per-region cluster URLs against regression.

The EU host is ``euapi.neakasa.com``: the bare ``eu.neakasa.com`` subdomain
serves the Shopify storefront and returns HTTP 404 on ``/api/login`` (see
issue ha-neakasa-litterbox#32).
"""

from __future__ import annotations

import pytest

from neakasa_litterbox_sdk import Region


@pytest.mark.parametrize(
    ("region", "web_url"),
    [
        (Region.US, "https://us.neakasa.com/api"),
        (Region.EU, "https://euapi.neakasa.com/api"),
        (Region.AP, "https://ap.neakasa.com/api"),
    ],
)
def test_region_web_url(region: Region, web_url: str) -> None:
    assert region.web_url == web_url
    assert region.value == web_url


def test_region_login_url_appends_login() -> None:
    assert Region.EU.login_url == "https://euapi.neakasa.com/api/login"
    assert Region.US.login_url == "https://us.neakasa.com/api/login"
    assert Region.AP.login_url == "https://ap.neakasa.com/api/login"


def test_eu_host_is_not_the_storefront_subdomain() -> None:
    # eu.neakasa.com is the Shopify store (HTTP 404 on the API path).
    assert "eu.neakasa.com" not in Region.EU.value
