from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubActionsDependabotMonitorObservation:
    repository: str
    default_branch: str
    github_directory_entries: list[str]
    dependabot_path: str
    dependabot_file_present: bool
    raw_file_api_endpoint: str
    raw_file_error: str | None
    raw_file_text: str
    parsed_file_is_mapping: bool
    updates_count: int
    github_actions_update_present: bool
    github_actions_directory: str | None
    github_actions_schedule_keys: list[str]
    github_actions_schedule_interval: str | None
    ui_url: str
    ui_matched_text: str | None
    ui_body_text: str
    ui_error: str | None
    ui_screenshot_path: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubActionsDependabotMonitorProbe(Protocol):
    def validate(self) -> GitHubActionsDependabotMonitorObservation: ...
