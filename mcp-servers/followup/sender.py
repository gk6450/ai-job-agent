"""Send emails via Gmail API."""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_gmail_service():
    """Get authenticated Gmail service from the gmail_sync module."""
    import sys
    from pathlib import Path
    gmail_path = Path(__file__).parent.parent / "gmail_sync"
    sys.path.insert(0, str(gmail_path))
    from auth import get_gmail_service
    return get_gmail_service()


def create_message(to: str, subject: str, body: str, from_email: str = "me") -> dict:
    """Create a Gmail API message object."""
    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject
    msg_body = MIMEText(body, "plain")
    message.attach(msg_body)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email via Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)

    Returns:
        dict with 'success' (bool), 'message_id' (str), 'error' (str)
    """
    try:
        service = _get_gmail_service()
        message = create_message(to, subject, body)
        sent = service.users().messages().send(userId="me", body=message).execute()
        logger.info(f"Email sent to {to}, ID: {sent.get('id')}")
        return {"success": True, "message_id": sent.get("id", ""), "error": ""}
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return {"success": False, "message_id": "", "error": str(e)}
