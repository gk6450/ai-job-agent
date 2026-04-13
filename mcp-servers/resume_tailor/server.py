import json
import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from .parser import parse_resume, parse_and_save
from .tailor import tailor_resume, generate_cover_letter
from .generator import generate_resume_pdf, generate_cover_letter_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "ResumeTailor",
    description="Parse, tailor, and generate PDF resumes and cover letters. Conservative tailoring -- never fabricates information.",
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
GENERATED_DIR = Path(__file__).parent.parent.parent / "generated"


def _load_base_resume() -> dict:
    """Load the structured base resume JSON."""
    json_path = DATA_DIR / "base_resume.json"
    if not json_path.exists():
        pdf_path = DATA_DIR / "base_resume.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError("No base resume found. Place base_resume.pdf in data/ folder.")
        logger.info("base_resume.json not found, parsing from PDF...")
        parse_and_save(pdf_path, json_path)

    return json.loads(json_path.read_text())


@mcp.tool()
async def parse_resume_pdf(pdf_path: str = "") -> str:
    """Parse a resume PDF into structured JSON data.

    Args:
        pdf_path: Path to the PDF file. Leave empty to parse the default base resume (data/base_resume.pdf).
    """
    if not pdf_path:
        pdf_path = str(DATA_DIR / "base_resume.pdf")

    path = Path(pdf_path)
    if not path.exists():
        return f"File not found: {pdf_path}"

    json_path = path.with_suffix(".json")
    data = parse_and_save(path, json_path)

    sections = []
    if data.get("contact"):
        sections.append(f"Contact: {data['contact']}")
    if data.get("summary"):
        sections.append(f"Summary: {data['summary'][:200]}...")
    if data.get("experience"):
        sections.append(f"Experience: {len(data['experience'])} entries")
    if data.get("skills"):
        sections.append(f"Skills: {len(data['skills'])} categories")
    if data.get("projects"):
        sections.append(f"Projects: {len(data['projects'])} entries")

    return f"Parsed resume saved to {json_path}\n\nSections found:\n" + "\n".join(f"  - {s}" for s in sections)


@mcp.tool()
async def tailor_resume_for_job(
    job_description: str,
    job_title: str,
    company: str,
    application_id: str = "",
) -> str:
    """Tailor the base resume for a specific job and generate a PDF.

    Conservative tailoring: reorders bullets, adjusts emphasis, highlights matching skills.
    NEVER fabricates skills, experience, or certifications.

    Args:
        job_description: Full job description text
        job_title: Target job title
        company: Target company name
        application_id: Application ID for filename (e.g., APP-001)
    """
    base = _load_base_resume()

    logger.info(f"Tailoring resume for {job_title} at {company}...")
    tailored = await tailor_resume(base, job_description, job_title, company)

    pdf_path = generate_resume_pdf(tailored, application_id)

    tailored_json_path = GENERATED_DIR / "resumes" / f"{application_id or 'latest'}_resume.json"
    tailored_json_path.write_text(json.dumps(tailored, indent=2, ensure_ascii=False))

    return (
        f"Resume tailored for {job_title} at {company}.\n"
        f"PDF: {pdf_path}\n"
        f"JSON: {tailored_json_path}"
    )


@mcp.tool()
async def generate_cover_letter_for_job(
    job_description: str,
    job_title: str,
    company: str,
    application_id: str = "",
) -> str:
    """Generate a cover letter for a specific job and create a PDF.

    Under 300 words, professional, specific to the job, no fabrication.

    Args:
        job_description: Full job description text
        job_title: Target job title
        company: Target company name
        application_id: Application ID for filename (e.g., APP-001)
    """
    base = _load_base_resume()

    logger.info(f"Generating cover letter for {job_title} at {company}...")
    letter_text = await generate_cover_letter(base, job_description, job_title, company)

    pdf_path = generate_cover_letter_pdf(
        cover_letter_text=letter_text,
        name=base.get("name", ""),
        contact=base.get("contact", {}),
        company=company,
        application_id=application_id,
    )

    # Also save the text version
    text_path = GENERATED_DIR / "cover_letters" / f"{application_id or 'latest'}_cover_letter.txt"
    text_path.write_text(letter_text)

    return (
        f"Cover letter generated for {job_title} at {company}.\n"
        f"PDF: {pdf_path}\n"
        f"Text: {text_path}\n\n"
        f"--- Preview ---\n{letter_text}"
    )


@mcp.tool()
async def list_generated_documents() -> str:
    """List all generated resumes and cover letters."""
    resume_dir = GENERATED_DIR / "resumes"
    cover_dir = GENERATED_DIR / "cover_letters"

    lines = ["Generated Documents:\n"]

    resumes = sorted(resume_dir.glob("*.pdf")) if resume_dir.exists() else []
    covers = sorted(cover_dir.glob("*.pdf")) if cover_dir.exists() else []

    if resumes:
        lines.append("Resumes:")
        for f in resumes:
            size_kb = f.stat().st_size / 1024
            lines.append(f"  - {f.name} ({size_kb:.1f} KB)")
    else:
        lines.append("Resumes: none generated yet")

    lines.append("")

    if covers:
        lines.append("Cover Letters:")
        for f in covers:
            size_kb = f.stat().st_size / 1024
            lines.append(f"  - {f.name} ({size_kb:.1f} KB)")
    else:
        lines.append("Cover Letters: none generated yet")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
