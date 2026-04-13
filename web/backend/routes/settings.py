"""Settings API routes for profile and preferences."""

import json
from fastapi import APIRouter, Depends
from pathlib import Path

from ..auth import verify_token
from ..config import DATA_DIR

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/profile")
async def get_profile(_=Depends(verify_token)):
    path = DATA_DIR / "profile.json"
    if not path.exists():
        return {"error": "profile.json not found"}
    return json.loads(path.read_text())


@router.put("/profile")
async def update_profile(body: dict, _=Depends(verify_token)):
    path = DATA_DIR / "profile.json"
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False))
    return {"message": "Profile updated", "profile": body}


@router.get("/preferences")
async def get_preferences(_=Depends(verify_token)):
    path = DATA_DIR / "preferences.json"
    if not path.exists():
        return {"error": "preferences.json not found"}
    return json.loads(path.read_text())


@router.put("/preferences")
async def update_preferences(body: dict, _=Depends(verify_token)):
    path = DATA_DIR / "preferences.json"
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False))
    return {"message": "Preferences updated", "preferences": body}


@router.get("/connections")
async def get_connection_status(_=Depends(verify_token)):
    """Check status of all external connections."""
    status = {
        "google_sheets": False,
        "gmail": False,
        "telegram": "configured",
        "whatsapp": "configured",
    }

    # Check Google Sheets
    service_account = DATA_DIR / "service-account.json"
    status["google_sheets"] = service_account.exists()

    # Check Gmail
    gmail_token = DATA_DIR / "gmail_token.json"
    gmail_creds = DATA_DIR / "gmail_credentials.json"
    if gmail_token.exists():
        status["gmail"] = "authenticated"
    elif gmail_creds.exists():
        status["gmail"] = "credentials_only"
    else:
        status["gmail"] = "not_configured"

    return status
