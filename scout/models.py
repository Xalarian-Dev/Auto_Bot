"""
Data models for the Scout agent.
Pydantic models for validation/transport, SQLAlchemy models for persistence.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    INTERESTING = "interesting"
    APPLIED = "applied"
    REJECTED = "rejected"
    IGNORED = "ignored"


class Region(str, Enum):
    APAC = "APAC"
    NORTH_AMERICA = "NA"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Pydantic model — used throughout the pipeline
# ---------------------------------------------------------------------------

class JobListing(BaseModel):
    """A single job listing as it flows through the Scout pipeline."""

    title: str
    company: str
    location: str
    country: str = ""
    region: Region = Region.OTHER

    url: str
    description: str = ""
    salary_raw: str = ""          # raw salary string, unparsed

    date_posted: Optional[datetime] = None
    source: str                   # seek, jobsdb, mycareersfuture, serpapi

    # Filled by the scorer
    relevance_score: Optional[int] = None     # 0-100
    relevance_notes: Optional[str] = None
    is_relocation_friendly: Optional[bool] = None

    status: JobStatus = JobStatus.NEW

    @computed_field
    @property
    def fingerprint(self) -> str:
        """Deduplication key — hash of title + company + location."""
        raw = f"{self.title.lower().strip()}|{self.company.lower().strip()}|{self.location.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class ScorerResult(BaseModel):
    """Structured output from Claude scorer."""
    score: int = Field(ge=0, le=100)
    is_relocation_friendly: bool
    notes: str


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class JobListingORM(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(16), unique=True, index=True)

    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(20), default=Region.OTHER)

    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    salary_raw: Mapped[str] = mapped_column(String(200), default="")

    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    date_found: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    source: Mapped[str] = mapped_column(String(50))

    relevance_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relevance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_relocation_friendly: Mapped[Optional[bool]] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=JobStatus.NEW)
    scout_mode: Mapped[str] = mapped_column(String(1), default="A", index=True)

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company} [{self.source}] score={self.relevance_score}>"
