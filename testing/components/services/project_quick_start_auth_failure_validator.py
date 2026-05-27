from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.project_cli_auth_failure_result import (
    ProjectCliAuthFailureResult,
)


class ProjectQuickStartAuthFailureValidator:
    def __init__(
        self,
        *,
        repository_root: Path,
        probe: ProjectCliProbe,
        invalid_token: str | None = None,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._probe = probe
        self._quick_start_validator = ProjectQuickStartValidator(
            repository_root=self._repository_root,
            probe=probe,
        )
        self._invalid_token = (
            invalid_token
            or os.environ.get("TS236_INVALID_GITHUB_TOKEN")
            or "ghp_invalid_trackstate_token_for_ts236"
        )

    def validate(
        self,
        *,
        config: ProjectCliValidationConfig,
    ) -> ProjectCliAuthFailureResult:
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._quick_start_validator._resolve_target_repository(
            config,
            viewer_login,
        )
        repository_info = self._probe.repository_metadata(target_repository)
        if (
            not repository_info.succeeded
            and target_repository != config.upstream_repository
        ):
            target_repository = config.upstream_repository
            repository_info = self._probe.repository_metadata(target_repository)

        default_branch = self._quick_start_validator._repository_default_branch(
            repository_info,
        )
        readme_text = (self._repository_root / config.readme_path).read_text(
            encoding="utf-8",
        )
        quick_start_section = self._quick_start_validator._read_quick_start_section(
            readme_text,
        )
        project_path = config.project_path
        documented_command_template = (
            self._quick_start_validator._documented_validation_command(
                quick_start_section,
                project_path=project_path,
            )
        )
        documented_command = self._quick_start_validator._expand_documented_command(
            documented_command_template,
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=project_path,
        )
        with self._invalid_github_credentials():
            invalid_command_result = self._quick_start_validator._documented_command_result(
                documented_command,
            )

        return ProjectCliAuthFailureResult(
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=project_path,
            quick_start_section=quick_start_section,
            documented_command_template=documented_command_template,
            documented_command=documented_command,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            invalid_command_result=invalid_command_result,
        )

    @contextmanager
    def _invalid_github_credentials(self) -> Iterator[None]:
        environment_updates = {
            "GH_TOKEN": self._invalid_token,
            "GITHUB_TOKEN": self._invalid_token,
            "GH_PAGER": "cat",
        }
        previous_values = {
            key: os.environ.get(key)
            for key in environment_updates
        }
        try:
            for key, value in environment_updates.items():
                os.environ[key] = value
            yield
        finally:
            for key, previous_value in previous_values.items():
                if previous_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous_value
