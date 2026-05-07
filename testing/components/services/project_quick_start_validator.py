from __future__ import annotations

import json
from pathlib import Path

from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.project_cli_validation_result import (
    ProjectCliValidationResult,
)


class ProjectQuickStartValidator:
    def __init__(self, repository_root: Path, probe: ProjectCliProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        repository: str,
        project_path: str,
        expected_project_file: Path,
    ) -> ProjectCliValidationResult:
        auth_status = self._probe.auth_status()
        project_fetch = self._probe.get_project(repository, project_path)
        expected_project = json.loads(
            (self._repository_root / expected_project_file).read_text(encoding="utf-8")
        )
        return ProjectCliValidationResult(
            repository=repository,
            project_path=project_path,
            expected_project=expected_project,
            auth_status=auth_status,
            project_fetch=project_fetch,
        )
