"""LLM-based resume tailoring and cover letter generation."""

from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)

TAILOR_SYSTEM_PROMPT = """You are a professional resume tailor. Given a base resume (JSON) and a job description, produce a tailored version of the resume.

STRICT RULES:
1. NEVER fabricate skills, experience, projects, or certifications that are not in the original resume
2. NEVER add technologies the candidate hasn't worked with
3. You MAY reorder bullet points to put the most relevant ones first
4. You MAY adjust emphasis and wording to better match the job description's language
5. You MAY highlight matching skills more prominently
6. You MAY slightly rephrase bullets for better alignment (but keep the same meaning)
7. Keep all factual information identical (dates, companies, titles, metrics)

Return ONLY valid JSON with the same structure as the input resume, with the tailored changes applied."""

COVER_LETTER_SYSTEM_PROMPT = """You are a professional cover letter writer. Given a resume (JSON) and a job description, write a concise cover letter.

RULES:
1. Keep it under 300 words
2. Be specific to the job and company -- reference actual requirements from the JD
3. Reference real experience and skills from the resume
4. NEVER fabricate or exaggerate accomplishments
5. Professional but personable tone
6. Standard format: greeting, 2-3 body paragraphs, closing
7. Do not use generic filler phrases

Return ONLY the cover letter text (no JSON wrapping)."""


async def _call_llm(system_prompt: str, user_prompt: str, gateway_url: str = "http://localhost:18789") -> str:
    """Call the OpenClaw gateway LLM API."""
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


async def tailor_resume(base_resume: dict, job_description: str, job_title: str, company: str) -> dict:
    """Tailor a resume for a specific job.

    Args:
        base_resume: Structured resume data (from base_resume.json)
        job_description: Full job description text
        job_title: Target job title
        company: Target company name

    Returns:
        Tailored resume as a dict (same structure as input)
    """
    user_prompt = f"""## Target Position
- Company: {company}
- Role: {job_title}

## Job Description
{job_description}

## Base Resume (JSON)
{json.dumps(base_resume, indent=2)}

Tailor this resume for the position above. Return valid JSON only."""

    response = await _call_llm(TAILOR_SYSTEM_PROMPT, user_prompt)

    # Extract JSON from response (handle markdown code blocks)
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON, returning original resume with note")
        base_resume["_tailoring_note"] = "Auto-tailoring failed, using original resume"
        return base_resume


async def generate_cover_letter(
    base_resume: dict, job_description: str, job_title: str, company: str
) -> str:
    """Generate a cover letter for a specific job.

    Returns:
        Cover letter text
    """
    user_prompt = f"""## Target Position
- Company: {company}
- Role: {job_title}

## Job Description
{job_description}

## Candidate Resume (JSON)
{json.dumps(base_resume, indent=2)}

Write a concise, specific cover letter for this position. Return only the cover letter text."""

    return await _call_llm(COVER_LETTER_SYSTEM_PROMPT, user_prompt)
