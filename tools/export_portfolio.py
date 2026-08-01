#!/usr/bin/env python3
"""Launch the local tailored CV and portfolio export dashboard.

Run from anywhere with:
    python3 tools/export_portfolio.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "start-application-generator.py"


def main() -> None:
    if not LAUNCHER.is_file():
        raise FileNotFoundError(f"Portfolio launcher not found: {LAUNCHER}")

    print("Opening the local portfolio export dashboard at http://127.0.0.1:8765/")
    print("Stop it with Control-C when you are finished.")
    runpy.run_path(str(LAUNCHER), run_name="__main__")


if __name__ == "__main__":
    main()
