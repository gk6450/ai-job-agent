"""Match incoming emails to tracked job applications."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from thefuzz import fuzz

from .reader import EmailMessage

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 75

CLASSIFICATION_KEYWORDS = {
    "interview": [
        "interview", "schedule", "calendar invite", "meeting", "call",
        "video call", "zoom", "teams", "google meet", "phone screen",
        "technical round", "coding round", "onsite",
    ],
    "rejection": [
        "unfortunately", "not moving forward", "not selected",
        "decided not to", "other candidates", "not a fit",
        "will not be proceeding", "regret to inform",
        "position has been filled", "not shortlisted",
    ],
    "assessment": [
        "assessment", "coding test", "coding challenge", "hackerrank",
        "codility", "take-home", "assignment", "online test",
        "technical assessment", "aptitude test",
    ],
    "offer": [
        "offer letter", "congratulations", "pleased to offer",
        "compensation", "joining date", "offer of employment",
    ],
}


def classify_email(email: EmailMessage) -> str:
    """Classify an email into: interview, rejection, assessment, offer, or other."""
    text = f"{email.subject} {email.body}".lower()

    scores = {}
    for category, keywords in CLASSIFICATION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score

    if not scores:
        return "other"

    return max(scores, key=scores.get)


def extract_company_domain(sender_email: str) -> str:
    """Extract the company domain from a sender email."""
    if "@" not in sender_email:
        return ""
    domain = sender_email.split("@")[1].lower()
    # Skip generic email providers
    generic = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "icloud.com"}
    if domain in generic:
        return ""
    return domain.split(".")[0]


def match_email_to_application(
    email: EmailMessage,
    applications: list[dict],
) -> dict | None:
    """Match an email to a tracked application using company name/domain fuzzy matching.

    Args:
        email: The email to match
        applications: List of application records from the tracker

    Returns:
        The matched application dict, or None
    """
    sender_domain = extract_company_domain(email.sender_email)
    text_to_check = f"{email.subject} {email.sender} {email.sender_email}".lower()

    best_match = None
    best_score = 0

    for app in applications:
        company = app.get("Company", "").lower().strip()
        if not company:
            continue

        # Direct company name match in email
        if company in text_to_check:
            return app

        # Domain match
        if sender_domain and sender_domain in company.replace(" ", ""):
            return app

        # Fuzzy match
        score = fuzz.partial_ratio(company, text_to_check)
        if score > best_score and score >= MATCH_THRESHOLD:
            best_score = score
            best_match = app

    return best_match


def suggest_status_update(classification: str) -> str | None:
    """Suggest a tracker status update based on email classification."""
    mapping = {
        "interview": "Interview Scheduled",
        "rejection": "Rejected",
        "assessment": "Assessment Received",
        "offer": "Offer Received",
    }
    return mapping.get(classification)
