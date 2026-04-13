"""Greenhouse single-page application handler."""

from __future__ import annotations

import logging

from .base import BaseHandler

logger = logging.getLogger(__name__)


class GreenhouseHandler(BaseHandler):
    """Fill Greenhouse forms without submitting."""

    ats_type = "greenhouse"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(350)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        pages_filled = 1
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        try:
            mapping = [
                ("#first_name", first),
                ("#last_name", last),
                ("#email", self.profile.get("email", "") or ""),
                ("#phone", self.profile.get("phone", "") or ""),
                ('input[name="first_name"]', first),
                ('input[name="last_name"]', last),
                ('input[name="email"]', self.profile.get("email", "") or ""),
                ('input[name="phone"]', self.profile.get("phone", "") or ""),
            ]
            for sel, val in mapping:
                if not val:
                    continue
                try:
                    if await self._safe_fill(page, sel, val):
                        fields_filled.append(sel)
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"{sel}: {e}")

            if resume_path:
                for sel in ('input[type="file"]', "#resume", 'input[name="resume"]'):
                    try:
                        if await self._upload_file(page, sel, resume_path):
                            fields_filled.append(f"resume:{sel}")
                            await self._short_wait(page)
                            break
                    except Exception as e:
                        errors.append(f"resume {sel}: {e}")

            if cover_letter_path:
                for sel in ('input[name="cover_letter"]', 'input[id*="cover" i]'):
                    try:
                        if await self._upload_file(page, sel, cover_letter_path):
                            fields_filled.append(f"cover:{sel}")
                            await self._short_wait(page)
                            break
                    except Exception as e:
                        errors.append(f"cover {sel}: {e}")

            try:
                custom = await page.query_selector_all(
                    "#application_form textarea, form#application_form textarea, .field textarea"
                )
                for ta in custom[:5]:
                    try:
                        if not await ta.is_visible():
                            continue
                        ph = (await ta.get_attribute("placeholder")) or ""
                        name = (await ta.get_attribute("name")) or ""
                        blob = f"{ph} {name}".lower()
                        ans = ""
                        if "linkedin" in blob:
                            ans = self.profile.get("linkedin", "") or ""
                        elif "github" in blob:
                            ans = self.profile.get("github", "") or ""
                        elif "why" in blob or "interest" in blob:
                            ans = f"Interested in this role. Experience: {self.profile.get('current_title', '')}."
                        if ans:
                            await ta.fill(ans)
                            fields_filled.append("custom_textarea")
                            await self._short_wait(page)
                    except Exception as e:
                        errors.append(f"custom q: {e}")
            except Exception as e:
                errors.append(f"custom scan: {e}")

            success = bool(fields_filled)
        except Exception as e:
            logger.exception("Greenhouse fill")
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
                "#submit_app",
                'button[type="submit"]',
                'input[type="submit"]',
                "#application_submit",
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Submitted Greenhouse application"}
            return {"success": False, "message": "Greenhouse submit control not found"}
        except Exception as e:
            logger.exception("Greenhouse submit")
            return {"success": False, "message": str(e)}
