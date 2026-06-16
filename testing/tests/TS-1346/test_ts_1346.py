from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.release_workflow_static_config import (
    ReleaseWorkflowStaticConfig,
)
from testing.core.interfaces.build_native_workflow_dispatch_probe import (
    BuildNativeWorkflowDispatchObservation,
)
from testing.tests.support.build_native_workflow_dispatch_probe_factory import (
    create_build_native_workflow_dispatch_probe,
)
from testing.tests.support.release_workflow_static_validator_factory import (
    create_release_workflow_static_validator,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class BuildNativeWrapperCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ReleaseWorkflowStaticConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-1346" / "config.yaml",
            repository_root=REPO_ROOT,
        )
        self.static_validator = create_release_workflow_static_validator(REPO_ROOT)
        self.dispatch_probe = create_build_native_workflow_dispatch_probe(REPO_ROOT)

    def test_build_native_calls_reusable_macos_workflow(self) -> None:
        static_observation = self.static_validator.validate(self.config)
        dispatch_observation = self.dispatch_probe.validate()

        self._write_result_if_requested(
            {
                "static": static_observation.to_dict(),
                "dispatch": dispatch_observation.to_dict(),
            }
        )

        failures: list[str] = []
        if not static_observation.workflow_exists:
            failures.append(
                f"Workflow file not found: {static_observation.workflow_path}"
            )
        if static_observation.failures:
            failures.append(
                "Static validation failed:\n" + "\n".join(static_observation.failures)
            )
        if not dispatch_observation.workflow_dispatch_enabled:
            failures.append(
                "Step 2 failed: build-native.yml does not expose a workflow_dispatch "
                "trigger, so the repair workflow cannot dispatch it."
            )

        if failures:
            self._write_failure_outputs(
                static_observation, dispatch_observation, failures
            )
            self.fail("\n\n".join(failures))

        if not dispatch_observation.runner_available:
            self._write_blocked_outputs(dispatch_observation)
            self.skipTest(
                "BLOCKED: no online self-hosted macOS release runner is available. "
                "Provision the TrackState maintainer-owned macOS release runner and rerun."
            )

        if not dispatch_observation.dispatched:
            failures.append(
                "Step 3 failed: build-native.yml was not dispatched. "
                f"Reason: {dispatch_observation.failure_reason}"
            )
        if dispatch_observation.run_status != "completed":
            failures.append(
                "Step 4 failed: the dispatched workflow run did not reach a completed state.\n"
                f"Run: {dispatch_observation.run_url}"
            )
        if dispatch_observation.run_conclusion != "success":
            failures.append(
                "Step 4 failed: the dispatched workflow run did not complete successfully.\n"
                f"Run: {dispatch_observation.run_url}"
            )
        if not dispatch_observation.reusable_workflow_invoked:
            failures.append(
                "Step 4 failed: the dispatched run did not invoke the reusable macOS "
                f"workflow {dispatch_observation.reusable_workflow_path}.\n"
                f"Run: {dispatch_observation.run_url}"
            )
        if dispatch_observation.build_macos_job_conclusion != "success":
            failures.append(
                "Step 4 failed: the build-macos job did not complete successfully.\n"
                f"Run: {dispatch_observation.run_url}"
            )

        if failures:
            self._write_failure_outputs(
                static_observation, dispatch_observation, failures
            )
            self.fail("\n\n".join(failures))

        self._write_pass_outputs(dispatch_observation)

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1346_RESULT_PATH")
        if not result_path:
            return
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_pass_outputs(self, observation: BuildNativeWorkflowDispatchObservation) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "summary": "1 passed, 0 failed",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        RESPONSE_PATH.write_text(
            _response_summary(observation, status="passed"),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(
            _pr_body(observation, status="passed"),
            encoding="utf-8",
        )

    def _write_blocked_outputs(self, observation: BuildNativeWorkflowDispatchObservation) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
        reason = observation.failure_reason or (
            "No online self-hosted macOS release runner is available."
        )
        missing = self._blocked_missing_item(observation, reason)
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "blocked_by_human",
                    "passed": 0,
                    "failed": 0,
                    "skipped": 1,
                    "summary": "0 passed, 0 failed, 1 skipped",
                    "blocked_reason": reason,
                    "missing": [missing],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        RESPONSE_PATH.write_text(
            f"h1. TS-1346 BLOCKED\n\n* {reason}\n",
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(
            "# TS-1346 Test Automation Result\n\n"
            "**Status:** 🚫 BLOCKED\n\n"
            f"- {reason}\n",
            encoding="utf-8",
        )

    @staticmethod
    def _blocked_missing_item(
        observation: BuildNativeWorkflowDispatchObservation,
        reason: str,
    ) -> dict[str, str]:
        if (
            "GH_TOKEN" in reason
            or "GITHUB_TOKEN" in reason
            or "read access to repository runners" in reason
        ):
            return {
                "type": "secret",
                "name": "GH_TOKEN or GITHUB_TOKEN",
                "description": (
                    "A GitHub token with read access to repository runners and workflow runs "
                    f"for {observation.repository}."
                ),
                "how_to_add": "Add the token using the CI secret-management process.",
            }
        return {
            "type": "infrastructure",
            "name": "self-hosted macOS release runner",
            "description": (
                "A GitHub Actions self-hosted runner with labels "
                f"{list(observation.runner_labels)} for "
                f"{observation.repository}."
            ),
            "how_to_add": (
                "Provision the TrackState maintainer-owned macOS release runner and "
                "rerun the test."
            ),
        }

    def _write_failure_outputs(
        self,
        static_observation: object,
        dispatch_observation: BuildNativeWorkflowDispatchObservation,
        failures: list[str],
    ) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        error = "\n\n".join(failures)
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "passed": 0,
                    "failed": 1,
                    "skipped": 0,
                    "summary": "0 passed, 1 failed",
                    "error": error,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        RESPONSE_PATH.write_text(
            _failure_response(dispatch_observation, error),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(
            _failure_pr_body(dispatch_observation, error),
            encoding="utf-8",
        )
        BUG_DESCRIPTION_PATH.write_text(
            _bug_description(static_observation, dispatch_observation, error),
            encoding="utf-8",
        )


def _response_summary(
    observation: BuildNativeWorkflowDispatchObservation, *, status: str
) -> str:
    lines = [
        f"h1. TS-1346 {status.upper()}",
        "",
        f"Dispatched {{build-native.yml}} on {observation.repository} and verified it "
        "invokes the reusable macOS workflow.",
        "",
        "h2. Observed",
        f"* Repository: {observation.repository}",
        f"* Workflow: {observation.workflow_path}",
        f"* workflow_dispatch enabled: {observation.workflow_dispatch_enabled}",
        f"* Runner available: {observation.runner_available}",
        f"* Online runners: {observation.online_runner_names}",
        f"* Dispatched: {observation.dispatched}",
        f"* Run URL: {observation.run_url}",
        f"* Run status: {observation.run_status}",
        f"* Run conclusion: {observation.run_conclusion}",
        f"* Reusable workflow invoked: {observation.reusable_workflow_invoked}",
        f"* build-macos job conclusion: {observation.build_macos_job_conclusion}",
    ]
    return "\n".join(lines) + "\n"


def _pr_body(
    observation: BuildNativeWorkflowDispatchObservation, *, status: str
) -> str:
    lines = [
        "## TS-1346 Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'passed' else status.upper()}",
        "",
        "### What was automated",
        "- Statically validated `.github/workflows/build-native.yml` structure.",
        f"- Dispatched `{observation.workflow_path}` via `workflow_dispatch`.",
        "- Verified the dispatched run invoked the reusable macOS workflow.",
        "",
        "### Observed",
        f"- Repository: `{observation.repository}`",
        f"- Runner available: `{observation.runner_available}`",
        f"- Online runners: `{observation.online_runner_names}`",
        f"- Dispatched: `{observation.dispatched}`",
        f"- Run URL: {observation.run_url}",
        f"- Run conclusion: `{observation.run_conclusion}`",
        f"- Reusable workflow invoked: `{observation.reusable_workflow_invoked}`",
        f"- build-macos job conclusion: `{observation.build_macos_job_conclusion}`",
    ]
    return "\n".join(lines) + "\n"


def _failure_response(
    observation: BuildNativeWorkflowDispatchObservation, error: str
) -> str:
    lines = [
        "h1. TS-1346 FAILED",
        "",
        "The live dispatch probe did not match the expected result.",
        "",
        "h2. Observed",
        f"* Repository: {observation.repository}",
        f"* Workflow: {observation.workflow_path}",
        f"* workflow_dispatch enabled: {observation.workflow_dispatch_enabled}",
        f"* Runner available: {observation.runner_available}",
        f"* Online runners: {observation.online_runner_names}",
        f"* Dispatched: {observation.dispatched}",
        f"* Run URL: {observation.run_url}",
        f"* Run status: {observation.run_status}",
        f"* Run conclusion: {observation.run_conclusion}",
        f"* Reusable workflow invoked: {observation.reusable_workflow_invoked}",
        f"* build-macos job conclusion: {observation.build_macos_job_conclusion}",
        "",
        "h2. Error",
        "{code}",
        error,
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _failure_pr_body(
    observation: BuildNativeWorkflowDispatchObservation, error: str
) -> str:
    lines = [
        "## TS-1346 Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        "",
        "### What was automated",
        "- Statically validated `.github/workflows/build-native.yml` structure.",
        f"- Dispatched `{observation.workflow_path}` via `workflow_dispatch`.",
        "- Verified the dispatched run invoked the reusable macOS workflow.",
        "",
        "### Observed",
        f"- Repository: `{observation.repository}`",
        f"- Runner available: `{observation.runner_available}`",
        f"- Online runners: `{observation.online_runner_names}`",
        f"- Dispatched: `{observation.dispatched}`",
        f"- Run URL: {observation.run_url}",
        f"- Run conclusion: `{observation.run_conclusion}`",
        f"- Reusable workflow invoked: `{observation.reusable_workflow_invoked}`",
        f"- build-macos job conclusion: `{observation.build_macos_job_conclusion}`",
        "",
        "### Error",
        "```text",
        error,
        "```",
    ]
    return "\n".join(lines) + "\n"


def _bug_description(
    static_observation: object,
    dispatch_observation: BuildNativeWorkflowDispatchObservation,
    error: str,
) -> str:
    static_dict = static_observation.to_dict() if hasattr(static_observation, "to_dict") else {}
    lines = [
        "h4. Environment",
        f"* Repository: `{dispatch_observation.repository}`",
        f"* Workflow: `{dispatch_observation.workflow_path}`",
        f"* Reusable workflow: `{dispatch_observation.reusable_workflow_path}`",
        "",
        "h4. Steps to Reproduce",
        "1. Open Actions > build-native.yml.",
        "2. Trigger the workflow via 'Run workflow' using the main branch.",
        "3. Observe the job execution graph.",
        "",
        "h4. Expected Result",
        "The workflow successfully invokes build-macos-reusable.yml, passes the required inputs, "
        "and the macOS build completes on the self-hosted runner.",
        "",
        "h4. Actual Result",
        f"{error}",
        "",
        "h4. Evidence",
        f"* workflow_dispatch enabled: `{dispatch_observation.workflow_dispatch_enabled}`",
        f"* Runner available: `{dispatch_observation.runner_available}`",
        f"* Online runners: `{dispatch_observation.online_runner_names}`",
        f"* Dispatched: `{dispatch_observation.dispatched}`",
        f"* Run URL: `{dispatch_observation.run_url}`",
        f"* Run status: `{dispatch_observation.run_status}`",
        f"* Run conclusion: `{dispatch_observation.run_conclusion}`",
        f"* Reusable workflow invoked: `{dispatch_observation.reusable_workflow_invoked}`",
        f"* build-macos job conclusion: `{dispatch_observation.build_macos_job_conclusion}`",
        f"* Static failures: `{static_dict.get('failures', [])}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    unittest.main()
