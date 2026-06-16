from __future__ import annotations

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

from testing.core.config.desktop_auth_ui_config import DesktopAuthUIConfig
from testing.tests.support.desktop_auth_ui_validator_factory import (
    create_desktop_auth_ui_validator,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_TEST_PATH = REPO_ROOT / "testing" / "tests" / "TS-1354" / "test_ts_1354_runtime.dart"


class DesktopAuthenticationUITest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = DesktopAuthUIConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-1354" / "config.yaml",
            repository_root=REPO_ROOT,
        )
        self.validator = create_desktop_auth_ui_validator(REPO_ROOT)

    def test_desktop_auth_ui_excludes_github_app_oauth(self) -> None:
        static_observation = self.validator.validate(self.config)
        runtime_observation = self._run_runtime_widget_test()

        combined = {
            "test_id": self.config.test_id,
            "static": static_observation.to_dict(),
            "runtime": runtime_observation,
            "failures": self._collect_failures(
                static_observation,
                runtime_observation,
            ),
        }
        self._write_result_if_requested(combined)

        self.assertTrue(
            static_observation.workflow_exists,
            f"Workflow file not found: {static_observation.workflow_path}",
        )
        self.assertTrue(
            static_observation.auth_source_exists,
            "Auth source file not found.",
        )
        self.assertFalse(
            static_observation.failures,
            "Static desktop auth UI guards failed:\n"
            + "\n".join(static_observation.failures),
        )

        runtime_failures = runtime_observation.get("failures", [])
        self.assertFalse(
            runtime_failures,
            "Runtime desktop auth UI validation failed:\n"
            + "\n".join(str(f) for f in runtime_failures),
        )

    def _run_runtime_widget_test(self) -> dict[str, object]:
        command = [
            "flutter",
            "test",
            str(RUNTIME_TEST_PATH),
            "--dart-define=TRACKSTATE_GITHUB_APP_CLIENT_ID=",
            "--dart-define=TRACKSTATE_GITHUB_AUTH_PROXY_URL=",
            "--reporter",
            "expanded",
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        observation = self._extract_observation(completed.stdout + completed.stderr)
        if observation is None:
            observation = {}

        failures: list[str] = []
        if completed.returncode != 0:
            failures.append(
                f"flutter test exited with code {completed.returncode}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

        return {
            "command": " ".join(command),
            "exit_code": completed.returncode,
            "observation": observation,
            "failures": failures,
        }

    def _extract_observation(self, combined_output: str) -> dict[str, object] | None:
        for line in combined_output.splitlines():
            match = re.search(r"TS-1354-OBSERVATION:(\{.*\})", line)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _collect_failures(
        self,
        static_observation: object,
        runtime_observation: dict[str, object],
    ) -> list[str]:
        failures = list(getattr(static_observation, "failures", []))
        runtime_failures = runtime_observation.get("failures")
        if isinstance(runtime_failures, list):
            failures.extend(str(f) for f in runtime_failures)
        return failures

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1354_RESULT_PATH")
        if not result_path:
            return
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
