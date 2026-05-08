from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ReleaseSourceWorkflowConfig:
    repository: str
    default_branch: str
    workflow_path: str

    @property
    def releases_api_endpoint(self) -> str:
        return f"/repos/{self.repository}/releases?per_page=1"

    @property
    def tags_api_endpoint(self) -> str:
        return f"/repos/{self.repository}/tags?per_page=1"

    @property
    def releases_page_url(self) -> str:
        return f"https://github.com/{self.repository}/releases"

    @property
    def tags_page_url(self) -> str:
        return f"https://github.com/{self.repository}/tags"


def load_release_source_workflow_config() -> ReleaseSourceWorkflowConfig:
    return ReleaseSourceWorkflowConfig(
        repository=os.getenv(
            "TRACKSTATE_RELEASE_SOURCE_REPOSITORY",
            "IstiN/trackstate-setup",
        ),
        default_branch=os.getenv("TRACKSTATE_RELEASE_SOURCE_BRANCH", "main"),
        workflow_path=os.getenv(
            "TRACKSTATE_RELEASE_SOURCE_WORKFLOW_PATH",
            ".github/workflows/install-update-trackstate.yml",
        ),
    )
