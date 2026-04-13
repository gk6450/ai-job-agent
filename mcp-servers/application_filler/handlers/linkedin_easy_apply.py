"""LinkedIn Easy Apply multi-step modal handler."""

from __future__ import annotations

import logging
import re

from .base import BaseHandler

try:
    from ..screenshot import capture_page
except ImportError:
    from screenshot import capture_page

logger = logging.getLogger(__name__)


class LinkedInEasyApplyHandler(BaseHandler):
    """Fill LinkedIn Easy Apply without submitting."""

    ats_type = "linkedin"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def _click_easy_apply(self, page) -> bool:
        try:
            btn = page.get_by_role("button", name=re.compile(r"easy apply", re.I))
            if await btn.count() > 0:
                await btn.first.click()
                await self._short_wait(page)
                return True
        except Exception as e:
            logger.debug(f"get_by_role Easy Apply: {e}")
        selectors = [
            'button:has-text("Easy Apply")',
            'a:has-text("Easy Apply")',
            '[data-test-modal-open]',
        ]
        for sel in selectors:
            if await self._safe_click(page, sel):
                await self._short_wait(page)
                return True
        return False

    async def _fill_modal_fields(self, page, fields_filled: list, errors: list) -> None:
        name_parts = self.profile.get("name", "").split()
        first = name_parts[0] if name_parts else ""
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        email = self.profile.get("email", "") or ""
        phone = self.profile.get("phone", "") or ""
        loc = self.profile.get("location", "") or ""

        prefix = "div.jobs-easy-apply-modal "
        pairs = [
            (f'{prefix}input[name="phoneNumber"], {prefix}input[id*="phone" i]', phone),
            (f"{prefix}input[type=\"tel\"]", phone),
            (f'{prefix}input[name="email"], {prefix}input[type="email"]', email),
            (f'{prefix}input[id*="email" i]', email),
            (f'{prefix}input[name="firstName"], {prefix}input[id*="firstName" i]', first),
            (f'{prefix}input[name="lastName"], {prefix}input[id*="lastName" i]', last),
            (f'{prefix}input[name="location"], {prefix}input[id*="location" i]', loc),
        ]
        for sel, val in pairs:
            if not val:
                continue
            try:
                if await self._safe_fill(page, sel, val):
                    fields_filled.append(sel)
                    await self._short_wait(page)
            except Exception as e:
                errors.append(f"linkedin fill {sel}: {e}")

    async def _upload_resume_in_modal(self, page, resume_path: str, fields_filled: list, errors: list) -> None:
        if not resume_path:
            return
        selectors = [
            'input[type="file"]',
            'div.jobs-easy-apply-modal input[type="file"]',
        ]
        for sel in selectors:
            try:
                if await self._upload_file(page, sel, resume_path):
                    fields_filled.append(f"resume:{sel}")
                    await self._short_wait(page)
                    return
            except Exception as e:
                errors.append(f"linkedin resume {sel}: {e}")

    async def _click_next_not_submit(self, page) -> bool:
        try:
            for label in ("Next", "Continue", "Review"):
                nxt = page.get_by_role("button", name=re.compile(rf"^{re.escape(label)}$", re.I))
                if await nxt.count() > 0:
                    for i in range(await nxt.count()):
                        el = nxt.nth(i)
                        if await el.is_visible():
                            txt = (await el.inner_text()).lower()
                            if "submit" in txt:
                                continue
                            await el.click()
                            await self._short_wait(page)
                            return True
        except Exception as e:
            logger.debug(f"role next: {e}")
        for sel in (
            'button:has-text("Next")',
            'button.artdeco-button--primary:has-text("Next")',
            'footer button:has-text("Continue")',
        ):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    t = (await el.inner_text()).lower()
                    if "submit" in t:
                        continue
                    await el.click()
                    await self._short_wait(page)
                    return True
            except Exception as e:
                logger.debug(f"next selector {sel}: {e}")
        return False

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        pages_filled = 0
        success = False
        try:
            if not await self._click_easy_apply(page):
                errors.append("Could not find or click Easy Apply")
                return {
                    "success": False,
                    "pages_filled": 0,
                    "fields_filled": fields_filled,
                    "errors": errors,
                }
            await self._short_wait(page)
            try:
                await page.wait_for_selector("div.jobs-easy-apply-modal", timeout=15000)
            except Exception as e:
                errors.append(f"Modal wait: {e}")

            max_steps = 25
            for step in range(max_steps):
                pages_filled = step + 1
                await self._fill_modal_fields(page, fields_filled, errors)
                await self._upload_resume_in_modal(page, resume_path, fields_filled, errors)
                if cover_letter_path:
                    try:
                        ta = "div.jobs-easy-apply-modal textarea"
                        if await self._safe_fill(page, ta, "See attached cover letter."):
                            fields_filled.append("cover_letter_text")
                        await self._upload_file(
                            page, 'div.jobs-easy-apply-modal input[type="file"]', cover_letter_path
                        )
                    except Exception as e:
                        errors.append(f"cover letter: {e}")

                try:
                    await capture_page(page, "linkedin_easy_apply", pages_filled)
                except Exception as e:
                    errors.append(f"screenshot: {e}")

                advanced = await self._click_next_not_submit(page)
                if not advanced:
                    success = True
                    break
                await self._short_wait(page)

            success = success or pages_filled > 0
        except Exception as e:
            logger.exception("LinkedIn fill")
            errors.append(str(e))
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
                'button:has-text("Submit application")',
                'button:has-text("Submit")',
                'footer button.artdeco-button--primary',
            ):
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        t = (await el.inner_text()).lower()
                        if "submit" in t:
                            await el.click()
                            await self._short_wait(page)
                            return {"success": True, "message": "Clicked submit on LinkedIn Easy Apply"}
                except Exception:
                    continue
            sub = page.get_by_role("button", name=re.compile(r"submit", re.I))
            if await sub.count() > 0:
                await sub.first.click()
                await self._short_wait(page)
                return {"success": True, "message": "Clicked submit (role)"}
            return {"success": False, "message": "Submit control not found"}
        except Exception as e:
            logger.exception("LinkedIn submit")
            return {"success": False, "message": str(e)}
