from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (  # noqa: E402
    PythonTrackStateCliCompiledLocalFramework,
)

TICKET_KEY = "TS-540"
TICKET_SUMMARY = (
    "Release-backed local-git attachment download succeeds through the GitHub "
    "Releases storage handler"
)
TEST_FILE_PATH = "testing/tests/TS-540/test_ts_540.py"
RUN_COMMAND = "python testing/tests/TS-540/test_ts_540.py"

PROJECT_KEY = "TS"
PROJECT_NAME = "TS-540 Project"
ISSUE_KEY = "TS-123"
ISSUE_SUMMARY = "Release-backed local attachment download success fixture"
ISSUE_PATH = f"{PROJECT_KEY}/{ISSUE_KEY}"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENT_NAME = "manual.pdf"
ATTACHMENT_RELATIVE_PATH = f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}"
ATTACHMENT_MEDIA_TYPE = "application/pdf"
ATTACHMENT_CREATED_AT = "2026-05-13T00:00:00Z"
ATTACHMENT_AUTHOR = "tester"
ATTACHMENT_REVISION_OR_OID = "ts540-release-download-success"
ATTACHMENT_TEXT = (
    "%PDF-1.4\n"
    "TS-540 successful release-backed local download fixture.\n"
    "This file proves the local provider delegated to GitHub Releases.\n"
)
ATTACHMENT_BYTES = ATTACHMENT_TEXT.encode("utf-8")
ATTACHMENT_TAG_PREFIX = "ts540-"
ATTACHMENT_RELEASE_TAG = f"{ATTACHMENT_TAG_PREFIX}{ISSUE_KEY}"
ATTACHMENT_RELEASE_TITLE = f"TS-540 local download fixture for {ISSUE_KEY}"
ATTACHMENT_RELEASE_BODY = (
    "TrackState TS-540 release-backed local download success fixture."
)
OUTPUT_FILE_ARGUMENT = "./downloads/manual.pdf"
EXPECTED_OUTPUT_RELATIVE_PATH = "downloads/manual.pdf"
REQUESTED_COMMAND = (
    "trackstate",
    "attachment",
    "download",
    "--attachment-id",
    ATTACHMENT_RELATIVE_PATH,
    "--out",
    OUTPUT_FILE_ARGUMENT,
    "--target",
    "local",
)
TICKET_COMMAND = " ".join(REQUESTED_COMMAND)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

RELEASE_TIMEOUT_SECONDS = 120
RELEASE_POLL_INTERVAL_SECONDS = 4
PROVIDER_CAPABILITY_FRAGMENTS = (
    "does not support github releases attachment downloads",
    "repository provider",
)
FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS = frozenset(
    {"base64", "content", "contentBase64", "dataUrl", "payload"}
)
REQUIRED_TOP_LEVEL_KEYS = (
    "schemaVersion",
    "ok",
    "provider",
    "target",
    "output",
    "data",
)
REQUIRED_TARGET_KEYS = ("type", "value")
REQUIRED_DATA_KEYS = ("command", "authSource", "issue", "savedFile", "attachment")
REQUIRED_ATTACHMENT_KEYS = (
    "id",
    "name",
    "mediaType",
    "sizeBytes",
    "createdAt",
    "revisionOrOid",
)


@dataclass(frozen=True)
class ReleaseFixture:
    repository: str
    repository_ref: str
    remote_origin_url: str
    tag_name: str
    title: str
    asset_name: str
    asset_id: int
    asset_bytes: bytes
    release_id: int


@dataclass(frozen=True)
class LocalRepositoryState:
    issue_main_exists: bool
    attachments_metadata_exists: bool
    metadata_attachment_ids: tuple[str, ...]
    metadata_storage_backends: tuple[str, ...]
    metadata_release_tags: tuple[str, ...]
    metadata_release_asset_names: tuple[str, ...]
    expected_output_exists: bool
    expected_output_size_bytes: int | None
    downloads_directory_exists: bool
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class LocalReleaseDownloadProbeResult:
    initial_state: LocalRepositoryState
    final_state: LocalRepositoryState
    observation: TrackStateCliCommandObservation
    saved_file_absolute_path: str
    saved_file_bytes: bytes | None
    stripped_environment_variables: tuple[str, ...]


