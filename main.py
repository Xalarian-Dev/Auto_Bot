"""
Auto_Bot - Job Research Multi-Agent System
Entry point for the Scout agent.

Usage:
    python main.py --mode A              # APAC (default)
    python main.py --mode B              # North America
    python main.py --mode C              # Northern Europe + Paris
    python main.py --mode A --dry-run    # Fetch only, no DB write, no scoring
    python main.py --top                 # Display top listings from DB
    python main.py --stats               # Show DB statistics
    python main.py --reset-failed-scores # Put old "0 by error" listings back to unscored
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console(force_terminal=True, highlight=False, emoji=False)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def cmd_run(args: argparse.Namespace) -> None:
    from scout.runner import run_scout, VALID_MODES
    from scout.db import expire_old_listings
    db_path = os.getenv("DB_PATH", "data/scout.db")
    if not args.dry_run:
        expired = expire_old_listings(days=21, db_path=db_path)
        if expired:
            console.print(f"[dim]Auto-ignored {expired} listing(s) older than 21 days.[/]")
    if not args.mode:
        console.print("[red]--mode is required for fetch runs. Choose: A (APAC), B (North America), C (Europe)")
        sys.exit(1)
    mode = args.mode.upper()
    if mode not in VALID_MODES:
        console.print(f"[red]Invalid mode '{mode}'. Choose from: {', '.join(VALID_MODES)}")
        sys.exit(1)
    run_scout(
        config_path=os.getenv("CONFIG_PATH", "config/criteria.yaml"),
        db_path=os.getenv("DB_PATH", "data/scout.db"),
        min_score_display=args.min_score,
        dry_run=args.dry_run,
        mode=mode,
    )


def cmd_top(args: argparse.Namespace) -> None:
    from scout.runner import print_top_by_mode, MODE_LABELS
    from scout.db import get_all_modes
    db_path = os.getenv("DB_PATH", "data/scout.db")
    # If a specific mode is requested show only that one, otherwise show all
    if args.mode:
        modes = [args.mode.upper()]
    else:
        modes = get_all_modes(db_path)
    print_top_by_mode(db_path, min_score=args.min_score, modes=modes)


def cmd_stats(args: argparse.Namespace) -> None:
    from scout.db import get_stats, get_all_modes
    from scout.runner import MODE_LABELS
    db_path = os.getenv("DB_PATH", "data/scout.db")
    modes = [args.mode.upper()] if args.mode else get_all_modes(db_path)

    console.print(f"\n[bold]Database stats[/]")
    for mode in modes:
        label = MODE_LABELS.get(mode, mode)
        stats = get_stats(db_path, scout_mode=mode)
        console.print(f"\n  [bold cyan]Mode {mode} - {label}[/]")
        console.print(f"    Total    : {stats['total']}")
        console.print(f"    Scored   : {stats['scored']}")
        console.print(f"    Unscored : {stats['unscored']}")
        console.print(f"    Avg score: {stats['avg_score']}")


def cmd_reset_failed_scores(args: argparse.Namespace) -> None:
    from scout.db import reset_failed_scores
    db_path = os.getenv("DB_PATH", "data/scout.db")
    count = reset_failed_scores(db_path)
    console.print(f"[green]{count} listing(s) put back to unscored.[/] "
                  "They will be scored at the next run.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto_Bot - Job Research Scout Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode", "-m",
        default=None,
        choices=["A", "B", "C", "a", "b", "c"],
        metavar="MODE",
        help="Search mode: A=APAC, B=North America, C=Northern Europe+Paris. "
             "Required for fetch runs, optional for --top/--stats (defaults to all modes).",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch only, no DB write, no scoring")
    parser.add_argument("--top", action="store_true",
                        help="Display top listings from DB without fetching")
    parser.add_argument("--stats", action="store_true",
                        help="Show DB statistics")
    parser.add_argument("--reset-failed-scores", action="store_true",
                        help="Put back to unscored the listings saved with 0 after a scoring "
                             "error (they are then re-scored at the next run)")
    parser.add_argument("--min-score", type=int, default=60,
                        help="Minimum score to display (default: 60)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.reset_failed_scores:
        cmd_reset_failed_scores(args)
    elif args.stats:
        cmd_stats(args)
    elif args.top:
        cmd_top(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
