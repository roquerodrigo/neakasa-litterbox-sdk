"""Cloud region selection for the Neakasa REST API."""

from __future__ import annotations

from enum import Enum


class Region(Enum):
    """Global Neakasa cloud cluster. Each region is a distinct backend.

    The bootstrap service (``/global/baseurl/country``) maps every country
    code to one of three clusters — verified against the live server. The
    Chinese mainland cluster (``region.neabot.com.cn``) is intentionally not
    exposed.
    """

    US = "https://us.neakasa.com/api"
    EU = "https://eu.neakasa.com/api"
    AP = "https://ap.neakasa.com/api"

    @property
    def web_url(self) -> str:
        """Base URL the official app stores as ``regionBaseURL.web``."""
        return self.value

    @property
    def login_url(self) -> str:
        """Fully-qualified login endpoint URL."""
        return f"{self.value}/login"
