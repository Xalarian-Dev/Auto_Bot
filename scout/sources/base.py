"""
Abstract base class for all job sources.
Each source must implement fetch() and return a list of JobListing objects.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from scout.models import JobListing, Region

logger = logging.getLogger(__name__)


# Region mapping by country
COUNTRY_REGION: dict[str, Region] = {
    # APAC
    "australia": Region.APAC,
    "new zealand": Region.APAC,
    "singapore": Region.APAC,
    "hong kong": Region.APAC,
    "japan": Region.APAC,
    "south korea": Region.APAC,
    "korea": Region.APAC,
    "malaysia": Region.APAC,
    "philippines": Region.APAC,
    "indonesia": Region.APAC,
    "vietnam": Region.APAC,
    "ho chi minh": Region.APAC,
    "thailand": Region.APAC,
    "bangkok": Region.APAC,
    "china": Region.APAC,
    "taiwan": Region.APAC,
    # North America
    "united states": Region.NORTH_AMERICA,
    "usa": Region.NORTH_AMERICA,
    "us": Region.NORTH_AMERICA,
    "canada": Region.NORTH_AMERICA,
}


# Codes courts : à chercher comme mots entiers seulement, sinon « us » est trouvé dans
# « Vienna, Austria » ou « Cyprus ».
_WHOLE_WORD_KEYS = {"us", "usa"}


def infer_region(country: str, location: str) -> Region:
    text = (country + " " + location).lower()
    for key, region in COUNTRY_REGION.items():
        if key in _WHOLE_WORD_KEYS:
            if re.search(rf"\b{re.escape(key)}\b", text):
                return region
        elif key in text:
            return region
    return Region.OTHER


class BaseSource(ABC):
    """All job sources inherit from this."""

    name: str = "base"

    # Default HTTP headers to look like a real browser
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/html, */*",
    }

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def fetch(self) -> list[JobListing]:
        """Fetch and return job listings from this source."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_client(self, timeout: int = 20) -> httpx.Client:
        return httpx.Client(
            headers=self.DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    def _get(self, client: httpx.Client, url: str, **kwargs) -> httpx.Response:
        logger.debug(f"[{self.name}] GET {url}")
        response = client.get(url, **kwargs)
        response.raise_for_status()
        return response

    def _safe_fetch(self) -> list[JobListing]:
        """Wraps fetch() with top-level error handling so one broken source never kills the run."""
        try:
            results = self.fetch()
            logger.info(f"[{self.name}] fetched {len(results)} listings")
            return results
        except Exception as exc:
            logger.error(f"[{self.name}] failed: {exc}")
            return []
