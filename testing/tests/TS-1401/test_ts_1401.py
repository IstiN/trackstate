from __future__ import annotations

import os
import unittest

from testing.components.services.setup_repo_smoke_validator import (
    SetupRepoSmokeValidator,
)
from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.tests.support.setup_repo_smoke_probe_factory import (
    create_setup_repo_smoke_probe,
)


class RuntimeVariablesValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()

    def _token_present(self) -> bool:
        return any(
            os.environ.get(name, "").strip() != ""
            for name in self._config.auth_token_variables
        )

    def test_preflight_detects_at_least_one_auth_token(self) -> None:
        validator = SetupRepoSmokeValidator(
            config=self._config,
            probe=create_setup_repo_smoke_probe(self._config),
        )
        observations = validator.validate_runtime_variables()

        self.assertTrue(
            observations,
            "Step 1 failed: no runtime variables were configured for validation.",
        )
        names = tuple(obs.name for obs in observations)
        self.assertEqual(
            names,
            self._config.auth_token_variables,
            "Step 1 failed: observed variables do not match the configured set.",
        )

        present = [obs for obs in observations if obs.present]
        self.assertTrue(
            present,
            "Step 2 failed: none of the configured auth-token variables are present. "
            f"Expected at least one of {self._config.auth_token_variables}.",
        )

        for observation in observations:
            with self.subTest(variable=observation.name):
                self.assertIsInstance(
                    observation.present,
                    bool,
                    f"Step 3 failed: presence flag for {observation.name} is not boolean.",
                )

    def test_preflight_reports_missing_tokens_when_none_present(self) -> None:
        """Sanity-check the pre-flight logic under a no-token environment."""
        env_backup = {
            name: os.environ.pop(name, None)
            for name in self._config.auth_token_variables
        }
        try:
            validator = SetupRepoSmokeValidator(
                config=self._config,
                probe=create_setup_repo_smoke_probe(self._config),
            )
            observations = validator.validate_runtime_variables()

            self.assertTrue(
                observations,
                "Step 1 failed: no runtime variables were configured for validation.",
            )

            for observation in observations:
                with self.subTest(variable=observation.name):
                    self.assertFalse(
                        observation.present,
                        f"Step 2 failed: {observation.name} should be reported as missing "
                        "when all token variables are cleared.",
                    )
        finally:
            for name, value in env_backup.items():
                if value is not None:
                    os.environ[name] = value
                else:
                    os.environ.pop(name, None)

    def test_preflight_does_not_accept_malformed_empty_tokens(self) -> None:
        """Whitespace-only token values must be treated as missing."""
        env_backup = {
            name: os.environ.get(name, "")
            for name in self._config.auth_token_variables
        }
        try:
            for name in self._config.auth_token_variables:
                os.environ[name] = "   \n\t  "

            validator = SetupRepoSmokeValidator(
                config=self._config,
                probe=create_setup_repo_smoke_probe(self._config),
            )
            observations = validator.validate_runtime_variables()

            for observation in observations:
                with self.subTest(variable=observation.name):
                    self.assertFalse(
                        observation.present,
                        f"Step 1 failed: whitespace-only value for {observation.name} "
                        "was incorrectly accepted as a valid token.",
                    )
        finally:
            for name, value in env_backup.items():
                os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
