"""
Indeed EU — via SerpAPI's Indeed engine.
Used for Mode C (Northern Europe + Paris) where Google Jobs has no coverage.
Docs: https://serpapi.com/indeed-search-api
"""

from __future__ import annotations

import logging
import os
from scout.models import JobListing, Region
from scout.sources.base import BaseSource, infer_region
from scout.sources.utils import parse_posted_at

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search.json"


class IndeedSource(BaseSource):
    """Queries Indeed regional sites via SerpAPI for European roles (Mode C)."""

    name = "indeed"

    def fetch(self) -> list[JobListing]:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            raise ValueError("SERPAPI_KEY not set in environment")

        queries: list[dict] = self.config.get("indeed_queries", [])
        if not queries:
            return []

        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=30) as client:
            for query_cfg in queries:
                q = query_cfg["q"]
                location = query_cfg.get("location", "")
                country = query_cfg.get("country", "")
                domain = query_cfg.get("domain", "indeed.com")
                region_val = query_cfg.get("region", Region.OTHER.value)

                params = {
                    "engine": "indeed",
                    "q": q,
                    "l": location,
                    "api_key": api_key,
                    "domain": domain,
                    "num": 15,
                }

                try:
                    resp = self._get(client, SERPAPI_BASE, params=params)
                    data = resp.json()
                except Exception as exc:
                    logger.warning(f"[indeed] '{q}' @ '{location}' failed: {exc}")
                    continue

                jobs = data.get("jobs_results", [])
                for job in jobs:
                    job_id = job.get("job_id", "")
                    key = f"{domain}|{job_id}"
                    if key in seen:
                        continue
                    seen.add(key)

                    listing = JobListing(
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("location", location),
                        country=country,
                        region=infer_region(country, job.get("location", location)),
                        url=job.get("link", ""),
                        description=job.get("description", ""),
                        salary_raw=job.get("salary", ""),
                        date_posted=parse_posted_at(job.get("date")),
                        source=self.name,
                    )
                    results.append(listing)

        return results
