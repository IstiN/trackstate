from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import traceback
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (  # noqa: E402
    PythonTrackStateCliCompiledLocalFramework,
)

TICKET_KEY = "TS-590"
TICKET_SUMMARY = (
    "Reuse release with modified metadata normalizes the release body"
)
TEST_FILE_PATH = "testing/tests/TS-590/test_ts_590.py"
RUN_COMMAND = "python testing/tests/TS-590/test_ts_590.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


@dataclass(frozen=True)
class Ts590Config:
    ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    release_tag_prefix_base: str
    seeded_release_body: str
    expected_release_body: str
    attachment_media_type: str
    manifest_poll_timeout_seconds: int
    manifest_poll_interval_seconds: int
    release_poll_timeout_seconds: int
    release_poll_interval_seconds: int
    gh_poll_timeout_seconds: int
    gh_poll_interval_seconds: int
    repository: str
    branch: str

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def expected_release_title(self) -> str:
        return f"Attachments for {self.issue_key}"

    @property
    def issue_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}"

    @property
    def issue_main_path(self) -> str:
        return f"{self.issue_path}/main.md"

    @property
    def manifest_path(self) -> str:
        return f"{self.issue_path}/attachments.json"

    @property
    def expected_attachment_relative_path(self) -> str:
        return f"{self.issue_path}/attachments/{self.source_file_name}"

    @classmethod
    def from_file(cls, path: Path) -> "Ts590Config":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must deserialize to a mapping.")
        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(f"{path} runtime_inputs must deserialize to a mapping.")

        repository_service = LiveSetupRepositoryService()
        return cls(
            ticket_command=_required_str(runtime_inputs, "ticket_command", path),
            requested_command=_required_str_list(runtime_inputs, "requested_command", path),
            project_key=_required_str(runtime_inputs, "project_key", path),
            project_name=_required_str(runtime_inputs, "project_name", path),
            issue_key=_required_str(runtime_inputs, "issue_key", path),
            issue_summary=_required_str(runtime_inputs, "issue_summary", path),
            source_file_name=_required_str(runtime_inputs, "source_file_name", path),
            source_file_text=_required_str(runtime_inputs, "source_file_text", path),
            release_tag_prefix_base=_required_str(
                runtime_inputs,
                "release_tag_prefix_base",
                path,
            ),
            seeded_release_body=_required_str(runtime_inputs, "seeded_release_body", path),
            expected_release_body=_required_str(runtime_inputs, "expected_release_body", path),
            attachment_media_type=_required_str(runtime_inputs, "attachment_media_type", path),
            manifest_poll_timeout_seconds=_required_int(
                runtime_inputs,
                "manifest_poll_timeout_seconds",
                path,
            ),
            manifest_poll_interval_seconds=_required_int(
                runtime_inputs,
                "manifest_poll_interval_seconds",
                path,
            ),
            release_poll_timeout_seconds=_required_int(
                runtime_inputs,
                "release_poll_timeout_seconds",
                path,
            ),
            release_poll_interval_seconds=_required_int(
                runtime_inputs,
                "release_poll_interval_seconds",
                path,
            ),
            gh_poll_timeout_seconds=_required_int(
                runtime_inputs,
                "gh_poll_timeout_seconds",
                path,
            ),
            gh_poll_interval_seconds=_required_int(
                runtime_inputs,
                "gh_poll_interval_seconds",
                path,
            ),
            repository=repository_service.repository,
            branch=repository_service.ref,
        )


@dataclass(frozen=True)
class SeededRelease:
    id: int
    tag_name: str
    name: str
    body: str
    draft: bool
    prerelease: bool


