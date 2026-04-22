from __future__ import annotations

import logging
import urllib.parse

from models import JobListing
from .base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scrape LinkedIn job listings (public search, no login required)."""

    platform = "linkedin"
    base_url = "https://www.linkedin.com/jobs/search"
    delay_min = 3.0
    delay_max = 6.0

    EXPERIENCE_MAP = {
        "entry": "2",
        "mid": "3",
        "senior": "4",
        "internship": "1",
    }

    def _build_url(
        self,
        keywords: str,
        location: str,
        experience_level: str,
        job_type: str,
        remote_only: bool,
    ) -> str:
        params = {
            "keywords": keywords,
            "location": location or "India",
            "trk": "public_jobs_jobs-search-bar_search-submit",
            "position": "1",
            "pageNum": "0",
        }
        exp = self.EXPERIENCE_MAP.get(experience_level.lower(), "")
        if exp:
            params["f_E"] = exp
        if remote_only:
            params["f_WT"] = "2"
        return f"{self.base_url}?{urllib.parse.urlencode(params)}"

    async def search(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        from playwright.async_api import async_playwright

        url = self._build_url(keywords, location, experience_level, job_type, remote_only)
        listings: list[JobListing] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.get_user_agent(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Scroll to load more results
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)

                cards = await page.query_selector_all("div.base-card, li.jobs-search-results__list-item, div.job-search-card")

                for card in cards[:self.max_results]:
                    try:
                        title_el = await card.query_selector("h3.base-search-card__title, h3.base-card__title, a.base-card__full-link")
                        company_el = await card.query_selector("h4.base-search-card__subtitle, a.hidden-nested-link")
                        location_el = await card.query_selector("span.job-search-card__location")
                        link_el = await card.query_selector("a.base-card__full-link")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        loc = (await location_el.inner_text()).strip() if location_el else ""
                        href = await link_el.get_attribute("href") if link_el else ""

                        if not title or not company:
                            continue

                        listings.append(JobListing(
                            title=title,
                            company=company,
                            location=loc,
                            url=href.split("?")[0] if href else "",
                            platform=self.platform,
                            is_remote="remote" in loc.lower(),
                        ))
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"LinkedIn scrape error: {e}")
            finally:
                await browser.close()

        return listings

    async def get_job_details(self, url: str) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.get_user_agent())

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Try to click "Show more" if present
                show_more = await page.query_selector("button.show-more-less-html__button--more")
                if show_more:
                    await show_more.click()
                    await page.wait_for_timeout(1000)

                desc_el = await page.query_selector("div.show-more-less-html__markup, div.description__text")
                if desc_el:
                    return (await desc_el.inner_text()).strip()
                return "Could not extract job description."
            except Exception as e:
                return f"Error fetching LinkedIn job details: {e}"
            finally:
                await browser.close()
