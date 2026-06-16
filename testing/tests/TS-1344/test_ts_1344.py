from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any

from testing.core.config.release_workflow_static_config import (
    ReleaseWorkflowStaticConfig,
)
from testing.core.interfaces.release_workflow_static_validator import (
    ReleaseWorkflowStaticObservation,
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


class CrossPlatformArtifactGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ReleaseWorkflowStaticConfig.from_file(
            REPO_ROOT / "testing" / "tests" / "TS-1344" / "config.yaml",
            repository_root=REPO_ROOT,
        )
        self.validator = create_release_workflow_static_validator(REPO_ROOT)

    def test_linux_and_windows_build_jobs_define_expected_artifacts(self) -> None:
        observation = self.validator.validate(self.config)
        self._write_result_if_requested(observation.to_dict())

        failures: list[str] = []
        if not observation.workflow_exists:
            failures.append(
                f"Workflow file not found: {observation.workflow_path}"
            )
        failures.extend(observation.failures)

        self._assert_hosted_runners(observation, failures)
        self._assert_upload_fails_fast(observation, failures)

        if failures:
            self._write_failure_outputs(observation, failures)
            self.fail("\n".join(failures))

        self._write_pass_outputs(observation)

    def _assert_hosted_runners(
        self,
        observation: ReleaseWorkflowStaticObservation,
        failures: list[str],
    ) -> None:
        for job_name, expected_runner in (
            ("build-linux", "ubuntu-latest"),
            ("build-windows", "windows-latest"),
        ):
            job = observation.jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(
                    f"Job '{job_name}' is missing; cannot verify hosted runner."
                )
                continue
            observed_runner = job.get("runs-on")
            if observed_runner != expected_runner:
                failures.append(
                    f"Job '{job_name}' must run on hosted runner '{expected_runner}'; "
                    f"observed: {observed_runner}"
                )

    def _assert_upload_fails_fast(
        self,
        observation: ReleaseWorkflowStaticObservation,
        failures: list[str],
    ) -> None:
        for job_name in ("build-linux", "build-windows"):
            job = observation.jobs.get(job_name)
            if not isinstance(job, dict):
                continue
            steps = job.get("steps", []) or []
            upload_step: dict[str, Any] | None = None
            for step in steps:
                if isinstance(step, dict) and "upload-artifact" in str(
                    step.get("uses", "")
                ):
                    upload_step = step
                    break
            if upload_step is None:
                failures.append(
                    f"Job '{job_name}' is missing an actions/upload-artifact step."
                )
                continue
            upload_with = upload_step.get("with", {}) or {}
            if upload_with.get("if-no-files-found") != "error":
                failures.append(
                    f"Job '{job_name}' upload step must set "
                    f"'if-no-files-found: error'; observed: "
                    f"{upload_with.get('if-no-files-found')}"
                )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1344_RESULT_PATH")
        if not result_path:
            return
        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_pass_outputs(
        self,
        observation: ReleaseWorkflowStaticObservation,
    ) -> None:
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
            _jira_pass_summary(observation),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(
            _markdown_pass_summary(observation),
            encoding="utf-8",
        )

    def _write_failure_outputs(
        self,
        observation: ReleaseWorkflowStaticObservation,
        failures: list[str],
    ) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        error = "\n".join(failures)
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
            _jira_failure_summary(observation, error),
            encoding="utf-8",
        )
        PR_BODY_PATH.write_text(
            _markdown_failure_summary(observation, error),
            encoding="utf-8",
        )
        BUG_DESCRIPTION_PATH.write_text(
            _bug_description(observation, error),
            encoding="utf-8",
        )


def _job_names(observation: ReleaseWorkflowStaticObservation) -> str:
    return ", ".join(sorted(observation.jobs.keys()))


def _runner(job: Any) -> str:
    if isinstance(job, dict):
        return str(job.get("runs-on", "<missing>"))
    return "<missing>"


