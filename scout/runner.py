"""
Scout runner -- orchestrates all sources, deduplication, scoring, and persistence.
"""

from __future__ import annotations

import logging
import os
import sys
import time

import yaml
from rich.console import Console
from rich.table import Table
from rich import box

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scout.db import upsert_listing, update_score, get_unscored, get_stats, get_top_listings, get_all_modes
from scout.models import JobListing, Region
from scout.scorer import Scorer
from scout.sources.base import infer_region
from scout.sources import (
    SerpAPISource, MyCareersFutureSource,
    IndeedSource, USAJobsSource, JobBankCanadaSource,
    JaabzSource, GlobalJobsSource, GreenhouseSource, ITJobBoardSource,
)
from scout.sources.base import BaseSource

logger = logging.getLogger(__name__)
console = Console(force_terminal=True, highlight=False, emoji=False)

VALID_MODES = ("A", "B", "C")

MODE_LABELS = {
    "A": "APAC",
    "B": "North America",
    "C": "Europe (North + Paris)",
}


def load_config(path: str = "config/criteria.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_mode_config(full_config: dict, mode: str) -> dict:
    mode = mode.upper()
    modes = full_config.get("modes", {})
    if mode not in modes:
        raise ValueError(f"Mode '{mode}' not found in criteria.yaml. Valid modes: {list(modes.keys())}")
    return modes[mode]


def build_sources(config: dict) -> list[BaseSource]:
    sources: list[BaseSource] = []

    if os.getenv("SERPAPI_KEY") and config.get("serpapi_queries"):
        sources.append(SerpAPISource(config))

    if os.getenv("SERPAPI_KEY") and config.get("indeed_queries"):
        sources.append(IndeedSource(config))

    if config.get("usajobs_queries"):
        sources.append(USAJobsSource(config))

    if config.get("jobbank_queries"):
        sources.append(JobBankCanadaSource(config))

    if config.get("mcf_queries"):
        sources.append(MyCareersFutureSource(config))

    if config.get("jaabz_queries"):
        sources.append(JaabzSource(config))

    if config.get("globaljobs_queries"):
        sources.append(GlobalJobsSource(config))

    if config.get("greenhouse_companies"):
        sources.append(GreenhouseSource(config))

    if config.get("itjobboard_queries"):
        sources.append(ITJobBoardSource(config))

    return sources


def run_scout(
    config_path: str = "config/criteria.yaml",
    db_path: str = "data/scout.db",
    min_score_display: int = 60,
    dry_run: bool = False,
    mode: str = "A",
) -> None:
    """
    Full Scout pipeline:
    1. Load config for the selected mode
    2. Fetch from all sources
    3. Deduplicate + persist (tagged with mode)
    4. Score new listings with Claude
    5. Print per-mode results table
    """
    full_config = load_config(config_path)
    config = extract_mode_config(full_config, mode)
    label = config.get("label", MODE_LABELS.get(mode, mode))
    console.rule(f"[bold blue]Scout Agent - Mode {mode}: {label}")

    # ------------------------------------------------------------------ Fetch
    sources = build_sources(config)
    if not sources:
        console.print("[red]No sources configured or available. Check your .env and criteria.yaml.")
        return

    all_listings: list[JobListing] = []
    for source in sources:
        console.print(f"  [cyan]Fetching from {source.name}...")
        listings = source._safe_fetch()
        all_listings.extend(listings)

    console.print(f"\n[green]Total fetched:[/] {len(all_listings)} listings across {len(sources)} sources")

    # --------------------------------------------------------- Region filter
    # Drop listings whose inferred region conflicts with the current mode.
    # Region.OTHER means location couldn't be resolved — keep those (no false drops).
    # Mode C is all Region.OTHER (Europe) so no filtering needed there.
    MODE_REJECT: dict[str, set[Region]] = {
        "A": {Region.NORTH_AMERICA},
        "B": {Region.APAC},
    }
    reject_regions = MODE_REJECT.get(mode, set())
    if reject_regions:
        filtered: list[JobListing] = []
        dropped = 0
        for listing in all_listings:
            r = infer_region(listing.country, listing.location)
            if r in reject_regions:
                logger.debug(f"[runner] Dropped (region={r.value}): {listing.title} @ {listing.location}")
                dropped += 1
            else:
                filtered.append(listing)
        if dropped:
            console.print(f"[dim]Region filter: dropped {dropped} listing(s) not matching Mode {mode}[/]")
        all_listings = filtered

    if dry_run:
        console.print("[yellow]Dry run -- skipping persistence and scoring.")
        _print_raw(all_listings[:20], mode, label)
        return

    # ----------------------------------------------------------- Deduplicate & persist
    new_listings: list[JobListing] = []
    skipped = 0

    for listing in all_listings:
        _, created = upsert_listing(listing, db_path, scout_mode=mode)
        if created:
            new_listings.append(listing)
        else:
            skipped += 1

    console.print(f"[green]New:[/] {len(new_listings)}  [dim]Already known: {skipped}[/]")

    # ------------------------------------------- Score new + still-unscored listings
    # Includes listings saved in an earlier run but never scored (crash, missing
    # key, API failure), so nothing stays "unscored" forever.
    pending = get_unscored(db_path, scout_mode=mode)
    if pending:
        if not os.getenv("ANTHROPIC_API_KEY"):
            console.print(
                f"[yellow]ANTHROPIC_API_KEY not set -- {len(pending)} listing(s) left unscored "
                "(they will be scored at the next run with a valid key)."
            )
        else:
            console.print(f"\n[cyan]Scoring {len(pending)} unscored listings with Claude...")
            scorer = Scorer()
            failed = 0

            for listing in pending:
                result = scorer.score(listing)
                if result is None:
                    failed += 1
                    continue
                update_score(
                    fingerprint=listing.fingerprint,
                    score=result.score,
                    notes=result.notes,
                    relocation_friendly=result.is_relocation_friendly,
                    db_path=db_path,
                )
                time.sleep(0.3)

            if failed:
                console.print(
                    f"[yellow]WARNING: {failed} listing(s) could not be scored and stay unscored "
                    "(check the API key / credit / rate limit). They will be retried at the next run.[/]"
                )
            console.print(f"[green]Scoring complete:[/] {len(pending) - failed} scored, {failed} failed.")

    # ----------------------------------------------------------------- Summary
    stats = get_stats(db_path, scout_mode=mode)
    console.print(
        f"\n[bold]Mode {mode} stats:[/] total={stats['total']}  "
        f"scored={stats['scored']}  unscored={stats['unscored']}  "
        f"avg_score={stats['avg_score']}"
    )

    print_top_by_mode(db_path, min_score_display, modes=[mode])
    console.rule("[bold blue]Scout done")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_top_by_mode(db_path: str, min_score: int, modes: list[str] | None = None) -> None:
    """Print one table per mode, only for modes that have data."""
    if modes is None:
        modes = get_all_modes(db_path)

    any_results = False
    for mode in modes:
        label = MODE_LABELS.get(mode, mode)
        top = get_top_listings(min_score=min_score, limit=20, db_path=db_path, scout_mode=mode)
        if not top:
            console.print(f"\n[dim]Mode {mode} ({label}): no listings with score >= {min_score}[/]")
            continue

        any_results = True
        table = Table(
            title=f"Mode {mode} - {label}  |  Top listings (score >= {min_score})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Score", style="bold green", width=6)
        table.add_column("Title", width=35)
        table.add_column("Company", width=25)
        table.add_column("Location", width=20)
        table.add_column("Source", width=14)
        table.add_column("Reloc?", width=6)

        for job in top:
            reloc = "[green]Yes[/]" if job.is_relocation_friendly else "[red]No[/]"
            table.add_row(
                str(job.relevance_score),
                job.title[:35],
                job.company[:25],
                job.location[:20],
                job.source,
                reloc,
            )

        console.print(table)

    if not any_results:
        console.print(f"\n[dim]No listings with score >= {min_score} in any mode.[/]")


def _print_raw(listings: list[JobListing], mode: str, label: str) -> None:
    table = Table(
        title=f"Mode {mode} - {label}  |  Fetched listings (dry run preview)",
        box=box.SIMPLE,
    )
    table.add_column("Title", width=40)
    table.add_column("Company", width=25)
    table.add_column("Location", width=20)
    table.add_column("Source", width=15)

    for job in listings:
        table.add_row(job.title[:40], job.company[:25], job.location[:20], job.source)

    console.print(table)
