from __future__ import annotations

import unittest

from testing.components.services.setup_repo_smoke_validator import (
    SetupRepoSmokeValidator,
)
from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.tests.support.setup_repo_smoke_probe_factory import (
    create_setup_repo_smoke_probe,
)

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

    def test_pages_time_to_interactive_meets_three_second_budget(self) -> None:
        self._skip_if_no_playwright()

        validator = SetupRepoSmokeValidator(
            config=self._config,
            probe=create_setup_repo_smoke_probe(self._config),
        )
        observation = validator.validate_pages_interactive()

        self.assertIsNotNone(
            observation,
            "Step 1 failed: no Pages time-to-interactive observation was produced.",
        )
        assert observation is not None

        self.assertIsNone(
            observation.error,
            "Step 2 failed: the interactive probe reported an error.\n"
            f"Error: {observation.error}",
        )
        self.assertEqual(
            observation.labels_found,
            self._config.shell_navigation_labels,
            "Step 3 failed: not all configured shell-navigation labels were visible.\n"
            f"Expected labels: {self._config.shell_navigation_labels}\n"
            f"Observed labels: {observation.labels_found}",
        )
        self.assertLessEqual(
            observation.elapsed_seconds,
            observation.budget_seconds,
            "Step 4 failed: time-to-interactive exceeded the configured budget.\n"
            f"Observed: {observation.elapsed_seconds:.3f}s "
            f"Budget: {observation.budget_seconds:.3f}s",
        )
        self.assertTrue(
            observation.within_budget,
            "Step 5 failed: the Pages time-to-interactive observation did not "
            "report within_budget=true.",
        )
        self.assertGreaterEqual(
            observation.elapsed_seconds,
            0.0,
            "Step 6 failed: elapsed time-to-interactive is negative.",
        )


if __name__ == "__main__":
    unittest.main()