def _jira_pass_summary(observation: ReleaseWorkflowStaticObservation) -> str:
    linux_job = observation.jobs.get("build-linux")
    windows_job = observation.jobs.get("build-windows")
    lines = [
        "h1. TS-1344 PASSED",
        "",
        "*Status:* ✅ PASSED",
        "*Test Case:* TS-1344 — Cross-platform Artifact Generation — Linux and Windows binaries produced on hosted runners",
        f"*Workflow:* {{.github/workflows/release-on-main.yml}}",
        f"*Jobs:* {_job_names(observation)}",
        "",
        "h2. What was tested",
        "* Verified {{build-linux}} runs on {{ubuntu-latest}} and produces {{TrackState-linux-x64-vX.Y.Z.tar.gz}} plus {{trackstate-cli-linux-x64-vX.Y.Z.tar.gz}}.",
        "* Verified {{build-windows}} runs on {{windows-latest}} and produces {{TrackState-windows-x64-vX.Y.Z.zip}} plus {{trackstate-cli-windows-x64-vX.Y.Z.tar.gz}}.",
        "* Verified each job exposes {{desktop_archive}}, {{cli_archive}}, and {{artifact_name}} outputs.",
        "* Verified build, package, and upload steps use clear headings.",
        "* Verified upload steps fail fast with {{if-no-files-found: error}}.",
        "",
        "h2. Observed",
        f"* Linux runner: {_runner(linux_job)}",
        f"* Windows runner: {_runner(windows_job)}",
        "* Static validation failures: none",
        "",
        "h2. Test file",
        "{code}",
        "testing/tests/TS-1344/test_ts_1344.py",
        "{code}",
        "",
        "h2. Run command",
        "{code:bash}",
        "python -m unittest testing.tests.TS-1344.test_ts_1344",
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _jira_failure_summary(
    observation: ReleaseWorkflowStaticObservation,
    error: str,
) -> str:
    lines = [
        "h1. TS-1344 FAILED",
        "",
        "*Status:* ❌ FAILED",
        "*Test Case:* TS-1344 — Cross-platform Artifact Generation — Linux and Windows binaries produced on hosted runners",
        f"*Workflow:* {{.github/workflows/release-on-main.yml}}",
        f"*Workflow exists:* {observation.workflow_exists}",
        f"*Jobs:* {_job_names(observation)}",
        "",
        "h2. Error",
        "{code}",
        error,
        "{code}",
        "",
        "h2. Test file",
        "{code}",
        "testing/tests/TS-1344/test_ts_1344.py",
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _markdown_pass_summary(observation: ReleaseWorkflowStaticObservation) -> str:
    linux_job = observation.jobs.get("build-linux")
    windows_job = observation.jobs.get("build-windows")
    lines = [
        "## TS-1344 Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        "**Test Case:** TS-1344 — Cross-platform Artifact Generation — Linux and Windows binaries produced on hosted runners",
        "**Workflow:** `.github/workflows/release-on-main.yml`",
        f"**Jobs:** `{_job_names(observation)}`",
        "",
        "### What was automated",
        "- Verified `build-linux` runs on `ubuntu-latest` and produces `TrackState-linux-x64-vX.Y.Z.tar.gz` plus `trackstate-cli-linux-x64-vX.Y.Z.tar.gz`.",
        "- Verified `build-windows` runs on `windows-latest` and produces `TrackState-windows-x64-vX.Y.Z.zip` plus `trackstate-cli-windows-x64-vX.Y.Z.tar.gz`.",
        "- Verified each job exposes `desktop_archive`, `cli_archive`, and `artifact_name` outputs.",
        "- Verified build, package, and upload steps use clear headings.",
        "- Verified upload steps fail fast with `if-no-files-found: error`.",
        "",
        "### Observed",
        f"- Linux runner: `{_runner(linux_job)}`",
        f"- Windows runner: `{_runner(windows_job)}`",
        "- Static validation failures: none",
        "",
        "### How to run",
        "```bash",
        "python -m unittest testing.tests.TS-1344.test_ts_1344",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _markdown_failure_summary(
    observation: ReleaseWorkflowStaticObservation,
    error: str,
) -> str:
    lines = [
        "## TS-1344 Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        "**Test Case:** TS-1344 — Cross-platform Artifact Generation — Linux and Windows binaries produced on hosted runners",
        "**Workflow:** `.github/workflows/release-on-main.yml`",
        f"**Workflow exists:** `{observation.workflow_exists}`",
        f"**Jobs:** `{_job_names(observation)}`",
        "",
        "### Error",
        "```text",
        error,
        "```",
        "",
        "### How to run",
        "```bash",
        "python -m unittest testing.tests.TS-1344.test_ts_1344",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _bug_description(
    observation: ReleaseWorkflowStaticObservation,
    error: str,
) -> str:
    return (
        "# Bug Report — TS-1344\n"
        "\n"
        "**Summary:** Cross-platform Artifact Generation — Linux and Windows binaries "
        "produced on hosted runners\n"
        "\n"
        "## Steps to Reproduce\n"
        "1. Open `.github/workflows/release-on-main.yml`.\n"
        "2. Inspect the `build-linux` and `build-windows` jobs.\n"
        "3. Compare the job definitions to the TS-1344 expected result.\n"
        "\n"
        "## Expected Result\n"
        "- `build-linux` runs on `ubuntu-latest`, builds the Linux desktop app and CLI, "
        "packages them as `TrackState-linux-x64-vX.Y.Z.tar.gz` and "
        "`trackstate-cli-linux-x64-vX.Y.Z.tar.gz`, and uploads the archives with "
        "`if-no-files-found: error`.\n"
        "- `build-windows` runs on `windows-latest`, builds the Windows desktop app and CLI, "
        "packages them as `TrackState-windows-x64-vX.Y.Z.zip` and "
        "`trackstate-cli-windows-x64-vX.Y.Z.tar.gz`, and uploads the archives with "
        "`if-no-files-found: error`.\n"
        "\n"
        "## Actual Result\n"
        f"```text\n{error}\n```\n"
        "\n"
        "## Environment\n"
        f"- Workflow path: `{observation.workflow_path}`\n"
        f"- Workflow exists: `{observation.workflow_exists}`\n"
        f"- Jobs observed: `{_job_names(observation)}`\n"
    )


if __name__ == "__main__":
    unittest.main()
