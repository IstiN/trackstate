from __future__ import annotations

from typing import Protocol

from testing.core.config.hosted_auth_precedence_cli_config import (
    HostedAuthPrecedenceCliConfig,
)
from testing.core.models.hosted_auth_precedence_cli_result import (
    HostedAuthPrecedenceCliObservation,
    HostedAuthPrecedenceTokenResolution,
)


class HostedAuthPrecedenceCliProbe(Protocol):
    def resolve_environment_token(
        self,
    ) -> tuple[HostedAuthPrecedenceTokenResolution, str | None]: ...

    def hosted_session_with_environment_token(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
        environment_token: str,
    ) -> HostedAuthPrecedenceCliObservation: ...

    def hosted_session_with_explicit_invalid_token(
        self,
        *,
        config: HostedAuthPrecedenceCliConfig,
        environment_token: str,
    ) -> HostedAuthPrecedenceCliObservation: ...
