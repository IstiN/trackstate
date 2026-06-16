from __future__ import annotations

from pathlib import Path

from testing.core.config.hosted_auth_precedence_cli_config import (
    HostedAuthPrecedenceCliConfig,
)
from testing.core.interfaces.hosted_auth_precedence_cli_probe import (
    HostedAuthPrecedenceCliProbe,
)
from testing.core.models.hosted_auth_precedence_cli_result import (
    HostedAuthPrecedenceCliValidationResult,
)


class HostedAuthPrecedenceCliValidator:
    def __init__(
        self,
        repository_root: Path,
        probe: HostedAuthPrecedenceCliProbe,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._probe = probe

    def validate(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
    ) -> HostedAuthPrecedenceCliValidationResult:
        token_resolution, environment_token = self._probe.resolve_environment_token()
        if environment_token is None:
            return HostedAuthPrecedenceCliValidationResult(
                token_resolution=token_resolution,
                environment_session=None,
                explicit_invalid_token_session=None,
            )

        project_json_ok, project_json_reason = (
            self._probe.verify_hosted_repository_has_project_json(
                config=config,
                environment_token=environment_token,
            )
        )
        if not project_json_ok:
            raise AssertionError(
                "Precondition failed: the configured hosted repository is not "
                "initialized as a TrackState project. "
                f"Repository: {config.repository}. "
                f"Reason: {project_json_reason}\n"
                "Set TS271_REPOSITORY to a hosted TrackState project that contains "
                "project.json, or ensure the default repository is accessible."
            )

        return HostedAuthPrecedenceCliValidationResult(
            token_resolution=token_resolution,
            environment_session=self._probe.hosted_session_with_environment_token(
                config=config,
                environment_token=environment_token,
            ),
            explicit_invalid_token_session=self._probe.hosted_session_with_explicit_invalid_token(
                config=config,
                environment_token=environment_token,
            ),
        )
