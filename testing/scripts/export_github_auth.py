#!/usr/bin/env python3
"""Export GitHub authenticated browser session for Playwright tests.

Usage:
    python testing/scripts/export_github_auth.py [output_path]

If output_path is omitted, defaults to ~/.github_browser_auth.json

This script opens a visible Chromium window, navigates to github.com/login,
and waits for the user to complete authentication. Once authenticated,
the browser storage state (cookies + localStorage) is saved to the output
file so that Playwright tests can reuse the session without manual login.

Set the environment variable before running TS-909:
    export GITHUB_BROWSER_AUTH_SESSION="$HOME/.github_browser_auth.json"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export GitHub auth session for Playwright tests",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=str(Path.home() / ".github_browser_auth.json"),
        help="Path to save the storage state JSON (default: ~/.github_browser_auth.json)",
    )
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Error: Playwright is not installed.\n"
            "Install it: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 1

    print("Opening Chromium for GitHub authentication...")
    print("1. Log into github.com in the opened browser window")
    print("2. Complete any 2FA if prompted")
    print("3. Press Enter here AFTER you see the GitHub dashboard")
    print("")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://github.com/login")

        input("Press Enter once you are logged in and see the GitHub dashboard... ")

        # Save storage state
        context.storage_state(path=str(output_path))
        browser.close()

    print(f"\n✅ GitHub auth session saved to: {output_path}")
    print(f"\nSet this environment variable before running TS-909:")
    print(f'    export GITHUB_BROWSER_AUTH_SESSION="{output_path}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
