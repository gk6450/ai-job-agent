import json
import logging
from pathlib import Path

from fastmcp import FastMCP

from .detector import detect_ats_type
from .screenshot import capture_page, list_screenshots, screenshot_to_base64
from .handlers import get_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "ApplicationFiller",
    description="Fill job application forms on major ATS platforms (Workday, Greenhouse, Lever, LinkedIn, Naukri, Indeed, iCIMS). Screenshots each page for approval before submission.",
)

# Persistent browser sessions for multi-step flows
_active_sessions: dict[str, dict] = {}


@mcp.tool()
async def detect_ats(url: str) -> str:
    """Identify the Applicant Tracking System (ATS) type from a job URL.

    Args:
        url: The job application URL
    """
    ats_type = await detect_ats_type(url)
    descriptions = {
        "workday": "Workday -- multi-page enterprise ATS, common at large companies",
        "greenhouse": "Greenhouse -- single-page form, popular with tech startups",
        "lever": "Lever -- simple single-page form with resume upload",
        "linkedin": "LinkedIn Easy Apply -- multi-step modal within LinkedIn",
        "naukri": "Naukri -- India's largest job portal",
        "indeed": "Indeed -- multi-step application flow",
        "icims": "iCIMS -- enterprise ATS with account creation",
        "unknown": "Unknown ATS -- will use generic form-filling approach",
    }
    desc = descriptions.get(ats_type, f"Detected as: {ats_type}")
    return f"ATS Type: {ats_type}\n{desc}"


@mcp.tool()
async def fill_application(
    url: str,
    application_id: str,
    resume_path: str = "",
    cover_letter_path: str = "",
) -> str:
    """Navigate to a job application URL, detect ATS type, and fill the form.

    Does NOT submit -- takes screenshots for user approval first.

    Args:
        url: The job application URL
        application_id: Unique application ID (e.g., APP-001)
        resume_path: Path to the tailored resume PDF to upload
        cover_letter_path: Path to the cover letter PDF to upload
    """
    from playwright.async_api import async_playwright

    ats_type = await detect_ats_type(url)
    handler = get_handler(ats_type)

    logger.info(f"Filling application {application_id} on {ats_type}: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            result = await handler.fill(
                page=page,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
            )

            # Take final screenshot
            screenshot_path = await capture_page(page, application_id, page_num=result.get("pages_filled", 1))

            # Store browser state for later submission
            _active_sessions[application_id] = {
                "ats_type": ats_type,
                "url": url,
                "handler_type": handler.ats_type,
            }

            lines = [
                f"Application form filled for {application_id}",
                f"ATS: {ats_type}",
                f"Pages filled: {result.get('pages_filled', 0)}",
                f"Fields filled: {', '.join(result.get('fields_filled', []))}",
            ]
            if result.get("errors"):
                lines.append(f"Warnings: {', '.join(result['errors'])}")
            lines.append(f"\nScreenshot: {screenshot_path}")
            lines.append("\nReview the screenshot and approve submission with submit_application()")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error filling application: {e}")
            try:
                await capture_page(page, application_id, page_num=0)
            except Exception:
                pass
            return f"Error filling application for {application_id}: {e}"
        finally:
            await browser.close()


@mcp.tool()
async def submit_application(application_id: str) -> str:
    """Submit a previously filled application after user approval.

    ONLY call this after the user has reviewed and approved the screenshots.

    Args:
        application_id: The application ID that was previously filled
    """
    if application_id not in _active_sessions:
        return (
            f"No active session for {application_id}. "
            "The browser session may have expired. "
            "Please run fill_application() again."
        )

    session = _active_sessions[application_id]
    from playwright.async_api import async_playwright

    ats_type = session["ats_type"]
    handler = get_handler(ats_type)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        try:
            await page.goto(session["url"], wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # Re-fill and then submit
            await handler.fill(page=page)
            result = await handler.submit(page)

            await capture_page(page, application_id, page_num=99)

            del _active_sessions[application_id]

            if result.get("success"):
                return f"Application {application_id} submitted successfully! {result.get('message', '')}"
            else:
                return f"Submission may have failed for {application_id}: {result.get('message', 'Unknown error')}"

        except Exception as e:
            return f"Error submitting application {application_id}: {e}"
        finally:
            await browser.close()


@mcp.tool()
async def get_application_screenshot(application_id: str, page_num: int = 1) -> str:
    """Get the screenshot path for an application form page.

    Args:
        application_id: The application ID
        page_num: Page number (1-based)
    """
    screenshots = list_screenshots(application_id)
    if not screenshots:
        return f"No screenshots found for {application_id}"

    lines = [f"Screenshots for {application_id}:"]
    for ss in screenshots:
        lines.append(f"  - {ss.name} ({ss.stat().st_size / 1024:.1f} KB)")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
