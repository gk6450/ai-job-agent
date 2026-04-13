"""Base handler for application form filling."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


class BaseHandler(ABC):
    """Abstract base for all ATS form handlers."""

    ats_type: str = "unknown"

    def __init__(self):
        self.profile = self._load_profile()

    def _load_profile(self) -> dict:
        profile_path = DATA_DIR / "profile.json"
        if profile_path.exists():
            return json.loads(profile_path.read_text())
        logger.warning("profile.json not found")
        return {}

    def _load_resume(self) -> dict:
        resume_path = DATA_DIR / "base_resume.json"
        if resume_path.exists():
            return json.loads(resume_path.read_text())
        return {}

    async def _safe_fill(self, page, selector: str, value: str) -> bool:
        """Safely fill a form field, returning True if successful."""
        try:
            el = await page.query_selector(selector)
            if el:
                await el.click()
                await el.fill("")
                await el.fill(value)
                return True
        except Exception as e:
            logger.debug(f"Could not fill {selector}: {e}")
        return False

    async def _safe_click(self, page, selector: str) -> bool:
        """Safely click a button/element."""
        try:
            el = await page.query_selector(selector)
            if el:
                await el.click()
                return True
        except Exception as e:
            logger.debug(f"Could not click {selector}: {e}")
        return False

    async def _safe_select(self, page, selector: str, value: str) -> bool:
        """Safely select an option from a dropdown."""
        try:
            el = await page.query_selector(selector)
            if el:
                await page.select_option(selector, value=value)
                return True
        except Exception:
            pass
        try:
            await page.select_option(selector, label=value)
            return True
        except Exception as e:
            logger.debug(f"Could not select {selector}: {e}")
        return False

    async def _upload_file(self, page, selector: str, file_path: str) -> bool:
        """Upload a file to a file input."""
        try:
            el = await page.query_selector(selector)
            if el:
                await el.set_input_files(file_path)
                return True
        except Exception as e:
            logger.debug(f"Could not upload to {selector}: {e}")
        return False

    @abstractmethod
    async def fill(
        self,
        page,
        resume_path: str = "",
        cover_letter_path: str = "",
    ) -> dict:
        """Fill the application form.

        Returns:
            dict with keys: success (bool), pages_filled (int), fields_filled (list[str]), errors (list[str])
        """
        ...

    @abstractmethod
    async def submit(self, page) -> dict:
        """Submit the application (only after user approval).

        Returns:
            dict with keys: success (bool), message (str)
        """
        ...
