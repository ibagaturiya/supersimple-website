#!/usr/bin/env python3
"""Compatibility entry point for the static-site generator."""

import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from tools.site_generator import main


def generate_public_cv():
    root = Path(__file__).resolve().parent
    local_python = root / ".venv" / "bin" / "python3"
    python = local_python if local_python.exists() else Path(sys.executable)
    subprocess.run(
        [str(python), str(root / "portfolio-export" / "generate_public_cv.py")],
        cwd=root,
        check=True,
    )


if __name__ == "__main__":
    main()
    generate_public_cv()
