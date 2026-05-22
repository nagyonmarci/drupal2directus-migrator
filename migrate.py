#!/usr/bin/env python3
"""
Main orchestrator for the Drupal 10 → Directus 11 migration.

Usage:
    python migrate.py --phase all
    python migrate.py --phase 1
    python migrate.py --phase 3,4
    python migrate.py --dry-run --phase 2
"""
import argparse
import sys
from importlib import import_module

from src.logger import get_logger

logger = get_logger("migrate")

PHASES: dict[int, str] = {
    1: "scripts.phase1_verify",
    2: "scripts.phase2_schema",
    3: "scripts.phase3_users",
    4: "scripts.phase4_files",
    5: "scripts.phase5_content",
    6: "scripts.phase6_blocks_views",
}

PHASE_NAMES: dict[int, str] = {
    1: "Preflight Verification",
    2: "Schema Extraction & Creation",
    3: "Identity & Access Migration",
    4: "Media & File Migration",
    5: "Content & Relational Data Migration",
    6: "Blocks & Views Handling",
}


def parse_phases(raw: str) -> list[int]:
    if raw.lower() == "all":
        return list(PHASES.keys())
    phases = []
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit() or int(part) not in PHASES:
            print(f"Error: '{part}' is not a valid phase number (1-6).", file=sys.stderr)
            sys.exit(1)
        phases.append(int(part))
    return sorted(set(phases))


def run_phase(phase_num: int, dry_run: bool) -> None:
    module_path = PHASES[phase_num]
    name = PHASE_NAMES[phase_num]
    logger.info(f"=== Phase {phase_num}: {name} {'[DRY RUN]' if dry_run else ''} ===")
    try:
        module = import_module(module_path)
        if dry_run and hasattr(module, "dry_run"):
            module.dry_run()
        else:
            module.main()
        logger.info(f"Phase {phase_num} completed successfully.")
    except Exception as e:
        logger.error(f"Phase {phase_num} failed: {e}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drupal 10 → Directus 11 migration orchestrator"
    )
    parser.add_argument(
        "--phase",
        default="all",
        help="Phase(s) to run: 'all', a single number (e.g. 2), or comma-separated (e.g. 3,4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing any data to Directus",
    )
    args = parser.parse_args()

    phases = parse_phases(args.phase)
    dry = args.dry_run

    logger.info(f"Migration starting — phases: {phases}{' [DRY RUN]' if dry else ''}")
    for phase_num in phases:
        run_phase(phase_num, dry)
    logger.info("Migration run complete.")


if __name__ == "__main__":
    main()
