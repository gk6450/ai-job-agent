import logging
from fastmcp import FastMCP

from .auth import get_gmail_service, check_auth_status
from .reader import fetch_messages, search_by_company, EmailMessage
from .matcher import classify_email, match_email_to_application, suggest_status_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "GmailSync",
    description="Monitor Gmail for job application responses. Classify emails as interview invites, rejections, assessments, or offers. Match responses to tracked applications.",
)


def _get_tracker_data() -> list[dict]:
    """Fetch all application records from the tracker MCP."""
    try:
        import sys
        from pathlib import Path
        tracker_path = Path(__file__).parent.parent / "tracker"
        sys.path.insert(0, str(tracker_path))
        from server import _get_worksheet
        ws = _get_worksheet()
        return ws.get_all_records()
    except Exception as e:
        logger.warning(f"Could not load tracker data: {e}")
        return []


@mcp.tool()
async def check_gmail_auth() -> str:
    """Check Gmail authentication status.

    Returns whether Gmail is authenticated and which email is connected.
    If not authenticated, provides setup instructions.
    """
    status = check_auth_status()
    lines = []

    if status["authenticated"]:
        lines.append(f"Gmail connected: {status['email']}")
    else:
        lines.append("Gmail NOT connected.")
        if not status["credentials_file"]:
            lines.append(
                "Missing: data/gmail_credentials.json\n"
                "Setup: Google Cloud Console > APIs & Services > Credentials > "
                "Create OAuth 2.0 Client ID (Desktop App) > Download JSON > "
                "Save as data/gmail_credentials.json"
            )
        else:
            lines.append("Credentials file found. Run Gmail auth to connect (will open browser for consent).")

    return "\n".join(lines)


@mcp.tool()
async def check_new_responses(days_back: int = 7) -> str:
    """Scan Gmail inbox for new application-related emails.

    Checks for unread emails that might be responses to job applications.

    Args:
        days_back: Number of days to look back (default: 7)
    """
    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        return str(e)

    query = f"is:unread newer_than:{days_back}d (interview OR application OR assessment OR offer OR position OR candidate)"
    emails = fetch_messages(service, query, max_results=20)

    if not emails:
        return "No new application-related emails found."

    applications = _get_tracker_data()

    lines = [f"Found {len(emails)} potential application response(s):\n"]
    for email in emails:
        classification = classify_email(email)
        matched_app = match_email_to_application(email, applications)

        line = f"- {email.summary()}"
        line += f"\n  Classification: {classification.upper()}"
        if matched_app:
            line += f"\n  Matched to: {matched_app.get('ID', '?')} ({matched_app.get('Company', '?')} - {matched_app.get('Role', '?')})"
            suggested = suggest_status_update(classification)
            if suggested:
                line += f"\n  Suggested status update: {suggested}"
        else:
            line += "\n  No matching application found"
        lines.append(line)

    return "\n".join(lines)


@mcp.tool()
async def classify_email_by_id(email_id: str) -> str:
    """Classify a specific email (interview/rejection/assessment/offer/other).

    Args:
        email_id: Gmail message ID
    """
    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        return str(e)

    emails = fetch_messages(service, f"rfc822msgid:{email_id}", max_results=1)
    if not emails:
        try:
            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            from .reader import _extract_header, _extract_sender_parts, _decode_body
            headers = msg.get("payload", {}).get("headers", [])
            email_obj = EmailMessage(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                subject=_extract_header(headers, "Subject"),
                sender=_extract_sender_parts(_extract_header(headers, "From"))[0],
                sender_email=_extract_sender_parts(_extract_header(headers, "From"))[1],
                date=_extract_header(headers, "Date"),
                body=_decode_body(msg.get("payload", {}))[:3000],
                snippet=msg.get("snippet", ""),
            )
            emails = [email_obj]
        except Exception as e:
            return f"Could not fetch email {email_id}: {e}"

    email = emails[0]
    classification = classify_email(email)
    suggested = suggest_status_update(classification)

    lines = [
        f"Email: {email.summary()}",
        f"Classification: {classification.upper()}",
    ]
    if suggested:
        lines.append(f"Suggested tracker status: {suggested}")
    lines.append(f"\nSnippet: {email.snippet}")

    return "\n".join(lines)


@mcp.tool()
async def sync_all() -> str:
    """Full Gmail sync: check inbox, match to tracked applications, report updates.

    Scans recent emails, classifies them, matches to applications, and suggests status updates.
    Does NOT auto-update statuses (reports them for user review).
    """
    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        return str(e)

    applications = _get_tracker_data()
    if not applications:
        return "No tracked applications found. Nothing to sync against."

    companies = set()
    for app in applications:
        company = app.get("Company", "").strip()
        if company:
            companies.add(company)

    all_matches = []
    for company in companies:
        emails = search_by_company(service, company, max_results=5)
        for email in emails:
            classification = classify_email(email)
            matched = match_email_to_application(email, applications)
            if matched:
                all_matches.append({
                    "email": email,
                    "classification": classification,
                    "application": matched,
                    "suggested_status": suggest_status_update(classification),
                })

    if not all_matches:
        return f"Synced {len(companies)} companies. No new responses found."

    lines = [f"Gmail Sync Complete -- {len(all_matches)} response(s) found:\n"]
    for m in all_matches:
        app = m["application"]
        lines.append(
            f"- {app.get('ID', '?')} | {app.get('Company', '?')} - {app.get('Role', '?')}\n"
            f"  Email: {m['email'].subject}\n"
            f"  Classification: {m['classification'].upper()}\n"
            f"  Current status: {app.get('Status', '?')}"
        )
        if m["suggested_status"]:
            lines.append(f"  Suggested update: {app.get('Status', '?')} -> {m['suggested_status']}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
