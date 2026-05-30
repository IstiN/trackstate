from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalTargetValidationCliConfig:
    requested_command: tuple[str, ...]
    expected_exit_code: int
    expected_error_code: str
    expected_error_category: str
    expected_provider: str
    expected_target_type: str
    required_stdout_fragments: tuple[str, ...]
    expected_reason_fragments: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "LocalTargetValidationCliConfig":
        return cls(
            requested_command=("trackstate", "session", "--target", "local"),
            expected_exit_code=4,
            expected_error_code="REPOSITORY_OPEN_FAILED",
            expected_error_category="repository",
            expected_provider="local-git",
            expected_target_type="local",
            required_stdout_fragments=(
                '"ok": false',
                '"code": "REPOSITORY_OPEN_FAILED"',
                '"category": "repository"',
            ),
            expected_reason_fragments=(
                "git rev-parse --abbrev-ref HEAD",
                "fatal: not a git repository",
            ),
        )
