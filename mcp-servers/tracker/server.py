import os
from datetime import datetime
from pathlib import Path

import gspread
from fastmcp import FastMCP
from google.oauth2.service_account import Credentials

mcp = FastMCP(
    "JobTracker",
    description="Track job applications in Google Sheets. Log applications, update statuses, query stats, and find pending follow-ups.",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COL_FOLLOWUP_DATE = "Follow-up Date"
STATUS_OFFER_RECEIVED = "Offer Received"
STATUS_OFFER_ACCEPTED = "Offer Accepted"
MSG_NO_APPLICATIONS = "No applications tracked yet."

COLUMNS = [
    "ID",
    "Company",
    "Role",
    "URL",
    "Platform",
    "Status",
    "Date Applied",
    "Last Updated",
    COL_FOLLOWUP_DATE,
    "Resume Version",
    "Cover Letter",
    "Notes",
]

VALID_STATUSES = [
    "Applied",
    "Viewed",
    "Interview Scheduled",
    "Interview Completed",
    "Assessment Received",
    "Assessment Submitted",
    STATUS_OFFER_RECEIVED,
    STATUS_OFFER_ACCEPTED,
    "Offer Declined",
    "Rejected",
    "Withdrawn",
    "Followed Up",
    "Follow-up Needed",
    "No Response",
    "Skipped",
]


def _get_creds_path() -> Path:
    """Resolve the service account credentials file path."""
    env_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if env_path:
        return Path(env_path)
    candidates = [
        Path(__file__).parent.parent.parent / "data" / "service-account.json",
        Path(__file__).parent / "service-account.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Google service account JSON not found. "
        "Place it at data/service-account.json or set GOOGLE_SERVICE_ACCOUNT_FILE env var."
    )


def _get_sheet_name() -> str:
    return os.environ.get("TRACKER_SHEET_NAME", "Job Application Tracker")


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(str(_get_creds_path()), scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    client = _get_client()
    sheet_name = _get_sheet_name()
    try:
        spreadsheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        raise ValueError(
            f"Spreadsheet '{sheet_name}' not found. "
            f"Create it and share with the service account email."
        )
    return spreadsheet.sheet1


def _next_id(worksheet: gspread.Worksheet) -> str:
    """Generate the next application ID like APP-001, APP-002, etc."""
    records = worksheet.get_all_records()
    if not records:
        return "APP-001"
    ids = [r.get("ID", "") for r in records if str(r.get("ID", "")).startswith("APP-")]
    if not ids:
        return "APP-001"
    max_num = max(int(i.split("-")[1]) for i in ids)
    return f"APP-{max_num + 1:03d}"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _find_row_by_id(worksheet: gspread.Worksheet, app_id: str) -> int:
    """Find the row number (1-indexed) for a given application ID."""
    col_values = worksheet.col_values(1)
    for i, val in enumerate(col_values):
        if val == app_id:
            return i + 1
    raise ValueError(f"Application '{app_id}' not found.")


@mcp.tool()
def log_application(
    company: str,
    role: str,
    url: str = "",
    platform: str = "",
    status: str = "Applied",
    notes: str = "",
    resume_version: str = "",
    cover_letter: str = "",
) -> str:
    """Log a new job application to the Google Sheet tracker.

    Args:
        company: Company name
        role: Job title/role
        url: Job listing URL
        platform: Platform where the job was found (LinkedIn, Naukri, Indeed, etc.)
        status: Application status (default: Applied)
        notes: Any additional notes
        resume_version: Path or identifier of the tailored resume used
        cover_letter: Path or identifier of the cover letter used
    """
    if status not in VALID_STATUSES:
        return f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}"

    ws = _get_worksheet()
    app_id = _next_id(ws)
    now = _now()

    followup_date = ""
    if status == "Applied":
        from datetime import timedelta  # noqa: F811
        followup_dt = datetime.now() + timedelta(days=7)
        followup_date = followup_dt.strftime("%Y-%m-%d")

    row = [
        app_id,
        company,
        role,
        url,
        platform,
        status,
        now,
        now,
        followup_date,
        resume_version,
        cover_letter,
        notes,
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return f"Logged: {app_id} | {company} - {role} | Status: {status}"


@mcp.tool()
def update_status(application_id: str, new_status: str, notes: str = "") -> str:
    """Update the status of an existing application.

    Args:
        application_id: The application ID (e.g., APP-001)
        new_status: New status value
        notes: Optional notes to append
    """
    if new_status not in VALID_STATUSES:
        return f"Invalid status '{new_status}'. Valid: {', '.join(VALID_STATUSES)}"

    ws = _get_worksheet()
    row_num = _find_row_by_id(ws, application_id)
    now = _now()

    ws.update_cell(row_num, COLUMNS.index("Status") + 1, new_status)
    ws.update_cell(row_num, COLUMNS.index("Last Updated") + 1, now)

    if new_status in ("Rejected", STATUS_OFFER_RECEIVED, STATUS_OFFER_ACCEPTED, "Withdrawn"):
        ws.update_cell(row_num, COLUMNS.index(COL_FOLLOWUP_DATE) + 1, "")

    if notes:
        existing = ws.cell(row_num, COLUMNS.index("Notes") + 1).value or ""
        updated_notes = f"{existing} | {now}: {notes}" if existing else f"{now}: {notes}"
        ws.update_cell(row_num, COLUMNS.index("Notes") + 1, updated_notes)

    return f"Updated {application_id} to '{new_status}'"


@mcp.tool()
def get_all_applications(status_filter: str = "") -> str:
    """Get all tracked applications, optionally filtered by status.

    Args:
        status_filter: Filter by status (e.g., 'Applied', 'Interview Scheduled'). Leave empty for all.
    """
    ws = _get_worksheet()
    records = ws.get_all_records()

    if not records:
        return MSG_NO_APPLICATIONS

    if status_filter:
        records = [r for r in records if r.get("Status", "").lower() == status_filter.lower()]
        if not records:
            return f"No applications with status '{status_filter}'."

    lines = []
    for r in records:
        line = (
            f"{r.get('ID', '?')} | {r.get('Company', '?')} - {r.get('Role', '?')} | "
            f"Status: {r.get('Status', '?')} | Applied: {r.get('Date Applied', '?')}"
        )
        lines.append(line)

    return f"Found {len(lines)} application(s):\n" + "\n".join(lines)


@mcp.tool()
def get_pending_followups(days_threshold: int = 7) -> str:
    """Get applications that need follow-up (no response within N days).

    Args:
        days_threshold: Number of days without response before flagging (default: 7)
    """
    ws = _get_worksheet()
    records = ws.get_all_records()

    if not records:
        return MSG_NO_APPLICATIONS

    today = datetime.now()
    pending = []

    terminal_statuses = {
        "Rejected", STATUS_OFFER_RECEIVED, STATUS_OFFER_ACCEPTED,
        "Offer Declined", "Withdrawn", "Skipped",
    }

    for r in records:
        status = r.get("Status", "")
        if status in terminal_statuses:
            continue

        followup_date_str = r.get(COL_FOLLOWUP_DATE, "")
        if not followup_date_str:
            continue

        try:
            followup_date = datetime.strptime(str(followup_date_str).strip(), "%Y-%m-%d")
        except ValueError:
            continue

        if followup_date <= today:
            days_overdue = (today - followup_date).days
            pending.append(
                f"{r.get('ID', '?')} | {r.get('Company', '?')} - {r.get('Role', '?')} | "
                f"Applied: {r.get('Date Applied', '?')} | Overdue by {days_overdue} day(s)"
            )

    if not pending:
        return "No pending follow-ups. All caught up!"

    return f"{len(pending)} application(s) need follow-up:\n" + "\n".join(pending)


@mcp.tool()
def get_stats() -> str:
    """Get a summary of application statistics (total, by status, etc.)."""
    ws = _get_worksheet()
    records = ws.get_all_records()

    if not records:
        return MSG_NO_APPLICATIONS

    total = len(records)
    by_status: dict[str, int] = {}
    for r in records:
        s = r.get("Status", "Unknown")
        by_status[s] = by_status.get(s, 0) + 1

    lines = [f"Total applications: {total}", ""]
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"  {status}: {count}")

    active = total - by_status.get("Rejected", 0) - by_status.get("Withdrawn", 0) - by_status.get("Skipped", 0)
    lines.append(f"\nActive applications: {active}")

    return "\n".join(lines)


@mcp.tool()
def initialize_sheet() -> str:
    """Initialize the Google Sheet with header columns. Run this once when setting up."""
    ws = _get_worksheet()
    existing = ws.row_values(1)
    if existing and existing[0] == "ID":
        return "Sheet already initialized with headers."

    ws.update("A1", [COLUMNS], value_input_option="USER_ENTERED")

    ws.format("A1:L1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
        "horizontalAlignment": "CENTER",
    })

    return f"Sheet initialized with {len(COLUMNS)} columns: {', '.join(COLUMNS)}"


if __name__ == "__main__":
    mcp.run()