class Ts590Runner(PythonTrackStateCliCompiledLocalFramework):
    def __init__(self, repository_root: Path, service: LiveSetupRepositoryService) -> None:
        super().__init__(repository_root)
        self._service = service

    def execute(self, config: Ts590Config) -> dict[str, object]:
        if not self._service.token:
            raise RuntimeError(
                "TS-590 requires GH_TOKEN or GITHUB_TOKEN to seed and verify live GitHub Releases.",
            )

        release_tag_prefix = f"{config.release_tag_prefix_base}{uuid.uuid4().hex[:8]}-"
        release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._service.repository}.git"

        with tempfile.TemporaryDirectory(prefix="trackstate-ts-590-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            seeded_release = self._service.create_release(
                tag_name=release_tag,
                name=config.expected_release_title,
                body=config.seeded_release_body,
                target_commitish=self._service.ref,
                draft=True,
                prerelease=False,
            )
            try:
                with tempfile.TemporaryDirectory(prefix="trackstate-ts-590-repo-") as temp_dir:
                    repository_path = Path(temp_dir)
                    self._seed_local_repository(
                        repository_path=repository_path,
                        config=config,
                        remote_origin_url=remote_origin_url,
                        release_tag_prefix=release_tag_prefix,
                    )
                    initial_state = self._capture_local_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    observation = self._run_upload_command(
                        repository_path=repository_path,
                        executable_path=executable_path,
                        requested_command=config.requested_command,
                    )
                    final_state = self._capture_local_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    manifest_observation = self._poll_manifest(
                        repository_path=repository_path,
                        config=config,
                        release_tag=release_tag,
                    )
                    release_observation = self._poll_release(
                        config=config,
                        seeded_release_id=seeded_release.id,
                        release_tag=release_tag,
                    )
                    gh_view = self._poll_gh_view(
                        config=config,
                        release_tag=release_tag,
                    )
            finally:
                cleanup = self._cleanup_release(release_tag)

        return {
            "release_tag_prefix": release_tag_prefix,
            "release_tag": release_tag,
            "remote_origin_url": remote_origin_url,
            "compiled_binary_path": str(executable_path),
            "seeded_release": serialize(
                SeededRelease(
                    id=seeded_release.id,
                    tag_name=seeded_release.tag_name,
                    name=seeded_release.name,
                    body=seeded_release.body,
                    draft=seeded_release.draft,
                    prerelease=seeded_release.prerelease,
                ),
            ),
            "initial_state": initial_state,
            "observation": observation,
            "final_state": final_state,
            "manifest_observation": manifest_observation,
            "release_observation": release_observation,
            "gh_release_view": gh_view,
            "cleanup": cleanup,
        }

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: Ts590Config,
        remote_origin_url: str,
        release_tag_prefix: str,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            json.dumps(
                {
                    "key": config.project_key,
                    "name": config.project_name,
                    "attachmentStorage": {
                        "mode": "github-releases",
                        "githubReleases": {
                            "tagPrefix": release_tag_prefix,
                        },
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self._write_file(
            repository_path / config.project_key / "config" / "statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.issue_main_path,
            (
                "---\n"
                f"key: {config.issue_key}\n"
                f"project: {config.project_key}\n"
                "issueType: story\n"
                "status: todo\n"
                f"summary: {config.issue_summary}\n"
                "priority: medium\n"
                "assignee: tester\n"
                "reporter: tester\n"
                "updated: 2026-05-13T00:00:00Z\n"
                "---\n\n"
                "# Description\n\n"
                "TS-590 release body normalization fixture.\n"
            ),
        )
        self._write_file(repository_path / config.manifest_path, "[]\n")
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-590 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts590@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        git_env = {
            "GIT_AUTHOR_NAME": "TS-590 Tester",
            "GIT_AUTHOR_EMAIL": "ts590@example.com",
            "GIT_AUTHOR_DATE": "2026-05-13T00:00:00Z",
            "GIT_COMMITTER_NAME": "TS-590 Tester",
            "GIT_COMMITTER_EMAIL": "ts590@example.com",
            "GIT_COMMITTER_DATE": "2026-05-13T00:00:00Z",
        }
        self._git(repository_path, "add", ".", env=git_env)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-590 release body normalization fixture",
            env=git_env,
        )

    def _capture_local_state(
        self,
        *,
        repository_path: Path,
        config: Ts590Config,
    ) -> dict[str, object]:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path)
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return {
            "issue_main_exists": (repository_path / config.issue_main_path).is_file(),
            "source_file_exists": (repository_path / config.source_file_name).is_file(),
            "manifest_exists": manifest_path.is_file(),
            "manifest_text": manifest_text,
            "git_status_lines": tuple(
                line
                for line in self._git_output(repository_path, "status", "--short").splitlines()
                if line.strip()
            ),
            "remote_origin_url": remote_origin_url or None,
        }

    def _run_upload_command(
        self,
        *,
        repository_path: Path,
        executable_path: Path,
        requested_command: tuple[str, ...],
    ) -> dict[str, object]:
        executed_command = (str(executable_path), *requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        for variable in ("GH_TOKEN", "GITHUB_TOKEN", "TRACKSTATE_TOKEN"):
            env.pop(variable, None)
        env["TRACKSTATE_TOKEN"] = self._service.token or ""
        env["GH_TOKEN"] = self._service.token or ""
        env["GITHUB_TOKEN"] = self._service.token or ""
        sandbox_home = repository_path / ".ts590-home"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(sandbox_home)
        env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
        env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
        env["GIT_TERMINAL_PROMPT"] = "0"
        result = self._run(executed_command, cwd=repository_path, env=env)
        return {
            "requested_command": requested_command,
            "executed_command": executed_command,
            "repository_path": str(repository_path),
            "result": serialize(result),
        }

    def _poll_manifest(
        self,
        *,
        repository_path: Path,
        config: Ts590Config,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_manifest_state(
                repository_path=repository_path,
                config=config,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.manifest_poll_timeout_seconds,
            interval_seconds=config.manifest_poll_interval_seconds,
        )
        return observation

    def _observe_manifest_state(
        self,
        *,
        repository_path: Path,
        config: Ts590Config,
        release_tag: str,
    ) -> dict[str, object]:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path) or ""
        matching_entries: list[dict[str, object]] = []
        try:
            payload = json.loads(manifest_text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            matching_entries = [
                entry
                for entry in payload
                if isinstance(entry, dict) and entry.get("name") == config.source_file_name
            ]
        matching_entry = matching_entries[0] if len(matching_entries) == 1 else None
        return {
            "manifest_text": manifest_text,
            "matching_entries": matching_entries,
            "matching_entry": matching_entry,
            "entry_count": len(matching_entries),
            "matches_expected": matching_entry is not None
            and str(matching_entry.get("id", "")) == config.expected_attachment_relative_path
            and str(matching_entry.get("storagePath", ""))
            == config.expected_attachment_relative_path
            and str(matching_entry.get("storageBackend", "")) == "github-releases"
            and str(matching_entry.get("githubReleaseTag", "")) == release_tag
            and str(matching_entry.get("githubReleaseAssetName", "")) == config.source_file_name
            and str(matching_entry.get("revisionOrOid", "")).strip() != "",
        }

    def _poll_release(
        self,
        *,
        config: Ts590Config,
        seeded_release_id: int,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_release_state(
                config=config,
                seeded_release_id=seeded_release_id,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        return observation

    def _observe_release_state(
        self,
        *,
        config: Ts590Config,
        seeded_release_id: int,
        release_tag: str,
    ) -> dict[str, object]:
        release = self._service.fetch_release_by_tag_any_state(release_tag)
        asset_names = tuple(asset.name for asset in release.assets) if release else ()
        asset_ids = tuple(asset.id for asset in release.assets) if release else ()
        return {
            "release_present": release is not None,
            "release_id": release.id if release else None,
            "release_tag": release.tag_name if release else None,
            "release_name": release.name if release else None,
            "release_body": release.body if release else None,
            "release_draft": release.draft if release else None,
            "release_prerelease": release.prerelease if release else None,
            "asset_names": asset_names,
            "asset_ids": asset_ids,
            "matches_expected": release is not None
            and release.id == seeded_release_id
            and release.tag_name == release_tag
            and release.name == config.expected_release_title
            and release.body == config.expected_release_body
            and release.draft is True
            and release.prerelease is False
            and asset_names == (config.source_file_name,),
        }

    def _poll_gh_view(
        self,
        *,
        config: Ts590Config,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_gh_release_view(
                config=config,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.gh_poll_timeout_seconds,
            interval_seconds=config.gh_poll_interval_seconds,
        )
        return observation

    def _observe_gh_release_view(
        self,
        *,
        config: Ts590Config,
        release_tag: str,
    ) -> dict[str, object]:
        env = os.environ.copy()
        env["GH_TOKEN"] = self._service.token or ""
        env["GITHUB_TOKEN"] = self._service.token or ""
        completed = subprocess.run(
            (
                "gh",
                "release",
                "view",
                release_tag,
                "--repo",
                self._service.repository,
                "--json",
                "tagName,name,isDraft,body,assets",
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        json_payload: dict[str, object] | None = None
        try:
            raw_payload = json.loads(completed.stdout) if completed.stdout.strip() else None
        except json.JSONDecodeError:
            raw_payload = None
        if isinstance(raw_payload, dict):
            json_payload = raw_payload
        assets = json_payload.get("assets") if isinstance(json_payload, dict) else None
        asset_names = tuple(
            str(asset.get("name", "")).strip()
            for asset in assets
            if isinstance(asset, dict) and str(asset.get("name", "")).strip()
        ) if isinstance(assets, list) else ()
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "json_payload": json_payload,
            "asset_names": asset_names,
            "matches_expected": completed.returncode == 0
            and isinstance(json_payload, dict)
            and str(json_payload.get("tagName", "")) == release_tag
            and str(json_payload.get("name", "")) == config.expected_release_title
            and json_payload.get("isDraft") is True
            and str(json_payload.get("body", "")) == config.expected_release_body
            and asset_names == (config.source_file_name,),
        }

    def _cleanup_release(self, release_tag: str) -> dict[str, object]:
        deleted_release_ids: list[int] = []
        deleted_asset_ids: list[int] = []
        releases = self._service.fetch_releases_by_tag_any_state(release_tag)
        for release in releases:
            for asset in release.assets:
                self._service.delete_release_asset(asset.id)
                deleted_asset_ids.append(asset.id)
            self._service.delete_release(release.id)
            deleted_release_ids.append(release.id)
        for ref in self._service.list_matching_tag_refs(release_tag):
            if ref.endswith(f"/{release_tag}"):
                self._service.delete_tag_ref(release_tag)
                break
        _, remaining = poll_until(
            probe=lambda: {
                "releases": serialize(self._service.fetch_releases_by_tag_any_state(release_tag)),
                "tag_refs": self._service.list_matching_tag_refs(release_tag),
            },
            is_satisfied=lambda value: len(value["releases"]) == 0 and len(value["tag_refs"]) == 0,
            timeout_seconds=120,
            interval_seconds=5,
        )
        return {
            "status": "deleted"
            if len(remaining["releases"]) == 0 and len(remaining["tag_refs"]) == 0
            else "failed",
            "release_tag": release_tag,
            "deleted_release_ids": tuple(deleted_release_ids),
            "deleted_asset_ids": tuple(deleted_asset_ids),
            "remaining": remaining,
        }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = Ts590Config.from_file(REPO_ROOT / "testing/tests/TS-590/config.yaml")
    service = LiveSetupRepositoryService()
    runner = Ts590Runner(REPO_ROOT, service)

    try:
        execution = runner.execute(config)
        result = _build_result(config=config, execution=execution)
        failures = _validate_result(config=config, result=result)
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            },
        )
        _write_failure_outputs(failure_result)
        raise


def _build_result(*, config: Ts590Config, execution: dict[str, object]) -> dict[str, object]:
    observation = execution["observation"]
    assert isinstance(observation, dict)
    result_payload = observation.get("result")
    result_data = result_payload if isinstance(result_payload, dict) else {}
    payload = result_data.get("json_payload")
    payload_dict = payload if isinstance(payload, dict) else None
    payload_data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
    payload_attachment = payload_data.get("attachment") if isinstance(payload_data, dict) else None
    return {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "repository": config.repository,
        "repository_ref": config.branch,
        "project_key": config.project_key,
        "project_name": config.project_name,
        "issue_key": config.issue_key,
        "issue_summary": config.issue_summary,
        "ticket_command": config.ticket_command,
        "requested_command": " ".join(config.requested_command),
        "executed_command": " ".join(observation.get("executed_command", ())),
        "compiled_binary_path": execution.get("compiled_binary_path"),
        "repository_path": observation.get("repository_path"),
        "source_file_name": config.source_file_name,
        "source_file_text": config.source_file_text,
        "expected_release_title": config.expected_release_title,
        "expected_release_body": config.expected_release_body,
        "seeded_release_body": config.seeded_release_body,
        "expected_attachment_relative_path": config.expected_attachment_relative_path,
        "release_tag": execution.get("release_tag"),
        "release_tag_prefix": execution.get("release_tag_prefix"),
        "remote_origin_url": execution.get("remote_origin_url"),
        "seeded_release": execution.get("seeded_release"),
        "initial_state": execution.get("initial_state"),
        "final_state": execution.get("final_state"),
        "manifest_state": execution.get("manifest_observation"),
        "release_state": execution.get("release_observation"),
        "gh_release_view": execution.get("gh_release_view"),
        "cleanup": execution.get("cleanup"),
        "payload": payload_dict,
        "payload_data": payload_data if isinstance(payload_data, dict) else None,
        "payload_attachment": payload_attachment if isinstance(payload_attachment, dict) else None,
        "stdout": str(result_data.get("stdout", "")),
        "stderr": str(result_data.get("stderr", "")),
        "exit_code": result_data.get("exit_code"),
        "visible_output": _visible_output(
            payload_dict,
            stdout=str(result_data.get("stdout", "")),
            stderr=str(result_data.get("stderr", "")),
        ),
        "steps": [],
        "human_verification": [],
    }


def _validate_result(*, config: Ts590Config, result: dict[str, object]) -> list[str]:
    failures: list[str] = []
    seeded_release = result.get("seeded_release")
    initial_state = result.get("initial_state")
    payload = result.get("payload")
    payload_attachment = result.get("payload_attachment")
    manifest_state = result.get("manifest_state")
    release_state = result.get("release_state")
    gh_release_view = result.get("gh_release_view")

    if not isinstance(seeded_release, dict):
        failures.append("Precondition failed: the seeded release details were not captured.")
        return failures
    if seeded_release.get("body") != config.seeded_release_body:
        failures.append(
            "Precondition failed: the seeded release did not start with the manual custom body.\n"
            f"Observed seeded release: {json.dumps(seeded_release, indent=2, sort_keys=True)}"
        )
    if not isinstance(initial_state, dict) or initial_state.get("remote_origin_url") != result.get(
        "remote_origin_url",
    ):
        failures.append(
            "Precondition failed: the disposable local repository was not seeded with the "
            "expected remote origin.\n"
            f"Observed initial state: {json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if isinstance(initial_state, dict) and initial_state.get("manifest_text") != "[]\n":
        failures.append(
            "Precondition failed: the local attachments.json manifest was not empty before upload.\n"
            f"Observed initial state: {json.dumps(initial_state, indent=2, sort_keys=True)}"
        )
    if failures:
        return failures

    record_step(
        result,
        step=1,
        status="passed",
        action=(
            "Seed a matching draft GitHub Release with the correct tag/title and a custom body, "
            "then prepare the disposable local repository."
        ),
        observed=(
            f"release_id={seeded_release.get('id')}; release_tag={seeded_release.get('tag_name')}; "
            f"release_body={seeded_release.get('body')!r}; remote_origin_url={result.get('remote_origin_url')}"
        ),
    )

    if result.get("requested_command") != config.ticket_command:
        failures.append(
            "Step 2 failed: the test did not run the exact ticket command.\n"
            f"Expected: {config.ticket_command}\n"
            f"Observed: {result.get('requested_command')}"
        )
        return failures
    if result.get("exit_code") != 0:
        failures.append(
            "Step 2 failed: executing the exact local upload command did not succeed.\n"
            f"{_observed_command_output(as_text(result.get('stdout')), as_text(result.get('stderr')))}"
        )
        return failures
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        failures.append(
            "Step 2 failed: the CLI did not return a successful JSON envelope.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
        )
        return failures
    payload_data = payload.get("data")
    if not isinstance(payload_data, dict) or payload_data.get("command") != "attachment-upload":
        failures.append(
            "Step 2 failed: the success payload did not identify the attachment-upload command.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
        )
        return failures
    if payload_data.get("issue") != config.issue_key:
        failures.append(
            "Step 2 failed: the success payload did not preserve the requested issue key.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
        )
        return failures
    if not isinstance(payload_attachment, dict):
        failures.append(
            "Step 2 failed: the success payload did not include attachment metadata.\n"
            f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
        )
        return failures
    if payload_attachment.get("name") != config.source_file_name:
        failures.append(
            "Step 2 failed: the success payload did not preserve the uploaded filename.\n"
            f"Observed attachment:\n{json.dumps(payload_attachment, indent=2, sort_keys=True)}"
        )
        return failures

    record_step(
        result,
        step=2,
        status="passed",
        action=config.ticket_command,
        observed=(
            f"exit_code={result.get('exit_code')}; "
            f"attachment_issue={payload_data.get('issue')}; "
            f"attachment_name={payload_attachment.get('name')}; "
            f"attachment_revision_or_oid={payload_attachment.get('revisionOrOid')}"
        ),
    )
    record_human_verification(
        result,
        check=(
            "Verified from the CLI output that the exact local upload command completed "
            "successfully for the requested issue and file."
        ),
        observed=as_text(result.get("visible_output")) or "<empty>",
    )

    if not isinstance(manifest_state, dict) or manifest_state.get("matches_expected") is not True:
        failures.append(
            "Step 3 failed: local attachments.json did not converge to the expected release-backed entry.\n"
            f"Observed manifest state:\n{json.dumps(manifest_state, indent=2, sort_keys=True)}"
        )
        return failures

    record_step(
        result,
        step=3,
        status="passed",
        action="Inspect the local attachment metadata after upload.",
        observed=(
            f"matching_entry={json.dumps(manifest_state.get('matching_entry'), sort_keys=True)}"
        ),
    )

    if not isinstance(release_state, dict) or release_state.get("matches_expected") is not True:
        failures.append(
            "Step 4 failed: the live GitHub Release did not converge to the expected normalized metadata.\n"
            f"Observed release state:\n{json.dumps(release_state, indent=2, sort_keys=True)}"
        )
        return failures
    if release_state.get("release_id") != seeded_release.get("id"):
        failures.append(
            "Step 4 failed: the upload did not reuse the seeded release id.\n"
            f"Seeded release: {json.dumps(seeded_release, indent=2, sort_keys=True)}\n"
            f"Observed release: {json.dumps(release_state, indent=2, sort_keys=True)}"
        )
        return failures
    if release_state.get("release_body") != config.expected_release_body:
        failures.append(
            "Step 4 failed: the release body was not normalized to the standard machine-managed note.\n"
            f"Expected body: {config.expected_release_body!r}\n"
            f"Observed release: {json.dumps(release_state, indent=2, sort_keys=True)}"
        )
        return failures
    if not isinstance(gh_release_view, dict) or gh_release_view.get("matches_expected") is not True:
        failures.append(
            "Step 4 failed: `gh release view` did not expose the normalized body and uploaded asset.\n"
            f"Observed gh release view:\n{json.dumps(gh_release_view, indent=2, sort_keys=True)}"
        )
        return failures

    gh_payload = gh_release_view.get("json_payload")
    record_step(
        result,
        step=4,
        status="passed",
        action=(
            f"Inspect the GitHub Release metadata via REST API and `gh release view {result.get('release_tag')}`."
        ),
        observed=(
            f"release_id={release_state.get('release_id')}; "
            f"release_name={release_state.get('release_name')}; "
            f"release_body={release_state.get('release_body')!r}; "
            f"gh_body={as_text(gh_payload.get('body') if isinstance(gh_payload, dict) else '')!r}; "
            f"gh_assets={list(gh_release_view.get('asset_names', []))}"
        ),
    )
    record_human_verification(
        result,
        check=(
            "Verified as a user through `gh release view` that the reused draft release still "
            "showed the expected title, the uploaded `note.txt` asset, and the normalized "
            "machine-managed body text in the visible release output."
        ),
        observed=as_text(gh_release_view.get("stdout")).strip() or "<empty>",
    )
    return failures


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
    jira = _jira_comment(result, passed=True)
    markdown = _markdown_summary(result, passed=True)
    JIRA_COMMENT_PATH.write_text(jira, encoding="utf-8")
    PR_BODY_PATH.write_text(markdown, encoding="utf-8")
    RESPONSE_PATH.write_text(markdown, encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = as_text(result.get("error")) or "AssertionError: unknown failure"
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
        )
        + "\n",
        encoding="utf-8",
    )
    jira = _jira_comment(result, passed=False)
    markdown = _markdown_summary(result, passed=False)
    bug = _bug_description(result)
    JIRA_COMMENT_PATH.write_text(jira, encoding="utf-8")
    PR_BODY_PATH.write_text(markdown, encoding="utf-8")
    RESPONSE_PATH.write_text(markdown, encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(bug, encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    manifest_state = as_dict(result.get("manifest_state"))
    release_state = as_dict(result.get("release_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_view.get("json_payload"))
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {{{{{as_text(result.get('ticket_command'))}}}}} from a disposable local "
            f"TrackState repository configured with {{{{attachmentStorage.mode = github-releases}}}} "
            f"and Git origin {{{{{as_text(result.get('remote_origin_url'))}}}}}."
        ),
        (
            f"* Seeded a matching draft GitHub Release {{{{{as_text(result.get('release_tag'))}}}}} / "
            f"{{{{{as_text(result.get('expected_release_title'))}}}}} with custom body "
            f"{{{{{as_text(result.get('seeded_release_body'))}}}}} before upload."
        ),
        (
            "* Verified the local manifest, live GitHub Release metadata, and "
            "{{gh release view}} output after the upload."
        ),
        "",
        "h4. Human-style verification",
        (
            f"* Terminal outcome observed by a user: "
            f"{{{{{_jira_safe(compact_text(as_text(result.get('visible_output')) or '<empty>'))}}}}}"
        ),
        (
            f"* Release output observed by a user in {{gh release view}}: "
            f"{{{{{_jira_safe(compact_text(as_text(gh_view.get('stdout')) or '<empty>'))}}}}}"
        ),
        "",
        "h4. Result",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.append(
        (
            "* Observed normalized release body: "
            f"{{{{{_jira_safe(as_text(release_state.get('release_body')))}}}}}"
        )
    )
    lines.append(
        (
            "* Observed gh release view body: "
            f"{{{{{_jira_safe(as_text(gh_payload.get('body')))}}}}}"
        )
    )
    if passed:
        lines.append("* The observed behavior matched the expected result.")
    else:
        lines.extend(
            [
                f"* ❌ Failure: {{noformat}}{as_text(result.get('error'))}{{noformat}}",
                "* Observed manifest state:",
                "{code:json}",
                json.dumps(manifest_state, indent=2, sort_keys=True),
                "{code}",
                "* Observed release state:",
                "{code:json}",
                json.dumps(release_state, indent=2, sort_keys=True),
                "{code}",
            ],
        )
    lines.extend(
        [
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
        ],
    )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    release_state = as_dict(result.get("release_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_view.get("json_payload"))
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed `{as_text(result.get('ticket_command'))}` from a disposable local "
            "TrackState repository configured with `attachmentStorage.mode = github-releases` "
            f"and Git origin `{as_text(result.get('remote_origin_url'))}`."
        ),
        (
            f"- Seeded a matching draft GitHub Release `{as_text(result.get('release_tag'))}` / "
            f"`{as_text(result.get('expected_release_title'))}` with custom body "
            f"`{as_text(result.get('seeded_release_body'))}` before upload."
        ),
        "- Verified the local manifest, live GitHub Release metadata, and `gh release view` output after the upload.",
        "",
        "## Result",
    ]
    lines.extend(_markdown_step_lines(result.get("steps")))
    lines.extend(
        [
            (
                f"- Observed normalized release body: `{as_text(release_state.get('release_body'))}`"
            ),
            (
                f"- Observed `gh release view` body: `{as_text(gh_payload.get('body'))}`"
            ),
            (
                f"- Human-style verification: terminal output "
                f"`{compact_text(as_text(result.get('visible_output')) or '<empty>')}` and "
                f"`gh release view` output "
                f"`{compact_text(as_text(gh_view.get('stdout')) or '<empty>')}`."
            ),
        ],
    )
    if passed:
        lines.append("- The observed behavior matched the expected result.")
    else:
        lines.extend(
            [
                f"- Failure: `{as_text(result.get('error'))}`",
                "",
                "## Exact error",
                "```text",
                as_text(result.get("traceback")).rstrip(),
                "```",
            ],
        )
    lines.extend(["", "## How to run", "```bash", RUN_COMMAND, "```"])
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    release_state = as_dict(result.get("release_state"))
    manifest_state = as_dict(result.get("manifest_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    lines = [
        f"# {TICKET_KEY} - Release body is not normalized when reusing a matching release",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Create a disposable local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases` and Git `origin` set to "
            f"`{as_text(result.get('remote_origin_url'))}`."
        ),
        (
            "2. ✅ Pre-create a draft GitHub Release with matching tag/title and a custom body.\n"
            f"   - Release tag: `{as_text(result.get('release_tag'))}`\n"
            f"   - Release title: `{as_text(result.get('expected_release_title'))}`\n"
            f"   - Actual seeded body: `{as_text(result.get('seeded_release_body'))}`"
        ),
        (
            f"3. {'✅' if _step_status(result, 2) == 'passed' else '❌'} Execute the exact CLI command "
            f"`{as_text(result.get('ticket_command'))}`."
        ),
        f"   - Actual behavior: `{as_text(result.get('error')) or compact_text(as_text(result.get('visible_output')) or '<empty>')}`",
        f"   - Visible CLI output: `{compact_text(as_text(result.get('visible_output')) or '<empty>')}`",
        (
            f"4. {'✅' if _step_status(result, 3) == 'passed' else '❌'} Inspect the local "
            "`attachments.json` metadata."
        ),
        f"   - Actual manifest state:\n```json\n{json.dumps(manifest_state, indent=2, sort_keys=True)}\n```",
        (
            f"5. {'✅' if _step_status(result, 4) == 'passed' else '❌'} Inspect the GitHub Release via REST API or `gh release view`."
        ),
        f"   - Actual release state:\n```json\n{json.dumps(release_state, indent=2, sort_keys=True)}\n```",
        f"   - Actual `gh release view` state:\n```json\n{json.dumps(gh_view, indent=2, sort_keys=True)}\n```",
        "",
        "## Actual vs Expected",
        (
            f"- **Expected:** the upload should succeed, reuse release id "
            f"`{as_dict(result.get('seeded_release')).get('id')}`, keep title "
            f"`{as_text(result.get('expected_release_title'))}`, and normalize the body to "
            f"`{as_text(result.get('expected_release_body'))}` while exposing `note.txt` in the release."
        ),
        (
            f"- **Actual:** {as_text(result.get('error')) or 'The release metadata did not converge.'} "
            f"The observed body was `{as_text(release_state.get('release_body'))}` and the "
            f"`gh release view` body was `{as_text(as_dict(gh_view.get('json_payload')).get('body'))}`."
        ),
        "",
        "## Exact error / assertion",
        "```text",
        as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Command output",
        "```text",
        _observed_command_output(
            as_text(result.get("stdout")),
            as_text(result.get("stderr")),
        ).rstrip(),
        "```",
        "",
        "## Environment",
        f"- Repository: `{as_text(result.get('repository'))}`",
        f"- Branch/ref: `{as_text(result.get('repository_ref'))}`",
        f"- Remote origin URL: `{as_text(result.get('remote_origin_url'))}`",
        f"- Release tag: `{as_text(result.get('release_tag'))}`",
        f"- Local runtime: local CLI upload through disposable git repository",
        f"- OS: `{os.uname().sysname}`",
        "",
        "## Logs",
        "```json",
        json.dumps(
            {
                "seeded_release": result.get("seeded_release"),
                "manifest_state": manifest_state,
                "release_state": release_state,
                "gh_release_view": gh_view,
                "cleanup": result.get("cleanup"),
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
    ]
    return "\n".join(lines) + "\n"


def record_step(
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


def record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, CliCommandResult):
        return {
            "command": value.command,
            "exit_code": value.exit_code,
            "stdout": value.stdout,
            "stderr": value.stderr,
            "json_payload": value.json_payload,
        }
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def compact_text(value: str) -> str:
    return " ".join(value.split())


def _visible_output(payload: object, *, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            if isinstance(details, dict):
                reason = str(details.get("reason", "")).strip()
                if reason:
                    fragments.append(reason)
            message = str(error.get("message", "")).strip()
            if message:
                fragments.append(message)
        data = payload.get("data")
        if payload.get("ok") is True and isinstance(data, dict):
            fragments.append(json.dumps(data, sort_keys=True))
    if stdout.strip() and not fragments:
        fragments.append(stdout.strip())
    if stderr.strip():
        fragments.append(stderr.strip())
    return "\n".join(fragment for fragment in fragments if fragment).strip()


def _observed_command_output(stdout: str, stderr: str) -> str:
    return "\n".join(
        [
            "stdout:",
            stdout.rstrip() or "<empty>",
            "",
            "stderr:",
            stderr.rstrip() or "<empty>",
        ],
    )


def _jira_step_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["* No step log was captured."]
    lines: list[str] = []
    for step in value:
        if isinstance(step, dict):
            lines.append(
                f"* Step {step.get('step')}: {'✅' if step.get('status') == 'passed' else '❌'} "
                f"{step.get('action')} Observed: {{{{{_jira_safe(as_text(step.get('observed')))}}}}}"
            )
    return lines or ["* No step log was captured."]


def _markdown_step_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["- No step log was captured."]
    lines: list[str] = []
    for step in value:
        if isinstance(step, dict):
            lines.append(
                f"- {'✅' if step.get('status') == 'passed' else '❌'} Step {step.get('step')}: "
                f"{step.get('action')} Observed: `{as_text(step.get('observed'))}`"
            )
    return lines or ["- No step log was captured."]


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return as_text(step.get("status"))
    return ""


def _jira_safe(value: str) -> str:
    return value.replace("{", "").replace("}", "")


def _required_str(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} runtime_inputs.{key} must be a non-empty string.")
    return value


def _required_int(payload: dict[str, Any], key: str, path: Path) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{path} runtime_inputs.{key} must be an integer.")
    return value


def _required_str_list(payload: dict[str, Any], key: str, path: Path) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} runtime_inputs.{key} must be a non-empty list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{path} runtime_inputs.{key} entries must be non-empty strings.",
            )
        items.append(item)
    return tuple(items)


if __name__ == "__main__":
    main()
