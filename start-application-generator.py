#!/usr/bin/env python3
"""Stable launcher for the private tailored-application dashboard."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "portfolio-export"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python3"

if (
    VENV_PYTHON.exists()
    and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve()
):
    environment = os.environ.copy()
    environment.pop("__PYVENV_LAUNCHER__", None)
    os.execve(
        str(VENV_PYTHON),
        [str(VENV_PYTHON), __file__, *sys.argv[1:]],
        environment,
    )

sys.path.insert(0, str(APP_DIR))
runpy.run_path(str(APP_DIR / "app.py"), run_name="__main__")
