"""Parse a PDF resume into structured JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber


SECTION_HEADERS = [
    "summary", "objective", "profile",
    "experience", "work experience", "employment",
    "education",
    "skills", "technical skills",
    "projects",
    "achievements", "awards", "honors",
    "certifications", "certificates",
]


def extract_text(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF file."""
    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _find_section_boundaries(lines: list[str]) -> list[tuple[str, int]]:
    """Identify section header lines and their positions."""
    boundaries = []
    for i, line in enumerate(lines):
        cleaned = line.strip().lower().rstrip(":")
        if cleaned in SECTION_HEADERS:
            boundaries.append((cleaned, i))
    return boundaries


def _extract_bullets(lines: list[str]) -> list[str]:
    """Extract bullet points from a list of lines."""
    bullets = []
    current = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                bullets.append(current)
                current = ""
            continue
        if stripped.startswith(("•", "-", "–", "▪", "►", "○")):
            if current:
                bullets.append(current)
            current = stripped.lstrip("•-–▪►○ ").strip()
        elif current:
            current += " " + stripped
        else:
            current = stripped
    if current:
        bullets.append(current)
    return bullets


def parse_resume(pdf_path: str | Path) -> dict:
    """Parse a PDF resume into structured JSON.

    Returns a dict with sections: contact, summary, experience,
    education, skills, projects, achievements.
    """
    text = extract_text(pdf_path)
    lines = text.split("\n")

    result = {
        "raw_text": text,
        "contact": {},
        "summary": "",
        "experience": [],
        "education": [],
        "skills": {},
        "projects": [],
        "achievements": [],
    }

    # Extract contact info from anywhere in the document
    for line in lines:
        stripped = line.strip()
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', stripped)
        if email_match and not result["contact"].get("email"):
            result["contact"]["email"] = email_match.group()

        phone_match = re.search(r'[\+]?\d[\d\s\-]{7,15}', stripped)
        if phone_match and not result["contact"].get("phone"):
            result["contact"]["phone"] = phone_match.group().strip()

        if "github.com/" in stripped.lower():
            result["contact"]["github"] = stripped
        if "linkedin.com/" in stripped.lower():
            result["contact"]["linkedin"] = stripped

    boundaries = _find_section_boundaries(lines)

    for idx, (section_name, start_line) in enumerate(boundaries):
        if idx + 1 < len(boundaries):
            end_line = boundaries[idx + 1][1]
        else:
            end_line = len(lines)

        section_lines = lines[start_line + 1:end_line]

        if section_name in ("summary", "objective", "profile"):
            result["summary"] = " ".join(
                l.strip() for l in section_lines if l.strip()
            )

        elif section_name in ("experience", "work experience", "employment"):
            result["experience"] = _extract_bullets(section_lines)

        elif section_name == "education":
            result["education"] = _extract_bullets(section_lines)

        elif section_name in ("skills", "technical skills"):
            for line in section_lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    result["skills"][key.strip()] = [
                        v.strip() for v in val.split(",")
                    ]

        elif section_name == "projects":
            result["projects"] = _extract_bullets(section_lines)

        elif section_name in ("achievements", "awards", "honors"):
            result["achievements"] = _extract_bullets(section_lines)

    return result


def parse_and_save(pdf_path: str | Path, output_path: str | Path | None = None) -> dict:
    """Parse a resume PDF and save as JSON."""
    data = parse_resume(pdf_path)

    if output_path is None:
        output_path = Path(pdf_path).with_suffix(".json")

    Path(output_path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return data
