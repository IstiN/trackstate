from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.live_setup_test_config import load_live_setup_test_config


@dataclass(frozen=True)
class TrackStateCliHostedLfsRestrictionConfig:
    requested_command: tuple[str, ...]
    repository: str
    branch: str
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    issue_root_path: str
    local_attachment_name: str
    expected_exit_code: int
    accepted_error_codes: tuple[str, ...]
    expected_error_category: str
    required_error_message_fragments: tuple[str, ...]
    required_stdout_fragments: tuple[str, ...]
    required_gitattributes_fragment: str

    @property
    def issue_main_path(self) -> str:
        return f"{self.issue_root_path}/main.md"

    @property
    def attachment_repo_path(self) -> str:
        return f"{self.issue_root_path}/attachments/{self.local_attachment_name}"

    @property
    def repository_index_path(self) -> str:
        return f"{self.project_key}/.trackstate/index/issues.json"

    @property
    def fixture_repo_paths(self) -> tuple[str, ...]:
        return (
            self.repository_index_path,
            self.issue_main_path,
        )

    @classmethod
    def from_env(cls) -> "TrackStateCliHostedLfsRestrictionConfig":
        live_setup = load_live_setup_test_config()
        repository = live_setup.repository
        branch = live_setup.ref
        local_attachment_name = "assets.zip"
        return cls(
            requested_command=(
                "trackstate",
                "attachment",
                "upload",
                "--issue",
                "TS-22",
                "--file",
                local_attachment_name,
                "--target",
                "hosted",
                "--provider",
                "github",
                "--repository",
                repository,
                "--branch",
                branch,
            ),
            repository=repository,
            branch=branch,
            project_key="DEMO",
            project_name="Demo TrackState Project",
            issue_key="TS-22",
            issue_summary="TS-383 hosted Git LFS upload restriction fixture",
            issue_root_path="DEMO/TS-22",
            local_attachment_name=local_attachment_name,
            expected_exit_code=5,
            accepted_error_codes=(
                "UNSUPPORTED_OPERATION",
                "UNSUPPORTED_REQUEST",
            ),
            expected_error_category="unsupported",
            required_error_message_fragments=(
                "git lfs",
                "upload",
                "not",
                "implemented",
            ),
            required_stdout_fragments=(
                '"ok": false',
                '"category": "unsupported"',
            ),
            required_gitattributes_fragment="*.zip filter=lfs",
        )
