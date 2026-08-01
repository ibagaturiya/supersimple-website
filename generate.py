#!/usr/bin/env python3
"""Compatibility entry point for the static-site generator."""

import subprocess
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

from tools.site_generator import main


def run_public_export(script_name):
    root = Path(__file__).resolve().parent
    local_python = root / ".venv" / "bin" / "python3"
    python = local_python if local_python.exists() else Path(sys.executable)
    subprocess.run(
        [str(python), str(root / "portfolio-export" / script_name)],
        cwd=root,
        check=True,
    )


def create_full_application_package():
    root = Path(__file__).resolve().parent
    downloads = root / "assets" / "downloads"
    cv_path = downloads / "Ivan_Bagaturiya_CV.pdf"
    portfolio_path = downloads / "Ivan_Bagaturiya_Portfolio.pdf"
    package_path = downloads / "Ivan_Bagaturiya_Full_CV_and_Portfolio.zip"
    missing = [path.name for path in (cv_path, portfolio_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Cannot create full application package; missing: " + ", ".join(missing)
        )
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(cv_path, cv_path.name)
        archive.write(portfolio_path, portfolio_path.name)
    print(f"Full CV + portfolio package: {package_path}")


if __name__ == "__main__":
    main()
    run_public_export("generate_public_cv.py")
    run_public_export("generate_public_portfolio.py")
    create_full_application_package()
