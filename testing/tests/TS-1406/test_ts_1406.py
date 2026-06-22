from __future__ import annotations

import unittest

from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config


try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when Playwright is absent
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = TimeoutError  # type: ignore[misc]
    PLAYWRIGHT_AVAILABLE = False


class ObservedPagesShellVisualQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def _skip_if_no_playwright(self) -> None:
        if not PLAYWRIGHT_AVAILABLE or sync_playwright is None:
            self.skipTest("Playwright is not available; cannot observe Pages shell.")

    def test_pages_shell_renders_with_expected_title_and_bootstrap(self) -> None:
        self._skip_if_no_playwright()

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
                    response = page.goto(
                        self._config.app_url,
                        wait_until="domcontentloaded",
                        timeout=120_000,
                    )
                    self.assertIsNotNone(
                        response,
                        "Step 1 failed: no HTTP response was received from the Pages URL.",
                    )
                    self.assertEqual(
                        response.status if response else 0,
                        200,
                        "Step 1 failed: Pages URL did not return HTTP 200.",
                    )

                    title = page.title()
                    self.assertEqual(
                        title.strip(),
                        self._config.expected_title,
                        "Step 2 failed: the rendered page title does not match the expected title.\n"
                        f"Expected: {self._config.expected_title}\n"
                        f"Observed: {title}",
                    )

                    base_href = page.locator("base").get_attribute("href")
                    self.assertEqual(
                        base_href,
                        self._config.expected_base_href,
                        "Step 3 failed: the base href does not match the expected Pages path.\n"
                        f"Expected: {self._config.expected_base_href}\n"
                        f"Observed: {base_href}",
                    )

                    bootstrap_present = page.locator(
                        'script[src*="flutter_bootstrap.js"]'
                    ).count() > 0 or "flutter_bootstrap.js" in page.content()
                    self.assertTrue(
                        bootstrap_present,
                        "Step 4 failed: the Flutter bootstrap script was not found in the Pages shell.",
                    )
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()

    def test_pages_shell_sign_in_prompt_is_visible(self) -> None:
        """Verify the pre-authentication shell renders a readable sign-in prompt.

        The full navigation labels require an authenticated session; this test
        confirms the unauthenticated shell is at least reachable and legible.
        """
        self._skip_if_no_playwright()

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
                    page.goto(
                        self._config.app_url,
                        wait_until="domcontentloaded",
                        timeout=120_000,
                    )
                    page.wait_for_selector(
                        "flt-semantics-host",
                        state="attached",
                        timeout=60_000,
                    )
                    page.wait_for_function(
                        """
                        () => {
                            const text = document.body?.innerText ?? '';
                            return text.includes('Needs sign-in') && text.includes('Workspace switcher');
                        }
                        """,
                        timeout=60_000,
                    )
                    body_text = page.inner_text("body")
                    self.assertIn(
                        "Needs sign-in",
                        body_text,
                        "Step 1 failed: the pre-authentication 'Needs sign-in' prompt "
                        "was not visible in the rendered Pages shell.",
                    )
                    self.assertIn(
                        "Workspace switcher",
                        body_text,
                        "Step 1 failed: the workspace switcher label was not visible.",
                    )
                except Exception as error:
                    self.fail(
                        "Step 1 failed: timed out waiting for the Flutter shell text.\n"
                        f"Error: {error}"
                    )
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()

    def test_pages_shell_focusable_elements_have_accessible_names(self) -> None:
        self._skip_if_no_playwright()

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
                    page.goto(
                        self._config.app_url,
                        wait_until="domcontentloaded",
                        timeout=120_000,
                    )
                    page.wait_for_selector(
                        "flt-semantics-host",
                        state="attached",
                        timeout=60_000,
                    )

                    focusable = page.query_selector_all(
                        'body button, body a[href], body input, body select, body textarea, '
                        'body [tabindex]:not([tabindex="-1"])'
                    )
                    unnamed: list[str] = []
                    for element in focusable:
                        # Skip elements that are not actually rendered or interactive.
                        if not element.is_visible():
                            continue
                        aria_label = element.get_attribute("aria-label") or ""
                        aria_labelled_by = element.get_attribute("aria-labelledby") or ""
                        text = (element.inner_text() or "").strip()
                        title = element.get_attribute("title") or ""
                        role = element.get_attribute("role") or element.evaluate(
                            "el => el.tagName.toLowerCase()"
                        )
                        if aria_label.strip():
                            continue
                        if aria_labelled_by.strip():
                            continue
                        if text:
                            continue
                        if title.strip():
                            continue
                        unnamed.append(
                            f"<{role}> aria-label={aria_label!r} text={text!r}"
                        )

                    self.assertEqual(
                        unnamed,
                        [],
                        "Step 1 failed: focusable elements were found without accessible names.\n"
                        f"Elements: {unnamed[:20]}",
                    )
                except PlaywrightTimeoutError as error:
                    self.fail(
                        "Step 1 failed: timed out waiting for the Flutter semantics host.\n"
                        f"Error: {error}"
                    )
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
