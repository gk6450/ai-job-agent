from __future__ import annotations

import logging
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from models import JobListing
from .base import BaseScraper

logger = logging.getLogger(__name__)


class NaukriScraper(BaseScraper):
    """Scrape Naukri.com job listings."""

    platform = "naukri"
    base_url = "https://www.naukri.com"
    delay_min = 2.0
    delay_max = 5.0

    EXPERIENCE_MAP = {
        "entry": "0-2",
        "mid": "2-5",
        "senior": "5-10",
        "internship": "0-0",
    }

    def _build_url(self, keywords: str, location: str, experience_level: str) -> str:
        slug = keywords.lower().replace(" ", "-")
        parts = [f"{slug}-jobs"]
        if location:
            parts.append(f"in-{location.lower().replace(' ', '-')}")

        exp = self.EXPERIENCE_MAP.get(experience_level.lower(), "")
        query_params = {}
        if exp:
            query_params["experience"] = exp

        path = "-".join(parts)
        url = f"{self.base_url}/{path}"
        if query_params:
            url += f"?{urllib.parse.urlencode(query_params)}"
        return url

    async def search(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        url = self._build_url(keywords, location, experience_level)
        listings: list[JobListing] = []

        headers = self.get_headers()
        headers["Referer"] = "https://www.naukri.com/"

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Naukri request failed: {e}")
                return []

        soup = BeautifulSoup(resp.text, "lxml")
        job_cards = soup.select("article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple")

        for card in job_cards[:self.max_results]:
            try:
                title_el = card.select_one("a.title, a.title.ellipsis")
                company_el = card.select_one("a.subTitle, a.comp-name")
                location_el = card.select_one("li.location span, span.locWdth, span.ellipsis.loc")
                salary_el = card.select_one("li.salary span, span.sal-wrap span")
                exp_el = card.select_one("li.experience span, span.expwdth")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                salary = salary_el.get_text(strip=True) if salary_el else ""
                exp = exp_el.get_text(strip=True) if exp_el else ""

                href = title_el.get("href", "") if title_el else ""

                if not title or not company:
                    continue

                listings.append(JobListing(
                    title=title,
                    company=company,
                    location=loc,
                    url=href,
                    platform=self.platform,
                    salary_range=salary,
                    experience_level=exp,
                    is_remote="remote" in loc.lower() or "work from home" in loc.lower(),
                ))
            except Exception:
                continue

        return listings

    async def get_job_details(self, url: str) -> str:
        headers = self.get_headers()
        headers["Referer"] = "https://www.naukri.com/"

        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                return f"Error fetching Naukri job details: {e}"

        soup = BeautifulSoup(resp.text, "lxml")
        desc = soup.select_one("div.job-desc, section.job-desc, div.dang-inner-html")
        if desc:
            return desc.get_text(separator="\n", strip=True)
        return "Could not extract job description."
