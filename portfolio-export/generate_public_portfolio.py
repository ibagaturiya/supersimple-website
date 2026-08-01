#!/usr/bin/env python3
"""Generate the canonical full HTML and PDF portfolio."""

from generate import generate_full_portfolio


if __name__ == "__main__":
    html_path, pdf_path = generate_full_portfolio()
    print(f"Full portfolio HTML: {html_path}")
    print(f"Full portfolio PDF: {pdf_path}")
