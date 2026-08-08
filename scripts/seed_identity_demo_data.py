"""Seed local HomePilot identity data without exposing demo credentials."""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    """Load the backend package after adding its project directory to sys.path."""

    from app.modules.identity.demo_seed_cli import run_demo_seed_command

    return asyncio.run(run_demo_seed_command())


if __name__ == "__main__":
    raise SystemExit(main())
