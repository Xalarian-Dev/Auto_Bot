"""
Claude-powered relevance scorer.
Evaluates each job listing against the candidate profile and returns
a score (0-100) plus structured notes.
"""

from __future__ import annotations

import logging
import os

import anthropic

from scout.models import JobListing, ScorerResult
from assets.candidate import get_scorer_profile

logger = logging.getLogger(__name__)

SCORE_TOOL = {
    "name": "score_job",
    "description": "Score a job listing for the candidate and assess relocation friendliness.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": (
                    "Relevance score 0-100. "
                    "80-100: excellent match. "
                    "60-79: good match, worth reviewing. "
                    "40-59: partial match, review if time permits. "
                    "0-39: poor match, skip."
                ),
            },
            "is_relocation_friendly": {
                "type": "boolean",
                "description": (
                    "True if the listing explicitly mentions relocation support, "
                    "visa sponsorship, or is in a country/city known to be expat-friendly "
                    "for this type of role. False if remote-only or unclear."
                ),
            },
            "notes": {
                "type": "string",
                "description": (
                    "2-4 sentences explaining the score. Highlight the strongest "
                    "positive and negative signals. Be specific. Keep it concise."
                ),
            },
        },
        "required": ["score", "is_relocation_friendly", "notes"],
    },
}


class Scorer:
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model  # Haiku for cost efficiency at scale

    def score(self, listing: JobListing) -> ScorerResult:
        """Score a single job listing. Returns a ScorerResult."""
        user_message = self._build_message(listing)

        try:
            response = self.client.messages.create(  # type: ignore[call-overload]
                model=self.model,
                max_tokens=512,
                system=get_scorer_profile(),
                tools=[SCORE_TOOL],
                tool_choice={"type": "tool", "name": "score_job"},
                messages=[{"role": "user", "content": user_message}],
            )

            # Extract tool use result
            for block in response.content:
                if block.type == "tool_use" and block.name == "score_job":
                    data = block.input
                    return ScorerResult(
                        score=int(data["score"]),
                        is_relocation_friendly=bool(data["is_relocation_friendly"]),
                        notes=str(data["notes"]),
                    )

            logger.warning(f"[scorer] no tool_use block for: {listing.title}")
            return ScorerResult(score=0, is_relocation_friendly=False, notes="Scorer returned no result.")

        except Exception as exc:
            logger.error(f"[scorer] failed for '{listing.title}': {exc}")
            return ScorerResult(score=0, is_relocation_friendly=False, notes=f"Scoring error: {exc}")

    def score_batch(self, listings: list[JobListing]) -> list[tuple[JobListing, ScorerResult]]:
        """Score a batch of listings sequentially (API rate limit friendly)."""
        results = []
        for i, listing in enumerate(listings, 1):
            logger.info(f"[scorer] scoring {i}/{len(listings)}: {listing.title} @ {listing.company}")
            result = self.score(listing)
            results.append((listing, result))
        return results

    # ------------------------------------------------------------------

    def _build_message(self, listing: JobListing) -> str:
        parts = [
            f"**Job Title:** {listing.title}",
            f"**Company:** {listing.company}",
            f"**Location:** {listing.location} ({listing.country})",
            f"**Source:** {listing.source}",
        ]
        if listing.salary_raw:
            parts.append(f"**Salary:** {listing.salary_raw}")
        if listing.date_posted:
            parts.append(f"**Posted:** {listing.date_posted.strftime('%Y-%m-%d')}")
        if listing.description:
            # Truncate description to avoid token waste
            desc = listing.description[:1500]
            parts.append(f"\n**Description:**\n{desc}")

        return "\n".join(parts)
