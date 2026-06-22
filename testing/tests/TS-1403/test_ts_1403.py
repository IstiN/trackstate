from __future__ import annotations

import time
import unittest

from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when Playwright is absent
    sync_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False


class PagesPerformanceNfrTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def _skip_if_no_playwright(self) -> None:
        if not PLAYWRIGHT_AVAILABLE or sync_playwright is None:
            self.skipTest("Playwright is not available; cannot measure Pages performance.")

    def test_pages_initial_load_meets_three_second_budget(self) -> None:
        self._skip_if_no_playwright()

        budget = self._config.page_interactive_budget_seconds
        url = self._config.app_url

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                args=[
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                ]
            )
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                try:
                    # Warm the cache with a single load.
                    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                    page.wait_for_timeout(500)

                    started_at = time.monotonic()
                    response = page.goto(
                        url, wait_until="domcontentloaded", timeout=120_000
                    )
                    elapsed = time.monotonic() - started_at

                    self.assertIsNotNone(
                        response,
                        "Step 1 failed: no HTTP response was received from the Pages URL.",
                    )
                    self.assertEqual(
                        response.status if response else 0,
                        200,
                        "Step 1 failed: Pages URL did not return HTTP 200.",
                    )
                    self.assertLessEqual(
                        elapsed,
                        budget,
                        "Step 2 failed: Pages initial load exceeded the 3-second budget.\n"
                        f"Observed: {elapsed:.3f}s Budget: {budget:.3f}s",
                    )

                    title = page.title().strip()
                    self.assertEqual(
                        title,
                        self._config.expected_title,
                        "Step 3 failed: the rendered page title does not match the expected title.\n"
                        f"Expected: {self._config.expected_title}\nObserved: {title}",
                    )

                    bootstrap_present = page.locator(
                        'script[src*="flutter_bootstrap.js"]'
                    ).count() > 0 or "flutter_bootstrap.js" in page.content()
                    self.assertTrue(
                        bootstrap_present,
                        "Step 4 failed: the Flutter bootstrap script was not loaded.",
                    )
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
