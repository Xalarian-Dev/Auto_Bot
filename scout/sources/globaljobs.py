"""
GlobalJobs.org — international, NGO, government, and development jobs.
Server-rendered HTML, no auth required.
Good source for IT Program Manager/Director roles at large NGOs and international orgs.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone  # noqa: F401

from bs4 import BeautifulSoup

from scout.models import JobListing
from scout.sources.base import BaseSource, infer_region

logger = logging.getLogger(__name__)

BASE_URL = "https://www.globaljobs.org/jobs"


class GlobalJobsSource(BaseSource):
    name = "globaljobs"

    def fetch(self) -> list[JobListing]:
        queries: list[dict] = self.config.get("globaljobs_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Referer": "https://www.globaljobs.org/",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })

            for query_cfg in queries:
                keyword = query_cfg.get("keyword", "")
                region = query_cfg.get("region", "")
                max_pages = query_cfg.get("max_pages", 3)

                for page in range(1, max_pages + 1):
                    params: dict = {}
                    if keyword:
                        params["q"] = keyword
                    if region:
                        params["region"] = region
                    if page > 1:
                        params["page"] = page

                    try:
                        resp = self._get(client, BASE_URL, params=params)
                        html = resp.text
                    except Exception as exc:
                        logger.warning(f"[globaljobs] '{keyword}' page {page} failed: {exc}")
                        break

                    listings, has_more = self._parse_page(html, seen)
                    results.extend(listings)

                    if not has_more:
                        break

        return results

    def _parse_page(self, html: str, seen: set) -> tuple[list[JobListing], bool]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Each card: div.atlas-job-title is the title wrapper; its parent div is the card
        for title_div in soup.find_all("div", class_="atlas-job-title"):
            link = title_div.find("a", href=re.compile(r"^/jobs/\d+"))
            if not link:
                continue

            href = str(link.get("href", ""))
            match = re.search(r"/jobs/(\d+)", href)
            if not match:
                continue

            job_id = match.group(1)
            if job_id in seen:
                continue
            seen.add(job_id)

            title = link.get_text(strip=True)
            if not title:
                continue

            url = f"https://www.globaljobs.org{href}"

            # Parent card div contains org, region, and mobile meta
            card = title_div.parent
            if not card:
                continue

            org_div = card.find("div", class_="atlas-job-org")
            company = org_div.get_text(strip=True) if org_div else ""

            # Mobile meta has date + location spans
            meta_div = card.find("div", class_="atlas-mobile-only")
            spans = meta_div.find_all("span") if meta_div else []
            date_raw = spans[0].get_text(strip=True) if len(spans) > 0 else ""
            location_str = spans[1].get_text(strip=True) if len(spans) > 1 else ""

            country = location_str.split(",")[-1].strip() if "," in location_str else location_str
            region = infer_region(country, location_str)

            listings.append(JobListing(
                title=title,
                company=company,
                location=location_str,
                country=country,
                region=region,
                url=url,
                description="",
                salary_raw="",
                date_posted=self._parse_date(date_raw),
                source=self.name,
            ))

        has_more = len(listings) > 0
        return listings, has_more

    def _parse_date(self, text: str) -> datetime | None:
        if not text:
            return None
        text = text.strip().lower()
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        if "today" in text:
            return today
        if "yesterday" in text:
            return today - timedelta(days=1)
        match = re.search(r"(\d+)\s+day", text)
        if match:
            return today - timedelta(days=int(match.group(1)))
        try:
            return datetime.strptime(text, "%B %d, %Y")
        except ValueError:
            pass
        return None
