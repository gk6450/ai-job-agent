"""Indeed multi-step apply flow handler."""

from __future__ import annotations

import logging
import re

from .base import BaseHandler

logger = logging.getLogger(__name__)


class IndeedApplyHandler(BaseHandler):
    """Fill Indeed application wizard without submitting."""

    ats_type = "indeed"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def _fill_contact(self, page, fields_filled: list, errors: list) -> None:
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        pairs = [
            ('input[name="firstName"]', first),
            ('input[name="lastName"]', last),
            ('input[id*="firstname" i]', first),
            ('input[id*="lastname" i]', last),
            ('input[name="email"]', self.profile.get("email", "") or ""),
            ('input[type="email"]', self.profile.get("email", "") or ""),
            ('input[name="phone"]', self.profile.get("phone", "") or ""),
            ('input[type="tel"]', self.profile.get("phone", "") or ""),
            ('input[name="phoneNumber"]', self.profile.get("phone", "") or ""),
            ('input[name="location"]', self.profile.get("location", "") or ""),
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

    async def _upload_resume(self, page, resume_path: str, fields_filled: list, errors: list) -> None:
        if not resume_path:
            return
        for sel in (
            'input[type="file"]',
            'input[data-testid="FileResumeInput"]',
            'input[aria-label*="resume" i]',
        ):
            try:
                if await self._upload_file(page, sel, resume_path):
                    fields_filled.append(f"resume:{sel}")
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"resume {sel}: {e}")

    async def _answer_qualification_questions(self, page, fields_filled: list, errors: list) -> None:
        try:
            selects = await page.query_selector_all("select")
            for sel_el in selects[:15]:
                try:
                    if not await sel_el.is_visible():
                        continue
                    sid = await sel_el.get_attribute("id") or ""
                    name = await sel_el.get_attribute("name") or ""
                    blob = f"{sid} {name}".lower()
                    if "year" in blob or "experience" in blob:
                        y = str(self.profile.get("total_experience_years", "") or "")
                        if y:
                            await self._safe_select(page, f"#{sid}" if sid else f"select[name='{name}']", y)
                            fields_filled.append("select_experience")
                    else:
                        await self._safe_select(page, f"#{sid}" if sid else f"select[name='{name}']", "Yes")
                        fields_filled.append("select_yes")
                    await self._short_wait(page)
                except Exception as e:
                    errors.append(f"select: {e}")

            radios = await page.query_selector_all('div[data-testid*="question"] input[type="radio"], fieldset input[type="radio"]')
            for r in radios[:40]:
                try:
                    if not await r.is_visible():
                        continue
                    val = await r.get_attribute("value")
                    if val and val.lower() in ("yes", "y", "true", "1"):
                        await r.click()
                        fields_filled.append("radio_yes")
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"radio: {e}")

            textareas = await page.query_selector_all("textarea")
            for ta in textareas[:8]:
                try:
                    if not await ta.is_visible():
                        continue
                    label = (await ta.get_attribute("aria-label")) or ""
                    if "why" in label.lower() or "summary" in label.lower():
                        snippet = f"{self.profile.get('current_title', '')} at {self.profile.get('current_company', '')}"
                        await ta.fill(f"I am interested in this role. {snippet}".strip())
                        fields_filled.append("textarea_why")
                        await self._short_wait(page)
                except Exception as e:
                    errors.append(f"textarea: {e}")
        except Exception as e:
            errors.append(f"qualification scan: {e}")

    async def _click_continue(self, page) -> bool:
        try:
            c = page.get_by_role("button", name=re.compile(r"continue|next", re.I))
            if await c.count() > 0:
                for i in range(await c.count()):
                    el = c.nth(i)
                    if await el.is_visible():
                        t = (await el.inner_text()).lower()
                        if "submit" in t:
                            continue
                        await el.click()
                        await self._short_wait(page)
                        return True
        except Exception as e:
            logger.debug(f"role continue: {e}")
        for sel in (
            'button:has-text("Continue")',
            'button[data-testid="continue-button"]',
            'button:has-text("Continue applying")',
        ):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
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
            max_steps = 25
            for step in range(max_steps):
                pages_filled = step + 1
                await self._fill_contact(page, fields_filled, errors)
                await self._upload_resume(page, resume_path, fields_filled, errors)
                if cover_letter_path:
                    try:
                        await self._upload_file(page, 'input[type="file"]', cover_letter_path)
                        fields_filled.append("cover_letter_file")
                    except Exception as e:
                        errors.append(f"cover: {e}")
                await self._answer_qualification_questions(page, fields_filled, errors)

                if not await self._click_continue(page):
                    break

            success = bool(fields_filled) or pages_filled > 0
        except Exception as e:
            logger.exception("Indeed fill")
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
                'button:has-text("Submit your application")',
                'button:has-text("Submit application")',
                'button[data-testid="submit-application"]',
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Clicked Indeed submit"}
            sub = page.get_by_role("button", name=re.compile(r"submit", re.I))
            if await sub.count() > 0:
                await sub.first.click()
                await self._short_wait(page)
                return {"success": True, "message": "Clicked submit (role)"}
            return {"success": False, "message": "Indeed submit not found"}
        except Exception as e:
            logger.exception("Indeed submit")
            return {"success": False, "message": str(e)}
