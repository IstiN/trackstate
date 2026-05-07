from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectCliValidationConfig:
    upstream_repository: str
    target_repository_override: str | None
    fork_repository_name: str
    project_path: str
    readme_path: Path
    project_template_path: Path
    required_quick_start_fragments: tuple[str, ...]
    required_runtime_readme_fragments: tuple[str, ...]
    visible_project_fields: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "ProjectCliValidationConfig":
        target_repository_override = os.environ.get(
            "TS74_SETUP_REPOSITORY",
            os.environ.get("TRACKSTATE_SETUP_REPOSITORY"),
        )
        return cls(
            upstream_repository=os.environ.get(
                "TS74_UPSTREAM_SETUP_REPOSITORY",
                "IstiN/trackstate-setup",
            ),
            target_repository_override=target_repository_override,
            fork_repository_name=os.environ.get(
                "TS74_FORK_REPOSITORY_NAME",
                "trackstate-setup",
            ),
            project_path=os.environ.get("TS74_PROJECT_PATH", "DEMO/project.json"),
            readme_path=Path("trackstate-setup/README.md"),
            project_template_path=Path("trackstate-setup/project-template.json"),
            required_quick_start_fragments=(
                "CLI quick start",
                "IstiN/trackstate",
                "DEMO/project.json",
                "DEMO/config/*.json",
            ),
            required_runtime_readme_fragments=(
                "`git/trees` for file discovery",
                "`contents` for markdown/config reads",
            ),
            visible_project_fields=(
                '"key": "DEMO"',
                '"name": "Demo TrackState Project"',
                '"defaultLocale": "en"',
                '"issueKeyPattern": "DEMO-{number}"',
                '"dataModel": "nested-tree"',
                '"configPath": "config"',
            ),
        )
