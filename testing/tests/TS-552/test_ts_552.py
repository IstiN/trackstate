from __future__ import annotations

import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (  # noqa: E402
    PythonTrackStateCliCompiledLocalFramework,
)

TICKET_KEY = "TS-552"
TICKET_SUMMARY = (
    "Local release-backed upload fails with an asset container conflict when the "
    "release already contains a foreign asset"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-552/test_ts_552.py"
RUN_COMMAND = "python testing/tests/TS-552/test_ts_552.py"


@dataclass(frozen=True)
class Ts552Config:
    ticket_command: str
    requested_command: tuple[str, ...]
    repository: str
    branch: str
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    seeded_manifest_text: str
    release_tag_prefix_base: str
    foreign_asset_name: str
    expected_release_title: str
    expected_exit_code: int
    expected_error_code: str
    expected_error_category: str
    required_reason_fragments: tuple[str, ...]
    release_poll_timeout_seconds: int
    release_poll_interval_seconds: int
    gh_poll_timeout_seconds: int
    gh_poll_interval_seconds: int

    @property
    def source_file_bytes(self) -> bytes:
        return (
            b"%PDF-1.4\n"
            + self.source_file_text.encode("utf-8")
            + b"\n%%EOF\n"
        )

    @property
    def manifest_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments.json"

    @classmethod
    def from_file(cls, path: Path) -> "Ts552Config":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must deserialize to a mapping.")
        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(f"{path} runtime_inputs must deserialize to a mapping.")

        live_setup = load_live_setup_test_config()
        repository = _optional_string(runtime_inputs, "repository") or live_setup.repository
        branch = _optional_string(runtime_inputs, "branch") or live_setup.ref

        return cls(
            ticket_command=_require_string(runtime_inputs, "ticket_command", path),
            requested_command=_require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            repository=repository,
            branch=branch,
            project_key=_require_string(runtime_inputs, "project_key", path),
            project_name=_require_string(runtime_inputs, "project_name", path),
            issue_key=_require_string(runtime_inputs, "issue_key", path),
            issue_summary=_require_string(runtime_inputs, "issue_summary", path),
            source_file_name=_require_string(runtime_inputs, "source_file_name", path),
            source_file_text=_require_string(runtime_inputs, "source_file_text", path),
            seeded_manifest_text=_require_string(runtime_inputs, "seeded_manifest_text", path),
            release_tag_prefix_base=_require_string(
                runtime_inputs,
                "release_tag_prefix_base",
                path,
            ),
            foreign_asset_name=_require_string(runtime_inputs, "foreign_asset_name", path),
            expected_release_title=_require_string(
                runtime_inputs,
                "expected_release_title",
                path,
            ),
            expected_exit_code=_require_int(runtime_inputs, "expected_exit_code", path),
            expected_error_code=_require_string(
                runtime_inputs,
                "expected_error_code",
                path,
            ),
            expected_error_category=_require_string(
                runtime_inputs,
                "expected_error_category",
                path,
            ),
            required_reason_fragments=_require_string_list(
                runtime_inputs,
                "required_reason_fragments",
                path,
            ),
            release_poll_timeout_seconds=_require_int(
                runtime_inputs,
                "release_poll_timeout_seconds",
                path,
            ),
            release_poll_interval_seconds=_require_int(
                runtime_inputs,
                "release_poll_interval_seconds",
                path,
            ),
            gh_poll_timeout_seconds=_require_int(
                runtime_inputs,
                "gh_poll_timeout_seconds",
                path,
            ),
            gh_poll_interval_seconds=_require_int(
                runtime_inputs,
                "gh_poll_interval_seconds",
                path,
            ),
        )


class Ts552LocalForeignAssetConflictScenario(PythonTrackStateCliCompiledLocalFramework):
    def __init__(self) -> None:
        super().__init__(REPO_ROOT)
        self.config_path = REPO_ROOT / "testing/tests/TS-552/config.yaml"
        self.config = Ts552Config.from_file(self.config_path)
        self.service = LiveSetupRepositoryService()
        if not self.service.token:
            raise AssertionError(
                "TS-552 requires GH_TOKEN or GITHUB_TOKEN to seed and inspect the live "
                "GitHub Release fixture.",
            )
        self.remote_origin_url = f"https://github.com/{self.config.repository}.git"
        self.run_suffix = uuid.uuid4().hex[:8]
        self.release_tag_prefix = f"{self.config.release_tag_prefix_base}{self.run_suffix}-"
        self.release_tag = f"{self.release_tag_prefix}{self.config.issue_key}"

    def execute(self) -> tuple[dict[str, object], list[str]]:
        result: dict[str, object] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "requested_command": " ".join(self.config.requested_command),
            "config_path": str(self.config_path),
            "repository": self.config.repository,
            "repository_ref": self.config.branch,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "manifest_path": self.config.manifest_path,
            "source_file_name": self.config.source_file_name,
            "foreign_asset_name": self.config.foreign_asset_name,
            "remote_origin_url": self.remote_origin_url,
            "release_tag": self.release_tag,
            "release_title": self.config.expected_release_title,
            "steps": [],
            "human_verification": [],
        }
        failures: list[str] = []

        release_created = False
        cleanup_error: Exception | None = None
        scenario_error: Exception | None = None

        try:
            self._seed_release_fixture()
            release_created = True
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-552-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                result["compiled_binary_path"] = str(executable_path)

                with tempfile.TemporaryDirectory(
                    prefix="trackstate-ts-552-repo-",
                    dir=OUTPUTS_DIR,
                ) as temp_repo_dir:
                    repository_path = Path(temp_repo_dir)
                    self._seed_local_repository(repository_path)
                    initial_state = self._capture_local_state(repository_path)
                    gh_preflight = self._observe_gh_release_view()
                    fixture_state = self._observe_release_state()
                    result["repository_path"] = str(repository_path)
                    result["initial_state"] = initial_state
                    result["fixture_release_state"] = fixture_state
                    result["preflight_gh_release_view"] = gh_preflight

                    failures.extend(
                        self._assert_fixture_state(
                            initial_state=initial_state,
                            fixture_state=fixture_state,
                            gh_view=gh_preflight,
                        ),
                    )
                    if not failures:
                        _record_step(
                            result,
                            step=1,
                            status="passed",
                            action=(
                                "Seed a disposable local TrackState repository plus a real "
                                "GitHub Release fixture with a foreign asset."
                            ),
                            observed=(
                                f"remote_origin_url={initial_state['remote_origin_url']}; "
                                f"manifest_text={initial_state['manifest_text']!r}; "
                                f"release_asset_names={fixture_state['release_asset_names']}"
                            ),
                        )

                    observation = self._run_ticket_command(
                        repository_path=repository_path,
                        executable_path=executable_path,
                    )
                    result.update(observation)

                    runtime_failures = self._assert_runtime_expectations(result)
                    failures.extend(runtime_failures)
                    if not runtime_failures:
                        _record_step(
                            result,
                            step=2,
                            status="passed",
                            action=self.config.ticket_command,
                            observed=(
                                f"exit_code={result.get('exit_code')}; "
                                f"error_code={result.get('observed_error_code')}; "
                                f"error_category={result.get('observed_error_category')}; "
                                f"visible_output={_compact_text(_as_text(result.get('visible_output')))}"
                            ),
                        )
                        _record_human_verification(
                            result,
                            check=(
                                "Verified the exact terminal output shown to a user named the "
                                "foreign release asset conflict and required manual cleanup."
                            ),
                            observed=_as_text(result.get("visible_output")),
                        )

                    final_state = self._capture_local_state(repository_path)
                    result["final_state"] = final_state
                    local_failures = self._assert_local_state(final_state)
                    failures.extend(local_failures)
                    if not local_failures:
                        _record_step(
                            result,
                            step=3,
                            status="passed",
                            action=(
                                "Inspect the local repository after the failed upload attempt."
                            ),
                            observed=(
                                f"manifest_text={final_state['manifest_text']!r}; "
                                f"stored_files={final_state['stored_files']}; "
                                f"git_status_lines={final_state['git_status_lines']}"
                            ),
                        )

            remote_state = self._observe_release_state()
            gh_release_view = self._observe_gh_release_view()
            result["remote_state_after_command"] = remote_state
            result["gh_release_view"] = gh_release_view
            remote_failures = self._assert_remote_state(
                remote_state=remote_state,
                gh_view=gh_release_view,
            )
            failures.extend(remote_failures)
            if not remote_failures:
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Check the release state after the failed upload attempt."
                    ),
                    observed=(
                        f"release_asset_names={remote_state['release_asset_names']}; "
                        f"gh_asset_names={gh_release_view['asset_names']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a user through `gh release view` that the release still "
                        "showed only the foreign asset and did not absorb `report.pdf`."
                    ),
                    observed=_as_text(gh_release_view.get("stdout")),
                )
        except Exception as error:
            scenario_error = error
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        finally:
            if release_created:
                try:
                    cleanup = self._cleanup_release()
                    result["cleanup"] = cleanup
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

        if failures and "error" not in result:
            assertion_error = AssertionError("\n".join(failures))
            scenario_error = assertion_error
            result["error"] = f"{type(assertion_error).__name__}: {assertion_error}"
            result["traceback"] = "".join(
                traceback.format_exception(
                    type(assertion_error),
                    assertion_error,
                    assertion_error.__traceback__,
                ),
            )

        if cleanup_error is not None and scenario_error is not None and cleanup_error is not scenario_error:
            result["traceback"] = (
                _as_text(result.get("traceback"))
                + "\nCleanup error:\n"
                + "".join(
                    traceback.format_exception(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )
            )

        return result, failures if scenario_error is None else [str(scenario_error)]

    def _seed_release_fixture(self) -> None:
        existing_release = self.service.fetch_release_by_tag(self.release_tag)
        if existing_release is not None:
            raise AssertionError(
                f"Precondition failed: release tag {self.release_tag} already exists.",
            )

        self.service.create_release(
            tag_name=self.release_tag,
            name=self.config.expected_release_title,
            body=(
                f"{TICKET_KEY} foreign asset conflict fixture for "
                f"{self.config.issue_key}."
            ),
            draft=False,
            prerelease=False,
            target_commitish=self.config.branch,
        )

        matched_release, release = poll_until(
            probe=lambda: self.service.fetch_release_by_tag(self.release_tag),
            is_satisfied=lambda value: value is not None
            and value.name == self.config.expected_release_title,
            timeout_seconds=self.config.release_poll_timeout_seconds,
            interval_seconds=self.config.release_poll_interval_seconds,
        )
        if not matched_release or release is None:
            raise AssertionError(
                "Precondition failed: the GitHub release fixture was not created with the "
                "expected tag/title.\n"
                f"Observed release: {release}",
            )

        self.service.upload_release_asset(
            release_id=release.id,
            asset_name=self.config.foreign_asset_name,
            content_type="application/zip",
            content=_foreign_asset_bytes(),
        )

        matched_asset, observed_release = poll_until(
            probe=lambda: self.service.fetch_release_by_tag(self.release_tag),
            is_satisfied=lambda value: value is not None
            and value.name == self.config.expected_release_title
            and self.config.foreign_asset_name in [asset.name for asset in value.assets],
            timeout_seconds=self.config.release_poll_timeout_seconds,
            interval_seconds=self.config.release_poll_interval_seconds,
        )
        if not matched_asset or observed_release is None:
            raise AssertionError(
                "Precondition failed: the GitHub release fixture never exposed the seeded "
                f"{self.config.foreign_asset_name} asset.\n"
                f"Observed release: {observed_release}",
            )

    def _seed_local_repository(self, repository_path: Path) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / self.config.project_key / "project.json",
            json.dumps(
                {
                    "key": self.config.project_key,
                    "name": self.config.project_name,
                    "attachmentStorage": {
                        "mode": "github-releases",
                        "githubReleases": {
                            "tagPrefix": self.release_tag_prefix,
                        },
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write_file(
            repository_path / self.config.project_key / "config" / "statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / self.config.project_key / "config" / "issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / self.config.project_key / "config" / "fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / self.config.project_key / self.config.issue_key / "main.md",
            (
                "---\n"
                f"key: {self.config.issue_key}\n"
                f"project: {self.config.project_key}\n"
                "issueType: story\n"
                "status: todo\n"
                f'summary: "{self.config.issue_summary}"\n'
                "priority: medium\n"
                "assignee: tester\n"
                "reporter: tester\n"
                "updated: 2026-05-13T00:00:00Z\n"
                "---\n\n"
                "# Description\n\n"
                f"{TICKET_KEY} local foreign asset conflict fixture.\n"
            ),
        )
        self._write_file(
            repository_path / self.config.manifest_path,
            self.config.seeded_manifest_text,
        )
        self._write_binary_file(
            repository_path / self.config.source_file_name,
            self.config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-552 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts552@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", self.remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-552 fixture")

    def _capture_local_state(self, repository_path: Path) -> dict[str, object]:
        issue_main_path = (
            repository_path / self.config.project_key / self.config.issue_key / "main.md"
        )
        manifest_path = repository_path / self.config.manifest_path
        attachments_directory = (
            repository_path / self.config.project_key / self.config.issue_key / "attachments"
        )
        source_file_path = repository_path / self.config.source_file_name
        stored_files = sorted(
            str(path.relative_to(repository_path))
            for path in attachments_directory.rglob("*")
            if path.is_file()
        ) if attachments_directory.is_dir() else []
        remote_names = [
            line.strip()
            for line in self._git_output(repository_path, "remote").splitlines()
            if line.strip()
        ]
        remote_origin_url = (
            self._git_output(repository_path, "remote", "get-url", "origin").strip()
            if "origin" in remote_names
            else None
        )
        return {
            "issue_main_exists": issue_main_path.is_file(),
            "manifest_exists": manifest_path.is_file(),
            "manifest_text": (
                manifest_path.read_text(encoding="utf-8")
                if manifest_path.is_file()
                else None
            ),
            "attachments_directory_exists": attachments_directory.is_dir(),
            "stored_files": stored_files,
            "source_file_exists": source_file_path.is_file(),
            "git_status_lines": [
                line
                for line in self._git_output(repository_path, "status", "--short").splitlines()
                if line.strip()
            ],
            "remote_names": remote_names,
            "remote_origin_url": remote_origin_url,
        }

    def _observe_release_state(self) -> dict[str, object]:
        matched, release = poll_until(
            probe=lambda: self.service.fetch_release_by_tag(self.release_tag),
            is_satisfied=lambda value: value is not None,
            timeout_seconds=self.config.release_poll_timeout_seconds,
            interval_seconds=self.config.release_poll_interval_seconds,
        )
        if not matched or release is None:
            raise AssertionError(
                f"Step 4 failed: the release {self.release_tag} was not observable.",
            )
        return {
            "release_tag": release.tag_name,
            "release_title": release.name,
            "release_asset_names": [asset.name for asset in release.assets],
        }

    def _observe_gh_release_view(self) -> dict[str, object]:
        matched, observation = poll_until(
            probe=self._gh_release_view_once,
            is_satisfied=lambda value: value.get("exit_code") == 0,
            timeout_seconds=self.config.gh_poll_timeout_seconds,
            interval_seconds=self.config.gh_poll_interval_seconds,
        )
        if not matched:
            raise AssertionError(
                "Step 4 failed: `gh release view` did not become available for the seeded "
                "release fixture.\n"
                f"Observed output: {observation}",
            )
        return observation

    def _gh_release_view_once(self) -> dict[str, object]:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env["GH_TOKEN"] = self.service.token or ""
        env["GITHUB_TOKEN"] = self.service.token or ""
        completed = subprocess.run(
            (
                "gh",
                "release",
                "view",
                self.release_tag,
                "--repo",
                self.config.repository,
                "--json",
                "assets,name,tagName",
            ),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = _parse_json(completed.stdout)
        assets = payload.get("assets") if isinstance(payload, dict) else None
        asset_names = [
            str(asset.get("name", ""))
            for asset in assets
            if isinstance(asset, dict) and str(asset.get("name", "")).strip()
        ] if isinstance(assets, list) else []
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "payload": payload,
            "asset_names": asset_names,
        }

    def _run_ticket_command(
        self,
        *,
        repository_path: Path,
        executable_path: Path,
    ) -> dict[str, object]:
        executed_command = (str(executable_path), *self.config.requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        env["TRACKSTATE_TOKEN"] = self.service.token or ""
        sandbox_home = repository_path / ".ts552-home"
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
        payload = _parse_json(completed.stdout)
        error = payload.get("error") if isinstance(payload, dict) else None
        details = error.get("details") if isinstance(error, dict) else None
        return {
            "executed_command": " ".join(executed_command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "payload": payload,
            "observed_error_code": error.get("code") if isinstance(error, dict) else None,
            "observed_error_category": (
                error.get("category") if isinstance(error, dict) else None
            ),
            "observed_error_message": (
                error.get("message") if isinstance(error, dict) else None
            ),
            "observed_error_details": details if isinstance(details, dict) else None,
            "observed_error_reason": (
                details.get("reason") if isinstance(details, dict) else None
            ),
            "visible_output": _visible_output(
                payload=payload,
                stdout=completed.stdout,
                stderr=completed.stderr,
            ),
        }

    def _assert_fixture_state(
        self,
        *,
        initial_state: dict[str, object],
        fixture_state: dict[str, object],
        gh_view: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.get("issue_main_exists"):
            failures.append(
                "Precondition failed: the disposable local repository did not contain "
                f"{self.config.issue_key}/main.md.\n"
                f"Observed state: {json.dumps(initial_state, indent=2, sort_keys=True)}",
            )
        if not initial_state.get("source_file_exists"):
            failures.append(
                "Precondition failed: the disposable local repository did not contain "
                f"{self.config.source_file_name}.\n"
                f"Observed state: {json.dumps(initial_state, indent=2, sort_keys=True)}",
            )
        if initial_state.get("manifest_text") != self.config.seeded_manifest_text:
            failures.append(
                "Precondition failed: local attachments.json was not seeded with the expected "
                "empty manifest.\n"
                f"Expected:\n{self.config.seeded_manifest_text}\n"
                f"Observed:\n{initial_state.get('manifest_text')}",
            )
        if initial_state.get("stored_files"):
            failures.append(
                "Precondition failed: the disposable local repository already contained "
                "attachment files before the upload attempt.\n"
                f"Observed stored files: {initial_state.get('stored_files')}",
            )
        if initial_state.get("remote_origin_url") != self.remote_origin_url:
            failures.append(
                "Precondition failed: the disposable local repository origin did not point "
                "at the live setup repository.\n"
                f"Expected origin: {self.remote_origin_url}\n"
                f"Observed origin: {initial_state.get('remote_origin_url')}",
            )
        if fixture_state.get("release_title") != self.config.expected_release_title:
            failures.append(
                "Precondition failed: the seeded release title did not match the issue "
                "contract.\n"
                f"Expected title: {self.config.expected_release_title}\n"
                f"Observed state: {json.dumps(fixture_state, indent=2, sort_keys=True)}",
            )
        asset_names = fixture_state.get("release_asset_names")
        if asset_names != [self.config.foreign_asset_name]:
            failures.append(
                "Precondition failed: the seeded release did not contain exactly the "
                "expected foreign asset.\n"
                f"Observed state: {json.dumps(fixture_state, indent=2, sort_keys=True)}",
            )
        if gh_view.get("asset_names") != [self.config.foreign_asset_name]:
            failures.append(
                "Precondition failed: `gh release view` did not expose exactly the seeded "
                "foreign asset before the upload attempt.\n"
                f"Observed gh view: {json.dumps(gh_view, indent=2, sort_keys=True)}",
            )
        return failures

    def _assert_runtime_expectations(self, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        exit_code = result.get("exit_code")
        payload = result.get("payload")
        visible_output = _as_text(result.get("visible_output"))
        if exit_code != self.config.expected_exit_code:
            failures.append(
                "Step 2 failed: the exact local upload command did not exit with the "
                "expected repository conflict code.\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {exit_code}\n"
                f"{_observed_command_output(result)}"
            )
            return failures

        required_fragments = (self.release_tag, *self.config.required_reason_fragments)
        lowered_output = visible_output.lower()
        missing_fragments = [
            fragment for fragment in required_fragments if fragment.lower() not in lowered_output
        ]
        if missing_fragments:
            failures.append(
                "Step 2 failed: the visible CLI output did not expose the expected foreign "
                "asset conflict details.\n"
                f"Missing visible fragments: {missing_fragments}\n"
                f"Visible output:\n{visible_output}\n"
                f"{_observed_command_output(result)}"
            )

        if isinstance(payload, dict):
            if payload.get("ok") is not False:
                failures.append(
                    "Expected result failed: the local upload payload did not stay in an "
                    "error state.\n"
                    f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                )
            error = payload.get("error")
            if not isinstance(error, dict):
                failures.append(
                    "Step 2 failed: the JSON payload did not include an `error` object.\n"
                    f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                )
            else:
                if error.get("code") != self.config.expected_error_code:
                    failures.append(
                        "Step 2 failed: the JSON payload did not expose the expected error "
                        "code.\n"
                        f"Expected code: {self.config.expected_error_code}\n"
                        f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                    )
                if error.get("category") != self.config.expected_error_category:
                    failures.append(
                        "Step 2 failed: the JSON payload did not expose the expected error "
                        "category.\n"
                        f"Expected category: {self.config.expected_error_category}\n"
                        f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                    )
        return failures

    def _assert_local_state(self, final_state: dict[str, object]) -> list[str]:
        failures: list[str] = []
        if final_state.get("manifest_text") != self.config.seeded_manifest_text:
            failures.append(
                "Step 3 failed: local attachments.json changed even though the upload "
                "should have been blocked by the foreign asset conflict.\n"
                f"Expected manifest:\n{self.config.seeded_manifest_text}\n"
                f"Observed manifest:\n{final_state.get('manifest_text')}",
            )
        if final_state.get("stored_files"):
            failures.append(
                "Step 3 failed: the local repository wrote attachment files even though the "
                "upload should have failed before any local attachment mutation.\n"
                f"Observed stored files: {final_state.get('stored_files')}",
            )
        if final_state.get("git_status_lines"):
            failures.append(
                "Step 3 failed: the local repository was left dirty after the failed upload.\n"
                f"Observed git status: {final_state.get('git_status_lines')}",
            )
        return failures

    def _assert_remote_state(
        self,
        *,
        remote_state: dict[str, object],
        gh_view: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        asset_names = remote_state.get("release_asset_names")
        if asset_names != [self.config.foreign_asset_name]:
            failures.append(
                "Step 4 failed: the live release did not preserve exactly the seeded foreign "
                "asset after the failed upload attempt.\n"
                f"Observed state: {json.dumps(remote_state, indent=2, sort_keys=True)}",
            )
        if gh_view.get("asset_names") != [self.config.foreign_asset_name]:
            failures.append(
                "Human-style verification failed: `gh release view` did not show exactly the "
                "expected foreign asset after the failed upload.\n"
                f"Observed gh view: {json.dumps(gh_view, indent=2, sort_keys=True)}",
            )
        return failures

    def _cleanup_release(self) -> dict[str, object]:
        release = self.service.fetch_release_by_tag(self.release_tag)
        if release is None:
            return {
                "status": "already-absent",
                "release_tag": self.release_tag,
            }
        deleted_assets: list[str] = []
        for asset in release.assets:
            self.service.delete_release_asset(asset.id)
            deleted_assets.append(asset.name)
        self.service.delete_release(release.id)
        matched, _ = poll_until(
            probe=lambda: self.service.fetch_release_by_tag(self.release_tag),
            is_satisfied=lambda value: value is None,
            timeout_seconds=self.config.release_poll_timeout_seconds,
            interval_seconds=self.config.release_poll_interval_seconds,
        )
        if not matched:
            raise AssertionError(
                f"Cleanup failed: the seeded release {self.release_tag} still exists.",
            )
        return {
            "status": "deleted-seeded-release",
            "release_tag": self.release_tag,
            "deleted_assets": deleted_assets,
        }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts552LocalForeignAssetConflictScenario()

    result: dict[str, object] = {}
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        if not result:
            result = {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
            }
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


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
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅' if passed else '❌'} {status}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {{{{{_as_text(result.get('ticket_command'))}}}}} from a disposable "
            f"local TrackState repository configured for "
            f"{{{{attachmentStorage.mode = github-releases}}}} with Git origin "
            f"{{{{{_as_text(result.get('remote_origin_url'))}}}}}."
        ),
        (
            f"* Seeded GitHub Release {{{{{_as_text(result.get('release_tag'))}}}}} titled "
            f"{{{{{_as_text(result.get('release_title'))}}}}} with the foreign asset "
            f"{{{{{_as_text(result.get('foreign_asset_name'))}}}}} while local "
            f"{{{{{_as_text(result.get('manifest_path'))}}}}} stayed empty."
        ),
        (
            "* Verified both the visible CLI output and the post-run release state via "
            "{{gh release view}}."
        ),
        "",
        "h4. Observed result",
        (
            "* The observed behavior matched the expected result."
            if passed
            else "* The observed behavior did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{_as_text(result.get('repository'))}}}}} @ "
            f"{{{{{_as_text(result.get('repository_ref'))}}}}}, OS "
            f"{{{{{platform.system()}}}}}, runtime {{Dart CLI compiled locally}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local "
            f"TrackState repository configured for `attachmentStorage.mode = github-releases` "
            f"with Git origin `{_as_text(result.get('remote_origin_url'))}`."
        ),
        (
            f"- Seeded GitHub Release `{_as_text(result.get('release_tag'))}` titled "
            f"`{_as_text(result.get('release_title'))}` with the foreign asset "
            f"`{_as_text(result.get('foreign_asset_name'))}` while local "
            f"`{_as_text(result.get('manifest_path'))}` stayed empty."
        ),
        "- Verified both the visible CLI output and the post-run release state via `gh release view`.",
        "",
        "### Observed result",
        (
            "- The observed behavior matched the expected result."
            if passed
            else "- The observed behavior did not match the expected result."
        ),
        (
            f"- Environment: repository `{_as_text(result.get('repository'))}` @ "
            f"`{_as_text(result.get('repository_ref'))}`, OS `{platform.system()}`, runtime "
            "`Dart CLI compiled locally`."
        ),
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Ran `{_as_text(result.get('ticket_command'))}` from a disposable local "
            f"repository backed by GitHub Releases after seeding release "
            f"`{_as_text(result.get('release_tag'))}` with `{_as_text(result.get('foreign_asset_name'))}`."
        ),
        "",
        "## Observed",
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Release tag: `{_as_text(result.get('release_tag'))}`",
        f"- Cleanup: `{json.dumps(result.get('cleanup', {}), sort_keys=True)}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    visible_output = _as_text(result.get("visible_output"))
    gh_stdout = _as_text(_as_dict(result.get("gh_release_view")).get("stdout"))
    return "\n".join(
        [
            "# TS-552 - Local release-backed upload does not preserve the expected foreign-asset conflict behavior",
            "",
            "## Steps to reproduce",
            (
                "1. Execute `trackstate attachment upload --issue TS-123 --file report.pdf "
                "--target local` from a local TrackState repository configured with "
                "`attachmentStorage.mode = github-releases`."
            ),
            (
                f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} "
                "Precondition: the disposable local repository used Git origin "
                f"`{_as_text(result.get('remote_origin_url'))}`, local "
                f"`{_as_text(result.get('manifest_path'))}` contained `[]`, and release "
                f"`{_as_text(result.get('release_tag'))}` already contained "
                f"`{_as_text(result.get('foreign_asset_name'))}`."
            ),
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"Command outcome: {_step_observation(result, 2) or visible_output or _as_text(result.get('error'))}"
            ),
            "2. Inspect the command output.",
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"Observed visible output:\n{visible_output or '<empty>'}"
            ),
            "3. Verify the release and local manifest state after the failed attempt.",
            (
                f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
                f"Local state: {_step_observation(result, 3)}"
            ),
            (
                f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} "
                f"Release state: {_step_observation(result, 4)}"
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            _as_text(result.get("traceback")) or _as_text(result.get("error")),
            "```",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: the local upload should fail with a visible foreign-asset "
                f"conflict that names `{_as_text(result.get('foreign_asset_name'))}`, requires "
                "manual cleanup, leaves local `attachments.json` unchanged, and keeps the "
                "release limited to the foreign asset."
            ),
            (
                "- Actual: "
                + (_as_text(result.get("error")) or "Unknown failure")
            ),
            "",
            "## Environment details",
            f"- Repository: `{_as_text(result.get('repository'))}`",
            f"- Branch: `{_as_text(result.get('repository_ref'))}`",
            f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
            f"- Release tag: `{_as_text(result.get('release_tag'))}`",
            f"- Local repository path: `{_as_text(result.get('repository_path'))}`",
            f"- OS: `{platform.system()}`",
            f"- Command: `{_as_text(result.get('executed_command')) or _as_text(result.get('requested_command'))}`",
            "",
            "## Relevant logs",
            "### Visible CLI output",
            "```text",
            visible_output,
            "```",
            "### stdout",
            "```text",
            _as_text(result.get("stdout")),
            "```",
            "### stderr",
            "```text",
            _as_text(result.get("stderr")),
            "```",
            "### gh release view",
            "```text",
            gh_stdout,
            "```",
        ],
    ) + "\n"


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
        },
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


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for entry in sorted(
        result.get("steps", []),
        key=lambda item: item.get("step", 0),
    ):
        lines.append(
            f"{prefix} Step {entry.get('step')} — {str(entry.get('status', '')).upper()}: "
            f"{entry.get('action', '')}",
        )
        if jira:
            lines.append(f"*Observed:* {{noformat}}{entry.get('observed', '')}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{entry.get('observed', '')}`")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        lines.append(f"{prefix} {entry.get('check', '')}")
        if jira:
            lines.append(f"*Observed:* {{noformat}}{entry.get('observed', '')}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{entry.get('observed', '')}`")
    return lines


def _step_status(result: dict[str, object], step: int) -> str | None:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("status"))
    return None


def _step_observation(result: dict[str, object], step: int) -> str:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("observed", ""))
    return ""


