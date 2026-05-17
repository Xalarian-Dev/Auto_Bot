"""
USAJobs.gov -- official US federal government job portal.
Free API, requires registration at https://developer.usajobs.gov/
Particularly relevant for IT Program Director roles in US government/public sector.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from scout.models import JobListing, Region
from scout.sources.base import BaseSource

logger = logging.getLogger(__name__)

USAJOBS_API = "https://data.usajobs.gov/api/search"


class USAJobsSource(BaseSource):
    name = "usajobs"

    def fetch(self) -> list[JobListing]:
        api_key = os.getenv("USAJOBS_KEY")
        user_agent = os.getenv("USAJOBS_EMAIL")
        if not api_key or not user_agent:
            logger.warning("[usajobs] USAJOBS_KEY or USAJOBS_EMAIL not set -- skipping.")
            return []

        queries: list[dict] = self.config.get("usajobs_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Host": "data.usajobs.gov",
                "User-Agent": user_agent,
                "Authorization-Key": api_key,
            })

            for query_cfg in queries:
                params = {
                    "Keyword": query_cfg["keyword"],
                    "ResultsPerPage": query_cfg.get("results_per_page", 25),
                    "SortField": "OpenDate",
                    "SortDirection": "Desc",
                }
                if query_cfg.get("location"):
                    params["LocationName"] = query_cfg["location"]

                try:
                    resp = self._get(client, USAJOBS_API, params=params)
                    data = resp.json()
                except Exception as exc:
                    logger.warning(f"[usajobs] '{query_cfg['keyword']}' failed: {exc}")
                    continue

                items = (
                    data.get("SearchResult", {})
                    .get("SearchResultItems", [])
                )

                for item in items:
                    mv = item.get("MatchedObjectDescriptor", {})
                    job_id = item.get("MatchedObjectId", "")

                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    # Location -- take first listed
                    locations = mv.get("PositionLocation", [])
                    location_str = locations[0].get("LocationName", "") if locations else ""
                    country = locations[0].get("CountrySubDivisionCode", "USA") if locations else "USA"

                    # Salary
                    remun = mv.get("PositionRemuneration", [{}])[0]
                    sal_min = remun.get("MinimumRange", "")
                    sal_max = remun.get("MaximumRange", "")
                    sal_freq = remun.get("RateIntervalCode", "")
                    salary_raw = f"USD {sal_min} - {sal_max} {sal_freq}".strip() if sal_min else ""

                    listing = JobListing(
                        title=mv.get("PositionTitle", ""),
                        company=mv.get("OrganizationName", ""),
                        location=location_str,
                        country="United States",
                        region=Region.NORTH_AMERICA,
                        url=mv.get("PositionURI", ""),
                        description=mv.get("UserArea", {})
                            .get("Details", {})
                            .get("JobSummary", ""),
                        salary_raw=salary_raw,
                        date_posted=self._parse_date(mv.get("PublicationStartDate")),
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
