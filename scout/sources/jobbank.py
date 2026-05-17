"""
Job Bank Canada -- official Canadian government job portal.
No API key required. HTML scraping of server-rendered pages.
Good source for senior IT PM roles in Canadian public and private sector.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from scout.models import JobListing, Region
from scout.sources.base import BaseSource

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jobbank.gc.ca"
SEARCH_URL = f"{BASE_URL}/jobsearch/jobsearch"


class JobBankCanadaSource(BaseSource):
    name = "jobbank"

    def fetch(self) -> list[JobListing]:
        queries: list[dict] = self.config.get("jobbank_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Referer": "https://www.jobbank.gc.ca/jobsearch",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-CA,en;q=0.9",
            })

            for query_cfg in queries:
                keyword = query_cfg["keyword"]
                location = query_cfg.get("location", "Canada")
                max_pages = query_cfg.get("max_pages", 3)

                for page in range(1, max_pages + 1):
                    params = {
                        "searchstring": keyword,
                        "locationstring": location,
                        "sort": "D",
                        "page": page,
                    }

                    try:
                        resp = self._get(client, SEARCH_URL, params=params)
                        html = resp.content.decode("utf-8", errors="replace")
                    except Exception as exc:
                        logger.warning(f"[jobbank] '{keyword}' page {page} failed: {exc}")
                        break

                    listings, has_more = self._parse_page(html, seen)
                    results.extend(listings)

                    if not has_more:
                        break

        return results

    def _parse_page(self, html: str, seen: set) -> tuple[list[JobListing], bool]:
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article")
        listings = []

        for article in articles:
            link_el = article.select_one("a.resultJobItem")
            if not link_el:
                continue

            # Extract job ID from article id attr (e.g. "article-49521361")
            article_id = article.get("id", "")
            job_id = article_id.replace("article-", "")
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)

            title_el = link_el.select_one("span.noctitle")
            employer_el = link_el.select_one("li.business")
            location_el = link_el.select_one("li.location")
            date_el = link_el.select_one("li.date")
            salary_el = link_el.select_one("li.salary")

            title = title_el.get_text(strip=True) if title_el else ""
            employer = employer_el.get_text(strip=True) if employer_el else ""
            location_raw = location_el.get_text(strip=True) if location_el else ""
            # Strip the icon text from location
            location_str = re.sub(r"\s+", " ", location_raw).strip()
            salary = salary_el.get_text(strip=True) if salary_el else ""
            # Clean salary text (strip icon/label)
            salary = re.sub(r"^Salary\s*", "", salary).strip()

            href = link_el.get("href", "")
            # Clean jsessionid from URL
            clean_href = re.sub(r";jsessionid=[^?]+", "", href)
            url = f"{BASE_URL}{clean_href}" if clean_href.startswith("/") else clean_href

            listing = JobListing(
                title=title,
                company=employer,
                location=location_str,
                country="Canada",
                region=Region.NORTH_AMERICA,
                url=url,
                description="",
                salary_raw=salary,
                date_posted=self._parse_date(date_el.get_text(strip=True) if date_el else ""),
                source=self.name,
            )
            listings.append(listing)

        # Check if there's a next page
        has_more = bool(soup.select_one("a[rel=next], .pagination .next:not(.disabled)"))
        # Also stop if we got fewer results than expected
        if len(articles) < 5:
            has_more = False

        return listings, has_more

    def _parse_date(self, text: str) -> datetime | None:
        if not text:
            return None
        # Format: "May 15, 2026" or "May 15, 2026"
        try:
            return datetime.strptime(text.strip(), "%b %d, %Y")
        except ValueError:
            return None
