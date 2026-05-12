from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountByEmailUnsupportedCliConfig:
    requested_command: tuple[str, ...]
    fallback_command: tuple[str, ...]
    expected_exit_code: int
    expected_error_category: str
    expected_error_code_prefix: str
    expected_message_fragments: tuple[str, ...]
    required_stdout_fragments: tuple[str, ...]

    @classmethod
    def from_defaults(cls) -> "AccountByEmailUnsupportedCliConfig":
        email = os.environ.get("TS378_EMAIL", "user@example.com")
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            requested_command=(
                "trackstate",
                "read",
                "account-by-email",
                email,
            ),
            fallback_command=(
                dart_bin,
                "run",
                "trackstate",
                "read",
                "account-by-email",
                email,
            ),
            expected_exit_code=5,
            expected_error_category="unsupported",
            expected_error_code_prefix="UNSUPPORTED",
            expected_message_fragments=("unsupported", "email"),
            required_stdout_fragments=(
                '"ok": false',
                '"category": "unsupported"',
            ),
        )
