from __future__ import annotations

import json
import os
import platform
from pathlib import Path
import traceback
import unittest

from testing.components.services.trackstate_cli_fallback_boundaries_validator import (
    TrackStateCliFallbackBoundariesValidator,
)
from testing.core.config.trackstate_cli_fallback_boundaries_config import (
    TrackStateCliFallbackBoundariesConfig,
    TrackStateCliFallbackBoundaryScenarioConfig,
)
from testing.core.models.trackstate_cli_fallback_boundaries_result import (
    TrackStateCliFallbackBoundaryObservation,
)
from testing.tests.support.trackstate_cli_fallback_boundaries_probe_factory import (
    create_trackstate_cli_fallback_boundaries_probe,
)

TICKET_KEY = "TS-385"
OUTPUTS_DIR = Path(__file__).resolve().parents[3] / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class TrackStateCliFallbackBoundariesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-385/config.yaml"
        self.config = TrackStateCliFallbackBoundariesConfig.from_file(self.config_path)
        self.validator = TrackStateCliFallbackBoundariesValidator(
            probe=create_trackstate_cli_fallback_boundaries_probe(self.repository_root)
        )

    def test_cli_rejects_binary_and_admin_fallback_requests_before_repo_access(
        self,
    ) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "repository_root": str(self.repository_root),
            "config_path": str(self.config_path),
            "steps": [],
            "human_verification": [],
            "expected": {
                "exit_code": self.config.expected_exit_code,
                "error_code": self.config.expected_error_code,
                "error_category": self.config.expected_error_category,
            },
        }

        try:
            validation_result = self.validator.validate(config=self.config)
            raw_payload = validation_result.to_dict()
            result["observations"] = raw_payload["observations"]
            self._write_result_if_requested(raw_payload)

            self.assertEqual(
                len(validation_result.observations),
                len(self.config.scenarios),
                "Precondition failed: TS-385 did not execute the expected number of "
                "fallback boundary scenarios.\n"
                f"Expected scenarios: {[scenario.name for scenario in self.config.scenarios]}\n"
                f"Observed scenarios: {[observation.name for observation in validation_result.observations]}",
            )

            failures: list[str] = []
            for step_index, (scenario, observation) in enumerate(
                zip(self.config.scenarios, validation_result.observations),
                start=1,
            ):
                scenario_failures = self._validate_observation(scenario, observation)
                self._record_step(
                    result,
                    step=step_index,
                    status="passed" if not scenario_failures else "failed",
                    action=(
                        "Execute "
                        f"`{scenario.ticket_command}` and inspect the terminal-visible "
                        "JSON error contract."
                    ),
                    observed=self._step_observed_text(scenario, observation),
                    failures=scenario_failures,
                )
                self._record_human_verification(
                    result,
                    check=(
                        "Observed the live CLI output exactly as a user would in the "
                        "terminal, including the visible target path, error code, "
                        "category, message, and JSON envelope."
                    ),
                    observed=self._human_observed_text(observation),
                )
                failures.extend(scenario_failures)

            self.assertFalse(failures, "\n\n".join(failures))
            self._write_pass_outputs(result)
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
            self._write_failure_outputs(
                result,
                product_failure=self._is_product_failure(result),
            )
            raise

    def _validate_observation(
        self,
        scenario: TrackStateCliFallbackBoundaryScenarioConfig,
        observation: TrackStateCliFallbackBoundaryObservation,
    ) -> list[str]:
        failures: list[str] = []
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error_dict = (
            payload_dict.get("error")
            if isinstance(payload_dict, dict) and isinstance(payload_dict.get("error"), dict)
            else None
        )
        target_dict = (
            payload_dict.get("target")
            if isinstance(payload_dict, dict) and isinstance(payload_dict.get("target"), dict)
            else None
        )

        if observation.ticket_command != scenario.ticket_command:
            failures.append(
                f"Precondition failed for {scenario.name}: the probe did not preserve "
                "the ticket command text.\n"
                f"Expected ticket command: {scenario.ticket_command}\n"
                f"Observed ticket command: {observation.ticket_command}"
            )

        if payload_dict is None:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not return a machine-"
                "readable JSON envelope.\n"
                f"Ticket command: {scenario.ticket_command}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Process cwd: {observation.process_cwd}\n"
                f"Local target path: {observation.local_target_path}\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
            return failures

        if observation.result.exit_code != self.config.expected_exit_code:
            failures.append(
                f"Step failed for {scenario.name}: the fallback command did not return "
                "the documented unsupported exit code before repository access.\n"
                f"Ticket command: {scenario.ticket_command}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Process cwd: {observation.process_cwd}\n"
                f"Local target path: {observation.local_target_path}\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed payload: {payload_dict}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )

        if payload_dict.get("ok") is not False:
            failures.append(
                f"Expected-result verification failed for {scenario.name}: the JSON "
                "envelope did not report ok=false.\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict is None:
            failures.append(
                f"Step failed for {scenario.name}: the JSON envelope omitted the error "
                "object for the unsupported request.\n"
                f"Observed payload: {payload_dict}"
            )
            return failures

        if error_dict.get("code") != self.config.expected_error_code:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not classify the unsafe "
                f"fallback request as {self.config.expected_error_code}.\n"
                f"Expected error code: {self.config.expected_error_code}\n"
                f"Observed error code: {error_dict.get('code')}\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict.get("category") != self.config.expected_error_category:
            failures.append(
                f"Step failed for {scenario.name}: the CLI did not report the "
                f"{self.config.expected_error_category} error category.\n"
                f"Expected category: {self.config.expected_error_category}\n"
                f"Observed category: {error_dict.get('category')}\n"
                f"Observed payload: {payload_dict}"
            )

        if error_dict.get("exitCode") != self.config.expected_exit_code:
            failures.append(
                f"Step failed for {scenario.name}: the JSON error object did not "
                "repeat the documented unsupported exit code.\n"
                f"Expected error exitCode: {self.config.expected_exit_code}\n"
                f"Observed error exitCode: {error_dict.get('exitCode')}\n"
                f"Observed payload: {payload_dict}"
            )

        if target_dict is None:
            failures.append(
                f"Human-style verification failed for {scenario.name}: the terminal "
                "output did not expose target metadata.\n"
                f"Observed payload: {payload_dict}"
            )
        else:
            if target_dict.get("type") != "local":
                failures.append(
                    f"Human-style verification failed for {scenario.name}: the visible "
                    "target type was not local.\n"
                    f"Observed target: {target_dict}"
                )
            if target_dict.get("value") != observation.local_target_path:
                failures.append(
                    f"Human-style verification failed for {scenario.name}: the visible "
                    "target value did not match the empty local directory used to "
                    "prove repository access was unnecessary.\n"
                    f"Expected target value: {observation.local_target_path}\n"
                    f"Observed target: {target_dict}"
                )

        message = str(error_dict.get("message", ""))
        lowered_message = message.lower()
        missing_fragments = [
            fragment
            for fragment in scenario.expected_message_fragments
            if fragment not in lowered_message
        ]
        if missing_fragments:
            failures.append(
                f"Human-style verification failed for {scenario.name}: the terminal "
                "error message did not visibly explain the unsupported request.\n"
                f"Missing message fragments: {missing_fragments}\n"
                f"Observed message: {message}\n"
                f"Observed payload: {payload_dict}"
            )

        for fragment in (
            '"ok": false',
            f'"code": "{self.config.expected_error_code}"',
            f'"category": "{self.config.expected_error_category}"',
        ):
            if fragment not in observation.result.stdout:
                failures.append(
                    f"Human-style verification failed for {scenario.name}: stdout did "
                    "not visibly show the unsupported JSON contract.\n"
                    f"Missing stdout fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                )

        return failures

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS385_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _step_observed_text(
        self,
        scenario: TrackStateCliFallbackBoundaryScenarioConfig,
        observation: TrackStateCliFallbackBoundaryObservation,
    ) -> str:
        payload_dict = self._payload_dict(observation)
        error_dict = self._error_dict(payload_dict)
        target_dict = self._target_dict(payload_dict)
        return (
            f"ticket_command={scenario.ticket_command}\n"
            f"executed_command={observation.executed_command_text}\n"
            f"process_cwd={observation.process_cwd}\n"
            f"expected_local_target={observation.local_target_path}\n"
            f"visible_target={target_dict}\n"
            f"exit_code={observation.result.exit_code}\n"
            f"error={error_dict}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}"
        )

    def _human_observed_text(
        self,
        observation: TrackStateCliFallbackBoundaryObservation,
    ) -> str:
        payload_dict = self._payload_dict(observation)
        error_dict = self._error_dict(payload_dict)
        target_dict = self._target_dict(payload_dict)
        return (
            f"visible_target={target_dict}; "
            f"visible_error_code={error_dict.get('code') if isinstance(error_dict, dict) else None}; "
            f"visible_error_category={error_dict.get('category') if isinstance(error_dict, dict) else None}; "
            f"visible_message={error_dict.get('message') if isinstance(error_dict, dict) else None}; "
            f"stdout_contains_ok_false={'\"ok\": false' in observation.result.stdout}"
        )

    def _payload_dict(
        self,
        observation: TrackStateCliFallbackBoundaryObservation,
    ) -> dict[str, object] | None:
        payload = observation.result.json_payload
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _error_dict(payload_dict: dict[str, object] | None) -> dict[str, object] | None:
        if not isinstance(payload_dict, dict):
            return None
        error = payload_dict.get("error")
        return error if isinstance(error, dict) else None

    @staticmethod
    def _target_dict(
        payload_dict: dict[str, object] | None,
    ) -> dict[str, object] | None:
        if not isinstance(payload_dict, dict):
            return None
        target = payload_dict.get("target")
        return target if isinstance(target, dict) else None

    def _record_step(
        self,
        result: dict[str, object],
        *,
        step: int,
        status: str,
        action: str,
        observed: str,
        failures: list[str],
    ) -> None:
        steps = result.setdefault("steps", [])
        assert isinstance(steps, list)
        steps.append(
            {
                "step": step,
                "status": status,
                "action": action,
                "observed": observed,
                "failures": list(failures),
            }
        )

    def _record_human_verification(
        self,
        result: dict[str, object],
        *,
        check: str,
        observed: str,
    ) -> None:
        checks = result.setdefault("human_verification", [])
        assert isinstance(checks, list)
        checks.append({"check": check, "observed": observed})

    def _write_pass_outputs(self, result: dict[str, object]) -> None:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "summary": "1 passed, 0 failed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        JIRA_COMMENT_PATH.write_text(
            self._jira_comment(result, passed=True),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(self._pr_body(result, passed=True), encoding="utf-8")
        RESPONSE_PATH.write_text(
            self._response_summary(result, passed=True),
            encoding="utf-8",
        )

    def _write_failure_outputs(
        self,
        result: dict[str, object],
        *,
        product_failure: bool,
    ) -> None:
        error = str(result.get("error", "AssertionError: unknown failure"))
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "passed": 0,
                    "failed": 1,
                    "skipped": 0,
                    "summary": "0 passed, 1 failed",
                    "error": error,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        JIRA_COMMENT_PATH.write_text(
            self._jira_comment(result, passed=False),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(self._pr_body(result, passed=False), encoding="utf-8")
        RESPONSE_PATH.write_text(
            self._response_summary(result, passed=False),
            encoding="utf-8",
        )
        if product_failure:
            BUG_DESCRIPTION_PATH.write_text(
                self._bug_description(result),
                encoding="utf-8",
            )
        else:
            BUG_DESCRIPTION_PATH.unlink(missing_ok=True)

    def _jira_comment(self, result: dict[str, object], *, passed: bool) -> str:
        status = "PASSED" if passed else "FAILED"
        observed_result = (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        )
        lines = [
            f"h3. {TICKET_KEY} {status}",
            "",
            "*Automation coverage*",
            (
                "* Executed the live CLI fallback command for the binary attachment "
                "DELETE path."
            ),
            (
                "* Executed the live CLI fallback command for the admin permission "
                "POST path."
            ),
            (
                "* Checked the terminal-visible JSON envelope, visible target path, "
                "error code, category, and message for each command."
            ),
            "",
            "*Observed result*",
            observed_result,
            (
                f"* Environment: repository {{{{{result['repository_root']}}}}}, "
                f"config {{{{{result['config_path']}}}}}, browser {{N/A - CLI}}, "
                f"OS {{{{{platform.system()}}}}}."
            ),
            "",
            "*Step results*",
            *self._step_lines(result, jira=True),
            "",
            "*Human-style verification*",
            *self._human_lines(result, jira=True),
        ]
        if not passed:
            lines.extend(
                [
                    "",
                    "*Exact error*",
                    "{code}",
                    str(result.get("traceback", result.get("error", ""))),
                    "{code}",
                ]
            )
        return "\n".join(lines) + "\n"

    def _pr_body(self, result: dict[str, object], *, passed: bool) -> str:
        status = "Passed" if passed else "Failed"
        lines = [
            f"## {TICKET_KEY} {status}",
            "",
            "### Automation",
            (
                "- Executed the live CLI fallback command for the binary attachment "
                "DELETE path."
            ),
            (
                "- Executed the live CLI fallback command for the admin permission "
                "POST path."
            ),
            (
                "- Verified the terminal-visible JSON envelope, visible target path, "
                "error code, category, and message for each command."
            ),
            "",
            "### Observed result",
            "- Matched the expected result."
            if passed
            else "- Did not match the expected result.",
            (
                f"- Environment: repository `{result['repository_root']}`, config "
                f"`{result['config_path']}`, browser `N/A - CLI`, OS `{platform.system()}`."
            ),
            "",
            "### Step results",
            *self._step_lines(result, jira=False),
            "",
            "### Human-style verification",
            *self._human_lines(result, jira=False),
        ]
        if not passed:
            lines.extend(
                [
                    "",
                    "### Exact error",
                    "```text",
                    str(result.get("traceback", result.get("error", ""))),
                    "```",
                ]
            )
        return "\n".join(lines) + "\n"

    def _response_summary(self, result: dict[str, object], *, passed: bool) -> str:
        summary = (
            "Matched the expected unsupported-request contract."
            if passed
            else "Did not match the expected unsupported-request contract."
        )
        lines = [
            f"# {TICKET_KEY} {'Passed' if passed else 'Failed'}",
            "",
            summary,
            "",
            "## Step results",
            *self._step_lines(result, jira=False),
            "",
            "## Human-style verification",
            *self._human_lines(result, jira=False),
        ]
        if not passed:
            lines.extend(
                [
                    "",
                    "## Exact error",
                    "```text",
                    str(result.get("traceback", result.get("error", ""))),
                    "```",
                ]
            )
        return "\n".join(lines) + "\n"

    def _bug_description(self, result: dict[str, object]) -> str:
        lines = [
            f"# {TICKET_KEY} bug report",
            "",
            "## Steps to reproduce",
            *self._bug_step_lines(result),
            "",
            "## Actual vs Expected",
            *self._actual_vs_expected_lines(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- Repository: `{result['repository_root']}`",
            f"- Config: `{result['config_path']}`",
            "- Surface: `dart run trackstate jira_execute_request`",
            "- Browser: `N/A - CLI`",
            f"- OS: `{platform.system()}`",
            "",
            "## Logs",
            *self._log_sections(result),
        ]
        return "\n".join(lines) + "\n"

    def _step_lines(self, result: dict[str, object], *, jira: bool) -> list[str]:
        steps = result.get("steps", [])
        if not isinstance(steps, list):
            return []
        rendered: list[str] = []
        for item in steps:
            if not isinstance(item, dict):
                continue
            marker = "PASS" if item.get("status") == "passed" else "FAIL"
            prefix = "h1. " if jira else "1. "
            rendered.append(
                f"{prefix}Step {item.get('step')} — {marker}: {item.get('action')}"
            )
            observed = str(item.get("observed", "")).strip()
            if observed:
                rendered.append(
                    f"   Observed: {{{{code}}}}{observed}{{{{code}}}}"
                    if jira
                    else f"   Observed: ```text\n{observed}\n```"
                )
            failures = item.get("failures")
            if isinstance(failures, list) and failures:
                rendered.append(
                    "   Failures: "
                    + (
                        "{{code}}"
                        + "\n\n".join(str(failure) for failure in failures)
                        + "{{code}}"
                        if jira
                        else "```text\n"
                        + "\n\n".join(str(failure) for failure in failures)
                        + "\n```"
                    )
                )
        return rendered

    def _human_lines(self, result: dict[str, object], *, jira: bool) -> list[str]:
        checks = result.get("human_verification", [])
        if not isinstance(checks, list):
            return []
        rendered: list[str] = []
        for item in checks:
            if not isinstance(item, dict):
                continue
            prefix = "* " if jira else "- "
            rendered.append(f"{prefix}{item.get('check')}")
            observed = str(item.get("observed", "")).strip()
            if observed:
                rendered.append(
                    f"  Observed: {{{{code}}}}{observed}{{{{code}}}}"
                    if jira
                    else f"  Observed: `{observed}`"
                )
        return rendered

    def _bug_step_lines(self, result: dict[str, object]) -> list[str]:
        steps = result.get("steps", [])
        if not isinstance(steps, list):
            return []
        rendered: list[str] = []
        for item in steps:
            if not isinstance(item, dict):
                continue
            passed = item.get("status") == "passed"
            marker = "✅" if passed else "❌"
            rendered.append(f"1. {marker} {item.get('action')}")
            observed = str(item.get("observed", "")).strip()
            if observed:
                rendered.append("```text")
                rendered.append(observed)
                rendered.append("```")
            failures = item.get("failures")
            if isinstance(failures, list) and failures:
                rendered.append("```text")
                rendered.extend(str(failure) for failure in failures)
                rendered.append("```")
        return rendered

    def _actual_vs_expected_lines(self, result: dict[str, object]) -> list[str]:
        observations = result.get("observations", [])
        if not isinstance(observations, list):
            return []
        rendered: list[str] = []
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            result_payload = observation.get("result", {})
            if not isinstance(result_payload, dict):
                continue
            json_payload = result_payload.get("jsonPayload", {})
            error = (
                json_payload.get("error", {})
                if isinstance(json_payload, dict)
                else {}
            )
            target = (
                json_payload.get("target", {})
                if isinstance(json_payload, dict)
                else {}
            )
            rendered.append(f"### {observation.get('name')}")
            rendered.append(
                "- Expected: exit code "
                f"`{self.config.expected_exit_code}`, error code "
                f"`{self.config.expected_error_code}`, category "
                f"`{self.config.expected_error_category}`, and target value equal to the "
                "empty temporary local directory passed via `--path`."
            )
            rendered.append(
                "- Actual: exit code "
                f"`{result_payload.get('exitCode')}`, error code "
                f"`{error.get('code')}`, category `{error.get('category')}`, visible target "
                f"`{target.get('value')}`, message `{error.get('message')}`."
            )
        return rendered

    def _log_sections(self, result: dict[str, object]) -> list[str]:
        observations = result.get("observations", [])
        if not isinstance(observations, list):
            return []
        rendered: list[str] = []
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            rendered.append(f"### {observation.get('name')}")
            result_payload = observation.get("result", {})
            if isinstance(result_payload, dict):
                rendered.append("```json")
                rendered.append(
                    json.dumps(result_payload.get("jsonPayload"), indent=2, sort_keys=True)
                )
                rendered.append("```")
                stdout = result_payload.get("stdout")
                stderr = result_payload.get("stderr")
                if stdout:
                    rendered.append("```text")
                    rendered.append(str(stdout))
                    rendered.append("```")
                if stderr:
                    rendered.append("```text")
                    rendered.append(str(stderr))
                    rendered.append("```")
        return rendered

    def _is_product_failure(self, result: dict[str, object]) -> bool:
        observations = result.get("observations", [])
        if not isinstance(observations, list):
            return False
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            result_payload = observation.get("result")
            if not isinstance(result_payload, dict):
                continue
            if isinstance(result_payload.get("jsonPayload"), dict):
                return True
            if str(result_payload.get("stdout", "")).strip():
                return True
        return False


if __name__ == "__main__":
    unittest.main()
