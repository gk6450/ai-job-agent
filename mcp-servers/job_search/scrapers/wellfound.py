from __future__ import annotations

import logging
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from models import JobListing
from .base import BaseScraper

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    """Scrape Wellfound (formerly AngelList Talent) job listings."""

    platform = "wellfound"
    base_url = "https://wellfound.com/role"
    delay_min = 2.0
    delay_max = 5.0

    ROLE_SLUGS = {
        "software engineer": "software-engineer",
        "full stack developer": "full-stack-developer",
        "backend developer": "backend-developer",
        "frontend developer": "frontend-developer",
        "data engineer": "data-engineer",
        "devops engineer": "devops-engineer",
    }

    def _build_url(self, keywords: str, location: str) -> str:
        slug = self.ROLE_SLUGS.get(keywords.lower(), keywords.lower().replace(" ", "-"))
        url = f"{self.base_url}/{slug}"
        if location:
            url += f"?locationPreference={urllib.parse.quote(location)}"
        return url

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
                logger.error(f"Wellfound request failed: {e}")
                return []

        soup = BeautifulSoup(resp.text, "lxml")
        job_cards = soup.select(
            "div.styles_jobListing__oPEaD, div[data-test='startup-jobs'] div.mb-6, div.styles_component__bQkJH"
        )

        for card in job_cards[:self.max_results]:
            try:
                title_el = card.select_one("a.styles_jobTitle__Fjsdd, h2 a, a[data-test='job-title']")
                company_el = card.select_one("a.styles_companyName__rFPSQ, h2.styles_startupName__hn2fv, a[data-test='startup-link']")
                location_el = card.select_one("span.styles_location__GS6Wb, span[data-test='job-location']")
                salary_el = card.select_one("span.styles_salary__il4Yf, span[data-test='job-salary']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                salary = salary_el.get_text(strip=True) if salary_el else ""
                href = title_el.get("href", "") if title_el else ""

                if not title or not company:
                    continue

                full_url = f"https://wellfound.com{href}" if href and href.startswith("/") else href

                listings.append(JobListing(
                    title=title,
                    company=company,
                    location=loc,
                    url=full_url or "",
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
                return f"Error fetching Wellfound job details: {e}"

        soup = BeautifulSoup(resp.text, "lxml")
        desc = soup.select_one(
            "div.styles_description__ClvSd, div[data-test='job-description'], div.styles_jobDescription__j7VVp"
        )
        if desc:
            return desc.get_text(separator="\n", strip=True)
        return "Could not extract job description."
