from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.frameworks.python.github_cli_project_framework import (
    GitHubCliProjectFramework,
)


def create_project_cli_probe(repository_root: Path) -> ProjectCliProbe:
    return GitHubCliProjectFramework(repository_root)
