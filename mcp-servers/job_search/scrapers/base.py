from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod

from ..models import JobListing

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    """Abstract base class for all job portal scrapers."""

    platform: str = "unknown"
    base_url: str = ""
    delay_min: float = 2.0
    delay_max: float = 5.0
    max_retries: int = 3
    max_results: int = 25

    def get_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    def get_headers(self) -> dict:
        return {
            "User-Agent": self.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    async def _delay(self) -> None:
        wait = random.uniform(self.delay_min, self.delay_max)
        await asyncio.sleep(wait)

    async def search_with_retry(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        """Execute search with retry logic. Returns empty list on total failure."""
        for attempt in range(1, self.max_retries + 1):
            try:
                results = await self.search(
                    keywords=keywords,
                    location=location,
                    experience_level=experience_level,
                    job_type=job_type,
                    remote_only=remote_only,
                )
                logger.info(
                    f"[{self.platform}] Found {len(results)} results for '{keywords}'"
                )
                return results
            except Exception as e:
                logger.warning(
                    f"[{self.platform}] Attempt {attempt}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)

        logger.error(f"[{self.platform}] All {self.max_retries} attempts failed for '{keywords}'")
        return []

    @abstractmethod
    async def search(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        remote_only: bool = False,
    ) -> list[JobListing]:
        """Search for jobs. Must be implemented by each scraper."""
        ...

    @abstractmethod
    async def get_job_details(self, url: str) -> str:
        """Fetch full job description from a URL."""
        ...
