#!/usr/bin/env python3
"""Compatibility entry point for the static-site generator."""

import sys

sys.dont_write_bytecode = True

from tools.site_generator import main


if __name__ == "__main__":
    main()
