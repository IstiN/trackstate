from __future__ import annotations

import json
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import yaml

from testing.components.pages.github_repository_file_page import (
    GitHubRepositoryFileObservation,
    GitHubRepositoryFilePage,
)
from testing.core.config.github_actions_dependabot_monitor_config import (
    GitHubActionsDependabotMonitorConfig,
)
from testing.core.interfaces.github_actions_dependabot_monitor_probe import (
    GitHubActionsDependabotMonitorObservation,
    GitHubActionsDependabotMonitorProbe,
)
from testing.core.interfaces.github_api_client import GitHubApiClient, GitHubApiClientError

FilePageFactory = Callable[[], AbstractContextManager[GitHubRepositoryFilePage]]


class GitHubActionsDependabotMonitorProbeService(
    GitHubActionsDependabotMonitorProbe
):
    def __init__(
        self,
        config: GitHubActionsDependabotMonitorConfig,
        *,
        github_api_client: GitHubApiClient,
        file_page_factory: FilePageFactory,
        screenshot_path: Path | None = None,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._file_page_factory = file_page_factory
        self._screenshot_path = screenshot_path

    def validate(self) -> GitHubActionsDependabotMonitorObservation:
        repository_metadata = self._load_json(endpoint=f"/repos/{self._config.repository}")
        default_branch = self._read_default_branch(repository_metadata)
        github_directory_entries = self._load_directory_entries(default_branch)

        raw_file_endpoint = (
            f"/repos/{self._config.repository}/contents/"
            f"{quote(self._config.dependabot_path, safe='/')}?ref="
            f"{quote(default_branch, safe='')}"
        )
        raw_file_text = ""
        raw_file_error: str | None = None
        dependabot_file_present = False
        try:
            raw_file_text = self._github_api_client.request_text(
                endpoint=raw_file_endpoint,
                field_args=["-H", "Accept: application/vnd.github.raw+json"],
            )
            dependabot_file_present = True
        except GitHubApiClientError as error:
            raw_file_error = str(error)

        parsed_file_is_mapping = False
        raw_file_parse_error: str | None = None
        updates_count = 0
        github_actions_update_present = False
        github_actions_directory: str | None = None
        github_actions_schedule_keys: list[str] = []
        github_actions_schedule_interval: str | None = None
        if raw_file_text:
            try:
                parsed = yaml.safe_load(raw_file_text)
            except yaml.YAMLError as error:
                raw_file_parse_error = str(error)
            else:
                if isinstance(parsed, dict):
                    parsed_file_is_mapping = True
                    updates = parsed.get("updates")
                    if isinstance(updates, list):
                        updates_count = len(updates)
                        github_actions_update = self._github_actions_update(updates)
                        if github_actions_update is not None:
                            github_actions_update_present = True
                            github_actions_directory = self._read_string_value(
                                github_actions_update,
                                "directory",
                            )
                            schedule = github_actions_update.get("schedule")
                            if isinstance(schedule, dict):
                                github_actions_schedule_keys = [
                                    key
                                    for key in schedule.keys()
                                    if isinstance(key, str) and key.strip()
                                ]
                                github_actions_schedule_interval = (
                                    self._read_string_value(
                                        schedule,
                                        "interval",
                                    )
                                )

        ui_expected_texts = tuple(
            dict.fromkeys(
                (
                    *self._config.expected_visible_texts,
                    *self._config.ui_missing_page_markers,
                )
            )
        )
        ui_url = self._build_file_url(default_branch=default_branch)
        ui_matched_text: str | None = None
        ui_body_text = ""
        ui_error: str | None = None
        ui_screenshot_path: str | None = None
        try:
            with self._file_page_factory() as file_page:
                ui_observation = file_page.open_file(
                    repository=self._config.repository,
                    branch=default_branch,
                    file_path=self._config.dependabot_path,
                    expected_texts=ui_expected_texts,
                    screenshot_path=(
                        str(self._screenshot_path)
                        if self._screenshot_path is not None
                        else None
                    ),
                    timeout_seconds=self._config.ui_timeout_seconds,
                )
            ui_url, ui_matched_text, ui_body_text, ui_screenshot_path = (
                ui_observation.url,
                ui_observation.matched_text,
                ui_observation.body_text,
                ui_observation.screenshot_path,
            )
        except AssertionError as error:
            ui_error = str(error)

        return GitHubActionsDependabotMonitorObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            github_directory_entries=github_directory_entries,
            dependabot_path=self._config.dependabot_path,
            dependabot_file_present=dependabot_file_present,
            raw_file_api_endpoint=raw_file_endpoint,
            raw_file_error=raw_file_error,
            raw_file_text=raw_file_text,
            raw_file_parse_error=raw_file_parse_error,
            parsed_file_is_mapping=parsed_file_is_mapping,
            updates_count=updates_count,
            github_actions_update_present=github_actions_update_present,
            github_actions_directory=github_actions_directory,
            github_actions_schedule_keys=github_actions_schedule_keys,
            github_actions_schedule_interval=github_actions_schedule_interval,
            ui_url=ui_url,
            ui_matched_text=ui_matched_text,
            ui_body_text=ui_body_text,
            ui_error=ui_error,
            ui_screenshot_path=ui_screenshot_path,
        )

    def _load_json(self, *, endpoint: str) -> dict[str, Any]:
        response_text = self._github_api_client.request_text(endpoint=endpoint)
        payload = json.loads(response_text)
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Expected GitHub API payload for {endpoint} to decode to a mapping."
            )
        return payload

    def _load_directory_entries(self, default_branch: str) -> list[str]:
        endpoint = (
            f"/repos/{self._config.repository}/contents/.github?ref="
            f"{quote(default_branch, safe='')}"
        )
        try:
            response_text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError:
            return []

        payload = json.loads(response_text)
        if not isinstance(payload, list):
            return []
        entries: list[str] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                entries.append(name)
        return entries

    def _read_default_branch(self, repository_metadata: dict[str, Any]) -> str:
        default_branch = repository_metadata.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return self._config.base_branch

    def _github_actions_update(
        self,
        updates: list[object],
    ) -> dict[str, Any] | None:
        for update in updates:
            if not isinstance(update, dict):
                continue
            ecosystem = self._read_string_value(update, "package-ecosystem")
            if ecosystem == self._config.expected_package_ecosystem:
                return update
        return None

    def _read_string_value(
        self,
        payload: dict[str, Any],
        key: str,
    ) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _build_file_url(self, *, default_branch: str) -> str:
        normalized_path = self._config.dependabot_path.strip("/")
        encoded_segments = "/".join(
            quote(segment, safe="") for segment in normalized_path.split("/") if segment
        )
        return (
            f"https://github.com/{self._config.repository}/blob/"
            f"{quote(default_branch, safe='')}/{encoded_segments}"
        )