class Ts540LocalReleaseDownloadProbe(PythonTrackStateCliCompiledLocalFramework):
    def execute(
        self,
        *,
        fixture: ReleaseFixture,
        token: str,
    ) -> LocalReleaseDownloadProbeResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-540-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-540-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(
                    repository_path=repository_path,
                    fixture=fixture,
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                )
                observation, stripped_environment_variables = self._observe_command(
                    repository_path=repository_path,
                    executable_path=executable_path,
                    token=token,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                )
                saved_file = repository_path / EXPECTED_OUTPUT_RELATIVE_PATH
                return LocalReleaseDownloadProbeResult(
                    initial_state=initial_state,
                    final_state=final_state,
                    observation=observation,
                    saved_file_absolute_path=str(saved_file.resolve()),
                    saved_file_bytes=saved_file.read_bytes() if saved_file.is_file() else None,
                    stripped_environment_variables=stripped_environment_variables,
                )

    def _observe_command(
        self,
        *,
        repository_path: Path,
        executable_path: Path,
        token: str,
    ) -> tuple[TrackStateCliCommandObservation, tuple[str, ...]]:
        executed_command = (str(executable_path), *REQUESTED_COMMAND[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        stripped = tuple(
            variable
            for variable in ("GH_TOKEN", "GITHUB_TOKEN", "TRACKSTATE_TOKEN")
            if env.pop(variable, None) is not None
        )
        env["TRACKSTATE_TOKEN"] = token
        sandbox_home = repository_path / ".ts540-home"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(sandbox_home)
        env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
        env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
        env["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            executed_command,
            cwd=repository_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        observation = TrackStateCliCommandObservation(
            requested_command=REQUESTED_COMMAND,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and injected the GitHub credential through TRACKSTATE_TOKEN so TS-540 "
                "runs the release-backed local download path deterministically."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=CliCommandResult(
                command=executed_command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                json_payload=self._parse_json(completed.stdout),
            ),
        )
        return observation, stripped

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        fixture: ReleaseFixture,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / PROJECT_KEY / "project.json",
            (
                "{\n"
                f'  "key": "{PROJECT_KEY}",\n'
                f'  "name": "{PROJECT_NAME}",\n'
                '  "attachmentStorage": {\n'
                '    "mode": "github-releases",\n'
                '    "githubReleases": {\n'
                f'      "tagPrefix": "{ATTACHMENT_TAG_PREFIX}"\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
        )
        self._write_file(
            repository_path / PROJECT_KEY / "config" / "statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / PROJECT_KEY / "config" / "issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / PROJECT_KEY / "config" / "fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / ISSUE_PATH / "main.md",
            f"""---
key: {ISSUE_KEY}
project: {PROJECT_KEY}
issueType: story
status: todo
summary: "{ISSUE_SUMMARY}"
assignee: tester
reporter: tester
updated: {ATTACHMENT_CREATED_AT}
---

# Description

TS-540 local github-releases attachment download success fixture.
""",
        )
        self._write_file(
            repository_path / MANIFEST_PATH,
            json.dumps(
                [
                    {
                        "id": ATTACHMENT_RELATIVE_PATH,
                        "name": ATTACHMENT_NAME,
                        "mediaType": ATTACHMENT_MEDIA_TYPE,
                        "sizeBytes": len(fixture.asset_bytes),
                        "author": ATTACHMENT_AUTHOR,
                        "createdAt": ATTACHMENT_CREATED_AT,
                        "storagePath": ATTACHMENT_RELATIVE_PATH,
                        "revisionOrOid": ATTACHMENT_REVISION_OR_OID,
                        "storageBackend": "github-releases",
                        "githubReleaseTag": fixture.tag_name,
                        "githubReleaseAssetName": fixture.asset_name,
                    }
                ],
                indent=2,
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-540 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts540@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", fixture.remote_origin_url)
        git_environment = {
            "GIT_AUTHOR_NAME": "TS-540 Tester",
            "GIT_AUTHOR_EMAIL": "ts540@example.com",
            "GIT_AUTHOR_DATE": ATTACHMENT_CREATED_AT,
            "GIT_COMMITTER_NAME": "TS-540 Tester",
            "GIT_COMMITTER_EMAIL": "ts540@example.com",
            "GIT_COMMITTER_DATE": ATTACHMENT_CREATED_AT,
        }
        self._git(repository_path, "add", ".", env=git_environment)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-540 release-backed local download fixture",
            env=git_environment,
        )

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
    ) -> LocalRepositoryState:
        issue_main = repository_path / ISSUE_PATH / "main.md"
        attachments_metadata_path = repository_path / MANIFEST_PATH
        metadata = self._metadata_summary(attachments_metadata_path)
        expected_output = repository_path / EXPECTED_OUTPUT_RELATIVE_PATH
        downloads_directory = expected_output.parent
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return LocalRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachments_metadata_exists=attachments_metadata_path.is_file(),
            metadata_attachment_ids=metadata["attachment_ids"],
            metadata_storage_backends=metadata["storage_backends"],
            metadata_release_tags=metadata["release_tags"],
            metadata_release_asset_names=metadata["release_asset_names"],
            expected_output_exists=expected_output.is_file(),
            expected_output_size_bytes=(
                expected_output.stat().st_size if expected_output.is_file() else None
            ),
            downloads_directory_exists=downloads_directory.is_dir(),
            git_status_lines=self._git_status_lines(repository_path),
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _metadata_summary(self, metadata_path: Path) -> dict[str, tuple[str, ...]]:
        if not metadata_path.is_file():
            empty: tuple[str, ...] = ()
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            empty = ()
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        if not isinstance(payload, list):
            empty = ()
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        attachment_ids: list[str] = []
        storage_backends: list[str] = []
        release_tags: list[str] = []
        release_asset_names: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            attachment_id = entry.get("id")
            storage_backend = entry.get("storageBackend")
            release_tag = entry.get("githubReleaseTag")
            release_asset_name = entry.get("githubReleaseAssetName")
            if isinstance(attachment_id, str) and attachment_id:
                attachment_ids.append(attachment_id)
            if isinstance(storage_backend, str) and storage_backend:
                storage_backends.append(storage_backend)
            if isinstance(release_tag, str) and release_tag:
                release_tags.append(release_tag)
            if isinstance(release_asset_name, str) and release_asset_name:
                release_asset_names.append(release_asset_name)
        return {
            "attachment_ids": tuple(attachment_ids),
            "storage_backends": tuple(storage_backends),
            "release_tags": tuple(release_tags),
            "release_asset_names": tuple(release_asset_names),
        }

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0


class Ts540ReleaseDownloadSuccessScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.live_config = load_live_setup_test_config()
        self.service = LiveSetupRepositoryService(config=self.live_config)
        self.probe = Ts540LocalReleaseDownloadProbe(self.repository_root)

    def execute(self) -> dict[str, object]:
        token = self.service.token
        if not token:
            raise RuntimeError(
                "TS-540 requires GH_TOKEN or GITHUB_TOKEN to create the live GitHub "
                "Release fixture and then download it through the local CLI path."
            )

        remote_origin_url = f"https://github.com/{self.service.repository}.git"
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "app_url": self.live_config.app_url,
            "repository": self.service.repository,
            "repository_ref": self.service.ref,
            "remote_origin_url": remote_origin_url,
            "ticket_command": TICKET_COMMAND,
            "requested_command": " ".join(REQUESTED_COMMAND),
            "os": platform.system(),
            "project_key": PROJECT_KEY,
            "project_name": PROJECT_NAME,
            "issue_key": ISSUE_KEY,
            "issue_summary": ISSUE_SUMMARY,
            "manifest_path": MANIFEST_PATH,
            "attachment_name": ATTACHMENT_NAME,
            "attachment_relative_path": ATTACHMENT_RELATIVE_PATH,
            "attachment_media_type": ATTACHMENT_MEDIA_TYPE,
            "attachment_size_bytes": len(ATTACHMENT_BYTES),
            "attachment_created_at": ATTACHMENT_CREATED_AT,
            "attachment_revision_or_oid": ATTACHMENT_REVISION_OR_OID,
            "attachment_tag_prefix": ATTACHMENT_TAG_PREFIX,
            "attachment_release_tag": ATTACHMENT_RELEASE_TAG,
            "attachment_release_title": ATTACHMENT_RELEASE_TITLE,
            "attachment_release_body": ATTACHMENT_RELEASE_BODY,
            "attachment_release_asset_name": ATTACHMENT_NAME,
            "expected_output_relative_path": EXPECTED_OUTPUT_RELATIVE_PATH,
            "steps": [],
            "human_verification": [],
        }

        cleanup_error: Exception | None = None
        scenario_error: Exception | None = None
        try:
            pre_cleanup_actions = _delete_releases_by_tag(
                service=self.service,
                tag_name=ATTACHMENT_RELEASE_TAG,
            )
            result["pre_cleanup_actions"] = pre_cleanup_actions
            fixture = _create_release_fixture(
                service=self.service,
                remote_origin_url=remote_origin_url,
            )
            result["fixture_setup"] = _fixture_to_dict(fixture)
            probe_result = self.probe.execute(fixture=fixture, token=token)
            result.update(_probe_result_to_dict(probe_result))

            failures = self._validate_preconditions(probe_result)
            failures.extend(self._validate_runtime(probe_result, result))
            failures.extend(self._validate_filesystem_state(probe_result, result))
            if failures:
                raise AssertionError("\n".join(failures))
        except Exception as error:
            scenario_error = error
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        finally:
            try:
                cleanup_actions = _delete_releases_by_tag(
                    service=self.service,
                    tag_name=ATTACHMENT_RELEASE_TAG,
                )
                result["cleanup"] = cleanup_actions
            except Exception as error:
                cleanup_error = error
                result["cleanup"] = {
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                }
                if scenario_error is None:
                    scenario_error = error
                    result["error"] = f"{type(error).__name__}: {error}"
                    result["traceback"] = traceback.format_exc()

        if scenario_error is not None:
            if cleanup_error is not None and cleanup_error is not scenario_error:
                result["traceback"] = (
                    str(result.get("traceback", ""))
                    + "\nCleanup error:\n"
                    + "".join(
                        traceback.format_exception(
                            type(cleanup_error),
                            cleanup_error,
                            cleanup_error.__traceback__,
                        )
                    )
                )
            _write_failure_outputs(result)
            raise scenario_error

        _write_pass_outputs(result)
        return result

    def _validate_preconditions(
        self,
        probe_result: LocalReleaseDownloadProbeResult,
    ) -> list[str]:
        failures: list[str] = []
        initial_state = probe_result.initial_state
        if probe_result.observation.requested_command != REQUESTED_COMMAND:
            failures.append(
                "Precondition failed: TS-540 did not execute the expected supported "
                "release-backed local download command.\n"
                f"Expected command: {' '.join(REQUESTED_COMMAND)}\n"
                f"Observed command: {probe_result.observation.requested_command_text}"
            )
        if probe_result.observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-540 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {probe_result.observation.executed_command_text}\n"
                f"Fallback reason: {probe_result.observation.fallback_reason}"
            )
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain TS-123 "
                "before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded local repository did not contain "
                "attachments.json before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if ATTACHMENT_RELATIVE_PATH not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-540.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if "github-releases" not in initial_state.metadata_storage_backends:
            failures.append(
                "Precondition failed: attachments.json did not preserve the "
                "github-releases storage backend before the download ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if ATTACHMENT_RELEASE_TAG not in initial_state.metadata_release_tags:
            failures.append(
                "Precondition failed: attachments.json did not point manual.pdf at the "
                "seeded GitHub Release tag.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if ATTACHMENT_NAME not in initial_state.metadata_release_asset_names:
            failures.append(
                "Precondition failed: attachments.json did not point manual.pdf at the "
                "seeded GitHub Release asset.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the disposable repository already contained the "
                "expected output file before TS-540 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        probe_result: LocalReleaseDownloadProbeResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = probe_result.observation
        payload = observation.result.json_payload
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_output = _visible_output_text(payload, stdout=stdout, stderr=stderr)
        result["visible_output_text"] = visible_output

        if observation.result.exit_code != 0:
            lowered_output = visible_output.lower()
            if any(fragment in lowered_output for fragment in PROVIDER_CAPABILITY_FRAGMENTS):
                result["failure_mode"] = "local_provider_capability_gate"
                result["product_gap"] = (
                    "The local attachment-download path still fails through the "
                    "provider-level GitHub Releases capability gate instead of "
                    "delegating to the release storage handler."
                )
            failures.append(
                "Step 1 failed: the release-backed local download command did not "
                "succeed.\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"Visible output:\n{visible_output}\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if not isinstance(payload, dict):
            failures.append(
                "Step 1 failed: the CLI succeeded but did not return a single JSON "
                "success envelope.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        missing_top_level = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
        if missing_top_level:
            failures.append(
                "Step 1 failed: the JSON success envelope omitted required top-level "
                "fields.\n"
                f"Missing keys: {missing_top_level}\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures

        if payload.get("ok") is not True:
            failures.append(
                "Step 1 failed: the CLI returned a JSON envelope, but it was not a "
                "successful attachment-download result.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if payload.get("provider") != "local-git":
            failures.append(
                "Step 1 failed: the success envelope did not report the canonical "
                "local-git provider.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        if payload.get("output") != "json":
            failures.append(
                "Step 1 failed: the CLI did not return the default JSON success "
                "envelope.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
        target = payload.get("target")
        if not isinstance(target, dict):
            failures.append(
                "Step 1 failed: the success envelope did not expose target metadata "
                "as an object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures
        missing_target = [key for key in REQUIRED_TARGET_KEYS if key not in target]
        if missing_target:
            failures.append(
                "Step 1 failed: the target metadata omitted required fields.\n"
                f"Missing keys: {missing_target}\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )
        if target.get("type") != "local":
            failures.append(
                "Step 1 failed: the success envelope did not report a local target.\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )
        if target.get("value") != observation.repository_path:
            failures.append(
                "Human-style verification failed: the visible target metadata did not "
                "show the repository path the user targeted.\n"
                f"Expected path: {observation.repository_path}\n"
                f"Observed target: {json.dumps(target, indent=2, sort_keys=True)}"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            failures.append(
                "Step 1 failed: the success envelope data payload was not an object.\n"
                f"Observed payload: {json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures

        missing_data = [key for key in REQUIRED_DATA_KEYS if key not in data]
        if missing_data:
            failures.append(
                "Step 1 failed: the success envelope omitted required attachment "
                "download metadata fields.\n"
                f"Missing keys: {missing_data}\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
            return failures

        if data.get("command") != "attachment-download":
            failures.append(
                "Step 1 failed: the success envelope did not identify the canonical "
                "attachment-download command.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("authSource") != "none":
            failures.append(
                "Step 1 failed: the success envelope did not preserve the deployed "
                "local-git authSource value.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("issue") != ISSUE_KEY:
            failures.append(
                "Step 1 failed: the success envelope did not identify the issue that "
                "owns the downloaded attachment.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        observed_saved_file = data.get("savedFile")
        if not isinstance(observed_saved_file, str) or not observed_saved_file:
            failures.append(
                "Step 1 failed: the success envelope did not return the saved-file path "
                "as a non-empty string.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
        elif str(Path(observed_saved_file).resolve()) != probe_result.saved_file_absolute_path:
            failures.append(
                "Step 1 failed: the success envelope did not report the resolved output "
                "file path requested by the user.\n"
                f"Expected savedFile: {probe_result.saved_file_absolute_path}\n"
                f"Observed savedFile: {observed_saved_file}"
            )

        attachment = data.get("attachment")
        if not isinstance(attachment, dict):
            failures.append(
                "Step 1 failed: the success envelope did not include attachment metadata "
                "as an object.\n"
                f"Observed data: {json.dumps(data, indent=2, sort_keys=True)}"
            )
            return failures

        missing_attachment = [
            key for key in REQUIRED_ATTACHMENT_KEYS if key not in attachment
        ]
        if missing_attachment:
            failures.append(
                "Step 1 failed: the attachment metadata omitted required fields.\n"
                f"Missing keys: {missing_attachment}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        forbidden_keys = sorted(FORBIDDEN_ATTACHMENT_PAYLOAD_KEYS.intersection(attachment))
        if forbidden_keys:
            failures.append(
                "Step 1 failed: the visible attachment metadata exposed payload content "
                "instead of metadata only.\n"
                f"Forbidden keys present: {forbidden_keys}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("id") != ATTACHMENT_RELATIVE_PATH:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the requested "
                "attachment identifier.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("name") != ATTACHMENT_NAME:
            failures.append(
                "Human-style verification failed: the visible CLI response did not show "
                "the downloaded attachment filename.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("mediaType") != ATTACHMENT_MEDIA_TYPE:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the PDF media "
                "type.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("sizeBytes") != len(ATTACHMENT_BYTES):
            failures.append(
                "Step 1 failed: the attachment metadata did not report the original "
                "binary size.\n"
                f"Expected size: {len(ATTACHMENT_BYTES)}\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("createdAt") != ATTACHMENT_CREATED_AT:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the seeded "
                "creation timestamp.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("revisionOrOid") != ATTACHMENT_REVISION_OR_OID:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the stored "
                "release-backed revision marker.\n"
                f"Observed attachment: {json.dumps(attachment, indent=2, sort_keys=True)}"
            )

        expected_stdout_fragments = (
            '"provider": "local-git"',
            '"command": "attachment-download"',
            '"authSource": "none"',
            f'"issue": "{ISSUE_KEY}"',
            f'"name": "{ATTACHMENT_NAME}"',
            '"savedFile": "',
            "/downloads/manual.pdf",
        )
        for fragment in expected_stdout_fragments:
            if fragment not in stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI response did not "
                    "show the expected success metadata.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{stdout}"
                )
        if stderr.strip():
            failures.append(
                "Step 1 failed: the successful download still emitted stderr output.\n"
                f"Observed stderr:\n{stderr}"
            )
        if not failures:
            _record_step(
                result,
                step=1,
                status="passed",
                action=TICKET_COMMAND,
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"provider={payload.get('provider')}; "
                    f"authSource={data.get('authSource')}; "
                    f"savedFile={observed_saved_file}; "
                    f"visible_output={visible_output}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the caller-visible JSON success response reported the "
                    "release-backed local-git download, the observed authSource value, the "
                    "manual.pdf attachment metadata, and the saved-file path."
                ),
                observed=visible_output,
            )
        return failures

    def _validate_filesystem_state(
        self,
        probe_result: LocalReleaseDownloadProbeResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = probe_result.final_state
        if not final_state.expected_output_exists:
            failures.append(
                "Step 2 failed: the local runtime did not create the requested "
                "downloaded manual.pdf file.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if probe_result.saved_file_bytes != ATTACHMENT_BYTES:
            failures.append(
                "Step 2 failed: the downloaded file bytes did not match the seeded "
                "GitHub Release asset payload.\n"
                f"Expected byte count: {len(ATTACHMENT_BYTES)}\n"
                f"Actual byte count: {len(probe_result.saved_file_bytes or b'')}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.expected_output_size_bytes != len(ATTACHMENT_BYTES):
            failures.append(
                "Step 2 failed: the filesystem size of the downloaded file did not "
                "match the release asset size.\n"
                f"Expected size: {len(ATTACHMENT_BYTES)}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )

        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Inspect the command output and the local filesystem after the "
                    "successful download."
                ),
                observed=(
                    f"expected_output_exists={final_state.expected_output_exists}; "
                    f"expected_output_size_bytes={final_state.expected_output_size_bytes}; "
                    f"saved_file_absolute_path={probe_result.saved_file_absolute_path}; "
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified as a user that manual.pdf was actually written to the "
                    "requested local path and that its bytes matched the GitHub Release "
                    "asset exactly."
                ),
                observed=(
                    f"saved_file={probe_result.saved_file_absolute_path}; "
                    f"size_bytes={final_state.expected_output_size_bytes}"
                ),
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts540ReleaseDownloadSuccessScenario()
    scenario.execute()


def _create_release_fixture(
    *,
    service: LiveSetupRepositoryService,
    remote_origin_url: str,
) -> ReleaseFixture:
    release = service.create_release(
        tag_name=ATTACHMENT_RELEASE_TAG,
        name=ATTACHMENT_RELEASE_TITLE,
        body=ATTACHMENT_RELEASE_BODY,
        target_commitish=service.ref,
        draft=False,
        prerelease=False,
    )
    uploaded_asset = service.upload_release_asset(
        release_id=release.id,
        asset_name=ATTACHMENT_NAME,
        content_type=ATTACHMENT_MEDIA_TYPE,
        content=ATTACHMENT_BYTES,
    )

    matched, observed = poll_until(
        probe=lambda: _fetch_release_fixture_state(service, remote_origin_url),
        is_satisfied=lambda value: value is not None
        and value.asset_name == ATTACHMENT_NAME
        and value.asset_bytes == ATTACHMENT_BYTES,
        timeout_seconds=RELEASE_TIMEOUT_SECONDS,
        interval_seconds=RELEASE_POLL_INTERVAL_SECONDS,
    )
    if not matched or observed is None:
        raise AssertionError(
            "Precondition failed: the seeded GitHub Release fixture never exposed the "
            f"{ATTACHMENT_NAME} asset bytes for TS-540.\n"
            f"Observed state: {observed}",
        )
    if observed.release_id != release.id or observed.asset_id != uploaded_asset.id:
        raise AssertionError(
            "Precondition failed: the observed release fixture did not match the "
            "release or asset created for TS-540.\n"
            f"Created release id: {release.id}; created asset id: {uploaded_asset.id}\n"
            f"Observed fixture: {_fixture_to_dict(observed)}"
        )
    return observed


def _fetch_release_fixture_state(
    service: LiveSetupRepositoryService,
    remote_origin_url: str,
) -> ReleaseFixture | None:
    release = service.fetch_release_by_tag(ATTACHMENT_RELEASE_TAG)
    if release is None:
        return None
    matching_asset = next(
        (asset for asset in release.assets if asset.name == ATTACHMENT_NAME),
        None,
    )
    if matching_asset is None:
        return None
    asset_bytes = service.download_release_asset_bytes(matching_asset.id)
    return ReleaseFixture(
        repository=service.repository,
        repository_ref=service.ref,
        remote_origin_url=remote_origin_url,
        tag_name=release.tag_name,
        title=release.name,
        asset_name=matching_asset.name,
        asset_id=matching_asset.id,
        asset_bytes=asset_bytes,
        release_id=release.id,
    )


def _delete_releases_by_tag(
    *,
    service: LiveSetupRepositoryService,
    tag_name: str,
) -> dict[str, object]:
    actions: list[str] = []
    matches = service.fetch_releases_by_tag_any_state(tag_name)
    for release in matches:
        for asset in release.assets:
            service.delete_release_asset(asset.id)
            actions.append(
                f"deleted asset {asset.name} ({asset.id}) from release {release.id}"
            )
        service.delete_release(release.id)
        actions.append(f"deleted release {release.id} ({release.tag_name})")
    matched, remaining = poll_until(
        probe=lambda: service.fetch_releases_by_tag_any_state(tag_name),
        is_satisfied=lambda value: not value,
        timeout_seconds=RELEASE_TIMEOUT_SECONDS,
        interval_seconds=RELEASE_POLL_INTERVAL_SECONDS,
    )
    if not matched:
        raise AssertionError(
            f"Cleanup failed: releases tagged {tag_name} still exist.\n"
            f"Remaining releases: {[release.id for release in remaining]}"
        )
    return {
        "status": "completed",
        "tag_name": tag_name,
        "actions": actions,
        "remaining_release_ids": [release.id for release in remaining],
    }


def _probe_result_to_dict(
    probe_result: LocalReleaseDownloadProbeResult,
) -> dict[str, object]:
    payload = probe_result.observation.result.json_payload
    payload_dict = payload if isinstance(payload, dict) else None
    return {
        "repository_path": probe_result.observation.repository_path,
        "compiled_binary_path": probe_result.observation.compiled_binary_path,
        "executed_command": probe_result.observation.executed_command_text,
        "exit_code": probe_result.observation.result.exit_code,
        "stdout": probe_result.observation.result.stdout,
        "stderr": probe_result.observation.result.stderr,
        "payload": payload_dict,
        "initial_state": _state_to_dict(probe_result.initial_state),
        "final_state": _state_to_dict(probe_result.final_state),
        "saved_file_absolute_path": probe_result.saved_file_absolute_path,
        "saved_file_size_bytes": (
            len(probe_result.saved_file_bytes)
            if probe_result.saved_file_bytes is not None
            else None
        ),
        "stripped_environment_variables": list(
            probe_result.stripped_environment_variables
        ),
    }


def _fixture_to_dict(fixture: ReleaseFixture) -> dict[str, object]:
    return {
        "repository": fixture.repository,
        "repository_ref": fixture.repository_ref,
        "remote_origin_url": fixture.remote_origin_url,
        "tag_name": fixture.tag_name,
        "title": fixture.title,
        "asset_name": fixture.asset_name,
        "asset_id": fixture.asset_id,
        "asset_size_bytes": len(fixture.asset_bytes),
        "release_id": fixture.release_id,
    }


def _write_pass_outputs(result: dict[str, object]) -> None:
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
        ),
        encoding="utf-8",
    )

    visible_output = _as_text(result.get("visible_output_text"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            "* Created a real GitHub Release fixture in "
            f"{_jira_inline(_as_text(result.get('repository')))} with tag "
            f"{_jira_inline(_as_text(result.get('attachment_release_tag')))} and asset "
            f"{_jira_inline(_as_text(result.get('attachment_name')))}."
        ),
        (
            f"* Executed the current supported equivalent {_jira_inline(_as_text(result.get('ticket_command')))} "
            "from a disposable local-git TrackState repository whose "
            f"{_jira_inline('attachments.json')} points {_jira_inline('manual.pdf')} at "
            f"GitHub Releases in {_jira_inline(_as_text(result.get('remote_origin_url')))}."
        ),
        "* Verified the caller-visible JSON success response and the downloaded local file contents.",
        "",
        "h4. Result",
        "* Step 1 passed: the local-git provider succeeded instead of failing at the provider capability gate.",
        f"* Observed visible response: {_jira_inline(visible_output)}",
        (
            "* Step 2 passed: "
            f"{_jira_inline(_as_text(result.get('saved_file_absolute_path')))} was created "
            "and matched the seeded GitHub Release asset bytes."
        ),
        (
            "* Human-style verification passed: the visible JSON output showed "
            f"{_jira_inline('provider = local-git')}, {_jira_inline('authSource = none')}, "
            f"{_jira_inline('Attachment: manual.pdf')}, and the requested saved-file path."
        ),
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Created a real GitHub Release fixture in `{_as_text(result.get('repository'))}` "
            f"with tag `{_as_text(result.get('attachment_release_tag'))}` and asset "
            f"`{_as_text(result.get('attachment_name'))}`."
        ),
        (
            f"- Executed the current supported equivalent `{_as_text(result.get('ticket_command'))}` "
            "from a disposable local-git TrackState repository whose `attachments.json` "
            f"points `manual.pdf` at GitHub Releases in `{_as_text(result.get('remote_origin_url'))}`."
        ),
        "- Verified the caller-visible JSON success response and the downloaded local file contents.",
        "",
        "## Result",
        "- Step 1 passed: the local-git provider succeeded instead of failing at the provider capability gate.",
        f"- Observed visible response: `{visible_output}`",
        (
            "- Step 2 passed: "
            f"`{_as_text(result.get('saved_file_absolute_path'))}` was created and matched "
            "the seeded GitHub Release asset bytes."
        ),
        (
            "- Human-style verification passed: the visible JSON output showed "
            "`provider = local-git`, `authSource = none`, `manual.pdf`, and the requested "
            "saved-file path."
        ),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        ),
        encoding="utf-8",
    )

    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    visible_output = _visible_output_text(result.get("payload"), stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state_text = json.dumps(result.get("final_state"), indent=2, sort_keys=True)
    failure_mode = _as_text(result.get("failure_mode"))
    product_gap = _as_text(result.get("product_gap"))
    if failure_mode == "local_provider_capability_gate":
        step_one_summary = (
            "the local release-backed download path failed earlier at the provider "
            "capability gate, so the command never delegated to the GitHub Releases "
            "storage handler"
        )
        actual_result_line = (
            "* The command failed with the generic provider capability error "
            f"{_jira_inline(visible_output)} instead of downloading the release asset."
        )
        human_summary = (
            "Human-style verification observed a terminal failure and no downloaded "
            "manual.pdf file, but the visible error was the generic provider "
            "capability message instead of a success response."
        )
    else:
        step_one_summary = (
            "the command did not produce the expected successful release-backed "
            "download outcome"
        )
        actual_result_line = (
            "* The command either failed outright or returned a malformed success "
            f"response. Visible output: {_jira_inline(visible_output)}."
        )
        human_summary = (
            "Human-style verification observed that the caller-visible output or the "
            "downloaded file state did not match the successful local download "
            "experience required by TS-540."
        )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Created a real GitHub Release fixture in {_jira_inline(_as_text(result.get('repository')))} "
            f"with tag {_jira_inline(_as_text(result.get('attachment_release_tag')))} and asset "
            f"{_jira_inline(_as_text(result.get('attachment_name')))}."
        ),
        (
            f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a "
            "disposable local-git TrackState repository whose release-backed "
            f"{_jira_inline('attachments.json')} entry targets {_jira_inline(_as_text(result.get('remote_origin_url')))}."
        ),
        "* Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "h4. Result",
        f"* ❌ Step 1 failed: {step_one_summary}.",
        f"* Observed visible output: {_jira_inline(visible_output)}",
        f"* Observed saved file: {_jira_inline(_as_text(result.get('saved_file_absolute_path')))}",
        f"* {human_summary}",
        *([f"* Product gap: {product_gap}"] if product_gap else []),
        "* Observed final repository state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Observed output",
        "{code}",
        observed_output,
        "{code}",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Created a real GitHub Release fixture in `{_as_text(result.get('repository'))}` "
            f"with tag `{_as_text(result.get('attachment_release_tag'))}` and asset "
            f"`{_as_text(result.get('attachment_name'))}`."
        ),
        (
            f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable "
            "local-git TrackState repository whose release-backed `attachments.json` "
            f"entry targets `{_as_text(result.get('remote_origin_url'))}`."
        ),
        "- Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "## Result",
        f"- ❌ Step 1 failed: {step_one_summary}.",
        f"- Observed visible output: `{visible_output}`",
        f"- Observed saved file: `{_as_text(result.get('saved_file_absolute_path'))}`",
        f"- {human_summary}",
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "- Observed final repository state:",
        "```json",
        final_state_text,
        "```",
        "",
        "## Observed output",
        "```text",
        observed_output,
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository: `{_as_text(result.get('repository'))}`",
        f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
        f"- Release tag: `{_as_text(result.get('attachment_release_tag'))}`",
        f"- Release asset: `{_as_text(result.get('attachment_name'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        "- Auth setup: the CLI process received the GitHub token through `TRACKSTATE_TOKEN` and ran with isolated HOME / gh config directories.",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Create a disposable local-git TrackState repository whose "
            "`attachments.json` contains a release-backed `manual.pdf` entry for "
            f"`{_as_text(result.get('attachment_release_tag'))}`. Observed: the seeded "
            "repository contained `TS-123`, `attachments.json`, and the expected "
            "GitHub Releases metadata before the command ran."
        ),
        (
            "2. ✅ Create a real GitHub Release in the live setup repository and upload "
            "`manual.pdf` to it. Observed: the release fixture existed and GitHub "
            "returned the uploaded asset bytes before the CLI command started."
        ),
        (
            "3. ❌ Execute the local attachment download command (automation executed the "
            f"current supported equivalent `{_as_text(result.get('ticket_command'))}`). "
            f"Observed: exit code `{_as_text(result.get('exit_code'))}` with visible output "
            f"`{visible_output}`."
        ),
        (
            "4. "
            + (
                "❌"
                if not result.get("final_state", {}).get("expected_output_exists")
                else "❌"
                if _as_text(result.get("saved_file_size_bytes")) != str(len(ATTACHMENT_BYTES))
                else "✅"
            )
            + " Inspect the command output and the local filesystem. Observed: "
            f"saved file path = `{_as_text(result.get('saved_file_absolute_path'))}`, "
            f"saved file size = `{_as_text(result.get('saved_file_size_bytes'))}`, "
            f"final repository state = `{final_state_text}`."
        ),
        "",
        "## Expected result",
        "- The command should succeed through the release-backed GitHub storage handler.",
        "- The visible CLI output should be a valid success response that reports `provider = local-git`, `authSource = none`, `manual.pdf`, and the saved-file path.",
        f"- The file should be written to `{_as_text(result.get('saved_file_absolute_path'))}` and its bytes should match the GitHub Release asset exactly.",
        "",
        "## Actual result",
        actual_result_line,
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```json",
        stdout.rstrip() or "{}",
        "```",
        "",
        "```text",
        stderr.rstrip() or "<empty>",
        "```",
        "",
        "## Final repository state",
        "```json",
        final_state_text,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _state_to_dict(state: LocalRepositoryState) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "metadata_attachment_ids": list(state.metadata_attachment_ids),
        "metadata_storage_backends": list(state.metadata_storage_backends),
        "metadata_release_tags": list(state.metadata_release_tags),
        "metadata_release_asset_names": list(state.metadata_release_asset_names),
        "expected_output_exists": state.expected_output_exists,
        "expected_output_size_bytes": state.expected_output_size_bytes,
        "downloads_directory_exists": state.downloads_directory_exists,
        "git_status_lines": list(state.git_status_lines),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(state: LocalRepositoryState) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _visible_output_text(payload: object, *, stdout: str = "", stderr: str = "") -> str:
    fragments: list[str] = []
    payload_text = _json_visible_output_text(payload)
    if payload_text:
        fragments.append(payload_text)
    text_fragments = []
    if not (payload_text and _looks_like_json(stdout)):
        text_fragments.append(_collapse_output(stdout))
    if not (payload_text and _looks_like_json(stderr)):
        text_fragments.append(_collapse_output(stderr))
    for fragment in text_fragments:
        if fragment and all(fragment.lower() not in existing.lower() for existing in fragments):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_output_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    provider = payload.get("provider")
    if isinstance(provider, str) and provider:
        parts.append(provider)
    target = payload.get("target")
    if isinstance(target, dict):
        target_type = target.get("type")
        target_value = target.get("value")
        if isinstance(target_type, str) and target_type:
            parts.append(target_type)
        if isinstance(target_value, str) and target_value:
            parts.append(target_value)
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("command", "authSource", "issue", "savedFile"):
            value = data.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
        attachment = data.get("attachment")
        if isinstance(attachment, dict):
            for key in ("name", "id", "mediaType", "revisionOrOid"):
                value = attachment.get(key)
                if isinstance(value, str) and value:
                    parts.append(value)
    error = payload.get("error")
    if isinstance(error, dict):
        for key in ("code", "category", "message"):
            value = error.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
    return " | ".join(parts)


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if stdout.strip():
        fragments.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        fragments.append(f"stderr:\n{stderr.rstrip()}")
    return "\n\n".join(fragments) or "<empty>"


def _jira_inline(value: str) -> str:
    safe = value or "<missing>"
    return "{{" + safe.replace("{{", "{").replace("}}", "}") + "}}"


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


if __name__ == "__main__":
    main()
