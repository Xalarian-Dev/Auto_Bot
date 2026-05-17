"""
SerpAPI — Google Jobs engine.
Covers LinkedIn, Indeed, Glassdoor and more through a single stable API.
Docs: https://serpapi.com/google-jobs-api
"""

from __future__ import annotations

import logging
import os
from typing import Any

from scout.models import JobListing, Region
from scout.sources.base import BaseSource, infer_region
from scout.sources.utils import parse_posted_at

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search.json"


class SerpAPISource(BaseSource):
    """
    Queries Google Jobs via SerpAPI for each (query, location) pair
    defined in config.
    """

    name = "serpapi"

    def fetch(self) -> list[JobListing]:
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            raise ValueError("SERPAPI_KEY not set in environment")

        queries: list[dict] = self.config.get("serpapi_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=30) as client:
            for query_cfg in queries:
                query = query_cfg["q"]
                location = query_cfg.get("location", "")
                region = Region(query_cfg.get("region", Region.OTHER.value))
                country = query_cfg.get("country", "")

                start = 0
                while True:
                    params = {
                        "engine": "google_jobs",
                        "q": query,
                        "api_key": api_key,
                        "hl": "en",
                        "num": 10,
                        "start": start,
                    }
                    if location:
                        params["location"] = location
                    gl = query_cfg.get("gl", "")
                    if gl:
                        params["gl"] = gl

                    try:
                        resp = self._get(client, SERPAPI_BASE, params=params)
                        data = resp.json()
                    except Exception as exc:
                        logger.warning(f"[serpapi] query '{query}' @ '{location}' failed: {exc}")
                        break

                    jobs = data.get("jobs_results", [])
                    if not jobs:
                        break

                    for job in jobs:
                        url = self._extract_url(job)
                        fingerprint_key = f"{job.get('title','')}|{job.get('company_name','')}|{location}"
                        if fingerprint_key in seen:
                            continue
                        seen.add(fingerprint_key)

                        listing = JobListing(
                            title=job.get("title", ""),
                            company=job.get("company_name", ""),
                            location=job.get("location", location),
                            country=country,
                            region=infer_region(country, job.get("location", location)),
                            url=url,
                            description=self._extract_description(job),
                            salary_raw=self._extract_salary(job),
                            date_posted=parse_posted_at(job.get("detected_extensions", {}).get("posted_at")),
                            source=self.name,
                        )
                        results.append(listing)

                    # SerpAPI paginates in steps of 10; stop after 3 pages (30 results) per query
                    start += 10
                    if start >= 30 or len(jobs) < 10:
                        break

        return results

    # ------------------------------------------------------------------

    def _extract_url(self, job: dict) -> str:
        # Prefer a direct apply link
        for link in job.get("apply_options", []):
            if link.get("link"):
                return link["link"]
        return job.get("share_link", "")

    def _extract_description(self, job: dict) -> str:
        highlights = job.get("job_highlights", [])
        parts = []
        for section in highlights:
            title = section.get("title", "")
            items = section.get("items", [])
            if items:
                parts.append(f"{title}:\n" + "\n".join(f"- {i}" for i in items))
        return "\n\n".join(parts) or job.get("description", "")

    def _extract_salary(self, job: dict) -> str:
        ext = job.get("detected_extensions", {})
        return ext.get("salary", "")
