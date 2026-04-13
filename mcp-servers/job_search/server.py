import asyncio
import json
import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from .models import JobListing, SearchQuery, SearchResult
from .dedup import deduplicate
from .scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "JobSearch",
    description="Search for job listings across LinkedIn, Indeed, Naukri, Glassdoor, and Wellfound. Deduplicate and rank results.",
)

PREFS_PATH = Path(__file__).parent.parent.parent / "data" / "preferences.json"


def _load_preferences() -> dict:
    if PREFS_PATH.exists():
        return json.loads(PREFS_PATH.read_text())
    return {}


@mcp.tool()
async def search_jobs(
    keywords: str,
    platform: str,
    location: str = "",
    experience_level: str = "",
    job_type: str = "",
    remote_only: bool = False,
    max_results: int = 25,
) -> str:
    """Search for jobs on a specific platform.

    Args:
        keywords: Job title or search keywords (e.g., 'Software Engineer', 'Python Developer')
        platform: Platform to search (linkedin, indeed, naukri, glassdoor, wellfound)
        location: Location filter (e.g., 'Bangalore', 'Chennai', 'Remote')
        experience_level: Experience level (entry, mid, senior, internship)
        job_type: Job type filter (full-time, part-time, contract)
        remote_only: Only show remote positions
        max_results: Maximum number of results to return
    """
    platform = platform.lower().strip()
    if platform not in SCRAPERS:
        return f"Unknown platform '{platform}'. Available: {', '.join(SCRAPERS.keys())}"

    scraper_class = SCRAPERS[platform]
    scraper = scraper_class()
    scraper.max_results = max_results

    listings = await scraper.search_with_retry(
        keywords=keywords,
        location=location,
        experience_level=experience_level,
        job_type=job_type,
        remote_only=remote_only,
    )

    if not listings:
        return f"No jobs found on {platform} for '{keywords}' in '{location or 'any location'}'."

    lines = [f"Found {len(listings)} job(s) on {platform}:\n"]
    for i, job in enumerate(listings, 1):
        lines.append(f"{i}. {job.summary()}")

    return "\n".join(lines)


@mcp.tool()
async def search_all_platforms(
    keywords: str,
    location: str = "",
    experience_level: str = "",
    remote_only: bool = False,
    platforms: str = "",
) -> str:
    """Search all configured job platforms, deduplicate, and return ranked results.

    Args:
        keywords: Job title or search keywords
        location: Location filter
        experience_level: Experience level (entry, mid, senior, internship)
        remote_only: Only show remote positions
        platforms: Comma-separated list of platforms to search (leave empty to use all from preferences)
    """
    prefs = _load_preferences()

    if platforms:
        platform_list = [p.strip().lower() for p in platforms.split(",")]
    else:
        platform_list = prefs.get("platforms", list(SCRAPERS.keys()))

    if not location:
        pref_locations = prefs.get("preferred_locations", [])
        if pref_locations and pref_locations != ["FILL_IN"]:
            location = pref_locations[0]

    all_listings: list[JobListing] = []
    errors: dict[str, str] = {}

    for platform_name in platform_list:
        if platform_name not in SCRAPERS:
            errors[platform_name] = "Unknown platform"
            continue

        scraper_class = SCRAPERS[platform_name]
        scraper = scraper_class()

        try:
            listings = await scraper.search_with_retry(
                keywords=keywords,
                location=location,
                experience_level=experience_level,
                remote_only=remote_only,
            )
            all_listings.extend(listings)
        except Exception as e:
            errors[platform_name] = str(e)

        await asyncio.sleep(1)

    total_before = len(all_listings)
    unique_listings = deduplicate(all_listings)

    result = SearchResult(
        query=SearchQuery(
            keywords=keywords,
            location=location,
            experience_level=experience_level,
            remote_only=remote_only,
            platforms=platform_list,
        ),
        listings=unique_listings,
        total_found=total_before,
        total_after_dedup=len(unique_listings),
        errors=errors,
    )

    lines = [result.summary(), ""]
    for i, job in enumerate(unique_listings, 1):
        lines.append(f"{i}. {job.summary()}")

    if errors:
        lines.append(f"\nPlatform errors: {errors}")

    return "\n".join(lines)


@mcp.tool()
async def get_job_details(url: str) -> str:
    """Fetch the full job description from a job listing URL.

    Args:
        url: The full URL of the job listing
    """
    url_lower = url.lower()

    platform = None
    if "linkedin.com" in url_lower:
        platform = "linkedin"
    elif "indeed.co" in url_lower or "indeed.com" in url_lower:
        platform = "indeed"
    elif "naukri.com" in url_lower:
        platform = "naukri"
    elif "glassdoor" in url_lower:
        platform = "glassdoor"
    elif "wellfound.com" in url_lower:
        platform = "wellfound"

    if platform and platform in SCRAPERS:
        scraper = SCRAPERS[platform]()
        return await scraper.get_job_details(url)

    # Generic fallback: try with httpx + BS4
    import httpx
    from bs4 import BeautifulSoup

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"
            })
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        for selector in ["div.job-description", "div.description", "div#job-details",
                         "section.job-description", "div[class*='description']", "article"]:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 100:
                return el.get_text(separator="\n", strip=True)

        body = soup.select_one("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            return text[:5000] if len(text) > 5000 else text

        return "Could not extract job description from this URL."
    except Exception as e:
        return f"Error fetching job details: {e}"


if __name__ == "__main__":
    mcp.run()
