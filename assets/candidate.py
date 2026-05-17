"""
Loads candidate profile from assets/candidate.yaml.
Single source of truth for all candidate-specific data.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
def load_candidate(assets_dir: str = "assets") -> dict:
    path = Path(assets_dir) / "candidate.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Candidate profile not found: {path}\n"
            "Copy assets/candidate.yaml.example and fill in your details."
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_identity_block(assets_dir: str = "assets") -> str:
    """Return a formatted identity block for Claude prompts."""
    c = load_candidate(assets_dir)
    strengths = "\n".join(f"- {s}" for s in c.get("core_strengths", []))
    experiences = "\n".join(f"- {e}" for e in c.get("key_experiences", []))
    education = "\n".join(f"- {e}" for e in c.get("education", []))
    languages = ", ".join(c.get("languages", []))

    return f"""Name: {c['name']}
Current title: {c['current_title']}
Location: {c['location']}
Email: {c['email']}
LinkedIn: {c['linkedin']}
Languages: {languages}

Core strengths:
{strengths}

Key experiences:
{experiences}

Education:
{education}"""


def get_scorer_profile(assets_dir: str = "assets") -> str:
    """Return the scorer system prompt built from candidate profile."""
    c = load_candidate(assets_dir)
    s = c.get("scorer", {})

    roles = ", ".join(s.get("target_roles", []))
    target_regions = "\n".join(f"- {r}" for r in s.get("target_regions", []))
    excluded = ", ".join(s.get("excluded_regions", []))
    positive = "\n".join(f"- {p}" for p in s.get("positive_signals", []))
    negative = "\n".join(f"- {n}" for n in s.get("negative_signals", []))
    languages = ", ".join(c.get("languages", []))

    return f"""You are evaluating job listings for a specific candidate. Here is their profile:

**Role target:** {roles}
**Experience:** {c.get('experience_years', '?')}+ years in IT project and program management
**Background:** IT consulting for public administration / government digital services
**Open to:** Any sector that requires managing people, teams, or complex projects
**Languages:** {languages}
**Target regions:**
{target_regions}
**Work mode:** {s.get('work_mode', '')}
**Excluded regions:** {excluded}. Do not score these positively.

**Strong positive signals:**
{positive}

**Negative signals:**
{negative}"""
