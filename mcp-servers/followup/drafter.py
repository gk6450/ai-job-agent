"""LLM-based follow-up and thank-you email drafting."""

from __future__ import annotations

import logging
import httpx

logger = logging.getLogger(__name__)

FOLLOWUP_SYSTEM_PROMPT = """You are a professional email writer. Draft a follow-up email for a job application.

RULES:
1. Keep it under 150 words
2. Professional but warm tone
3. Reference the specific role and company
4. Express continued interest
5. Politely ask for an update on the application status
6. Do not sound desperate or pushy
7. No generic filler -- be specific and concise

Return ONLY the email body (no subject line, no "Subject:" prefix)."""

THANK_YOU_SYSTEM_PROMPT = """You are a professional email writer. Draft a post-interview thank-you email.

RULES:
1. Keep it under 200 words
2. Thank them for their time
3. Reference specific topics discussed if provided
4. Reiterate interest in the role
5. Professional but genuine tone
6. No generic platitudes

Return ONLY the email body (no subject line, no "Subject:" prefix)."""


async def _call_llm(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                "http://localhost:18789/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


async def draft_followup_email(
    company: str,
    role: str,
    applied_date: str,
    candidate_name: str,
    followup_number: int = 1,
) -> dict:
    """Draft a follow-up email.

    Returns:
        dict with 'subject' and 'body' keys
    """
    ordinal = "first" if followup_number == 1 else "second"

    prompt = f"""Draft a {ordinal} follow-up email for this application:
- Company: {company}
- Role: {role}
- Applied on: {applied_date}
- Candidate: {candidate_name}

This is follow-up #{followup_number}. {"Be slightly more direct since this is a second follow-up." if followup_number > 1 else ""}"""

    body = await _call_llm(FOLLOWUP_SYSTEM_PROMPT, prompt)

    subject = f"Following Up - {role} Application"
    if followup_number > 1:
        subject = f"Re: Following Up - {role} Application"

    return {"subject": subject, "body": body.strip()}


async def draft_thank_you_email(
    company: str,
    role: str,
    interviewer_name: str = "",
    discussion_points: str = "",
    candidate_name: str = "",
) -> dict:
    """Draft a post-interview thank-you email.

    Returns:
        dict with 'subject' and 'body' keys
    """
    prompt = f"""Draft a thank-you email after an interview:
- Company: {company}
- Role: {role}
- Candidate: {candidate_name}"""

    if interviewer_name:
        prompt += f"\n- Interviewer: {interviewer_name}"
    if discussion_points:
        prompt += f"\n- Topics discussed: {discussion_points}"

    body = await _call_llm(THANK_YOU_SYSTEM_PROMPT, prompt)

    subject = f"Thank You - {role} Interview"

    return {"subject": subject, "body": body.strip()}
