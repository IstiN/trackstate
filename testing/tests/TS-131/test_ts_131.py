from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.components.services.hardcoded_hex_lint_validator import (
    HardcodedHexLintValidator,
)
from testing.core.config.hardcoded_hex_lint_config import HardcodedHexLintConfig
from testing.core.config.theme_token_ci_config import ThemeTokenCiConfig
from testing.core.interfaces.theme_token_ci_probe import ThemeTokenCiProbe
from testing.core.models.hardcoded_hex_lint_validation_result import (
    HardcodedHexLintValidationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (
    create_flutter_analyze_probe,
)
from testing.tests.support.theme_token_ci_probe_factory import (
    create_theme_token_ci_probe,
)


class ThemeTokenPullRequestGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.ci_config = ThemeTokenCiConfig.from_file(
            self.repository_root / "testing/tests/TS-131/config.yaml"
        )
        self.lint_config = HardcodedHexLintConfig.from_env()
        self.probe: ThemeTokenCiProbe = create_theme_token_ci_probe(self.repository_root)
        flutter_probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.lint_config.flutter_version,
        )
        self.lint_validator = HardcodedHexLintValidator(
            self.repository_root,
            flutter_probe,
        )

    def test_pull_request_ci_gate_blocks_non_tokenized_colors(self) -> None:
        workflow_observation = self.probe.validate()
        lint_result = self.lint_validator.validate(config=self.lint_config)
        self._write_result_if_requested(
            workflow_observation=workflow_observation.to_dict(),
            lint_result=lint_result,
        )

        self.assertEqual(
            workflow_observation.repository,
            self.ci_config.repository,
            "Step 1 failed: the live CI verification targeted the wrong repository.\n"
            f"Expected repository: {self.ci_config.repository}\n"
            f"Observed repository: {workflow_observation.repository}",
        )
        self.assertEqual(
            workflow_observation.workflow_path,
            self.ci_config.workflow_path,
            "Step 1 failed: the live CI verification targeted the wrong workflow file.\n"
            f"Expected workflow path: {self.ci_config.workflow_path}\n"
            f"Observed workflow path: {workflow_observation.workflow_path}",
        )
        self.assertEqual(
            workflow_observation.workflow_name,
            self.ci_config.workflow_name,
            "Step 1 failed: the live GitHub Actions workflow name changed.\n"
            f"Expected workflow name: {self.ci_config.workflow_name}\n"
            f"Observed workflow name: {workflow_observation.workflow_name}",
        )
        self.assertTrue(
            workflow_observation.workflow_declares_pull_request_trigger,
            "Step 2 failed: the live workflow source no longer declares a "
            "`pull_request` trigger, so a Pull Request would not be blocked by "
            "this gate.\n"
            f"Workflow URL: {workflow_observation.workflow_html_url}\n"
            f"Observed workflow text:\n{workflow_observation.workflow_text}",
        )
        self.assertTrue(
            workflow_observation.workflow_declares_gate_step,
            "Step 2 failed: the live workflow source no longer visibly declares "
            f"the `{self.ci_config.workflow_step_name}` step.\n"
            f"Workflow URL: {workflow_observation.workflow_html_url}\n"
            f"Observed workflow text:\n{workflow_observation.workflow_text}",
        )
        self.assertTrue(
            workflow_observation.workflow_declares_gate_command,
            "Step 2 failed: the live workflow source no longer runs the theme-token "
            "policy command, so the Pull Request gate would not execute.\n"
            f"Expected command: {self.ci_config.gate_command}\n"
            f"Workflow URL: {workflow_observation.workflow_html_url}\n"
            f"Observed workflow text:\n{workflow_observation.workflow_text}",
        )

        self.assertTrue(
            workflow_observation.pull_request_head_branch.startswith(
                self.ci_config.branch_prefix
            ),
            "Step 3 failed: the disposable pull request did not use the configured "
            "TS-131 branch prefix.\n"
            f"Observed branch: {workflow_observation.pull_request_head_branch}",
        )
        self.assertEqual(
            workflow_observation.pull_request_probe_path,
            self.ci_config.probe_path,
            "Step 3 failed: the disposable pull request did not commit the expected "
            "probe file path.\n"
            f"Expected probe path: {self.ci_config.probe_path}\n"
            f"Observed probe path: {workflow_observation.pull_request_probe_path}",
        )
        self.assertEqual(
            workflow_observation.latest_pull_request_run_event,
            "pull_request",
            "Step 3 failed: the observed workflow run was not triggered by the "
            "disposable Pull Request.\n"
            f"Run URL: {workflow_observation.latest_pull_request_run_url}\n"
            f"Observed event: {workflow_observation.latest_pull_request_run_event}",
        )
        self.assertEqual(
            workflow_observation.latest_pull_request_run_conclusion,
            "failure",
            "Step 3 failed: the disposable Pull Request workflow run did not fail "
            "as required for a merge-blocking theme-token gate.\n"
            f"Pull Request URL: {workflow_observation.pull_request_url}\n"
            f"Run URL: {workflow_observation.latest_pull_request_run_url}\n"
            f"Status: {workflow_observation.latest_pull_request_run_status}\n"
            f"Conclusion: {workflow_observation.latest_pull_request_run_conclusion}",
        )
        self.assertIn(
            self.ci_config.workflow_job_name,
            workflow_observation.observed_job_names,
            "Step 3 failed: the disposable Pull Request workflow run did not expose "
            "the expected job name.\n"
            f"Run URL: {workflow_observation.latest_pull_request_run_url}\n"
            f"Observed job names: {workflow_observation.observed_job_names}",
        )
        self.assertIn(
            self.ci_config.workflow_step_name,
            workflow_observation.observed_step_names,
            "Step 3 failed: the disposable Pull Request workflow run did not expose "
            "the theme-token gate step in the job details.\n"
            f"Run URL: {workflow_observation.latest_pull_request_run_url}\n"
            f"Observed step names: {workflow_observation.observed_step_names}",
        )
        self.assertEqual(
            workflow_observation.theme_token_step_conclusion,
            "failure",
            "Human-style verification failed for Step 3: GitHub Actions did not "
            "show the `Enforce theme tokens` step failing on the disposable "
            "Pull Request.\n"
            f"Pull Request URL: {workflow_observation.pull_request_url}\n"
            f"Run URL: {workflow_observation.latest_pull_request_run_url}\n"
            f"Matched job: {workflow_observation.theme_token_job_name}\n"
            f"Step status: {workflow_observation.theme_token_step_status}\n"
            f"Step conclusion: {workflow_observation.theme_token_step_conclusion}",
        )
        self.assertEqual(
            workflow_observation.pull_request_mergeable_state,
            "blocked",
            "Step 3 failed: GitHub did not report the disposable Pull Request as "
            "blocked after the failing theme-token gate.\n"
            f"Pull Request URL: {workflow_observation.pull_request_url}\n"
            f"Observed mergeable state: "
            f"{workflow_observation.pull_request_mergeable_state}\n"
            f"Observed status state: {workflow_observation.pull_request_status_state}",
        )
        self.assertEqual(
            workflow_observation.pull_request_status_state,
            "failure",
            "Step 3 failed: GitHub did not report failing status checks for the "
            "disposable Pull Request head commit.\n"
            f"Pull Request URL: {workflow_observation.pull_request_url}\n"
            f"Observed status state: {workflow_observation.pull_request_status_state}",
        )

        self.assertTrue(
            lint_result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-131.\n"
            f"Command: {lint_result.flutter_version.command_text}\n"
            f"Exit code: {lint_result.flutter_version.exit_code}\n"
            f"stdout:\n{lint_result.flutter_version.stdout}\n"
            f"stderr:\n{lint_result.flutter_version.stderr}",
        )
        self.assertTrue(
            lint_result.pub_get.succeeded,
            "Precondition failed: `flutter pub get` did not complete in the "
            "temporary reproduction project, so TS-131 could not run the real "
            "policy gate.\n"
            f"Command: {lint_result.pub_get.command_text}\n"
            f"Exit code: {lint_result.pub_get.exit_code}\n"
            f"stdout:\n{lint_result.pub_get.stdout}\n"
            f"stderr:\n{lint_result.pub_get.stderr}",
        )

        tokenized_output = HardcodedHexLintValidationResult.combine_output(
            lint_result.tokenized_analyze,
        )
        self.assertTrue(
            lint_result.tokenized_analyze.succeeded,
            "Step 4 failed: the tokenized Flutter probe did not pass the same "
            "theme-token policy gate that CI executes.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Command: {lint_result.tokenized_analyze.command_text}\n"
            f"Exit code: {lint_result.tokenized_analyze.exit_code}\n"
            f"Observed output:\n{tokenized_output}",
        )
        self.assertIn(
            "No theme token policy violations found.",
            tokenized_output,
            "Human-style verification failed for Step 4: the terminal output for "
            "the tokenized probe did not clearly show a clean policy-gate result.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Observed output:\n{tokenized_output}",
        )

        hardcoded_output = HardcodedHexLintValidationResult.combine_output(
            lint_result.hardcoded_analyze,
        )
        output_lower = hardcoded_output.lower()
        has_terminal_diagnostic = any(
            marker in output_lower
            for marker in (
                "error •",
                "warning •",
                "info •",
                " error - ",
                " warning - ",
                " info - ",
            )
        )
        self.assertNotEqual(
            lint_result.hardcoded_analyze.exit_code,
            0,
            "Step 5 failed: the local theme-token policy command exited successfully "
            "after the probe widget was changed to a hardcoded Flutter color.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Command: {lint_result.hardcoded_analyze.command_text}\n"
            f"Exit code: {lint_result.hardcoded_analyze.exit_code}\n"
            f"Observed output:\n{hardcoded_output}",
        )
        self.assertTrue(
            has_terminal_diagnostic,
            "Human-style verification failed for Step 5: the local theme-token "
            "policy output did not include a contributor-visible diagnostic.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )
        self.assertNotIn(
            "No theme token policy violations found.",
            hardcoded_output,
            "Step 5 failed: the terminal still reported a clean theme-token result "
            "after the probe widget was changed to a hardcoded hex color.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )
        self.assertIn(
            self.lint_config.probe_relative_path.name,
            hardcoded_output,
            "Human-style verification failed for Step 5: the terminal diagnostic "
            "did not point the user to the offending probe file.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )
        self.assertIn(
            self.lint_config.hardcoded_color_expression,
            hardcoded_output,
            "Human-style verification failed for Step 5: the terminal diagnostic "
            "did not visibly include the hardcoded color expression.\n"
            f"Probe file: {lint_result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )

    def _write_result_if_requested(
        self,
        *,
        workflow_observation: dict[str, object],
        lint_result,
    ) -> None:
        result_path = os.environ.get("TS131_RESULT_PATH")
        if not result_path:
            return

        payload = {
            "workflow_observation": workflow_observation,
            "lint_validation": {
                "probe_path": str(lint_result.probe_path),
                "flutter_version": {
                    "command": lint_result.flutter_version.command_text,
                    "exit_code": lint_result.flutter_version.exit_code,
                    "stdout": lint_result.flutter_version.stdout,
                    "stderr": lint_result.flutter_version.stderr,
                },
                "pub_get": {
                    "command": lint_result.pub_get.command_text,
                    "exit_code": lint_result.pub_get.exit_code,
                    "stdout": lint_result.pub_get.stdout,
                    "stderr": lint_result.pub_get.stderr,
                },
                "tokenized_analyze": {
                    "command": lint_result.tokenized_analyze.command_text,
                    "exit_code": lint_result.tokenized_analyze.exit_code,
                    "output": HardcodedHexLintValidationResult.combine_output(
                        lint_result.tokenized_analyze,
                    ),
                },
                "hardcoded_analyze": {
                    "command": lint_result.hardcoded_analyze.command_text,
                    "exit_code": lint_result.hardcoded_analyze.exit_code,
                    "output": HardcodedHexLintValidationResult.combine_output(
                        lint_result.hardcoded_analyze,
                    ),
                },
            },
        }
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
