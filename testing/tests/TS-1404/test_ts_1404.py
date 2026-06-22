from __future__ import annotations

import unittest

from testing.components.services.setup_repo_smoke_validator import (
    SetupRepoSmokeValidator,
)
from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.tests.support.setup_repo_smoke_probe_factory import (
    create_setup_repo_smoke_probe,
)


class CliPerformanceBenchmarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def test_ten_concurrent_processes_maintain_zero_error_rate_and_p95_latency(self) -> None:
        validator = SetupRepoSmokeValidator(
            config=self._config,
            probe=create_setup_repo_smoke_probe(self._config),
        )
        observation = validator.validate_cli_benchmark()

        self.assertIsNotNone(
            observation,
            "Step 1 failed: CLI benchmark observation was not produced. "
            "This usually means no auth token was available.",
        )
        assert observation is not None

        self.assertEqual(
            observation.concurrency,
            10,
            "Step 2 failed: benchmark did not run with the expected 10 concurrent workers.\n"
            f"Observed concurrency: {observation.concurrency}",
        )
        self.assertEqual(
            observation.failed_commands,
            0,
            "Step 3 failed: benchmark reported failed commands.\n"
            f"Successful: {observation.successful_commands}\n"
            f"Failed: {observation.failed_commands}\n"
            f"Errors: {observation.errors}",
        )
        self.assertEqual(
            observation.total_commands,
            observation.successful_commands,
            "Step 3 failed: not all benchmark commands succeeded.",
        )
        self.assertLessEqual(
            observation.p95_seconds,
            observation.budget_seconds,
            "Step 4 failed: p95 latency exceeded the budget.\n"
            f"Observed p95: {observation.p95_seconds:.3f}s "
            f"Budget: {observation.budget_seconds:.3f}s",
        )
        self.assertLessEqual(
            observation.max_seconds,
            observation.max_budget_seconds,
            "Step 5 failed: maximum latency exceeded the allowed ceiling.\n"
            f"Observed max: {observation.max_seconds:.3f}s "
            f"Ceiling: {observation.max_budget_seconds:.3f}s",
        )
        self.assertTrue(
            observation.passed,
            "Step 6 failed: the benchmark did not report an overall pass.",
        )


if __name__ == "__main__":
    unittest.main()
