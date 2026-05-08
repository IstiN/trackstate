from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class TemplateWorkflowFileConfig:
    repository: str
    workflow_path: str
    expected_default_branch: str | None = None

    @property
    def workflow_directory_path(self) -> str:
        directory, _, _ = self.workflow_path.rpartition("/")
        return directory

    @property
    def workflow_filename(self) -> str:
        _, _, filename = self.workflow_path.rpartition("/")
        return filename

    @classmethod
    def from_env(cls) -> "TemplateWorkflowFileConfig":
        expected_default_branch = os.getenv("TS82_EXPECTED_DEFAULT_BRANCH")
        return cls(
            repository=os.getenv(
                "TS82_TEMPLATE_REPOSITORY",
                os.getenv(
                    "TRACKSTATE_TEMPLATE_REPOSITORY",
                    "IstiN/trackstate-setup",
                ),
            ),
            workflow_path=os.getenv(
                "TS82_WORKFLOW_PATH",
                ".github/workflows/install-update-trackstate.yml",
            ),
            expected_default_branch=(
                expected_default_branch if expected_default_branch else None
            ),
        )
