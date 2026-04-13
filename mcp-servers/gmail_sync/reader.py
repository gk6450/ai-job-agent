"""Read and parse emails from Gmail."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    date: str
    body: str
    snippet: str
    labels: list[str] = field(default_factory=list)
    is_unread: bool = False

    def summary(self) -> str:
        return f"From: {self.sender} <{self.sender_email}> | Subject: {self.subject} | Date: {self.date}"


def _extract_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_sender_parts(from_header: str) -> tuple[str, str]:
    """Extract name and email from a From header like 'Name <email@example.com>'."""
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        email = from_header.split("<")[1].split(">")[0].strip()
        return name, email
    return from_header, from_header


def _decode_body(payload: dict) -> str:
    """Recursively extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text

    return ""


def fetch_messages(service, query: str, max_results: int = 20) -> list[EmailMessage]:
    """Fetch emails matching a Gmail search query.

    Args:
        service: Authenticated Gmail service
        query: Gmail search query (e.g., 'from:company.com subject:application')
        max_results: Maximum number of messages to fetch
    """
    try:
        response = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
    except Exception as e:
        logger.error(f"Gmail list failed: {e}")
        return []

    messages_data = response.get("messages", [])
    if not messages_data:
        return []

    results = []
    for msg_ref in messages_data:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            subject = _extract_header(headers, "Subject")
            from_header = _extract_header(headers, "From")
            date_header = _extract_header(headers, "Date")

            sender_name, sender_email = _extract_sender_parts(from_header)
            body = _decode_body(msg.get("payload", {}))
            labels = msg.get("labelIds", [])

            results.append(EmailMessage(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                subject=subject,
                sender=sender_name,
                sender_email=sender_email,
                date=date_header,
                body=body[:3000],
                snippet=msg.get("snippet", ""),
                labels=labels,
                is_unread="UNREAD" in labels,
            ))
        except Exception as e:
            logger.warning(f"Failed to fetch message {msg_ref.get('id')}: {e}")

    return results


def search_by_company(service, company_name: str, max_results: int = 10) -> list[EmailMessage]:
    """Search for emails related to a specific company."""
    queries = [
        f'from:{company_name.lower().replace(" ", "")}',
        f'subject:"{company_name}"',
        f'"{company_name}" application',
    ]
    query = " OR ".join(f"({q})" for q in queries)
    return fetch_messages(service, query, max_results)
