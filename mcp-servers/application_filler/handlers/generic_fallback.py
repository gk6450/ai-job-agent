"""Generic fallback handler for unknown ATS types."""

from __future__ import annotations

import logging
import re

from .base import BaseHandler

logger = logging.getLogger(__name__)


class GenericFallbackHandler(BaseHandler):
    """Heuristic fill for unrecognized application forms."""

    ats_type = "unknown"

    async def _short_wait(self, page) -> None:
        try:
            await page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"wait_for_timeout: {e}")

    async def _guess_and_fill_input(self, page, el, fields_filled: list, unfilled: list) -> None:
        try:
            if not await el.is_visible():
                return
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            input_type = (await el.get_attribute("type")) or "text"
            if input_type == "file":
                return
            name = (await el.get_attribute("name")) or ""
            el_id = (await el.get_attribute("id")) or ""
            placeholder = (await el.get_attribute("placeholder")) or ""
            ac = (await el.get_attribute("autocomplete")) or ""
            blob = f"{name} {el_id} {placeholder} {ac}".lower()

            name_parts = self.profile.get("name", "").split()
            first = name_parts[0] if name_parts else ""
            last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            value = ""
            if re.search(r"first|given", blob):
                value = first
            elif re.search(r"last|family|surname", blob):
                value = last
            elif re.search(r"full.?name|^name$|your.?name", blob) or (
                name == "name" and "first" not in blob
            ):
                value = self.profile.get("name", "") or ""
            elif "email" in blob or input_type == "email":
                value = self.profile.get("email", "") or ""
            elif re.search(r"phone|tel|mobile|cell", blob) or input_type == "tel":
                value = self.profile.get("phone", "") or ""
            elif re.search(r"city|location|address|zip|postal", blob):
                value = self.profile.get("location", "") or ""
            elif "linkedin" in blob:
                value = self.profile.get("linkedin", "") or ""
            elif "github" in blob:
                value = self.profile.get("github", "") or ""
            elif re.search(r"company|employer|organization", blob):
                value = self.profile.get("current_company", "") or ""
            elif re.search(r"title|position|role", blob) and "linkedin" not in blob:
                value = self.profile.get("current_title", "") or ""

            ident = el_id or name or placeholder or tag
            if not value:
                unfilled.append(ident or "unnamed_input")
                return
            try:
                await el.click()
                await el.fill("")
                await el.fill(value)
                fields_filled.append(ident or "input")
                await self._short_wait(page)
            except Exception as e:
                unfilled.append(f"{ident}:{e}")
        except Exception as e:
            unfilled.append(str(e))

    async def fill(self, page, resume_path: str = "", cover_letter_path: str = "") -> dict:
        fields_filled: list[str] = []
        errors: list[str] = []
        unfilled: list[str] = []
        pages_filled = 1

        try:
            selectors = 'input[type="text"], input[type="email"], input[type="tel"], input:not([type]), textarea'
            elements = await page.query_selector_all(selectors)
            for el in elements[:80]:
                await self._guess_and_fill_input(page, el, fields_filled, unfilled)

            if resume_path:
                try:
                    files = await page.query_selector_all('input[type="file"]')
                    uploaded = False
                    for finp in files:
                        try:
                            accept = (await finp.get_attribute("accept")) or ""
                            if "pdf" in accept.lower() or "doc" in accept.lower() or not accept:
                                await finp.set_input_files(resume_path)
                                fields_filled.append("resume_upload")
                                uploaded = True
                                await self._short_wait(page)
                                break
                        except Exception as e:
                            errors.append(f"resume upload: {e}")
                    if not uploaded and files:
                        try:
                            await files[0].set_input_files(resume_path)
                            fields_filled.append("resume_upload_first")
                            await self._short_wait(page)
                        except Exception as e:
                            errors.append(f"resume fallback: {e}")
                except Exception as e:
                    errors.append(f"resume scan: {e}")

            if cover_letter_path:
                try:
                    from pathlib import Path

                    p = Path(cover_letter_path)
                    text = (
                        p.read_text(encoding="utf-8", errors="replace")
                        if p.exists()
                        else ""
                    )
                    tas = await page.query_selector_all("textarea")
                    for ta in tas[:5]:
                        try:
                            if not await ta.is_visible():
                                continue
                            ph = ((await ta.get_attribute("placeholder")) or "").lower()
                            if "cover" in ph or not text:
                                await ta.fill(text or "Cover letter attached separately.")
                                fields_filled.append("cover_letter_textarea")
                                await self._short_wait(page)
                                break
                        except Exception as e:
                            errors.append(f"cover textarea: {e}")
                except Exception as e:
                    errors.append(f"cover letter: {e}")

            if unfilled:
                logger.info("Generic fallback could not map fields: %s", unfilled)
                errors.append(f"Unfilled field hints: {', '.join(unfilled[:25])}")

            success = bool(fields_filled)
        except Exception as e:
            logger.exception("Generic fallback fill")
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
                'input[type="submit"]',
                'button:has-text("Submit")',
            ):
                if await self._safe_click(page, sel):
                    await self._short_wait(page)
                    return {"success": True, "message": "Clicked generic submit"}
            return {"success": False, "message": "Generic submit not found"}
        except Exception as e:
            logger.exception("Generic submit")
            return {"success": False, "message": str(e)}