def _foreign_asset_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.txt",
            "TS-552 foreign release asset that must remain outside attachments.json.\n",
        )
    return buffer.getvalue()


def _visible_output(
    *,
    payload: object | None,
    stdout: str,
    stderr: str,
) -> str:
    if isinstance(payload, dict):
        return json.dumps(payload, indent=2, sort_keys=True)
    stdout_text = stdout.strip()
    stderr_text = stderr.strip()
    if stdout_text and stderr_text:
        return f"{stdout_text}\n{stderr_text}"
    return stdout_text or stderr_text


def _observed_command_output(result: dict[str, object]) -> str:
    return (
        "stdout:\n"
        f"{_as_text(result.get('stdout'))}\n"
        "stderr:\n"
        f"{_as_text(result.get('stderr'))}"
    )


def _parse_json(text: str) -> object | None:
    payload = text.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _as_dict(value: object | None) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"runtime_inputs.{key} must be a string.")
    normalized = value.strip()
    return normalized or None


def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} runtime_inputs.{key} must be a non-empty string.")
    return value


def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{path} runtime_inputs.{key} must be an integer.")
    return value


def _require_string_list(
    payload: dict[str, Any],
    key: str,
    path: Path,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} runtime_inputs.{key} must be a non-empty list.")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{path} runtime_inputs.{key}[{index}] must be a non-empty string.",
            )
        items.append(item)
    return tuple(items)


if __name__ == "__main__":
    main()
