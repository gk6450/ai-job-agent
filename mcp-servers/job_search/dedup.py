from __future__ import annotations

from thefuzz import fuzz

from .models import JobListing

SIMILARITY_THRESHOLD = 85


def deduplicate(listings: list[JobListing]) -> list[JobListing]:
    """Remove duplicate job listings using fuzzy matching on company + title."""
    if not listings:
        return []

    unique: list[JobListing] = []
    seen_keys: list[str] = []

    for listing in listings:
        key = f"{listing.company.lower().strip()} | {listing.title.lower().strip()}"
        is_dup = False
        for seen in seen_keys:
            if fuzz.token_sort_ratio(key, seen) >= SIMILARITY_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            unique.append(listing)
            seen_keys.append(key)

    return unique
