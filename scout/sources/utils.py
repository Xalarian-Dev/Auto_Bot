"""
Shared utilities for job sources.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import httpx


_AGO_MAP = {
    "hour": timedelta(hours=1),
    "hours": timedelta(hours=1),
    "day": timedelta(days=1),
    "days": timedelta(days=1),
    "week": timedelta(weeks=1),
    "weeks": timedelta(weeks=1),
    "month": timedelta(days=30),
    "months": timedelta(days=30),
}


def parse_posted_at(text: str | None) -> datetime | None:
    """Parse SerpAPI 'posted_at' strings like '3 days ago' into a datetime."""
    if not text:
        return None
    text = text.lower()
    for unit, delta in _AGO_MAP.items():
        if unit in text:
            try:
                number = int("".join(filter(str.isdigit, text)) or "1")
                return datetime.now() - delta * number
            except ValueError:
                return None
    return None


def describe_error(exc: Exception) -> str:
    """Short, safe description of a request error, for logs.

    The text of an httpx error contains the full URL of the request, and SerpAPI
    receives its key in that URL (``api_key=...``). Never log ``str(exc)`` as is:
    for an HTTP error, keep only the status code and reason; otherwise, mask any
    ``api_key`` value left in the message.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code} {exc.response.reason_phrase}".strip()
    text = re.sub(r"(api_key=)[^&\s'\"]+", r"\1***", str(exc))
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__
