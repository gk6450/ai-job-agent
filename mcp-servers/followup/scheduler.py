"""Follow-up scheduling logic."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

PREFS_PATH = Path(__file__).parent.parent.parent / "data" / "preferences.json"

TERMINAL_STATUSES = {
    "Rejected", "Offer Received", "Offer Accepted",
    "Offer Declined", "Withdrawn", "Skipped",
}


def _load_preferences() -> dict:
    if PREFS_PATH.exists():
        return json.loads(PREFS_PATH.read_text())
    return {}


def get_due_followups(applications: list[dict]) -> list[dict]:
    """Determine which applications are due for follow-up.

    Args:
        applications: List of tracker records (dicts with keys: ID, Company, Role, Status, Date Applied, etc.)

    Returns:
        List of applications needing follow-up, each enriched with 'followup_number' and 'days_since_applied'
    """
    prefs = _load_preferences()
    first_days = prefs.get("followup_days_first", 7)
    second_days = prefs.get("followup_days_second", 14)
    max_followups = prefs.get("max_followups_per_application", 2)

    today = datetime.now()
    due = []

    for app in applications:
        status = app.get("Status", "")
        if status in TERMINAL_STATUSES:
            continue

        applied_str = app.get("Date Applied", "")
        if not applied_str:
            continue

        try:
            applied_date = datetime.strptime(applied_str.strip()[:10], "%Y-%m-%d")
        except ValueError:
            try:
                applied_date = datetime.strptime(applied_str.strip()[:16], "%Y-%m-%d %H:%M")
            except ValueError:
                continue

        days_since = (today - applied_date).days

        # Determine follow-up number based on status
        if status == "Followed Up":
            followup_num = 2
            threshold = second_days
        else:
            followup_num = 1
            threshold = first_days

        if followup_num > max_followups:
            continue

        if days_since >= threshold:
            due.append({
                **app,
                "followup_number": followup_num,
                "days_since_applied": days_since,
                "threshold_days": threshold,
            })

    return due
