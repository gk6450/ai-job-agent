"""Application tracking API routes."""

import logging
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from ..auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["applications"])

TRACKER_PATH = Path(__file__).parent.parent.parent.parent / "mcp-servers" / "tracker"

_EMPTY_STATS = {
    "total": 0,
    "active": 0,
    "interviews": 0,
    "pending_followups": 0,
    "by_status": {},
    "by_date": [],
    "recent_activity": [],
}


def _get_tracker():
    sys.path.insert(0, str(TRACKER_PATH))
    import importlib
    server = importlib.import_module("server")
    return server


def _safe_get_records():
    """Fetch records from Sheets, returning [] on any failure (so the UI can show an empty state instead of 500)."""
    try:
        tracker = _get_tracker()
        ws = tracker._get_worksheet()
        return ws.get_all_records()
    except Exception as exc:
        logger.warning("Failed to fetch tracker records: %s", exc)
        return []


def _parse_date(value: str):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value)[:10], fmt[:10] if "T" in fmt else fmt)
        except ValueError:
            continue
    return None


@router.get("")
async def list_applications(
    status: str = Query("", description="Filter by status"),
    _=Depends(verify_token),
):
    records = _safe_get_records()

    if status:
        records = [r for r in records if str(r.get("Status", "")).lower() == status.lower()]

    return {"applications": records, "total": len(records)}


@router.get("/stats")
async def get_stats(_=Depends(verify_token)):
    records = _safe_get_records()
    if not records:
        return _EMPTY_STATS

    total = len(records)
    by_status: dict[str, int] = {}
    for r in records:
        s = str(r.get("Status", "Unknown")) or "Unknown"
        by_status[s] = by_status.get(s, 0) + 1

    inactive_keys = {"Rejected", "Withdrawn", "Skipped"}
    active = sum(v for k, v in by_status.items() if k not in inactive_keys)
    interviews = by_status.get("Interview", 0) + by_status.get("Interviewing", 0)

    pending_followups = sum(
        1 for r in records
        if str(r.get("Followup Status", "")).lower() in {"pending", "due", "scheduled"}
    )

    date_counter: Counter = Counter()
    for r in records:
        d = _parse_date(r.get("Applied Date") or r.get("Date") or "")
        if d:
            date_counter[d.strftime("%Y-%m-%d")] += 1

    by_date = [{"date": d, "count": c} for d, c in sorted(date_counter.items())]

    recent_sorted = sorted(
        records,
        key=lambda r: (_parse_date(r.get("Applied Date") or r.get("Date") or "") or datetime.min),
        reverse=True,
    )[:10]
    recent_activity = [
        {
            "id": str(r.get("ID") or r.get("Application ID") or ""),
            "company": str(r.get("Company") or ""),
            "role": str(r.get("Role") or r.get("Title") or ""),
            "action": str(r.get("Status") or "Applied"),
            "timestamp": str(r.get("Applied Date") or r.get("Date") or ""),
        }
        for r in recent_sorted
    ]

    return {
        "total": total,
        "active": active,
        "interviews": interviews,
        "pending_followups": pending_followups,
        "by_status": by_status,
        "by_date": by_date,
        "recent_activity": recent_activity,
    }


@router.get("/followups")
async def get_followups(_=Depends(verify_token)):
    tracker = _get_tracker()
    result = tracker.get_pending_followups()
    return {"message": result}


@router.get("/{application_id}")
async def get_application(application_id: str, _=Depends(verify_token)):
    tracker = _get_tracker()
    ws = tracker._get_worksheet()
    records = ws.get_all_records()

    app = next((r for r in records if r.get("ID") == application_id), None)
    if not app:
        return {"error": f"Application {application_id} not found"}, 404

    return {"application": app}


@router.put("/{application_id}/status")
async def update_application_status(
    application_id: str,
    body: dict,
    _=Depends(verify_token),
):
    tracker = _get_tracker()
    new_status = body.get("status", "")
    notes = body.get("notes", "")

    result = tracker.update_status(application_id, new_status, notes)
    return {"message": result}
