import json
import logging
from pathlib import Path

from fastmcp import FastMCP

from .drafter import draft_followup_email, draft_thank_you_email
from .sender import send_email
from .scheduler import get_due_followups

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "FollowUp",
    description="Manage follow-up emails for job applications. Draft, review, and send follow-up or thank-you emails based on configurable policies.",
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PREFS_PATH = DATA_DIR / "preferences.json"


def _load_preferences() -> dict:
    if PREFS_PATH.exists():
        return json.loads(PREFS_PATH.read_text())
    return {}


def _load_profile() -> dict:
    profile_path = DATA_DIR / "profile.json"
    if profile_path.exists():
        return json.loads(profile_path.read_text())
    return {}


def _get_tracker_data() -> list[dict]:
    try:
        import sys
        tracker_path = Path(__file__).parent.parent / "tracker"
        sys.path.insert(0, str(tracker_path))
        from server import _get_worksheet
        ws = _get_worksheet()
        return ws.get_all_records()
    except Exception as e:
        logger.warning(f"Could not load tracker data: {e}")
        return []


@mcp.tool()
async def check_due_followups() -> str:
    """Check which applications are due for follow-up emails.

    Uses the follow-up schedule from preferences.json (default: 7 days first, 14 days second).
    """
    applications = _get_tracker_data()
    if not applications:
        return "No tracked applications found."

    due = get_due_followups(applications)
    if not due:
        return "No follow-ups due. All caught up!"

    prefs = _load_preferences()
    policy = prefs.get("followup_policy_default", "draft_for_review")

    lines = [f"{len(due)} follow-up(s) due (policy: {policy}):\n"]
    for app in due:
        lines.append(
            f"- {app.get('ID', '?')} | {app.get('Company', '?')} - {app.get('Role', '?')}\n"
            f"  Applied: {app.get('Date Applied', '?')} ({app['days_since_applied']} days ago)\n"
            f"  Follow-up #{app['followup_number']}"
        )

    return "\n".join(lines)


@mcp.tool()
async def draft_followup(application_id: str) -> str:
    """Draft a follow-up email for a specific application.

    Args:
        application_id: The application ID (e.g., APP-001)
    """
    applications = _get_tracker_data()
    app = next((a for a in applications if a.get("ID") == application_id), None)

    if not app:
        return f"Application {application_id} not found."

    profile = _load_profile()
    candidate_name = profile.get("name", "")

    status = app.get("Status", "")
    followup_num = 2 if status == "Followed Up" else 1

    result = await draft_followup_email(
        company=app.get("Company", ""),
        role=app.get("Role", ""),
        applied_date=app.get("Date Applied", ""),
        candidate_name=candidate_name,
        followup_number=followup_num,
    )

    return (
        f"Draft follow-up for {application_id} ({app.get('Company', '')} - {app.get('Role', '')}):\n\n"
        f"Subject: {result['subject']}\n\n"
        f"{result['body']}\n\n"
        f"---\nTo send, use send_followup() with the application ID and email body."
    )


@mcp.tool()
async def send_followup(
    application_id: str,
    email_body: str,
    recipient_email: str = "",
) -> str:
    """Send a follow-up email for an application.

    The follow-up policy is checked before sending:
    - 'remind_only': Won't send, just returns a reminder
    - 'draft_for_review': Requires this explicit send call (default)
    - 'auto_send': Sends automatically (used by scheduled checks)

    Args:
        application_id: The application ID
        email_body: The email body to send
        recipient_email: Recipient email. If empty, will try to find from application URL.
    """
    applications = _get_tracker_data()
    app = next((a for a in applications if a.get("ID") == application_id), None)

    if not app:
        return f"Application {application_id} not found."

    prefs = _load_preferences()
    policy = prefs.get("followup_policy_default", "draft_for_review")

    if policy == "remind_only":
        return (
            f"Follow-up policy is 'remind_only'. Email NOT sent.\n"
            f"Reminder: Follow up with {app.get('Company', '')} about {app.get('Role', '')} position."
        )

    if not recipient_email:
        return (
            "No recipient email provided. Please specify the recipient email address.\n"
            "Tip: Check the original job listing or company careers page for the contact email."
        )

    company = app.get("Company", "")
    role = app.get("Role", "")
    subject = f"Following Up - {role} Application"

    result = send_email(to=recipient_email, subject=subject, body=email_body)

    if result["success"]:
        return (
            f"Follow-up email sent to {recipient_email} for {application_id}.\n"
            f"Message ID: {result['message_id']}\n"
            f"Don't forget to update the tracker status to 'Followed Up'."
        )
    else:
        return f"Failed to send email: {result['error']}"


@mcp.tool()
async def draft_thank_you(
    application_id: str,
    interviewer_name: str = "",
    discussion_points: str = "",
) -> str:
    """Draft a post-interview thank-you email.

    Args:
        application_id: The application ID
        interviewer_name: Name of the interviewer (if known)
        discussion_points: Key topics discussed during the interview
    """
    applications = _get_tracker_data()
    app = next((a for a in applications if a.get("ID") == application_id), None)

    if not app:
        return f"Application {application_id} not found."

    profile = _load_profile()

    result = await draft_thank_you_email(
        company=app.get("Company", ""),
        role=app.get("Role", ""),
        interviewer_name=interviewer_name,
        discussion_points=discussion_points,
        candidate_name=profile.get("name", ""),
    )

    return (
        f"Thank-you email draft for {application_id} ({app.get('Company', '')} - {app.get('Role', '')}):\n\n"
        f"Subject: {result['subject']}\n\n"
        f"{result['body']}\n\n"
        f"---\nTo send, use send_followup() with the email body and recipient email."
    )


if __name__ == "__main__":
    mcp.run()
