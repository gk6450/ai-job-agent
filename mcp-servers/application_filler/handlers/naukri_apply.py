"""Naukri apply flow handler (assumes logged-in session)."""

from __future__ import annotations

import logging
import re

from .base import BaseHandler

logger = logging.getLogger(__name__)


class NaukriApplyHandler(BaseHandler):
    """Fill Naukri application steps without submitting."""

    ats_type = "naukri"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(450)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def _click_apply_if_present(self, page, errors: list) -> bool:
        try:
            for label in ("Apply", "Apply now", "Easy Apply"):
                btn = page.get_by_role("button", name=re.compile(re.escape(label), re.I))
                if await btn.count() > 0:
                    await btn.first.click()
                    await self._short_wait(page)
                    return True
        except Exception as e:
            errors.append(f"apply button: {e}")
        for sel in (
            'a:has-text("Apply")',
            'button:has-text("Apply")',
            ".apply-button",
            '[data-testid="apply-button"]',
        ):
            try:
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return True
            except Exception as e:
                errors.append(f"{sel}: {e}")
        return False

    async def _toggle_update_resume(self, page, fields_filled: list, errors: list) -> None:
        for sel in (
            'input[type="checkbox"][id*="update" i]',
            'label:has-text("Update resume") input',
            'input[name="isResumeChanged"]',
        ):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    fields_filled.append("update_resume_toggle")
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"resume toggle {sel}: {e}")

    async def _fill_common_fields(self, page, fields_filled: list, errors: list) -> None:
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        mapping = [
            ('input[name="name"]', self.profile.get("name", "") or ""),
            ('input[name="firstName"]', first),
            ('input[name="lastName"]', last),
            ('input[name="email"]', self.profile.get("email", "") or ""),
            ('input[type="email"]', self.profile.get("email", "") or ""),
            ('input[name="mobile"]', self.profile.get("phone", "") or ""),
            ('input[name="phone"]', self.profile.get("phone", "") or ""),
            ('input[id*="mob" i]', self.profile.get("phone", "") or ""),
            ('input[name="currentCity"]', self.profile.get("location", "") or ""),
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

    async def _answer_skill_questions(self, page, fields_filled: list, errors: list) -> None:
        try:
            y = str(self.profile.get("total_experience_years", "") or "")
            for sel in (
                'input[type="number"]',
                'input[name*="experience" i]',
                'input[id*="experience" i]',
                'input[name*="year" i]',
            ):
                try:
                    if y and await self._safe_fill(page, sel, y):
                        fields_filled.append(f"experience:{sel}")
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"experience {sel}: {e}")

            li = self.profile.get("linkedin", "") or ""
            if li:
                for sel in ('input[type="url"]', 'input[name*="linkedin" i]', 'input[id*="linkedin" i]'):
                    try:
                        if await self._safe_fill(page, sel, li):
                            fields_filled.append(f"linkedin:{sel}")
                            await self._short_wait(page)
                            break
                    except Exception as e:
                        errors.append(f"linkedin {sel}: {e}")

            yes_labels = await page.query_selector_all(
                'label:has-text("Yes"), span:has-text("Yes")'
            )
            for lab in yes_labels[:15]:
                try:
                    if not await lab.is_visible():
                        continue
                    await lab.click()
                    fields_filled.append("qual_yes")
                    await self._short_wait(page)
                except Exception as e:
                    errors.append(f"yes label: {e}")
        except Exception as e:
            errors.append(f"skill scan: {e}")

    async def _click_continue(self, page) -> bool:
        for sel in (
            'button:has-text("Continue")',
            'button:has-text("Save and Continue")',
            'button:has-text("Next")',
            'input[type="submit"][value="Continue"]',
        ):
            try:
                if await self._safe_click(page, sel):
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
            await self._click_apply_if_present(page, errors)
            await self._short_wait(page)

            max_steps = 20
            for step in range(max_steps):
                pages_filled = step + 1
                await self._toggle_update_resume(page, fields_filled, errors)
                await self._fill_common_fields(page, fields_filled, errors)

                if resume_path:
                    for sel in ('input[type="file"]', 'input[name="attachCV"]', 'input[id*="resume" i]'):
                        try:
                            if await self._upload_file(page, sel, resume_path):
                                fields_filled.append(f"resume:{sel}")
                                await self._short_wait(page)
                                break
                        except Exception as e:
                            errors.append(f"resume: {e}")

                await self._answer_skill_questions(page, fields_filled, errors)

                if not await self._click_continue(page):
                    break

            success = bool(fields_filled) or pages_filled > 0
        except Exception as e:
            logger.exception("Naukri fill")
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
                'button:has-text("Submit")',
                'button:has-text("Submit application")',
                'input[type="submit"][value="Submit"]',
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Clicked Naukri submit"}
            sub = page.get_by_role("button", name=re.compile(r"submit", re.I))
            if await sub.count() > 0:
                await sub.first.click()
                await self._short_wait(page)
                return {"success": True, "message": "Clicked submit (role)"}
            return {"success": False, "message": "Naukri submit not found"}
        except Exception as e:
            logger.exception("Naukri submit")
            return {"success": False, "message": str(e)}
