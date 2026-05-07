from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliCommandResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    json_payload: dict[str, object] | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def command_text(self) -> str:
        return " ".join(self.command)
