"""Screenshot utility for application form pages."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path(__file__).parent.parent.parent / "generated" / "screenshots"


async def capture_page(page, application_id: str, page_num: int = 1) -> Path:
    """Capture a full-page screenshot.

    Args:
        page: Playwright page object
        application_id: Application ID (e.g., APP-001)
        page_num: Page number in multi-page forms

    Returns:
        Path to the saved screenshot
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{application_id}_page{page_num}.png"
    filepath = SCREENSHOTS_DIR / filename

    await page.screenshot(path=str(filepath), full_page=True)
    logger.info(f"Screenshot saved: {filepath}")

    return filepath


async def capture_element(page, selector: str, application_id: str, label: str = "form") -> Path:
    """Capture a screenshot of a specific element."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{application_id}_{label}.png"
    filepath = SCREENSHOTS_DIR / filename

    element = await page.query_selector(selector)
    if element:
        await element.screenshot(path=str(filepath))
    else:
        await page.screenshot(path=str(filepath), full_page=True)

    logger.info(f"Element screenshot saved: {filepath}")
    return filepath


def screenshot_to_base64(filepath: Path) -> str:
    """Convert a screenshot file to base64 string for sending via chat."""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def list_screenshots(application_id: str) -> list[Path]:
    """List all screenshots for an application."""
    if not SCREENSHOTS_DIR.exists():
        return []
    return sorted(SCREENSHOTS_DIR.glob(f"{application_id}_*.png"))
