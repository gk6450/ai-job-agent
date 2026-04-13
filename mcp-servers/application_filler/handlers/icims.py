"""iCIMS multi-page application handler."""

from __future__ import annotations

import logging

from .base import BaseHandler

logger = logging.getLogger(__name__)


class ICIMSHandler(BaseHandler):
    """Fill iCIMS candidate forms without submitting."""

    ats_type = "icims"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    def _frames(self, page):
        return [page] + list(page.frames)

    async def _try_skip_signin(self, page, errors: list) -> None:
        for sel in (
            'a:has-text("Apply")',
            'button:has-text("Apply")',
            'a:has-text("Continue as guest")',
            'button:has-text("Create an account")',  # avoid
        ):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    if "Create an account" in (await el.inner_text()):
                        continue
                    await el.click()
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"icims landing {sel}: {e}")

    async def _fill_personal(self, page, fields_filled: list, errors: list) -> None:
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        pairs = [
            ('input[name="firstName"]', first),
            ('input[name="lastName"]', last),
            ('input[id*="firstName" i]', first),
            ('input[id*="lastName" i]', last),
            ('input[name="email"]', self.profile.get("email", "") or ""),
            ('input[type="email"]', self.profile.get("email", "") or ""),
            ('input[name="phone"]', self.profile.get("phone", "") or ""),
            ('input[type="tel"]', self.profile.get("phone", "") or ""),
            ('input[name="addressLine1"]', self.profile.get("location", "") or ""),
            ('input[name="city"]', self.profile.get("location", "") or ""),
        ]
        for fr in self._frames(page):
            for sel, val in pairs:
                if not val:
                    continue
                try:
                    if await self._safe_fill(fr, sel, val):
                        fields_filled.append(f"{sel}")
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"{sel}: {e}")

    async def _fill_work_education(self, page, fields_filled: list, errors: list) -> None:
        resume_data = self._load_resume()
        try:
            exp = resume_data.get("experience") or resume_data.get("work_history") or []
            if exp and isinstance(exp, list) and isinstance(exp[0], dict):
                e0 = exp[0]
                title = str(e0.get("title", "") or e0.get("position", "") or "")
                company = str(e0.get("company", "") or e0.get("employer", "") or "")
                for fr in self._frames(page):
                    await self._safe_fill(fr, 'input[name="jobTitle"]', title)
                    await self._safe_fill(fr, 'input[name="employer"]', company)
                    if title or company:
                        fields_filled.append("work_history")
                    await self._short_wait(page)
        except Exception as e:
            errors.append(f"work history: {e}")

        try:
            edu = resume_data.get("education") or []
            if edu and isinstance(edu, list) and isinstance(edu[0], dict):
                e0 = edu[0]
                school = str(e0.get("school", "") or e0.get("institution", "") or "")
                for fr in self._frames(page):
                    await self._safe_fill(fr, 'input[name="schoolName"]', school)
                    await self._safe_fill(fr, 'input[name="institution"]', school)
                    if school:
                        fields_filled.append("education")
                    await self._short_wait(page)
        except Exception as e:
            errors.append(f"education: {e}")

    async def _upload_resume_all_frames(self, page, resume_path: str, fields_filled: list, errors: list) -> None:
        if not resume_path:
            return
        for fr in self._frames(page):
            try:
                if await self._upload_file(fr, 'input[type="file"]', resume_path):
                    fields_filled.append("resume_upload")
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"resume: {e}")

    async def _click_next(self, page) -> bool:
        for fr in self._frames(page):
            for sel in (
                'button:has-text("Next")',
                'input[type="submit"][value="Next"]',
                'a:has-text("Next")',
                'button:has-text("Save and Continue")',
            ):
                try:
                    if await self._safe_click(fr, sel):
                        await self._short_wait(page)
                        return True
                except Exception:
                    continue
        return False

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        pages_filled = 0

        try:
            await self._try_skip_signin(page, errors)

            max_pages = 25
            for step in range(max_pages):
                pages_filled = step + 1
                await self._fill_personal(page, fields_filled, errors)
                await self._fill_work_education(page, fields_filled, errors)
                await self._upload_resume_all_frames(page, resume_path, fields_filled, errors)
                if cover_letter_path:
                    for fr in self._frames(page):
                        try:
                            if await self._upload_file(fr, 'input[type="file"]', cover_letter_path):
                                fields_filled.append("cover_letter")
                                break
                        except Exception as e:
                            errors.append(f"cover: {e}")

                if not await self._click_next(page):
                    break

            success = bool(fields_filled) or pages_filled > 0
        except Exception as e:
            logger.exception("iCIMS fill")
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
            for fr in self._frames(page):
                for sel in (
                    'button:has-text("Submit")',
                    'input[type="submit"][value="Submit"]',
                    'button[id*="submit" i]',
                ):
                    if await self._safe_click(fr, sel):
                        await self._short_wait(page)
                        return {"success": True, "message": "Clicked iCIMS submit"}
            return {"success": False, "message": "iCIMS submit not found"}
        except Exception as e:
            logger.exception("iCIMS submit")
            return {"success": False, "message": str(e)}
