from __future__ import annotations

import logging
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from ..models import JobListing
from .base import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """Scrape Indeed job listings using requests + BeautifulSoup."""

    platform = "indeed"
    base_url = "https://www.indeed.co.in/jobs"
    delay_min = 2.0
    delay_max = 4.0

    def _build_url(self, keywords: str, location: str, start: int = 0) -> str:
        params = {
            "q": keywords,
            "l": location or "India",
            "start": str(start),
            "sort": "date",
        }
        return f"{self.base_url}?{urllib.parse.urlencode(params)}"

    async def search(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        url = self._build_url(keywords, location)
        listings: list[JobListing] = []

        async with httpx.AsyncClient(headers=self.get_headers(), follow_redirects=True, timeout=30) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Indeed request failed: {e}")
                return []

        soup = BeautifulSoup(resp.text, "lxml")
        job_cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList div.cardOutline, td.resultContent")

        for card in job_cards[:self.max_results]:
            try:
                title_el = card.select_one("h2.jobTitle a, h2.jobTitle span")
                company_el = card.select_one("span[data-testid='company-name'], span.companyName")
                location_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
                salary_el = card.select_one("div.salary-snippet-container, div.metadata.salary-snippet-container")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                salary = salary_el.get_text(strip=True) if salary_el else ""

                link_el = card.select_one("h2.jobTitle a")
                job_id = link_el.get("data-jk", "") if link_el else ""
                job_url = f"https://www.indeed.co.in/viewjob?jk={job_id}" if job_id else ""

                if not title or not company:
                    continue

                listings.append(JobListing(
                    title=title,
                    company=company,
                    location=loc,
                    url=job_url,
                    platform=self.platform,
                    salary_range=salary,
                    is_remote="remote" in loc.lower(),
                ))
            except Exception:
                continue

        return listings

    async def get_job_details(self, url: str) -> str:
        async with httpx.AsyncClient(headers=self.get_headers(), follow_redirects=True, timeout=30) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                return f"Error fetching Indeed job details: {e}"

        soup = BeautifulSoup(resp.text, "lxml")
        desc = soup.select_one("div#jobDescriptionText, div.jobsearch-JobComponent-description")
        if desc:
            return desc.get_text(separator="\n", strip=True)
        return "Could not extract job description."
