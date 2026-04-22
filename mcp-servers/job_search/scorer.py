"""Score job listings against the user's resume and preferences."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from thefuzz import fuzz

from models import JobListing

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load_resume() -> dict:
    path = DATA_DIR / "base_resume.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _load_preferences() -> dict:
    path = DATA_DIR / "preferences.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _flatten_skills(resume: dict) -> set[str]:
    """Extract all skills as a flat lowercase set."""
    skills_dict = resume.get("skills", {})
    all_skills = set()
    for category_items in skills_dict.values():
        if isinstance(category_items, list):
            for s in category_items:
                all_skills.add(s.lower().strip())
    return all_skills


def score_job(listing: JobListing) -> int:
    """Score a job listing 0-100 based on match to resume and preferences.

    Scoring breakdown:
      - Title match to target roles: 0-30 points
      - Skills overlap: 0-35 points
      - Location match: 0-15 points
      - Remote preference: 0-10 points
      - Experience level match: 0-10 points
    """
    resume = _load_resume()
    prefs = _load_preferences()
    score = 0

    # --- Title match (30 pts) ---
    target_roles = prefs.get("target_roles", [])
    title_lower = listing.title.lower()
    best_title_score = 0
    for role in target_roles:
        ratio = fuzz.token_sort_ratio(role.lower(), title_lower)
        best_title_score = max(best_title_score, ratio)
    score += int(best_title_score * 0.30)

    # --- Skills overlap (35 pts) ---
    user_skills = _flatten_skills(resume)
    if user_skills:
        job_text = f"{listing.title} {listing.description}".lower()
        matched = sum(1 for skill in user_skills if skill in job_text)
        skill_ratio = min(matched / max(len(user_skills) * 0.3, 1), 1.0)
        score += int(skill_ratio * 35)

    # --- Location match (15 pts) ---
    pref_locations = prefs.get("preferred_locations", [])
    if pref_locations and pref_locations != ["FILL_IN"]:
        loc_lower = listing.location.lower()
        for pref_loc in pref_locations:
            if pref_loc.lower() in loc_lower:
                score += 15
                break
            elif fuzz.partial_ratio(pref_loc.lower(), loc_lower) >= 80:
                score += 10
                break
    else:
        score += 8  # no location preference = neutral

    # --- Remote preference (10 pts) ---
    open_to_remote = prefs.get("open_to_remote", "FILL_IN")
    if listing.is_remote:
        if open_to_remote in (True, "yes", "Yes"):
            score += 10
        elif open_to_remote == "FILL_IN":
            score += 5
    else:
        if open_to_remote not in (True, "yes", "Yes") or open_to_remote == "FILL_IN":
            score += 5

    # --- Experience level (10 pts) ---
    pref_exp = prefs.get("experience_level", "").lower()
    listing_exp = listing.experience_level.lower()
    if pref_exp and listing_exp:
        if any(term in listing_exp for term in pref_exp.split()):
            score += 10
        elif "2" in listing_exp or "entry" in listing_exp or "junior" in listing_exp:
            score += 7
    else:
        score += 5  # no info = neutral

    return min(score, 100)


def score_and_rank(listings: list[JobListing]) -> list[tuple[JobListing, int]]:
    """Score all listings and return sorted by score descending."""
    scored = [(listing, score_job(listing)) for listing in listings]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


AUTO_APPLY_THRESHOLD = 85
