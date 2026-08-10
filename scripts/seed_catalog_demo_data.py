"""Seed local catalog data for both HomePilot demo merchants."""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    from app.modules.catalog.demo_seed_cli import run_catalog_seed_command

    return asyncio.run(run_catalog_seed_command())


if __name__ == "__main__":
    raise SystemExit(main())
