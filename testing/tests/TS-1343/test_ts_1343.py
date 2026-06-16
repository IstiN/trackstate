from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from testing.core.config.release_workflow_static_config import (
    ReleaseWorkflowStaticConfig,
)
from testing.tests.support.release_workflow_static_validator_factory import (
    create_release_workflow_static_validator,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class ReleaseValidationGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ReleaseWorkflowStaticConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-1343" / "config.yaml",
            repository_root=REPO_ROOT,
        )
        self.validator = create_release_workflow_static_validator(REPO_ROOT)

    def test_platform_builds_depend_on_validation(self) -> None:
        observation = self.validator.validate(self.config)
        self._write_result_if_requested(observation.to_dict())

        self.assertTrue(
            observation.workflow_exists,
            f"Workflow file not found: {observation.workflow_path}",
        )
        self.assertFalse(
            observation.failures,
            "Static validation failed:\n" + "\n".join(observation.failures),
        )

        job_names = set(observation.jobs.keys())
        self.assertIn("validate", job_names)
        self.assertIn("build-linux", job_names)
        self.assertIn("build-windows", job_names)
        self.assertIn("build-macos", job_names)

        for job_name in ("build-linux", "build-windows", "build-macos"):
            needs = observation.jobs[job_name].get("needs")
            self.assertIn(
                "validate",
                needs if isinstance(needs, list) else [needs],
                f"Job '{job_name}' does not depend on validation.",
            )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1343_RESULT_PATH")
        if not result_path:
            return
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
