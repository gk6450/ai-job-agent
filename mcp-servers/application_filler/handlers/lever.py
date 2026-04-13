"""Lever single-page application handler."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import BaseHandler

logger = logging.getLogger(__name__)


class LeverHandler(BaseHandler):
    """Fill Lever job forms without submitting."""

    ats_type = "lever"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        pages_filled = 1
        full_name = self.profile.get("name", "") or ""

        try:
            pairs = [
                ('input[name="name"]', full_name),
                ('input[name="email"]', self.profile.get("email", "") or ""),
                ('input[name="phone"]', self.profile.get("phone", "") or ""),
                ('input[name="org"]', self.profile.get("current_company", "") or ""),
                ('input[name="urls[LinkedIn]"]', self.profile.get("linkedin", "") or ""),
                ('input[name="urls[GitHub]"]', self.profile.get("github", "") or ""),
                ('input[name="urls[Portfolio]"]', self.profile.get("portfolio", "") or ""),
                ('input[placeholder*="LinkedIn" i]', self.profile.get("linkedin", "") or ""),
                ('input[placeholder*="GitHub" i]', self.profile.get("github", "") or ""),
            ]
            for sel, val in pairs:
                if not val:
                    continue
                try:
                    if await self._safe_fill(page, sel, val):
                        fields_filled.append(sel)
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"{sel}: {e}")

            if resume_path:
                for sel in ('input[type="file"]', 'input[name="resume"]'):
                    try:
                        if await self._upload_file(page, sel, resume_path):
                            fields_filled.append(f"resume:{sel}")
                            await self._short_wait(page)
                            break
                    except Exception as e:
                        errors.append(f"resume: {e}")

            if cover_letter_path:
                try:
                    p = Path(cover_letter_path)
                    text = (
                        p.read_text(encoding="utf-8", errors="replace")
                        if p.exists()
                        else "Please see attached cover letter."
                    )
                    if await self._safe_fill(page, 'textarea[name="comments"]', text):
                        fields_filled.append("comments")
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"cover letter textarea: {e}")

            success = bool(fields_filled)
        except Exception as e:
            logger.exception("Lever fill")
            errors.append(str(e))
            success = False

        return {
            "success": success,
            "pages_filled": pages_filled,
            "fields_filled": fields_filled,
            "errors": errors,
        }

    async def submit(self, page) -> dict:
        try:
            await self._short_wait(page)
            for sel in (
                'button[type="submit"]',
                ".template-btn-submit",
                'input[type="submit"]',
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Submitted Lever application"}
            return {"success": False, "message": "Lever submit not found"}
        except Exception as e:
            logger.exception("Lever submit")
            return {"success": False, "message": str(e)}
