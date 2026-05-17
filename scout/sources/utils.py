"""
Shared utilities for job sources.
"""

from __future__ import annotations

from datetime import datetime, timedelta


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
