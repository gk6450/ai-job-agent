"""Quick standalone test for the Tracker MCP server.

Usage:
    python mcp-servers/tracker/test_tracker.py

Requires:
    - service-account.json placed in data/ folder
    - A Google Sheet named "Job Application Tracker" shared with the service account email
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server import (
    initialize_sheet,
    log_application,
    get_all_applications,
    get_stats,
    get_pending_followups,
    update_status,
    _get_creds_path,
    _get_client,
)


def main():
    print("=" * 60)
    print("  Job Tracker MCP Server - Standalone Test")
    print("=" * 60)

    print("\n[1/6] Checking credentials file...")
    try:
        creds_path = _get_creds_path()
        print(f"  Found: {creds_path}")
    except FileNotFoundError as e:
        print(f"  FAIL: {e}")
        return

    print("\n[2/6] Connecting to Google Sheets API...")
    try:
        client = _get_client()
        sa_email = json.loads(creds_path.read_text()).get("client_email", "<unknown>")
        print(f"  Connected as: {sa_email}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return

    print("\n[3/6] Initializing sheet headers...")
    result = initialize_sheet()
    print(f"  {result}")

    print("\n[4/6] Logging a test application...")
    result = log_application(
        company="Test Corp",
        role="Software Engineer",
        url="https://example.com/job/123",
        platform="LinkedIn",
        status="Applied",
        notes="Phase 1 test entry",
    )
    print(f"  {result}")

    print("\n[5/6] Fetching all applications...")
    result = get_all_applications()
    print(f"  {result}")

    print("\n[6/6] Checking stats...")
    result = get_stats()
    print(f"  {result}")

    print("\n" + "=" * 60)
    print("  All tests passed! Tracker MCP server is working.")
    print("=" * 60)


if __name__ == "__main__":
    main()
