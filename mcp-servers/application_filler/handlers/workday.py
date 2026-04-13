"""Workday multi-page application handler."""

from __future__ import annotations

import logging

from .base import BaseHandler

logger = logging.getLogger(__name__)


class WorkdayHandler(BaseHandler):
    """Fill Workday candidate apply flow without final submit."""

    ats_type = "workday"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def _try_guest_or_continue(self, page, errors: list) -> None:
        for sel in (
            'a:has-text("Apply Manually")',
            'button:has-text("Apply as Guest")',
            'a:has-text("Create Account")',  # skip — prefer guest
            '[data-automation-id="applyManually"]',
            'button[data-automation-id="skipToApplication"]',
        ):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    if "Create Account" in (await el.inner_text()):
                        continue
                    await el.click()
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"workday guest flow {sel}: {e}")
        try:
            cont = await page.query_selector('button:has-text("Continue")')
            if cont and await cont.is_visible():
                await cont.click()
                await self._short_wait(page)
        except Exception as e:
            logger.debug(f"continue: {e}")

    async def _fill_by_automation_id(self, page, aid: str, value: str, fields_filled: list) -> bool:
        if not value:
            return False
        sel = f'[data-automation-id="{aid}"]'
        try:
            if await self._safe_fill(page, sel, value):
                fields_filled.append(aid)
                await self._short_wait(page)
                return True
        except Exception:
            pass
        return False

    async def _click_next(self, page) -> bool:
        for aid in ("bottom-navigation-next-button", "nextButton", "forwardButton"):
            sel = f'button[data-automation-id="{aid}"]'
            if await self._safe_click(page, sel):
                await self._short_wait(page)
                return True
        for text_sel in ('button:has-text("Next")', 'button:has-text("Save and Continue")'):
            if await self._safe_click(page, text_sel):
                await self._short_wait(page)
                return True
        return False

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        pages_filled = 0
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        try:
            await self._try_guest_or_continue(page, errors)

            max_pages = 30
            for step in range(max_pages):
                pages_filled = step + 1
                await self._short_wait(page)

                await self._fill_by_automation_id(
                    page, "legalNameSection_firstName", first, fields_filled
                )
                await self._fill_by_automation_id(
                    page, "legalNameSection_lastName", last, fields_filled
                )
                for aid, key in (
                    ("contactEmail", "email"),
                    ("contactPhone", "phone"),
                    ("addressSection_addressLine1", "location"),
                    ("addressSection_city", "location"),
                ):
                    await self._fill_by_automation_id(
                        page, aid, str(self.profile.get(key, "") or ""), fields_filled
                    )

                try:
                    if resume_path:
                        for sel in (
                            'input[data-automation-id="file-upload-input-ref"]',
                            'input[type="file"]',
                        ):
                            if await self._upload_file(page, sel, resume_path):
                                fields_filled.append("resume_upload")
                                await self._short_wait(page)
                                break
                except Exception as e:
                    errors.append(f"resume: {e}")

                if cover_letter_path:
                    try:
                        await self._upload_file(page, 'input[type="file"]', cover_letter_path)
                        fields_filled.append("cover_letter_upload")
                    except Exception as e:
                        errors.append(f"cover letter: {e}")

                resume_data = self._load_resume()
                try:
                    edu = resume_data.get("education") or []
                    if edu and isinstance(edu, list) and edu[0]:
                        e0 = edu[0] if isinstance(edu[0], dict) else {}
                        await self._fill_by_automation_id(
                            page,
                            "educationSection_schoolName",
                            str(e0.get("school", "") or e0.get("institution", "") or ""),
                            fields_filled,
                        )
                except Exception as e:
                    errors.append(f"education: {e}")

                try:
                    exp_y = self.profile.get("total_experience_years")
                    if exp_y is not None:
                        await self._fill_by_automation_id(
                            page,
                            "yearsOfExperience",
                            str(exp_y),
                            fields_filled,
                        )
                except Exception as e:
                    errors.append(f"experience: {e}")

                advanced = await self._click_next(page)
                if not advanced:
                    break

            success = bool(fields_filled) or pages_filled > 0
        except Exception as e:
            logger.exception("Workday fill")
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
                'button[data-automation-id="bottom-navigation-submit-button"]',
                'button[data-automation-id="submitButton"]',
                'button:has-text("Submit")',
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Clicked Workday submit"}
            return {"success": False, "message": "Workday submit not found"}
        except Exception as e:
            logger.exception("Workday submit")
            return {"success": False, "message": str(e)}
