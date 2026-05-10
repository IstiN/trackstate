from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HostedAuthPrecedenceCliConfig:
    requested_environment_command: tuple[str, ...]
    fallback_environment_command: tuple[str, ...]
    requested_invalid_token_command: tuple[str, ...]
    fallback_invalid_token_command: tuple[str, ...]
    repository: str
    provider: str
    invalid_explicit_token: str
    expected_success_auth_source: str
    expected_failure_exit_code: int
    expected_failure_error_code: str
    expected_failure_error_category: str
    expected_visible_failure_message: str
    expected_failure_reason_fragments: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "HostedAuthPrecedenceCliConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        repository = os.environ.get("TS271_REPOSITORY", "IstiN/trackstate")
        provider = os.environ.get("TS271_PROVIDER", "github")
        invalid_explicit_token = os.environ.get(
            "TS271_INVALID_TOKEN",
            "DIFFERENT_INVALID_TOKEN",
        )
        base_command = (
            "--target",
            "hosted",
            "--provider",
            provider,
            "--repository",
            repository,
        )
        return cls(
            requested_environment_command=("trackstate", "session", *base_command),
            fallback_environment_command=(
                dart_bin,
                "run",
                "trackstate",
                "session",
                *base_command,
            ),
            requested_invalid_token_command=(
                "trackstate",
                "session",
                *base_command,
                "--token",
                invalid_explicit_token,
            ),
            fallback_invalid_token_command=(
                dart_bin,
                "run",
                "trackstate",
                "session",
                *base_command,
                "--token",
                invalid_explicit_token,
            ),
            repository=repository,
            provider=provider,
            invalid_explicit_token=invalid_explicit_token,
            expected_success_auth_source="env",
            expected_failure_exit_code=3,
            expected_failure_error_code="AUTHENTICATION_FAILED",
            expected_failure_error_category="auth",
            expected_visible_failure_message=(
                "Authentication is required for the selected provider."
            ),
            expected_failure_reason_fragments=("Bad credentials", "401"),
        )
