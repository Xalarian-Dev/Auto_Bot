"""
Drafter agent — generates a tailored cover letter and talking points
for a specific job listing using Claude Sonnet.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import anthropic

from assets.candidate import get_identity_block
from drafter.resume import get_resume_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert career coach and professional writer helping a senior IT program manager
apply for executive roles abroad. Your task is to produce two deliverables for each job application:

1. A tailored COVER LETTER — professional, confident, direct. 3-4 paragraphs:
   - Opening: why this specific role and company excite the candidate
   - Body: 2-3 concrete achievements from the candidate's background that directly match the job requirements
   - Closing: clear statement of intent to relocate, availability, call to action

   Style: senior executive tone, no buzzword stuffing, no generic phrases like "I am passionate about".
   Be specific. Reference real numbers and achievements from the profile.
   Language: English unless the job is clearly in France/Belgium (then French).
   IMPORTANT: Do NOT include the candidate's contact information (email, phone, LinkedIn, address)
   in the cover letter body. These are already in the document header. Start directly with the opening paragraph.

2. TALKING POINTS for resume tailoring — a bullet list of:
   - Which bullet points or achievements to expand or emphasize within each role (resume stays reverse-chronological — do NOT suggest reordering roles)
   - Keywords from the job description to weave into the resume summary
   - Any skills or certifications mentioned in the job to highlight if present in the profile
   - What NOT to emphasize for this specific role (irrelevant experience)

Format your response EXACTLY as:
---COVER LETTER---
[cover letter text]

---TALKING POINTS---
[bullet points]
"""


@dataclass
class DraftResult:
    cover_letter: str
    talking_points: str
    job_title: str
    company: str
    language: str  # "en" or "fr"


class DrafterAgent:
    def __init__(self, model: str = "claude-sonnet-4-6", assets_dir: str = "assets"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.resume_text = get_resume_text(assets_dir)

    def draft(
        self,
        job_title: str,
        company: str,
        location: str,
        description: str,
        notes: str = "",
        salary: str = "",
    ) -> DraftResult:
        """Generate cover letter + talking points for a job listing."""

        # Detect language: use French if job is clearly in France/Belgium
        location_lower = (location + " " + company).lower()
        language = "fr" if any(w in location_lower for w in ["france", "paris", "belgium", "bruxelles", "brussels"]) else "en"
        lang_instruction = "Write the cover letter in FRENCH." if language == "fr" else "Write the cover letter in ENGLISH."

        user_message = f"""
{lang_instruction}

## CANDIDATE PROFILE
{get_identity_block()}

## CANDIDATE'S RESUME (full text)
{self.resume_text}

## JOB TO APPLY FOR
**Title:** {job_title}
**Company:** {company}
**Location:** {location}
**Salary:** {salary or "Not specified"}
**Scout notes:** {notes or "None"}

**Job description:**
{description[:4000] if description else "No description available."}

---

Now produce:
1. A tailored cover letter for this specific role
2. Talking points for resume tailoring
"""

        logger.info(f"[drafter] Generating draft for: {job_title} @ {company}")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text  # type: ignore[union-attr]
        logger.debug(f"[drafter] raw response:\n{raw[:500]}")
        cover_letter, talking_points = self._parse_response(raw)

        return DraftResult(
            cover_letter=cover_letter,
            talking_points=talking_points,
            job_title=job_title,
            company=company,
            language=language,
        )

    def _parse_response(self, raw: str) -> tuple[str, str]:
        """Split Claude's response into cover letter and talking points."""
        # Try several marker variations Claude might use
        cl_markers = ["---COVER LETTER---", "**COVER LETTER**", "# COVER LETTER", "COVER LETTER"]
        tp_markers = ["---TALKING POINTS---", "**TALKING POINTS**", "# TALKING POINTS", "TALKING POINTS"]

        raw_upper = raw.upper()

        cl_start = -1
        cl_marker_len = 0
        for m in cl_markers:
            idx = raw_upper.find(m)
            if idx != -1:
                cl_start = idx
                cl_marker_len = len(m)
                break

        tp_start = -1
        tp_marker_len = 0
        for m in tp_markers:
            idx = raw_upper.find(m)
            if idx != -1:
                tp_start = idx
                tp_marker_len = len(m)
                break

        if cl_start == -1 and tp_start == -1:
            # No markers at all — return full text as cover letter
            logger.warning("[drafter] Could not find section markers in response")
            return raw.strip(), ""

        if cl_start == -1:
            # Only talking points marker found
            cover_letter = raw[:tp_start].strip()
            talking_points = raw[tp_start + tp_marker_len:].strip()
            return cover_letter, talking_points

        if tp_start == -1:
            # Only cover letter marker found
            cover_letter = raw[cl_start + cl_marker_len:].strip()
            return cover_letter, ""

        cover_letter = raw[cl_start + cl_marker_len:tp_start].strip()
        talking_points = raw[tp_start + tp_marker_len:].strip()
        return cover_letter, talking_points
