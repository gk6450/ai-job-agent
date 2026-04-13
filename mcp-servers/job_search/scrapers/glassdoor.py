from __future__ import annotations

import logging
import urllib.parse

from ..models import JobListing
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    """Scrape Glassdoor job listings using Playwright."""

    platform = "glassdoor"
    base_url = "https://www.glassdoor.co.in/Job"
    delay_min = 3.0
    delay_max = 6.0

    def _build_url(self, keywords: str, location: str) -> str:
        params = {"sc.keyword": keywords}
        if location:
            params["locT"] = "C"
            params["locKeyword"] = location
        return f"{self.base_url}/jobs.htm?{urllib.parse.urlencode(params)}"

    async def search(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        from playwright.async_api import async_playwright

        url = self._build_url(keywords, location)
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

                # Dismiss any modals/popups
                for selector in ["button.modal_closeIcon", "button[data-test='close-modal']", "button.CloseButton"]:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(500)

                cards = await page.query_selector_all(
                    "li.JobsList_jobListItem__wjTHv, li[data-test='jobListing'], div.JobCard_jobCardContainer__arQlW"
                )

                for card in cards[:self.max_results]:
                    try:
                        title_el = await card.query_selector("a.JobCard_jobTitle__GLyJ1, a[data-test='job-title']")
                        company_el = await card.query_selector("span.EmployerProfile_compactEmployerName__9MGcV, div.EmployerProfile_employerInfo__GaPbq")
                        location_el = await card.query_selector("div.JobCard_location__N_iYE, div[data-test='emp-location']")
                        salary_el = await card.query_selector("div.JobCard_salaryEstimate__QpbTW, div[data-test='detailSalary']")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        loc = (await location_el.inner_text()).strip() if location_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else ""
                        href = await title_el.get_attribute("href") if title_el else ""

                        if not title or not company:
                            continue

                        full_url = f"https://www.glassdoor.co.in{href}" if href and href.startswith("/") else href

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

            except Exception as e:
                logger.error(f"Glassdoor scrape error: {e}")
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

                # Dismiss modals
                for selector in ["button.modal_closeIcon", "button[data-test='close-modal']"]:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(500)

                desc_el = await page.query_selector(
                    "div.JobDetails_jobDescription__uW_fK, div[data-test='jobDescriptionContent']"
                )
                if desc_el:
                    return (await desc_el.inner_text()).strip()
                return "Could not extract job description."
            except Exception as e:
                return f"Error fetching Glassdoor job details: {e}"
            finally:
                await browser.close()
