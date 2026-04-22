import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

from auth import get_gmail_service, check_auth_status
from reader import fetch_messages, search_by_company, EmailMessage
from matcher import classify_email, match_email_to_application, suggest_status_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("GmailSync")


def _get_tracker_module():
    """Import the tracker server module."""
    import sys
    from pathlib import Path
    tracker_path = Path(__file__).parent.parent / "tracker"
    if str(tracker_path) not in sys.path:
        sys.path.insert(0, str(tracker_path))
    import server as tracker_server
    return tracker_server


def _get_tracker_data() -> list[dict]:
    """Fetch all application records from the tracker MCP."""
    try:
        tracker = _get_tracker_module()
        ws = tracker._get_worksheet()
        return ws.get_all_records()
    except Exception as e:
        logger.warning(f"Could not load tracker data: {e}")
        return []


def _auto_update_tracker(application_id: str, new_status: str, notes: str = "") -> bool:
    """Auto-update an application's status in the tracker sheet."""
    try:
        tracker = _get_tracker_module()
        result = tracker.update_status(application_id, new_status, notes)
        logger.info(f"Auto-updated {application_id} -> {new_status}")
        return "Updated" in result
    except Exception as e:
        logger.error(f"Failed to auto-update tracker: {e}")
        return False


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

    updated_count = 0
    lines = [f"Found {len(emails)} potential application response(s):\n"]
    for email in emails:
        classification = classify_email(email)
        matched_app = match_email_to_application(email, applications)

        line = f"- {email.summary()}"
        line += f"\n  Classification: {classification.upper()}"
        if matched_app:
            app_id = matched_app.get("ID", "?")
            current_status = matched_app.get("Status", "")
            line += f"\n  Matched to: {app_id} ({matched_app.get('Company', '?')} - {matched_app.get('Role', '?')})"
            suggested = suggest_status_update(classification)
            if suggested and suggested != current_status:
                email_note = f"Gmail: {email.subject} ({email.date})"
                updated = _auto_update_tracker(app_id, suggested, email_note)
                if updated:
                    line += f"\n  Tracker AUTO-UPDATED: {current_status} -> {suggested}"
                    updated_count += 1
                else:
                    line += f"\n  Update needed: {current_status} -> {suggested} (auto-update failed)"
        else:
            line += "\n  No matching application found"
        lines.append(line)

    if updated_count:
        lines.insert(1, f"Auto-updated {updated_count} application(s) in tracker.\n")

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
    """Full Gmail sync: check inbox, match to tracked applications, auto-update tracker.

    Scans recent emails, classifies them, matches to applications, automatically
    updates the tracker sheet, and returns a notification summary.
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

    updated_count = 0
    lines = [f"Gmail Sync Complete -- {len(all_matches)} response(s) found:\n"]
    for m in all_matches:
        app = m["application"]
        new_status = m["suggested_status"]
        current_status = app.get("Status", "")
        app_id = app.get("ID", "?")

        status_line = f"  Status: {current_status}"

        if new_status and new_status != current_status:
            email_note = f"Gmail: {m['email'].subject} ({m['email'].date})"
            updated = _auto_update_tracker(app_id, new_status, email_note)
            if updated:
                status_line = f"  Status: {current_status} -> {new_status} (AUTO-UPDATED)"
                updated_count += 1
            else:
                status_line = f"  Status: {current_status} -> {new_status} (update failed)"

        lines.append(
            f"- {app_id} | {app.get('Company', '?')} - {app.get('Role', '?')}\n"
            f"  Email: {m['email'].subject}\n"
            f"  Classification: {m['classification'].upper()}\n"
            f"{status_line}"
        )

    if updated_count:
        lines.insert(1, f"Auto-updated {updated_count} application(s) in tracker.\n")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
