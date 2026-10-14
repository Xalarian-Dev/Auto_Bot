"""
Database layer — SQLite via SQLAlchemy 2.0.
"""

from __future__ import annotations

from pathlib import Path

from datetime import datetime, timedelta

from sqlalchemy import create_engine, distinct, func, select
from sqlalchemy.orm import Session

from scout.models import Base, JobListing, JobListingORM, JobStatus


_ENGINE = None


def get_engine(db_path: str = "data/scout.db"):
    global _ENGINE
    if _ENGINE is None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _ENGINE = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(_ENGINE)
    return _ENGINE


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def upsert_listing(listing: JobListing, db_path: str = "data/scout.db",
                   scout_mode: str = "A") -> tuple[JobListingORM, bool]:
    """
    Insert a job listing if it doesn't exist (by fingerprint).
    Returns (orm_object, created: bool).
    """
    engine = get_engine(db_path)
    with Session(engine) as session:
        existing = session.scalar(
            select(JobListingORM).where(JobListingORM.fingerprint == listing.fingerprint)
        )
        if existing:
            return existing, False

        orm = JobListingORM(
            fingerprint=listing.fingerprint,
            title=listing.title,
            company=listing.company,
            location=listing.location,
            country=listing.country,
            region=listing.region.value,
            url=listing.url,
            description=listing.description,
            salary_raw=listing.salary_raw,
            date_posted=listing.date_posted,
            source=listing.source,
            relevance_score=listing.relevance_score,
            relevance_notes=listing.relevance_notes,
            is_relocation_friendly=listing.is_relocation_friendly,
            status=listing.status.value,
            scout_mode=scout_mode,
        )
        session.add(orm)
        session.commit()
        session.refresh(orm)
        return orm, True


def expire_old_listings(days: int = 21, db_path: str = "data/scout.db") -> int:
    """Set status=IGNORED on NEW listings older than `days` days. Returns count updated."""
    cutoff = datetime.now() - timedelta(days=days)
    engine = get_engine(db_path)
    with Session(engine) as session:
        rows = session.scalars(
            select(JobListingORM)
            .where(JobListingORM.status == JobStatus.NEW)
            .where(JobListingORM.date_found < cutoff)
        ).all()
        for row in rows:
            row.status = JobStatus.IGNORED
        session.commit()
        return len(rows)


def update_status(fingerprint: str, status: str, db_path: str = "data/scout.db") -> None:
    engine = get_engine(db_path)
    with Session(engine) as session:
        orm = session.scalar(
            select(JobListingORM).where(JobListingORM.fingerprint == fingerprint)
        )
        if orm:
            orm.status = status
            session.commit()


def update_score(fingerprint: str, score: int, notes: str, relocation_friendly: bool,
                 db_path: str = "data/scout.db") -> None:
    engine = get_engine(db_path)
    with Session(engine) as session:
        orm = session.scalar(
            select(JobListingORM).where(JobListingORM.fingerprint == fingerprint)
        )
        if orm:
            orm.relevance_score = score
            orm.relevance_notes = notes
            orm.is_relocation_friendly = relocation_friendly
            session.commit()


def reset_failed_scores(db_path: str = "data/scout.db") -> int:
    """
    Put back to "unscored" (NULL) the old listings that were saved with a score
    of 0 only because scoring had failed. Returns the number of rows reset.
    Safe to run several times: a second run finds nothing to change.
    Real 0 scores (with a normal explanation) are left untouched.
    """
    engine = get_engine(db_path)
    with Session(engine) as session:
        rows = session.scalars(
            select(JobListingORM)
            .where(JobListingORM.relevance_score == 0)
            .where(
                JobListingORM.relevance_notes.like("Scoring error%")
                | JobListingORM.relevance_notes.like("Scorer returned no result%")
            )
        ).all()
        for row in rows:
            row.relevance_score = None
            row.relevance_notes = None
            row.is_relocation_friendly = None
        session.commit()
        return len(rows)


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_unscored(db_path: str = "data/scout.db",
                 scout_mode: str | None = None) -> list[JobListingORM]:
    engine = get_engine(db_path)
    with Session(engine) as session:
        q = select(JobListingORM).where(JobListingORM.relevance_score.is_(None))
        if scout_mode:
            q = q.where(JobListingORM.scout_mode == scout_mode)
        return list(session.scalars(q).all())


def get_top_listings(min_score: int = 60, limit: int = 50,
                     db_path: str = "data/scout.db",
                     scout_mode: str | None = None,
                     status: str | None = JobStatus.NEW) -> list[JobListingORM]:
    engine = get_engine(db_path)
    with Session(engine) as session:
        q = select(JobListingORM).where(JobListingORM.relevance_score >= min_score)
        if status:
            q = q.where(JobListingORM.status == status)
        if scout_mode:
            q = q.where(JobListingORM.scout_mode == scout_mode)
        q = q.order_by(JobListingORM.relevance_score.desc()).limit(limit)
        return list(session.scalars(q).all())


def get_all_modes(db_path: str = "data/scout.db") -> list[str]:
    """Return the sorted list of modes that have data in the DB."""
    engine = get_engine(db_path)
    with Session(engine) as session:
        return list(session.scalars(
            select(distinct(JobListingORM.scout_mode)).order_by(JobListingORM.scout_mode)
        ).all())


def get_stats(db_path: str = "data/scout.db", scout_mode: str | None = None) -> dict:
    engine = get_engine(db_path)
    with Session(engine) as session:
        def _count(extra_filter=None) -> int:
            q = select(func.count(JobListingORM.id))
            if scout_mode:
                q = q.where(JobListingORM.scout_mode == scout_mode)
            if extra_filter is not None:
                q = q.where(extra_filter)
            return session.scalar(q) or 0

        total = _count()
        scored = _count(JobListingORM.relevance_score.is_not(None))

        avg_q = select(func.avg(JobListingORM.relevance_score)).where(
            JobListingORM.relevance_score.is_not(None)
        )
        if scout_mode:
            avg_q = avg_q.where(JobListingORM.scout_mode == scout_mode)
        avg_score = session.scalar(avg_q)

        return {
            "total": total,
            "scored": scored,
            "unscored": total - scored,
            "avg_score": round(avg_score or 0, 1),
        }
