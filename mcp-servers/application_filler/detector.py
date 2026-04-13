"""Detect the ATS (Applicant Tracking System) type from a job URL."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# URL pattern -> ATS type mapping
URL_PATTERNS: list[tuple[str, str]] = [
    (r"myworkdayjobs\.com", "workday"),
    (r"wd\d+\.myworkday\.com", "workday"),
    (r"boards\.greenhouse\.io", "greenhouse"),
    (r"job-boards\.greenhouse\.io", "greenhouse"),
    (r"jobs\.lever\.co", "lever"),
    (r"linkedin\.com/jobs", "linkedin"),
    (r"linkedin\.com/in/.*/apply", "linkedin"),
    (r"naukri\.com", "naukri"),
    (r"indeed\.com", "indeed"),
    (r"indeed\.co\.", "indeed"),
    (r"icims\.com", "icims"),
    (r"careers-.*\.icims\.com", "icims"),
    (r"jobs\.ashbyhq\.com", "ashby"),
    (r"bamboohr\.com", "bamboohr"),
    (r"smartrecruiters\.com", "smartrecruiters"),
    (r"jobvite\.com", "jobvite"),
    (r"taleo\.net", "taleo"),
    (r"successfactors\.com", "successfactors"),
    (r"zoho\.com/recruit", "zoho"),
    (r"breezy\.hr", "breezy"),
    (r"applytojob\.com", "breezy"),
]

# DOM signatures for fallback detection
DOM_SIGNATURES: dict[str, list[str]] = {
    "workday": ["data-automation-id", "workday", "wd-popup"],
    "greenhouse": ["greenhouse", "gh-header", "boards.greenhouse.io"],
    "lever": ["lever-jobs-container", "lever-application"],
    "icims": ["icims", "iCIMS_MainWrapper"],
    "taleo": ["taleo", "requisition"],
    "smartrecruiters": ["smartrecruiters", "smrtr"],
}


def detect_from_url(url: str) -> str | None:
    """Detect ATS type from URL patterns."""
    url_lower = url.lower()
    for pattern, ats_type in URL_PATTERNS:
        if re.search(pattern, url_lower):
            return ats_type
    return None


async def detect_from_dom(page) -> str | None:
    """Detect ATS type by inspecting the page DOM."""
    try:
        html = await page.content()
        html_lower = html.lower()

        for ats_type, signatures in DOM_SIGNATURES.items():
            matches = sum(1 for sig in signatures if sig.lower() in html_lower)
            if matches >= 2:
                return ats_type

    except Exception:
        pass
    return None


async def detect_ats_type(url: str, page=None) -> str:
    """Detect ATS type using URL patterns first, then DOM analysis.

    Returns:
        ATS type string (e.g., 'workday', 'greenhouse') or 'unknown'
    """
    result = detect_from_url(url)
    if result:
        return result

    if page:
        result = await detect_from_dom(page)
        if result:
            return result

    return "unknown"
