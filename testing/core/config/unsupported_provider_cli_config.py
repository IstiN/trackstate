from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class UnsupportedProviderCliConfig:
    requested_command: tuple[str, ...]
    fallback_command: tuple[str, ...]
    expected_exit_code: int
    expected_error_code: str
    expected_error_category: str
    expected_provider: str
    expected_repository: str
    required_stdout_fragments: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "UnsupportedProviderCliConfig":
        provider = os.environ.get("TS273_PROVIDER", "gitlab")
        repository = os.environ.get("TS273_REPOSITORY", "owner/repo")
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            requested_command=(
                "trackstate",
                "session",
                "--target",
                "hosted",
                "--provider",
                provider,
                "--repository",
                repository,
            ),
            fallback_command=(
                dart_bin,
                "run",
                "trackstate",
                "session",
                "--target",
                "hosted",
                "--provider",
                provider,
                "--repository",
                repository,
            ),
            expected_exit_code=5,
            expected_error_code="UNSUPPORTED_PROVIDER",
            expected_error_category="unsupported",
            expected_provider=provider,
            expected_repository=repository,
            required_stdout_fragments=(
                '"ok": false',
                '"code": "UNSUPPORTED_PROVIDER"',
                '"category": "unsupported"',
            ),
        )
