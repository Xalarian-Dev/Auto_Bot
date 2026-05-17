"""
Jaabz — visa-sponsored and relocation-friendly international jobs.
No auth required. Job data embedded as JSON-LD (schema.org JobPosting) in HTML.
Supports keyword + location filtering via query params.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from scout.models import JobListing
from scout.sources.base import BaseSource, infer_region

logger = logging.getLogger(__name__)

BASE_URL = "https://jaabz.com/jobs"


class JaabzSource(BaseSource):
    name = "jaabz"

    def fetch(self) -> list[JobListing]:
        queries: list[dict] = self.config.get("jaabz_queries", [])
        results: list[JobListing] = []
        seen: set[str] = set()

        with self._make_client(timeout=20) as client:
            client.headers.update({
                "Referer": "https://jaabz.com/",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })

            for query_cfg in queries:
                keyword = query_cfg.get("keyword", "")
                location = query_cfg.get("location", "")
                max_pages = query_cfg.get("max_pages", 3)

                for page in range(1, max_pages + 1):
                    params: dict = {"page": page}
                    if keyword:
                        params["q"] = keyword
                    if location:
                        params["location"] = location

                    try:
                        resp = self._get(client, BASE_URL, params=params)
                        html = resp.text
                    except Exception as exc:
                        logger.warning(f"[jaabz] '{keyword}' page {page} failed: {exc}")
                        break

                    listings, has_more = self._parse_page(html, seen)
                    results.extend(listings)

                    if not has_more:
                        break

        return results

    def _parse_page(self, html: str, seen: set) -> tuple[list[JobListing], bool]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Each job is a JSON-LD block with @type JobPosting, wrapped in a ListItem
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            # Page-level ItemList wraps all jobs
            if data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
                for item in items:
                    # URL is on the ListItem, not on the nested JobPosting
                    item_url = item.get("url", "")
                    job = item.get("item", item)
                    listing = self._parse_job(job, seen, fallback_url=item_url)
                    if listing:
                        listings.append(listing)

            # Fallback: individual JobPosting block
            elif data.get("@type") == "JobPosting":
                listing = self._parse_job(data, seen)
                if listing:
                    listings.append(listing)

        # Detect next page link
        has_more = bool(soup.select_one("a[rel=next], .pagination a[aria-label='Next']"))
        if len(listings) == 0:
            has_more = False

        return listings, has_more

    def _parse_job(self, job: dict, seen: set, fallback_url: str = "") -> JobListing | None:
        if job.get("@type") != "JobPosting":
            return None

        # Job ID from identifier or URL
        identifier = job.get("identifier", {})
        job_id = str(identifier.get("value", "")) if identifier else ""
        url = job.get("url", "") or fallback_url
        if not job_id:
            # Extract from URL slug: /jobs/213454-some-title
            match = re.search(r"/jobs/(\d+)", url)
            job_id = match.group(1) if match else url

        if not job_id or job_id in seen:
            return None
        seen.add(job_id)

        title = job.get("title", "").strip()
        if not title:
            return None

        # Company
        org = job.get("hiringOrganization", {})
        company = org.get("name", "").strip() if isinstance(org, dict) else ""

        # Location
        job_location = job.get("jobLocation", {})
        address = job_location.get("address", {}) if isinstance(job_location, dict) else {}
        locality = address.get("addressLocality", "").strip() if isinstance(address, dict) else ""
        country_raw = address.get("addressCountry", "").strip() if isinstance(address, dict) else ""
        location_str = ", ".join(filter(None, [locality, country_raw])) or "International"

        # Normalize country name (Jaabz uses "United State" — singular)
        country_clean = country_raw
        if "united state" in country_raw.lower():
            country_clean = "United States"

        region = infer_region(country_clean, locality)

        # Salary
        salary_raw = ""
        base_salary = job.get("baseSalary", {})
        if isinstance(base_salary, dict):
            value_obj = base_salary.get("value", {})
            currency = base_salary.get("currency", "")
            if isinstance(value_obj, dict):
                amount = value_obj.get("value", "")
                unit = value_obj.get("unitText", "YEAR")
                if amount:
                    salary_raw = f"{currency} {amount}/{unit}".strip()

        # Description
        description = job.get("description", "").strip()

        # Date
        date_posted = self._parse_date(job.get("datePosted"))

        return JobListing(
            title=title,
            company=company,
            location=location_str,
            country=country_clean,
            region=region,
            url=url,
            description=description[:2000] if description else "",
            salary_raw=salary_raw,
            date_posted=date_posted,
            source=self.name,
        )

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
