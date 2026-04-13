"""Application tracking API routes."""

from fastapi import APIRouter, Depends, Query
from ..auth import verify_token

import sys
from pathlib import Path

router = APIRouter(prefix="/api/applications", tags=["applications"])

TRACKER_PATH = Path(__file__).parent.parent.parent.parent / "mcp-servers" / "tracker"


def _get_tracker():
    sys.path.insert(0, str(TRACKER_PATH))
    import importlib
    server = importlib.import_module("server")
    return server


@router.get("")
async def list_applications(
    status: str = Query("", description="Filter by status"),
    _=Depends(verify_token),
):
    tracker = _get_tracker()
    ws = tracker._get_worksheet()
    records = ws.get_all_records()

    if status:
        records = [r for r in records if r.get("Status", "").lower() == status.lower()]

    return {"applications": records, "total": len(records)}


@router.get("/stats")
async def get_stats(_=Depends(verify_token)):
    tracker = _get_tracker()
    ws = tracker._get_worksheet()
    records = ws.get_all_records()

    total = len(records)
    by_status = {}
    for r in records:
        s = r.get("Status", "Unknown")
        by_status[s] = by_status.get(s, 0) + 1

    active = total - by_status.get("Rejected", 0) - by_status.get("Withdrawn", 0) - by_status.get("Skipped", 0)

    return {
        "total": total,
        "active": active,
        "by_status": by_status,
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
