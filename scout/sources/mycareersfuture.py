"""
MyCareersFuture.gov.sg — Singapore government job portal.
Has a public REST API, no auth required. Strong source for expat-friendly roles.
"""

from __future__ import annotations

import logging
from datetime import datetime

from scout.models import JobListing, Region
from scout.sources.base import BaseSource

logger = logging.getLogger(__name__)

MCF_API = "https://api.mycareersfuture.gov.sg/v2/jobs"


class MyCareersFutureSource(BaseSource):
    name = "mycareersfuture"

    def fetch(self) -> list[JobListing]:
        queries: list[dict] = self.config.get("mcf_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Referer": "https://www.mycareersfuture.gov.sg/",
                "Accept": "application/json",
            })

            for query_cfg in queries:
                search = query_cfg["search"]
                max_pages = query_cfg.get("max_pages", 3)

                for page in range(max_pages):
                    params = {
                        "search": search,
                        "sortBy": "new_posting_date",
                        "pageSize": 20,
                        "page": page,
                    }

                    try:
                        resp = self._get(client, MCF_API, params=params)
                        data = resp.json()
                    except Exception as exc:
                        logger.warning(f"[mcf] '{search}' page {page} failed: {exc}")
                        break

                    jobs = data.get("results", [])
                    if not jobs:
                        break

                    for job in jobs:
                        uuid = job.get("uuid", "")
                        if uuid in seen:
                            continue
                        seen.add(uuid)

                        # Extract nested data
                        position = job.get("position", {})
                        company = job.get("postedCompany", {})
                        salary = job.get("salary", {})

                        title = position.get("title", job.get("title", ""))
                        company_name = company.get("name", "")
                        location_raw = job.get("address", {})
                        location_str = ", ".join(filter(None, [
                            location_raw.get("block", ""),
                            location_raw.get("streetName", ""),
                            location_raw.get("postalCode", ""),
                            "Singapore",
                        ]))

                        salary_min = salary.get("minimum")
                        salary_max = salary.get("maximum")
                        salary_raw = ""
                        if salary_min and salary_max:
                            salary_raw = f"SGD {salary_min:,} - {salary_max:,}"
                        elif salary_min:
                            salary_raw = f"SGD {salary_min:,}+"

                        listing = JobListing(
                            title=title,
                            company=company_name,
                            location=location_str or "Singapore",
                            country="Singapore",
                            region=Region.APAC,
                            url=f"https://www.mycareersfuture.gov.sg/job/{uuid}",
                            description=job.get("description", ""),
                            salary_raw=salary_raw,
                            date_posted=self._parse_date(job.get("metadata", {}).get("createdAt")),
                            source=self.name,
                        )
                        results.append(listing)

                    if len(jobs) < 20:
                        break

        return results

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
