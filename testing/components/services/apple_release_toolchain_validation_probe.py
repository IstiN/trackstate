from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

from testing.components.pages.github_repository_file_page import (
    GitHubRepositoryFileObservation,
)
from testing.core.config.apple_release_toolchain_validation_config import (
    AppleReleaseToolchainValidationConfig,
)
from testing.core.interfaces.apple_release_toolchain_validation_probe import (
    AppleReleaseToolchainValidationJobObservation,
    AppleReleaseToolchainValidationObservation,
    AppleReleaseToolchainValidationStepObservation,
)
from testing.core.interfaces.github_api_client import GitHubApiClient
from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)


class AppleReleaseToolchainValidationProbeError(RuntimeError):
    pass


class AppleReleaseToolchainValidationProbeService:
    def __init__(
        self,
        config: AppleReleaseToolchainValidationConfig,
        *,
        github_api_client: GitHubApiClient,
        workflow_run_log_reader: GitHubWorkflowRunLogReader,
        file_page_factory,
        screenshot_directory: Path | None = None,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._workflow_run_log_reader = workflow_run_log_reader
        self._file_page_factory = file_page_factory
        self._screenshot_directory = screenshot_directory

    def validate(self) -> AppleReleaseToolchainValidationObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._optional_string(repository_info.get("default_branch"))
        if default_branch is None:
            default_branch = self._config.default_branch

        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise AppleReleaseToolchainValidationProbeError(
                "TS-707 could not resolve a numeric workflow ID for "
                f"{self._config.workflow_path}."
            )

        workflow_text = self._read_workflow_text(default_branch)
        ui_observation = self._load_ui_observation(default_branch)
        disposable_run = self._create_and_observe_incompatible_tag_run(
            workflow_id=workflow_id,
            default_branch=default_branch,
        )

        jobs = [
            self._job_observation(job)
            for job in disposable_run["jobs"]
            if isinstance(job, dict)
        ]
        verify_runner_job = self._find_job(jobs, self._config.verify_runner_job_name)
        build_job = self._find_job(jobs, self._config.build_job_name)
        setup_flutter_step = self._find_step(build_job, self._config.setup_flutter_step_name)
        validation_step = self._find_step(build_job, self._config.validation_step_name)
        desktop_build_step = self._find_step(
            build_job, self._config.desktop_build_step_name
        )
        cli_build_step = self._find_step(build_job, self._config.cli_build_step_name)

        run_log = str(disposable_run["run_log"])
        version_error_line = self._first_matching_line(
            run_log,
            (
                f"Flutter {self._config.required_flutter_version} or newer is required;",
                f"::error::Flutter {self._config.required_flutter_version} or newer is required;",
            ),
        )
        setup_failure_line = None
        if setup_flutter_step is not None and setup_flutter_step.conclusion == "failure":
            setup_failure_line = self._first_matching_line(
                run_log,
                (
                    "Unable to determine Flutter version",
                    f"{build_job.name}\t{self._config.setup_flutter_step_name}\t##[error]",
                    f"{build_job.name}\t{self._config.setup_flutter_step_name}\tProcess completed with exit code 1.",
                ),
            )
        excerpt_marker = version_error_line or setup_failure_line or self._first_matching_line(
            run_log,
            (
                self._config.validation_step_name,
                self._config.setup_flutter_step_name,
                "Resource not accessible by integration",
                "Unhandled error: HttpError",
                "status: 403",
                "No runner registered",
                "none are online",
            ),
        )
        run_log_excerpt = self._log_excerpt(
            run_log,
            excerpt_marker,
            context_lines=self._config.log_excerpt_lines,
        )

        return AppleReleaseToolchainValidationObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            workflow_id=workflow_id,
            workflow_name=str(workflow.get("name", "")),
            workflow_path=self._config.workflow_path,
            workflow_url=str(workflow.get("html_url", "")),
            workflow_text=workflow_text,
            main_ui_url=ui_observation.url if ui_observation else None,
            main_ui_body_text=ui_observation.body_text if ui_observation else "",
            main_ui_error=None if ui_observation else "GitHub workflow file page did not load.",
            main_ui_screenshot_path=(
                ui_observation.screenshot_path if ui_observation else None
            ),
            test_tag=str(disposable_run["tag_name"]),
            test_commit_sha=str(disposable_run["commit_sha"]),
            run_id=int(disposable_run["run_id"]),
            run_url=str(disposable_run["run_url"]),
            run_event=str(disposable_run["run_event"]),
            run_status=self._optional_string(disposable_run.get("run_status")),
            run_conclusion=self._optional_string(disposable_run.get("run_conclusion")),
            run_created_at=self._optional_string(disposable_run.get("run_created_at")),
            run_display_title=self._optional_string(disposable_run.get("run_display_title")),
            jobs=jobs,
            verify_runner_job=verify_runner_job,
            build_job=build_job,
            setup_flutter_step=setup_flutter_step,
            validation_step=validation_step,
            desktop_build_step=desktop_build_step,
            cli_build_step=cli_build_step,
            version_error_line=version_error_line,
            run_log_excerpt=run_log_excerpt,
            cleanup_deleted_tag=bool(disposable_run["cleanup_deleted_tag"]),
        )

    def _select_workflow(self) -> dict[str, Any]:
        payload = self._read_json_object(f"/repos/{self._config.repository}/actions/workflows")
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise AppleReleaseToolchainValidationProbeError(
                "GitHub Actions workflows response did not return a workflows list."
            )

        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            path = workflow.get("path")
            if isinstance(path, str) and path == self._config.workflow_path:
                return workflow

        raise AppleReleaseToolchainValidationProbeError(
            "TS-707 could not find the configured workflow path "
            f"{self._config.workflow_path} in {self._config.repository}."
        )

    def _read_workflow_text(self, default_branch: str) -> str:
        return self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(self._config.workflow_path, safe='/')}?ref="
                f"{quote(default_branch, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )

    def _load_ui_observation(
        self,
        default_branch: str,
    ) -> GitHubRepositoryFileObservation | None:
        screenshot_path: str | None = None
        if self._screenshot_directory is not None:
            screenshot_path = str(self._screenshot_directory / "ts707_apple_workflow_page.png")

        with self._file_page_factory() as file_page:
            return file_page.open_file(
                repository=self._config.repository,
                branch=default_branch,
                file_path=self._config.workflow_path,
                expected_texts=(
                    self._config.workflow_name,
                    self._config.required_flutter_version,
                    self._config.validation_step_name,
                    "./tool/check_macos_release_runner.sh",
                ),
                screenshot_path=screenshot_path,
                timeout_seconds=self._config.ui_timeout_seconds,
            )

    def _create_and_observe_incompatible_tag_run(
        self,
        *,
        workflow_id: int,
        default_branch: str,
    ) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts707-"))
        tag_name: str | None = None
        commit_sha = ""
        disposable_observation: dict[str, object] | None = None

        try:
            self._run_command(["gh", "auth", "setup-git"], cwd=None)
            self._run_command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    self._origin_clone_url(),
                    str(temp_repository_root),
                ],
                cwd=None,
            )
            self._run_command(
                ["git", "checkout", "-b", "ts707-probe", f"origin/{default_branch}"],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.name", "ai-teammate"],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.email", "agent.ai.native@gmail.com"],
                cwd=temp_repository_root,
            )

            workflow_file = temp_repository_root / self._config.workflow_path
            if not workflow_file.exists():
                raise AppleReleaseToolchainValidationProbeError(
                    "TS-707 precondition failed: the Apple workflow file does not exist in "
                    f"the cloned repository.\nPath: {self._config.workflow_path}"
                )

            original_text = workflow_file.read_text(encoding="utf-8")
            workflow_file.write_text(
                self._inject_validation_probe_step(original_text),
                encoding="utf-8",
            )
            self._run_command(["git", "add", self._config.workflow_path], cwd=temp_repository_root)
            self._run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "TS-707 probe: inject incompatible Flutter validation shim\n\n"
                    "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>",
                ],
                cwd=temp_repository_root,
            )
            commit_sha = (
                self._run_command(["git", "rev-parse", "HEAD"], cwd=temp_repository_root)
                .stdout.strip()
            )
            if not commit_sha:
                raise AppleReleaseToolchainValidationProbeError(
                    "TS-707 could not resolve the disposable probe commit SHA."
                )

            tag_name = self._unique_tag_name()
            self._run_command(["git", "tag", tag_name], cwd=temp_repository_root)
            started_at = time.time()
            self._run_command(
                ["git", "push", "origin", f"refs/tags/{tag_name}"],
                cwd=temp_repository_root,
            )

            run_detail = self._wait_for_push_run(
                workflow_id=workflow_id,
                expected_head_sha=commit_sha,
                started_at=started_at,
            )
            run_id = run_detail.get("id")
            if not isinstance(run_id, int):
                raise AppleReleaseToolchainValidationProbeError(
                    "TS-707 observed a workflow run without a numeric run ID."
                )
            jobs = self._read_jobs(run_id)
            run_log = self._workflow_run_log_reader.read_run_log(run_id)

            disposable_observation = {
                "tag_name": tag_name,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_url": str(run_detail.get("html_url", "")),
                "run_event": str(run_detail.get("event", "")),
                "run_status": run_detail.get("status"),
                "run_conclusion": run_detail.get("conclusion"),
                "run_created_at": run_detail.get("created_at"),
                "run_display_title": run_detail.get("display_title"),
                "jobs": jobs,
                "run_log": run_log,
                "cleanup_deleted_tag": False,
            }
        finally:
            if tag_name is not None:
                cleanup_deleted_tag = self._delete_tag(tag_name, temp_repository_root)
                if disposable_observation is not None:
                    disposable_observation["cleanup_deleted_tag"] = cleanup_deleted_tag
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

        if disposable_observation is not None:
            return disposable_observation

        raise AppleReleaseToolchainValidationProbeError(
            "TS-707 did not produce a disposable Apple release workflow observation."
        )

    def _inject_validation_probe_step(self, workflow_text: str) -> str:
        validation_marker = f"      - name: {self._config.validation_step_name}\n"
        if workflow_text.count(validation_marker) != 1:
            raise AppleReleaseToolchainValidationProbeError(
                "TS-707 expected to inject the incompatible Flutter probe immediately "
                "before the validation step in the disposable workflow branch.\n"
                f"Validation marker: {validation_marker.strip()}\n"
                f"Observed matches: {workflow_text.count(validation_marker)}"
            )

        injection = (
            "      - name: Inject incompatible Flutter validation probe\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
            "\n"
            "          probe_dir=\"$RUNNER_TEMP/ts707-probe/bin\"\n"
            "          mkdir -p \"$probe_dir\"\n"
            "\n"
            "          original_flutter=\"$(command -v flutter)\"\n"
            "          if [[ -z \"$original_flutter\" ]]; then\n"
            "            echo \"::error::TS-707 probe could not locate the runner's Flutter "
            "binary before validation.\"\n"
            "            exit 1\n"
            "          fi\n"
            "\n"
            "          printf '%s\\n' \"$original_flutter\" > \"$probe_dir/flutter.real\"\n"
            "          cat > \"$probe_dir/flutter\" <<'EOF'\n"
            "          #!/usr/bin/env bash\n"
            "          set -euo pipefail\n"
            "\n"
            "          script_dir=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
            "          real_flutter=\"$(cat \"$script_dir/flutter.real\")\"\n"
            "\n"
            "          if [[ \"${1:-}\" == \"--version\" ]]; then\n"
            f"            echo \"Flutter {self._config.incompatible_flutter_version} • "
            "channel stable • https://github.com/flutter/flutter.git\"\n"
            "            exit 0\n"
            "          fi\n"
            "\n"
            "          exec \"$real_flutter\" \"$@\"\n"
            "          EOF\n"
            "          chmod +x \"$probe_dir/flutter\"\n"
            "          echo \"$probe_dir\" >> \"$GITHUB_PATH\"\n"
            "\n"
        )
        return workflow_text.replace(validation_marker, injection + validation_marker, 1)

    def _wait_for_push_run(
        self,
        *,
        workflow_id: int,
        expected_head_sha: str,
        started_at: float,
    ) -> dict[str, Any]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_run_detail: dict[str, Any] | None = None

        while time.time() < deadline:
            latest_run = self._latest_matching_run(
                workflow_id=workflow_id,
                expected_head_sha=expected_head_sha,
                started_at=started_at,
            )
            if latest_run is None:
                time.sleep(self._config.poll_interval_seconds)
                continue

            run_id = latest_run.get("id")
            if not isinstance(run_id, int):
                time.sleep(self._config.poll_interval_seconds)
                continue

            latest_run_detail = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            if latest_run_detail.get("status") != "completed":
                time.sleep(self._config.poll_interval_seconds)
                continue
            if latest_run_detail.get("conclusion") == "cancelled":
                time.sleep(self._config.poll_interval_seconds)
                continue
            return latest_run_detail

        if latest_run_detail is not None:
            raise AppleReleaseToolchainValidationProbeError(
                "TS-707 observed a disposable Apple release run, but it did not reach a "
                "non-cancelled completed state within the timeout.\n"
                f"Run ID: {latest_run_detail.get('id')}\n"
                f"Status: {latest_run_detail.get('status')}\n"
                f"Conclusion: {latest_run_detail.get('conclusion')}\n"
                f"URL: {latest_run_detail.get('html_url')}"
            )

        raise AppleReleaseToolchainValidationProbeError(
            "TS-707 did not observe a new Apple release push run for the disposable tag "
            f"commit {expected_head_sha} within {self._config.run_timeout_seconds} seconds."
        )

    def _latest_matching_run(
        self,
        *,
        workflow_id: int,
        expected_head_sha: str,
        started_at: float,
    ) -> dict[str, Any] | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows/{workflow_id}/runs"
            f"?event=push&per_page=30"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise AppleReleaseToolchainValidationProbeError(
                "GitHub Actions workflow runs response did not return a workflow_runs list."
            )

        started_floor = started_at - max(self._config.poll_interval_seconds, 1)
        matches: list[dict[str, Any]] = []
        for run in workflow_runs:
            if not isinstance(run, dict):
                continue
            if self._optional_string(run.get("head_sha")) != expected_head_sha:
                continue
            created_at = self._run_created_at_epoch(run)
            if created_at is None or created_at < started_floor:
                continue
            matches.append(run)

        if not matches:
            return None

        return max(
            matches,
            key=lambda run: (
                self._run_created_at_epoch(run) or 0.0,
                int(run.get("id", 0)),
            ),
        )

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise AppleReleaseToolchainValidationProbeError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _job_observation(
        self,
        job: dict[str, Any],
    ) -> AppleReleaseToolchainValidationJobObservation:
        raw_steps = job.get("steps")
        steps: list[AppleReleaseToolchainValidationStepObservation] = []
        if isinstance(raw_steps, list):
            for step in raw_steps:
                if not isinstance(step, dict):
                    continue
                number = step.get("number")
                steps.append(
                    AppleReleaseToolchainValidationStepObservation(
                        name=self._optional_string(step.get("name")) or "",
                        status=self._optional_string(step.get("status")),
                        conclusion=self._optional_string(step.get("conclusion")),
                        number=number if isinstance(number, int) else None,
                    )
                )
        return AppleReleaseToolchainValidationJobObservation(
            name=self._optional_string(job.get("name")) or "",
            status=self._optional_string(job.get("status")),
            conclusion=self._optional_string(job.get("conclusion")),
            url=self._optional_string(job.get("html_url"))
            or self._optional_string(job.get("url"))
            or "",
            steps=steps,
        )

    @staticmethod
    def _find_job(
        jobs: list[AppleReleaseToolchainValidationJobObservation],
        name: str,
    ) -> AppleReleaseToolchainValidationJobObservation | None:
        for job in jobs:
            if job.name == name:
                return job
        return None

    @staticmethod
    def _find_step(
        job: AppleReleaseToolchainValidationJobObservation | None,
        name: str,
    ) -> AppleReleaseToolchainValidationStepObservation | None:
        if job is None:
            return None
        for step in job.steps:
            if step.name == name:
                return step
        return None

    def _delete_tag(self, tag_name: str, cwd: Path) -> bool:
        try:
            self._run_command(
                ["git", "push", "origin", f":refs/tags/{tag_name}"],
                cwd=cwd,
            )
        except AppleReleaseToolchainValidationProbeError:
            return False
        return True

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AppleReleaseToolchainValidationProbeError(
                f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed

    def _read_json_object(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        try:
            payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        except json.JSONDecodeError as error:
            raise AppleReleaseToolchainValidationProbeError(
                f"GitHub API response for {endpoint} was not valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise AppleReleaseToolchainValidationProbeError(
                f"GitHub API response for {endpoint} was not a JSON object."
            )
        return payload

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at.strip():
            return None
        try:
            return datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            return None

    def _unique_tag_name(self) -> str:
        now = datetime.now(tz=timezone.utc)
        return f"v2099.{now.strftime('%j')}.{now.strftime('%H%M%S%f')}"

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    @staticmethod
    def _first_matching_line(
        text: str,
        needles: tuple[str, ...],
    ) -> str | None:
        for line in text.splitlines():
            for needle in needles:
                if needle in line:
                    return line
        return None

    @staticmethod
    def _log_excerpt(
        text: str,
        marker: str | None,
        *,
        context_lines: int,
    ) -> str:
        lines = text.splitlines()
        if not lines:
            return ""
        if marker is None:
            return "\n".join(lines[-context_lines:])

        for index, line in enumerate(lines):
            if marker in line:
                start = max(index - context_lines // 2, 0)
                end = min(index + context_lines // 2 + 1, len(lines))
                return "\n".join(lines[start:end])
        return "\n".join(lines[-context_lines:])
