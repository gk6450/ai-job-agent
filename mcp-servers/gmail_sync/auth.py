"""Gmail OAuth2 authentication handler."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CREDENTIALS_FILE = DATA_DIR / "gmail_credentials.json"
TOKEN_FILE = DATA_DIR / "gmail_token.json"


def get_gmail_service():
    """Get an authenticated Gmail API service.

    First run requires browser-based OAuth consent.
    Subsequent runs use the saved token (auto-refreshed).
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing Gmail token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials not found at {CREDENTIALS_FILE}. "
                    "Download it from Google Cloud Console > APIs & Services > Credentials > "
                    "OAuth 2.0 Client ID > Download JSON, and save as data/gmail_credentials.json"
                )
            logger.info("Starting Gmail OAuth flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        logger.info(f"Gmail token saved to {TOKEN_FILE}")

    return build("gmail", "v1", credentials=creds)


def check_auth_status() -> dict:
    """Check Gmail authentication status without triggering auth flow."""
    status = {
        "credentials_file": CREDENTIALS_FILE.exists(),
        "token_file": TOKEN_FILE.exists(),
        "authenticated": False,
        "email": None,
    }

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if creds.valid or (creds.expired and creds.refresh_token):
                if creds.expired:
                    creds.refresh(Request())
                status["authenticated"] = True

                service = build("gmail", "v1", credentials=creds)
                profile = service.users().getProfile(userId="me").execute()
                status["email"] = profile.get("emailAddress")
        except Exception as e:
            logger.debug(f"Auth check failed: {e}")

    return status
