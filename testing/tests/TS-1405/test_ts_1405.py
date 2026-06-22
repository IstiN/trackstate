from __future__ import annotations

import unittest

from testing.components.services.setup_repo_smoke_validator import (
    SetupRepoSmokeValidator,
)
from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.tests.support.setup_repo_smoke_probe_factory import (
    create_setup_repo_smoke_probe,
)


class CiSmokeReportingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def test_smoke_summary_includes_pages_load_time_and_benchmark_percentiles(self) -> None:
        validator = SetupRepoSmokeValidator(
            config=self._config,
            probe=create_setup_repo_smoke_probe(self._config),
        )
        result = validator.validate_full_smoke()
        payload = result.to_dict()

        self.assertIn(
            "pages_interactive",
            payload,
            "Step 1 failed: smoke summary does not contain a pages_interactive section.",
        )
        pages_interactive = payload["pages_interactive"]
        self.assertIsNotNone(
            pages_interactive,
            "Step 1 failed: pages_interactive is null.",
        )
        self.assertIn(
            "elapsed_seconds",
            pages_interactive,
            "Step 2 failed: pages_interactive is missing elapsed_seconds.",
        )
        self.assertIsInstance(
            pages_interactive["elapsed_seconds"],
            (int, float),
            "Step 2 failed: pages_interactive.elapsed_seconds is not numeric.",
        )
        self.assertGreaterEqual(
            pages_interactive["elapsed_seconds"],
            0.0,
            "Step 2 failed: pages_interactive.elapsed_seconds is negative.",
        )

        self.assertIn(
            "cli_benchmark",
            payload,
            "Step 3 failed: smoke summary does not contain a cli_benchmark section.",
        )
        cli_benchmark = payload["cli_benchmark"]
        self.assertIsNotNone(
            cli_benchmark,
            "Step 3 failed: cli_benchmark is null.",
        )
        self.assertIn(
            "p95_seconds",
            cli_benchmark,
            "Step 4 failed: cli_benchmark is missing p95_seconds.",
        )
        self.assertIn(
            "max_seconds",
            cli_benchmark,
            "Step 4 failed: cli_benchmark is missing max_seconds.",
        )
        self.assertIsInstance(
            cli_benchmark["p95_seconds"],
            (int, float),
            "Step 4 failed: cli_benchmark.p95_seconds is not numeric.",
        )
        self.assertIsInstance(
            cli_benchmark["max_seconds"],
            (int, float),
            "Step 4 failed: cli_benchmark.max_seconds is not numeric.",
        )
        self.assertGreaterEqual(
            cli_benchmark["p95_seconds"],
            0.0,
            "Step 4 failed: cli_benchmark.p95_seconds is negative.",
        )

        self.assertIn(
            "pages_health",
            payload,
            "Step 5 failed: smoke summary does not contain a pages_health section.",
        )
        pages_health = payload["pages_health"]
        self.assertIsNotNone(
            pages_health,
            "Step 5 failed: pages_health is null.",
        )


if __name__ == "__main__":
    unittest.main()
