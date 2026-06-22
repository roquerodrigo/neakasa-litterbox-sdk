"""Cloud region selection for the Neakasa REST API."""

from __future__ import annotations

from enum import Enum


class Region(Enum):
    """Global Neakasa cloud cluster. Each region is a distinct backend.

    Every country code maps to one of three clusters — verified against the
    live servers. Note the EU API host is ``euapi.neakasa.com``, not
    ``eu.neakasa.com``: the bare ``eu`` subdomain serves the Shopify
    storefront (returns HTTP 404 on ``/api/login``). The Chinese mainland
    cluster (``region.neabot.com.cn``) is intentionally not exposed.
    """

    US = "https://us.neakasa.com/api"
    EU = "https://euapi.neakasa.com/api"
    AP = "https://ap.neakasa.com/api"

    @property
    def web_url(self) -> str:
        """Base URL the official app stores as ``regionBaseURL.web``."""
        return self.value

    @property
    def login_url(self) -> str:
        """Fully-qualified login endpoint URL."""
        return f"{self.value}/login"
