from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    url: str
    platform: str
    description: str = ""
    salary_range: str = ""
    posted_date: str = ""
    job_type: str = ""  # Full-time, Part-time, Contract, Internship
    experience_level: str = ""
    is_remote: bool = False
    skills: list[str] = field(default_factory=list)
    company_logo_url: str = ""
    apply_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        parts = [f"{self.title} at {self.company}"]
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.salary_range:
            parts.append(f"Salary: {self.salary_range}")
        if self.job_type:
            parts.append(f"Type: {self.job_type}")
        parts.append(f"Platform: {self.platform}")
        parts.append(f"URL: {self.url}")
        return " | ".join(parts)


@dataclass
class SearchQuery:
    keywords: str
    location: str = ""
    experience_level: str = ""
    job_type: str = ""
    remote_only: bool = False
    posted_within_days: int = 30
    platforms: list[str] = field(default_factory=lambda: [
        "linkedin", "indeed", "naukri", "glassdoor", "wellfound"
    ])


@dataclass
class SearchResult:
    query: SearchQuery
    listings: list[JobListing] = field(default_factory=list)
    total_found: int = 0
    total_after_dedup: int = 0
    errors: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Search: '{self.query.keywords}' in {self.query.location or 'any location'}",
            f"Found: {self.total_found} total, {self.total_after_dedup} after dedup",
        ]
        if self.errors:
            lines.append(f"Errors: {', '.join(f'{k}: {v}' for k, v in self.errors.items())}")
        return "\n".join(lines)
