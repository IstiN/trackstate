from __future__ import annotations

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


class InstallScriptAssetAvailabilityStaticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ReleaseWorkflowStaticConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-1357" / "config.yaml",
            repository_root=REPO_ROOT,
        )
        self.validator = create_release_workflow_static_validator(REPO_ROOT)

    def test_install_script_source_files_exist_and_are_published_as_standalone_assets(self) -> None:
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

        publish_release = observation.jobs.get("publish-release", {})
        job_text = __import__("json").dumps(publish_release)
        for asset in ("install.sh", "install.ps1", "install.cmd"):
            self.assertIn(
                asset,
                job_text,
                f"Publish-release job does not reference standalone asset '{asset}'",
            )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1357_RESULT_PATH")
        if not result_path:
            return
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            __import__("json").dumps(payload, indent=2, sort_keys=True) + "\n"
        )


if __name__ == "__main__":
    unittest.main()
