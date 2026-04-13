"""Generate PDF resumes and cover letters from structured data."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
GENERATED_DIR = Path(__file__).parent.parent.parent / "generated"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )


def generate_resume_pdf(resume_data: dict, application_id: str = "") -> Path:
    """Render a tailored resume to PDF.

    Args:
        resume_data: Structured resume data (from tailor.py output)
        application_id: Application ID for filename (e.g., APP-001)

    Returns:
        Path to the generated PDF file
    """
    env = _get_jinja_env()
    template = env.get_template("resume.html")

    html_content = template.render(**resume_data)

    output_dir = GENERATED_DIR / "resumes"
    output_dir.mkdir(parents=True, exist_ok=True)

    if application_id:
        filename = f"{application_id}_resume.pdf"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{timestamp}.pdf"

    output_path = output_dir / filename
    HTML(string=html_content).write_pdf(str(output_path))
    logger.info(f"Resume PDF generated: {output_path}")

    return output_path


def generate_cover_letter_pdf(
    cover_letter_text: str,
    name: str,
    contact: dict,
    company: str,
    application_id: str = "",
) -> Path:
    """Render a cover letter to PDF.

    Args:
        cover_letter_text: The cover letter body text
        name: Candidate name
        contact: Contact info dict (email, phone, location)
        company: Target company name
        application_id: Application ID for filename

    Returns:
        Path to the generated PDF file
    """
    env = _get_jinja_env()
    template = env.get_template("cover_letter.html")

    # Split the cover letter into paragraphs (skip greeting/closing if present)
    lines = cover_letter_text.strip().split("\n")
    paragraphs = []
    skip_patterns = ["dear ", "sincerely", "regards", "best,", "yours"]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.lower().startswith(p) for p in skip_patterns):
            continue
        paragraphs.append(stripped)

    html_content = template.render(
        name=name,
        contact=contact,
        company=company,
        date=datetime.now().strftime("%B %d, %Y"),
        paragraphs=paragraphs,
    )

    output_dir = GENERATED_DIR / "cover_letters"
    output_dir.mkdir(parents=True, exist_ok=True)

    if application_id:
        filename = f"{application_id}_cover_letter.pdf"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_letter_{timestamp}.pdf"

    output_path = output_dir / filename
    HTML(string=html_content).write_pdf(str(output_path))
    logger.info(f"Cover letter PDF generated: {output_path}")

    return output_path
