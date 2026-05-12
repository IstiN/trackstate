from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class AccountByEmailUnsupportedCliObservation:
    requested_command: tuple[str, ...]
    executed_command: tuple[str, ...]
    fallback_reason: str | None
    result: CliCommandResult

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)

    @property
    def output(self) -> str:
        fragments = [
            self.result.stdout.strip(),
            self.result.stderr.strip(),
        ]
        return "\n".join(fragment for fragment in fragments if fragment).strip()


@dataclass(frozen=True)
class AccountByEmailUnsupportedCliValidationResult:
    account_by_email_unsupported: AccountByEmailUnsupportedCliObservation
