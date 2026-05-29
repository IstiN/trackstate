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
