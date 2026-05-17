"""
Greenhouse ATS — public job board API, no auth required.
Query specific company board tokens to fetch their open roles.
Covers tech companies and global firms using Greenhouse as their ATS.
"""

from __future__ import annotations

import logging
from datetime import datetime

from scout.models import JobListing
from scout.sources.base import BaseSource, infer_region

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseSource(BaseSource):
    name = "greenhouse"

    def fetch(self) -> list[JobListing]:
        companies: list[dict] = self.config.get("greenhouse_companies", [])
        title_filters: list[str] = self.config.get("greenhouse_title_filters", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({"Accept": "application/json"})

            for company_cfg in companies:
                token = company_cfg["token"]
                company_name = company_cfg.get("name", token)
                url = GREENHOUSE_API.format(token=token)

                try:
                    resp = self._get(client, url)
                    data = resp.json()
                except Exception as exc:
                    logger.warning(f"[greenhouse] '{token}' failed: {exc}")
                    continue

                jobs = data.get("jobs", [])
                for job in jobs:
                    job_id = str(job.get("id", ""))
                    if not job_id or job_id in seen:
                        continue

                    title = job.get("title", "").strip()
                    if not title:
                        continue

                    # Filter by title keywords if configured
                    if title_filters:
                        title_lower = title.lower()
                        if not any(f.lower() in title_lower for f in title_filters):
                            continue

                    seen.add(job_id)

                    location_obj = job.get("location", {})
                    location_str = location_obj.get("name", "") if isinstance(location_obj, dict) else ""

                    country = location_str.split(",")[-1].strip() if "," in location_str else location_str
                    region = infer_region(country, location_str)

                    listing = JobListing(
                        title=title,
                        company=company_name,
                        location=location_str,
                        country=country,
                        region=region,
                        url=job.get("absolute_url", ""),
                        description="",
                        salary_raw="",
                        date_posted=self._parse_date(job.get("first_published")),
                        source=self.name,
                    )
                    results.append(listing)

        return results

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
