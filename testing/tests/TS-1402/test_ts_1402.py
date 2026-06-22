from __future__ import annotations

import unittest

from testing.components.services.setup_repo_smoke_validator import (
    SetupRepoSmokeValidator,
)
from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.tests.support.setup_repo_smoke_probe_factory import (
    create_setup_repo_smoke_probe,
)


class SetupRepoIntegratedSmokePathTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def test_mvp_workflow_creates_transitions_and_searches_tracker_data(self) -> None:
        validator = SetupRepoSmokeValidator(
            config=self._config,
            probe=create_setup_repo_smoke_probe(self._config),
        )
        result = validator.validate_full_smoke()

        self.assertIsNotNone(
            result.cli_smoke,
            "Step 1 failed: CLI smoke observation was not produced. "
            "This usually means no auth token was available.",
        )
        cli_smoke = result.cli_smoke
        assert cli_smoke is not None

        self.assertTrue(
            cli_smoke.session is not None and cli_smoke.session.succeeded,
            "Step 2 failed: hosted session probe did not succeed.\n"
            f"Command: {cli_smoke.session.command if cli_smoke.session else None}\n"
            f"Error: {cli_smoke.session.error if cli_smoke.session else 'N/A'}",
        )
        self.assertTrue(
            cli_smoke.create is not None and cli_smoke.create.succeeded,
            "Step 3 failed: issue creation did not succeed.\n"
            f"Command: {cli_smoke.create.command if cli_smoke.create else None}\n"
            f"Error: {cli_smoke.create.error if cli_smoke.create else 'N/A'}",
        )
        self.assertIsNotNone(
            cli_smoke.create and cli_smoke.create.issue_key,
            "Step 3 failed: created issue key was not extracted from the CLI output.",
        )
        self.assertTrue(
            cli_smoke.transition is not None and cli_smoke.transition.succeeded,
            "Step 4 failed: workflow transition did not succeed.\n"
            f"Command: {cli_smoke.transition.command if cli_smoke.transition else None}\n"
            f"Error: {cli_smoke.transition.error if cli_smoke.transition else 'N/A'}",
        )
        self.assertTrue(
            cli_smoke.search is not None and cli_smoke.search.succeeded,
            "Step 5 failed: JQL search did not succeed.\n"
            f"Command: {cli_smoke.search.command if cli_smoke.search else None}\n"
            f"Error: {cli_smoke.search.error if cli_smoke.search else 'N/A'}",
        )
        self.assertTrue(
            cli_smoke.cleanup is not None and cli_smoke.cleanup.succeeded,
            "Step 6 failed: cleanup transition did not succeed.\n"
            f"Command: {cli_smoke.cleanup.command if cli_smoke.cleanup else None}\n"
            f"Error: {cli_smoke.cleanup.error if cli_smoke.cleanup else 'N/A'}",
        )
        self.assertTrue(
            cli_smoke.delete is not None and cli_smoke.delete.succeeded,
            "Step 7 failed: issue deletion did not succeed.\n"
            f"Command: {cli_smoke.delete.command if cli_smoke.delete else None}\n"
            f"Error: {cli_smoke.delete.error if cli_smoke.delete else 'N/A'}",
        )

        self.assertTrue(
            cli_smoke.all_succeeded,
            "Step 8 failed: the integrated smoke path did not report full success.",
        )


if __name__ == "__main__":
    unittest.main()
