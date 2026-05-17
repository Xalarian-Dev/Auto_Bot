"""
IT Job Board USA (itjobboard.net) — North America IT-specific job board.
Server-rendered HTML, no auth, no Cloudflare.
Pagination is AJAX-based so we scrape first page per query only.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from scout.models import JobListing, Region
from scout.sources.base import BaseSource

logger = logging.getLogger(__name__)

BASE_URL = "https://www.itjobboard.net/jobs/"


class ITJobBoardSource(BaseSource):
    name = "itjobboard"

    def fetch(self) -> list[JobListing]:
        queries: list[dict] = self.config.get("itjobboard_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Referer": "https://www.itjobboard.net/",
                "Accept": "text/html,application/xhtml+xml",
            })

            for query_cfg in queries:
                keyword = query_cfg.get("keyword", "")
                location = query_cfg.get("location", "")

                params: dict = {"action": "search", "listing_type[equal]": "Job"}
                if keyword:
                    params["keywords[all_words]"] = keyword
                if location:
                    params["Location[location][value]"] = location

                try:
                    resp = self._get(client, BASE_URL, params=params)
                    html = resp.text
                except Exception as exc:
                    logger.warning(f"[itjobboard] '{keyword}' failed: {exc}")
                    continue

                listings = self._parse_page(html, seen)
                results.extend(listings)

        return results

    def _parse_page(self, html: str, seen: set) -> list[JobListing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        for article in soup.find_all("article", class_="listing-item__jobs"):
            # Title + URL
            title_link = article.select_one(".listing-item__title .link")
            if not title_link:
                continue

            url = title_link.get("href", "")
            title = title_link.get_text(strip=True)
            if not url or not title:
                continue

            # Job ID from URL: /job/16676950/...
            match = re.search(r"/job/(\d+)/", url)
            job_id = match.group(1) if match else url
            if job_id in seen:
                continue
            seen.add(job_id)

            company_el = article.select_one(".listing-item__info--item-company")
            location_el = article.select_one(".listing-item__info--item-location")
            date_el = article.select_one(".listing-item__date")
            desc_el = article.select_one(".listing-item__desc")

            company = company_el.get_text(strip=True) if company_el else ""
            location_str = location_el.get_text(strip=True) if location_el else ""
            date_raw = date_el.get_text(strip=True) if date_el else ""
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Extract salary from description if present
            salary_raw = ""
            salary_match = re.search(
                r"(?:salary|pay|base pay)[^\$]*(\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?)",
                description, re.IGNORECASE
            )
            if salary_match:
                salary_raw = salary_match.group(0).strip()

            listings.append(JobListing(
                title=title,
                company=company,
                location=location_str,
                country="United States",
                region=Region.NORTH_AMERICA,
                url=str(url),
                description=description[:2000],
                salary_raw=salary_raw,
                date_posted=self._parse_date(date_raw),
                source=self.name,
            ))

        return listings

    def _parse_date(self, text: str) -> datetime | None:
        if not text:
            return None
        try:
            return datetime.strptime(text.strip(), "%m/%d/%Y")
        except ValueError:
            return None
